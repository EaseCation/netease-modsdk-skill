# 自定义方块与方块实体

先选注册路线，再选渲染、交互和状态模型。普通方块、方块实体、实体模型不是同一种对象。

## 先用原版，按缺口选扩展

目标包体支持且满足需求时，采用 `BP/blocks` 的标准 minecraft:block 定义，按当前格式声明组件/状态，使用 geometry、material_instances 与 RP 纹理图集接通外观。需要时读取本文末尾的原版格式来源。

只有需要网易独有组件、方块实体等能力，或现有项目明确采用网易 loader 时，才核验并采用以下专用接入；不因运行于中国版就默认选专用目录。

## 网易方块扩展的接入

1. 行为定义放 `BP/netease_blocks/*.json`，根 `minecraft:block`，声明唯一小写 `namespace:id`，按网易合同填写 description 与 components。格式决定字段：旧 `destroy_time` 与较新 `destructible_by_mining` 不能无条件混用。
2. 贴图链是 `RP/blocks.json` 的纹理简称 → `RP/textures/terrain_texture.json` → `RP/textures/blocks/` 的图片。名称用 `RP/texts/zh_CN.lang` 的 `tile.<identifier>.name`。模型路线按其专门文档配置，不把外观当碰撞盒。
3. 分别定义挖掘、掉落、碰撞/选择、方向和光照；不要把某个“实心”开关理解为包含全部行为。红石、容器、流体等按需读专门章节，避免把特殊类型混进基础定义。
4. 少量离散外观/朝向状态与持久化业务数据分别设计。国际版 states/permutations 的数据模型不等同于网易 `netease:block_properties`；后者是具体功能标志，不能拿它注册任意属性。
5. 需要独立持久化数据时核验 `netease:block_entity` 与 `blockEntityData`。tick/client_tick 按需开启，文档规定模拟范围内约 20 次/秒；不要在每个方块 tick 全量扫描或打印。
6. 玩家手动放置和世界生成放置使用不同事件。初始化与交互都先核对维度、坐标、方块类型和数据是否存在。区块卸载后不能长期持有旧数据对象；更改 identifier/卸载包会影响已有存档。
7. 实机检查放置、挖掘、重进、区块卸载重载、不同朝向及多人同时交互；只看物品栏图标不代表方块已完成。

## 实际格式与扩展差异

| 能力 | 原版 1.21.130 路线（优先） | 网易专用路线 | 边界 |
| --- | --- | --- | --- |
| 注册 | `BP/blocks`，标准 `menu_category` 等 | `BP/netease_blocks`，网易 description 字段 | 不能只搬目录而保留另一套完整 schema |
| 基础组件 | 对应版本的标准组件 | 明确列出的 `minecraft:*` 与 `netease:*` | 同名也核对值域；例如光照存在旧浮点格式与新整数格式 |
| 外观 | geometry、material_instances、纹理图集 | blocks.json、纹理图集及网易模型配置 | 现代国际版不宜照抄旧镜像的全套 blocks.json 用法 |
| 自定义状态/变体 | 标准状态和条件组件变体 | 核验目标包体对标准 states/permutations 的具体支持 | 本地网易文档不足以保证完整等价；不据此断言全部不可用 |
| 方块实体与容器 | 不提供同名网易扩展 | 网易扩展及对应 Python 数据/事件能力 | 状态、容器槽位和持久化数据各自核验 |

## 按需原文

- `cn-blocks` → `mcguide/20-玩法开发/15-自定义游戏内容/2-自定义方块/0-自定义方块概述.md`：注册、存档卸载行为。
- `cn-block-components` → 同目录 `1-JSON组件.md`：只读正在使用的组件。
- `cn-block-entity` → 同目录 `4-自定义方块实体.md`：添加、数据与事件。
- `mirror-blocks` → `wiki/blocks/blocks-intro.md`：历史基础说明；版本差异读下项。
- `be-blocks`、`be-block-states` → 国际版固定快照 `docs/blocks/blocks-intro.md`、`docs/blocks/block-states.md`。

API 检索拆成方块读取/写入、玩家交互事件、方块实体数据、容器槽位，保留对象与范围，避免“容器”搜到玩家背包。
