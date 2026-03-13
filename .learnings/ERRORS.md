# 错误日志

记录系统运行中遇到的错误、失败操作及解决方案。

---

## [ERR-20260313-001] 定时任务全面失效 - isolated模式工具调用被禁

**Logged**: 2026-03-13T09:50:00+08:00
**Priority**: critical
**Status**: resolved
**Area**: cron_tasks

### 问题
今天所有使用 `isolated` + `agentTurn` 的定时任务全部停止实际执行：
- 健康检查报告停留在昨天 17:51
- 自动会话压缩未执行
- 消息延迟监控未执行
- 动态上下文压缩未执行
- **自我进化系统未执行**（没有检查已安装skill，没有标注来源）

### 根本原因
OpenClaw 2026.2.13 版本更新后，`isolated` session 中的 AI **无法调用任何工具**（exec、read、write 等），只能生成文本回复。昨天还能执行，今天彻底失效。

### 影响
1. 系统健康监控盲区
2. 会话积压风险
3. 自我进化停滞（技能状态未更新）
4. 所有依赖定时任务的自动化流程中断

### 解决方案
**立即修复**：将所有定时任务迁移到系统级 Linux Cron
- 不再使用 OpenClaw 的 `agentTurn` 定时任务
- 改用 `systemEvent` 或直接 crontab
- 7个任务全部迁移完成

**长期方案**：
- 监控 OpenClaw 版本更新说明
- 避免使用 `isolated` 模式执行需要工具调用的任务
- 使用 `main` session + `systemEvent` 或纯 Bash 脚本

### 验证命令
```bash
# 检查系统级cron是否生效
ls -lt /root/.openclaw/workspace/.learnings/health_check_report.json

# 检查定时任务日志
tail -f /tmp/health_check.log
```

---

## [ERR-20260307-1000] git_push_timeout

**Logged**: 2026-03-07T10:46:00+08:00
**Priority**: high
**Status**: pending
**Area**: git_sync

### 问题
Git推送失败：Failed to connect to github.com port 443 after 130000 ms: Connection timeout
多次重试后仍然失败，导致代码无法同步到远程仓库。

### 解决方案
待系统自动改进

---

## [ERR-20260305-001] deploy_check.sh 退出码检测

**Logged**: 2026-03-05T09:41:33+08:00
**Priority**: medium
**Status**: resolved
**Area**: deploy

### 问题
deploy_check.sh 使用 `set -e`，当某个测试失败时整个脚本直接退出，无法看到完整检查结果。

### 解决方案
改为手动跟踪 passed/failed 计数，最后统一返回状态码。

### 关联
- 文件: second-brain-processor/deploy_check.sh

## [ERR-20260313-104919] git_push_failed

**Logged**: 2026-03-13T10:49:19.023732
**Priority**: high
**Status**: pending
**Area**: git_sync

### 问题
补推失败: 🔍 检查1: Git仓库验证
   ✅ 当前目录是有效的Git仓库

🔍 检查2: 当前分支
   ✅ 当前分支: main
   ℹ️  提示: 你在 main 分支上

🔍 检查3: Remote URL
   ✅ Remote: https://github.com/Lizhiyu-foshan/obsidian-vault.git
   ℹ️  提示: 目标是笔记仓库(obsidian-v

### 解决方案
待记录

---

## [ERR-20260313-160604] git_push_failed

**Logged**: 2026-03-13T16:06:04.730569
**Priority**: high
**Status**: pending
**Area**: git_sync

### 问题
补推失败: 🔍 检查1: Git仓库验证
   ✅ 当前目录是有效的Git仓库

🔍 检查2: 当前分支
   ✅ 当前分支: main
   ℹ️  提示: 你在 main 分支上

🔍 检查3: Remote URL
   ✅ Remote: https://github.com/Lizhiyu-foshan/obsidian-vault.git
   ℹ️  提示: 目标是笔记仓库(obsidian-v

### 解决方案
待记录

---

## [ERR-20260313-161627] git_retry_failed

**Logged**: 2026-03-13T16:16:27.706205
**Priority**: medium
**Status**: pending
**Area**: git_sync

### 问题
补推检查失败: Command '['git', 'push', '--force-with-lease']' timed out after 60 seconds

### 解决方案
待记录

---

## [ERR-20260313-164838] git_push_failed

**Logged**: 2026-03-13T16:48:38.258189
**Priority**: high
**Status**: pending
**Area**: git_sync

### 问题
补推失败: 🔍 检查1: Git仓库验证
   ✅ 当前目录是有效的Git仓库

🔍 检查2: 当前分支
   ✅ 当前分支: main
   ℹ️  提示: 你在 main 分支上

🔍 检查3: Remote URL
   ✅ Remote: https://github.com/Lizhiyu-foshan/obsidian-vault.git
   ℹ️  提示: 目标是笔记仓库(obsidian-v

### 解决方案
待记录

---
