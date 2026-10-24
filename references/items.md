# 自定义物品

先选网易专用物品格式或经目标包体核验的标准格式；同名 `minecraft:item` 不代表整份定义能混用。

## 网易路线的最短接线

`BP/netease_items_beh` 行为定义 ↔ 相同 identifier 的 `RP/netease_items_res` 表现定义 → `RP/textures/item_texture.json` 的纹理简称 → `textures/items/` 图片。显示名通常为 `item.<identifier>.name`，写入 `texts/zh_CN.lang`。

1. 在行为定义中声明唯一的小写命名空间 ID、分类与组件；需要武器、盔甲、桶、盾牌等专门类型时核对 `custom_item_type` 与对应组件。基础网易教程指定 `format_version: "1.10"`，这不是说游戏只支持旧引擎。
2. 行为/表现 identifier 必须一致；表现 category 与行为一致或按合同省略。网易路线的 icon、use_animation 等表现字段可能位于资源包，不能照搬现代标准物品的字段位置。
3. 先验证可获取、名称、图标、堆叠和基本使用，再增加耐久、食物、冷却、配方、掉落与交易。配方有自己的文件/格式，不能由物品定义自动推导。
4. 背包图标、手持平面贴图、第三人称附着物和第一人称模型分别接线。3D 表现需要时再读 attachable/动画资源；仅配置 icon 不会自动产生完整 3D 装备。
5. 使用前拦截、使用中、使用后是相关但不同的事件。查询时保留整个事件族，选定真正负责取消/修改的阶段。消耗和发放都由服务端核验，避免重复事件导致多次结算。
6. 实机覆盖手持/副手、连续使用、堆叠分拆、耐久耗尽、容器转移和重进；仅测创造栏出现不足以确认完成。

## 路线对比

| 能力 | 中国版网易路线 | 国际版 1.21.130 数据格式 | 边界 |
| --- | --- | --- | --- |
| 注册 | netease_items_beh + netease_items_res | `BP/items`，标准 description/components | 两套 loader、字段位置和分类结构分别核对 |
| 纹理 | RP 表现定义关联 item_texture | 标准 item 的 icon 关联 RP 图集 | 图集机制相通，icon 的写法/位置有版本差异 |
| 武器、耐久、食物、冷却 | 网易专门类型及支持组件 | 对应版本标准组件 | `max_damage`/durability、旧 use_duration/新 use_modifiers 等不机械改名 |
| 新版专门组件 | 是否可用须有目标包体或网易文档依据 | 1.21.130 增加 kinetic_weapon、piercing_weapon 等 | 不能仅凭基岩版本号将其认定为网易专用物品格式已支持 |
| 3D 持有表现 | 原版附着物路线及网易专门方案 | attachable/geometry/动画路线 | 选择资源和接口属于同一模型体系 |

## 按需原文

- `cn-items` → `mcguide/20-玩法开发/15-自定义游戏内容/1-自定义物品/1-自定义基础物品.md`：注册、格式及当前组件。
- `cn-items-3d` → 同目录 `9-自定义3D物品/1-自定义3D物品（一）.md`：仅需 3D 表现时读。
- `mirror-attachables` → `wiki/items/attachables.md`：装备资源接线。
- `be-items` → 国际版固定快照 `docs/items/items-intro.md`：Registering Items、Applying Textures。
- `be-item-history` → 同快照 `docs/items/item-format-history.md`：只读涉及的版本章节，不沿用已移除的旧物品事件写法。
