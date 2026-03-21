# 第二大脑内容处理系统设计方案 v2.0

> 整合定时任务、文章处理、会话处理的完整流程
> 版本日期：2026-03-21

---

## 一、目录结构定义（严格遵循）

```
obsidian-vault/
├── 00-Inbox/              # 待整理入口（原始对话记录）
├── 01-Discussions/        # 主题讨论精华（按主题整理）
│   └── 命名格式：主题内容_整理时间.md
├── 02-Conversations/      # 对话记录（按时间整理）
│   └── 命名格式：YYYY-MM-DD_主题.md
├── 03-Articles/           # 文章剪藏（按来源整理）
│   ├── WeChat/            # 微信文章
│   ├── Zhihu/             # 知乎文章
│   └── Substack/          # Substack文章
├── 04-Documents/          # 关键文档
├── 05-Videos/             # 视频内容
├── 06-Ebooks/             # 电子书笔记
└── 99-Meta/               # 格式模板
```

**命名规范**：
- 01-Discussions：`主题内容_整理时间.md`（按主题）
- 02-Conversations：`日期_主题.md`（按时间）
- 03-Articles：`日期_标题.md`（按来源子目录）

---

## 二、处理流程总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              内容入口                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  入口A：定时任务    │  入口B：文章链接    │  入口C：主动要求    │  入口D：自动处理  │
│  （5点+8点半）      │  （发送链接）       │  （说"整理"）       │  （定时任务超时） │
└───────────┬─────────┴───────────┬─────────┴───────────┬─────────┴───────────┬──┘
            │                     │                     │                     │
            ▼                     ▼                     ▼                     ▼
┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐
│   5:00 原始收集    │   │   保存到03-Articles│   │   判断讨论类型     │   │   提醒自动处理     │
│   保存到00-Inbox   │   │   等待讨论触发     │   │   （AI判断）       │   │   （回复"自动"）   │
└─────────┬─────────┘   └─────────┬─────────┘   └─────────┬─────────┘   └─────────┬─────────┘
          │                       │                       │                     │
          ▼                       ▼                       ▼                     ▼
┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐
│   8:30 复盘报告    │   │   用户发起讨论     │   │   深度讨论/普通    │   │   采用入口C方式    │
│   + 提示"整理"     │   │   或设置定时讨论   │   │   讨论分类        │   │   自动分析分类     │
└─────────┬─────────┘   └─────────┬─────────┘   └─────────┬─────────┘   └─────────┬─────────┘
          │                       │                       │                     │
          ▼                       ▼                       │                     │
┌───────────────────┐   ┌───────────────────┐           │                     │
│   回复"整理"触发   │   │   讨论结束后      │           │                     │
│   统一处理        │   │   说"整理"触发    │           │                     │
└───────────────────┘   └───────────────────┘           │                     │
          │                       │                       │                     │
          └───────────────────────┴───────────────────────┴─────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AI深度整理（四步法）                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   第一步：主题精华识别                                                        │
│   • 调用 kimi-coding/k2p5 分析对话内容                                         │
│   • 识别深度讨论（哲学/社会学/系统论/技术冲击/系统影响）                         │
│   • 不硬编码轮数，AI判断内容价值                                               │
│   • 输出：候选主题列表 + 对应原始对话片段                                        │
│                                                                              │
│   第二步：生成主题讨论精华                                                     │
│   • 对每个候选主题调用AI生成结构化内容                                          │
│   • 包含：一句话摘要、核心要点、关联思考、关联链接                               │
│   • 来源标注：文章链接 或 对话日期                                              │
│   • 输出：主题讨论精华.md 文件                                                 │
│                                                                              │
│   第三步：剩余内容整理                                                         │
│   • 提取精华后的剩余对话按主题整理                                              │
│   • 生成对话记录文件                                                          │
│   • 输出：对话记录.md 文件                                                    │
│                                                                              │
│   第四步：分类推送                                                             │
│   • 主题讨论精华 → 01-Discussions/                                             │
│   • 对话记录 → 02-Conversations/                                               │
│   • 文章相关内容 → 03-Articles/ 对应子目录                                      │
│   • Git提交并推送                                                             │
│   • 告知用户生成的主题讨论精华文件                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 三、详细流程设计

### 3.1 入口A：定时任务处理

#### 5:00 原始对话收集

**脚本**：`collect_raw_conversations.py`

