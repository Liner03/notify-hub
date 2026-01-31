# Notify Hub

轻量级 Python 通知框架：多渠道推送 + 防爆策略。

## 特性

- **统一接口**: 单一 API 发送到多个渠道
- **多渠道支持**: 企业微信 / Telegram / 飞书 / Bark
- **防爆策略**: 去重 / 冷却 / 限流 / 聚合
- **轻量设计**: 基础内存 ~10 MB，运行时稳定在 ~3 MB
- **环境变量**: 支持 `${VAR}` 占位符，避免硬编码密钥

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 快速开始

**1. 创建配置文件 `notify.yaml`**

```yaml
notify:
  channels:
    - type: bark
      key: "${BARK_KEY}"
      server: "https://api.day.app"
```

**2. 发送通知**

```python
from notify import Notify

notify = Notify.from_config("notify.yaml")
notify.send("Hello from Notify Hub!", notify_level="info")
```

## API

```python
Notify.send(
    raw_content,           # 消息内容
    type="text",           # 消息类型: text/markdown/html
    notify_level="info",   # 事件等级: fatal/error/warn/info
    event_key=None,        # 事件唯一标识（可选，用于去重/聚合）
    source=None            # 来源标识（可选）
)
```

## 渠道配置示例

完整配置见 [`notify.yml.example`](notify.yml.example)。

**Telegram**
```yaml
- type: telegram
  token: "${TG_TOKEN}"
  chat_id: "${TG_CHAT_ID}"
```

**企业微信**
```yaml
- type: wecom
  corpid: "${WECOM_CORPID}"
  corpsecret: "${WECOM_CORPSECRET}"
  agentid: ${WECOM_AGENTID}
  touser: "@all"
```

**飞书**
```yaml
- type: feishu
  webhook: "${FEISHU_WEBHOOK}"
```

**Bark**
```yaml
- type: bark
  key: "${BARK_KEY}"
  server: "https://api.day.app"
```

## 支持的渠道

| 渠道 | 消息类型 |
| --- | --- |
| Telegram | `text` / `markdown` / `html` |
| 企业微信 | `text` / `markdown` / `image` / `news` / `file` / `textcard` 等 |
| 飞书 | `text` / `markdown` |
| Bark | `text` / `markdown` |

## 策略配置

```yaml
notify:
  policies:
    dedupe:              # 去重
      ttl: 3600
      levels: ["fatal", "error"]
    cooldown:            # 冷却
      ttl: 21600
      levels: ["fatal"]
    rate_limit:          # 限流
      per_minute: 30
      levels: ["fatal", "error", "warn"]
    aggregate:           # 聚合
      window: 3600
      levels: ["warn"]
```

## 性能表现

**内存占用** (Python 3.12 / macOS)

| 场景 | 内存使用 |
| --- | --- |
| 导入模块 + 创建实例 | ~10 MB |
| 发送 100 条消息 | +0.05 MB |
| 发送 10,000 条消息 | +0.02 MB |
| 发送 16,000 条消息 | 总增长 ~6 MB |

**关键特性**
- 内存稳定，增长曲线平坦
- TTL 过期自动清理
- 存储量与 unique keys 成正比（不是消息总数）

## 示例

查看 [`examples/`](examples/) 目录获取各渠道的完整示例。

```bash
export BARK_KEY=your_key
python examples/bark/send.py
```

## 扩展开发

添加自定义渠道：

```python
from notify.channels.base import BaseNotifier, REQUIRED
from notify.core.registry import NotifierRegistry

class CustomNotifier(BaseNotifier):
    type_name = "custom"
    supported_types = {"text", "markdown"}

    @classmethod
    def config(cls):
        cfg = super().config()
        cfg.update({"webhook": REQUIRED})
        return cfg

    def send(self, event):
        # 实现发送逻辑
        pass

NotifierRegistry.register("custom", CustomNotifier)
```

## License

MIT
