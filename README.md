# AstrBot 消息等待与合并插件

`message_waiter` 是一个用于改善 AstrBot 连续对话体验的插件。它会在用户发送消息后先等待一小段时间；如果同一用户继续发送内容，则重新计时，并把这些文本合并为一条完整输入后再交给 AstrBot 的默认 AI 流程。

这可以避免用户习惯分段发送时，机器人在第一句话刚发出后就立即抢答。

## 功能特性

- **静默等待**：用户停止输入达到指定时间后，才允许 AstrBot 开始回复。
- **连续消息合并**：同一用户在等待窗口内发送的多段文本会以换行符合并。
- **自动重新计时**：每收到一条新的连续消息，静默等待计时都会重置。
- **私聊会话隔离**：不同私聊会话之间互不影响。
- **群聊用户隔离**：同一群内不同用户的消息不会被错误合并。
- **群聊连续输入支持**：第一条消息正常唤醒机器人后，同一用户紧接着发送的未 `@` 消息也可以加入本轮合并。
- **命令直接放行**：默认不延迟 `/help`、`!help` 等命令消息。
- **可选语义完整性判断**：可调用 AstrBot 已配置的模型，判断用户是否像是还没有说完，并在必要时追加一次等待。
- **无额外第三方依赖**：仅使用 Python 标准库与 AstrBot 提供的 API。

## 使用效果

假设静默等待时间设置为 `2.5` 秒。

用户连续发送：

```text
帮我写一个 Python 函数
输入是一个整数列表
返回其中所有偶数的平方
```

在没有本插件时，AstrBot 可能会在第一条消息后立即开始回复。

启用本插件后，只要这些消息的间隔均小于 `2.5` 秒，插件就会把它们合并为：

```text
帮我写一个 Python 函数
输入是一个整数列表
返回其中所有偶数的平方
```

然后仅让最后一条消息继续进入 AstrBot 的默认 AI 处理流程，因此通常只会产生一次完整回复。

## 工作原理

1. 插件以较高优先级接收消息事件。
2. 第一条符合条件的消息到达后，插件为当前会话启动静默计时。
3. 如果等待期间同一用户又发送了文本：
   - 旧消息事件会被停止；
   - 新文本会加入当前缓存；
   - 静默计时会从头开始。
4. 用户停止发送达到 `wait_seconds` 后，插件将缓存文本以换行符合并。
5. 如果启用了语义判断，插件会额外调用一次模型判断消息是否完整；若模型判定为未完成，则追加一次等待。
6. 最后一条消息事件携带合并后的文本，继续进入 AstrBot 原有的 AI 回复链路。

插件不会自行生成聊天回复，也不会替换 AstrBot 的默认模型、提示词或 Agent 流程。

## 运行要求

- AstrBot：`>=4.16,<5`
- Python：兼容 Python 3.10 及以上语法环境
- 第三方 Python 包：无

### 依赖检查结果

当前源码使用的导入如下：

| 来源 | 模块或对象 | 安装方式 |
| --- | --- | --- |
| Python 标准库 | `asyncio` | Python 自带 |
| Python 标准库 | `contextlib` | Python 自带 |
| Python 标准库 | `dataclasses` | Python 自带 |
| AstrBot 宿主 | `AstrBotConfig`、`logger` | 由 AstrBot 提供 |
| AstrBot 宿主 | `AstrMessageEvent`、`filter` | 由 AstrBot 提供 |
| AstrBot 宿主 | `Context`、`Star`、`register` | 由 AstrBot 提供 |

因此，安装本插件时**不需要手动执行额外的 `pip install` 命令**。仓库中的 `requirements.txt` 用于明确声明当前没有第三方 PyPI 依赖。

## 安装方法

### 方法一：通过 AstrBot WebUI 安装

1. 打开 AstrBot WebUI。
2. 进入插件管理页面。
3. 选择从 Git 仓库安装插件。
4. 填入仓库地址：

   ```text
   https://github.com/XuShan0425/astrbot_message_waiter
   ```

5. 等待安装完成，然后重载插件或重启 AstrBot。
6. 在插件配置页面中启用“消息等待与合并”。

不同 AstrBot 版本的按钮名称可能略有差异。如果 WebUI 无法通过网络访问 GitHub，可以改用手动安装。

### 方法二：手动克隆

进入 AstrBot 的插件目录后执行：

```bash
cd AstrBot/data/plugins
git clone https://github.com/XuShan0425/astrbot_message_waiter.git
```

完成后，在 WebUI 中重载插件，或重启 AstrBot。