**功能**：
- 收集过去24小时对话
- 保存到 `00-Inbox/YYYY-MM-DD_conversations_raw.md`
- **不分析、不AI处理**（仅收集原材料）

**输出示例**：
```markdown
---
date: 2026-03-21
type: 原始对话记录
source: 自动收集
---

# 2026-03-21 原始对话记录

## 时间段1：08:30-09:00
[用户] 复盘报告内容...
[AI] 收到，以下是昨天...

## 时间段2：10:00-11:30
[用户] 分享文章链接...
[AI] 已保存文章...
...
```

#### 8:30 复盘报告 + 整理提示

**脚本**：`daily_complete_report.py`

**功能**：
1. 生成复盘报告（现有功能）
2. **新增**：追加整理提示：

```
📋 今日对话已收集到 00-Inbox/2026-03-21_conversations_raw.md

如需AI深度整理，请回复"整理"
整理内容包括：
• 识别主题讨论精华
• 生成结构化摘要
• 分类推送到对应目录

⏰ 15分钟内回复有效，超时将保留在Inbox等待下次处理
```

3. **新增**：设置待处理队列
```python
queue_response_handler.add_pending(
    type="daily_conversation_organize",
    raw_file="00-Inbox/2026-03-21_conversations_raw.md",
    timeout_minutes=15
)
```

---

### 3.2 入口B：文章链接处理

#### 用户发送文章链接

**触发关键词**：包含 `http://`、`https://`、`zhuanlan.zhihu.com`、`mp.weixin.qq.com` 等

**处理流程**：

```python
def handle_article_link(url):
    # 1. 识别来源
    source = identify_source(url)  # Zhihu/WeChat/Substack/Other
    
    # 2. 获取文章内容（如有API）或等待用户复制
    content = fetch_or_wait_content(url)
    
    # 3. 保存到对应目录
    filename = f"{date}_{title}.md"
    save_to(f"03-Articles/{source}/", filename, content)
    
    # 4. 询问用户
    send_message(f"""
    文章已保存到 03-Articles/{source}/{filename}
    
    请选择：
    1. 现在讨论（回复"讨论"）
    2. 稍后讨论（回复"稍后 X小时"设置定时任务）
    3. 自动处理（回复"自动"，AI将自动整理分类）
    """)
    
    # 5. 设置待处理队列
    queue_response_handler.add_pending(
        type="article_discussion",
        article_file=f"03-Articles/{source}/{filename}",
        url=url
    )
```

#### 文章讨论结束后整理

**触发**：用户在文章讨论后说"整理"

**AI判断逻辑**：

```python
def analyze_discussion_depth(messages, article_url=None):
    """
    调用 kimi-coding/k2.5 判断讨论深度
    """
    prompt = f"""
    分析以下对话内容，判断是否涉及：
    - 哲学思考（存在论、认识论、伦理学等）
    - 社会学洞察（社会结构、群体行为、文化演变等）
    - 系统论思考（复杂系统、涌现、反馈循环等）
    - 重大技术革新对社会的冲击
    - 对系统长远运行有重大影响的设计决策
    
    对话内容：
    {messages}
    
    请返回：
    1. 讨论类型：深度讨论 / 普通讨论
    2. 置信度：high / medium / low
    3. 理由：简要说明判断依据
    4. 建议分类：主题讨论精华 / 文章相关内容
    """
    
    result = call_kimi_coding_k2_5(prompt)
    return parse_analysis(result)
```

**处理分支**：

```
if 深度讨论:
    # 进入四步法整理
    # 最终输出到 01-Discussions/
    generate_discussion_essence()
else:
    # 普通讨论
    # 整理后保存到 03-Articles/{source}/ 目录
    # 作为文章的补充讨论
    generate_article_discussion()
```

---

### 3.3 入口C：主动要求整理

**触发**：用户在任意对话结束后说"整理"

**处理**：
1. AI判断对话内容类型（深度讨论 / 普通讨论）
2. 深度讨论 → 进入四步法整理 → 01-Discussions/
3. 普通讨论 → 直接整理 → 02-Conversations/

---

### 3.4 入口D：定时任务自动处理

**场景**：文章链接设置"稍后 X小时"定时讨论，但用户回复"没有时间"

**流程**：

