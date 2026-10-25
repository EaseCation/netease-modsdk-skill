# 查询请求协议 4

知识数据仍为 v3；请求协议独立版本化，旧引擎明确报错。`query.py schema` 从运行时字段定义生成清单；`schema <概念词>` 查局部词表，`--all-concepts` 才展开全部概念。不要把下面说明当作另一套字段定义。

根节点接受 intents（1–12 项）、side、scope、read_only。每项 query 非空、id 唯一；超过 12 项分批并保留职责清单。JSON 计划不混用命令行的操作/对象过滤参数。

| 字段 | 决策规则 |
| --- | --- |
| mode | atomic 查单项操作；workflow 查整体接入路线；默认 auto。已知流程的各步允许不同操作，不强迫都匹配最终动作 |
| query | 动作＋对象＋属性/内容＋必要限定；去除无关玩法背景，保留改变答案的条件 |
| kind / side / scope | 见 schema 枚举；事件单列 kind=event；一般继承根节点端侧和范围 |
| operation | 明确填写 read/set/create/delete/play/pause/resume/stop/observe；write 泛指变更，覆盖各类写操作；混合流程省略 |
| target / extent / target_scope / batch | 对象类别、单个/全局/维度范围、本人/其他/全部玩家、批量返回；取值来自 schema |
| concepts | 必需能力概念；缺事实报告缺口，明确冲突才排除 |
| action / subject / object / property / qualifiers | 概念 ID 或数组，明确动作/施动者/作用对象/属性/限定。不要将同一概念随意分配到多个角色 |
| hints | 可选概念线索，仅辅助召回排序，不参与完整覆盖与排除；没有线索就不填 |
| requirements | 尚未建模的关键条件文本数组；始终作为未核验条件返回，需读原文确认，不因词面命中自动满足 |
| read_only | true 限读取/观察，子目标不能解除根节点只读 |
| phase | 仅事件；before/after/change/any。阶段用于排序，取消和字段修改另核验 |
| exclude_targets / exclude | 排除对象类别/能力说明中的精确词组；不是任意逻辑解析器 |
| must_support | 要求正向说明中存在的精确词组；不是同义词检索，证据缺失不证明平台不支持 |

已明确的结构化操作优先于文字推断；AI 须保证两者一致。未指定操作时由 Wiki 共享操作词表辅助识别，多类操作返回 split_required。工作流操作与单 API 共用 write 的上位关系。

默认输出仅保留候选和职责对应关系，正常状态省略。query_incomplete 是未识别核心能力，evidence_missing 是对应事实不足；partial 表示部分已核验。missing、missing_roles 和 unverified 指向仍需核对的概念、合同维度或文字条件。no_capability_match 表示没有推荐候选；均不等同于平台不支持。流程未确认返回 workflow_unverified，不能把其中单个 API 当作完整方案。

匹配只针对已表达的条件；提交和读取结果时均须对照原始需求。候选名称正确不等于生命周期、对象归属和范围正确。替代候选不能合并成完整覆盖，只有有来源的组合关系可以连接步骤。

review 保留取消能力等必要条件尚未核验的入口，不能作为已支持的步骤，也不能解释为不支持；读其合同后再决定。workflows 提供步骤、前置条件和来源；related 是同族关联事件。phase=change 不等于 after，timing_review 不能当作所需阶段已满足。

`--limit` 1–24，`--per-intent` 1–3；默认每职责一个候选再补必要前置，关联事件独立返回，整体受字符预算约束。detail 保留完整合同和紧凑 source，诊断版本、证据和哈希使用 --verbose；缺合同会标明 documentation_status。搜索后批量读必要合同，不先下载整库到上下文。
