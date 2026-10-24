# 查询计划协议 2

`query.py schema` 给出当前受控枚举。根节点仅接受 `intents`（1–12 项）、`side`、`scope`、`read_only`。每个子目标 ID 不重复；不要夹带目标 API 答案。复杂需求超过 12 项时分批提交并保留职责清单。

| 子目标字段 | 用法 |
| --- | --- |
| id / query | 唯一职责 ID / 中文基础能力描述 |
| kind | api、event、enum、document、all；事件明确使用 event |
| side / scope | server、client、common、any / modsdk、preset、all；一般继承根节点 |
| operation | read、write、create、set、delete、play、pause、resume、stop、observe、any；write 是变更操作的统称 |
| read_only | true 将 API 限为读取、事件限为观察；不能在子目标解除根节点只读 |
| target | `schema` 中的对象类别，如 player_inventory、player_equipment、block_container；不确定时省略 |
| extent | single、many、global、dimension、any |
| target_scope | local_player、other_player、all_players、any；用于区分客户端完整背包读取限制 |
| phase | before、after、change、any；仅事件，影响排序但不排除关联阶段 |
| batch | bulk、any；明确需要批量结果时使用 |
| exclude_targets | 明确排除的对象类别数组 |
| exclude | 排除候选能力说明中的精确词组数组；不是任意自然语言逻辑解析器 |
| must_support | 必须有正向文本证据的精确词组数组；限制文本不能满足要求 |

`must_support` 不会自动归一所有近义词，缺少文本证据表示尚未核实，不代表平台不支持。对象、操作和范围部分来自原文及组件名称的规则推断，仍需读详情；阶段 change 表示“发生/变化时”，不能擅自解释为 after。需要取消能力时，查询中保留取消职责并核对参数。

输入计划时把筛选条件写入 JSON，不混用文本查询的操作/对象参数。`--limit` 限主候选（1–24），`--per-intent` 为 1–3；关联事件独立去重返回，仍受总字符预算限制。超预算明确报错，不静默丢失合同。

输出中 `intents` 保留每项候选和状态；`results` 是去重主候选；`related` 是事件族其他阶段；`limitations` 是限制证据；`prerequisites` 是前置关系。关联事件包含 `related_to` 指向主候选，不能拿它满足当前阶段的能力断言。仅主候选匹配时 status 为 candidates，表示待读合同而非已验证。no_capability_match、timing_review、budget_limited、prerequisite_conflict 均保留为未解决项。

同一事件族不同阶段应一起供 Agent 理解，不混同触发时机；只读、对象和端侧约束仍需独立执行。普通读写接口的 related 不会因此自动混入只读搜索结果，完整关联可从 detail 查看。
