#!/usr/bin/env python3
"""
配置健康检查脚本

验证所有关键配置、路径、环境变量是否正确
用于预防定时任务因配置错误而失败
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

class ConfigHealthChecker:
    def __init__(self):
        self.workspace = Path('/root/.openclaw/workspace')
        self.issues = []
        self.warnings = []
        self.passed = []
        
    def check_path_exists(self, path: Path, description: str, critical: bool = True) -> bool:
        """检查路径是否存在"""
        if path.exists():
            self.passed.append(f"{description}: {path}")
            return True
        else:
            msg = f"{description} 路径不存在：{path}"
            if critical:
                self.issues.append(msg)
            else:
                self.warnings.append(msg)
            return False
    
    def check_python_import(self, module_name: str, description: str) -> bool:
        """检查 Python 模块是否可导入"""
        try:
            __import__(module_name)
            self.passed.append(f"{description}: {module_name}")
            return True
        except ImportError as e:
            msg = f"{description} 导入失败：{module_name} - {e}"
            self.issues.append(msg)
            return False
    
    def check_file_importable(self, filepath: Path, function_name: str = None) -> bool:
        """检查 Python 文件是否可导入"""
        if not filepath.exists():
            self.issues.append(f"文件不存在：{filepath}")
            return False
        
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("temp_module", filepath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if function_name:
                if hasattr(module, function_name):
                    self.passed.append(f"{filepath.name}.{function_name}() 可导入")
                    return True
                else:
                    msg = f"函数不存在：{filepath.name}.{function_name}()"
                    self.warnings.append(msg)
                    return False
            else:
                self.passed.append(f"{filepath.name} 可导入")
                return True
        except Exception as e:
            msg = f"导入失败：{filepath.name} - {e}"
            self.issues.append(msg)
            return False
    
    def check_env_variable(self, var_name: str, description: str, required: bool = True) -> bool:
        """检查环境变量是否设置"""
        value = os.getenv(var_name)
        if value:
            self.passed.append(f"{description}: {var_name}={value[:20]}...")
            return True
        else:
            msg = f"{description} 未设置：{var_name}"
            if required:
                self.issues.append(msg)
            else:
                self.warnings.append(msg)
            return False
    
    def check_cron_status(self) -> bool:
        """检查 OpenClaw Cron 状态"""
        import subprocess
        try:
            result = subprocess.run(
                ['openclaw', 'cron', 'status'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                self.passed.append("OpenClaw Cron 服务正常")
                return True
            else:
                msg = f"OpenClaw Cron 状态异常：{result.stderr}"
                self.issues.append(msg)
                return False
        except Exception as e:
            msg = f"检查 Cron 状态失败：{e}"
            self.issues.append(msg)
            return False
    
    def check_cron_jobs(self) -> Tuple[bool, List[Dict]]:
        """检查定时任务配置"""
        import subprocess
        try:
            result = subprocess.run(
                ['openclaw', 'cron', 'list'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                # 简单检查是否有任务
                jobs = [line for line in result.stdout.split('\n') if line.strip()]
                if len(jobs) > 0:
                    self.passed.append(f"定时任务数量：{len(jobs)}")
                    return True, jobs
                else:
                    msg = "未找到任何定时任务"
                    self.warnings.append(msg)
                    return False, []
            else:
                msg = f"获取定时任务失败：{result.stderr}"
                self.issues.append(msg)
                return False, []
        except Exception as e:
            msg = f"检查定时任务失败：{e}"
            self.issues.append(msg)
            return False, []
    
    def check_cron_validation(self) -> bool:
        """验证定时任务执行状态（调用 cron_manager.py）"""
        import subprocess
        try:
            cron_manager = self.workspace / 'scripts' / 'cron_manager.py'
            if not cron_manager.exists():
                msg = "cron_manager.py 不存在，跳过验证"
                self.warnings.append(msg)
                return False
            
            result = subprocess.run(
                ['python3', str(cron_manager), 'verify', '--all'],
                capture_output=True,
                text=True,
                timeout=60,  # 增加到 60 秒
                cwd=self.workspace
            )
            
            if result.returncode == 0:
                self.passed.append("定时任务验证通过（所有任务配置正常）")
                return True
            else:
                # 解析验证结果
                output = result.stdout + result.stderr
                if "WARNING" in output:
                    msg = f"定时任务验证警告：部分任务可能存在问 题"
                    self.warnings.append(msg)
                else:
                    msg = f"定时任务验证失败：{output[:200]}"
                    self.issues.append(msg)
                return False
        except subprocess.TimeoutExpired:
            msg = "定时任务验证超时（>60s）"
            self.warnings.append(msg)
            return False
        except Exception as e:
            msg = f"执行定时任务验证失败：{e}"
            self.warnings.append(msg)
            return False
    
    def check_critical_paths(self):
        """检查关键路径"""
        critical_paths = [
            (self.workspace / 'second-brain-processor', '核心处理器目录'),
            (self.workspace / 'memory', '记忆目录'),
            (self.workspace / '.learnings', '学习记录目录'),
            (self.workspace / 'daily_review', '每日复盘目录'),
            (self.workspace / 'scripts', '脚本目录'),
            (self.workspace / 'docs', '文档目录'),
        ]
        
        for path, desc in critical_paths:
            self.check_path_exists(path, desc, critical=(desc != '每日复盘目录'))
    
    def check_critical_files(self):
        """检查关键文件"""
        critical_files = [
            (self.workspace / 'second-brain-processor' / 'run_morning_process_progress.py', '晨间整理脚本'),
            (self.workspace / 'second-brain-processor' / 'run_daily_report_progress.py', '每日复盘脚本'),
            (self.workspace / 'second-brain-processor' / 'feishu_receive_dedup.py', '接收去重模块'),
            (self.workspace / 'second-brain-processor' / 'feishu_guardian.py', '发送防重模块'),
            (self.workspace / 'scripts' / 'task_execution_monitor.py', '任务监控脚本'),
        ]
        
        for filepath, desc in critical_files:
            self.check_path_exists(filepath, desc, critical=True)
    
    def check_python_modules(self):
        """检查关键 Python 模块"""
        # requests 库
        self.check_python_import('requests', 'HTTP 请求库')
        
        # 飞书 SDK 通过 extension 安装，检查 extension 目录
        feishu_ext = Path('/root/.openclaw/extensions/feishu')
        if feishu_ext.exists():
            self.passed.append(f"飞书 Extension: {feishu_ext}")
        else:
            self.issues.append(f"飞书 Extension 不存在：{feishu_ext}")
    
    def check_processor_scripts(self):
        """检查处理器脚本可执行性"""
        scripts = [
            self.workspace / 'second-brain-processor' / 'run_morning_process_progress.py',
            self.workspace / 'second-brain-processor' / 'kimiclaw_v2.py',
            self.workspace / 'second-brain-processor' / 'run_daily_report_progress.py',
            self.workspace / 'second-brain-processor' / 'standalone_daily_report.py',
        ]
        
        for filepath in scripts:
            if filepath.exists():
                self.passed.append(f"脚本存在：{filepath.name}")
            else:
                self.issues.append(f"脚本不存在：{filepath}")
    
    def run_all_checks(self) -> bool:
        """运行所有检查"""
        print(f"{Colors.BLUE}{'='*70}{Colors.RESET}")
        print(f"{Colors.BLUE}配置健康检查 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}")
        print(f"{Colors.BLUE}{'='*70}{Colors.RESET}\n")
        
        # 执行检查
        print("1. 检查关键路径...")
        self.check_critical_paths()
        
        print("2. 检查关键文件...")
        self.check_critical_files()
        
        print("3. 检查 Python 模块...")
        self.check_python_modules()
        
        print("4. 检查脚本可导入性...")
        self.check_processor_scripts()
        
        print("5. 检查 OpenClaw Cron 状态...")
        self.check_cron_status()
        
        print("6. 检查定时任务配置...")
        self.check_cron_jobs()
        
        print("7. 验证定时任务执行状态（调用 cron_manager.py）...")
        self.check_cron_validation()
        
        # 输出结果
        print(f"\n{Colors.GREEN}{'='*70}{Colors.RESET}")
        print(f"{Colors.GREEN}检查结果{Colors.RESET}")
        print(f"{Colors.GREEN}{'='*70}{Colors.RESET}\n")
        
        if self.passed:
            print(f"{Colors.GREEN}✅ 通过项 ({len(self.passed)}){Colors.RESET}:")
            for item in self.passed[:20]:  # 限制显示数量
                print(f"   {Colors.GREEN}✓{Colors.RESET} {item}")
            if len(self.passed) > 20:
                print(f"   ... 还有 {len(self.passed) - 20} 项")
        
        if self.warnings:
            print(f"\n{Colors.YELLOW}⚠️ 警告项 ({len(self.warnings)}){Colors.RESET}:")
            for item in self.warnings:
                print(f"   {Colors.YELLOW}⚠{Colors.RESET} {item}")
        
        if self.issues:
            print(f"\n{Colors.RED}❌ 问题项 ({len(self.issues)}){Colors.RESET}:")
            for i, item in enumerate(self.issues, 1):
                print(f"   {Colors.RED}{i}.{Colors.RESET} {item}")
        
        # 总结
        print(f"\n{Colors.BLUE}{'='*70}{Colors.RESET}")
        if not self.issues:
            print(f"{Colors.GREEN}✅ 配置健康检查通过！系统状态良好{Colors.RESET}")
            return True
        else:
            print(f"{Colors.RED}❌ 发现 {len(self.issues)} 个问题需要修复{Colors.RESET}")
            print(f"\n{Colors.YELLOW}💡 建议操作:{Colors.RESET}")
            print("1. 根据上述问题列表逐一修复")
            print("2. 修复后重新运行此脚本验证")
            print("3. 如果是路径问题，检查文件是否被移动或删除")
            print("4. 如果是导入问题，检查依赖是否安装")
            return False

def main():
    checker = ConfigHealthChecker()
    success = checker.run_all_checks()
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