```
定时任务触发
  ↓
发送提醒："您之前保存的文章已到讨论时间，是否开始讨论？"
  ↓
用户回复"没有时间"
  ↓
等待10分钟 → 发送二次提醒：
"检测到您没有时间讨论，是否需要AI自动处理？
回复：
• '自动' → AI自动分析分类整理
• '跳过' → 保留文章，等待下次讨论
• 超时15分钟默认跳过"
  ↓
用户回复"自动"
  ↓
采用【入口C】方式处理：
  1. AI分析文章内容
  2. 判断是否为深度讨论（哲学/社会学/系统论/技术冲击等）
  3. 深度讨论 → 四步法整理 → 01-Discussions/
  4. 普通讨论 → 整理后 → 03-Articles/{source}/
```

**实现代码**：

```python
def handle_scheduled_discussion_timeout(article_file, url):
    """
    处理定时讨论超时后的自动处理提醒
    """
    # 发送二次提醒
    send_message(f"""
    ⏰ 文章讨论提醒
    
    您之前保存的文章：{article_file}
    检测到您没有时间讨论。
    
    请选择：
    • 回复"自动" → AI自动分析分类整理
    • 回复"跳过" → 保留文章，等待下次讨论
    
    ⏱️ 15分钟内回复有效
    """)
    
    # 设置待处理队列
    queue_response_handler.add_pending(
        type="article_auto_process",
        article_file=article_file,
        url=url,
        timeout_minutes=15
    )

def handle_auto_process_confirmation(user_input, pending):
    """
    处理自动处理确认
    """
    if user_input == "自动":
        # 读取文章内容
        article_content = read_file(pending["article_file"])
        
        # AI分析文章深度
        analysis = analyze_article_depth(article_content, pending["url"])
        
        if analysis["type"] == "深度讨论":
            # 采用入口C方式（四步法）
            run_four_step_process(
                content=article_content,
                source_type="文章自动处理",
                source_url=pending["url"]
            )
            return f"已自动处理，生成主题讨论精华，请查看 01-Discussions/"
        else:
            # 普通文章，整理后保存到03-Articles
            generate_article_summary(
                article_file=pending["article_file"],
                content=article_content
            )
            return f"已自动处理，文章整理完成，保存在 03-Articles/"
    
    elif user_input == "跳过":
        return "已跳过，文章保留在 03-Articles/ 等待下次讨论"
    
    else:
        return "请回复'自动'或'跳过'"
```

---

## 四、AI深度整理四步法详解

### 4.1 第一步：主题精华识别

**脚本**：`step1_identify_essence.py`

**模型**：kimi-coding/k2.5（长文本处理+逻辑分析）

