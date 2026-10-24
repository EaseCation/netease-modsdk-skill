#!/usr/bin/env python3
"""显式开启后才加载的本地查询复盘与受限标注维护入口。"""
import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from config import SKILL_ROOT, read_config, resolve_root, validate_wiki
from network import atomic_json, git, load_json, run_bounded, sanitize, file_lock, clear_http_headers

LEDGER = SKILL_ROOT / '.local/maintenance/ledger.json'
TRANSACTION = SKILL_ROOT / '.local/maintenance/transaction.json'
ANNOTATIONS = 'knowledge/annotations.json'


def enabled():
    # 仅进程环境开启；不接受仓库 .env 自动授予维护能力。
    return os.environ.get('MODSDK_MAINTAINER_MODE') == '1'


def require_enabled():
    if not enabled():
        raise ValueError('此入口未启用。')


def seconds():
    value = os.environ.get('MODSDK_MAINTAINER_REVIEW_HOURS', '24')
    if not value.isdigit() or not 1 <= int(value) <= 720:
        raise ValueError('整理间隔须为 1–720 小时')
    return int(value) * 3600


def digest(data):
    return hashlib.sha256(data).hexdigest()


def ledger():
    return load_json(LEDGER, {'started_at': time.time(), 'last_organized_at': None,
                              'last_reminded_at': None, 'observations': [], 'issues': []})


def save_ledger(state):
    require_enabled()
    atomic_json(LEDGER, state)


def issue_key(root, query):
    return digest((str(root) + '\0' + query).encode())[:16]


def add_issue(state, root, query, summary):
    key = issue_key(root, query)
    now = time.time()
    existing = next((i for i in state['issues'] if i['id'] == key), None)
    if existing:
        if existing['status'] != 'pending':
            existing.update({'status': 'pending', 'reopened_at': now})
        existing['last_seen_at'] = now
        existing['occurrences'] += 1
        existing['summary'] = summary[:600]
    else:
        if len(state['issues']) >= 200:
            closed = next((i for i in state['issues'] if i['status'] != 'pending'), None)
            if closed:
                state['issues'].remove(closed)
            else:
                state['suppressed_new_issues'] = state.get('suppressed_new_issues', 0) + 1
                return None
        state['issues'].append({'id': key, 'wiki_root': str(root), 'query': query[:1500],
                                'summary': summary[:600], 'status': 'pending', 'occurrences': 1,
                                'first_seen_at': now, 'last_seen_at': now})
    return key


def capture_query(arguments, root, invoke):
    """正常 stdout 不变；开关关闭时调用者不会导入本模块。"""
    require_enabled()
    commands = ('resolve', 'search', 'detail')
    command = next((x for x in arguments if x in commands), None)
    if not command:
        return invoke()
    request = ' '.join(arguments)[:1500]
    original_stdin = sys.stdin
    if '--plan-file' in arguments and arguments.index('--plan-file') + 1 < len(arguments):
        name = arguments[arguments.index('--plan-file') + 1]
        if name == '-':
            text = sys.stdin.read()
            sys.stdin = io.StringIO(text)
        else:
            text = Path(name).read_text(encoding='utf8')
        try:
            plan = json.loads(text)
            request = '；'.join(i.get('query', '') for i in plan.get('intents', []))[:1500]
        except (ValueError, AttributeError, TypeError):
            pass
    stream = sys.stdout
    captured = io.StringIO()

    class Tee:
        def write(self, value):
            if captured.tell() < 100000:
                captured.write(value[:100000 - captured.tell()])
            return stream.write(value)

        def flush(self):
            stream.flush()

    error = None
    try:
        with contextlib.redirect_stdout(Tee()):
            return invoke()
    except (ValueError, OSError) as exc:
        error = sanitize(exc)
        raise
    finally:
        sys.stdin = original_stdin
        try:
            output = json.loads(captured.getvalue()) if not error else {}
            if not isinstance(output, dict):
                output = {}
            with file_lock(LEDGER.with_suffix('.lock')):
                state = ledger()
                row = {'at': time.time(), 'wiki_root': str(root), 'command': command, 'query': request,
                       'chars': len(captured.getvalue()), 'unresolved': output.get('unresolved_intents', []),
                       'candidates': [r.get('name') or r.get('id') for r in output.get('results', [])[:8] if r.get('name') or r.get('id')],
                       'error': error}
                state['observations'] = (state['observations'] + [row])[-60:]
                state['last_activity_at'] = row['at']
                if error or row['unresolved'] or not row['candidates']:
                    add_issue(state, root, request, error or '未命中/有未解决项；需先区分预期能力边界与检索缺口。')
                save_ledger(state)
        except (OSError, ValueError, TypeError, AttributeError):
            # 记录失败不改变业务查询结果，也不在工作中发整理提醒。
            pass


