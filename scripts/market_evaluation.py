"""执行冻结的市场需求题库；只调用真实查询 CLI，不模拟游戏引擎。"""
import json
import os
import subprocess
import sys
from pathlib import Path
from config import SKILL_ROOT, read_config, resolve_root


def evaluate_market(variant='all'):
    bank=json.loads((SKILL_ROOT/'evals/market.json').read_text())
    root=resolve_root(read_config()['MODSDK_WIKI_ROOT'])
    env={**os.environ,'MODSDK_MAINTAINER_MODE':'0'}
    subprocess.run([sys.executable,str(SKILL_ROOT/'scripts/query.py'),'build'],env=env,capture_output=True,text=True,check=True)
    index=json.loads((root/'.api-index/index.json').read_text());bykey={r['key']:r for r in index['records']}
    variants={'original':0,'development':1,'holdout':2};selected=variants if variant=='all' else {variant:variants[variant]}
    rows=[];totals={}
    for name,number in selected.items():
        totals[name]=0
        for case in bank['cases']:
            intents=[];groups={}
            for goal in case['intents']:
                leaves=goal.get('atomic',[])
                if leaves:
                    for n,leaf in enumerate(leaves):
                        entry={k:goal[k] for k in ('kind','side','operation')}
                        entry.update({'id':goal['id']+'.'+str(n),'query':leaf['queries'][number]})
                        entry.update(leaf.get('constraints',{}));intents.append(entry)
                    groups[goal['id']]=[goal['id']+'.'+str(n) for n in range(len(leaves))]
                else:
                    entry={k:goal[k] for k in ('id','kind','side','operation','phase') if k in goal}
                    entry.update(goal.get('constraints',{}));entry['query']=goal['queries'][number]
                    intents.append(entry);groups[goal['id']]=[goal['id']]
            command=[sys.executable,str(SKILL_ROOT/'scripts/query.py'),'--max-chars',str(case['max_chars']),'resolve','--plan-file','-','--limit',str(case['limit'])]
            process=subprocess.run(command,input=json.dumps({'intents':intents},ensure_ascii=False),text=True,capture_output=True,env=env,timeout=120)
            output=json.loads(process.stdout) if not process.returncode else {};errors=[]
            if process.returncode:errors.append(process.stderr.strip())
            actual={g['id']:g for g in output.get('intents',[])}
            workflows={w['intent']:w for w in output.get('workflows',[])}
            reviewed=[]
            for goal in case['intents']:
                ids={bykey[key]['id'] for gid in groups[goal['id']] for key in actual.get(gid,{}).get('candidates',[])}
                missing=[required for required in goal['required'] if not ids&set(required)]
                if missing:errors.append(goal['id']+':遗漏能力')
                if ids&set(goal['forbidden']):errors.append(goal['id']+':推荐禁止误用接口')
                if goal.get('recipe') and not any(workflows.get(gid,{}).get('id')==goal['recipe'] for gid in groups[goal['id']]):errors.append(goal['id']+':遗漏组合流程')
                coverages=[actual.get(gid,{}).get('state','matched') for gid in groups[goal['id']]]
                if goal['expected_state']=='matched' and any(c!='matched' for c in coverages):errors.append(goal['id']+':能力尚未完整核验')
                if goal['expected_state']!='matched' and any(c=='matched' for c in coverages):errors.append(goal['id']+':未核验能力冒充完整覆盖')
                reviewed.append({'id':goal['id'],'ids':sorted(ids),'coverage':coverages})
            chars=len(process.stdout.rstrip('\n'));totals[name]+=chars
            if chars>case['max_chars']:errors.append('超过单组预算')
            row={'id':case['id'],'variant':name,'chars':chars,'calls':1,'errors':errors,'intents':reviewed,'output':output};rows.append(row)
            print(('FAIL' if errors else 'PASS'),name,case['id'],chars,'; '.join(errors),flush=True)
    errors=[]
    for name,count in totals.items():
        if count>bank['total_chars_budget']:errors.append(name+':超过完整需求总预算')
    # 验证实际编译合同，而不是只验命中了同名 API。
    server=next(r for r in index['records'] if r['name']=='PlayerAttackEntityEvent' and r['side']=='server')
    client=next(r for r in index['records'] if r['name']=='PlayerAttackEntityEvent' and r['side']=='client')
    params={p['name']:p['description'] for p in server['parameters']}
    if not {'damage','isValid','cancel'}<=params.keys() or '允许' not in params.get('damage',''):errors.append('服务端攻击合同错误')
    if any(p['name']=='isValid' for p in client['parameters']) or '修改无效' not in next(p['description'] for p in client['parameters'] if p['name']=='damage'):errors.append('客户端攻击合同错误')
    # 同一个真实 CLI：默认精简输出必须保留合同，诊断字段只能显式开启。
    checks=[]
    outputs=[]
    for flags in ([],['--verbose']):
        command=[sys.executable,str(SKILL_ROOT/'scripts/query.py'),*flags,'detail','PlayerAttackEntityEvent','--side','server','--examples','0']
        proc=subprocess.run(command,env=env,capture_output=True,text=True,check=True)
        outputs.append(json.loads(proc.stdout)['results'][0])
    for field in ('parameters','returns','class_path'):
        if (outputs[0].get(field) or '')!=(outputs[1].get(field) or ''):errors.append('精简输出丢失合同字段：'+field)
    if 'source_sha256' in outputs[0] or 'source_sha256' not in outputs[1] or not outputs[0].get('source'):errors.append('诊断元数据未正确按需返回')
    checks.append('compact_output_preserves_contract')
    # 通过独立真实 Wiki 数据副本验证别名扩充，不写入工作区或生产标注。
    import tempfile, shutil
    with tempfile.TemporaryDirectory(prefix='modsdk-alias-check-') as directory:
        isolated=Path(directory);(isolated/'scripts').mkdir();(isolated/'knowledge').mkdir()
        shutil.copy2(root/'scripts/api_knowledge.py',isolated/'scripts/api_knowledge.py')
        (isolated/'docs').mkdir()
        for source in (root/'docs').rglob('*.md'):
            if '.vitepress' in source.parts:continue
            destination=isolated/'docs'/source.relative_to(root/'docs')
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,destination)
        for source in (root/'knowledge').glob('*.json'):shutil.copy2(source,isolated/'knowledge'/source.name)
        results=[]
        for expand in (False,True):
            if expand:
                file=isolated/'knowledge/annotations.json';notes=json.loads(file.read_text())
                target=next(a for a in notes['entries'] if a['id'].endswith('ItemCompServer.SetInvItemNum') and '@' not in a['id'])
                target['aliases']+=['无关说明甲','无关说明乙','无关说明丙','无关说明丁','无关说明戊','无关说明己']
                file.write_text(json.dumps(notes,ensure_ascii=False))
            proc=subprocess.run([sys.executable,str(SKILL_ROOT/'scripts/query.py'),'search','修改玩家背包指定槽位的物品数量','--side','server','--operation','set','--limit','1'],env={**env,'MODSDK_WIKI_ROOT':str(isolated)},capture_output=True,text=True)
            if proc.returncode:raise ValueError('别名扩充验收失败：'+proc.stderr)
            results.append(json.loads(proc.stdout)['results'][0]['name'])
        if results!=['SetInvItemNum','SetInvItemNum']:errors.append('无关别名扩充导致数量接口退化')
    checks.append('alias_extension_preserves_capability_rank')
    role_plan={'side':'server','intents':[{'id':'count','query':'修改背包槽位数量','kind':'api','operation':'set','object':['inventory'],'property':['count']}]}
    proc=subprocess.run([sys.executable,str(SKILL_ROOT/'scripts/query.py'),'resolve','--plan-file','-','--limit','1'],input=json.dumps(role_plan,ensure_ascii=False),env=env,capture_output=True,text=True,check=True)
    role_output=json.loads(proc.stdout)
    if not role_output.get('results') or role_output['results'][0]['name']!='SetInvItemNum' or role_output['intents'][0].get('state'):errors.append('显式对象/属性匹配失败')
    checks.append('explicit_roles_use_verified_facts')
    report={'kind':'market-capability-regression','bank_version':bank['schema_version'],'corpus_sha256':index['corpus_sha256'],'cases':len(rows),'passed':sum(not r['errors'] for r in rows),'chars':totals,'errors':errors,'checks':checks,'rows':rows}
    out=SKILL_ROOT/'.local';out.mkdir(exist_ok=True);(out/'market-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('cases','passed','chars','errors')},ensure_ascii=False))
    return 0 if report['passed']==report['cases'] and not errors else 1
