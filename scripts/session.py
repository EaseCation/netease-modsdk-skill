#!/usr/bin/env python3
"""会话开始时检查本地来源、上游版本及按需上下文。"""
import json
import os
import sys
from config import SKILL_ROOT, read_config, resolve_root, validate_wiki
from upstream import check_updates


def main():
    values = read_config()
    root = resolve_root(values['MODSDK_WIKI_ROOT'])
    if not root.exists():
        result = {'wiki_ready': False, 'next_action': 'python3 scripts/setup.py'}
    else:
        validate_wiki(root)
        result = {'wiki_ready': True, 'upstream': check_updates(root, values)}
    if os.environ.get('MODSDK_MAINTAINER_MODE') == '1':
        result['context_file'] = str(SKILL_ROOT / '.maintenance/guide.md')
    print(json.dumps(result, ensure_ascii=False, separators=(',', ':')))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, SyntaxError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
