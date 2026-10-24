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


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--split',choices=['regression','holdout','protocol','all'],default='all')
    parser.add_argument('--record-baseline',action='store_true',help='全部通过后，显式记录新的成本基线；不会改题目或期望 API')
    args=parser.parse_args()
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
        if not case.get('expect_error') and set(output.get('unresolved_intents',[])) != expected_unresolved:errors.append('子目标未完成状态与预期不符')
        if case.get('expect_no_capability_match') and ids:errors.append('支持边界被当作可用能力')
        if case.get('expect_limitation') and not output.get('limitations'):errors.append('未提供限制证据')
        if case['plan'].get('read_only') and any(r.get('operation') not in ('read','observe') for r in output.get('results',[])):errors.append('只读约束泄漏')
        for result in output.get('results',[]):
            record=by_key[result['id']]
            if record['scope']!='modsdk':errors.append('默认范围泄漏到 Preset')
            if record['side'] not in (case['side'],'common'):errors.append('端侧不匹配')
            if result.get('match_type')!='capability_text':errors.append('限制证据混入能力候选')
        related_ids=[by_key[r['id']]['id'] for r in output.get('related',[])]
        if set(case.get('related_required',[]))-set(related_ids):errors.append('遗漏关联阶段事件')
        for result in output.get('related',[]):
            record=by_key[result['id']]
            if record['kind']!='event' or result.get('match_type')!='related_phase':errors.append('关联阶段类型不正确')
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
