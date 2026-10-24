# JSON UI 接入

用于布局、Python 绑定或界面失效定位；只改文字/尺寸时不扩展到整个 UI 框架。

## 最短加载链

```text
RP/ui/_ui_defs.json → RP/ui/<界面>.json
JSON namespace.screen → RegisterUI 的 uiScreenDef
Python 类路径 → ScreenNode 子类 → UI 实例 → 控件树
```

1. 在 `RP/ui/` 放界面 JSON，根对象设置唯一 `namespace`，其中画布与可继承模板是命名节点。`controls` 是子节点对象的数组；`实例名@命名空间.模板名` 创建继承实例。
2. `RP/ui/_ui_defs.json` 使用 `{"ui_defs":["ui/acme_panel.json"]}`。路径相对 RP 根且含扩展名；各包清单会合并，只登记新增文件，不复制全部原版清单。
3. 先连通一个最小画布与控件，再增加模板、贴图、锚点、尺寸和层级。`$变量`、`#绑定`、`namespace.control`、Python 控件路径是四种不同标识，不能替换着用。UI 表达式也不是 Molang。
4. 客户端监听 `UiInitFinished`，先 `RegisterUI(namespace, key, clsPath, uiScreenDef)`，再选择 `CreateUI` 或 `PushScreen`。同一 UI 的注册关系只建立一次，与具体实例生命周期分开；切维度可能再次触发初始化，创建逻辑需识别旧实例失效，避免重复绑定。
5. `CreateUI` 的 HUD/输入参数与 `PushScreen` 的参数不相同。菜单栈用 `PushScreen/PopScreen`，并核对 JSON 的 `is_showing_menu`；HUD 按 `CreateUI` 合同配置。不要混用关闭方式。
6. 在 `ScreenNode.Create` 后获取 `GetBaseUIControl(path)`，转换为正确控件类型后修改。静态模板参数用 `$`；动态展示可用控件 API，列表/集合或声明式刷新按需读数据绑定章节。按钮只提交意图，涉及物品和权限的操作由服务端确认。
7. 依次排查：文件登记 → namespace/画布名 → Python 类路径 → 初始化事件 → 控件真实路径/类型 → 可见性、尺寸、锚点、层级与输入拦截。实机观察不同屏幕比例、触摸、重复打开关闭与切维度。

## 路线对比

| 能力 | 中国版 | 国际版 JSON UI | 限制 |
| --- | --- | --- | --- |
| 布局、模板继承、`_ui_defs`、变量/绑定 | 共享核心语法 | 修改仍使用 JSON UI 的屏幕 | 原版控件/绑定名称须核对目标包体 |
| 自建交互画布 | ModSDK `ScreenNode`、注册与创建 API | 资源包定义控件并接到引擎已有屏幕/绑定 | 没有等价的网易 Python 画布注册入口 |
| 改原生 HUD | 支持相应文件/控件和原生界面接入能力 | 使用 JSON UI 修改/扩展对应屏幕 | 整文件覆盖易与其他包冲突，优先最小修改 |
| 其他 UI 技术 | 本指引使用已核验 JSON UI 路线 | 部分屏幕迁移到其他 UI 实现 | 不能据旧镜像的“即将弃用”推断中国版当前不可用，也不能假定所有原生屏幕可改 |

查询合同时分别处理创建/关闭、控件读写、点击事件和刷新职责，限定客户端；同时阅读关联生命周期事件。

## 按需原文

- `cn-ui` → `mcguide/18-界面与交互/30-UI说明文档.md`：文件目录、`_ui_defs`、命名空间、继承控件。
- `cn-ui-bind` → `mcguide/18-界面与交互/70-UI数据绑定.md`：需要集合、列表或动态绑定时再读。
- `cn-ui-api` → `mcdocs/1-ModAPI/接口/自定义UI/通用.md`：RegisterUI、CreateUI、PushScreen、PopScreen。
- `mirror-ui` → `wiki/json-ui/json-ui-intro.md`：操作符、变量、数据绑定、按钮映射、修改操作；不要一次读取全文。
- `be-ui` → 国际版固定快照 `docs/json-ui/json-ui-intro.md`：仅遇屏幕实现差异时读取 Introduction。

教程中基于界面预设/逻辑零件的流程不属于默认路线。
