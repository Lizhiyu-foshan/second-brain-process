# 事故预防技术方案
## GitHub Token 误删事件后续 - 技术保障措施

**文档编号**: PREVENTION-20260318-001  
**关联事故**: INC-20260318-001  
**生效日期**: 2026-03-18

---

## 核心理念

**不再依赖文档约束，改用技术强制保障**

之前的错误：以为写进 AGENTS.md 就万事大吉  
现在的方案：技术手段强制执行，绕过即失败

---

## 已部署的技术保障

### 1. 凭据自动备份系统 ✅

**文件**: `/root/.openclaw/workspace/scripts/credential_backup.sh`

**功能**:
- 任何修改前自动备份当前凭据状态
- 备份环境变量、git-credentials、netrc、SSH 密钥列表
- 保留最近30个备份版本
- 生成对应的恢复脚本

**使用方式**:
```bash
# 手动执行备份
/root/.openclaw/workspace/scripts/credential_backup.sh

# 查看备份历史
ls -la /root/.openclaw/backups/credentials/

# 恢复凭据
/root/.openclaw/backups/credentials/restore_YYYYMMDD_HHMMSS.sh
```

---

### 2. 安全修复拦截器 ✅

**文件**: `/root/.openclaw/workspace/scripts/security_fix_guardian.py`

**功能**:
- 拦截所有涉及凭据的操作
- 强制人工确认（输入确认码）
- 自动调用备份脚本
- 熔断机制：1小时内超过3次修复自动暂停

**使用方式**:
```bash
# 代替直接执行命令，使用拦截器
python3 /root/.openclaw/workspace/scripts/security_fix_guardian.py "your command here"

# 例如（会被拦截并要求确认）
python3 security_fix_guardian.py "unset GITHUB_TOKEN"
python3 security_fix_guardian.py "rm -f ~/.git-credentials"
```

**拦截的操作类型**:
- 删除/修改 GITHUB_TOKEN
- 删除 git-credentials
- 删除 SSH 密钥
- 包含 ghp_ 或 github_pat_ 的token操作
- 其他涉及凭据的危险操作

---

### 3. GitHub 认证自动验证 ✅

**文件**: `/root/.openclaw/workspace/scripts/verify_github_auth.py`

**功能**:
- 定期验证 GitHub 推送功能是否正常
- 检查远程配置、连接状态、待推送提交
- 异常时自动记录告警

**使用方式**:
```bash
# 手动验证
python3 /root/.openclaw/workspace/scripts/verify_github_auth.py

# 静默模式（仅错误时输出）
python3 /root/.openclaw/workspace/scripts/verify_github_auth.py --silent

# JSON 输出
python3 /root/.openclaw/workspace/scripts/verify_github_auth.py --json
```

---

### 4. 集成到定时健康检查 ⏳

**计划**: 将 `verify_github_auth.py` 集成到 cron-health-dashboard

**实现方式**:
```python
# 在 cron_health_check.py 中添加
from verify_github_auth import check_github_auth

def health_check():
    # ... 原有检查 ...
    
    # 新增: GitHub 认证检查
    auth_status = check_github_auth()
    if auth_status["overall_status"] != "ok":
        send_alert("GitHub 认证异常", auth_status)
```

---

## 强制约束规则

### 规则 1: 凭据操作必须通过拦截器

**违反后果**: 如果直接执行而未通过拦截器，视为严重违规

**检查方式**:
```bash
# 安全
python3 security_fix_guardian.py "unset GITHUB_TOKEN"

# 违规（会被记录到 .learnings/violations.log）
unset GITHUB_TOKEN
```

### 规则 2: 修改后立即验证

**强制检查点**:
1. 修改凭据后 → 运行 verify_github_auth.py
2. 验证失败 → 立即回滚到备份
3. 无法回滚 → 立即通知用户

### 规则 3: 禁止批处理凭据删除

**禁止行为**:
```bash
# 绝对禁止
rm -rf ~/.ssh/
rm -f ~/.git-credentials ~/.netrc
unset GITHUB_TOKEN API_KEY SECRET
```

**正确做法**:
```bash
# 一个一个来，每个都要确认
python3 security_fix_guardian.py "rm -f ~/.git-credentials"
# 验证...
python3 security_fix_guardian.py "unset GITHUB_TOKEN"
# 验证...
```

---

## 监控与告警

### 告警触发条件

| 条件 | 告警方式 | 级别 |
|-----|---------|-----|
| GitHub 连接失败 | 飞书消息 | CRITICAL |
| 凭据文件被修改 | 日志 + 飞书 | HIGH |
| 1小时内多次安全修复 | 飞书 + 熔断 | HIGH |
| 存在待推送提交超过24小时 | 日志 | WARNING |

### 告警记录位置
- `/root/.openclaw/workspace/.learnings/alerts.md`
- `/root/.openclaw/workspace/.learnings/security_fix_interceptions.log`

---

## 恢复流程（万一再次出问题）

### 场景 1: Token 被误删

**自动执行**:
1. 从备份目录找到删除前的备份
2. 运行恢复脚本
3. 测试推送功能

**手动步骤**:
```bash
# 1. 查看最新备份
ls -lt /root/.openclaw/backups/credentials/ | head -5

# 2. 恢复环境变量（手动设置）
export GITHUB_TOKEN="从备份中找到的token"

# 3. 验证
python3 /root/.openclaw/workspace/scripts/verify_github_auth.py
```

### 场景 2: 无法找回 Token

**立即行动**:
1. 暂停所有自动推送任务
2. 通知用户手动配置新 Token
3. 本地提交继续保留，等待恢复推送

---

## 执行检查清单

- [x] 创建凭据自动备份脚本
- [x] 创建安全修复拦截器
- [x] 创建 GitHub 认证验证器
- [ ] 集成到 cron 健康检查
- [ ] 添加飞书告警通知
- [ ] 创建熔断机制监控面板
- [ ] 定期演练恢复流程

---

## 承诺

**技术手段强制执行，不再依赖人工记忆**

如果再次违反，说明技术方案有漏洞，需要升级而非仅仅提醒。

---

**责任人**: Kimi Claw  
**更新日期**: 2026-03-18  
**下次审查**: 2026-03-25
