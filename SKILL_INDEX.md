# 已安装 Skill 清单

**更新日期**: 2026-03-13
**检查方式**: 手动执行（因定时任务失效）

---

## 📦 系统级 Skills（/root/.openclaw/skills/）

这些是通过 `clawhub install` 从市场安装的官方/社区技能：

| Skill | 用途 | 市场来源 | 状态 |
|-------|------|---------|------|
| auto-fix | 自动修复系统问题（会话清理、磁盘释放） | clawhub | ✅ 活跃 |
| bmad-evo | BMAD进化版多Agent开发框架 | clawhub | ✅ 活跃 |
| bmad-method | BMAD基础开发框架 | clawhub | ✅ 活跃 |
| channels-setup | IM频道配置指南 | clawhub | ✅ 活跃 |
| feishu-automation | 飞书自动化 | clawhub | ✅ 活跃 |
| git-safety-guardian | Git推送安全检查 | clawhub | ✅ 活跃 |
| knowledge-studio | Obsidian知识处理 | clawhub | ✅ 活跃 |
| pipeline-health-monitor | 文章剪藏链路监控 | clawhub | ✅ 活跃 |

---

## 🛠️ 工作区级 Skills（/root/.openclaw/workspace/skills/）

这些是自建技能，针对特定需求定制：

| Skill | 用途 | 创建日期 | 状态 |
|-------|------|---------|------|
| auto-compact-dynamic | 动态上下文压缩守护 | 2026-03-12 | ✅ 活跃 |
| meeting-prep-orchestrator | 讨论准备与知识预加载 | 2026-03-13 | ✅ 刚安装 |
| auto-fix | 自动修复系统问题（自建增强版） | 2026-03-12 | ⚠️ 与系统级重复 |
| feishu-deduplication | 飞书消息去重 | 2026-03-12 | ✅ 活跃 |
| feishu-send-guardian | 飞书发送防重守护 | 2026-03-12 | ✅ 活跃 |
| git-safety-guardian | Git推送安全检查（自建版） | 2026-03-12 | ⚠️ 与系统级重复 |
| knowledge-studio | 知识处理（自建定制版） | 2026-02-27 | ⚠️ 与系统级重复 |
| nano-banana-pro-apiyi | APIYi NanoBananaPro集成 | 2026-02-25 | ❓ 待确认 |
| pipeline-health-monitor | 链路监控（自建增强版） | 2026-03-12 | ⚠️ 与系统级重复 |

---

## ⚠️ 重复技能说明

以下技能在**系统级和工作区级同时存在**：

1. **auto-fix** - 工作区版本可能包含增强功能
2. **git-safety-guardian** - 工作区版本包含额外检查
3. **knowledge-studio** - 工作区版本有自定义配置
4. **pipeline-health-monitor** - 工作区版本是实际使用的版本

**处理建议**: 检查两个版本的差异，合并功能后保留一个。

---

## 🔄 自我进化任务状态

**今天（2026-03-13）的问题**:
- ❌ 定时任务未执行（isolated模式工具调用被禁）
- ❌ 未检查已安装skill更新
- ❌ 未标注市场来源

**已修复**:
- ✅ 手动执行并生成本清单
- ✅ 记录到 ERRORS.md
- ✅ 迁移到系统级cron

---

## 📋 下次检查清单

- [ ] 检查 clawhub 是否有skill更新
- [ ] 检查工作区skill是否有改进
- [ ] 清理重复skill
- [ ] 更新 SKILL_INDEX.md
