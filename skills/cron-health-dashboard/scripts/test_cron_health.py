#!/usr/bin/env python3
"""
Cron Health Dashboard 测试套件

运行方式：
    python3 -m pytest test_cron_health.py -v
    或
    python3 test_cron_health.py

作者：Kimi Claw
创建时间：2026-03-15
"""

import json
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

# 添加脚本路径
sys.path.insert(0, str(Path(__file__).parent))

from cron_health_check import CronHealthChecker


class TestCronHealthChecker(unittest.TestCase):
    """CronHealthChecker 单元测试"""
    
    def setUp(self):
        """测试前准备"""
        self.checker = CronHealthChecker()
    
    def test_init(self):
        """测试初始化"""
        self.assertEqual(self.checker.results["overall_status"], "unknown")
        self.assertEqual(self.checker.results["openclaw"]["total"], 0)
        self.assertEqual(self.checker.results["linux"]["total"], 0)
        self.assertEqual(len(self.checker.results["issues"]), 0)
    
    def test_parse_openclaw_cron_list(self):
        """测试解析 openclaw cron list 输出"""
        sample_output = """ID                                   Name                     Schedule                         Next       Last       Status    Target    Agent     
bc1e430c-b55b-4188-8d2c-03804f121ac2 自我进化流水线-架构师              cron 0 4,20 * * * @ Asia/Shanghai in 3h      13h ago    error     isolated  main
efccc41b-7887-4af7-b619-54f91679cdaa 凌晨5:00聊天记录整理             cron 0 5 * * * @ Asia/Shanghai   in 12h     12h ago    ok        main      main
ab5cc2b3-4325-420e-85f8-addf1dbf636f GAP02-cron-health-dash   at 2026-03-15 12:00Z             in 3h      -          idle      isolated  main"""
        
        tasks = self.checker.parse_openclaw_cron_list(sample_output)
        
        self.assertEqual(len(tasks), 3)
        
        # 检查第一个任务（error 状态）
        self.assertEqual(tasks[0]["id"], "bc1e430c-b55b-4188-8d2c-03804f121ac2")
        self.assertEqual(tasks[0]["status"], "error")
        self.assertEqual(tasks[0]["last"], "13h ago")  # 正确解析 "13h ago"
        self.assertEqual(tasks[0]["target"], "isolated")
        
        # 检查第二个任务（ok 状态）
        self.assertEqual(tasks[1]["status"], "ok")
        self.assertEqual(tasks[1]["last"], "12h ago")  # 正确解析
        
        # 检查第三个任务（idle 状态）
        self.assertEqual(tasks[2]["status"], "idle")
    
    def test_detect_zombie_tasks_no_issues(self):
        """测试僵尸任务检测 - 无问题"""
        # 设置一个健康的任务列表
        self.checker.results["openclaw"]["tasks"] = [
            {
                "id": "test1",
                "name": "正常任务",
                "status": "ok",
                "last": "1h ago"
            }
        ]
        
        zombies = self.checker.detect_zombie_tasks()
        self.assertEqual(len(zombies), 0)
    
    @patch('cron_health_check.subprocess.run')
    def test_check_openclaw_cron_success(self, mock_run):
        """测试检查 OpenClaw cron - 成功场景"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="""ID                                   Name                     Schedule                         Next       Last       Status    Target    Agent
efccc41b-7887-4af7-b619-54f91679cdaa 凌晨5:00聊天记录整理             cron 0 5 * * * @ Asia/Shanghai   in 12h     12h ago    ok        main      main""",
            stderr=""
        )
        
        healthy, message, issues = self.checker.check_openclaw_cron()
        
        self.assertTrue(healthy)
        self.assertIn("正常", message)
        self.assertEqual(len(issues), 0)
    
    @patch('cron_health_check.subprocess.run')
    def test_check_openclaw_cron_with_errors(self, mock_run):
        """测试检查 OpenClaw cron - 有错误任务"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="""ID                                   Name                     Schedule                         Next       Last       Status    Target    Agent
bc1e430c-b55b-4188-8d2c-03804f121ac2 自我进化流水线-架构师              cron 0 4,20 * * * @ Asia/Shanghai in 3h      13h ago    error     isolated  main""",
            stderr=""
        )
        
        healthy, message, issues = self.checker.check_openclaw_cron()
        
        self.assertFalse(healthy)
        self.assertIn("严重", message)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["type"], "error_status")
    
    @patch('cron_health_check.subprocess.run')
    def test_check_openclaw_cron_timeout(self, mock_run):
        """测试检查 OpenClaw cron - 超时"""
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired("openclaw cron list", 30)
        
        healthy, message, issues = self.checker.check_openclaw_cron()
        
        self.assertFalse(healthy)
        self.assertIn("超时", message)
    
    @patch('cron_health_check.subprocess.run')
    def test_check_linux_cron_success(self, mock_run):
        """测试检查 Linux cron - 成功"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="# 每天凌晨5点执行\n0 5 * * * /usr/bin/python3 /path/to/script.py\n# 每小时检查\n0 * * * * /usr/bin/echo 'check'",
            stderr=""
        )
        
        healthy, message = self.checker.check_linux_cron()
        
        self.assertTrue(healthy)
        self.assertIn("2", message)
    
    def test_generate_recommendations(self):
        """测试生成修复建议"""
        self.checker.results["issues"] = [
            {
                "type": "error_status",
                "task_id": "test123",
                "task_name": "测试任务",
                "severity": "critical"
            }
        ]
        
        self.checker._generate_recommendations()
        
        self.assertEqual(len(self.checker.results["recommendations"]), 1)
        self.assertEqual(self.checker.results["recommendations"][0]["priority"], "high")
        self.assertIn("test123", self.checker.results["recommendations"][0]["command"])


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def test_full_check_with_mock(self):
        """测试完整检查流程（使用 mock）"""
        checker = CronHealthChecker()
        
        with patch('cron_health_check.subprocess.run') as mock_run:
            # 模拟 OpenClaw cron list 和 Linux crontab
            def mock_run_side_effect(*args, **kwargs):
                if args[0] == ["openclaw", "cron", "list"]:
                    return MagicMock(
                        returncode=0,
                        stdout="""ID                                   Name                     Schedule                         Next       Last       Status    Target    Agent
efccc41b-7887-4af7-b619-54f91679cdaa 凌晨5:00聊天记录整理             cron 0 5 * * * @ Asia/Shanghai   in 12h     12h ago    ok        main      main""",
                        stderr=""
                    )
                elif args[0] == ["crontab", "-l"]:
                    return MagicMock(
                        returncode=0,
                        stdout="0 5 * * * /usr/bin/python3 /path/to/script.py",
                        stderr=""
                    )
                elif args[0] == ["df", "-h"]:
                    return MagicMock(
                        returncode=0,
                        stdout="Filesystem      Size  Used Avail Use% Mounted on\n/dev/sda1        50G   20G   30G  40% /",
                        stderr=""
                    )
                return MagicMock(returncode=0, stdout="", stderr="")
            
            mock_run.side_effect = mock_run_side_effect
            
            results = checker.run_full_check(verbose=False)
            
            self.assertIn("overall_status", results)
            self.assertIn("openclaw", results)
            self.assertIn("linux", results)


def run_tests():
    """运行测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestCronHealthChecker))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回结果
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
