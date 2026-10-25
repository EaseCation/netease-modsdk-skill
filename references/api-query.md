# API、事件与枚举核验

入口：`python3 <技能目录>/scripts/query.py`。查询器核对能力证据，不代替 AI 理解需求。

## 先整理请求

把用户表述整理为“动作＋作用对象＋属性/内容＋必要限定”。保留端侧、对象归属、范围、时机、持久化及可修改/取消要求；区分执行行为与控制权限、输入与效果。不要照抄长段玩法背景，也不要为了命中删掉限定。

- 单项能力用 `mode: atomic`，一项一个操作；事件单列 `kind: event, operation: observe`。读后写、按下/松开、多对象分别查询。
- 注册与创建、捕获与恢复等接入路线用 `mode: workflow`，保留整体目标和生命周期；操作混合时省略 operation。流程未命中再拆职责，不能把一个步骤当成整个方案。
- 明确填写 `operation`、`target`、`extent` 等已有字段；结构化操作优先，不让脚本从句子重复猜测。使用 read/set/create/play 等具体操作，只有泛指变更才用 write。
- 有角色歧义时用 `schema <概念词>` 查局部词表。`action/subject/object/property/qualifiers` 明确角色；`concepts` 是必需能力，`hints` 只是可选召回线索。不要猜 ID 或通读全词表。
- 关键条件没有受控字段可表达时放入 `requirements`，原样保留待核验；不能用堆概念替代语义拆解。
- 提交前对照原需求检查是否丢失对象、操作或限定。返回后再对照一次；matched 只证明已表达条件的文档覆盖，不证明完整理解了用户需求。

通过 stdin 批量提交，计划中不填目标 API 答案：

```sh
python3 <技能目录>/scripts/query.py resolve --plan-file - --limit 8 <<'JSON'
{"side":"server","intents":[
  {"id":"read","mode":"atomic","query":"读取实体当前生命值","kind":"api","operation":"read"},
  {"id":"set","mode":"atomic","query":"设置实体当前生命值","kind":"api","operation":"set"},
  {"id":"event","mode":"atomic","query":"监听实体生命值变化之前的事件","kind":"event","operation":"observe","phase":"before"}
]}
JSON
python3 <技能目录>/scripts/query.py detail <短ID1> <短ID2> --side server --examples 0
```

完整字段与输出语义按需读 [查询计划](query-plan.md)，实际可用字段以 `schema` 为准。只读用 `read_only: true`；否定条件用 exclude_targets/exclude，禁止把否定对象变成正向能力。

## 判断结果后再补查

- `results` 默认每项一个主要候选，按 `intents[].candidates` 对应职责。`limit` 至少覆盖子目标数；必要比较才设 `--per-intent 2`。
- `query_incomplete`：没识别出可核对的核心能力，明确属性/对象后补查；`split_required`：混合操作，拆职责或查询整体流程。
- `evidence_missing`：找到候选但缺对应核验事实，读合同；`partial` 的 missing/missing_roles/unverified 是尚未证明的条件，不等于平台不支持。不要仅为消除状态而删条件。
- `workflow_unverified`：没有已审的整体路线，候选只能作为单步线索；`workflows` 给出有来源的步骤、警告及文档路径。
- `review` 保留关键能力条件尚未核验的候选，不作为已支持的步骤；`limitations` 是已知冲突或限制证据；`related` 是同族关联阶段，不能替代所需时机。`timing_review` 需核对真实阶段。取消能力、可修改参数不能从“之前”推断。
- 未命中的单项职责用 search，必要时查局部词表或分页；不循环盲猜同义词。替代候选不能拼成完整能力。

最后批量读必要 detail 合同：核对组件归属、参数、返回、端侧和限制，不凭摘要或名称实现。source 可定位原文；developer_notes 是工程补充。`--verbose` 才展开诊断。长合同用 `detail ID --part remarks|examples|raw --offset 0 --page-chars 6000` 分页；next_offset 表示还有后文。输出超预算应缩小候选/示例，不截掉限制后声称核验完成。

默认 scope=modsdk 排除 Preset；仅用户明确要求时使用 preset/all。当前是 ModSDK 3.9 文档快照，不证明其他版本兼容；旧请求引擎报错时同步更新 Wiki 与 Skill，不回退协议。

Bukkit/Nukkit 迁移先解释中文能力并保留范围，按需读 [常用能力迁移](bukkit-basics.md)；字符串问题读 [Python 数据边界](python-boundaries.md)。`str` 不证明 Unicode 兼容，无返回值也不证明失败。引用原文可用 section；原文或标注变化自动重建，证据哈希变化须先复核。

回复包含端侧、能力边界、来源和组合职责。检索命中不等于游戏实机验收。
