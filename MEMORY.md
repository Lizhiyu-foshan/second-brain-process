# Kimi Claw 用户偏好与背景记录

> 本文档记录用户偏好、历史决策和背景信息。  
> 行为规则请查看 [AGENTS.md](../AGENTS.md)

---

## 记忆分层索引

| 层级 | 文件 | 用途 | 更新频率 |
|------|------|------|---------|
| **索引层** | [MEMORY.md](./MEMORY.md) | 核心信息概览 | 月度 |
| **教训层** | [memory/lessons.md](./lessons.md) | 踩坑记录，按严重程度分级 | 踩坑后 |
| **基础设施层** | [memory/infra.md](./infra.md) | 服务器/API/配置 | 配置变更时 |
| **日志层** | [memory/YYYY-MM-DD.md](./2026-03-19.md) | 每日原始记录 | 每日 |

---

## 核心原则

### 代码修复黄金法则（2026-03-17 用户教育）

**用户原话**："记住，任何修复都不能破坏原文件的运行逻辑，如果修复导致系统不能运行，那修复了还有什么意义，以后这种情况，你要做好思考，才能行动"

**事件背景**：
- 我看到审计报告说有 CRITICAL 问题（硬编码密钥等）
- 没有人工验证问题真实性（实际是示例代码，不是真实问题）
- 直接运行自动修复脚本，引入语法错误
- 破坏了 7 个 Python 文件的正常运行
- 最后从 git 恢复才修复

**核心原则**：
> **修复不能破坏运行，否则不如不修。先思考，后行动。**

**修复前检查清单**（必须严格执行）：
```
□ 1. 验证问题真实性
□ 2. 评估修复风险
□ 3. 创建备份
□ 4. 小步修复
□ 5. 语法检查
□ 6. 功能测试
□ 7. 提交更改
```

**记录时间**：2026-03-17 19:30  
**教训等级**：critical

---

## 系统配置参考

### OpenClaw 模型排名（2026-03-08）

**成功率排名 Top 5**：
1. google/gemini-3-flash-preview
2. minimax/minimax-m2.1
3. moonshotai/kimi-k2.5
4. anthropic/claude-sonnet-4.5
5. google/gemini-3-pro-preview

**关键发现**：
- MiniMax M2.5 成功率只有 35.5%，垫底
- 已切换到 GLM-5（2026-03-08）

### 版本升级提醒事项（2026-03-06）

**OpenClaw 2026.2.13 版本已知问题**：
- `agentTurn` + `isolated` session 模式下，子 Agent 工具调用会出现 `35 validation errors`
- 解决方案：将定时任务从 `agentTurn` 改为 `systemEvent`，`sessionTarget` 从 `isolated` 改为 `main`

**已修复任务**：
- ✅ 凌晨5:00聊天记录整理
- ✅ 每日复盘报告推送

---

## 工作流程偏好

### 聊天记录整理要求（2026-03-09 更新）

**核心原则**：按主题分类整理，提取有价值的观点和核心思考

**具体要求**：
1. **主题分类**：识别对话中的不同主题
2. **核心观点提炼**：Key Takeaway + 详细观点 + 思考 + 关联
3. **删除内容**：操作细节、系统错误排查、重复确认
4. **保留内容**：重要决策、哲学思考、长远预测、新发现

### 定时任务流程配置（2026-03-17 最终版）

**核心决策**：系统不主动调用 AI，用户确认后再触发深度处理

**当前配置**：
- **5:00** - 清晨整理（无 AI）：`process_raw.py`
- **8:30** - 复盘报告推送（完整版）：`daily_complete_report.py`
- **用户确认后** - AI 深度整理：`ai_process_and_push.py --confirmed`

**相关脚本**：
- `process_raw.py` - 原始对话整理
- `daily_complete_report.py` - 完整复盘报告
- `ai_process_and_push.py` - AI 深度整理 + GitHub 推送

### 文章整理归档规则（2026-03-19 新增）

**规则**: AI整理后的内容保留，删除原始碎片

**适用场景**:
1. **对话整理**: 用AI整理完对话后，删除原始的 `..._raw.md` 和 `..._conversations.md`，只保留 `..._analyzed.md` 或 `..._主题整理版.md`
2. **文章整理**: 用AI整理完文章后（如生成A2版本），删除原始快速保存的文件，只保留整理后的版本

**操作步骤**:
1. 确认整理后的文件已生成并推送到GitHub
2. 备份原始文件到 `.backup/` 目录
3. 删除原始碎片文件
4. Git提交并推送

**目的**: 保持Obsidian Vault整洁，避免原始碎片和整理后内容重复占用空间

**开屏显示**：最近3天项目列表 + 快捷指令

**快捷指令**：
- "继续开发" / "加载 [项目名]" / "查看项目" / "测试项目" / "推送 GitHub" / "新项目"

---

## 项目成果

### BMAD-EVO AST 审计引擎集成（2026-03-17 完成）

**核心成果**：将约束检查从正则升级为 AST 分析，实现零误报

**新增文件**：
- `lib/ast_auditor.py` (32KB) - AST 核心审计引擎
- `templates/constraints/` - 约束模板
- `docs/AST_AUDITOR.md` - 完整文档

**AST 检查规则**（8 种）：

| 规则 | 说明 | 严重性 |
|------|------|--------|
| `null_check` | 函数参数空值检查 | HIGH |
| `exception_flow` | 异常流完整性 | MEDIUM |
| `no_bare_except` | 禁止裸 except | MEDIUM |
| `no_empty_except` | 禁止空异常处理器 | CRITICAL |
| `io_exception` | IO 操作异常处理 | HIGH |
| `network_exception` | 网络请求异常处理 | HIGH |
| `hardcoded_secret` | 硬编码密钥检测 | CRITICAL |
| `type_annotation` | 类型注解 | LOW |

**性能对比**：

| 模式 | 速度 | 准确率 | 推荐场景 |
|------|------|--------|----------|
| AST only (fast) | <2ms/文件 | 99% | 开发时快速反馈 |
| AST + regex (strict) | <10ms/文件 | 99% | 发布前全面检查 |
| Regex only | <5ms/文件 | 85% | 向后兼容 |

**状态**：✅ 核心功能完成，可投入使用

---

## 待办事项

### 代码审核任务（2026-03-08）

**待审核项目**：
1. 自己安装的 skill：`bmad-evo`, `bmad-method`, `channels-setup`, `knowledge-studio`
2. GitHub 项目：`bmad-kimi`, `bmad-method-kimi`, `museum-collector`, `museum-exhibitions`, `second-brain-processor`, `second-brain-web`, `skills/`, `projects/`

**状态**：待完成

### 2026-03-17 16:30 讨论预约

**主题**: OpenClaw Moltbook 70个真实用例深度分析  
**状态**: 已确认 ⏰  
**准备材料**: 文章已保存到 Obsidian Vault

---

## 删除的内容说明

以下内容已在 AGENTS.md 中规范，从 MEMORY.md 删除：

| 原内容 | 删除原因 | AGENTS.md 对应位置 |
|--------|---------|-------------------|
| 模型切换规则 | 规则已完整记录 | 规则6：模型切换检查 |
| 定时任务流程微调（3条） | 重复且已固化 | 规则5：定时任务监控 |
| 周一美术馆推送问题 | 已解决的历史问题 | 无（已关闭） |

---

*最后更新：2026-03-19*
