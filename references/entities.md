# 自定义实体的行为与表现

先决定实体承担的服务端职责，再接客户端外观。能看到模型不代表实体行为已注册。

## 文件与状态链

```text
BP/entities/*.json                       minecraft:entity
  description.identifier
  components / component_groups / events
  （按需）description.properties、spawn_rules、loot_tables
RP/entity/*.json                         minecraft:client_entity，同一 identifier
  geometry / textures / materials / animations / render_controllers
```

1. BP 定义生命、碰撞、运动、AI 与事件；RP 声明模型和表现资源。自然生成另设 `BP/spawn_rules`；可召唤、生成蛋和自然生成是不同能力。
2. `components` 是基础行为；`component_groups` 是待加入/移除的组件集合，定义后不自动激活；`events` 用 add/remove 等响应切换行为。不要假定多个组中的同名组件自动合并或移除后恢复到期望值。
3. AI 同时需要匹配的移动、导航、感知、目标和行为组件；先保留最小行为链，再增加目标选择与互斥条件。`runtime_identifier` 不是继承整份原版实体 JSON 的快捷方式，涉及硬编码特性时才核验它。
4. 区分引擎属性（生命等）、数据驱动 properties、自定义持久化数据及表现变量。需要 RP 读取的 property 使用正确类型/default/range 或 enum values，并核对 `client_sync`；不要沿用早期镜像的旧属性格式。
5. 网易 `SetPropertyValue`、组件调用及事件监听按具体合同接入；客户端自定义 `query.mod.*` 不是天然双端同步。服务端决定业务状态，客户端从明确的属性/消息更新表现。
6. 只在当前问题需要时读取 [渲染](rendering.md)、[动画](animations.md)、[Molang](molang-math.md)；不要把三个模块总是一起加载。
7. 实机区分出生/加载、死亡/移除、区块卸载/销毁。观察重新加载后的 AI、组件组、属性和动画恢复；不要仅监听死亡就清理所有引用。

## 共享实体体系与扩展点

这里始终是一套 BP 行为实体与 RP 客户端实体。优先原版组件、组件组、实体事件、属性、几何和动画；这些已经满足需求时，不引入专用模型或自定义 AI。

确需运行时控制时，在现有实体上按职责接入 ModSDK；确需网易自定义 AI 或专用模型时，只扩展相应行为/表现部分。网易骨骼模型与原版 geometry 的资源和控制接口确有区别，但它们不构成两种独立的实体注册体系。


## 按需原文

- `cn-entity` → `mcguide/20-玩法开发/15-自定义游戏内容/3-自定义生物/01-自定义基础生物.md`：行为定义、组件组、事件、自定义 AI。
- `cn-molang-api` → `mcdocs/1-ModAPI/接口/实体/molang.md`：属性读写的约束。
- `mirror-entity-bp` → `wiki/entities/entity-intro-bp.md`：行为结构；`mirror-entity-rp` → `wiki/entities/entity-intro-rp.md`：表现引用。
- `be-properties` → 国际版固定快照 `docs/entities/entity-properties.md` 的 Defining Properties：当前类型与同步定义。
- `be-runtime-id` → 国际版固定快照 `docs/entities/runtime-identifier.md`：只有确需借用硬编码行为时读取。
