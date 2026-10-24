#!/usr/bin/env python3
"""按来源 ID 读取教程目录、章节或局部行；不加载 API 索引，不执行原文。"""
import argparse
import hashlib
import html
import json
from pathlib import Path, PurePosixPath
import re
import sys
import urllib.request
from config import SKILL_ROOT, read_config, resolve_root, validate_wiki


def source_digest(data):
    return hashlib.sha256(data.decode('utf-8-sig').replace('\r\n', '\n').encode('utf8')).hexdigest()


def catalog():
    return json.loads((SKILL_ROOT / 'references/sources.json').read_text(encoding='utf8'))['sources']


def headings(lines):
    """忽略 frontmatter 和 fenced code；保存实际行号及层级路径。"""
    result, stack = [], []
    fence = None
    frontmatter = bool(lines and lines[0].strip('\ufeff \r\n') == '---')
    for number, line in enumerate(lines, 1):
        if frontmatter:
            if number > 1 and line.strip() == '---':
                frontmatter = False
            continue
        marker = re.match(r'^\s{0,3}(`{3,}|~{3,})', line)
        if marker:
            value = marker.group(1)
            if fence is None:
                fence = value
            elif value[0] == fence[0] and len(value) >= len(fence):
                fence = None
            continue
        if fence:
            continue
        match = re.match(r'^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$', line)
        if not match:
            continue
        level = len(match[1])
        title = html.unescape(re.sub(r'<[^>]*>', '', match[2]))
        title = re.sub(r'\\([_\[\]()*#])', r'\1', title).strip()
        while stack and stack[-1]['level'] >= level:
            stack.pop()
        item = {'id': 'h' + str(number), 'title': title, 'level': level,
                'line': number, 'path': ' > '.join([x['title'] for x in stack] + [title])}
        result.append(item)
        stack.append(item)
    for i, item in enumerate(result):
        item['end_line'] = next((x['line'] - 1 for x in result[i + 1:] if x['level'] <= item['level']), len(lines))
    return result


def select_heading(items, query):
    found = [h for h in items if query in (h['id'], h['path'], h['title'])]
    if len(found) != 1:
        raise ValueError('章节不存在或重名；先读取目录并使用 h行号 标识。' +
                         ('候选：' + ', '.join(h['id'] for h in found) if found else ''))
    return found[0]


def load_source(source_id):
    source = catalog().get(source_id)
    if not source:
        raise ValueError('未知来源 ID，请使用模块页列出的来源。')
    relative = PurePosixPath(source['path'])
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('来源路径越界')
    metadata = {'id': source_id, 'evidence': source['evidence']}
    if source['provider'] == 'wiki':
        root = validate_wiki(resolve_root(read_config()['MODSDK_WIKI_ROOT']))
        path = (root / 'docs' / relative).resolve()
        if (root / 'docs').resolve() not in path.parents:
            raise ValueError('来源路径越界')
        if not path.is_file():
            raise ValueError('缺少教程：' + str(path) + '；受管精简副本请运行 setup.py --update')
        data = path.read_bytes()
        metadata['path'] = str(path)
    elif source['provider'] == 'github':
        repo, revision = source['repository'], source['revision']
        if repo not in ('Bedrock-OSS/bedrock-wiki', 'MicrosoftDocs/minecraft-creator') or not re.fullmatch('[a-f0-9]{40}', revision):
            raise ValueError('外部来源必须是登记的仓库及完整提交')
        url = 'https://raw.githubusercontent.com/' + repo + '/' + revision + '/' + str(relative)
        path = SKILL_ROOT / '.data/guide-sources' / repo / revision / relative
        metadata.update({'path': str(path), 'url': url, 'revision': revision})
        if path.is_file():
            data = path.read_bytes()
        else:
            request = urllib.request.Request(url, headers={'User-Agent': 'netease-modsdk-skill', 'Accept-Encoding': 'identity'})
            with urllib.request.urlopen(request, timeout=30) as response:
                data = response.read(2_000_001)
            if len(data) > 2_000_000:
                raise ValueError('来源文件超过 2 MB，请缩小登记范围')
            if source_digest(data) != source['sha256']:
                raise ValueError('固定原文摘要不符，未写入缓存：' + source_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    else:
        raise ValueError('未知来源类型')
    digest = source_digest(data)
    changed = digest != source['sha256']
    metadata.update({'sha256': digest, 'source_changed': changed})
    if changed and source['provider'] == 'github':
        raise ValueError('固定原文缓存摘要不符，请核对缓存文件：' + str(path))
    if changed and (source.get('line_scope') or source.get('section_scope')):
        raise ValueError('定界节选的原文已改变，需复核范围后更新登记：' + source_id)
    lines = data.decode('utf-8-sig').splitlines(keepends=True)
    items = headings(lines)
    ranges = source.get('line_scope', [[1, len(lines)]])
    if source.get('section_scope'):
        chosen = select_heading(items, source['section_scope'])
        ranges = [[chosen['line'], chosen['end_line']]]
    visible = {n for begin, end in ranges for n in range(begin, end + 1)}
    items = [h for h in items if h['line'] in visible]
    metadata['available_line_ranges'] = ranges
    if changed:
        metadata['notice'] = '原文与编写指引时不同，请复核当前模块结论。'
    return metadata, lines, items, visible


def response(args):
    metadata, lines, items, visible = load_source(args.source)
    result = {'source': metadata}
    if args.find is not None:
        if not args.find.strip():
            raise ValueError('查找词不能为空')
        matches = [{'line': n, 'text': line.strip()[:180]} for n, line in enumerate(lines, 1)
                   if n in visible and args.find.casefold() in line.casefold()]
        result.update({'mode': 'find', 'query': args.find, 'matches': matches[args.offset:args.offset + 12],
                       'next_offset': args.offset + 12 if len(matches) > args.offset + 12 else None})
        return result
    if args.section is None and args.start_line is None:
        result.update({'mode': 'outline', 'sections': items[args.offset:args.offset + 20],
                       'next_offset': args.offset + 20 if len(items) > args.offset + 20 else None})
        return result
    if args.section is not None:
        item = select_heading(items, args.section)
        begin, end = item['line'], item['end_line']
        result['section'] = item['path']
    else:
        begin, end = args.start_line, min(len(lines), args.start_line + args.lines - 1)
        if begin < 1 or begin > len(lines):
            raise ValueError('起始行超出文件范围')
    chosen = [n for n in range(begin, end + 1) if n in visible]
    if not chosen:
        raise ValueError('请求超出该来源登记的章节范围')
    content = ''.join(lines[n - 1] for n in chosen)
    finish = args.offset + args.max_chars
    result.update({'mode': 'text', 'line_range': [chosen[0], chosen[-1]], 'offset': args.offset,
                   'text': content[args.offset:finish], 'total_chars': len(content),
                   'next_offset': finish if finish < len(content) else None})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--section')
    group.add_argument('--find')
    group.add_argument('--start-line', type=int)
    parser.add_argument('--lines', type=int, default=40)
    parser.add_argument('--offset', type=int, default=0)
    parser.add_argument('--max-chars', type=int, default=4000, help='正文片段字符上限（不含来源元数据）')
    args = parser.parse_args()
    if args.offset < 0 or not 1 <= args.lines <= 200 or not 100 <= args.max_chars <= 12000:
        raise ValueError('offset 须非负，lines 为 1–200，max-chars 为 100–12000')
    print(json.dumps(response(args), ensure_ascii=False, separators=(',', ':')))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, UnicodeError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
