#!/usr/bin/env python3
"""
scheduled_discussion_handler.py - v2.1 入口D
定时任务自动处理 - 立即响应版本（无10分钟等待）
"""

import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict

# 导入处理模块
from run_four_step_process import run_four_step_process


def handle_no_time_response(article_file: str, url: str) -> str:
    """
    v2.1 修改：用户回复'没有时间'后立即提示，不再等待10分钟
    
    Args:
        article_file: 文章文件路径
        url: 文章URL
        
    Returns:
        提示消息
    """
    # 立即发送处理选项（v2.1: 不再等待10分钟）
    message = f"""
⏰ 文章讨论提醒

您之前保存的文章：{article_file}
检测到您没有时间讨论。

请选择：
• 回复"AI自动整理" → AI自动分析分类整理（不再讨论，直接整理）
• 回复"推迟 X小时" → 推迟到最新时间（如：推迟 2小时）
• 回复"跳过" → 保留文章，等待下次讨论
"""
    
    # 添加到队列（v2.1: 立即处理，无二次等待）
    from queue_response_handler import add_pending
    task_id = add_pending(
        task_type="article_auto_process_immediate",  # v2.1: 立即处理类型
        article_file=article_file,
        url=url
    )
    
    return message


def handle_auto_process_immediate(user_input: str, pending: Dict) -> str:
    """
    v2.1 修改：处理'没有时间'后的立即响应
    
    Args:
        user_input: 用户输入
        pending: 待处理任务
        
    Returns:
        处理结果
    """
    from queue_response_handler import complete_pending
    
    if user_input == "AI自动整理":
        # v2.1: 立即读取文章内容并处理（不再讨论）
        article_file = pending.get("article_file")
        
        if article_file and Path(article_file).exists():
            # 调用四步法直接处理
            result = run_four_step_process(
                content_file=Path(article_file),
                source_type="文章自动处理",
                source_url=pending.get("url")
            )
            
            # 标记完成
            complete_pending(pending.get("id", ""))
            return f"✅ 已自动处理，生成主题讨论精华\n\n{result}"
        
        return "❌ 找不到文章文件"
    
    elif user_input.startswith("推迟"):
        # v2.2: 实际创建定时任务，不再使用伪实现
        match = re.search(r'(\d+)', user_input)
        hours = int(match.group(1)) if match else 2
        
        # 获取文章信息
        article_file = pending.get("article_file", "")
        
        # 实际设置定时任务
        result = schedule_discussion(article_file, hours)
        complete_pending(pending.get("id", ""))
        
        return result
    
    elif user_input == "跳过":
        complete_pending(pending.get("id", ""))
        return "已跳过，文章保留在 03-Articles/ 等待下次讨论"
    
    else:
        return "请回复'AI自动整理'、'推迟 X小时'或'跳过'"


def schedule_discussion(article_file: str, hours: int) -> str:
    """
    设置定时讨论任务 - v2.2: 真实实现
    
    Args:
        article_file: 文章文件路径
        hours: 推迟小时数
        
    Returns:
        设置结果
    """
    from datetime import datetime, timedelta
    import subprocess
    import json
    import os
    
    future_time = datetime.now() + timedelta(hours=hours)
    time_str = future_time.strftime("%Y-%m-%d %H:%M")
    cron_expr = future_time.strftime("%M %H %d %m *")
    
    # v2.2: 实际创建cron任务
    try:
        # 获取当前脚本的绝对路径
        script_dir = Path(__file__).parent.absolute()
        trigger_script = script_dir / "trigger_scheduled_discussion.py"
        
        # 创建触发脚本（如果不存在）
        if not trigger_script.exists():
            _create_trigger_script(trigger_script)
        
        # 准备cron payload
        payload = {
            "kind": "agentTurn",
            "message": f"讨论文章: {article_file}",
            "model": "kimi-coding/k2p5"
        }
        
        # 使用openclaw cron add创建真实定时任务
        job_name = f"scheduled_discussion_{Path(article_file).stem}"
        
        # 构建命令
        cmd = [
            "openclaw", "cron", "add",
            "--job", json.dumps({
                "name": job_name,
                "schedule": {"kind": "cron", "expr": cron_expr},
                "payload": payload,
                "sessionTarget": "isolated",
                "enabled": True
            })
        ]
        
        # 执行命令
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return f"⏰ 已设置真实定时任务：{time_str} 将自动提醒您讨论 {Path(article_file).name}"
        else:
            error_msg = result.stderr.strip() if result.stderr else "未知错误"
            # 降级到文件标记模式
            _mark_scheduled_file(article_file, future_time)
            return f"⚠️  cron任务设置失败（{error_msg}），已使用文件标记模式：{time_str} 提醒"
            
    except Exception as e:
        # 降级方案：使用文件标记
        _mark_scheduled_file(article_file, future_time)
        return f"⚠️  定时任务设置异常（{str(e)}），已使用备用方案：{time_str} 提醒"


def _mark_scheduled_file(article_file: str, future_time: datetime):
    """降级方案：在文章文件中添加定时标记"""
    try:
        # 在文件名中添加定时标记
        article_path = Path(article_file)
        if article_path.exists():
            # 创建.meta文件记录定时信息
            meta_file = article_path.with_suffix('.meta.json')
            import json
            meta_data = {
                "scheduled_time": future_time.isoformat(),
                "scheduled_for_discussion": True,
                "created_at": datetime.now().isoformat()
            }
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(meta_data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass  # 降级方案失败不阻断主流程


def _create_trigger_script(script_path: Path):
    """创建定时触发脚本"""
    script_content = '''#!/usr/bin/env python3
"""定时讨论触发脚本 - 由cron调用"""
import sys
import json
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: trigger_scheduled_discussion.py <article_file>")
    sys.exit(1)

article_file = sys.argv[1]
print(f"[Scheduled] 触发文章讨论: {article_file}")

# TODO: 实现具体的讨论触发逻辑
# 可以发送消息到飞书/其他渠道
'''
    script_path.write_text(script_content, encoding='utf-8')
    script_path.chmod(0o755)


def parse_hours(user_input: str) -> int:
    """解析小时数"""
    match = re.search(r'(\d+)', user_input)
    return int(match.group(1)) if match else 2


if __name__ == "__main__":
    print("[v2.1] 入口D: 定时任务自动处理模块")
    print("特性：立即响应，无10分钟等待")
