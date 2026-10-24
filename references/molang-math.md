# Molang 与空间数学

用于表达式、动画/粒子参数和地形函数；只需要查某个 Python 接口时直接查询合同。

## 先确定求值环境

`q./query.` 读取当前环境提供的值；`v./variable.` 保存该对象的变量；`t./temp.` 是临时量；`c./context.` 由调用环境提供。实体、粒子、渲染控制器、特征规则的可用查询和变量不同，不能把一个环境的表达式原样搬到另一个环境。变量也不会因为同名就跨实体、跨端同步。网易自定义节点使用单精度浮点数，不用它保存实体 ID 或要求精确表示的大整数。

简单表达式直接产生值；多条语句用分号隔开，需要返回值时显式 `return`。不要沿用旧镜像“通常不推荐 return”的概括。先用常量连通资源，再增加单个 query，再组合公式；未知 query、未初始化变量和错误上下文分别定位。

## 常用数学契约

| 问题 | 最小公式/原则 | 必须先确认 |
| --- | --- | --- |
| 周期摆动 | `A * math.sin(360 * t / T + phase)` | Molang 三角函数用角度；t、T 同一时间单位，T > 0 |
| 归一化进度 | `u = clamp((t-start)/duration, 0, 1)` | duration > 0；是否循环另行决定 |
| 插值/缓动 | `a+(b-a)*u`；平滑可用 `u*u*(3-2*u)` | 角度跨越 ±180° 时用最短角差/旋转插值 |
| 方向与速度 | `d = target-origin`，非零时 `d/length(d)` | 零向量不归一化；方向、位移、速度是不同量 |
| 局部转世界 | `origin + R*(scale*local)` | 原点、旋转顺序和比例由具体 API 决定，旋转通常不可交换 |
| 世界到区块 | `floor(x/16)`，局部坐标 `x-16*chunkX` | 负坐标不能用向零截断代替 floor |
| 地形连续性 | `base + amplitude*noise(worldX/wavelength, worldZ/wavelength)` | 用世界坐标保持区块接缝连续；波长 > 0；是否受种子影响看 query 合同 |

数学公式是推导说明；具体赋值写法按 Molang 语法。Molang 的角度输入与 Python `math.sin/cos` 的弧度输入不同；换算为 `rad=deg*pi/180`。不要把教程中错误的角度注释照搬到代码。

动画时间、粒子寿命常以秒计；Python API 可能使用秒、帧或 tick，逐项读合同。模型常用 16 单位/格，不把这一尺度应用到 UI 像素、世界坐标或所有组件参数。`~` 是世界轴相对偏移，`^` 是朝向局部坐标；脚部、眼部、骨骼 pivot 和 locator 也不是同一原点。

## 共享表达式与扩展边界

Molang 的基础逻辑和数学语义是一套共享机制；按宿主字段及格式版本检查可用函数。能用标准查询、已声明 property 或局部变量表达的状态，就使用这条路径。

仅在确需 Python 驱动时核验网易客户端 `query.mod.*` 注册/设置或实体属性接口，不能混同自定义 query、属性与普通变量。`SetPropertyValue` 的表达式需无副作用且查询范围受限。粒子和地形的标准变量优先；网易扩展变量只在需要其特定能力时采用。


## 按需原文

- `cn-molang` → `mconline/15-玩法组件教程/11-精通自定义复杂的实体/1-认识Molang.md`：基本概念、查询函数、自定义变量。
- `cn-molang-api` → `mcdocs/1-ModAPI/接口/实体/molang.md`：Register/Set、SetPropertyValue；注册节点仅限其合同规定的端侧和前缀。
- `mirror-math-animation` → `wiki/visuals/math-based-animations.md`：查询值如何驱动骨骼，编辑器预览与游戏上下文的区别。
- `be-molang` → 国际版固定快照 `docs/concepts/molang.md`：Math Functions、Simple vs Complex Expressions、Versioning。
- `ms-math` → 官方固定快照 `creator/Reference/Content/MolangReference/Examples/MolangConcepts/MathFunctions.md`：只查需要的函数，不全读函数表。
