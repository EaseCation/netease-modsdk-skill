---
name: netease-modsdk-skill
description: 为网易我的世界中国版 Addon 开发按需查阅工程结构、JSON UI、粒子、实体物品方块、Molang 动画及世界生成教程，并查询 ModSDK Python API、事件与枚举；核对原版共享能力及网易扩展的适用边界。不负责游戏启动、构建或发布。
---

# ModSDK 开发知识

先确认任务的目标包体、产物和当前阶段。默认普通 Addon；只有用户明确要求时才研究 Preset。优先目标包体可用且满足需求的原版共享能力、格式与接口；只有明确缺口才使用网易扩展，并记录扩展解决的职责。确需脚本时使用 ModSDK Python；资源和行为 JSON 与脚本合同分开核验。

## 先路由，再读取

只查一个 API：读 [API 查询](references/api-query.md)，无需先读模块教程。涉及文件放置、资源接线、实现方案或跨版迁移：从下表选择当前阻塞点，一次通常读一篇；确有依赖再追加。不要顺序通读本表。

| 当前要解决的问题 | 读取 |
| --- | --- |
| 新建组件、BP/RP、Python 入口、端侧职责与分层 | [工程结构](references/foundations.md) |
| JSON UI 布局、定义清单、Python 绑定与生命周期 | [UI](references/json-ui.md) |
| 原版粒子 JSON、资源接入和发射器脚本控制 | [粒子](references/particles.md) |
| 表达式、变量作用域、角度/时间/坐标与数学驱动 | [Molang 与数学](references/molang-math.md) |
| 动画接线、状态机、转移与生命周期 | [动画与控制器](references/animations.md) |
| 几何、纹理、材质简称及渲染控制器 | [渲染](references/rendering.md) |
| 自定义方块及方块实体 | [方块](references/blocks.md) |
| 自定义实体行为、资源及状态同步 | [实体](references/entities.md) |
| 自定义物品、贴图、持有表现与使用流程 | [物品](references/items.md) |
| 新维度注册、传送与存档边界 | [维度](references/dimensions.md) |
| 群系、地形高度、特征规则与大型结构 | [世界生成](references/worldgen.md) |
| 合成、掉落、交易或生物自然生成的 JSON 接线 | [数据表](references/data-tables.md) |
| 跨端通信、状态保存、重进恢复与资源释放 | [状态与生命周期](references/state-sync.md) |
| 已有故障定位、性能与实机验收范围 | [排错与性能](references/diagnostics.md) |
| 中外版迁移、格式版本或资料相互矛盾 | [版本与证据](references/versions.md) |

规划阶段先输出职责和资源引用关系；实现阶段只补当前文件/字段的原文；调试阶段沿加载、标识符、引用、生命周期逐层定位；验收阶段列出当前变更需要观察的游戏行为。文件检查和文档检索不算实机验收。

## 继续查证与控制上下文

模块页给出共享机制、必要的扩展边界、实施顺序及原文路径。实体等共享体系不按国别拆成两套；仅对真实分叉的格式、目录或模型系统作比较。仅当具体字段、限制或示例仍不确定时，按 [原文读取](references/reading.md) 读取对应章节。API 签名通过 query 的批量 detail 获取；不要用宏观教程代替合同。

在当前任务中保留一份简短工作记忆：目标版本、已选路线、标识符与端侧、已核验 API/来源章节、待解决问题。阶段切换时保留这些结论与路径，不重复粘贴长原文；重复读取只用于版本变化或新问题。输出超过预算时缩小章节或分页，不删掉限制后声称已核验。

首次需要原文/API 时运行 `python3 <技能目录>/scripts/setup.py --check`。已有 Wiki 可用 `--wiki-root /实际路径` 绑定；缺少时运行 `setup.py`，已有受管副本用 `--update`。仅需 Python 3.9+ 和 Git；配置由本技能 `.env`/环境变量指定。安装细节见 [README](README.md)，不要求为阅读短指引先下载全站。
