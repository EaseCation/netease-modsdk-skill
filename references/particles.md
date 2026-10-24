# 原版粒子 JSON 与脚本控制

先确认需要的是原版粒子系统。网易特效粒子、序列帧和原版粒子使用不同文件与组件，不用“粒子”一个词替代类型。

## 资源到运行实例

`RP/particles/*.json` 定义一个粒子系统：`particle_effect.description.identifier` 是创建时使用的资源 ID；返回的发射器句柄是运行实例 ID，不能互换。纹理放在 RP 对应路径，JSON 引用一般不带图片扩展名。

1. 根为 `format_version` 与 **`particle_effect`**；description 包含 identifier、`basic_render_parameters` 的材质/纹理；components 分别描述发射器和单个粒子。常用格式为 `1.10.0`，不随目标引擎号随意提升。
2. 先选发射速率（瞬时/持续）、最大粒子数、形状、发射器寿命，再定单个粒子的寿命、大小、UV、朝向和运动。`half_dimensions` 是半尺寸。估算持续存活量约为发射速率 × 平均寿命，再受上限等条件约束。
3. 区分发射器与粒子各自的 age/lifetime；动态运动处理速度/加速度，参数化运动直接计算位置。随机外观优先使用创建时生成的随机变量，避免每帧随机引起抖动。需要公式再读 [Molang 与数学](molang-math.md)。
4. 在目标客户端用 `ParticleSystemCompClient` 的 `Create` 或绑定创建接口接入；创建即播放。JSON 中 `looping` 不保证所有创建方式都永远循环：当前 `Create` 合同注明未绑定实体的世界空间发射器只播放一次/一周期后销毁。
5. 需要调整效果时用发射器 `SetVariable`，不要把实体 `query.mod.*` 注册接口当成粒子变量接口。手动发射类型需 `EmitManually`。绑定时核对骨骼/定位器、局部偏移与角度顺序。
6. `Stop` 停逻辑且隐藏，不等于销毁，也可能阻止自然寿命结束；最终释放用 `Remove`。按拥有者记录句柄，在对象销毁/切维度/界面退出等对应时机清理。
7. 资源文件按当前 API 备注避免中文内容；观察多人可见范围、离开重返、远近裁剪、循环结束和移动端数量成本。客户端效果不作为伤害/碰撞权威判定。

## 路线对比

| 能力 | 中国版原版粒子 | 国际版原版粒子 | 限制 |
| --- | --- | --- | --- |
| JSON 发射器、粒子、UV、Molang、曲线与事件 | 支持共享机制 | 同类数据格式 | 单个组件和 query 仍核对版本/上下文 |
| 接入 | ModSDK 创建/绑定/控制句柄；也可接动画效果 | 命令、实体动画/控制器中的效果引用 | 创建渠道决定生命周期，不能只看 JSON |
| 变量 | 发射器变量接口；`variable.emitter_speed` 有网易扩展说明 | 标准发射器/粒子变量 | 网易扩展变量不承诺国际版可用 |
| 网易特效粒子 | 独立系统及 API | 无同名网易资源合同 | 骨骼绑定、生命周期等旧对比须以现有 API 为准 |

## 按需原文

- `cn-particle-build` → `mconline/15-玩法组件教程/16-自定义原版粒子/1-开始制作下雪粒子.md`：发射器、外观、运动。
- `cn-particle-events` → 同目录 `4-了解粒子事件.md`：仅需连锁效果、碰撞或生命周期事件时读。
- `cn-particle-api` → `mcdocs/1-ModAPI/接口/特效/微软粒子.md`：Create、CreateBindEntityNew、SetVariable、Stop、Remove；这些备注优先于早期特效对比文章。
- `mirror-particles` → `wiki/particles/particles.md`：资源机制补充；字段实现仍以具体版本原文为准。
