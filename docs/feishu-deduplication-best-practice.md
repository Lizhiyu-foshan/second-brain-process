# OpenClaw Feishu 消息去重最佳实践

> 作者: @Lizhiyu-foshan
> 日期: 2026-03-12
> 适用场景: 使用 Feishu Webhook 模式接入 OpenClaw

## 问题背景

使用 Feishu Webhook 模式时，飞书服务器会在以下情况重试发送消息：
- OpenClaw 处理时间超过 3 秒（飞书超时阈值）
- 网络抖动导致飞书未收到 HTTP 200 确认

这会导致用户收到重复回复。

## 解决方案

### 1. 消息接收去重 (feishu_receive_dedup.py)

在 AI 处理消息前进行去重检查：

```python
# AGENTS.md 规则 9 示例
收到用户消息时首先检查：
python3 -c "
import sys
sys.path.insert(0, '/path/to/your/utils')
from feishu_receive_dedup import is_message_received
content = '''用户消息内容'''
result = is_message_received(content)
sys.exit(0 if not result else 1)
"
```

**关键配置：**
- 去重窗口：2小时
- 指纹规则：内容 + 发送者（跨小时有效）

### 2. 消息发送防重 (feishu_guardian.py)

防止重复发送相同回复：

```python
from feishu_guardian import send_feishu_safe

result = send_feishu_safe(
    message="回复内容",
    target="user_open_id",
    msg_type="response",
    max_retries=1
)
```

**关键配置：**
- 去重窗口：30分钟
- 全局指纹追踪

### 3. 健康监控 (pipeline-health-monitor)

后台静默检测链路健康：

```python
python3 health_check.py --silent
```

**特性：**
- 每30分钟检查一次
- 无异常不通知
- 自动修复建议

## 完整代码

见 `second-brain-processor/` 目录：
- `feishu_receive_dedup.py` - 接收去重
- `feishu_guardian.py` - 发送防重
- `check_message_delay_v2.sh` - 延迟监控

## 建议

对于新部署：
1. 优先使用 WebSocket 模式（无3秒限制）
2. 如必须用 Webhook，务必添加去重机制
3. 监控消息延迟，及时发现网络问题

## 参考

- Feishu Webhook 文档: https://open.feishu.cn/document/ukTMukTMukTM/uUTNz4SN1MjL1UzM
- OpenClaw Feishu 插件: https://github.com/m1heng-clawd/openclaw-feishu
