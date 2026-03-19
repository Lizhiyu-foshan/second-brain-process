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

## 每周记忆维护（周日自动执行）

每周检查一次记忆系统健康度：

```markdown
### 维护检查项
- [ ] 检查 memory/ 目录文件大小
- [ ] 清理超过30天的临时备份
- [ ] 检查 lessons.md 是否需要更新
- [ ] 验证 infra.md 配置是否最新
- [ ] 生成本周记忆统计报告

### 维护脚本
```bash
#!/bin/bash
# /root/.openclaw/workspace/memory-maintenance.sh

echo "=== 记忆系统维护 $(date) ==="

# 读取上次维护时间
LAST_MAINTENANCE=$(cat /root/.openclaw/workspace/memory/.last_maintenance 2>/dev/null || echo "1970-01-01")
DAYS_SINCE=$(( ($(date +%s) - $(date -d "$LAST_MAINTENANCE" +%s)) / 86400 ))

if [ $DAYS_SINCE -ge 7 ]; then
    echo "距离上次维护 $DAYS_SINCE 天，执行维护..."
    
    # 清理旧备份（保留7天）
    find /root/.openclaw/workspace -name "*.backup.*" -mtime +7 -delete
    
    # 更新维护时间
    date +%Y-%m-%d > /root/.openclaw/workspace/memory/.last_maintenance
    
    echo "✅ 维护完成"
else
    echo "距离上次维护 $DAYS_SINCE 天，跳过"
fi
```

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