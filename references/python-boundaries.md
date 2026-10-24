# Python 与引擎的数据边界

用于中文显示、指令、UI 文本、序列化或持久化异常；这是 Python 2.7 调用规则，不是全部接口的编码承诺。

## 按参数核验，不按“字符串”统推

Python 2.7 的 `str` 是字节串，`unicode` 是文本；本工具的 Python 3 类型规则不能套用到游戏。文档里的 `str` 有时是宽泛描述，不能据此证明接受或拒绝 `unicode`。同一组件、同名方法、不同端侧也不能相互担保。

| 参数/数据角色 | 核验与处理 |
| --- | --- |
| 传入引擎的文本 | 明确要求 UTF-8 或已实测只接收字节串的参数，在调用边界编码；明确支持 Unicode 的按合同处理；其余保持未核实 |
| 引擎返回文本 | 核验实际类型；返回值可能是 `unicode`，不代表下一个接口也接收它。已知编码的字节串先解码再拼接 |
| 标识符、控件路径、资源名称 | 文本类型与允许字符是两项约束；编码正确不代表中文名称、路径或命名空间合法 |
| 字典、列表与序列化数据 | 容器可用不等于嵌套字符串都可用；分别核验键、值、序列化格式和大小单位，不能递归编码所有字段 |

业务层统一使用一种文本表示，通常以 `unicode` 做拼接与格式化；在已确认需要字节串的 API 参数处集中适配。UTF-8 文件头只控制源码解码，不会转换运行时参数。`unicode_literals`、JSON 反序列化、UI 输入及本地化返回值都可能改变类型，ASCII 内容也不保证绑定接受 `unicode`。

```python
# 仅用于已确认要求 UTF-8 字节串的参数；既有 str 须已是 UTF-8。
def engine_utf8(value):
    if isinstance(value, unicode):
        return value.encode('utf-8')
    if isinstance(value, str):
        return value
    raise TypeError('expected text')
```

不使用 `str(unicode_value)` 做编码，不重复编码字节串，不用 `errors='ignore'` 隐藏数据损失，也不全局修改默认编码。处理外部字节串时按已知协议解码，不猜编码。

## 序列化与结果确认

先完成文本拼接、JSON 转义和序列化，再按接收合同编码。`json.dumps(..., ensure_ascii=False)` 的输出不能未经类型检查就传入引擎；`ensure_ascii=True` 只影响 JSON 转义，不证明嵌套对象可被任意 SDK 接收。仅当存储协议允许字符串载荷时，才用 JSON 文本封装并配套反序列化，不擅自把字典参数改成字符串。

无异常不等于成功；无返回值接口的 `None` 也不等于失败。布尔返回值按合同解释，并结合可见效果、回读或事件确认。失败时同时排查类型、端侧、对象有效性、权限与调用时机，不能将所有 `False` 都归因于编码。

目标包体实机核验只覆盖相关边界：同内容的 `unicode` 与 UTF-8 `str`、ASCII 与中文、必要的空文本/特殊字符；记录端侧、参数类型、返回及实际结果。剪贴板或持久化另做回读，必要时重进；一次成功不外推至其他接口、平台或版本。

## 按需查合同

以下相对 Wiki `docs/`，用 query 的 `detail` 或 `section` 阅读对应章节，不全量加载：

- `mcdocs/1-ModAPI/接口/物品.md` → SetCustomName：明确支持 Unicode。
- `mcdocs/1-ModAPI/接口/通用/工具.md` → GetChinese：明确说明 Unicode 返回；SetClipboardContent 仅标 `str`。
- `mcdocs/1-ModAPI/接口/联机大厅.md` → LobbySetStorageAndUserItem：嵌套值的中文明确要求 UTF-8，不用 Unicode。
- `mcdocs/1-ModAPI/接口/世界/消息.md`、`指令.md`、`自定义UI/UI控件.md`：多数文本参数仅标 `str`，仍需结合目标引擎证据。

具体接口差异与实机证据放对应 API 的独立标注或本地维护记录；本页只保留可复用的边界规则，不累计项目故障清单。
