# Kimi Claw 用户偏好记录

## 模型切换规则（重要）

**规则**: 切换模型时必须检查上下文长度配置

**问题案例** (2026-03-08):
- 从 k2p5 (262k) 切换到 GLM-5 (128k) 时
- 上下文长度配置未更新，仍使用 262k
- 导致 `Range of input length should be [1, 202752]` 错误
- 系统无法通信

**切换模型前必须执行**:
1. 检查新模型的上下文窗口限制
2. 如果当前上下文 > 新模型限制，先压缩 (`/compact`) 或重置 (`/reset`) 会话
3. 确保上下文长度配置与新模型匹配

**模型上下文窗口参考**:
- k2p5: 262144 (256k)
- GLM-5: 128000 (128k)
- MiniMax-M2.5: 204800 (200k)
- Qwen3.5 Plus: 128000 (128k)

---

## 版本升级提醒事项

### OpenClaw 2026.2.13 版本已知问题
**记录时间**: 2026-03-06
**触发条件**: 升级到 2026.2.13 或更高版本时

**问题描述**:
- `agentTurn` + `isolated` session 模式下，子 Agent 工具调用会出现 `35 validation errors`
- 错误信息: `{'type': 'missing', 'loc': ('body', 'tools', 0, 'function'), 'msg': 'Field required'...}`
- 子 Agent 可能误判自己无文件系统权限

**影响范围**:
- 所有使用 `agentTurn` payload + `isolated` sessionTarget 的定时任务
- 具体表现为：任务触发但子 Agent 无法正常执行工具调用

**解决方案**:
1. 将定时任务从 `agentTurn` 改为 `systemEvent`
2. 将 `sessionTarget` 从 `isolated` 改为 `main`
3. 由主会话直接执行命令，绕过子 Agent 的工具调用问题

**已修复任务**:
- ✅ 凌晨5:00聊天记录整理 (efccc41b-7887-4af7-b619-54f91679cdaa)
- ✅ 每日复盘报告推送 (35ff007b-d995-4650-a90f-f3c973a386ca)

**提醒**: 下次升级 OpenClaw 版本时，检查是否有类似问题，并考虑官方是否已修复此问题。

---

## 聊天记录整理要求（2026-03-09 更新）

**核心原则**：按主题分类整理，提取有价值的观点和核心思考，而非简单的时间顺序记录。

### 具体要求
1. **主题分类**：识别对话中的不同主题，每个主题单独成篇
2. **核心观点提炼**：
   - 提取 Key Takeaway（一句话核心观点）
   - 列出详细观点（bullet points）
   - 记录引发的思考（implications）
   - 关联已有知识（connections）
3. **删除内容**：
   - 操作细节、代码修改等技术过程
   - 系统错误排查过程
   - 重复的消息和确认
4. **保留内容**：
   - 重要决策和洞察
   - 有价值的哲学思考
   - 长远视角的预测和担忧
   - 新发现和方法论

### 特别关注
- **3.6和3.7日晚上关于AI发展对人类社会冲击的内容**：需要详细整理
- **用户纠正和反馈**：记录用户明确指出的问题和改进方向

### 执行方式
- 使用AI进行深度分析和整理，不能只用硬编码规则
- 凌晨5:00定时任务应包含AI深度整理，而非仅保存原始内容
- 整理后推送到GitHub，删除原始流水账记录

---

## 项目恢复偏好

用户希望每次启动 Kimi Claw 时：

### 开屏显示
1. 列出最近 3 天内的项目
2. 显示项目名称、最后修改时间、简介
3. 提供快捷指令选择

### 交互流程
```
用户启动 Kimi Claw
    ↓
显示最近项目列表
    ↓
用户选择：
  ├── [1] 继续开发项目 → 加载 PROJECT_LOG.md → 询问具体操作
  ├── [2] 查看项目详情 → 显示代码结构
  ├── [3] 运行测试     → 执行测试
  ├── [4] 推送到 GitHub → 执行推送
  └── [n] 新项目      → 开始新对话
```

### 快捷指令
- "继续开发" → 加载最近项目
- "加载 [项目名]" → 加载指定项目
- "查看项目" → 显示项目详情
- "测试项目" → 运行测试
- "推送 GitHub" → 推送到远程
- "新项目" → 开始新对话
- "列出所有" → 显示所有历史项目

## 项目位置

所有项目保存在：`/root/.openclaw/workspace/projects/`

当前活跃项目：
- **ecommerce-mvp** (2026-02-21 创建)
  - 位置: `/root/.openclaw/workspace/projects/ecommerce-mvp/`
  - 类型: FastAPI 电商系统 MVP
  - 状态: 多 Agent 开发完成，已整合为单体架构

## 辅助脚本

| 脚本 | 位置 | 用途 |
|------|------|------|
| 欢迎界面 | `/root/.openclaw/workspace/kimi-welcome.sh` | 开屏显示最近项目 |
| 项目选择器 | `/root/.openclaw/workspace/welcome-screen.sh` | 交互式项目选择 |
| 项目加载器 | `/root/.openclaw/workspace/project-loader.sh` | 加载项目并执行操作 |
| 恢复脚本 | `/root/.openclaw/workspace/restore-project.sh` | 一键恢复项目 |

