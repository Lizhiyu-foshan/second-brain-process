---
name: second-brain
description: Second Brain Processor - 自动化知识管理流水线。定时整理对话记录、处理待读队列、AI摘要、GitHub同步，构建个人知识库。
homepage: https://github.com/Lizhiyu-foshan/second-brain-process
metadata:
  openclaw:
    emoji: 🧠
    requires:
      bins: ["python3", "git"]
      env: ["KIMI_API_KEY"]
---

# Second Brain Processor 🧠

自动化知识管理流水线，构建个人第二大脑。

## 功能

- **📅 定时整理**: 每日5:00自动整理OpenClaw对话记录
- **📥 文章剪藏**: 微信/知乎文章自动获取和整理  
- **🤖 AI摘要**: 自动生成核心观点和关联思考
- **📤 GitHub同步**: 自动推送到Obsidian Vault仓库
- **📊 Dashboard**: 自动更新知识库统计

## 安装

### 方式1: 直接克隆

```bash
git clone https://github.com/Lizhiyu-foshan/second-brain-process.git
cd second-brain-process
```

### 方式2: 通过 clawhub (推荐)

```bash
clawhub install second-brain
```

## 快速开始

### 1. 配置

编辑 `config.py`:

```python
VAULT_DIR = "/path/to/your/obsidian-vault"
QUEUE_DIR = "/path/to/queue"
```

### 2. 手动运行

```bash
# 整理昨日对话
python3 process_raw.py

# 处理待读队列
python3 process_all.py --batch summary

# 同步到GitHub
python3 git_sync.py
```

### 3. 设置定时任务

```bash
# 每日5:00整理对话
0 5 * * * cd /path/to/second-brain-process && python3 process_raw.py

# 每日8:30生成报告
30 8 * * * cd /path/to/second-brain-process && python3 daily_complete_report.py
```

## 命令参考

### 处理命令

| 命令 | 功能 | 示例 |
|------|------|------|
| `process_raw.py` | 整理昨日对话 | `python3 process_raw.py` |
| `process_incremental.py` | 增量处理（高性能） | `python3 process_incremental.py` |
| `process_all.py` | 处理待读队列 | `python3 process_all.py --batch summary` |
| `git_sync.py` | 同步到GitHub | `python3 git_sync.py` |

### 队列响应指令

用户回复以下指令触发处理:

| 指令 | 功能 |
|------|------|
| `A1` / `A 1` | 原文保存 |
| `A2` / `A 2` / `A` | 主体+核心观点 |
| `A3` / `A 3` | 精简摘要 |
| `AI自动整理` | AI自动处理 |
| `推迟` | 延迟2小时处理 |

## 目录结构

```
second-brain-process/
├── README.md                  # 说明文档
├── SKILL.md                   # Skill定义
├── config.py                  # 配置
├── process_raw.py            # 对话整理(v3日期编号)
├── process_incremental.py    # 增量索引处理
├── process_all.py            # 队列批量处理
├── queue_response_handler.py # 用户响应处理
├── git_sync.py               # GitHub同步+Dashboard更新
├── update_dashboard.py       # Dashboard更新
├── daily_complete_report.py  # 每日完整报告
├── verify_send_link.py       # 发送链路验证
└── lib/
    └── message_index.py      # 增量索引核心
```

## 核心特性

### 1. 增量索引系统
- 首次全量建立索引（~1秒）
- 后续只处理新增消息（~0.1秒）
- 解决定时任务超时问题

### 2. 7天滚动保留
- raw对话按日期保存：`YYYY-MM-DD_raw.md`
- 自动删除7天前的旧文件
- 保留历史但不堆积

### 3. 立即响应
- 移除10分钟等待
- 用户回复立即触发
- 支持"推迟"延迟处理

### 4. Dashboard自动更新
- 每次GitHub推送自动更新
- 统计各类笔记数量
- 显示今日新增

## 环境变量

| 变量 | 说明 | 必需 |
|------|------|------|
| `KIMI_API_KEY` | Kimi API密钥 | 是 |
| `GITHUB_TOKEN` | GitHub Token（可选） | 否 |

## 版本历史

- **v3.0** (2026-03-21) - Skill化改造，增量索引，7天滚动
- **v2.0** (2026-03-15) - 快速预检查，哈希去重
- **v1.0** (2026-03-01) - 初始版本

## License

MIT

## 依赖

- [Incremental-Message-Index-System](https://github.com/Lizhiyu-foshan/Incremental-Message-Index-System) - 增量索引核心（可选，用于高性能场景）
