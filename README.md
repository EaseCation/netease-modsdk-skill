# 网易 ModSDK 开发知识 Skill

公开仓库：[EaseCation/netease-modsdk-skill](https://github.com/EaseCation/netease-modsdk-skill)。

这是独立的轻量 Git 仓库。Wiki 保管官方 Markdown、中文 Bedrock 镜像、补充标注与唯一 API 查询实现；本仓库提供按阶段/模块展开的开发指引、配置、精简安装和调用入口。

## 获取 Skill

```sh
git clone --depth=1 https://github.com/EaseCation/netease-modsdk-skill.git
cd netease-modsdk-skill
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
- 稀疏检出 `docs/mcdocs`、`docs/mcguide`、`docs/mconline`、`docs/wiki` 下的 Markdown、`knowledge/*.json` 和查询脚本；不检出图片、视频或整个站点源码，并设置 `GIT_LFS_SKIP_SMUDGE=1`。

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
ln -s /absolute/path/to/netease-modsdk-skill ~/.codex/skills/netease-modsdk-skill
```

已有同名安装时先确认归属，避免覆盖其他内容。技能的自动选择设置在 `agents/openai.yaml`；使用指引见 [SKILL.md](SKILL.md)。

## 按需开发指引

[SKILL.md](SKILL.md) 保持短入口，按当前任务选择 14 个模块中的相关一篇；需要跨版判断时再加载版本说明，具体字段再读取原文章节。API 合同仍调用现有 query，不将全部教程混入 API 索引。

指引覆盖工程结构、UI、粒子、Molang/数学、动画与渲染、方块/实体/物品、维度与地形，并补充数据表、状态同步及排错性能。每个模块有中外版能力对比和详情路径。国际版比较以 1.21.130 为目标；网易文档快照的版本与项目实际包体分开记录。

```sh
# 默认只输出目录
python3 scripts/read_doc.py cn-ui
# 按章节读取；超出默认 4,000 字符时显式分页
python3 scripts/read_doc.py cn-ui --section 文件目录
# 教程来源、引用和阅读路径预算
python3 scripts/evaluate.py --guides
```

主要详情来自已绑定 Wiki；国际版补充按固定提交只下载所需 Markdown 文件并缓存，首次读取需联网，后续可离线。文本摘要统一 UTF-8 换行后比较。来源登记表由工具读取，Agent 不需要整体加载。[阅读说明](references/reading.md) 解释章节、关键词定位和分页。

[evals/guidance.json](evals/guidance.json) 固定 14 条实际需求阅读路径及内容复核点；检查来源可读、引用闭合、默认不输出全文及字符预算。这不是独立 Agent 自动选路评测，也不是游戏功能验收。根入口上限 2,200 字符、单篇参考上限 2,600 字符，复杂路径可按题目明确追加预算。

## 查询和固定回归

最新版要求 Wiki 运行时与标注协议均为 2，不兼容旧快照。复杂需求用 `resolve --plan-file -` 一次提交原子职责和约束，格式见 [查询计划](references/query-plan.md)。主候选优先匹配请求阶段，关联前后阶段仍一起返回；限制命中与正向能力分开。

稳定题库、参考能力、禁止误用项和预算均存放在本仓库 [evals/cases.json](evals/cases.json)。运行实际查询 CLI：

```sh
MODSDK_WIKI_ROOT=../netease-modsdk-wiki python3 scripts/evaluate.py
# 人工复核题库或输出预算变更后，才显式更新基线：
python3 scripts/evaluate.py --record-baseline
```

题库包含产品职责、改写与边界对照、关联阶段及无效计划。它冻结语义计划，评估候选召回、误推荐、未解决状态、关联事件和输出字符预算；并非对 Agent 自动拆解自然语言的独立评估，也不是游戏功能验收。`contract_checks` 是人工复核提示，不冒称已自动执行。初次留出失败保存在 [evals/history.json](evals/history.json)，修复后这些题是已知回归，不再称盲测。

[evals/baseline.json](evals/baseline.json) 记录已接受的完整通过基线。改变题库哈希会要求人工复核并显式重录；任何题失败都不能记录基线。固定硬预算之外，每题输出比基线增长超过 15%（至少 128 字符容差）也会报错。字符数不是模型 token；调用数是评估器固定执行次数，不表示真实 Agent 自主调用成本。

最近一次详细回执写入忽略的 `.local/regression-report.json`。GitHub Actions 在 Skill 推送和 PR 时浅克隆公开 Wiki 并执行同一题库；Wiki 部署也在构建前绑定当前提交执行它。历史 Wiki 题库与旧查询器可从 Wiki 提交 `2ae0d396c1f4e079b685e73e45245e73a515a9a7` 追溯，不维护第二套活跃题库。

支持 Python 3.9+。格式检查使用宿主 skill-creator 的 `quick_validate.py`；发布应包含绑定已有 Wiki、从最新版 Git 快照精简安装、执行真实查询和文件完整性核对。
