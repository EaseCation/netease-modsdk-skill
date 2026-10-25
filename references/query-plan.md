# 查询计划协议 3

`query.py schema` 给出受控字段；`schema <概念词>` 查局部词表，`schema --all-concepts` 才展开全部概念。根节点仅接受 `intents`（1–12 项）、`side`、`scope`、`read_only`。每个子目标 ID 不重复；不要夹带目标 API 答案。复杂需求超过 12 项时分批提交并保留职责清单。

| 子目标字段 | 用法 |
| --- | --- |
| concepts | 可选能力概念 ID 数组；通过 schema 查询，词表由 Wiki 维护 |
| action / subject / object / property / qualifiers | 操作／施动者／作用对象／属性／限定的概念 ID 或数组；明确分配的角色分别核对，未知不填 |
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

默认 JSON 仅保留候选及子目标对应关系。每项 `intents` 用 `id` 关联输入，省略正常状态；出现 `state`（partial、unknown、no_capability_match、timing_review 等）就表示尚未完整解决。`missing`/`missing_roles` 指出缺口。空字段、重复查询、版本与哈希不默认返回；诊断时显式加全局 `--verbose`。

`detail` 默认保留参数、返回、重要备注、组件和紧凑来源路径；返回短 ID，需要完整身份或来源哈希时加 `--verbose`。参数列表为空时省略，原文缺合同会明确标出 documentation_status，不能误当成无参数 API。

`workflows` 返回通用组合步骤、必要 API 和进一步原文路径。恢复、动画接线等能力可能需要完整流程，不强求单个函数。事件族关联仍在 `related` 中返回，不替代指定阶段。默认只补充必要互补能力；确需比较替代路线再增加 per-intent，不能靠无限扩大候选覆盖需求。

明确冲突与未知分开：已核验的端侧、对象或属性冲突不作为支持推荐；未知操作分类不会直接删掉答案。引用概念来自 Wiki 词表，不在 Skill 或调用脚本中复制同义词表。所有接口最终仍读 detail 的合同与限制。
