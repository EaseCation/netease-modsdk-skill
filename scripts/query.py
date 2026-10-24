#!/usr/bin/env python3
"""独立 skill 查询入口，Wiki 路径由环境变量或仓库 .env 配置。"""
import json
import os
import runpy
import sys
from config import read_config, resolve_root, validate_wiki


def main():
    values = read_config()
    root = validate_wiki(resolve_root(values['MODSDK_WIKI_ROOT']))
    script = root / 'scripts/api_knowledge.py'
    # 不允许额外 --root 覆盖已验证配置；避免查询数据源和诊断信息不一致。
    if any(arg == '--root' or arg.startswith('--root=') for arg in sys.argv[1:]):
        raise ValueError('请通过 MODSDK_WIKI_ROOT 或本技能 .env 选择 Wiki，不使用 --root')
    sys.argv = [str(script), '--root', str(root)] + sys.argv[1:]
    if os.environ.get('MODSDK_MAINTAINER_MODE') == '1':
        from maintenance import capture_query
        capture_query(sys.argv[1:], root, lambda: runpy.run_path(str(script), run_name='__main__'))
    else:
        runpy.run_path(str(script), run_name='__main__')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, SyntaxError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
