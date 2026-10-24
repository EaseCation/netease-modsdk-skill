"""只读取本 skill 的配置，不执行 .env，也不读取 Wiki 中的服务凭据。"""
import os
import ast
import json
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
KEYS = ('MODSDK_WIKI_ROOT', 'MODSDK_WIKI_REPOSITORY', 'MODSDK_WIKI_REF',
        'MODSDK_UPDATE_CHECK_HOURS', 'MODSDK_NETWORK_TIMEOUT', 'MODSDK_GITHUB_PROXY_PREFIX')
DEFAULTS = {'MODSDK_WIKI_ROOT': '.data/wiki',
            'MODSDK_WIKI_REPOSITORY': 'https://github.com/EaseCation/netease-modsdk-wiki.git',
            'MODSDK_WIKI_REF': 'main', 'MODSDK_UPDATE_CHECK_HOURS': '24',
            'MODSDK_NETWORK_TIMEOUT': '30', 'MODSDK_GITHUB_PROXY_PREFIX': ''}


def read_config():
    values = dict(DEFAULTS)
    file = SKILL_ROOT / '.env'
    if file.is_file():
        for number, line in enumerate(file.read_text(encoding='utf-8-sig').splitlines(), 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('export '):
                line = line[7:].strip()
            key, sep, value = line.partition('=')
            key = key.strip()
            if key not in KEYS:
                continue
            if not sep:
                raise ValueError('.env 第 {} 行缺少等号'.format(number))
            value = value.strip()
            if value.startswith(('"', "'")):
                quote = value[0]
                end = value.find(quote, 1)
                if end < 0 or value[end + 1:].strip() and not value[end + 1:].strip().startswith('#'):
                    raise ValueError('.env 第 {} 行引号格式错误'.format(number))
                value = value[1:end]
            else:
                value = value.split(' #', 1)[0].rstrip()
            values[key] = value
    for key in KEYS:
        if key in os.environ:
            values[key] = os.environ[key]
        if key != 'MODSDK_GITHUB_PROXY_PREFIX' and not values[key].strip():
            raise ValueError(key + ' 不能为空')
    for key, low, high in [('MODSDK_UPDATE_CHECK_HOURS', 0, 720), ('MODSDK_NETWORK_TIMEOUT', 1, 120)]:
        if not values[key].isdigit() or not low <= int(values[key]) <= high:
            raise ValueError(key + ' 的值超出允许范围')
    return values


def resolve_root(value):
    path = Path(value).expanduser()
    return (path if path.is_absolute() else SKILL_ROOT / path).resolve()


def write_config(values):
    """只替换所管理的键，保留用户其他配置和注释。"""
    path = SKILL_ROOT / '.env'
    lines = path.read_text(encoding='utf8').splitlines() if path.exists() else []
    remaining = dict(values)
    result = []
    for line in lines:
        key = line.strip().removeprefix('export ').partition('=')[0].strip()
        if key in values:
            if key in remaining:
                result.append(format_value(key, remaining.pop(key)))
        else:
            result.append(line)
    result += [format_value(k, v) for k, v in remaining.items()]
    path.write_text('\n'.join(result) + '\n', encoding='utf8')


def format_value(key, value):
    if any(c in value for c in ('\n', '\r', '"')):
        raise ValueError(key + ' 包含不支持的换行或双引号')
    return '{}="{}"'.format(key, value)


def validate_contract(script_text, annotation_text):
    # 只检查声明，不为检查版本执行 Wiki 代码。
    tree = ast.parse(script_text)
    schema = next((node.value.value for node in tree.body
                   if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
                   and any(isinstance(t, ast.Name) and t.id == 'SCHEMA_VERSION' for t in node.targets)), None)
    annotations = json.loads(annotation_text)
    if not isinstance(annotations, dict) or schema != 2 or annotations.get('schema_version') != 2:
        raise ValueError('Wiki 查询协议版本不匹配，请同步更新 skill 和 Wiki')
    if not isinstance(annotations.get('entries'), list):
        raise ValueError('Wiki 标注格式不完整，请使用最新版 Wiki')


def validate_wiki(root):
    required = [root / 'scripts/api_knowledge.py', root / 'knowledge/annotations.json']
    missing = [str(p.relative_to(root)) for p in required if not p.is_file()]
    if missing:
        raise ValueError('Wiki 版本不满足要求，缺少 ' + '、'.join(missing) + '；请使用已发布查询功能的最新版 Wiki，不提供旧版回退')
    api_dir = root / 'docs/mcdocs/1-ModAPI'
    if not api_dir.is_dir() or not any(api_dir.rglob('*.md')):
        raise ValueError('未找到 ModSDK Markdown。请运行本技能 scripts/setup.py 或检查 MODSDK_WIKI_ROOT')
    validate_contract(required[0].read_text(encoding='utf8'), required[1].read_text(encoding='utf8'))
    return root
