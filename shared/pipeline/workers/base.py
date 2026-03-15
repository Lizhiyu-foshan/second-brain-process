"""
角色工作器基础类
"""
import logging
import time
import traceback
from abc import ABC, abstractmethod
from typing import Dict, Any

from layer1.api import ResourceSchedulerAPI

logger = logging.getLogger(__name__)


class BaseRoleWorker(ABC):
    """
    角色工作器基类
    
    职责:
    - 轮询获取任务
    - 申请/释放锁
    - 执行任务
    - 上报结果
    """
    
    def __init__(self, role_id: str, scheduler_api: ResourceSchedulerAPI):
        self.role_id = role_id
        self.scheduler_api = scheduler_api
        self.running = False
        self.current_task = None
    
    def start(self):
        """启动工作器"""
        self.running = True
        logger.info(f"Worker {self.role_id} started")
        
        while self.running:
            try:
                self._poll_and_execute()
            except Exception as e:
                logger.error(f"Worker {self.role_id} error: {e}")
                time.sleep(60)  # 出错后等待1分钟
    
    def stop(self):
        """停止工作器"""
        self.running = False
        logger.info(f"Worker {self.role_id} stopped")
    
    def _poll_and_execute(self):
        """轮询并执行任务"""
        # 1. 获取任务
        task_data = self.scheduler_api.poll_task(self.role_id)
        
        if not task_data:
            # 无任务，等待
            time.sleep(60)  # 1分钟后再次轮询
            return
        
        task_id = task_data["task_id"]
        self.current_task = task_id
        logger.info(f"Worker {self.role_id} got task {task_id}")
        
        # 2. 获取锁
        lock_result = self.scheduler_api.acquire_lock(self.role_id, task_id)
        
        if not lock_result["acquired"]:
            logger.warning(f"Failed to acquire lock for task {task_id}")
            time.sleep(10)
            return
        
        try:
            # 3. 执行任务
            logger.info(f"Executing task {task_id}")
            result = self.execute_task(task_data)
            
            # 4. 完成任务
            success = result.get("success", False)
            self.scheduler_api.complete_task(task_id, success, result)
            
            logger.info(f"Task {task_id} completed: {success}")
            
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            self.scheduler_api.complete_task(
                task_id,
                False,
                {"error": str(e), "traceback": traceback.format_exc()}
            )
        finally:
            # 5. 释放锁
            self.scheduler_api.release_lock(self.role_id)
            self.current_task = None
    
    @abstractmethod
    def execute_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行任务，子类必须实现
        
        Returns:
            {
                "success": bool,
                "output": str,
                "artifacts": [...],
                "metrics": {...}
            }
        """
        pass
