# 消息聚合通知

轻量的 Python 通知框架：多渠道推送 + 防爆策略（去重/冷却/限流/聚合）。

## 特性

- 单一入口：`Notify.send(raw_content, ...)`
- 多渠道：企业微信 / Telegram / 飞书 / Bark
- 防爆策略：`dedupe` / `cooldown` / `rate_limit` / `aggregate`
- 配置加载：YAML + 环境变量 `${VAR}` 替换

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 快速开始

1) 准备配置 `notify.yaml`：

```yaml
notify:
  channels:
    - type: bark
      key: "${BARK_KEY}"
      server: "https://api.day.app"
      title: "Notice"
      group: "demo"
```

2) 发送：

```python
from notify import Notify

notify = Notify.from_config("notify.yaml")
notify.send("hello from notice", notify_level="info")
```

## API

`Notify.send(raw_content, type="text", notify_level="info", event_key=None, source=None)`

- `raw_content`：消息内容
- `type`：内容类型（默认 `text`）
- `notify_level`：事件等级（`fatal/error/warn/info`，用于策略）
- `event_key`：事件唯一标识（可选）
- `source`：来源标识（可选）

说明：渠道相关参数仅在 YAML 中配置，`send()` 不接受渠道参数。

## 配置说明

根节点必须是 `notify:`（否则会报错）。

环境变量替换：配置里出现 `${VAR}` 时，如果环境变量不存在会直接报错（避免静默使用空值）。

`timeout`：所有渠道都支持。

- `timeout: 10` 或 `timeout: "10"`
- `timeout: [3, 10]` 表示 `(connect, read)`

渠道项除了直接写字段外，也支持用 `config:` 子对象做覆盖（等价于把字段平铺到渠道项内）。

## event_key 说明

未传 `event_key` 时，会根据消息内容生成短 hash 作为默认 key（固定长度，避免中文内容导致大量碰撞）。

如果你希望更强的去重/聚合效果，推荐业务侧传入稳定的 `event_key`（例如 `"order_failed"`、`"svcA:db_down"`）。

## 支持的渠道

| 渠道 | type | 成功判定 |
| --- | --- | --- |
| `telegram` | `text/markdown/html` | HTTP 2xx + JSON `ok=true` |
| `wecom` | `text/markdown/markdown_v2/image/news/file/voice/mpnews/video/textcard/template_card` | JSON `errcode==0` |
| `feishu` | `text/markdown` | JSON `code/StatusCode==0`（未知格式回退 HTTP） |
| `bark` | `text/markdown` | HTTP 2xx |

## 渠道配置

完整示例见 `notify.yml.example`。

最小配置：

```yaml
notify:
  channels:
    - type: telegram
      token: "${TG_TOKEN}"
      chat_id: "${TG_CHAT_ID}"

    - type: wecom
      corpid: "${WECOM_CORPID}"
      corpsecret: "${WECOM_CORPSECRET}"
      agentid: ${WECOM_AGENTID}
      touser: "@all"

    - type: feishu
      webhook: "${FEISHU_WEBHOOK}"

    - type: bark
      key: "${BARK_KEY}"
      server: "https://api.day.app"  # 自建服务端可改为 http://your-host:port
```

Telegram：除 `token/chat_id/timeout/parse_mode` 外，其余 `sendMessage` 参数可以直接写在配置里；但不要在配置里写 `text`（会被忽略，避免覆盖消息正文）。

企业微信（应用消息 API）：支持 `text/markdown/markdown_v2/image/news/file/voice/mpnews/video/textcard/template_card`。对卡片/文件等复杂类型，可在配置里指定 `msgtype`，并通过 `payload` 提供固定结构；或者在 `send()` 时传入 JSON 字符串作为消息体。

企业微信必填项：`corpid/corpsecret/agentid`，并且至少要配置一个收件人字段（`touser`/`toparty`/`totag`）。如需自定义网关，可覆盖 `base_url/req_url`。

示例（textcard）：

```yaml
notify:
  channels:
    - type: wecom
      corpid: "${WECOM_CORPID}"
      corpsecret: "${WECOM_CORPSECRET}"
      agentid: ${WECOM_AGENTID}
      touser: "@all"
      msgtype: textcard
      payload:
        title: "告警"
        description: "服务异常"
        url: "https://example.com"
        btntxt: "查看"
```

> 说明：当前 `wecom` 渠道是企业微信「应用消息 API」。

## 策略配置

策略在 `notify.policies` 下：

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

## Examples

每个渠道都有一套独立示例：

- `examples/telegram/notify.yaml` + `examples/telegram/send.py`
- `examples/wecom/notify.yaml` + `examples/wecom/send.py`
- `examples/feishu/notify.yaml` + `examples/feishu/send.py`
- `examples/bark/notify.yaml` + `examples/bark/send.py`

运行示例（以 bark 为例）：

```bash
export BARK_KEY=...
python examples/bark/send.py
```

## 本地测试（不入库）

仓库根目录有一个本地测试脚本 `test_examples_local.py` 用来验证 `examples/*/notify.yaml` 都能被加载。

它会先加载根目录的 `notify.test.yml`，再加载每个示例配置。

这个文件会被写入 `.git/info/exclude`，用于本地开发，不会提交到仓库。

```bash
python test_examples_local.py
```

如需真实发送测试消息（需要配置真实环境变量）：

```bash
python test_examples_local.py --send --message "[notice] test"
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
- 请保护好 token/secret/webhook/key，避免泄漏。
