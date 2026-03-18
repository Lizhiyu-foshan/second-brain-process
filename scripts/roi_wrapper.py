#!/usr/bin/env python3
"""
ROI 追踪包装器 - 用于包裹任何检查脚本

用法：
python3 roi_wrapper.py --script <原脚本路径> --task-name <任务名称> [--task-type <任务类型>] [--silent]

示例：
python3 roi_wrapper.py --script cron_health_check.py --task-name "定时任务健康监控"

功能：
1. 执行原脚本
2. 捕获执行结果（是否发现问题）
3. 记录 ROI 数据
4. 返回原脚本的退出码
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

# ROI 追踪器路径
ROI_TRACKER_PATH = Path(__file__).parent / "roi_tracker.py"


def parse_output(output: str) -> tuple:
    """
    从输出中解析是否发现问题和改进数
    
    Returns:
        (found_issues, improvements, details)
    """
    found_issues = False
    improvements = 0
    details = ""
    
    # 检查常见的问题标识
    issue_indicators = [
        "发现", "警告", "错误", "失败", "异常", "❌", "⚠️",
        "issue", "warning", "error", "failed", "critical"
    ]
    
    # 检查改进标识
    improvement_indicators = [
        "已修复", "已自动", "已优化", "已清理", "已恢复",
        "fixed", "repaired", "optimized", "cleaned", "recovered"
    ]
    
    output_lower = output.lower()
    
    # 检测问题
    for indicator in issue_indicators:
        if indicator.lower() in output_lower:
            # 进一步确认是否真的是问题
            if any(x in output for x in ["发现", "警告", "错误", "失败", "❌", "⚠️"]):
                found_issues = True
                break
    
    # 检测改进
    for indicator in improvement_indicators:
        if indicator.lower() in output_lower:
            improvements += 1
    
    # 提取关键信息作为详情
    if "发现" in output:
        import re
        match = re.search(r'发现 (\d+) 个[警告错误]', output)
        if match:
            details = f"发现{match.group(1)}个问题"
        else:
            details = "发现问题"
    
    return found_issues, improvements, details


def main():
    parser = argparse.ArgumentParser(description='ROI 追踪包装器')
    parser.add_argument('--script', required=True, help='原脚本路径')
    parser.add_argument('--task-name', required=True, help='任务名称')
    parser.add_argument('--task-type', default='openclaw_cron', help='任务类型')
    parser.add_argument('--silent', action='store_true', help='静默模式')
    parser.add_argument('--no-roi', action='store_true', help='禁用 ROI 追踪')
    parser.add_argument('args', nargs='*', help='传递给原脚本的参数')
    
    args = parser.parse_args()
    
    start_time = time.time()
    
    # 构建原脚本命令
    script_path = Path(args.script)
    if not script_path.is_absolute():
        # 如果是相对路径，尝试在当前目录或常见位置查找
        possible_paths = [
            script_path,
            Path(__file__).parent / args.script,
            Path(script_path.name),
        ]
        for p in possible_paths:
            if p.exists():
                script_path = p
                break
    
    cmd = [sys.executable, str(script_path)] + args.args
    
    # 执行原脚本
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 分钟超时
        )
        
        output = result.stdout + result.stderr
        exit_code = result.returncode
        
        # 输出原脚本的结果
        if not args.silent:
            print(output)
        elif result.returncode != 0 and output:
            # 静默模式下只输出错误
            print(output, file=sys.stderr)
        
        # 记录 ROI 数据
        if not args.no_roi:
            duration_ms = int((time.time() - start_time) * 1000)
            found_issues, improvements, details = parse_output(output)
            
            # 如果退出码为 1，也认为发现了问题
            if exit_code == 1 and not found_issues:
                found_issues = True
                if not details:
                    details = "检查失败"
            
            # 调用 ROI 追踪器
            sys.path.insert(0, str(Path(__file__).parent))
            from roi_tracker import record_task_execution
            
            record_task_execution(
                task_name=args.task_name,
                found_issues=found_issues,
                improvements=improvements,
                duration_ms=duration_ms,
                details=details if details else ("执行成功" if exit_code == 0 else "执行失败"),
                task_type=args.task_type
            )
        
        sys.exit(exit_code)
        
    except subprocess.TimeoutExpired:
        print(f"[ERROR] 脚本执行超时 (5 分钟)", file=sys.stderr)
        if not args.no_roi:
            sys.path.insert(0, str(Path(__file__).parent))
            from roi_tracker import record_task_execution
            record_task_execution(
                task_name=args.task_name,
                found_issues=True,
                improvements=0,
                duration_ms=300000,
                details="执行超时",
                task_type=args.task_type
            )
        sys.exit(1)
        
    except FileNotFoundError:
        print(f"[ERROR] 脚本不存在：{script_path}", file=sys.stderr)
        sys.exit(1)
        
    except Exception as e:
        print(f"[ERROR] 执行失败：{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
