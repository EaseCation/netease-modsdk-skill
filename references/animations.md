# 动画与动画控制器

用于动作接入、状态切换、动画卡住/重播。纯贴图或模型不可见问题先读 [渲染](rendering.md)。

## 将四层接起来

`RP/models/entity` 的骨骼名 → `RP/animations` 的动画 ID → 实体 description.animations 的简称 → `scripts.animate` 或控制器状态。控制器也需要在 animations 中注册简称并被 animate 启动；仅放入文件夹不会自动执行。

1. 先让一个骨骼播放一个常量关键帧，核对骨骼名、pivot、时间、旋转和 loop；再增加 Molang 或多动作混合。`animation_length`、关键帧位置和单次动作结束条件需要一致。
2. 状态机声明 `initial_state`，缺省通常为 `default`。每个控制器同一时刻只有一个活动状态；状态内可播放多个动画。多个独立控制器可同时运行。
3. `transitions` 按顺序寻找首个满足条件的转移；不要把多个条件同时为真理解为同时进入多个状态。需要终止状态、打断优先级或防抖时明确建模。
4. `on_entry/on_exit` 表示进入/离开，不是每帧回调。一次性音效/粒子放在确切事件点；持续动作写在状态动画或正确寿命的效果中。`blend_transition` 平滑姿态，不自动修复业务状态。
5. 区块重载或实体重新加载可能让控制器回到初始状态。需要恢复的状态从稳定的实体属性/已同步状态重建，不能只存在控制器瞬时状态里。RP 动画结束不等于服务端业务完成。
6. RP 控制器用于骨骼/音效/粒子表现；BP 控制器处理其支持的实体事件/命令。业务规则仍按服务端权威实现。检查实际触发端、实体重载、循环边界、连续打断和多控制器混合。

## 共享动画与扩展边界

原版动画、动画控制器和 `scripts.animate` 使用同一套共享机制，优先由已有查询、属性和实体事件驱动。常量、关键帧或 Molang 已能表达的动作，不为了播放它而增加专用模型系统。

只有缺少运行时驱动能力时再核验 ModSDK 节点/表现接口。网易骨骼模型的动作接口属于另一套模型资源系统，不能把它套到原版动画上；选择这种扩展也不改变共享实体的身份。


## 按需原文

- `cn-entity` → `mcguide/20-玩法开发/15-自定义游戏内容/3-自定义生物/01-自定义基础生物.md`：4.自定义动画、5.自定义动画控制器、8.资源包实体定义。
- `mirror-ac` → `wiki/animation-controllers/animation-controllers-intro.md`：附加控制器、RP/BP 区别；旧译“同时转移多个状态”应按上述运行顺序理解。
- `be-ac` → 国际版固定快照 `docs/animation-controllers/animation-controllers-intro.md`：Animation Controller Flow、Resetting。
- `mirror-animation-effects` → `wiki/visuals/animation-effects.md`：只在需要关键帧效果与 locator 时读取。