def checkpoint(work_complete):
    require_enabled()
    with file_lock(LEDGER.with_suffix('.lock')):
        state = ledger()
        pending = [i for i in state['issues'] if i['status'] == 'pending']
        now = time.time()
        last = state['last_organized_at'] or state['started_at']
        reminded = state['last_reminded_at'] or 0
        due = bool(work_complete and pending and now - last >= seconds() and now - reminded >= seconds())
        if due:
            state['last_reminded_at'] = now
        if work_complete:
            state['last_work_completed_at'] = now
            save_ledger(state)
        result = {'remind': due, 'pending': len(pending), 'last_organized_at': state['last_organized_at']}
        if due:
            result['message'] = '本地有 {} 个待复核的查询问题，已到整理时间；当前工作结束后可以进行整理。'.format(len(pending))
        return result


def repo_slug(url):
    match = re.fullmatch(r'https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?', url)
    if not match:
        raise ValueError('维护写入仅支持明确配置的 https://github.com/owner/repo.git，不使用下载代理域名')
    return match[1]


def github(slug, endpoint):
    result = run_bounded(['gh', 'api', '--hostname', 'github.com', endpoint], timeout=30,
                         env={**os.environ, 'GH_HOST': 'github.com', 'GH_PROMPT_DISABLED': '1'})
    if result.returncode:
        raise ValueError('GitHub 登录、权限或网络检查失败；停止维护，保留本地记录。' + sanitize(result.stderr))
    return json.loads(result.stdout)


def permission(values):
    require_enabled()
    slug = repo_slug(values['MODSDK_WIKI_REPOSITORY'])
    user = github(slug, 'user')
    repo = github(slug, 'repos/' + slug)
    if repo.get('full_name', '').lower() != slug.lower() or not repo.get('permissions', {}).get('push'):
        raise ValueError('当前 gh 登录者没有指定 Wiki 仓库的写权限；只保留本地问题，不修改或推送。')
    head = github(slug, 'repos/' + slug + '/git/ref/heads/main')['object']['sha']
    return {'login': user['login'], 'repository': slug, 'remote_head': head}


def workspace():
    values = read_config()
    if values['MODSDK_WIKI_REF'] != 'main':
        raise ValueError('维护入口只面向配置的 main；先在独立任务中处理其他分支')
    root = validate_wiki(resolve_root(values['MODSDK_WIKI_ROOT']))
    if git(['remote', 'get-url', 'origin'], root) != values['MODSDK_WIKI_REPOSITORY']:
        raise ValueError('工作区 origin 与指定仓库不同，停止维护')
    return root, values


def tool_fingerprint():
    paths = sorted(list((SKILL_ROOT / 'scripts').glob('*.py')) + list((SKILL_ROOT / 'evals').glob('*.json')) + list((SKILL_ROOT / 'references').glob('*')))
    return digest(b''.join(str(p.relative_to(SKILL_ROOT)).encode() + b'\0' + p.read_bytes() for p in paths if p.is_file()))


def changed_paths(root):
    # 包括已暂存、未暂存和未跟踪文件，不能夹带其他任务的内容。
    raw = git(['status', '--porcelain', '-z', '--untracked-files=all'], root, strip_output=False)
    rows = [r for r in raw.split('\0') if r]
    if any('R' in r[:2] or 'C' in r[:2] for r in rows):
        raise ValueError('不支持夹带重命名或复制操作')
    return {r[3:] for r in rows}


def begin():
    require_enabled()
    root, values = workspace()
    if git(['status','--porcelain','--untracked-files=all'],SKILL_ROOT):
        raise ValueError('Skill 有未完成修改；先完成其维护，不能使用正在变化的题库或工具验收 Wiki')
    identity = permission(values)
    if changed_paths(root):
        raise ValueError('Wiki 有现存修改，保留现场；先使用干净且与 main 对齐的工作区')
    head = git(['rev-parse', 'HEAD'], root)
    if head != identity['remote_head']:
        raise ValueError('Wiki 未对齐最新 main；受管副本可先 setup.py --update，完整工作区按其维护流程更新')
    transaction = {'root': str(root), 'base': head, 'repository': identity['repository'],
                   'started_at': time.time(), 'phase': 'editing', 'probes': [], 'tools': tool_fingerprint()}
    previous = load_json(TRANSACTION)
    if previous and previous.get('phase') not in ('published', 'closed'):
        raise ValueError('已有未完成整理，先 inspect 并继续原记录，不覆盖其回执')
    atomic_json(TRANSACTION, transaction)
    return {'ready': True, 'login': identity['login'], 'wiki_root': str(root), 'editable': [ANNOTATIONS]}