推荐保持目录结构类似：

```text
AstrBot/
└── data/
    └── plugins/
        └── astrbot_message_waiter/
            ├── main.py
            ├── metadata.yaml
            ├── _conf_schema.json
            ├── requirements.txt
            └── README.md
```

### 方法三：下载压缩包

1. 从 GitHub 下载仓库 ZIP 文件。
2. 解压到 AstrBot 的 `data/plugins/` 目录。
3. 确保 `main.py` 和 `metadata.yaml` 位于插件目录的第一层，而不是多嵌套了一层同名目录。
4. 重载插件或重启 AstrBot。

## 配置说明

插件安装后，可在 AstrBot WebUI 的插件配置页面修改以下选项。

| 配置项 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `enabled` | 布尔值 | `true` | 是否启用消息等待与合并。关闭后消息会按 AstrBot 原有流程直接处理。 |
| `wait_seconds` | 浮点数 | `2.5` | 每次收到消息后等待用户继续输入的静默时间。新消息到达时重新计时。 |
| `max_wait_seconds` | 浮点数 | `10.0` | 语义判断认为消息未完成时，限制固定等待与追加等待的配置上限。仅在启用语义判断后生效。 |
| `ignore_commands` | 布尔值 | `true` | 是否让命令消息绕过等待。建议保持开启。 |
| `command_prefixes` | 字符串列表 | `["/", "!"]` | 以这些前缀开头的消息会被视为命令并直接放行。 |
| `semantic_check` | 布尔值 | `false` | 是否调用模型判断消息在语义上是否完整。开启后会增加延迟和模型用量。 |
| `semantic_provider_id` | 字符串 | 空 | 指定用于语义判断的模型提供商。留空时尝试使用当前会话正在使用的提供商。 |
| `semantic_min_chars` | 整数 | `6` | 合并文本达到该字符数后才执行语义判断，过短消息只进行固定等待。 |
| `semantic_extend_seconds` | 浮点数 | `2.0` | 模型判定消息未完成时追加的等待时间。当前每轮最多追加一次。 |

### 固定等待与语义判断的区别

#### 仅使用固定等待（默认）

插件只根据消息之间的时间间隔判断用户是否发送完毕：

- 优点：不消耗额外 Token，速度稳定，不依赖模型判断。
- 缺点：如果用户停顿时间超过等待窗口，AstrBot 仍会开始回复。

#### 启用语义判断

达到基础静默时间后，插件会让一个已配置的 AstrBot 模型把合并文本分类为“完整”或“未完整”：

- 完整：立即继续默认 AI 流程。
- 未完整：再等待 `semantic_extend_seconds` 秒。
- 判断调用失败：记录警告并安全放行消息，不阻断正常聊天。

语义判断只会追加一次等待，不会无限循环调用模型。

> 开启语义判断后，每轮符合字符数条件的消息最多会增加一次额外模型请求。请留意模型费用、Token 用量、速率限制与响应时间。

## 推荐配置

### 日常使用

适合大多数聊天场景：

```json
{
  "enabled": true,
  "wait_seconds": 2.5,
  "ignore_commands": true,
  "semantic_check": false
}
```

### 经常分多段输入

如果用户经常停顿一两秒后继续发送：

```json
{
  "enabled": true,
  "wait_seconds": 4.0,
  "ignore_commands": true,
  "semantic_check": false
}
```

等待时间越长，越容易收集完整消息，但每次正常回复前的延迟也会相应增加。

### 使用语义完整性判断

```json
{
  "enabled": true,
  "wait_seconds": 2.0,
  "max_wait_seconds": 8.0,
  "semantic_check": true,
  "semantic_provider_id": "",
  "semantic_min_chars": 6,
  "semantic_extend_seconds": 3.0
}
```

建议先确认当前会话已配置可用的聊天模型提供商。如果留空自动选择失败，可在 WebUI 中明确选择 `semantic_provider_id`。

## 私聊行为

- 缓存键使用 AstrBot 的统一会话标识。
- 同一私聊中的连续文本会被合并。
- 不同私聊会话互不影响。
- 空文本不会进入缓存。

## 群聊行为

- 第一条消息仍需按照 AstrBot 当前规则正常唤醒机器人，例如 `@机器人`、使用唤醒词或触发相应规则。
- 第一条消息建立等待缓存后，同一用户紧接着发送的后续文本即使没有再次 `@机器人`，也会加入本轮缓存。
- 缓存按“群会话 + 发送者 ID”隔离，同一群中不同用户的消息不会合并到一起。
- 最终合并事件会被标记为已唤醒，以便继续进入 AstrBot 默认 AI 链路。
- 如果某条群消息本身不能唤醒机器人，并且该用户当前也没有等待中的缓存，插件不会接管该消息。

