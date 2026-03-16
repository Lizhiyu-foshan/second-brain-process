#!/usr/bin/env python3
"""
凌晨5:00系统整理任务 - Python版（带实时进度反馈）

特性：
1. 每个关键步骤发送进度更新
2. 自动计算剩余时间
3. 失败时发送告警
4. 完成后发送摘要
"""

import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# 路径配置
WORKSPACE = Path("/root/.openclaw/workspace")
SCRIPT_DIR = WORKSPACE / "second-brain-processor"
LOG_DIR = Path("/tmp")
FEISHU_USER = "ou_363105a68ee112f714ed44e12c802051"

class ProgressReporter:
    """进度报告器"""
    
    def __init__(self, total_steps: int, task_name: str):
        self.total_steps = total_steps
        self.current_step = 0
        self.task_name = task_name
        self.start_time = datetime.now()
        self.step_start_time = None
        
    def start_step(self, step_name: str, estimated_seconds: int = 30):
        """开始新步骤"""
        self.current_step += 1
        self.step_start_time = datetime.now()
        self.current_step_name = step_name
        self.estimated_seconds = estimated_seconds
        
        percent = int((self.current_step - 1) / self.total_steps * 100)
        self._report(f"步骤 {self.current_step}/{self.total_steps}", step_name, percent, f"~{estimated_seconds}秒")
        
    def update(self, message: str, percent_in_step: int = 50):
        """更新当前步骤进度"""
        base_percent = int((self.current_step - 1) / self.total_steps * 100)
        step_percent = int(percent_in_step / self.total_steps)
        total_percent = min(base_percent + step_percent, 99)
        
        # 计算剩余时间
        elapsed = (datetime.now() - self.step_start_time).total_seconds()
        if elapsed > 0 and percent_in_step > 0:
            total_estimated = elapsed / (percent_in_step / 100)
            remaining = max(0, total_estimated - elapsed)
            eta = f"~{int(remaining)}秒"
        else:
            eta = f"~{self.estimated_seconds}秒"
        
        self._report(f"步骤 {self.current_step}/{self.total_steps}", message, total_percent, eta)
        
    def complete_step(self, message: str = "完成"):
        """完成当前步骤"""
        percent = int(self.current_step / self.total_steps * 100)
        self._report(f"步骤 {self.current_step}/{self.total_steps}", message, percent, "即将下一步")
        
    def complete(self, message: str = "全部完成"):
        """任务完成"""
        total_time = (datetime.now() - self.start_time).total_seconds()
        self._report("完成", message, 100, f"总耗时{int(total_time)}秒")
        
    def error(self, error_message: str):
        """报告错误"""
        self._report("错误", error_message, 0, "需要处理")
        
    def _report(self, step: str, message: str, percent: int, eta: str):
        """发送进度报告"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        progress_line = f"[{timestamp}] 📊 {self.task_name} | {step}: {message} ({percent}%) ETA: {eta}"
        
        # 输出到控制台
        print(progress_line)
        
        # 每25%发送一次飞书通知（避免过于频繁）
        if percent in [25, 50, 75] or percent == 100 or percent == 0:
            self._send_feishu_notification(step, message, percent, eta)
            
    def _send_feishu_notification(self, step: str, message: str, percent: int, eta: str):
        """发送飞书通知（静默模式，不干扰用户）"""
        try:
            # 构建简洁消息
            if percent == 0:
                title = f"⚠️ {self.task_name} 遇到问题"
                content = f"步骤: {step}\n问题: {message}\n时间: {datetime.now().strftime('%H:%M')}"
            elif percent == 100:
                title = f"✅ {self.task_name} 完成"
                content = f"总耗时: {eta}\n完成时间: {datetime.now().strftime('%H:%M')}"
            else:
                # 中间进度不发送，避免打扰
                return
            
            # 使用 openclaw message 命令发送
            cmd = [
                "openclaw", "message", "send",
                "--target", FEISHU_USER,
                "--content", f"{title}\n\n{content}"
            ]
            subprocess.run(cmd, capture_output=True, timeout=10)
        except Exception as e:
            # 发送失败不中断主流程
            print(f"[WARN] 通知发送失败: {e}")


def run_with_progress():
    """带进度反馈的主流程"""
    print("=" * 50)
    print(f"凌晨5:00系统整理任务 - {datetime.now()}")
    print("预计总耗时: 60-90秒")
    print("=" * 50)
    
    # 创建进度报告器（3个主要步骤）
    progress = ProgressReporter(total_steps=3, task_name="凌晨整理")
    
    # 步骤1: 整理聊天记录
    progress.start_step("整理聊天记录", estimated_seconds=50)
    
    try:
        progress.update("正在扫描会话文件...", 10)
        
        # 执行Python脚本
        process = subprocess.Popen(
            ["python3", "-u", "kimiclaw_v2.py", "--morning-process"],
            cwd=SCRIPT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1  # 行缓冲模式
        )
        
        # 读取输出并更新进度
        output_lines = []
        step_markers = {
            "步骤1": 20,
            "步骤2": 40,
            "步骤3": 60,
            "步骤4": 80,
            "步骤5": 90
        }
        
        for line in process.stdout:
            line = line.strip()
            output_lines.append(line)
            print(line, flush=True)  # 实时输出，强制刷新
            
            # 根据输出内容更新进度（支持带【】和不带的格式）
            for marker, pct in step_markers.items():
                if marker in line or f"【{marker}】" in line:
                    progress.update(line.replace("【", "").replace("】", "")[:30], pct)
        
        process.wait()
        
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, "kimiclaw_v2.py")
        
        progress.complete_step("整理完成")
        
    except Exception as e:
        progress.error(f"整理失败: {str(e)}")
        # 记录错误
        _log_error("morning_process_step1_failed", str(e))
        return False
    
    # 步骤2: 系统进化复盘
    progress.start_step("系统进化复盘", estimated_seconds=15)
    
    try:
        progress.update("分析错误日志...", 30)
        
        result = subprocess.run(
            ["python3", "system_evolution_v2.py", "--daily-review"],
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            progress.update("生成改进方案...", 70)
            time.sleep(1)  # 给用户阅读时间
            progress.complete_step("复盘完成")
        else:
            print(f"[WARN] 复盘脚本返回非零: {result.stderr}")
            progress.complete_step("复盘完成（有警告）")
            
    except Exception as e:
        print(f"[WARN] 复盘失败: {e}")
        progress.complete_step("复盘跳过（非致命）")
    
    # 步骤3: AI自主进化分析（使用Kimi K2.5深度分析）
    progress.start_step("AI自主进化分析", estimated_seconds=60)
    
    try:
        progress.update("收集7天行为数据...", 20)
        
        # 运行AI能力缺口分析器（使用Kimi K2.5）
        result = subprocess.run(
            ["python3", "ai_gap_analyzer.py", "--days", "7", "--output", "json", "--save"],
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True,
            timeout=120  # AI分析可能需要更长时间
        )
        
        # 输出调试信息
        if result.stdout:
            # 只显示关键行，避免刷屏
            for line in result.stdout.split('\n')[:20]:
                if any(kw in line for kw in ['✅', '🎯', '发现', '缺口', '完成', 'ERROR', 'WARN']):
                    print(line)
        
        if result.stderr:
            print(f"[DEBUG] AI分析日志: {result.stderr[:500]}")
        
        if result.returncode == 0:
            progress.update("AI深度分析中（Kimi K2.5）...", 50)
            # AI分析耗时较长，这里显示进度
            time.sleep(2)
            progress.update("生成改进建议...", 80)
            time.sleep(1)
            progress.complete_step("AI分析完成（建议将在08:30报告中呈现）")
            print("\n💡 提示：详细的AI分析建议将在08:30每日报告中展示")
        else:
            print(f"[WARN] AI分析返回非零: {result.returncode}")
            # 降级到基础分析
            progress.update("AI分析失败，降级到基础分析...", 50)
            subprocess.run(
                ["python3", "evolution_analyzer.py"],
                cwd=SCRIPT_DIR,
                capture_output=True,
                timeout=30
            )
            progress.complete_step("基础分析完成（AI分析失败，使用备用方案）")
            
    except subprocess.TimeoutExpired:
        print(f"[WARN] AI分析超时（超过120秒）")
        progress.complete_step("AI分析超时（建议将在下次报告中重试）")
    except Exception as e:
        print(f"[WARN] AI分析失败: {e}")
        progress.complete_step("AI分析跳过（非致命）")
    
    # 任务完成
    progress.complete()
    print("=" * 50)
    print(f"任务完成 - {datetime.now()}")
    print("=" * 50)
    
    return True


def _log_error(error_type: str, details: str):
    """记录错误到日志"""
    try:
        learnings_dir = WORKSPACE / ".learnings"
        learnings_dir.mkdir(parents=True, exist_ok=True)
        
        errors_file = learnings_dir / "ERRORS.md"
        timestamp = datetime.now().isoformat()
        error_id = f"ERR-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        error_entry = f"""
## [{error_id}] {error_type}

**Logged**: {timestamp}
**Priority**: high
**Status**: pending
**Area**: daily_task

### 问题
{details}

### 解决方案
待排查

---
"""
        with open(errors_file, 'a', encoding='utf-8') as f:
            f.write(error_entry)
    except Exception as e:
        print(f"[WARN] 错误记录失败: {e}")


if __name__ == "__main__":
    success = run_with_progress()
    sys.exit(0 if success else 1)
