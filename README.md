# 通知系统（Python 内存框架）

这是一个独立的通知框架，支持多平台通知（Webhook/企业微信/Telegram/飞书等），
并提供去重、冷却、限流、聚合、升级等防爆策略。该框架与业务项目解耦，
业务系统只需调用通知接口即可。

## 依赖安装

推荐使用 venv：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

## 使用方式

### 1. 代码实例化

```python
from notify import Notify
from notify.channels import WebhookNotifier, TelegramNotifier
from notify.core.policies import DedupePolicy, RateLimitPolicy

notify = Notify(
    channels=[
        WebhookNotifier(url="https://example.com/webhook"),
        TelegramNotifier(token="YOUR_TOKEN", chat_id="YOUR_CHAT_ID"),
    ],
    policies=[
        DedupePolicy(ttl=3600, levels=["fatal", "error"], upgrade_after=10),
        RateLimitPolicy(per_minute=30, levels=["fatal", "error", "warn"]),
    ],
)

notify.send(
    "Please refresh QUARK_COOKIE",
    event_key="quark_cookie_invalid",
    notify_level="fatal",
    type="text",
    source="consumer",
    telegram_parse_mode="MarkdownV2",
)
```

### 2. YAML 配置加载

推荐使用配置文件 + 环境变量方式，避免在代码里写 token。

```python
from notify import Notify

notify = Notify.from_config("notify.yaml")
notify.send(
    "task_id=123",
    event_key="task_failed",
    notify_level="error",
    type="text",
    wecom_mentioned_list=["@all"],
)
```

环境变量支持 `${VAR}` 替换，示例见 `notify.yaml.example`。

## 事件等级

通过 `notify_level` 指定事件等级：

- `fatal`：系统级不可用或全量失败
- `error`：任务失败/重试耗尽
- `warn`：可恢复异常，建议聚合摘要
- `info`：信息类（可不通知）

## 消息参数

`Notify.send(raw_content, type="text", notify_level="info", event_key=None, source=None, **kwargs)`：

仅支持参数调用方式，不再接收 `Event` 或 dict。

- `raw_content`：原始内容（必填，第一个参数）
- `type`：内容类型（默认 `text`）
- `notify_level`：事件等级（默认 `info`）
- `event_key`：事件唯一标识（可选，未传会自动生成）
- `source`：来源标识（可选）
- `**kwargs`：平台参数（见下文参数约定，Bark 的 `level` 也在这里）

## 多渠道格式适配

不同平台支持的 `type` 不一致，框架会自动降级到 `text`：

- `webhook`：`text`/`markdown`/`html`/`json`
- `telegram`：`text`/`markdown`/`html`
- `wecom`：`text`/`markdown`
- `feishu`：`text`/`markdown`（`markdown` 默认使用交互卡片）
- `bark`：`text`

## 参数约定（kwargs）

平台参数通过 `**kwargs` 传递，使用前缀区分：

- `common_`：注入所有渠道
- `<channel>_`：注入到对应渠道（`webhook_`/`telegram_`/`wecom_`/`feishu_`/`bark_`）
- `<name>_`：注入到指定实例（当渠道配置了 `name`）

默认情况下，未带前缀的参数不会注入到其他渠道；Bark 支持常用字段直接传入（如 `level`、`icon`）。
如果需要强制指定 Bark 参数，也可以使用 `bark_` 前缀（例如 `bark_sound`、`bark_group`）。

示例：

```python
notify.send(
    "deploy failed",
    notify_level="error",
    telegram_parse_mode="MarkdownV2",
    wecom_mentioned_list=["@all"],
    common_trace_id="abc",
)
```

## Bark 配置说明

`bark` 仅支持 `text`，消息体默认来自 `raw_content`，也可通过 `body` 覆盖。

YAML 渠道配置（支持自建服务端）：

```yaml
- type: bark
  key: "${BARK_KEY}"
  server: "https://api.day.app"  # 自建服务端可改为 http://your-host:port
```

常用参数（可直接作为 `Notify.send(..., **kwargs)` 传入）：

- `title`/`subtitle`/`body`：推送标题/副标题/内容
- `markdown`：推送内容（传了会忽略 `body`）
- `device_key`/`device_keys`：设备 key（批量推送用，通常不需要）
- `url`：点击跳转链接
- `group`：分组
- `icon`：自定义图标（iOS 15+）
- `image`：推送图片
- `sound`：铃声
- `call`：重复播放铃声 30 秒
- `badge`：角标数字
- `autoCopy`：自动复制（传 `1`）
- `copy`：指定复制内容
- `ciphertext`：加密密文
- `isArchive`：是否保存推送（传 `1` 保存）
- `action`：传 `none` 点击不弹窗
- `id`：推送 ID（相同 ID 覆盖更新）
- `delete`：传 `1` 删除（需配合 `id`）
- `level`：推送中断级别（`active`/`timeSensitive`/`passive`/`critical`）
- `volume`：重要警告音量（0-10）

注意：事件等级使用 `notify_level`，Bark 推送中断级别使用 `level`。

示例（带图 + 时效性通知）：

```python
notify.send(
    "job_id=123",
    event_key="task_failed",
    notify_level="error",
    type="text",
    title="任务失败",
    icon="https://example.com/icon.png",
    level="timeSensitive",
    url="https://example.com/jobs/123",
)
```

## 扩展多渠道

实现一个新的通知渠道时：

1) 继承 `BaseNotifier`
2) 实现 `send(self, event)`（`event` 为 dict）
3) 注册到 `NotifierRegistry`

```python
from notify.channels.base import BaseNotifier
from notify.core.registry import NotifierRegistry

class DingTalkNotifier(BaseNotifier):
    type_name = "dingtalk"
    supported_types = {"text", "markdown"}

    def __init__(self, webhook: str, name=None):
        super().__init__(name=name)
        self.webhook = webhook

    def send(self, event):
        ...

NotifierRegistry.register("dingtalk", DingTalkNotifier)
```

## Webhook 扩展

Webhook 可能对应不同平台的自定义格式，框架将其单独拆分为目录，
你可以继承 `WebhookBaseNotifier` 来适配不同 payload：

```python
from notify.channels.webhook.base import WebhookBaseNotifier
from notify.core.registry import NotifierRegistry

class CustomWebhookNotifier(WebhookBaseNotifier):
    type_name = "webhook.custom"

    def build_payload(self, event, channel_args):
        return {
            "title": event.get("event_key"),
            "content": event.get("raw_content"),
            "level": event.get("level"),
            "extra": channel_args,
        }

NotifierRegistry.register("webhook.custom", CustomWebhookNotifier)
```

## 通知策略（默认建议）

- 去重：`dedupe`
- 冷却：`cooldown`
- 限流：`rate_limit`
- 聚合：`aggregate`

## 通道说明

- `webhook`：发送 JSON payload
- `telegram`：bot sendMessage
- `wecom`：企业微信机器人 webhook
- `feishu`：飞书机器人 webhook
- `bark`：Bark 推送接口（可自建服务端）

## 注意事项

- 内存型状态仅对单进程有效
- 多进程/多机部署需替换为外部存储（Redis/PG）
