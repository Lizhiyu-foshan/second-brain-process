#!/usr/bin/env python3
"""
凌晨 5:00 任务执行验证脚本

用途：
1. 检查昨晚的任务是否真正执行
2. 如果未执行，发送告警
3. 可以手动触发补执行

使用：
python3 verify_morning_task.py [--force-run]
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

LOG_FILE = Path("/tmp/morning_process_execution.log")
ERROR_FILE = Path("/tmp/morning_process_execution.error")
WRAPPER_SCRIPT = Path("/root/.openclaw/workspace/second-brain-processor/run_morning_wrapper.sh")

def check_last_execution():
    """检查最后一次执行时间"""
    if not LOG_FILE.exists():
        return None, "日志文件不存在"
    
    try:
        content = LOG_FILE.read_text()
        # 查找状态行
        last_status = None
        last_time = None
        
        for line in reversed(content.split('\n')):
            if '状态：SUCCESS' in line or '状态：FAILED' in line:
                last_status = "成功" if 'SUCCESS' in line else "失败"
            if '完成时间：' in line or '失败时间：' in line:
                time_str = line.split('：')[1].strip()
                last_time = datetime.fromisoformat(time_str)
                if last_status:
                    return last_time, last_status
                return last_time, "未知"
        
        # 如果没有找到，返回 STARTED 状态
        for line in reversed(content.split('\n')):
            if '启动时间：' in line:
                time_str = line.split('：')[1].strip()
                return datetime.fromisoformat(time_str), "已启动（未完成）"
        
        return None, "日志格式异常"
    except Exception as e:
        return None, f"读取失败：{e}"

def send_alert(message: str):
    """发送告警消息"""
    try:
        # 使用现有的发送脚本
        send_script = Path("/root/.openclaw/workspace/second-brain-processor/send_feishu.py")
        if send_script.exists():
            import subprocess
            subprocess.run([
                str(send_script),
                "⚠️ 凌晨 5:00 任务执行告警",
                message
            ], timeout=30)
            print(f"✅ 告警已发送")
        else:
            print(f"⚠️ 发送脚本不存在，告警内容：\n{message}")
    except Exception as e:
        print(f"⚠️ 告警发送失败：{e}")

def main(force_run: bool = False):
    """主函数"""
    print("=== 凌晨 5:00 任务执行验证 ===")
    print(f"检查时间：{datetime.now().isoformat()}")
    
    # 检查最后一次执行
    last_time, status = check_last_execution()
    
    if last_time is None:
        print(f"❌ 未找到执行记录：{status}")
        alert = f"""⚠️ **凌晨 5:00 任务执行告警**

检查时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}
状态：**未找到执行记录**
详情：{status}

可能原因：
1. 定时任务未触发
2. 脚本执行失败
3. 日志文件丢失

建议操作：
1. 检查 cron 任务状态
2. 手动执行验证脚本
3. 查看系统日志
"""
        send_alert(alert)
        
        if force_run:
            print("\n🔄 强制执行任务...")
            import subprocess
            result = subprocess.run([str(WRAPPER_SCRIPT)], capture_output=False)
            if result.returncode == 0:
                print("✅ 补执行成功")
            else:
                print(f"❌ 补执行失败，退出码：{result.returncode}")
        
        return False
    
    # 检查是否是今天的执行（允许 30 小时误差）
    now = datetime.now()
    # 确保时区一致
    if last_time.tzinfo is not None and now.tzinfo is None:
        last_time = last_time.replace(tzinfo=None)
    
    time_diff = now - last_time
    
    print(f"✅ 最后执行时间：{last_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   执行状态：{status}")
    print(f"   距今：{time_diff.total_seconds() / 3600:.1f}小时")
    
    # 如果超过 30 小时未执行，发送告警
    if time_diff > timedelta(hours=30):
        alert = f"""⚠️ **凌晨 5:00 任务执行告警**

检查时间：{now.strftime('%Y-%m-%d %H:%M')}
最后执行：{last_time.strftime('%Y-%m-%d %H:%M:%S')}
距今：**{time_diff.total_seconds() / 3600:.1f}小时**
状态：**超时未执行**

建议操作：
1. 检查 cron 任务是否正常
2. 查看执行日志：/tmp/morning_process_execution.log
3. 手动执行：bash /root/.openclaw/workspace/second-brain-processor/run_morning_wrapper.sh
"""
        send_alert(alert)
        return False
    
    print("✅ 任务执行正常")
    return True

if __name__ == "__main__":
    force = "--force-run" in sys.argv
    success = main(force)
    sys.exit(0 if success else 1)