def transaction_state():
    require_enabled()
    root, values = workspace()
    state = load_json(TRANSACTION)
    if state.get('root') != str(root) or state.get('repository') != repo_slug(values['MODSDK_WIKI_REPOSITORY']):
        raise ValueError('没有与当前工作区对应的整理记录，请先 begin')
    return root, values, state


def inspect_changes(root, state):
    if changed_paths(root) - {ANNOTATIONS}:
        raise ValueError('发现白名单外的修改；只允许维护独立 annotations.json，保留其他文件并停止')
    before = json.loads(git(['show', state['base'] + ':' + ANNOTATIONS], root))
    current = json.loads((root / ANNOTATIONS).read_text(encoding='utf8'))
    if {k:v for k,v in before.items() if k != 'entries'} != {k:v for k,v in current.items() if k != 'entries'}:
        raise ValueError('不能修改标注协议或顶层结构')
    left = {r['id']: r for r in before['entries']}
    right = {r['id']: r for r in current['entries']}
    changed = [id for id in left.keys() | right.keys() if left.get(id) != right.get(id)]
    if not 1 <= len(changed) <= 20:
        raise ValueError('每轮整理须有 1–20 条实质标注变更；大批量或仅格式变化需单独处理')
    allowed = {'id','source_sha256','authority','tags','aliases','questions','usage','cautions','related','source_dependencies','retrieval'}
    for id in changed:
        old, new = left.get(id, {}), right.get(id)
        if new is None:
            continue
        if set(new) - allowed or new.get('authority') != 'curated_note' or new.get('retrieval') != old.get('retrieval'):
            raise ValueError('不能扩张字段或改检索约束；问题涉及过滤规则时另行处理：' + id)
        if len(new.get('usage', '')) > max(400, len(old.get('usage', ''))):
            raise ValueError('补充正文过长：' + id)
        for key, cap, width in [('aliases',24,100),('questions',6,160),('cautions',6,240),('related',12,500)]:
            entries = new.get(key, [])
            if not isinstance(entries, list) or len(entries) > max(cap, len(old.get(key, []))) or any(not isinstance(x, str) or len(x) > width for x in entries):
                raise ValueError('标注字段超出紧凑预算：' + id + ':' + key)
    return sorted(changed)


def probe_result(root, spec):
    result = run_bounded([sys.executable, str(SKILL_ROOT / 'scripts/query.py'), '--max-chars', str(spec['max_chars']),
                          'resolve', '--plan-file', '-', '--limit', '8'], stdin=json.dumps(spec['plan'], ensure_ascii=False),
                         timeout=120, env={**os.environ, 'MODSDK_WIKI_ROOT': str(root), 'MODSDK_MAINTAINER_MODE': '0'})
    if result.returncode:
        return {'passed': False, 'error': sanitize(result.stderr), 'chars': len(result.stderr)}
    output = json.loads(result.stdout)
    index = json.loads((root / '.api-index/index.json').read_text())
    keys = {r['key']: r['id'] for r in index['records']}
    known = set(keys.values())
    if (set(spec['required_ids']) | set(spec['forbidden_ids'])) - known:
        raise ValueError('复现中存在原文未收录的完整 ID')
    returned = {keys[r['id']] for r in output['results']}
    return {'passed': (not returned if spec.get('expect_no_capability_match') else set(spec['required_ids']) <= returned) and not set(spec['forbidden_ids']) & returned,
            'ids': sorted(returned), 'chars': len(result.stdout.rstrip('\n'))}


