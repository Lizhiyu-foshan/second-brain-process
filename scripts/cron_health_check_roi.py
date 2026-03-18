#!/usr/bin/env python3
"""
Cron 健康检查 - ROI 追踪版本

在原 cron_health_check.py 基础上增加 ROI 追踪，
记录每次执行的价值（是否发现问题、触发改进等）。

用法：
python3 cron_health_check_roi.py --silent

与原脚本的区别：
1. 执行后自动记录 ROI 数据
2. 支持 --no-roi 参数禁用追踪
3. 保留原脚本所有功能
"""

import sys
import os
import time
from pathlib import Path

# 添加原脚本路径
SCRIPT_DIR = Path(__file__).parent.parent / "skills" / "cron-health-dashboard" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from cron_health_check import main as health_check_main
from roi_tracker import record_task_execution

def main():
    start_time = time.time()
    
    # 解析参数
    silent_mode = "--silent" in sys.argv
    no_roi = "--no-roi" in sys.argv
    
    # 执行原检查逻辑
    found_issues = False
    improvements = 0
    details = ""
    
    try:
        # 捕获原脚本的输出和返回值
        import io
        from contextlib import redirect_stdout, redirect_stderr
        
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        # 临时替换 sys.argv
        original_argv = sys.argv.copy()
        sys.argv = [sys.argv[0]] + [arg for arg in sys.argv[1:] if arg not in ["--no-roi"]]
        
        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                result = health_check_main()
                # 检查返回值（如果原脚本返回）
                found_issues = (result == 1) or (result is None and "issues_found" in stdout_capture.getvalue().lower())
        except SystemExit as e:
            # 原脚本调用 sys.exit()
            found_issues = (e.code == 1)
        except Exception as e:
            details = f"执行异常：{str(e)}"
            found_issues = True  # 异常也算问题
        finally:
            sys.argv = original_argv
        
        # 分析输出内容
        output = stdout_capture.getvalue()
        if not silent_mode:
            print(output)
        
        # 从输出中解析问题和改进
        if "发现" in output and "警告" in output:
            # 尝试解析具体数字
            import re
            warning_match = re.search(r'发现 (\d+) 个警告', output)
            if warning_match:
                warnings = int(warning_match.group(1))
                if warnings > 0:
                    found_issues = True
                    details = f"发现{warnings}个警告"
            
            # 检查是否有"严重"问题
            if "严重" in output:
                critical_match = re.search(r'严重：(\d+)', output)
                if critical_match and int(critical_match.group(1)) > 0:
                    found_issues = True
                    details += "; 发现严重问题"
        
        # 记录 ROI 数据
        if not no_roi:
            duration_ms = int((time.time() - start_time) * 1000)
            record_task_execution(
                task_name="定时任务健康监控",
                found_issues=found_issues,
                improvements=improvements,
                duration_ms=duration_ms,
                details=details if details else ("发现问题" if found_issues else "无问题"),
                task_type="openclaw_cron"
            )
        
        # 返回原脚本的退出码
        sys.exit(1 if found_issues else 0)
        
    except Exception as e:
        print(f"ROI 追踪失败：{e}", file=sys.stderr)
        # 即使追踪失败，也要执行原脚本
        sys.argv = [sys.argv[0]] + [arg for arg in sys.argv[1:] if arg not in ["--no-roi"]]
        sys.exit(health_check_main())


if __name__ == "__main__":
    main()
