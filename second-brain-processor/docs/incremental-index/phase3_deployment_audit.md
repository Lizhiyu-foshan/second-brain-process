# Phase 3: 部署阶段 - BMAD-EVO 审计报告

**项目**: Incremental Message Index System  
**阶段**: deployment  
**时间**: 2026-03-21  

---

## 部署方案

### 1. 部署策略

**策略**: 蓝绿部署（并行运行）

```
阶段1: 部署新系统，并行运行
  - 安装新脚本
  - 首次运行建立索引
  - 对比输出与原系统一致

阶段2: 切换定时任务
  - 修改cron job使用新脚本
  - 观察3天运行
  - 监控性能和完整性

阶段3: 清理旧系统
  - 确认新系统稳定
  - 移除旧脚本
  - 归档项目文档
```

### 2. 部署步骤

```bash
# 1. 运行部署脚本
cd /root/.openclaw/workspace/projects/incremental-index-system
bash scripts/deploy.sh

# 2. 验证安装
python3 /root/.openclaw/workspace/second-brain-processor/process_incremental.py

# 3. 对比输出
# - 检查生成的对话文件
# - 确认消息数量与原方案一致

# 4. 更新定时任务
openclaw cron update <job-id> \
  --payload "python3 /root/.openclaw/workspace/second-brain-processor/process_incremental.py"

# 5. 监控
# - 观察3天运行
# - 检查执行时间
# - 验证消息完整性
```

### 3. 回滚方案

```bash
# 紧急情况回滚
bash scripts/rollback.sh

# 手动回滚步骤:
# 1. 停止当前任务
pkill -f process_incremental.py

# 2. 恢复旧脚本
cp process_raw.py.backup process_raw.py

# 3. 更新cron
openclaw cron update <job-id> --payload "...process_raw.py..."
```

---

## 约束检查

### 部署前检查清单

| 检查项 | 状态 | 说明 |
|--------|------|------|
| S3: 不阻塞定时任务 | ✅ | 脚本可独立运行 |
| S4: 优雅降级 | ✅ | 保留原脚本作为fallback |
| R3: 双重验证 | ✅ | 首次运行可对比输出 |
| R4: 7天备份 | ✅ | 部署脚本自动备份 |

---

## 验收标准

### 功能验收

| 验收项 | 验收方法 | 通过标准 |
|--------|---------|---------|
| 消息完整性 | 对比原方案输出 | 消息数量差 < 1% |
| 执行时间 | 日志记录 | < 1秒 |
| 索引正确性 | 检查索引文件 | 包含正确的时间戳 |
| 异常恢复 | 手动删除索引 | 自动重建成功 |

### 性能验收

| 指标 | 目标 | 验收方法 |
|------|------|---------|
| 执行时间 | < 1秒 | 日志统计 |
| 内存使用 | < 100MB | 系统监控 |
| 磁盘IO | 最小化 | 文件读取次数 |

---

## 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 消息遗漏 | 低 | 高 | 并行运行3天对比 |
| 首次运行超时 | 中 | 中 | 手动触发首次运行 |
| 索引损坏 | 低 | 高 | 自动重建+备份机制 |
| 定时任务冲突 | 低 | 中 | 低峰期部署 |

---

## 阶段结论

**状态**: ✅ 就绪，等待部署  

**部署建议**:
1. 选择低峰期（周末）部署
2. 首次手动运行建立索引
3. 并行观察3天再切换定时任务
4. 保留回滚能力至少1周

**下一步**: 执行部署脚本，开始并行验证

---

**审计人**: Kimi Claw  
**审计时间**: 2026-03-21