def add_probe(file):
    root, _, state = transaction_state()
    if state['phase'] != 'editing' or changed_paths(root) or git(['rev-parse','HEAD'],root) != state['base']:
        raise ValueError('先在未修改的基线记录复现问题，再编辑标注')
    spec = json.loads(Path(file).read_text(encoding='utf8'))
    required = {'issue_id','plan','required_ids','forbidden_ids','max_chars'}
    if not required <= set(spec) or set(spec) - required - {'expect_no_capability_match'} or not isinstance(spec['max_chars'], int) or not 500 <= spec['max_chars'] <= 18000:
        raise ValueError('复现文件字段应为 issue_id、plan、required_ids、forbidden_ids、max_chars')
    if not any(i['id'] == spec['issue_id'] and i['status'] == 'pending' and i['wiki_root'] == str(root) for i in ledger()['issues']):
        raise ValueError('复现必须关联当前工作区的待整理问题')
    for key in ('required_ids','forbidden_ids'):
        if not isinstance(spec[key], list) or any(not isinstance(x,str) for x in spec[key]):
            raise ValueError('参考 ID 必须为字符串数组')
    if 'expect_no_capability_match' in spec and not isinstance(spec['expect_no_capability_match'],bool):
        raise ValueError('expect_no_capability_match 须为布尔值')
    if not spec['required_ids'] and not (spec.get('expect_no_capability_match') and spec['forbidden_ids']):
        raise ValueError('需有经原文核实的期望 ID；能力边界题需声明无能力命中及禁止误用的 ID')
    if len(state['probes']) >= 20:
        raise ValueError('每轮最多 20 个复现')
    before = probe_result(root, spec)
    state['probes'].append({'spec': spec, 'before': before})
    atomic_json(TRANSACTION, state)
    return before


def validate():
    root, _, state = transaction_state()
    if state['phase'] != 'editing' or git(['rev-parse', 'HEAD'], root) != state['base']:
        raise ValueError('工作区提交已变化，不能复用旧基线')
    if state['tools'] != tool_fingerprint():
        raise ValueError('验证工具或固定题库已变化；不能通过改答案/预算掩盖退化')
    changed = inspect_changes(root, state)
    if not state['probes']:
        raise ValueError('尚未记录本轮问题的基线复现')
    note_hash = digest((root / ANNOTATIONS).read_bytes())
    env = {**os.environ, 'MODSDK_WIKI_ROOT': str(root), 'MODSDK_MAINTAINER_MODE': '0', 'MODSDK_UPDATE_CHECK_HOURS': '0'}
    for flags in ([], ['--guides']):
        result = run_bounded([sys.executable, str(SKILL_ROOT / 'scripts/evaluate.py'), *flags], env=env, timeout=900)
        if result.returncode:
            raise ValueError('回归失败，未允许提交；查看 .local 下的最新验收回执。' + sanitize(result.stderr))
    for probe in state['probes']:
        after = probe_result(root, probe['spec'])
        if not after['passed'] or (probe['before']['passed'] and after['chars'] > probe['before']['chars'] + max(256, int(probe['before']['chars'] * .25))):
            raise ValueError('本轮复现未改善或输出预算退化，未允许提交：' + probe['spec']['issue_id'])
    if note_hash != digest((root / ANNOTATIONS).read_bytes()) or state['tools'] != tool_fingerprint():
        raise ValueError('验收期间文件发生变化，请复核后重新验证')
    state['receipt'] = {'notes_sha256': note_hash, 'tools': state['tools'], 'validated_at': time.time(), 'changed': changed}
    atomic_json(TRANSACTION, state)
    return {'passed': True, 'changed_entries': len(changed)}


def publish():
    root, values, state = transaction_state()
    receipt = state.get('receipt', {})
    if (receipt.get('notes_sha256') != digest((root / ANNOTATIONS).read_bytes()) or
        receipt.get('tools') != tool_fingerprint() or time.time() - receipt.get('validated_at', 0) > 86400):
        raise ValueError('缺少对应当前内容的有效回归回执；先 validate，不重录基线')
    identity = permission(values)  # 每次提交/重试推送都重新核验实际登录者。
    candidate = state.get('commit')
    expected = candidate or state['base']
    if git(['rev-parse', 'HEAD'], root) != expected:
        raise ValueError('HEAD 已变化，停止发布')
    if identity['remote_head'] not in (state['base'], candidate):
        raise ValueError('上游 main 已前进；保留本地内容，重新基于最新原文复核与验收，不强推')
    inspect_changes(root, state)
    canonical = 'https://github.com/' + identity['repository'] + '.git'
    if git(['ls-remote', '--get-url', canonical], root) != canonical:
        raise ValueError('Git 写入地址被 URL rewrite 改写；写入不得走公开下载代理')
    if candidate is None:
        git(['add', '--', ANNOTATIONS], root)
        staged = git(['diff','--cached','--name-only'],root).splitlines()
        if staged != [ANNOTATIONS] or digest(git(['show', ':' + ANNOTATIONS], root).encode()) != digest((root / ANNOTATIONS).read_text().strip().encode()):
            raise ValueError('暂存内容变化，保留现场并停止')
        git(['commit','-m','改进检索标注与开发补充'],root)
        candidate = git(['rev-parse','HEAD'],root)
        state.update({'commit': candidate, 'phase': 'committed'})
        atomic_json(TRANSACTION,state)
    if changed_paths(root) or git(['rev-parse',candidate+'^'],root) != state['base'] or git(['diff','--name-only',state['base'],candidate],root).splitlines() != [ANNOTATIONS]:
        raise ValueError('提交包含未验收内容，停止推送并保留现场')
    if identity['remote_head'] != candidate:
        result = run_bounded(['git','-c','credential.helper=','-c','credential.helper=!gh auth git-credential',
                              '-c','http.version=HTTP/1.1',*clear_http_headers(root),'push',canonical,'HEAD:refs/heads/main'], cwd=root, timeout=90,
                             env={**os.environ,'GH_HOST':'github.com','GH_PROMPT_DISABLED':'1','GIT_TERMINAL_PROMPT':'0'})
        if result.returncode:
            raise ValueError('推送未确认完成；保留已验证提交 ' + candidate + '，调整网络后再运行 publish，不重复提交。' + sanitize(result.stderr))
    state['phase'] = 'published'
    atomic_json(TRANSACTION,state)
    marker = root / '.git/modsdk-skill-checkout.json'
    if marker.exists():
        managed = load_json(marker)
        managed['commit'] = candidate
        atomic_json(marker,managed)
    with file_lock(LEDGER.with_suffix('.lock')):
        record = ledger()
        completed = {p['spec']['issue_id'] for p in state['probes']}
        for issue in record['issues']:
            if issue['id'] in completed:
                issue.update({'status':'resolved','resolved_at':time.time(),'commit':candidate})
        record['last_organized_at'] = time.time()
        save_ledger(record)
    return {'published': True, 'repository': identity['repository'], 'commit': candidate}


