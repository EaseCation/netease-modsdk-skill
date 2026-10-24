# 几何、材质与渲染控制器

用于实体/附着物的视觉资源接线、变体和显示问题。先让单模型、单材质、单纹理工作，再增加条件与层次。

## 资源引用关系

```text
RP/entity/*.json 的 minecraft:client_entity.description
  identifier                         对应 BP 实体标识符
  geometry.default → geometry.*      指向模型内部 ID，不是文件路径
  textures.default → textures/...    指向纹理路径，一般无扩展名
  materials.default → 材质 ID
  render_controllers → controller.render.*
RP/render_controllers/*.json
  Geometry.default / Texture.default / Material.default
```

1. 核对 BP/RP identifier 一致，模型位于 `RP/models/entity/`，几何内部 ID 和 bone 名与引用一致。先检查解析日志，再检查相机范围、可见边界和实体是否存在。
2. 渲染控制器消费实体文件声明的简称；在控制器里写对一个资源文件名，并不能代替实体中的简称声明。相同简称可让不同实体复用一个控制器。
3. 多皮肤/模型用数组与受控索引或条件选择；先约束索引范围和输入含义。骨骼显示通过对应的可见性字段；材质映射按骨骼匹配。多个控制器可能多次绘制模型，需要明确哪部分各自负责。
4. 透明、裁切、自发光和纹理分层依赖材质。纹理数组不是任意叠加万能机制；只有支持对应通道/混合的材质才会产生预期效果。先使用目标包体已有的适当材质。
5. 模型动画改变骨骼变换；渲染控制器选择如何绘制；碰撞盒属于行为/物理侧。不要通过改变模型尺度推断碰撞和服务端位置已同步变化。
6. 网易运行时修改玩家表现时，按合同完成资源注册/更新及必要的重建，避免每帧重建。原版 geometry 与网易骨骼模型的导出和 API 路线分别选择。

## 路线对比

| 能力 | 中国版 | 国际版 | 限制 |
| --- | --- | --- | --- |
| client_entity 与控制器简称 | 共享原版资源机制 | 共享 | 资产、简称和内部 ID 各自核对 |
| 纹理/几何条件变体 | 原版控制器及相应 ModSDK 表现能力 | JSON 控制器 | 渲染输入不自动改变服务端行为 |
| 网易骨骼模型/动作系统 | 有独立资源与接口 | 无同名网易格式合同 | 不混用几何文件与模型组件 |
| 自定义材质/着色器 | 受当前渲染后端和文档限制 | 受目标渲染后端限制 | 旧 OpenGL 材质教程不能直接证明其他后端可用 |

需要动画转移时再读 [动画](animations.md)；需要坐标推导时读 [Molang 与数学](molang-math.md)。

## 按需原文

- `cn-entity` → `mcguide/20-玩法开发/15-自定义游戏内容/3-自定义生物/01-自定义基础生物.md`：6.自定义模型、7.自定义渲染控制器、8.资源包实体定义。
- `mirror-render` → `wiki/entities/render-controllers.md`：简称、复用和纹理分层。
- `be-entity-rp` → 国际版固定快照 `docs/entities/entity-intro-rp.md`：Geometry、Render Controllers、Animations。
