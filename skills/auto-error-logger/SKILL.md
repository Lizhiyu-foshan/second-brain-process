# auto-error-logger

## 概述
自动错误捕获与记录 Skill。在关键操作包装 try-catch，失败时自动写入 ERRORS.md，定期回顾错误模式。

## 背景
- **问题**：系统错误需要依赖用户反馈或手动检查才能发现，缺乏自动捕获和记录机制。
- **证据**：FEATURE_REQUESTS.md FR-20260305-001: 需要自动错误捕获机制
- **影响**：问题发现延迟，被动响应模式

## 核心功能

### 1. 错误捕获装饰器
```python
from auto_error_logger import catch_errors

@catch_errors(context="api_call", notify=True)
def call_external_api():
    # 如果失败，自动记录到 ERRORS.md
    # 可选：发送通知
    pass
```

### 2. 错误记录格式
自动写入 `.learnings/ERRORS.md`，格式：
```markdown
## ERR-YYYYMMDD-HHMMSS
- **时间**: 2026-03-15 04:45:00
- **操作**: api_call
- **错误类型**: ConnectionError
- **错误信息**: Connection refused
- **上下文**: {"url": "https://api.example.com"}
- **状态**: pending
```

### 3. 错误模式分析
定期分析 ERRORS.md，识别重复出现的错误模式。

## 使用方法

### 作为装饰器使用
```python
from auto_error_logger import catch_errors

@catch_errors(context="git_push", notify=True, retry=3)
def push_to_github():
    # Git 推送操作
    pass
```

### 作为上下文管理器使用
```python
from auto_error_logger import error_context

with error_context("database_query"):
    # 数据库操作
    pass
```

### 手动记录错误
```python
from auto_error_logger import log_error

try:
    risky_operation()
except Exception as e:
    log_error(e, context="risky_operation", metadata={"key": "value"})
```

## 定时任务建议
- **每日错误回顾**：每天早上 6:00 分析昨天的错误，识别需要关注的问题
- **错误模式检测**：每周检测重复出现的错误模式，建议修复方案

## 文件结构
```
auto-error-logger/
├── SKILL.md
├── scripts/
│   ├── auto_error_logger.py    # 核心模块
│   ├── error_analyzer.py       # 错误模式分析
│   └── test_error_logger.py    # 测试脚本
```

## 相关文档
- `.learnings/ERRORS.md` - 错误记录文件
- `FEATURE_REQUESTS.md` - 功能请求
- `AGENTS.md` - 规则9（错误记录机制）

## 版本历史
- v1.0.0 (2026-03-15): 初始版本，实现基础错误捕获和记录功能