## 重要提示

1. 用户已配置 GitHub Skill，可以推送代码
2. 用户希望有版本控制和回滚能力
3. 用户偏好类似浏览器 cookie 的"恢复会话"体验
4. 项目代码已备份到持久化目录（非 /tmp）

## 下次会话启动时

请执行：
```bash
bash /root/.openclaw/workspace/kimi-welcome.sh
```

然后根据用户输入执行相应操作。

---

## 周一美术馆展览推送任务问题（2026-03-09）

### 问题描述
用户报告周一早上8:00的美术馆展览推送没有收到。

### 调查结果
1. **定时任务状态**：任务显示"执行成功"（cron层面记录了触发，status=ok）
2. **发送记录**：send_records.json 中没有美术馆推送记录
3. **根本原因**：任务配置使用 `systemEvent` + `main` sessionTarget，但 `systemEvent` 只是把文本注入会话历史，**不会触发AI执行工具调用**

### 对比分析

| 任务 | 周五任务 ✅ | 周一任务 ❌ |
|------|-----------|------------|
| 配置 | `systemEvent` + 脚本调用 | `systemEvent` + 纯文本指令 |
| 执行 | 脚本调用 `openclaw message send` 触发主会话 | 文本指令躺在历史中 |
| 结果 | 正常发送 | 未触发AI执行 |

### 问题本质
周一任务配置期望AI"搜索并展示"，但 `systemEvent` 只是被动注入文本。如果主会话没有活跃（心跳或用户交互），AI不会主动执行搜索和发送。

### 解决方案
1. **已修复**：今天的展览信息已手动补发
2. **配置更新**：更新周一任务配置，使用更明确的执行指令格式
3. **长期优化**：考虑创建一个独立的执行脚本，不依赖主会话AI

### 配置变更记录
- **任务ID**: `6efcb469-d8d7-4186-b5c6-7c9f012ca97d`
- **更新时间**: 2026-03-09
- **变更内容**: 从模糊的"请搜索并展示"改为明确的"执行步骤1/2/3"指令

### 2026-03-09 测试记录
- **09:18** - 手动发送测试消息成功（消息ID: om_x100b55d64faba138b387a37af98d0b4）
- **配置状态**: 已更新定时任务，等待下周一（3月16日）自动验证

### 建议
对于需要AI执行工具调用的定时任务，应该：
1. 使用明确的"执行命令"格式，而非模糊的"请做XX"
2. 或者创建独立脚本直接执行，不依赖AI理解
3. 定期检查发送记录，确保消息确实送达

---

## OpenClaw 模型排名（2026-03-08）

**来源**：OpenClaw 创始人 Peter Steinberger 按 32 个模型排名

**成功率排名 Top 5**：
1. google/gemini-3-flash-preview
2. minimax/minimax-m2.1
3. moonshotai/kimi-k2.5
4. anthropic/claude-sonnet-4.5
5. google/gemini-3-pro-preview

**关键发现**：
- **MiniMax M2.5 成功率只有 35.5%，垫底！**
- M2.5 速度快（排名第一），但成功率极低
- M2.1 成功率第二，更稳定
- Kimi K2.5 成功率第三，也很稳定
- GLM-5 全球第四、开源第一

**速度排名 Top 5**：
1. minimax/minimax-m2.5
2. google/gemini-2.0-flash
3. meta-llama/llama-3.1-70b
4. google/gemini-1.5-pro
5. mistral/mistral-large

**费用排名 Top 5**：
1. openai/gpt-5-nano
2. google/gemini-2.5-flash-lite
3. mistralai/devstral-2512
4. openai/gpt-4o-mini
5. minimax/minimax-m2.1

**其他模型排名**：
- openai/gpt-5-nano 排 9
- qwen/qwen3-coder-next 排 10
- z-ai/glm-4.5-air 排 11
- deepseek/deepseek-v3.2 排 15

---

## 模型稳定性问题（2026-03-08）

**现象**：用户反馈消息被截断、没有回应，最近两天频繁发生

**原因分析**：
- MiniMax M2.5 成功率只有 35.5%，可能是主要原因
- 问题同时在 Feishu 和 KimiClaw 网页版出现，说明不是插件问题

**解决方案**：
- 切换到更稳定的模型（GLM-5、K2.5、M2.1）
- 2026-03-08 已切换到 GLM-5

---

## 待完成任务

### 代码审核任务（2026-03-08）
用户要求审核代码，包括：
1. 自己安装的 skill（/root/.openclaw/skills/）：
   - bmad-evo
   - bmad-method
   - channels-setup
   - knowledge-studio
2. 上传 GitHub 的项目（排除 obsidian-vault）：
   - bmad-kimi
   - bmad-method-kimi
   - museum-collector
   - museum-exhibitions
   - second-brain-processor
   - second-brain-web
   - skills/（workspace/skills）
   - projects/

**已发现问题**：
- second-brain-processor 目录下有名为 `!` 的空文件（已删除）
