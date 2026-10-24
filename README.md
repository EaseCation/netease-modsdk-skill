# 网易 ModSDK API 查询 Skill

公开仓库：[EaseCation/netease-api-query](https://github.com/EaseCation/netease-api-query)。

这是独立的轻量 Git 仓库。Wiki 保管官方 Markdown、补充标注与唯一查询实现；本仓库提供 Agent 指引、配置、精简安装和调用入口。

## 获取 Skill

```sh
git clone --depth=1 https://github.com/EaseCation/netease-api-query.git
cd netease-api-query
```

## 使用已有 Wiki

```sh
python3 scripts/setup.py --wiki-root ../netease-modsdk-wiki
python3 scripts/setup.py --check
python3 scripts/query.py resolve '获取玩家背包物品' --side server
```

`setup.py` 将路径写入本仓库 `.env`；不会修改已有 Wiki 的 Git 配置、检出范围或当前分支。`.env` 不提交 Git。

## 首次下载 Wiki

新安装且没有 `.env` 时，默认下载到本仓库 `.data/wiki`：

```sh
python3 scripts/setup.py
python3 scripts/query.py detail SetAttrValue --side server --examples 0
```

下载默认来自 `https://github.com/EaseCation/netease-modsdk-wiki.git` 的 `main`。可通过 `.env` 或 `--repository`、`--ref`、`--wiki-root` 选择其他明确来源、分支或标签。目标版本须包含 `scripts/api_knowledge.py` 和 `knowledge/annotations.json`；旧快照会报错，不提供兼容回退。

三个配合使用的步骤减少下载量：

- `--depth=1 --single-branch`：只取所需分支的最新浅层历史。
- `--filter=blob:none --no-checkout`：在确定检出范围前不取全部文件内容；来源 Git 服务需支持 partial clone，GitHub 支持。
- 稀疏检出 `docs/mcdocs`、`docs/mcguide`、`docs/mconline` 下的 Markdown、`knowledge/*.json` 和查询脚本；不检出图片、视频或整个站点源码，并设置 `GIT_LFS_SKIP_SMUDGE=1`。

安装器的 Git 请求使用 HTTP/1.1，以规避部分网络环境中 HTTP/2 的传输中断；仅作用于本次命令，不修改全局 Git 配置。

无需 git-lfs 或 npm。图像链接仍会保留在原文中，但媒体文件不在精简副本中。这个副本适用于文字查询；要预览或构建完整 Wiki，使用完整 Wiki 仓库。

## 配置和更新

`.env.example` 给出了所有配置。环境变量优先于本仓库 `.env`；文件仅作为文本解析，不执行 shell 表达式。相对路径始终以本 skill 仓库根目录为基准，也支持带空格的带引号路径。不要从 Wiki 的 `.env` 复制部署或服务凭据。

```dotenv
MODSDK_WIKI_ROOT=../netease-modsdk-wiki
MODSDK_WIKI_REPOSITORY=https://github.com/EaseCation/netease-modsdk-wiki.git
MODSDK_WIKI_REF=main
```

更新工具自建的精简副本：

```sh
python3 scripts/setup.py --update
```

精简副本是用于查询的 detached HEAD 快照。更新前检查所有本地修改和提交位置；有用户修改时拒绝继续。候选版本缺少必要查询文件时，保留当前可用副本。普通完整 Wiki 不由本工具自动更新。

查询只调用 Wiki 的 `scripts/api_knowledge.py`，全部参数继续传递。新增标注或原文变更后由 Wiki 运行时重建索引，并检查标注依据的哈希；这里没有第二套解析器、兼容运行时或文档副本。

## 安装到 Agent

将本仓库目录安装或符号链接到 Agent 的技能目录。例如在 macOS/Linux：

```sh
ln -s /absolute/path/to/netease-api-query ~/.codex/skills/netease-api-query
```

已有同名安装时先确认归属，避免覆盖其他内容。技能的自动选择设置在 `agents/openai.yaml`；使用指引见 [SKILL.md](SKILL.md)。

## Wiki 侧验收

Wiki 的检索验收入口可通过 `MODSDK_SKILL_ROOT` 指向这个独立仓库；默认查找同级 `netease-api-query`，再查 Agent 已安装目录。验收进程显式传入它正在检查的 Wiki 路径，不受 skill 本地绑定的另一个 Wiki 干扰。

支持 Python 3.9+。格式检查使用宿主 skill-creator 的 `quick_validate.py`；实际验证应包含绑定已有 Wiki、从最新版 Git 快照精简安装、执行真实查询和文件完整性核对。
