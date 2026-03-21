# Second Brain Processor

第二大脑处理器 - 自动化知识管理流水线

## 功能

- **对话整理**: 每日5:00自动整理OpenClaw对话记录
- **文章剪藏**: 微信/知乎文章自动获取和整理
- **AI摘要**: 自动生成核心观点和关联思考
- **GitHub同步**: 自动推送到Obsidian Vault仓库

## 安装

```bash
git clone https://github.com/Lizhiyu-foshan/second-brain-process.git
cd second-brain-process
```

## 依赖

```bash
pip install requests beautifulsoup4 markdown
```

## 配置

编辑 `config.py`:

```python
VAULT_DIR = "/path/to/your/obsidian-vault"
QUEUE_DIR = "/path/to/queue"
```

## 核心脚本

| 脚本 | 功能 | 定时 |
|------|------|------|
| `process_raw.py` | 整理原始对话 | 每日5:00 |
| `process_all.py` | 处理待读队列 | 手动/定时 |
| `git_sync.py` | GitHub同步 | 自动 |
| `queue_response_handler.py` | 响应用户指令 | - |

## 使用

### 命令行

```bash
# 整理昨日对话
python3 process_raw.py

# 处理待读队列（批量）
python3 process_all.py --batch summary

# 同步到GitHub
python3 git_sync.py
```

### 队列响应

用户回复以下指令触发处理:
- `A1` / `A 1` - 原文保存
- `A2` / `A 2` / `A` - 主体+核心观点
- `A3` / `A 3` - 精简摘要
- `AI自动整理` - AI自动处理
- `推迟` - 延迟处理

## 目录结构

```
second-brain-process/
├── lib/                    # 核心库
│   └── message_index.py   # 增量索引
├── queue/                  # 待读队列
├── process_raw.py         # 对话整理
├── process_all.py         # 队列处理
├── git_sync.py           # Git同步
├── queue_response_handler.py  # 响应处理
├── update_dashboard.py    # Dashboard更新
└── config.py             # 配置
```

## 定时任务

```bash
# 每日5:00整理对话
0 5 * * * cd /path/to/second-brain-process && python3 process_raw.py

# 每日8:30生成报告
30 8 * * * cd /path/to/second-brain-process && python3 daily_complete_report.py
```

## 版本

v3.0 - 2026-03-21
- 增量索引系统
- 7天滚动删除
- AI自动整理

## License

MIT

---

## 依赖组件

### Incremental Message Index System
本项目的增量处理功能依赖独立的增量索引系统：
- 仓库: https://github.com/Lizhiyu-foshan/Incremental-Message-Index-System
- 功能: 高性能消息索引管理，支持自动重建和完整性验证
