#!/usr/bin/env python3
"""实际调用查询 CLI 运行稳定题库；不启动游戏，不修改 Wiki 或期望答案。"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
from config import SKILL_ROOT, read_config, resolve_root, validate_wiki


def evaluate_guides():
    """核对真实原文、引用闭合与阅读路径预算；内容决策仍需复核。"""
    import re
    from concurrent.futures import ThreadPoolExecutor
    from read_doc import catalog, load_source
    bank=json.loads((SKILL_ROOT/'evals/guidance.json').read_text())
    entry=(SKILL_ROOT/'SKILL.md').read_text();errors=[]
    if len(entry)>bank['max_entry_chars']:errors.append('技能入口超过字符预算')
    refs=list((SKILL_ROOT/'references').glob('*.md'))
    sources=catalog()
    for path in [SKILL_ROOT/'SKILL.md',*refs]:
        content=path.read_text()
        if path in refs and len(content)>bank['max_reference_chars']:errors.append('参考页超过预算：'+path.name)
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',content):
            if '://' not in target and not target.startswith('#') and not (path.parent/target.split('#')[0]).is_file():errors.append('参考链接失效：'+target)
        for id in re.findall(r'`((?:cn|be|ms|mirror)-[a-z-]+)`',content):
            if id not in sources:errors.append('来源未登记：'+id)
    def inspect_source(id):
        try:
            metadata,_,_,_=load_source(id)
            return id if metadata['source_changed'] else None
        except (OSError,ValueError) as error:return id+': '+str(error)
    with ThreadPoolExecutor(max_workers=6) as pool:
        invalid=[r for r in pool.map(inspect_source,sources) if r]
    errors += ['来源需复核：'+r for r in invalid]
    rows=[]
    for case in bank['cases']:
        initial=len(entry)+sum(len((SKILL_ROOT/p).read_text()) for p in case['references'])
        proc=subprocess.run([sys.executable,str(SKILL_ROOT/'scripts/read_doc.py'),*case['source_request']],capture_output=True,text=True)
        output=json.loads(proc.stdout) if proc.returncode==0 else {}
        expanded=initial+len(proc.stdout.rstrip('\n'))
        row_errors=[]
        if proc.returncode:row_errors.append(proc.stderr.strip())
        if not output.get('text'):row_errors.append('未返回指定章节')
        if initial>case['max_initial_chars'] or expanded>case['max_expanded_chars']:row_errors.append('阅读路径超过字符预算')
        rows.append({'id':case['id'],'initial_chars':initial,'expanded_chars':expanded,'paged':output.get('next_offset') is not None,'errors':row_errors})
        print(('FAIL' if row_errors else 'PASS'),case['id'],initial,expanded,flush=True)
    outline=subprocess.run([sys.executable,str(SKILL_ROOT/'scripts/read_doc.py'),'cn-ui'],capture_output=True,text=True,check=True)
    outline_data=json.loads(outline.stdout)
    if outline_data.get('mode')!='outline' or 'text' in outline_data:errors.append('默认读取泄漏整篇正文')
    report={'kind':'guide-source-and-budget-check','sources':len(sources),'cases':len(rows),'passed':sum(not r['errors'] for r in rows),'errors':errors,'rows':rows,'scope':'固定阅读路径；不评估 Agent 自主路由或游戏功能'}
    out=SKILL_ROOT/'.local';out.mkdir(exist_ok=True)
    (out/'guidance-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('sources','cases','passed','errors')},ensure_ascii=False))
    return 0 if not errors and report['passed']==report['cases'] else 1


def evaluate_operations():
    """隔离目录中运行真实 CLI，检查可见性、提醒、超时及回执门槛。"""
    import shutil
    import socket
    import tempfile
    from network import run_bounded, NetworkError
    root=validate_wiki(resolve_root(read_config()['MODSDK_WIKI_ROOT']))
    checks=[]
    with tempfile.TemporaryDirectory(prefix='modsdk-operations-') as temp:
        clone=Path(temp)/'skill'
        shutil.copytree(SKILL_ROOT,clone,ignore=shutil.ignore_patterns('.git','.data','.local','.env','__pycache__'))
        env={**os.environ,'MODSDK_WIKI_ROOT':str(root),'MODSDK_MAINTAINER_MODE':'0','MODSDK_UPDATE_CHECK_HOURS':'0'}
        def run(script,*args,settings=None,code=0):
            proc=subprocess.run([sys.executable,str(clone/'scripts'/script),*args],cwd=clone,env={**env,**(settings or {})},capture_output=True,text=True,timeout=150)
            if proc.returncode!=code:raise ValueError(script+' 返回值异常：'+proc.stderr[:300])
            return json.loads(proc.stdout or proc.stderr),proc.stdout
        value,_=run('session.py')
        assert 'context_file' not in value
        value,_=run('maintenance.py','publish',code=1)
        assert value=={'enabled':False} and not (clone/'.local/maintenance').exists()
        checks.append('disabled_mode_hidden_and_write_denied')
        query=['resolve','给指定玩家发送系统聊天消息','--side','server']
        _,ordinary=run('query.py',*query)
        assert not (clone/'.local/maintenance').exists()
        active={'MODSDK_MAINTAINER_MODE':'1'}
        value,_=run('session.py',settings=active)
        assert Path(value['context_file']).is_file()
        _,observed=run('query.py',*query,settings=active)
        assert ordinary==observed
        log=clone/'.local/maintenance/ledger.json';state=json.loads(log.read_text())
        assert len(state['observations'])==1 and not state['issues']
        checks.append('enabled_mode_preserves_query_stdout')
        value,_=run('maintenance.py','record','--query','检索复盘集成核验','--summary','隔离目录记录与提醒检查',settings=active)
        issue=value['issue_id'];state=json.loads(log.read_text());state['started_at']=time.time()-172800
        log.write_text(json.dumps(state,ensure_ascii=False))
        value,_=run('maintenance.py','checkpoint',settings=active);assert not value['remind']
        value,_=run('maintenance.py','checkpoint','--work-complete',settings=active);assert value['remind']
        value,_=run('maintenance.py','checkpoint','--work-complete',settings=active);assert not value['remind']
        run('maintenance.py','dismiss',issue,'--reason','集成核验已结束，无需修改公共标注',settings=active)
        state=json.loads(log.read_text());assert state['last_organized_at'] and state['last_reminded_at'] and state['issues'][0]['status']=='not_actionable'
        run('maintenance.py','record','--query','检索复盘集成核验','--summary','检查重复问题重新打开',settings=active)
        state=json.loads(log.read_text());assert len(state['issues'])==1 and state['issues'][0]['occurrences']==2 and state['issues'][0]['status']=='pending'
        checks.append('reminder_requires_time_and_task_boundary_and_deduplicates')
        # 只验证 ls-remote 的引用检查；对象库可为未补齐图片的稀疏副本。
        remote=Path(temp)/'upstream.git'
        subprocess.run(['git','init','--bare',str(remote)],check=True,capture_output=True)
        objects=subprocess.check_output(['git','rev-parse','--git-path','objects'],cwd=root,text=True).strip()
        (remote/'objects/info/alternates').write_text(str((root/objects).resolve())+'\n')
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
        subprocess.run(['git','--git-dir',str(remote),'update-ref','refs/heads/main',head],check=True)
        settings={'MODSDK_WIKI_REPOSITORY':str(remote),'MODSDK_WIKI_REF':'main','MODSDK_UPDATE_CHECK_HOURS':'24'}
        value,_=run('session.py',settings=settings);assert value['upstream']['checked_now'] and value['upstream']['status']=='up_to_date'
        value,_=run('session.py',settings=settings);assert not value['upstream']['checked_now']
        checks.append('upstream_check_obeys_interval')
        with socket.socket() as reserved:
            reserved.bind(('127.0.0.1',0))
            settings={'MODSDK_WIKI_REPOSITORY':'http://127.0.0.1:'+str(reserved.getsockname()[1])+'/missing.git','MODSDK_NETWORK_TIMEOUT':'1','MODSDK_GITHUB_PROXY_PREFIX':'','NO_PROXY':'*','no_proxy':'*'}
            value,_=run('setup.py','--check-updates',settings=settings,code=1);assert value['status']=='unavailable'
            value,_=run('setup.py','--check-updates',settings=settings,code=1);assert '冷却' in value['message']
            # 远程检查失败不阻断已有本地语料。
            _,cached=run('query.py',*query,settings=settings);assert cached==ordinary
        checks.append('network_failure_cools_down_and_local_query_still_works')
        started=time.monotonic()
        try:
            run_bounded([sys.executable,'-c','import time;time.sleep(5)'],timeout=.2)
            raise AssertionError('未执行总超时')
        except NetworkError:assert time.monotonic()-started<3
        checks.append('subprocess_total_timeout')
        # 回执缺失时在接触 GitHub 写入前即拒绝。
        tx=clone/'.local/maintenance/transaction.json'
        tx.write_text(json.dumps({'root':str(root),'repository':'EaseCation/netease-modsdk-wiki','base':head,'phase':'editing','probes':[]}))
        value,_=run('maintenance.py','publish',settings={**active,'MODSDK_WIKI_REF':'validation-branch'},code=1)
        assert '只面向配置的 main' in value['error']
        checks.append('maintenance_rejects_non_main')
        value,_=run('maintenance.py','publish',settings={**active,'MODSDK_WIKI_REF':'main'},code=1);assert '回归回执' in value['error']
        checks.append('publish_requires_current_validation_receipt')
    report={'passed':len(checks),'checks':checks,'scope':'真实 CLI/文件/Git/超时检查；不执行生产推送或游戏测试'}
    out=SKILL_ROOT/'.local';out.mkdir(exist_ok=True);(out/'operations-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False));return 0


def evaluate_requests():
    """固定真实自然语言与规范计划；检查结果、状态、流程和运行协议。"""
    bank_path=SKILL_ROOT/'evals/request-contract.json'
    bank=json.loads(bank_path.read_text());rows=[]
    env={**os.environ,'MODSDK_MAINTAINER_MODE':'0'}
    for case in bank['cases']:
        cmd=[sys.executable,str(SKILL_ROOT/'scripts/query.py'),'resolve','--plan-file','-']
        proc=subprocess.run(cmd,input=json.dumps({'intents':[case['intent']]},ensure_ascii=False),capture_output=True,text=True,env=env,timeout=120)
        output=json.loads(proc.stdout) if proc.returncode==0 else {};errors=[]
        if proc.returncode:errors.append(proc.stderr.strip())
        group=next(iter(output.get('intents',[])),{});state=group.get('state','matched')
        names={r['name'] for r in output.get('results',[])}
        if case['required'] and not names & set(case['required']):errors.append('遗漏必需能力')
        if names & set(case.get('forbidden',[])):errors.append('错误替代')
        if state not in case['states']:errors.append('状态不符：'+state)
        if not set(case.get('missing',[]))<=set(group.get('missing',[])):errors.append('丢失必需条件')
        if case['intent'].get('requirements')!=group.get('unverified'):errors.append('未建模条件未原样保留')
        if case.get('recipe') not in (None,*[w['id'] for w in output.get('workflows',[])]):errors.append('遗漏流程')
        if not set(case.get('review',[]))<=set(x['name'] for x in output.get('review',[])):errors.append('丢失待核验入口')
        if not set(case.get('missing_roles',[]))<=set(group.get('missing_roles',[])):errors.append('丢失合同维度')
        chars=len(proc.stdout.rstrip('\n'))
        if chars>bank['max_case_chars']:errors.append('超过输出预算')
        rows.append({'id':case['id'],'chars':chars,'state':state,'errors':errors,'output':output})
        print(('FAIL' if errors else 'PASS'),'request',case['id'],chars,'; '.join(errors),flush=True)
    schema_proc=subprocess.run([sys.executable,str(SKILL_ROOT/'scripts/query.py'),'schema'],capture_output=True,text=True,env=env,check=True)
    schema=json.loads(schema_proc.stdout);errors=[]
    if schema.get('query_protocol')!=4 or not {'mode','hints','requirements','concepts','action','subject','object','property','qualifiers'}<=set(schema['intent_fields']):errors.append('运行时协议发现不完整')
    from config import validate_contract
    try:validate_contract('SCHEMA_VERSION = 3', '{"schema_version":3,"entries":[]}')
    except ValueError:pass
    else:errors.append('旧请求引擎未拒绝')
    root=resolve_root(read_config()['MODSDK_WIKI_ROOT']);index=json.loads((root/'.api-index/index.json').read_text())
    report={'query_protocol':schema['query_protocol'],'corpus_sha256':index['corpus_sha256'],'bank_sha256':hashlib.sha256(bank_path.read_bytes()).hexdigest(),'cases':len(rows),'passed':sum(not r['errors'] for r in rows),'chars':sum(r['chars'] for r in rows),'errors':errors,'rows':rows,'scope':'真实查询 CLI；非独立模型生成计划评测、非游戏实机'}
    (SKILL_ROOT/'.local').mkdir(exist_ok=True)
    (SKILL_ROOT/'.local/request-contract-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('cases','passed','chars','errors')},ensure_ascii=False))
    return 0 if not errors and report['passed']==report['cases'] else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--split',choices=['regression','holdout','protocol','all'],default='all')
    parser.add_argument('--requests',action='store_true',help='检查自然语言与规范请求合同')
    parser.add_argument('--market-expanded', action='store_true', help='执行新增独立市场产品回归')
    parser.add_argument('--market', action='store_true', help='验证冻结的市场能力需求')
    parser.add_argument('--market-variant', choices=['all','original','development','holdout'], default='all')
    parser.add_argument('--operations',action='store_true',help='隔离核验安装、网络与会话机制')
    parser.add_argument('--guides',action='store_true',help='检查教程来源、引用与固定阅读路径的字符预算')
    parser.add_argument('--record-baseline',action='store_true',help='全部通过后，显式记录新的成本基线；不会改题目或期望 API')
    args=parser.parse_args()
    if args.requests:
        if args.market or args.market_expanded or args.guides or args.operations or args.record_baseline or args.split!='all':raise ValueError('--requests 单独运行')
        return evaluate_requests()
    if args.market_expanded:
        if args.market or args.guides or args.operations or args.record_baseline or args.split!='all' or args.market_variant!='all':raise ValueError('--market-expanded 单独运行')
        from market_evaluation import evaluate_expansion
        return evaluate_expansion()
    if args.market:
        if args.guides or args.operations or args.record_baseline or args.split!='all': raise ValueError('--market 单独运行')
        from market_evaluation import evaluate_market, evaluate_expansion
        result = evaluate_market(args.market_variant)
        if result or args.market_variant!='all': return result
        return evaluate_expansion()
    if args.operations:
        if args.guides or args.record_baseline or args.split!='all':raise ValueError('--operations 单独运行')
        return evaluate_operations()
    if args.guides:
        if args.record_baseline or args.split!='all':raise ValueError('--guides 不与 API 题库筛选或基线记录混用')
        return evaluate_guides()
    if args.record_baseline and args.split!='all':raise ValueError('记录基线必须运行完整题库')
    bank_path=SKILL_ROOT/'evals/cases.json';bank=json.loads(bank_path.read_text())
    root=validate_wiki(resolve_root(read_config()['MODSDK_WIKI_ROOT']))
    # build/load 由实际 CLI 完成，评估器只读取生成后的索引以映射稳定 ID。
    subprocess.run([sys.executable,str(SKILL_ROOT/'scripts/query.py'),'build'],env={**os.environ,'MODSDK_WIKI_ROOT':str(root)},check=True,capture_output=True,text=True)
    index=json.loads((root/'.api-index/index.json').read_text());by_key={r['key']:r for r in index['records']};known_ids={r['id'] for r in index['records']}
    baseline_path=SKILL_ROOT/'evals/baseline.json';baseline=json.loads(baseline_path.read_text()) if baseline_path.exists() else {}
    expected_baseline=baseline.get('cases',{})
    bank_hash=hashlib.sha256(bank_path.read_bytes()).hexdigest()
    if baseline and baseline.get('bank_sha256')!=bank_hash and not args.record_baseline:
        raise ValueError('题库已改变，请先人工复核题目与期望差异，再显式记录完整基线')
    selected=[c for c in bank['cases'] if args.split=='all' or c['split']==args.split]
    rows=[]
    for case in selected:
        reference={i for g in case['required'] for i in g['ids']} | set(case.get('hard_negative_ids',[])) | set(case.get('related_required',[]))
        errors=[]
        if reference-known_ids:errors.append('原文接口身份已变化，需人工复核参考答案')
        arguments=['--max-chars',str(case['max_chars']),'resolve','--plan-file','-','--limit',str(case['limit'])]
        started=time.monotonic()
        proc=subprocess.run([sys.executable,str(SKILL_ROOT/'scripts/query.py'),*arguments],input=json.dumps(case['plan'],ensure_ascii=False),env={**os.environ,'MODSDK_WIKI_ROOT':str(root),'PYTHONHASHSEED':'0'},capture_output=True,text=True)
        try:output=json.loads(proc.stderr if proc.returncode else proc.stdout)
        except json.JSONDecodeError:output={};errors.append('查询未返回合法 JSON')
        if case.get('expect_error'):
            if not proc.returncode or not isinstance(output.get('error'),str):errors.append('无效计划未被明确拒绝')
            elif case['expected_error_contains'] not in output['error']:errors.append('错误原因与预期不符')
        elif proc.returncode:errors.append('查询失败：'+proc.stderr.strip())
        ids=[by_key[r['id']]['id'] for r in output.get('results',[])]
        hit_groups=[g['label'] for g in case['required'] if set(g['ids'])&set(ids)]
        missing=[g['label'] for g in case['required'] if not set(g['ids'])&set(ids)]
        if missing:errors.append('遗漏能力：'+','.join(missing))
        forbidden=sorted(set(ids)&set(case.get('hard_negative_ids',[])))
        if forbidden:errors.append('推荐了禁止误用的接口')
        expected_unresolved = {i['id'] for i in case['plan']['intents']} if case.get('expect_no_capability_match') else set()
        if not case.get('expect_error'):
            # v2 candidates 只表示分配了候选；v3 未解决项还包括尚未核验的能力事实。
            # 原有必需 ID、负例、端侧和预算断言保持；新增状态与分组一致性校验。
            groups=output.get('intents',[])
            actual_unresolved={g['id'] for g in groups if g.get('state','matched')!='matched'}
            if 'unresolved_intents' in output and set(output['unresolved_intents']) != actual_unresolved:errors.append('子目标未完成状态与分组不一致')
            if case.get('expect_no_capability_match') and actual_unresolved != expected_unresolved:errors.append('能力边界未保留未解决状态')
            if any((g.get('missing') or g.get('missing_roles')) and not g.get('state') for g in groups):errors.append('未知能力冒充完整覆盖')
        if case.get('expect_no_capability_match') and ids:errors.append('支持边界被当作可用能力')
        if case.get('expect_limitation') and not output.get('limitations'):errors.append('未提供限制证据')
        if case['plan'].get('read_only') and any(by_key[r['id']].get('annotation',{}).get('facts',{}).get('operation',by_key[r['id']].get('annotation',{}).get('inferred',{}).get('operation')) not in ('read','observe') for r in output.get('results',[])):errors.append('只读约束泄漏')
        for result in output.get('results',[]):
            record=by_key[result['id']]
            if record['scope']!='modsdk':errors.append('默认范围泄漏到 Preset')
            if record['side'] not in (case['side'],'common'):errors.append('端侧不匹配')
            if result['id'] in {x['id'] for x in output.get('limitations',[])}:errors.append('限制证据混入能力候选')
        related_ids=[by_key[r['id']]['id'] for r in output.get('related',[])]
        if set(case.get('related_required',[]))-set(related_ids):errors.append('遗漏关联阶段事件')
        for result in output.get('related',[]):
            record=by_key[result['id']]
            if record['kind']!='event' or not result.get('related_to'):errors.append('关联阶段类型不正确')
            if record['scope']!='modsdk' or record['side'] not in (case['side'],'common'):errors.append('关联阶段范围或端侧泄漏')
        chars=len((proc.stderr if proc.returncode else proc.stdout).rstrip('\n'));calls=1
        if chars>case['max_chars'] or len(ids)>case['limit']:errors.append('超出硬预算')
        old=expected_baseline.get(case['id'])
        if old and not args.record_baseline:
            if chars>old['chars']+max(128,math.ceil(old['chars']*.15)):errors.append('输出较已接受基线增加超过容差')
        row={'id':case['id'],'title':case['title'],'split':case['split'],'required':len(case['required']),'hits':len(hit_groups),
             'missing':missing,'forbidden':forbidden,'chars':chars,'calls':calls,'elapsed_ms':round((time.monotonic()-started)*1000),
             'errors':errors,'result_ids':ids,'related_ids':related_ids,'output':output}
        rows.append(row)
        print(('PASS' if not errors else 'FAIL'),case['id'],f"{len(hit_groups)}/{len(case['required'])}",chars,'; '.join(errors),flush=True)
    report={'bank_sha256':hashlib.sha256(bank_path.read_bytes()).hexdigest(),'runtime_schema_version':index['schema_version'],
            'corpus_sha256':index['corpus_sha256'],'wiki_root':str(root),'cases':len(rows),'passed':sum(not r['errors'] for r in rows),
            'hits':sum(r['hits'] for r in rows),'required':sum(r['required'] for r in rows),'chars':sum(r['chars'] for r in rows),'calls':sum(r['calls'] for r in rows),'rows':rows}
    out=SKILL_ROOT/'.local';out.mkdir(exist_ok=True);(out/'regression-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    if args.record_baseline and report['passed']==report['cases']:
        value={'bank_sha256':report['bank_sha256'],'runtime_schema_version':index['schema_version'],'corpus_sha256':index['corpus_sha256'],
               'cases':{r['id']:{'chars':r['chars'],'hits':r['hits'],'calls':r['calls']} for r in rows}}
        baseline_path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');print('已记录完整通过的基线；题目和参考答案未修改。')
    print(json.dumps({k:report[k] for k in ['cases','passed','hits','required','chars','calls']},ensure_ascii=False))
    return 0 if report['passed']==report['cases'] else 1

if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,ValueError,subprocess.CalledProcessError) as e:
        print(str(e),file=sys.stderr);sys.exit(1)
