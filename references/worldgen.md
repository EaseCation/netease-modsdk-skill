# 群系、地形生成与特征

先把需求拆成：维度/群系分布、基础地形高度与材料、后处理特征、结构、生物自然生成、客户端环境。需要的是哪一层，就只读那一层的章节。

原版特征、特征规则、群系覆盖/替换等已能满足且目标包体可用时，优先采用。需要网易独有维度群系源、高度节点或大型结构能力时，才沿下面的扩展管线接入；共同的噪声、标识符和后处理概念不因此成为两套机制。

## 需要网易扩展时的生成管线

```text
netease_dimension 的类型/群系源
  → netease_biomes 的群系配置与高度节点
  → netease_features + netease_feature_rules 的后处理
  → 按需大型结构池/规则、spawn_rules
RP 的群系环境定义只处理相应客户端表现
```

1. 在 `BP/netease_biomes/` 按自定义维度组织群系，核对模板继承关系、完整 identifier、标签与维度。使用自定义群系源后，旧 `minecraft:overworld_generation_rules` 不再决定该路线的群系分布。
2. 要改变基础地形，使用文档定义的 `netease:overworld_surface.adjustments` 流水线（fill/move/replace），逐步确定高度区间和材料。当前教程给出自定义高度约 0–256 的范围，不能直接继承国际版主世界的负高度范围。具体边界按目标包体核验。
3. 地形函数使用世界坐标保持接缝连续。高度可写成 `base + amplitude*noise(x/scale,z/scale)`；先限制频率、振幅、范围和计算量，再叠加层数。区块局部随机、每次加载重算且没有稳定输入，可能让接缝或结果不一致。
4. feature 定义“放什么”，feature_rule 定义“在哪种群系、哪个生成阶段、以何种分布放”。目录分别为 `netease_features`、`netease_feature_rules`；保持 identifier、文件名、places_feature 引用匹配。需要具体字段才读 placement_pass、iterations、scatter_chance 和坐标求值顺序。
5. `BP/structures/<namespace>/*.mcstructure` 是结构资产。普通方块特征可能不能正确构造方块实体，按需选结构特征并核对实体/NBT 保留行为。当前网易结构特征文档的尺寸、高度、下界/超平坦限制不能套成所有结构 API 的统一限制。
6. 大型拼接结构另走 `netease_large_feature_pools` 与 `netease_large_feature_rules`，核对起始池、接点、递归深度和终结方式。不要把大片 Python 填方块或每次区块加载时重建当成原生生成器。
7. 修改群系标签用于自然生成筛选，不自动改变客户端雾色；RP 环境配置与服务端地形分别核验。已有区块、未生成区块及卸载/重装后的边界要分别观察；不自动清空用户存档来“验证”。

## 共享能力与实际扩展差异

| 层次 | 原版 1.21.130 能力（优先） | 网易扩展路线 | 能力/限制 |
| --- | --- | --- | --- |
| 群系分布 | 覆盖原版群系；Custom Biomes 实验下部分替换 | 维度群系源及网易节点组合 | 官方资料已提供 replace_biomes；旧镜像“1.18 后全部失效”不能概括目标版本 |
| 基础地形高度 | 原版生成机制和相应群系组件 | 网易高度节点流水线 | feature 散布构成的地形仍是后处理，不等于替换底层生成器 |
| 特征与规则 | features / feature_rules 的标准结构 | netease_features / netease_feature_rules，支持文档列出的原版特征与扩展 | 共同概念可借鉴，路径、阶段、值域及扩展分别核验 |
| 大型结构 | 标准结构及目标版本的拼图配置 | 网易大型特征池/规则 | 不把两套池格式互换，复杂规则按需读原文 |
| 客户端环境 | 对应版本 client biome 定义 | 文档中的 biomes_client 及环境能力 | 天空/水色变更不等于地形/群系分布变更 |

## 按需原文

- `cn-biomes` → `mcguide/20-玩法开发/15-自定义游戏内容/4-自定义维度/2-群系地貌.md`：先按目录选“自定义群系高度”或“自定义群系生成流程”，不通读千行教程。
- `cn-features` → 同目录 `4-自定义特征.md`；`cn-large-features` → 同目录 `6-自定义大型特征.md`。
- `mirror-heightmap` → `wiki/world-generation/heightmap-noise.md`：理解连续噪声/散布；其中高度范围不直接当中国版参数。
- `ms-biomes`、`ms-biome-replacement` → 官方固定快照 `creator/Documents/Biomes/BiomeOverview.md`、`CustomPartialBiomeReplacement.md`：覆盖、实验开关和替换发生的阶段。
- `be-jigsaw` → 国际版固定快照 `docs/world-generation/jigsaw-structures.md`：仅需国际版结构格式比较时读取。
