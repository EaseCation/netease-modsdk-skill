---
name: netease-api-query
description: 查询网易我的世界中国版 ModSDK API、事件与枚举，根据完整模组需求检索相关能力并按需读取参数、限制和示例。使用 Wiki 原文与独立人工标注，默认排除 Preset 预设系统；用于开发前 API 核验，不负责构建或游戏操作。
---

# ModSDK API 查询

本技能独立于 Wiki 分发。需要 Python 3.9+ 和 Git；无需 Node、npm 或 git-lfs。入口为 `python3 <本技能目录>/scripts/query.py`。

首次先运行 `python3 <本技能目录>/scripts/setup.py --check`。已有 Wiki 时用 `setup.py --wiki-root /实际/Wiki/路径` 绑定；尚未安装时运行 `setup.py`，按 `.env` 或默认配置浅克隆最新版 Wiki。设置可从 `.env.example` 复制，优先级为环境变量 > 本技能根目录 `.env` > 默认值。相对路径始终相对本技能实际目录，不相对调用者工作目录。

下载默认使用 `--depth=1 --filter=blob:none --no-checkout` 和非 cone 稀疏检出，只保留 Markdown、独立标注和查询脚本，禁用 LFS 下载。图片、视频和其他资产不参与 API 文本查询；精简副本不能用于完整 Wiki 网页构建。`setup.py --update` 只更新本工具创建且没有用户修改的精简副本；已有完整 Wiki 保持原有管理流程。

查询实现与数据全部来自配置的 Wiki，不随 skill 复制运行时或维护第二套索引。Wiki 缺少查询入口、标注或协议版本不匹配时明确报错；应更新到相互配套的最新版，不回退旧版。首次部署须先发布含增强查询功能的 Wiki 版本，再提供 skill 的安装入口。详细配置见 [README.md](README.md)。

优先把完整需求一次传给 `resolve`，指定已知端侧。例如：

```sh
python3 <本技能目录>/scripts/query.py resolve '使用治疗法杖回血，显示生命上限，5秒冷却，只提示本人' --side server
python3 <本技能目录>/scripts/query.py detail <候选短ID1> <候选短ID2> --side server --examples 0
```

- 默认 `--scope modsdk` 排除 Preset API、预设零件及预设教程。只有用户明确要使用或研究预设时传 `--scope preset`；明确比较两套框架时传 `--scope all`。“不要预设”不构成放开范围的理由。
- 当前为 ModSDK 3.9 文档快照（含 3.8 基础文档），并非全部接口的引入版本。其他目标版本不能由此证明兼容；`--sdk-version` 会拒绝不支持的版本。
- `resolve` 的 groups 是人工能力关联，`uncovered_groups` 只表示已知组的遗漏。逐项对照需求，未命中的需求仍需核验，不能宣称全部覆盖。未知领域用 `search`，必要时换一个明确概念并通过 `--offset` 翻页；不要循环盲猜同义词或加载整库。
- 从 Bukkit/Nukkit 需求出发时，先将社区方法名解释为中文基础能力，并保留对象、读写动作和时机，再查询。例如将生命值增减表达为“读取玩家当前生命值并设置目标值”，将背包材料扣除拆成“读取槽位、匹配数量、写回”。不依赖英文方法名相似度，也不把近似 SDK 名称当成已确认等价。
- 迁移时按返回的合同核对坐标基准、秒与帧、玩家与非玩家、事件触发阶段、发放结果等差异。权限节点、配方文件或计分板对象模型没有核准对应时说明缺口；未搜到不等于平台一定不支持。
- `detail` 接受短 ID、完整 ID 或名称；同名歧义返回候选，结合端侧、组件和来源选定 ID。不要从搜索摘要推断完整签名。
- 默认合同保留全部官方备注与开发注意事项。`developer_notes` 是人工工程建议；签名、端侧和限制以原文为准，不能把业务组合方案描述成内建 API。
- 按需读取示例或原文：`detail ID --part examples|remarks|raw --offset 0 --page-chars 6000`；返回 `next_offset` 时表示仍有后文。搜索一次、批量读必要合同通常即可，不先拉全量索引。
- 默认输出预算 18000 字符；超限会明确报错。先减少候选或示例，关键备注不能省略后当作已核验。枚举通过 `detail AttrType --part raw` 读取，原文片段通过 `section 'mcdocs/…/工具.md' 'AddTimer > 服务端接口'` 获取。
- 本地原文或标注变化后自动重建；标注依据的章节哈希变化会阻止构建，须复核补充信息后更新哈希。

回复开发者时给出必要 API、端侧、重要限制及来源；多 API 组合说明各自职责，并指出未确定的能力。查询成功只证明找到了文档，不证明玩法已通过实机测试。
