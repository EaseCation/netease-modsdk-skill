"""有总超时的子进程、只读下载代理与失败冷却；不改变全局 Git 配置。"""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
from urllib.parse import urlsplit
from config import SKILL_ROOT, read_config

COOLDOWN_SECONDS = 900
_HTTP_LOCK = threading.Lock()


class NetworkError(ValueError):
    pass


class LockBusyError(ValueError):
    pass


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_json(path, default=None):
    if not path.exists():
        return {} if default is None else default
    try:
        return json.loads(path.read_text(encoding='utf8'))
    except (ValueError, OSError):
        return {} if default is None else default


def sanitize(text):
    text = re.sub(r'(https?://)[^/@\s]+@', r'\1[redacted]@', str(text))
    text = re.sub(r'(https?://[^\s?]+)\?[^\s]+', r'\1?[redacted]', text)
    text = re.sub(r'\b(?:gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+)\b', '[redacted]', text)
    return text[:800]


def run_bounded(command, *, cwd=None, stdin=None, timeout=30, env=None):
    """超时后结束本次进程树，避免 Git 子进程/凭据提示继续悬挂。"""
    binary = isinstance(stdin, bytes)
    process = subprocess.Popen(command, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=not binary, encoding=None if binary else 'utf8', env=env,
                               start_new_session=os.name != 'nt')
    try:
        out, err = process.communicate(stdin, timeout=timeout)
    except subprocess.TimeoutExpired:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True, timeout=10)
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        try:
            process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)
        raise NetworkError('操作超过 {} 秒，已终止本次进程。'.format(round(timeout, 1)))
    return subprocess.CompletedProcess(command, process.returncode, out, err)



def clear_http_headers(cwd=None):
    result = run_bounded(['git','config','--name-only','--get-regexp',r'^http\..*(extraheader|cookiefile)$'],cwd=cwd,timeout=5)
    flags = ['-c','http.extraheader=','-c','http.cookiefile=','-c','http.savecookies=false']
    if result.returncode == 0:
        for key in result.stdout.splitlines():
            flags += ['-c', key + '=']
    return flags


@contextlib.contextmanager
def file_lock(path, timeout=3):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as handle:
        if handle.tell() == 0:
            handle.write(b'0');handle.flush()
        end = time.monotonic() + timeout
        while True:
            try:
                handle.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= end:raise LockBusyError('另一个操作正在使用此记录，本次停止，不重复重试')
                time.sleep(.05)
        try:yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_UN)

def proxy_prefix(values):
    prefix = values['MODSDK_GITHUB_PROXY_PREFIX'].strip()
    if not prefix:
        return ''
    parsed = urlsplit(prefix)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('MODSDK_GITHUB_PROXY_PREFIX 必须是无凭据、查询参数和片段的 HTTPS 前缀')
    return prefix.rstrip('/') + '/'


def fingerprint(values):
    # 网络环境变化后可重新尝试；只保存摘要，不保存代理中的认证内容。
    fields = [values['MODSDK_GITHUB_PROXY_PREFIX'], values['MODSDK_NETWORK_TIMEOUT']]
    fields += [os.environ.get(k, '') for k in ('HTTPS_PROXY', 'HTTP_PROXY', 'ALL_PROXY', 'https_proxy', 'http_proxy', 'all_proxy', 'NO_PROXY', 'no_proxy')]
    return hashlib.sha256('\0'.join(fields).encode()).hexdigest()[:16]


def circuit_path(scope, values):
    key = hashlib.sha256((scope + fingerprint(values)).encode()).hexdigest()[:20]
    return SKILL_ROOT / '.local/network' / (key + '.json')


def check_circuit(scope, values):
    state = load_json(circuit_path(scope, values))
    if state.get('retry_after', 0) > time.time():
        raise NetworkError('网络失败冷却中，本次未再联网。请启用代理或切换网络；调整后可运行 setup.py --retry-network，再重试一次。')


def fail_circuit(scope, values):
    atomic_json(circuit_path(scope, values), {'retry_after': time.time() + COOLDOWN_SECONDS})


def clear_circuits():
    for path in (SKILL_ROOT / '.local/network').glob('*.json'):
        path.unlink()


def network_message(detail):
    return ('网络访问失败，已停止本轮重试。可启用系统代理、配置可信代理域名前缀，或切换网络；'
            '已有快照可继续离线查询，无快照时需恢复网络后安装。原因：' + sanitize(detail))


