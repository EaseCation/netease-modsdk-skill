# Bukkit 常用能力迁移

用于消息、标题、计分板和基础玩家操作的名称迁移。表左是需求来源，不是 ModSDK 函数名；先确定接收者、显示区域、读写与单位，再 query/detail。直接接口、原生命令和组合步骤分别核验，不假造同名方法。

| 常见需求 | 已核准的入口/组合 | 关键边界 |
| --- | --- | --- |
| sendMessage | 服务端 NotifyOneMessage | 单个玩家聊天框系统消息 |
| broadcastMessage | GetPlayerList 后逐个 NotifyOneMessage | 列表跨维度；不冒充玩家发言 |
| 玩家 chat / 玩家间私聊 | SendMsg / SendMsgToPlayer | 带玩家身份；SendMsg 的不存在名字会触发随机选择 |
| sendTitle / resetTitle | SetCommand 执行 title/titleraw | 中央主副标题、时间、清除/重置 |
| sendActionBar | SetCommand 执行 title/titleraw 的 actionbar | 与 Tip/Popup 分开核验 |
| 快捷栏 Tip/Popup | SetOneTipMessage/SetOnePopupNotice；客户端对应本地接口 | 服务端不带 One 的接口影响全部玩家 |
| 结构化聊天 | SetCommand 执行 tellraw | 使用 Bedrock rawtext，Java 聊天组件不可原样传入 |
| 记分板目标/分数写入/侧边栏 | SetCommand 执行 scoreboard | 读取玩家分数用 GetAllPlayerScoreboardObjects；目标枚举另有接口 |
| getExp / 总经验 | GetPlayerExp(isPercent) / GetPlayerTotalExp | 本级经验、比例、等级、总点数分开；百分比数值范围仍需核验 |
| giveExp / 绝对等级 | AddPlayerExperience；GetPlayerLevel 后按差值 AddPlayerLevel | 负经验扣减不会自动跨级；设置总经验会重新计算等级 |
| getLocation / 同维度 teleport 的坐标部分 | GetFootPos / SetFootPos 或 SetPos | 完整 Location 另查维度/朝向；两个服务端位置写入接口等价，不混同 GetPos 的读取基准 |
| 跨维度 teleport | ChangePlayerDimension | 该接口 pos 为头部位置，脚底会低 1.62；ChangeEntityDimension 不用于玩家 |
| setVelocity | SetPlayerMotion | SetMotion 用于非玩家生物；单位与时序仍查合同 |
| setHealth / setFoodLevel | SetAttrValue + AttrType | HealthLevel/StarveLevel 是阈值；回血上限先读取 |
| addPotionEffect / setFireTicks | AddEffectToEntity / SetEntityOnFire | 前者浮点秒，后者整数秒；从 tick 换算并确定取整 |
| setInvulnerable | ImmuneDamage | 该状态存档 |
| inventory.addItem | SpawnItemToPlayerInv | False 不保证无写入，按实际结果处理剩余量 |
| playSound | 客户端 PlayCustomMusic | 名称含 CustomMusic，但支持原版音效；服务端定向请求需通知客户端 |

## 标题与指令的最小接入

服务端创建 Command 组件后，明确传入执行玩家；接收者另由选择器决定。只作用于该玩家可用 `@s`，全体才用 `@a`，不要省略 entityId 让引擎随机选择执行者。

定向系统通知与指令入口（NotifyOneMessage/SetCommand）的文本在 Python 2.7 调用边界转为 UTF-8 `str`，见 [数据边界](python-boundaries.md)；不推广到所有接口。

```python
command_comp.SetCommand(b'/title @s times 10 40 10', player_id, False)
# 需要副标题时，先用同样方式设置 subtitle，再显示 title。
raw = json.dumps({'rawtext': [{'text': title_text}]}, ensure_ascii=False)  # title_text 为 unicode
cmd = u'/titleraw @s title ' + raw
command_comp.SetCommand(cmd.encode('utf-8'), player_id, False)
```

示意代码需导入 json 并取得组件；不直接拼接未转义的用户文本。title 时间为游戏 tick，与 Python 定时器单位不同。权限、作弊与极限模式限制按实际命令及 SetCommand 备注核验。showOutput 控制命令输出，不是标题可见性的开关。

## 按需原文

- `cn-messages` → Wiki `docs/mcdocs/1-ModAPI/接口/世界/消息.md`；`cn-commands` → 同目录 `指令.md`。参数以 query 的合同为准。
- `ms-title`、`ms-titleraw`、`ms-tellraw`、`ms-scoreboard` → 官方固定快照 `creator/Commands/commands/<同名命令>.md`；只读对应 Usage 子节或参数。

复杂任务仍拆成职责；一个名字命中不代表整个需求已完成。
