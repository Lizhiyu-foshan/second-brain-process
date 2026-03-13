# 心跳检查任务

## 检查清单（每次心跳执行）

### 1. 系统健康检查
- [ ] 检查 OpenClaw 网关状态
- [ ] 检查当前模型配置
- [ ] 检查会话上下文使用情况

### 2. 错误检测
- [ ] 检查最近的错误日志
- [ ] 检查是否有 HTTP 400/500 错误
- [ ] 检查是否有上下文超限错误

### 3. 自动恢复（如果检测到问题）
- [ ] 切换回默认模型 k2p5
- [ ] 压缩或重置会话
- [ ] 通知用户系统已恢复

## 执行方式

通过 OpenClaw 的 heartbeat 机制定期执行（每 30 分钟）。

## 故障恢复脚本

```bash
#!/bin/bash
# 位置: /root/.openclaw/workspace/auto-recover.sh

echo "=== 自动恢复检查 $(date) ==="

# 检查 OpenClaw 状态
if ! openclaw status > /dev/null 2>&1; then
    echo "OpenClaw 网关异常，尝试重启..."
    openclaw gateway restart
fi

# 检查会话状态
SESSION_FILE="/root/.openclaw/agents/main/sessions/sessions.json"
MODEL_OVERRIDE=$(python3 -c "import json; d=json.load(open('$SESSION_FILE')); print(d.get('agent:main:main', {}).get('modelOverride', 'none'))")

if [ "$MODEL_OVERRIDE" != "none" ]; then
    echo "检测到模型覆盖: $MODEL_OVERRIDE"
    # 检查是否需要恢复
    # 这里可以添加更多逻辑
fi

echo "=== 检查完成 ==="
```

## 注意事项

- 心跳检查应该是轻量级的，不应该影响正常操作
- 检测到问题时优先自动恢复，然后通知用户
- 恢复操作应该有日志记录，便于追溯