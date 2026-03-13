#!/usr/bin/env python3
"""
Cron 任务监护系统 - 自愈型监控
功能：
1. 监控 cron 任务执行状态
2. 检测超时、失败等异常情况
3. 自动重试、补发、告警
4. 生成监控报告

设计原则：
- 不依赖单一检查点，多维度验证
- 异常时主动干预，而非被动等待
- 所有操作记录日志，可追溯
"""

import json
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# 配置
WORKSPACE = Path("/root/.openclaw/workspace")
LOG_DIR = WORKSPACE / "cron-monitor"
LOG_DIR.mkdir(exist_ok=True)

# 任务定义
MONITORED_JOBS = {
    "35ff007b-d995-4650-a90f-f3c973a386ca": {
        "name": "每日复盘报告推送",
        "schedule": "8:30",
        "expected_duration": 30,  # 秒
        "max_retries": 2,
        "auto_recover": True,  # 失败时自动补发
        "notify_on_failure": True
    },
    "53918d8d-df68-49cc-bdf4-1fa6ca1c39ed": {
        "name": "每日待确认列表推送",
        "schedule": "23:30",
        "expected_duration": 60,
        "max_retries": 2,
        "auto_recover": True,
        "notify_on_failure": True
    }
}

class CronMonitor:
    def __init__(self):
        self.log_file = LOG_DIR / f"monitor_{datetime.now().strftime('%Y%m%d')}.log"
        
    def log(self, level: str, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] [{level}] {message}"
        print(log_line)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')
    
    def get_cron_status(self) -> dict:
        """获取 cron 任务状态"""
        try:
            result = subprocess.run(
                ["openclaw", "cron", "list"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception as e:
            self.log("ERROR", f"获取 cron 状态失败: {e}")
        return {"jobs": []}
    
    def get_job_runs(self, job_id: str, limit: int = 5) -> list:
        """获取任务运行历史"""
        try:
            result = subprocess.run(
                ["openclaw", "cron", "runs", job_id, "--limit", str(limit)],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data.get("entries", [])
        except Exception as e:
            self.log("ERROR", f"获取任务 {job_id} 运行历史失败: {e}")
        return []
    
    def check_job_health(self, job_id: str, config: dict) -> dict:
        """检查单个任务健康状态"""
        runs = self.get_job_runs(job_id, limit=3)
        
        if not runs:
            return {
                "status": "unknown",
                "message": "无运行记录",
                "needs_action": False
            }
        
        latest = runs[0]
        status = latest.get("status", "unknown")
        error = latest.get("error", "")
        duration_ms = latest.get("durationMs", 0)
        duration_sec = duration_ms / 1000
        
        # 分析状态
        result = {
            "status": status,
            "last_run": latest.get("runAtMs"),
            "duration_sec": duration_sec,
            "error": error,
            "needs_action": False,
            "action_type": None,
            "message": ""
        }
        
        if status == "error":
            result["needs_action"] = True
            
            if "timed out" in error.lower():
                result["action_type"] = "timeout_recover"
                result["message"] = f"任务超时 ({duration_sec:.1f}s)，需要补发"
            else:
                result["action_type"] = "failure_recover"
                result["message"] = f"任务失败: {error}"
                
        elif status == "ok":
            # 检查执行时间是否异常
            expected = config.get("expected_duration", 30)
            if duration_sec > expected * 3:
                result["action_type"] = "slow_warning"
                result["message"] = f"执行时间异常: {duration_sec:.1f}s (预期 {expected}s)"
            else:
                result["message"] = f"正常完成，耗时 {duration_sec:.1f}s"
        
        return result
    
    def should_run_now(self, schedule: str) -> bool:
        """检查任务是否应该在当前时间运行"""
        now = datetime.now()
        hour, minute = map(int, schedule.split(':'))
        
        # 检查是否在计划时间后的 2 小时内
        scheduled_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if scheduled_time > now:
            scheduled_time -= timedelta(days=1)
        
        time_diff = (now - scheduled_time).total_seconds() / 60  # 分钟
        return 0 <= time_diff <= 120  # 计划时间后 2 小时内
    
    def send_daily_report_manually(self) -> bool:
        """手动触发每日复盘报告"""
        try:
            self.log("INFO", "开始手动补发每日复盘报告...")
            
            # 运行报告脚本
            result = subprocess.run(
                ["python3", str(WORKSPACE / "second-brain-processor/daily_report.py")],
                capture_output=True, text=True, timeout=60
            )
            
            if result.returncode != 0:
                self.log("ERROR", f"报告生成失败: {result.stderr}")
                return False
            
            report = result.stdout.strip()
            if not report:
                self.log("INFO", "报告为空（可能免打扰），跳过发送")
                return True
            
            # 发送到飞书
            send_result = subprocess.run(
                ["openclaw", "message", "send", 
                 "--target", "ou_363105a68ee112f714ed44e12c802051",
                 "--message", report],
                capture_output=True, text=True, timeout=30
            )
            
            if send_result.returncode == 0:
                self.log("INFO", "报告补发成功")
                return True
            else:
                self.log("ERROR", f"发送失败: {send_result.stderr}")
                return False
                
        except Exception as e:
            self.log("ERROR", f"补发过程异常: {e}")
            return False
    
    def send_notification(self, title: str, message: str):
        """发送通知到飞书"""
        try:
            full_message = f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n⚠️ {title}\n\n{message}\n\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
            
            subprocess.run(
                ["openclaw", "message", "send",
                 "--target", "ou_363105a68ee112f714ed44e12c802051",
                 "--message", full_message],
                capture_output=True, text=True, timeout=30
            )
        except Exception as e:
            self.log("ERROR", f"发送通知失败: {e}")
    
    def run_health_check(self) -> dict:
        """运行健康检查"""
        self.log("INFO", "="*50)
        self.log("INFO", "开始 Cron 任务健康检查")
        
        summary = {
            "checked_at": datetime.now().isoformat(),
            "jobs": [],
            "actions_taken": [],
            "alerts": []
        }
        
        for job_id, config in MONITORED_JOBS.items():
            self.log("INFO", f"\n检查任务: {config['name']} ({job_id[:8]}...)")
            
            health = self.check_job_health(job_id, config)
            
            job_summary = {
                "id": job_id,
                "name": config["name"],
                "health": health
            }
            summary["jobs"].append(job_summary)
            
            self.log("INFO", f"  状态: {health['status']}")
            self.log("INFO", f"  消息: {health['message']}")
            
            # 需要采取行动
            if health["needs_action"] and config.get("auto_recover"):
                if health["action_type"] in ["timeout_recover", "failure_recover"]:
                    # 检查是否在今天已经尝试过恢复
                    if self.should_run_now(config["schedule"]):
                        self.log("INFO", "  触发自动恢复...")
                        
                        if "复盘报告" in config["name"]:
                            success = self.send_daily_report_manually()
                            if success:
                                summary["actions_taken"].append(f"补发 {config['name']}")
                            else:
                                summary["alerts"].append(f"{config['name']} 补发失败")
                        else:
                            # 其他任务的重试逻辑
                            summary["alerts"].append(f"{config['name']} 需要手动处理")
                    else:
                        self.log("INFO", "  不在计划执行窗口，跳过恢复")
            
            # 发送告警通知
            if health["needs_action"] and config.get("notify_on_failure"):
                if health["action_type"] == "timeout_recover":
                    self.send_notification(
                        "任务超时告警",
                        f"{config['name']} 执行超时\n{health['message']}"
                    )
        
        # 保存检查记录
        summary_file = LOG_DIR / f"summary_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        self.log("INFO", f"\n检查完成，记录保存至: {summary_file}")
        return summary


def main():
    """主入口"""
    monitor = CronMonitor()
    
    # 解析参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "--now":
            # 立即执行一次健康检查
            monitor.run_health_check()
        elif sys.argv[1] == "--report":
            # 手动补发报告
            monitor.send_daily_report_manually()
        else:
            print("用法: python3 cron_monitor.py [--now|--report]")
    else:
        # 默认：执行健康检查
        monitor.run_health_check()


if __name__ == "__main__":
    main()
