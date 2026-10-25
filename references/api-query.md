# API、事件与枚举核验

入口：`python3 <技能目录>/scripts/query.py`。只在需要 Python 接口合同时读取本页。

先把完整需求拆为原子职责，一项只负责一种对象、一个操作或一个事件时机。通过 `resolve --plan-file -` 从 stdin 一次提交 JSON；不要把复杂需求当作单个关键词串，也不要事先猜 API 名称。已知端侧写在根节点，事件单独用 `kind: event`。例如：

```sh
python3 <本技能目录>/scripts/query.py resolve --plan-file - --limit 8 <<'JSON'
{"side":"server","intents":[
  {"id":"read","query":"读取实体当前生命值","kind":"api","operation":"read"},
  {"id":"update","query":"设置实体当前生命值","kind":"api","operation":"set"},
  {"id":"before","query":"实体生命值变化之前的事件","kind":"event","phase":"before"}
]}
JSON
python3 <本技能目录>/scripts/query.py detail <候选短ID1> <候选短ID2> --side server --examples 0
```

- 只读需求设 `read_only: true`；否定条件写入 `exclude_targets` 或 `exclude`，不要让被否定的词变成正向命中。保留对象类型、单个/全局范围，以及本人/其他玩家的区别。
- `target` 等值使用受控枚举，不确定时省略或调用 `schema` 查看，不发明字段。完整计划约束和输出说明见 [references/query-plan.md](query-plan.md)。
- `results` 按子目标分配候选，默认每项一条，再补必需前置与互补能力；`--per-intent 2` 可增加候选。`limit` 至少覆盖子目标数。按 `intents[].candidates` 核对各职责，不能把返回了八条理解为需求完整。
- `related` 返回同一事件族的关联阶段。添加前、获得时、刷新和移除事件可同时返回，主候选按请求阶段优先排序；关联事件不当作该阶段的替代。`phase` 只是索引中的保守分类，取消能力、参数可修改性、确切时机仍查原文。`timing_review` 表示主候选阶段未匹配。
- `limitations` 是限制或未核实能力的证据，不是支持能力的推荐。`prerequisites` 标明必需前置；子目标的 `state`、`missing` 与缺失角色必须继续核验；`workflows` 提供必要组合步骤和原文入口，不能把一个候选当成整个能力。

- 默认 `--scope modsdk` 排除 Preset API、预设零件及预设教程。只有用户明确要使用或研究预设时传 `--scope preset`；明确比较两套框架时传 `--scope all`。“不要预设”不构成放开范围的理由。
- 当前为 ModSDK 3.9 文档快照（含 3.8 基础文档），并非全部接口的引入版本。其他目标版本不能由此证明兼容；`--sdk-version` 会拒绝不支持的版本。
- 未命中的单项职责用 `search`，必要时换一个明确概念并通过 `--offset` 翻页；不要循环盲猜同义词或加载整库。查询未命中不证明平台不支持。
- 消息、标题、计分板等 Bukkit 基础能力迁移，按需读 [常用能力迁移](bukkit-basics.md)。
- 涉及字符串参数或嵌套文本时，按需读 [Python 数据边界](python-boundaries.md)；`str` 标注不足以证明 Unicode 兼容，无返回值也不能作为失败证据。
- 从 Bukkit/Nukkit 需求出发时，先将社区方法名解释为中文基础能力，并保留对象、读写动作和时机，再查询。例如将生命值增减表达为“读取玩家当前生命值并设置目标值”，将背包材料扣除拆成“读取槽位、匹配数量、写回”。不依赖英文方法名相似度，也不把近似 SDK 名称当成已确认等价。
- 迁移时按返回的合同核对坐标基准、秒与帧、玩家与非玩家、事件触发阶段、发放结果等差异。权限节点、配方文件或计分板对象模型没有核准对应时说明缺口；未搜到不等于平台一定不支持。
- `detail` 接受短 ID、完整 ID 或名称；同名歧义返回候选，结合端侧、组件和来源选定 ID。不要从搜索摘要推断完整签名。
- 默认合同保留全部官方备注与开发注意事项。默认输出省略正常状态与空字段，`--verbose` 才返回诊断元数据。`developer_notes` 是人工工程建议；签名、端侧和限制以原文为准，不能把业务组合方案描述成内建 API。
- 按需读取示例或原文：`detail ID --part examples|remarks|raw --offset 0 --page-chars 6000`；返回 `next_offset` 时表示仍有后文。搜索一次、批量读必要合同通常即可，不先拉全量索引。
- 默认输出预算 18000 字符；超限会明确报错。先减少候选或示例，关键备注不能省略后当作已核验。枚举通过 `detail AttrType --part raw` 读取，原文片段通过 `section 'mcdocs/…/工具.md' 'AddTimer > 服务端接口'` 获取。
- 本地原文或标注变化后自动重建；标注依据的章节哈希变化会阻止构建，须复核补充信息后更新哈希。

回复开发者时给出必要 API、端侧、重要限制及来源；多 API 组合说明各自职责，并指出未确定的能力。查询成功不证明能力完整或玩法已通过实机测试。
