#!/usr/bin/env python3
"""配置已有 Wiki，或下载仅供查询的浅克隆 Markdown 副本。"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from config import SKILL_ROOT, read_config, resolve_root, validate_contract, validate_wiki, write_config

PATTERNS = ['/scripts/api_knowledge.py', '/knowledge/*.json',
            '/docs/mcdocs/**/*.md', '/docs/mcguide/**/*.md', '/docs/mconline/**/*.md', '/docs/wiki/**/*.md']
MARKER = 'modsdk-skill-checkout.json'


def git(args, cwd=None, stdin=None):
    # 只对本次 Git 子进程生效，不依赖 git-lfs 安装，不改宿主全局配置。
    command = ['git', '-c', 'http.version=HTTP/1.1',
               '-c', 'http.lowSpeedLimit=1', '-c', 'http.lowSpeedTime=60',
               '-c', 'filter.lfs.smudge=', '-c', 'filter.lfs.process=',
               '-c', 'filter.lfs.required=false', *args]
    result = subprocess.run(command, cwd=cwd, input=stdin, text=True, capture_output=True,
                            env={**os.environ, 'GIT_LFS_SKIP_SMUDGE': '1', 'GIT_TERMINAL_PROMPT': '0'})
    if result.returncode:
        raise ValueError('Git 操作失败：' + result.stderr.strip())
    return result.stdout.strip()


def marker(root):
    return root / '.git' / MARKER


def set_marker(root, repository, ref):
    marker(root).write_text(json.dumps({'owner': 'netease-modsdk-skill', 'repository': repository,
                                      'ref': ref, 'commit': git(['rev-parse', 'HEAD'], root),
                                      'patterns': PATTERNS}, ensure_ascii=False, indent=2) + '\n')


def validate_revision(root, revision):
    try:
        script = git(['show', revision + ':scripts/api_knowledge.py'], root)
        annotations = git(['show', revision + ':knowledge/annotations.json'], root)
        git(['cat-file', '-e', revision + ':docs/mcdocs/1-ModAPI'], root)
    except ValueError as error:
        if 'does not exist in' in str(error) or 'exists on disk, but not in' in str(error):
            raise ValueError('所选 Wiki 提交缺少新版查询文件；请先发布最新版 Wiki 或选择包含查询功能的分支/标签') from error
        raise  # 网络或对象传输失败不能伪装成旧版 Wiki。
    validate_contract(script, annotations)


def clone(root, repository, ref):
    root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.' + root.name + '-download-', dir=root.parent))
    try:
        print('准备浅克隆：只检出 Markdown、标注数据与查询入口，跳过图片和视频。', file=sys.stderr, flush=True)
        git(['clone', '--depth=1', '--single-branch', '--filter=blob:none', '--no-checkout',
             '--branch', ref, '--', repository, str(staging)])
        validate_revision(staging, 'HEAD')
        git(['sparse-checkout', 'set', '--no-cone', '--stdin'], staging, '\n'.join(PATTERNS) + '\n')
        git(['checkout', '--detach', 'HEAD'], staging)
        validate_wiki(staging)
        # 这些是查询运行时产生的本地缓存，旧版 Wiki 可能尚未配置忽略规则。
        exclude = staging / '.git/info/exclude'
        with exclude.open('a', encoding='utf8') as file:
            file.write('\n/.api-index/\n/docs/public/ai/\n')
        set_marker(staging, repository, ref)
        if root.exists():
            raise ValueError('目标目录已出现，保留现状，不覆盖：' + str(root))
        staging.rename(root)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def update(root, repository, ref):
    file = marker(root)
    if not file.is_file():
        raise ValueError('--update 只更新本工具创建的精简副本；现有 Wiki 请自行按仓库流程更新')
    state = json.loads(file.read_text())
    if state.get('owner') != 'netease-modsdk-skill':
        raise ValueError('不是本工具管理的副本')
    if git(['status', '--porcelain', '--untracked-files=all'], root):
        raise ValueError('副本存在修改，保留现场；请先处理修改再更新')
    if git(['rev-parse', 'HEAD'], root) != state['commit']:
        raise ValueError('副本提交已由用户改变，保留现状')
    if git(['remote', 'get-url', 'origin'], root) != repository:
        raise ValueError('配置的来源与现有 origin 不同，拒绝静默切换来源')
    print('更新查询副本的浅层快照。', file=sys.stderr, flush=True)
    git(['fetch', '--depth=1', '--filter=blob:none', '--', 'origin', ref], root)
    # 检查候选提交后再切换，缺少新版文件时保留当前可用副本。
    validate_revision(root, 'FETCH_HEAD')
    # 保留旧提交的 Git 可恢复状态；不 reset、不清理用户文件。
    git(['checkout', '--detach', 'FETCH_HEAD'], root)
    git(['sparse-checkout', 'set', '--no-cone', '--stdin'], root, '\n'.join(PATTERNS) + '\n')
    validate_wiki(root)
    set_marker(root, repository, ref)


def status(root):
    validate_wiki(root)
    script = root / 'scripts/api_knowledge.py'
    note = root / 'knowledge/annotations.json'
    annotation_count = len(json.loads(note.read_text())['entries'])
    result = {'wiki_root': str(root), 'runtime': 'wiki', 'runtime_path': str(script),
              'annotations': annotation_count, 'knowledge_status': 'annotated',
              'bedrock_tutorials_present': (root / 'docs/wiki/json-ui/json-ui-intro.md').is_file(),
              'managed_text_checkout': marker(root).is_file(), 'markdown_files': sum(1 for _ in (root / 'docs').rglob('*.md'))}
    if (root / '.git').is_dir():
        result['commit'] = git(['rev-parse', 'HEAD'], root)
        result['working_tree_dirty'] = bool(git(['status', '--porcelain', '--untracked-files=all'], root))
        result['shallow'] = git(['rev-parse', '--is-shallow-repository'], root) == 'true'
        result['lfs_objects_present'] = (root / '.git/lfs/objects').exists()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wiki-root', help='已有 Wiki 或新精简副本的路径；相对 skill 仓库根目录')
    parser.add_argument('--repository', help='首次下载或受管更新的仓库地址，也可为本地 Git 路径')
    parser.add_argument('--ref', help='要浅克隆的分支或标签；默认 main')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--check', action='store_true', help='只检查配置和数据，不下载或写配置')
    group.add_argument('--update', action='store_true', help='更新本工具创建、没有用户修改的精简副本')
    args = parser.parse_args()
    values = read_config()
    for attr, key in [('wiki_root', 'MODSDK_WIKI_ROOT'), ('repository', 'MODSDK_WIKI_REPOSITORY'), ('ref', 'MODSDK_WIKI_REF')]:
        if getattr(args, attr) is not None:
            values[key] = getattr(args, attr)
    if any(not v.strip() for v in values.values()):
        raise ValueError('Wiki 路径、仓库和版本不能为空')
    root = resolve_root(values['MODSDK_WIKI_ROOT'])
    if not args.check:
        if not root.exists():
            clone(root, values['MODSDK_WIKI_REPOSITORY'], values['MODSDK_WIKI_REF'])
        elif args.update:
            update(root, values['MODSDK_WIKI_REPOSITORY'], values['MODSDK_WIKI_REF'])
        else:
            validate_wiki(root)
        try:
            values['MODSDK_WIKI_ROOT'] = os.path.relpath(root, SKILL_ROOT)
        except ValueError:  # Windows 的不同盘符无法使用相对路径。
            values['MODSDK_WIKI_ROOT'] = str(root)
        write_config(values)
    print(json.dumps(status(root), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, SyntaxError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