## 命令消息

默认情况下，以下消息不会等待或合并：

```text
/help
/plugin list
!help
```

如需修改命令前缀，可编辑 `command_prefixes`。例如只保留 `/`：

```json
{
  "command_prefixes": ["/"]
}
```

如果希望命令也参与等待，可以关闭 `ignore_commands`，但这可能让管理命令或插件命令的响应变慢。

## 已知限制

1. **只合并纯文本**
   插件会修改最终事件的文本内容，但不会把旧事件中的图片、语音、视频、文件或其他消息组件复制到最终事件。

2. **图文上下文应尽量一次发送**
   如果媒体内容对问题很重要，建议将媒体和相关文字放在同一条消息中发送。

3. **语义判断不是绝对准确**
   判断结果取决于所选模型。模型可能误判用户是否已经说完，因此固定等待仍然是主要机制。

4. **语义判断期间的新消息仍以最新输入为准**
   新消息会取消旧的等待任务并重新计时，旧消息事件不会继续调用 AI。

5. **插件只处理本轮实时事件**
   它不是长期会话存储，也不会在 AstrBot 重启后恢复尚未释放的消息缓存。

6. **回复延迟是设计行为**
   即使用户只发送一条完整消息，也至少需要等待 `wait_seconds` 后才会进入默认回复流程。

## 常见问题

### 插件安装后没有生效

请依次检查：

1. 插件是否已在 WebUI 中启用。
2. 配置项 `enabled` 是否为 `true`。
3. 安装目录第一层是否直接包含 `main.py` 和 `metadata.yaml`。
4. 是否已经重载插件或重启 AstrBot。
5. AstrBot 版本是否满足 `>=4.16,<5`。
6. AstrBot 日志中是否有插件加载错误。

### 每条消息还是分别回复

- 确认连续消息间隔小于 `wait_seconds`。
- 确认这些消息来自同一个私聊会话，或群聊中的同一位用户。
- 如果消息以 `/` 或 `!` 开头，它们默认会直接放行。
- 群聊中的第一条消息必须先正常唤醒机器人。

### 回复等待太久

- 调低 `wait_seconds`。
- 如果启用了语义判断，调低 `semantic_extend_seconds`，或直接关闭 `semantic_check`。
- 检查用于语义判断的模型提供商是否响应过慢。

### 开启语义判断后日志出现警告

插件在模型不可用、Provider 选择失败或请求异常时会安全放行消息。请检查：

- AstrBot 是否配置了可用的模型提供商。
- `semantic_provider_id` 指向的提供商是否存在且可用。
- 模型服务的网络、额度和速率限制是否正常。

### `/help` 等命令也被延迟

确认：

```json
{
  "ignore_commands": true,
  "command_prefixes": ["/", "!"]
}
```

如果使用其他命令前缀，请把它加入 `command_prefixes`。

## 开发与验证

本插件遵循 AstrBot 插件结构，主要文件如下：

```text
main.py            插件逻辑
metadata.yaml      插件元数据和 AstrBot 版本范围
_conf_schema.json  WebUI 配置定义
requirements.txt   Python 第三方依赖声明
README.md          使用文档
```

提交代码前建议执行：

```bash
ruff format .
ruff check .
python -m compileall -q main.py
```

如需在 AstrBot 本体中调试，可将仓库克隆到 `AstrBot/data/plugins/`，启动 AstrBot 后通过 WebUI 重载插件。

## 数据与隐私说明

- 固定等待模式只在进程内短暂缓存消息文本，不写入插件目录或独立数据库。
- AstrBot 或插件卸载、重载时，未释放的等待任务会被取消。
- 启用语义判断后，合并文本会发送给所选 AstrBot 模型提供商进行完整性分类；请根据所使用模型服务的隐私政策决定是否开启。

## 仓库与问题反馈

- GitHub 仓库：<https://github.com/XuShan0425/astrbot_message_waiter>
- 问题反馈：<https://github.com/XuShan0425/astrbot_message_waiter/issues>

提交问题时，建议附上 AstrBot 版本、消息平台、插件配置（请移除密钥）以及相关错误日志。

## 许可证

当前仓库暂未提供独立的 `LICENSE` 文件。使用、修改或分发前，请先联系仓库作者确认授权范围。