def git(args, cwd=None, stdin=None, *, network=False, values=None, timeout=None, cleanup=None, strip_output=True):
    values = values or read_config()
    routes = ['', proxy_prefix(values)] if network else ['']
    routes = list(dict.fromkeys(routes))
    scope = 'git-read'
    if network:
        check_circuit(scope, values)
    deadline = time.monotonic() + (timeout or int(values['MODSDK_NETWORK_TIMEOUT']) * len(routes))
    error = ''
    for number, route in enumerate(routes):
        if number and cleanup:
            cleanup()
        command = ['git', '-c', 'http.version=HTTP/1.1', '-c', 'http.lowSpeedLimit=1',
                   '-c', 'http.lowSpeedTime=' + values['MODSDK_NETWORK_TIMEOUT'],
                   '-c', 'filter.lfs.smudge=', '-c', 'filter.lfs.process=', '-c', 'filter.lfs.required=false']
        if network:
            command += ['-c', 'credential.helper=', '-c', 'credential.interactive=false', *clear_http_headers(cwd)]
        if route:
            command += ['-c', 'url.' + route + 'https://github.com/.insteadOf=https://github.com/']
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            result = run_bounded(command + args, cwd=cwd, stdin=stdin,
                                 timeout=min(int(values['MODSDK_NETWORK_TIMEOUT']), remaining),
                                 env={**os.environ, 'GIT_LFS_SKIP_SMUDGE': '1', 'GIT_TERMINAL_PROMPT': '0', 'GCM_INTERACTIVE': 'never'})
            if result.returncode == 0:
                return result.stdout.strip() if strip_output else result.stdout
            error = result.stderr.strip()
            if result.returncode == 2 and args and args[0] == 'ls-remote' and not error:
                raise ValueError('上游分支或标签没有匹配记录')
            transient = bool(re.search(r'timed out|timeout|resolve host|connect|connection|SSL|TLS|RPC failed|EOF|502|503|504|429|network|unable to access|early eof|fetch', error, re.I))
            if not network or not transient:
                raise ValueError('Git 操作失败：' + sanitize(error))
        except NetworkError as exc:
            error = str(exc)
            if not network:
                raise
    fail_circuit(scope, values)
    raise NetworkError(network_message(error or '总时间预算已用尽'))


def fetch_public(url, max_bytes=2_000_000):
    values = read_config()
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in ('raw.githubusercontent.com', 'github.com') or parsed.username or parsed.password:
        raise ValueError('只读下载仅允许登记的公开 GitHub 地址')
    with _HTTP_LOCK:
        check_circuit('public-http', values)
        prefix = proxy_prefix(values)
        routes = [url] + ([prefix + url] if prefix else [])
        error = ''
        for route in routes:
            try:
                result = run_bounded([sys.executable, str(Path(__file__).resolve()), '--http-worker', route, str(max_bytes)],
                                     stdin=b'', timeout=int(values['MODSDK_NETWORK_TIMEOUT']))
                if result.returncode == 0:
                    return result.stdout
                error = result.stderr.decode('utf8', errors='replace')
                if error.startswith('PERMANENT:'):
                    raise ValueError('原文下载失败：' + sanitize(error.removeprefix('PERMANENT:')))
            except NetworkError as exc:
                error = str(exc)
        fail_circuit('public-http', values)
        raise NetworkError(network_message(error))


def _http_worker(url, max_bytes):
    import urllib.request
    import urllib.error
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'netease-modsdk-skill', 'Accept-Encoding': 'identity'})
        with urllib.request.urlopen(request, timeout=15) as response:
            data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            print('PERMANENT:来源文件超过大小预算', file=sys.stderr)
            return 1
        sys.stdout.buffer.write(data)
        return 0
    except urllib.error.HTTPError as exc:
        prefix = 'PERMANENT:' if exc.code in (400, 401, 404, 410) else ''
        print(prefix + 'HTTP ' + str(exc.code), file=sys.stderr)
        return 1
    except (OSError, ValueError) as exc:
        print(sanitize(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--http-worker':
        sys.exit(_http_worker(sys.argv[2], int(sys.argv[3])))
    raise SystemExit('此模块由安装器和原文读取器调用。')