**输入**：原始对话文件（00-Inbox/*.md 或 文章讨论记录）

**Prompt设计**：
```python
IDENTIFY_ESSENCE_PROMPT = """
你是一位深度对话分析专家。请分析以下对话内容：

【对话内容】
{conversation_content}

【分析任务】
1. 识别所有涉及以下领域的深度讨论：
   - 哲学：存在论、认识论、伦理学、自由意志等
   - 社会学：社会结构、群体行为、文化演变、价值体系等
   - 系统论：复杂系统、涌现、反馈循环、架构设计等
   - 技术冲击：AI对人类社会、工作、认知的深远影响
   - 系统设计：对长期运行有重大影响的技术决策

2. 不看重对话轮数，看重内容深度和思想价值
   - 10轮深度讨论 > 50轮闲聊
   - 一个顿悟时刻 > 大量重复确认

3. 对每处识别出的精华，提取：
   - 主题名称（简洁有力）
   - 对话片段（原文引用）
   - 核心价值（一句话概括）
   - 置信度（high/medium/low）

4. 如果对话中包含文章链接的讨论，标注来源链接

【输出格式】
## 候选主题1：[主题名称]
- 置信度：high/medium/low
- 对话片段：
  [引用原文，保留发言人]
- 核心价值：[一句话概括]
- 来源类型：文章讨论 / 纯对话
- 来源链接：（如有）

## 候选主题2：...

如果没有识别到深度讨论，返回"未识别到主题讨论精华"
"""
```

**输出**：候选主题列表（JSON格式）

```json
{
  "topics": [
    {
      "name": "AGENTS.md治理进化",
      "confidence": "high",
      "fragments": ["用户原文...", "AI原文..."],
      "core_value": "从应激修补到系统性设计的规则治理进化",
      "source_type": "纯对话",
      "source_url": null
    }
  ]
}
```

---

### 4.2 第二步：生成主题讨论精华

**脚本**：`step2_generate_essence.py`

**模型**：kimi-coding/k2.5

**输入**：第一步识别的候选主题 + 原始对话片段

**Prompt设计**：
```python
GENERATE_ESSENCE_PROMPT = """
基于以下对话片段，生成一份主题讨论精华文档。

【主题名称】{topic_name}

【原始对话片段】
{fragments}

【生成要求】
1. 一句话摘要（20字以内，点明核心洞察）
2. 核心要点（3-5个，每个配详细说明）
3. 关联思考（与其他主题、理论、实践的关联）
4. 关联链接（相关的文章、概念、资源）
5. 来源标注（文章链接 或 对话日期）

【输出格式】
---
date: {date}
type: 主题讨论精华
theme: {theme_category}
---

# {topic_name}

> {one_sentence_summary}

---

## 核心要点

### 1. [要点标题]
[详细说明，包含对话中的关键观点]

### 2. [要点标题]
...

## 关联思考

[与其他主题的关联、延伸思考、实践启示]

## 来源

- 类型：{source_type}
- 链接：{source_url or '对话日期：' + conversation_date}
- 整理时间：{date}

---
"""
```

**输出**：完整的主题讨论精华.md文件内容

---

### 4.3 第三步：剩余内容整理

**脚本**：`step3_organize_remainder.py`

**功能**：
- 从原始对话中移除已提取的精华片段
- 将剩余内容按主题分组
- 生成对话记录文件

**输出**：`02-Conversations/YYYY-MM-DD_主题.md`

---

### 4.4 第四步：分类推送

**脚本**：`step4_push_to_github.py`

**功能**：
1. 生成符合命名规范的文件名
   - 01-Discussions：`{主题名称}_{date}.md`
   - 02-Conversations：`{date}_{主题}.md`
2. 写入对应目录
3. Git提交：
```bash
git add -A
git commit -m "discussions: 提取主题讨论精华

新增：
- 01-Discussions/{文件名1}
- 01-Discussions/{文件名2}

整理：
- 02-Conversations/{文件名}

来源：{原始对话文件}"
git push origin main
```
4. 发送完成通知：
```
✅ 整理完成

生成主题讨论精华：
• 01-Discussions/{文件名1}
• 01-Discussions/{文件名2}

对话记录：
• 02-Conversations/{文件名}

已推送到GitHub
```

---

## 五、定时任务设计

### 5.1 文章定时讨论

**场景**：用户发送文章后回复"稍后 X小时"

**实现**：
```python
def schedule_article_discussion(article_file, hours_later):
    # 使用 OpenClaw Cron 设置一次性定时任务
    cron.add(
        schedule={"kind": "at", "at": f"{now + hours_later}"},
        payload={
            "kind": "agentTurn",
            "message": f"提醒：您之前保存的文章 {article_file} 已到达讨论时间。是否开始讨论？"
        }
    )
```

### 5.2 自动处理提醒

**场景**：定时讨论时间到，用户未响应

**流程**：
```
定时任务触发 → 发送提醒 → 等待10分钟 → 无响应
  ↓
发送二次提醒："是否自动处理？回复'自动'或'跳过'"
  ↓
用户回复"自动" → 调用AI判断深度 → 分类整理
用户回复"跳过" → 保留文章，等待下次
超时 → 保留文章，等待下次
```

---

## 六、queue_response_handler 扩展

**新增处理类型**：

```python
HANDLERS = {
    # 现有处理...
    "daily_conversation_organize": handle_daily_organize,
    "article_discussion": handle_article_discussion,
    "article_auto_process": handle_auto_process,
}

def handle_daily_organize(user_input, pending):
    if user_input == "整理":
        # 执行四步法
        run_four_step_process(pending["raw_file"])
        return "已开始AI深度整理，完成后将通知您"
    elif user_input == "跳过":
        return "已跳过，对话保留在00-Inbox等待下次处理"
    else:
        return "请回复'整理'或'跳过'"

def handle_article_discussion(user_input, pending):
    if user_input == "讨论":
        # 开始讨论
        start_article_discussion(pending["article_file"])
    elif user_input.startswith("稍后"):
        hours = parse_hours(user_input)
        schedule_discussion(pending["article_file"], hours)
    elif user_input == "自动":
        # 直接调用AI整理（相当于入口D立即触发）
        auto_process_article(pending["article_file"])
    elif user_input == "没有时间":
        # 转入入口D流程
        handle_scheduled_discussion_timeout(
            pending["article_file"], 
            pending["url"]
        )

def handle_auto_process(user_input, pending):
    """处理入口D的自动处理确认"""
    if user_input == "自动":
        # 读取文章内容
        article_content = read_file(pending["article_file"])
        
        # AI分析文章深度
        analysis = analyze_article_depth(article_content, pending["url"])
        
        if analysis["type"] == "深度讨论":
            # 采用入口C方式（四步法）
            run_four_step_process(
                content=article_content,
                source_type="文章自动处理",
                source_url=pending["url"]
            )
            return "已自动处理，生成主题讨论精华，请查看 01-Discussions/"
        else:
            # 普通文章，整理后保存到03-Articles
            generate_article_summary(
                article_file=pending["article_file"],
                content=article_content
            )
            return "已自动处理，文章整理完成，保存在 03-Articles/"
    
    elif user_input == "跳过":
        return "已跳过，文章保留在 03-Articles/ 等待下次讨论"
    
    else:
        return "请回复'自动'或'跳过'"
```

---

## 七、需要创建的文件清单

| 文件名 | 用途 | 调用时机 |
|--------|------|---------|
| `collect_raw_conversations.py` | 5:00原始收集 | 定时任务 |
| `daily_complete_report.py` | 8:30复盘报告 | 定时任务 |
| `step1_identify_essence.py` | 识别主题精华 | 四步法-第1步 |
| `step2_generate_essence.py` | 生成精华文档 | 四步法-第2步 |
| `step3_organize_remainder.py` | 整理剩余内容 | 四步法-第3步 |
| `step4_push_to_github.py` | 推送GitHub | 四步法-第4步 |
| `run_four_step_process.py` | 四步法主控 | 用户触发 |
| `article_handler.py` | 文章链接处理 | 用户发送链接 |
| `queue_response_handler.py` | 扩展现有文件 | 响应处理 |

---

## 八、总结：四个入口汇总

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              四个内容入口                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  入口A：每天定时任务                                                          │
│    • 5:00 收集原始对话 → 00-Inbox/                                           │
│    • 8:30 发送复盘报告 + 提示"整理"                                           │
│    • 用户回复"整理" → 触发四步法                                              │
│                                                                              │
│  入口B：文章链接处理                                                          │
│    • 用户发送文章链接 → 保存到 03-Articles/{来源}/                            │
│    • 用户选择：现在讨论 / 稍后X小时 / 自动处理                                  │
│    • 讨论结束后说"整理" → 触发四步法                                          │
│                                                                              │
│  入口C：主动要求整理                                                          │
│    • 任意对话结束后说"整理"                                                   │
│    • AI判断深度 → 深度讨论四步法 / 普通讨论直接整理                             │
│                                                                              │
│  入口D：定时任务自动处理（新增）                                               │
│    • 文章设置"稍后X小时"定时任务                                               │
│    • 用户回复"没有时间"                                                       │
│    • 提醒"是否自动处理？"                                                     │
│    • 用户回复"自动" → 采用入口C方式自动分析分类                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
        ┌──────────────────────────────┐
        │    统一处理：AI深度整理（四步法） │
        │    kimi-coding/k2.5 分析          │
        └──────────────┬───────────────┘
                       │
           ┌───────────┴───────────┐
           │                       │
           ▼                       ▼
    ┌─────────────┐          ┌─────────────┐
    │  深度讨论    │          │  普通讨论    │
    │ (哲学/社会学/│          │ (文章相关/   │
    │  系统论/技术 │          │  日常操作)   │
    │  冲击等)     │          │              │
    └──────┬──────┘          └──────┬──────┘
           │                       │
           ▼                       ▼
    ┌─────────────┐          ┌─────────────┐
    │  四步法整理  │          │  直接整理    │
    │ →01-Discuss │          │ →对应目录    │
    └─────────────┘          └─────────────┘
```

---

**待确认问题**：
1. 四步法的脚本是否按此设计实现？
2. 是否需要先实现一个最小可用版本（MVP）测试流程？
3. 文章链接的自动获取（爬虫）是否需要，还是用户手动复制内容？
