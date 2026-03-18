# 定时任务流程微调（2026-03-17）

## 核心决策
**原则**：系统不主动调用 AI，用户确认后再触发深度处理

## 新流程

### 清晨 5:00 - 对话整理（无 AI）
**触发**：定时任务自动执行  
**操作**：
1. 读取昨日对话记录
2. 按主题分类保存原始内容
3. 保存到 Obsidian Vault
4. **不调用 AI**，仅做基础整理

**脚本**：`/root/.openclaw/workspace/second-brain-processor/process_raw.py`  
**耗时**：秒级完成  
**输出**：原始笔记（待 AI 处理）

**定时任务 ID**：`7df3087c-1492-4b4c-874e-cf07ab874c25`

---

### 8:30 - 复盘报告推送（待确认模式）
**触发**：定时任务自动执行  
**操作**：
1. 检查是否有待整理的笔记
2. 发送飞书消息给用户："有 X 条笔记待 AI 整理，是否现在处理？"
3. **等待用户确认**
4. 用户确认后，触发 AI 整理脚本

**脚本**：`/root/.openclaw/workspace/second-brain-processor/request_confirmation.py`  
**消息模板**：
```
📝 有待整理内容

- 对话笔记：X 条
- 待读笔记：Y 条

回复"整理"开始 AI 处理，预计耗时 2-5 分钟。
```

**定时任务 ID**：`35ff007b-d995-4650-a90f-f3c973a386ca`（已更新）

---

### 用户确认后 - AI 深度整理
**触发**：用户回复"整理"  
**操作**：
1. 加载待处理笔记
2. 调用 AI（Kimi K2.5）进行深度分析
3. 提取核心观点、Key Takeaway、关联知识
4. 生成结构化报告
5. 推送到 GitHub 仓库

**脚本**：
- `/root/.openclaw/workspace/second-brain-processor/handle_user_confirm.py`（消息处理器）
- `/root/.openclaw/workspace/second-brain-processor/ai_process_and_push.py --confirmed`（AI 处理）

**模型**：Kimi K2.5（深度思考）  
**耗时**：2-5 分钟  
**输出**：
- 结构化笔记（Obsidian）
- GitHub 推送（obsidian-vault 仓库）
- 自我进化报告（.learnings/）

---

## 用户交互方式

### 确认整理
回复以下任一关键词：
- "整理"
- "开始整理"
- "AI 处理"
- "开始"

### 跳过今天
回复：
- "跳过"
- "明天再说"

### 查看待整理内容
回复：
- "待整理"
- "有哪些笔记"

---

## 消息处理器

当用户回复消息时，可以通过以下方式触发处理：

```bash
# 手动触发
python3 /root/.openclaw/workspace/second-brain-processor/message_handler.py "整理"

# 或集成到 Feishu Webhook
# 在 Webhook 处理逻辑中调用 message_handler.py
```

---

## 配置文件更新

### 5:00 定时任务（新增）
```json
{
  "id": "7df3087c-1492-4b4c-874e-cf07ab874c25",
  "name": "对话整理（原始）",
  "schedule": { "kind": "cron", "expr": "0 5 * * *" },
  "payload": { 
    "kind": "systemEvent", 
    "text": "python3 /root/.openclaw/workspace/second-brain-processor/process_raw.py"
  },
  "sessionTarget": "main"
}
```

### 8:30 定时任务（已更新）
```json
{
  "id": "35ff007b-d995-4650-a90f-f3c973a386ca",
  "name": "每日复盘报告推送",
  "schedule": { "kind": "cron", "expr": "30 8 * * *" },
  "payload": { 
    "kind": "systemEvent", 
    "text": "python3 /root/.openclaw/workspace/second-brain-processor/request_confirmation.py"
  },
  "sessionTarget": "main"
}
```

---

## 优势

1. **系统克制**：不主动调用 AI，避免资源浪费和消息丢失
2. **用户可控**：何时整理、整理什么，完全由用户决定
3. **体验优化**：清晨任务秒级完成，深度整理在用户需要时执行
4. **质量保证**：AI 整理后立即推送 GitHub，确保内容新鲜度
5. **流程清晰**：5:00 整理 → 8:30 请求 → 用户确认 → AI 处理 → GitHub 推送

---

## 记录时间
2026-03-17 13:00
**决策者**：郎瀚威

## 执行状态
- [x] 创建 process_raw.py（5:00 无 AI 整理）
- [x] 创建 request_confirmation.py（8:30 请求确认）
- [x] 创建 ai_process_and_push.py（AI 深度处理）
- [x] 创建 handle_user_confirm.py（用户确认处理器）
- [x] 创建 message_handler.py（消息处理器）
- [x] 更新 8:30 定时任务配置
- [x] 创建 5:00 定时任务
- [ ] 集成 Feishu Webhook 消息监听（待实现）
- [ ] 测试完整流程（等待明天 5:00 和 8:30）
