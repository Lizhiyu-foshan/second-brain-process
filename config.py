#!/usr/bin/env python3
"""
config.py - Second Brain Processor v2.1 配置
"""

from pathlib import Path

# 基础路径配置
WORKSPACE_DIR = Path("/root/.openclaw/workspace")
VAULT_DIR = WORKSPACE_DIR / "obsidian-vault"
SESSIONS_DIR = Path("/root/.openclaw/agents/main/sessions")

# v2.1 目录结构
INBOX_DIR = VAULT_DIR / "00-Inbox"
DISCUSSIONS_DIR = VAULT_DIR / "01-Discussions"
CONVERSATIONS_DIR = VAULT_DIR / "02-Conversations"
ARTICLES_DIR = VAULT_DIR / "03-Articles"

# 文章子目录
WECHAT_DIR = ARTICLES_DIR / "WeChat"
ZHIHU_DIR = ARTICLES_DIR / "Zhihu"
SUBSTACK_DIR = ARTICLES_DIR / "Substack"

# 数据目录
DATA_DIR = WORKSPACE_DIR / ".data"
QUEUE_FILE = DATA_DIR / "response_queue.json"
INDEX_PATH = DATA_DIR / "message_index.json"

# v2.1 配置参数
KEEP_DAYS = 7  # raw文件保留天数
TIMEOUT_MINUTES = 15  # 响应超时时间

# 模型配置
MODEL_DEEP_ANALYSIS = "kimi-coding/k2p5"  # 深度分析使用k2.5


def ensure_directories():
    """确保所有目录存在"""
    dirs = [
        INBOX_DIR,
        DISCUSSIONS_DIR,
        CONVERSATIONS_DIR,
        WECHAT_DIR,
        ZHIHU_DIR,
        SUBSTACK_DIR,
        DATA_DIR,
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    ensure_directories()
    print("✅ 目录结构已初始化")
    for d in [INBOX_DIR, DISCUSSIONS_DIR, CONVERSATIONS_DIR, ARTICLES_DIR]:
        print(f"  {d}")
