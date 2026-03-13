---
name: git-safety-guardian
description: Git推送安全守护工具。用于在git push前执行安全检查，防止误推送到错误仓库（特别是多仓库嵌套环境如obsidian-vault）。执行四确认检查（当前目录、remote URL、当前分支、嵌套仓库），高危操作（--force）需二次确认。使用场景：(1) 执行git push前自动验证，(2) 多仓库嵌套环境下的推送确认，(3) 安装pre-push钩子实现自动拦截，(4) 高危操作前的安全提醒。
---

# Git Safety Guardian

Git推送安全守护工具，防止误推送到错误仓库。

## 背景问题

在多仓库嵌套环境中（如工作区根目录包含obsidian-vault子仓库），极易发生误推送事故：
- 在工作区根目录执行git push，实际推送了obsidian-vault
- 导致笔记仓库被污染，需要耗时修复（曾发生1小时修复事故）

## 核心功能

执行**四确认检查**：

1. **当前目录验证** - 确认是有效的Git仓库
2. **Remote URL检查** - 显示目标仓库，特殊标记obsidian-vault等敏感仓库
3. **当前分支确认** - 显示当前分支，警告main/master分支操作
4. **嵌套仓库检测** - 检测子目录中的其他git仓库，防止在错误层级推送

**高危操作保护**：
- `--force` 推送强制二次确认
- 可配置为交互模式或钩子模式

## 使用方法

### 方法1: 手动检查（推荐用于单次推送）

```bash
# 执行安全检查
python3 ~/.openclaw/skills/git-safety-guardian/scripts/git_safety_check.py

# 检查结果后，确认无误再执行
git push
```

### 方法2: 安装pre-push钩子（推荐用于长期保护）

```bash
# 在当前仓库安装pre-push钩子
python3 ~/.openclaw/skills/git-safety-guardian/scripts/git_safety_check.py --install-hook
```

安装后，每次执行 `git push` 会自动运行安全检查：
- 检查通过：允许推送
- 检查失败：阻止推送，需用户确认

### 方法3: 强制推送检查

```bash
# 标记为强制推送检查（会触发额外警告）
python3 ~/.openclaw/skills/git-safety-guardian/scripts/git_safety_check.py --force
```

## 输出示例

```
==================================================
Git 安全检查报告
==================================================
🔍 检查1: Git仓库验证
   ✅ 当前目录是有效的Git仓库

🔍 检查2: 当前分支
   ✅ 当前分支: main
   ⚠️  警告: 你在 main 分支上，请确保操作正确

🔍 检查3: Remote URL
   ✅ Remote: git@github.com:user/obsidian-vault.git
   ⚠️  警告: 目标是笔记仓库(obsidian-vault)，请确认推送内容正确

🔍 检查4: 嵌套仓库检测
   ⚠️  发现 2 个嵌套仓库:
      - second-brain-processor
      - museum-collector
   💡 提示: 确保你在正确的目录层级执行推送
==================================================

是否继续推送? (yes/no):
```

## 集成到工作流

### 与Kimi Claw集成

当用户提到"git push"、"推送代码"、"同步到GitHub"等操作时：

1. 提醒用户使用安全检查：
   ```
   建议在推送前运行安全检查：
   python3 ~/.openclaw/skills/git-safety-guardian/scripts/git_safety_check.py
   ```

2. 如果检测到多仓库嵌套环境，主动推荐安装钩子：
   ```
   检测到嵌套仓库结构，建议安装pre-push钩子防止误推送：
   python3 ~/.openclaw/skills/git-safety-guardian/scripts/git_safety_check.py --install-hook
   ```

### 与AGENTS.md规则8配合

此skill自动化了AGENTS.md规则8（GitHub推送安全检查）中的手动检查流程，将"人工记忆规则"转变为"系统级拦截"。

## 配置选项

### 环境变量

- `GIT_SAFETY_SKIP_CONFIRM` - 设置为`1`时跳过交互确认（CI环境使用）

### 自定义敏感仓库列表

编辑脚本中的敏感仓库检测逻辑（默认检测obsidian-vault）：

```python
# 检查是否是敏感仓库
SENSITIVE_REPOS = ["obsidian-vault", "notes", "private"]
if any(repo in remote.lower() for repo in SENSITIVE_REPOS):
    messages.append(f"   ⚠️  警告: 目标是敏感仓库")
```

## 故障排除

### 钩子未生效

检查钩子是否有执行权限：
```bash
ls -la .git/hooks/pre-push
# 如果没有执行权限，手动添加：
chmod +x .git/hooks/pre-push
```

### 误报嵌套仓库

如果某些子目录的git仓库是预期的（如submodule），可以调整检测深度或排除规则。

## 相关文件

- 脚本位置：`scripts/git_safety_check.py`
- 相关规则：`AGENTS.md` 规则8（GitHub推送安全检查）
