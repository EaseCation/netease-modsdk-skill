"""使用时检查配置的 Wiki 上游；不修改完整工作区，不安装后台任务。"""
import hashlib
import time
from pathlib import Path
from config import SKILL_ROOT
from network import atomic_json, fingerprint, git, load_json, NetworkError, file_lock, LockBusyError

STATE = SKILL_ROOT / '.local/upstream.json'


def remote_head(values):
    ref = values['MODSDK_WIKI_REF']
    patterns = [ref] if ref.startswith('refs/') else ['refs/heads/' + ref, 'refs/tags/' + ref, 'refs/tags/' + ref + '^{}']
    output = git(['ls-remote', '--exit-code', '--', values['MODSDK_WIKI_REPOSITORY'], *patterns],
                 network=True, values=values)
    refs = dict(line.split()[::-1] for line in output.splitlines() if len(line.split()) == 2)
    order = [patterns[0]] if len(patterns) == 1 else [patterns[0], patterns[2], patterns[1]]
    for item in order:
        if item in refs:
            return refs[item]
    raise ValueError('上游分支或标签不存在：' + ref)


def _check_updates(root, values, force=False):
    hours = int(values['MODSDK_UPDATE_CHECK_HOURS'])
    if not hours and not force:
        return {'status': 'disabled'}
    key = hashlib.sha256(('\0'.join([str(root), values['MODSDK_WIKI_REPOSITORY'], values['MODSDK_WIKI_REF'], fingerprint(values)])).encode()).hexdigest()[:20]
    states = load_json(STATE)
    cached = states.get(key, {})
    now = time.time()
    due = force or now - cached.get('checked_at', 0) >= hours * 3600
    if due:
        # 先保存短租约，避免多个会话在网络失败时同时反复探测。
        if cached.get('in_progress_until', 0) > now:
            return {'status': 'check_in_progress'}
        states[key] = {**cached, 'in_progress_until': now + 2 * int(values['MODSDK_NETWORK_TIMEOUT']) + 5}
        atomic_json(STATE, states)
        try:
            cached = {'checked_at': now, 'remote_commit': remote_head(values)}
        except (OSError, ValueError) as error:
            cached = {'checked_at': now, 'error': str(error), 'error_type': 'network' if isinstance(error, NetworkError) else 'source'}
        states = load_json(STATE)
        states[key] = cached
        # 仅保留最近使用的来源状态。
        states = dict(sorted(states.items(), key=lambda item: item[1].get('checked_at', 0))[-16:])
        atomic_json(STATE, states)
    if 'error' in cached:
        return {'status': 'unavailable' if due else 'unavailable_cached', 'message': cached['error'], 'error_type': cached.get('error_type', 'source'),
                'local_snapshot_usable': root.exists()}
    local = git(['rev-parse', 'HEAD'], root, values=values)
    available = local != cached.get('remote_commit')
    result = {'status': 'update_available' if available else 'up_to_date',
              'checked_now': due, 'local_commit': local[:12], 'remote_commit': cached['remote_commit'][:12]}
    if available:
        managed = (root / '.git/modsdk-skill-checkout.json').is_file()
        clean = not git(['status', '--porcelain', '--untracked-files=all'], root, values=values)
        result['next_action'] = 'setup.py --update' if managed and clean else '保留现有工作区；由其维护流程更新，不自动 pull/reset'
    return result


def check_updates(root, values, force=False):
    if not int(values['MODSDK_UPDATE_CHECK_HOURS']) and not force:
        return {'status':'disabled'}
    try:
        with file_lock(STATE.with_suffix('.lock'), timeout=.1):
            return _check_updates(root, values, force)
    except LockBusyError:
        return {'status':'check_in_progress'}
