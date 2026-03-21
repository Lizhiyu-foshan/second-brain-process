---
name: second-brain
description: Second Brain Processor v2.1 - 知识整理系统。支持四个入口（定时任务/文章链接/主动整理/自动处理），四步法深度整理，增量索引，Dashboard自动更新。
homepage: https://github.com/Lizhiyu-foshan/second-brain-process
metadata:
  openclaw:
    emoji: 🧠
    version: 2.1.0
    requires:
      bins: ["python3", "git"]
---

# Second Brain Processor v2.1 🧠

第二大脑处理器 - 自动化知识管理流水线

## v2.1 新特性

- **入口D立即响应**: 回复"没有时间"后立即提示AI自动整理，不再等待10分钟
- **日期编号+7天滚动**: raw对话按`YYYY-MM-DD_raw.md`保存，保留7天自动清理
- **Dashboard自动更新**: 每次GitHub推送自动更新统计信息

## 目录结构

```
obsidian-vault/
├── 00-Inbox/              # 原始对话记录（7天滚动）
├── 01-Discussions/        # 主题讨论精华
├── 02-Conversations/      # 对话记录
├── 03-Articles/           # 文章剪藏
│   ├── WeChat/
│   ├── Zhihu/
│   └── Substack/
└── 99-Meta/               # 格式模板
```

## 四个入口

| 入口 | 触发方式 | 处理流程 |
|------|---------|---------|
| **A** | 5:00+8:30定时任务 | 收集→提示"整理"→四步法 |
| **B** | 发送文章链接 | 保存→讨论/稍后/自动处理 |
| **C** | 说"整理" | 直接四步法整理 |
| **D** | 回复"没有时间" | 立即提示→AI自动整理 |

## 四步法深度整理

1. **识别主题精华** - AI分析深度讨论
2. **生成精华文档** - 结构化输出
3. **整理剩余内容** - 对话记录
4. **分类推送GitHub** - 自动更新Dashboard

## 安装

```bash
git clone https://github.com/Lizhiyu-foshan/second-brain-process.git
cd second-brain-process
```

## 使用

```bash
# 手动运行
./second-brain collect      # 收集原始对话
./second-brain process      # 运行四步法整理
./second-brain article URL  # 处理文章链接
./second-brain sync         # 同步GitHub

# 定时任务
crontab -e
0 5 * * * /path/to/second-brain collect
30 8 * * * /path/to/second-brain report
```

## 文件清单

| 文件 | 用途 |
|------|------|
| `collect_raw_conversations.py` | 5:00原始收集 |
| `daily_complete_report.py` | 8:30复盘报告 |
| `step1_identify_essence.py` | 四步法-识别主题 |
| `step2_generate_essence.py` | 四步法-生成精华 |
| `step3_organize_remainder.py` | 四步法-整理剩余 |
| `step4_push_to_github.py` | 四步法-推送GitHub |
| `run_four_step_process.py` | 四步法主控 |
| `article_handler.py` | 文章链接处理 |
| `queue_response_handler.py` | 四个入口响应处理 |
| `scheduled_discussion_handler.py` | 入口D定时任务 |
| `lib/message_index.py` | 增量索引系统 |

## License

MIT
