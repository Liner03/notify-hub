# 消息聚合通知

轻量的 Python 通知框架：多渠道推送 + 防爆策略（去重/冷却/限流/聚合）。

## 特性

- 单一入口：`notify.send(raw_content, ...)`
- 多渠道：企业微信 / Telegram / 飞书 / Bark
- 防爆策略：dedupe / cooldown / rate_limit / aggregate
- 配置加载：支持 YAML + 环境变量 `${VAR}`

## 快速开始

安装依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

推荐使用配置文件：

`notify.yaml`：

```yaml
notify:
  channels:
    - type: bark
      key: "${BARK_KEY}"
      server: "https://api.day.app"
      title: "Notice"
      group: "demo"
```

代码使用：

```python
from notify import Notify
notify = Notify.from_config("notify.yaml")

notify.send(
    "hello from notice",
    notify_level="info",
)
```

## API

`Notify.send(raw_content, type="text", notify_level="info", event_key=None, source=None)`

- `raw_content`：消息内容（必填）
- `type`：内容类型（默认 `text`；不同渠道会自动降级）
- `notify_level`：事件等级（用于策略；`fatal/error/warn/info`）
- `event_key`：事件唯一标识（可选，未传自动生成）
- `source`：来源标识（可选）

说明：渠道相关参数仅在渠道配置中设置，`send()` 不接受渠道参数。

## 支持的渠道

| 渠道 | type | 说明 |
| --- | --- | --- |
| `telegram` | `text/markdown/html` | Bot `sendMessage` |
| `wecom` | `text/markdown` | 机器人 webhook |
| `feishu` | `text/markdown` | `markdown` 默认交互卡片 |
| `bark` | `text/markdown` | Bark 推送（支持自建服务端） |

## 渠道配置（YAML）

渠道在 `notify.yaml` 的 `notify.channels` 下配置；每个渠道项至少包含 `type`。

```yaml
notify:
  channels:
    - type: telegram
      token: "${TG_TOKEN}"
      chat_id: "${TG_CHAT_ID}"

    - type: wecom
      webhook: "${WECOM_WEBHOOK}"

    - type: feishu
      webhook: "${FEISHU_WEBHOOK}"

    - type: bark
      key: "${BARK_KEY}"
      server: "https://api.day.app"  # 自建服务端可改为 http://your-host:port
```

对应字段说明：

- `telegram`：`token/chat_id`（可选：`name/timeout/parse_mode`，其余 `sendMessage` 参数可直接加在配置里）
- `wecom`：`webhook`（可选：`name/timeout/mentioned_list/mentioned_mobile_list/extra`）
- `feishu`：`webhook`（可选：`name/timeout/extra`）
- `bark`：`key/server`（可选：`name/timeout/level/level_map/...`）

## Bark

官方文档：`https://bark.day.app/#/tutorial`

渠道配置：

```yaml
- type: bark
  key: "${BARK_KEY}"
  server: "https://api.day.app"  # 自建服务端可改为 http://your-host:port
  title: "告警"
  group: "ops"
  level: "timeSensitive"
```

常用配置项：

- `title/subtitle/body`
- `level`：推送中断级别（`active/timeSensitive/passive/critical`）
- `icon/image/sound/call/badge/group/url`
- `copy/autoCopy/isArchive/ciphertext/id/delete/action/volume`
- `level_map`：按 `notify_level` 映射推送中断级别（可选）

如需发送 Markdown，调用 `send(..., type="markdown")`。

注意：事件等级使用 `notify_level`（策略用），Bark 中断级别使用 `level`（推送用）。

## 配置加载

```python
from notify import Notify

notify = Notify.from_config("notify.yaml")
notify.send("task_id=123", notify_level="error")
```

环境变量支持 `${VAR}` 替换，示例见 `notify.yaml.example`。

## 策略配置

策略在 `notify.yaml` 的 `notify.policies` 下配置：

```yaml
notify:
  policies:
    dedupe:
      ttl: 3600
      levels: ["fatal", "error"]
      upgrade_after: 10
    cooldown:
      ttl: 21600
      levels: ["fatal"]
    rate_limit:
      per_minute: 30
      levels: ["fatal", "error", "warn"]
      scope: global  # global/event_key/level
    aggregate:
      window: 3600
      levels: ["warn"]
      max_samples: 5
```

## 扩展渠道

实现新渠道：继承 `BaseNotifier`，覆写 `config()` 声明必填/默认参数，并注册到 `NotifierRegistry`。

```python
from notify.channels.base import BaseNotifier, REQUIRED
from notify.core.registry import NotifierRegistry


class DingTalkNotifier(BaseNotifier):
    type_name = "dingtalk"
    supported_types = {"text", "markdown"}

    @classmethod
    def config(cls) -> dict:
        cfg = super().config()
        cfg.update({"webhook": REQUIRED})
        return cfg

    def send(self, event: dict):
        ...


NotifierRegistry.register("dingtalk", DingTalkNotifier)
```

## 注意事项

- 状态存储默认是内存，仅对单进程有效；多进程/多机可替换为外部存储（如 Redis）。
