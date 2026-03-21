#!/bin/bash
# 凌晨5:00可靠任务 - 纯脚本执行，不依赖OpenClaw
# 设计原则：只做"必须可靠"的事，AI分析移到主会话

set -e

WORKSPACE="/root/.openclaw/workspace"
LOG_FILE="/tmp/morning_reliable.log"
DATE=$(date +%Y-%m-%d)
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)

echo "=== 凌晨5:00可靠任务 [$DATE] ===" > "$LOG_FILE"
echo "启动时间: $(date -Iseconds)" >> "$LOG_FILE"

# ============ 阶段1: 提取对话（纯脚本，100%可靠）============
echo "[$(date '+%H:%M:%S')] 阶段1: 提取昨日对话..." >> "$LOG_FILE"

# 查找昨天的会话文件
SESSION_DIR="$WORKSPACE"
CONV_DIR="$WORKSPACE/obsidian-vault/02-Conversations"
mkdir -p "$CONV_DIR"

# 提取需要处理的对话
python3 << 'PYTHON_EOF'
import json
import os
from pathlib import Path
from datetime import datetime, timedelta

workspace = Path("/root/.openclaw/workspace")
yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

# 查找昨天的会话文件
sessions_dir = Path("/root/.openclaw/agents/main/sessions")
extracted = []

for session_file in sessions_dir.glob("*.jsonl"):
    try:
        # 检查文件修改时间
        mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
        if mtime.strftime("%Y-%m-%d") == yesterday:
            # 提取对话内容（简化版）
            with open(session_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 解析jsonl，提取用户消息
            conversations = []
            for line in lines[-100:]:  # 只处理最近100行
                try:
                    data = json.loads(line)
                    if data.get('role') == 'user':
                        content = data.get('content', [])
                        if isinstance(content, list) and len(content) > 0:
                            text = content[0].get('text', '')
                            if text and len(text) > 20:  # 过滤短消息
                                conversations.append(text[:200])  # 截断
                except:
                    continue
            
            if conversations:
                extracted.append({
                    'session': session_file.name,
                    'count': len(conversations),
                    'preview': conversations[:3]
                })
    except Exception as e:
        continue

# 输出摘要
print(f"提取完成: 找到 {len(extracted)} 个会话")
for e in extracted:
    print(f"  - {e['session']}: {e['count']} 条对话")

# 保存待处理队列
queue_file = Path("/tmp/ai_analysis_queue.json")
queue_file.write_text(json.dumps({
    'date': yesterday,
    'sessions': extracted,
    'status': 'pending',
    'created_at': datetime.now().isoformat()
}, ensure_ascii=False, indent=2))

print(f"待处理队列已保存: {queue_file}")
PYTHON_EOF

if [ $? -eq 0 ]; then
    echo "[$(date '+%H:%M:%S')] ✅ 阶段1完成: 对话提取成功" >> "$LOG_FILE"
else
    echo "[$(date '+%H:%M:%S')] ❌ 阶段1失败: 对话提取出错" >> "$LOG_FILE"
    exit 1
fi

# ============ 阶段2: 创建基础文件（不依赖AI）============
echo "[$(date '+%H:%M:%S')] 阶段2: 创建基础对话文件..." >> "$LOG_FILE"

# 读取队列，为每个对话创建基础文件（无AI分析）
python3 << 'PYTHON_EOF'
import json
from pathlib import Path
from datetime import datetime, timedelta

queue_file = Path("/tmp/ai_analysis_queue.json")
conv_dir = Path("/root/.openclaw/workspace/obsidian-vault/02-Conversations")

if not queue_file.exists():
    print("队列为空，跳过")
    exit(0)

queue = json.loads(queue_file.read_text())
yesterday = queue['date']

created = 0
for session in queue.get('sessions', []):
    # 创建基础文件（占位，等待AI分析）
    base_name = session['session'].replace('.jsonl', '')
    file_path = conv_dir / f"{yesterday}_{base_name}.md"
    
    content = f"""---
date: {yesterday}
type: 聊天记录
tags: [对话, 自动归档, 待AI分析]
---

# {base_name}

## 统计
- 生成时间：{datetime.now().isoformat()}
- 对话数量：{session['count']}
- AI分析: ⏳ 待处理（将在主会话中完成）

---

## AI深度分析

⏳ **待AI分析**

此文件由凌晨5:00自动任务创建，AI深度分析将在用户下次交互时完成。

---

## 原始对话预览

"""
    
    for i, preview in enumerate(session['preview'][:5], 1):
        content += f"### 对话 {i}\n{preview}...\n\n"
    
    file_path.write_text(content, encoding='utf-8')
    created += 1

print(f"创建完成: {created} 个基础文件")

# 更新队列状态
queue['status'] = 'files_created'
queue['files_created'] = created
queue['files_created_at'] = datetime.now().isoformat()
queue_file.write_text(json.dumps(queue, ensure_ascii=False, indent=2))
PYTHON_EOF

if [ $? -eq 0 ]; then
    echo "[$(date '+%H:%M:%S')] ✅ 阶段2完成: 基础文件创建成功" >> "$LOG_FILE"
else
    echo "[$(date '+%H:%M:%S')] ⚠️ 阶段2部分失败" >> "$LOG_FILE"
fi

# ============ 阶段3: Git推送（100%可靠）============
echo "[$(date '+%H:%M:%S')] 阶段3: Git推送..." >> "$LOG_FILE"

cd "$WORKSPACE"
git add obsidian-vault/02-Conversations/
git commit -m "🤖 Morning backup: $YESTERDAY conversations (AI analysis pending)" || true

# 推送（带重试）
for i in 1 2 3; do
    if git push origin main 2>/dev/null; then
        echo "[$(date '+%H:%M:%S')] ✅ Git推送成功" >> "$LOG_FILE"
        break
    else
        echo "[$(date '+%H:%M:%S')] ⏳ Git推送失败，重试 $i/3..." >> "$LOG_FILE"
        git pull --rebase origin main 2>/dev/null || true
        sleep 5
    fi
done

# ============ 阶段4: 记录完成状态 ============
echo "[$(date '+%H:%M:%S')] 任务完成" >> "$LOG_FILE"
echo "状态: SUCCESS" >> "$LOG_FILE"
echo "完成时间: $(date -Iseconds)" >> "$LOG_FILE"

# 创建标记文件供验证
mkdir -p "$WORKSPACE/.learnings"
echo "$(date -Iseconds)" > "$WORKSPACE/.learnings/last_morning_task.txt"

echo "✅ 凌晨5:00任务完成"