def close(reason):
    if not reason.strip():raise ValueError('需要保留整理结论')
    root, _, state = transaction_state()
    if changed_paths(root) or git(['rev-parse','HEAD'],root) != state['base']:
        raise ValueError('仍有修改或本地提交，保留现场，不能直接结束记录')
    state.update({'phase':'closed','conclusion':reason[:1000]})
    atomic_json(TRANSACTION,state)
    with file_lock(LEDGER.with_suffix('.lock')):
        record=ledger();record['last_organized_at']=time.time();save_ledger(record)
    return {'closed':True}


def main():
    if not enabled():
        print(json.dumps({'enabled': False}))
        return 0 if sys.argv[1:] in ([], ['status']) else 1
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('status');sub.add_parser('inspect');sub.add_parser('begin');sub.add_parser('validate');sub.add_parser('publish')
    p=sub.add_parser('checkpoint');p.add_argument('--work-complete',action='store_true')
    p=sub.add_parser('record');p.add_argument('--query',required=True);p.add_argument('--summary',required=True)
    p=sub.add_parser('probe');p.add_argument('file')
    p=sub.add_parser('close');p.add_argument('--reason',required=True)
    p=sub.add_parser('dismiss');p.add_argument('issue_id');p.add_argument('--reason',required=True)
    args=parser.parse_args()
    if args.command in ('status','inspect'):
        state=ledger();result={'enabled':True,'last_organized_at':state['last_organized_at'],'pending':[i for i in state['issues'] if i['status']=='pending'][-10:]}
        if args.command=='inspect':result.update({'recent_queries':state['observations'][-6:],'transaction':load_json(TRANSACTION)})
    elif args.command=='checkpoint':result=checkpoint(args.work_complete)
    elif args.command=='record':
        with file_lock(LEDGER.with_suffix('.lock')):
            root=resolve_root(read_config()['MODSDK_WIKI_ROOT']);state=ledger()
            result={'issue_id':add_issue(state,root,args.query,args.summary)};save_ledger(state)
    elif args.command=='dismiss':
        with file_lock(LEDGER.with_suffix('.lock')):
            if not args.reason.strip():raise ValueError('需要保留复核结论')
            state=ledger();issue=next((i for i in state['issues'] if i['id']==args.issue_id and i['status']=='pending'),None)
            if issue is None:raise ValueError('待整理问题不存在')
            issue.update({'status':'not_actionable','review_note':args.reason[:1000],'resolved_at':time.time()})
            state['last_organized_at']=time.time();save_ledger(state);result={'closed':args.issue_id}
    else:
        with file_lock(TRANSACTION.with_suffix('.lock'), timeout=1):
            result={'begin':begin,'validate':validate,'publish':publish,'probe':lambda:add_probe(args.file),'close':lambda:close(args.reason)}[args.command]()
    print(json.dumps(result,ensure_ascii=False,separators=(',',':')))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError,ValueError,KeyError,TypeError) as error:
        print(json.dumps({'error':sanitize(error)},ensure_ascii=False),file=sys.stderr)
        sys.exit(1)
