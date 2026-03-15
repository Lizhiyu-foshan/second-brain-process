#!/usr/bin/env python3
"""
Layer 0 工作器启动脚本
启动所有角色工作器
"""
import sys
import os
import time
import signal
import logging
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from layer1.api import ResourceSchedulerAPI
from layer0 import ArchitectWorker, DeveloperWorker, TesterWorker, WorkerPool

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WorkerDaemon:
    """工作器守护进程"""
    
    def __init__(self, state_dir: str = None, lock_dir: str = None):
        """初始化守护进程"""
        base_dir = Path(__file__).parent.parent
        
        self.state_dir = state_dir or str(base_dir / "state")
        self.lock_dir = lock_dir or str(base_dir / "locks")
        
        os.makedirs(self.state_dir, exist_ok=True)
        os.makedirs(self.lock_dir, exist_ok=True)
        
        self.layer1 = ResourceSchedulerAPI(self.state_dir, self.lock_dir)
        self.worker_pool = WorkerPool()
        self.running = False
        
        # 信号处理
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理"""
        logger.info(f"收到信号 {signum}，正在停止...")
        self.stop()
    
    def register_workers(self):
        """注册所有工作器"""
        # 架构师
        architect = ArchitectWorker(self.layer1, poll_interval=5.0)
        self.worker_pool.register(architect)
        
        # 开发者
        developer = DeveloperWorker(self.layer1, poll_interval=5.0)
        self.worker_pool.register(developer)
        
        # 测试员
        tester = TesterWorker(self.layer1, poll_interval=5.0)
        self.worker_pool.register(tester)
        
        logger.info("所有工作器已注册")
    
    def start(self):
        """启动所有工作器"""
        logger.info("=" * 80)
        logger.info("Layer 0 工作器守护进程启动")
        logger.info("=" * 80)
        
        self.register_workers()
        self.worker_pool.start_all()
        self.running = True
        
        logger.info("所有工作器已启动")
        logger.info("按 Ctrl+C 停止")
        
        # 主循环
        try:
            while self.running:
                self._report_status()
                time.sleep(30)  # 每30秒报告一次状态
        except KeyboardInterrupt:
            logger.info("收到中断信号")
        finally:
            self.stop()
    
    def stop(self):
        """停止所有工作器"""
        if not self.running:
            return
        
        self.running = False
        logger.info("正在停止所有工作器...")
        self.worker_pool.stop_all(timeout=10.0)
        logger.info("所有工作器已停止")
    
    def _report_status(self):
        """报告状态"""
        status = self.worker_pool.get_status()
        
        logger.info("-" * 40)
        for role_id, worker_status in status.items():
            state = worker_status.get("state", "unknown")
            stats = worker_status.get("stats", {})
            completed = stats.get("tasks_completed", 0)
            failed = stats.get("tasks_failed", 0)
            logger.info(f"[{role_id}] 状态: {state} | 完成: {completed} | 失败: {failed}")
        logger.info("-" * 40)


def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Layer 0 工作器守护进程')
    parser.add_argument('--state-dir', help='状态文件目录')
    parser.add_argument('--lock-dir', help='锁文件目录')
    parser.add_argument('--daemon', '-d', action='store_true', help='后台运行')
    
    args = parser.parse_args()
    
    daemon = WorkerDaemon(
        state_dir=args.state_dir,
        lock_dir=args.lock_dir
    )
    
    daemon.start()


if __name__ == "__main__":
    main()
