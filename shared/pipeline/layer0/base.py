"""
Layer 0: 角色工作器 (Role Workers)
基础工作器类和通用接口
"""
import logging
import time
import threading
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class WorkerState(Enum):
    """工作器状态"""
    IDLE = "idle"           # 空闲
    POLLING = "polling"     # 轮询中
    ACQUIRING = "acquiring" # 获取锁中
    EXECUTING = "executing" # 执行中
    RELEASING = "releasing" # 释放锁中
    ERROR = "error"         # 错误状态
    STOPPED = "stopped"     # 已停止


class TaskResult:
    """任务执行结果"""
    def __init__(self, 
                 success: bool, 
                 output: Optional[Any] = None,
                 error_message: Optional[str] = None,
                 artifacts: Optional[Dict] = None):
        self.success = success
        self.output = output
        self.error_message = error_message
        self.artifacts = artifacts or {}
        self.completed_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "output": self.output,
            "error_message": self.error_message,
            "artifacts": self.artifacts,
            "completed_at": self.completed_at
        }


class BaseRoleWorker(ABC):
    """
    角色工作器基类
    
    职责:
    1. 轮询获取任务
    2. 获取/释放锁
    3. 执行任务
    4. 上报结果
    
    生命周期:
    IDLE → POLLING → ACQUIRING → EXECUTING → RELEASING → IDLE
    """
    
    def __init__(self,
                 role_id: str,
                 role_name: str,
                 capabilities: List[str],
                 layer1_api,
                 poll_interval: float = 5.0,
                 lock_timeout_ms: int = 30000):
        """
        初始化工作器
        
        Args:
            role_id: 角色唯一标识 (固定，如 'architect')
            role_name: 角色显示名称
            capabilities: 能力列表
            layer1_api: Layer 1 API 实例
            poll_interval: 轮询间隔（秒）
            lock_timeout_ms: 锁超时时间（毫秒）
        """
        self.role_id = role_id
        self.role_name = role_name
        self.capabilities = capabilities
        self.layer1 = layer1_api
        self.poll_interval = poll_interval
        self.lock_timeout_ms = lock_timeout_ms
        
        self.state = WorkerState.IDLE
        self.current_task: Optional[Dict] = None
        self.running = False
        self.worker_thread: Optional[threading.Thread] = None
        
        # 统计信息
        self.stats = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_execution_time": 0.0,
            "started_at": None
        }
        
        # 钩子函数
        self.hooks: Dict[str, List[Callable]] = {
            "before_poll": [],
            "after_poll": [],
            "before_acquire": [],
            "after_acquire": [],
            "before_execute": [],
            "after_execute": [],
            "before_release": [],
            "after_release": [],
            "on_error": []
        }
        
        logger.info(f"[{self.role_id}] 工作器初始化完成")
    
    def register_hook(self, event: str, callback: Callable):
        """注册钩子函数"""
        if event in self.hooks:
            self.hooks[event].append(callback)
    
    def _trigger_hooks(self, event: str, *args, **kwargs):
        """触发钩子函数"""
        for callback in self.hooks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.warning(f"[{self.role_id}] 钩子执行失败: {e}")
    
    def start(self):
        """启动工作器"""
        if self.running:
            logger.warning(f"[{self.role_id}] 工作器已在运行")
            return
        
        self.running = True
        self.stats["started_at"] = datetime.now().isoformat()
        
        self.worker_thread = threading.Thread(
            target=self._work_loop,
            name=f"Worker-{self.role_id}",
            daemon=True
        )
        self.worker_thread.start()
        
        logger.info(f"[{self.role_id}] 工作器已启动")
    
    def stop(self, timeout: float = 10.0):
        """停止工作器"""
        if not self.running:
            return
        
        logger.info(f"[{self.role_id}] 正在停止工作器...")
        self.running = False
        
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=timeout)
        
        self.state = WorkerState.STOPPED
        logger.info(f"[{self.role_id}] 工作器已停止")
    
    def _work_loop(self):
        """工作主循环"""
        while self.running:
            try:
                self._execute_cycle()
            except Exception as e:
                logger.error(f"[{self.role_id}] 工作循环异常: {e}")
                self._trigger_hooks("on_error", e)
                self.state = WorkerState.ERROR
                time.sleep(self.poll_interval)
    
    def _execute_cycle(self):
        """执行一个完整的工作周期"""
        # 1. 轮询获取任务（直接使用固定role_id）
        self.state = WorkerState.POLLING
        self._trigger_hooks("before_poll")
        
        task = self.layer1.poll_task(self.role_id)
        self._trigger_hooks("after_poll", task)
        
        if not task:
            time.sleep(self.poll_interval)
            return
        
        self.current_task = task
        task_id = task.get("id", "unknown")
        logger.info(f"[{self.role_id}] 获取任务: {task_id}")
        
        # 2. 获取锁
        self.state = WorkerState.ACQUIRING
        self._trigger_hooks("before_acquire", task_id)
        
        lock_acquired = self.layer1.acquire_lock(
            self.role_id, 
            task_id,
            timeout_ms=self.lock_timeout_ms
        )
        
        self._trigger_hooks("after_acquire", task_id, lock_acquired)
        
        if not lock_acquired:
            logger.warning(f"[{self.role_id}] 获取锁失败: {task_id}")
            self.current_task = None
            time.sleep(self.poll_interval)
            return
        
        logger.info(f"[{self.role_id}] 获取锁成功: {task_id}")
        
        # 3. 执行任务
        result = None
        try:
            self.state = WorkerState.EXECUTING
            self._trigger_hooks("before_execute", task)
            
            start_time = time.time()
            result = self.execute_task(task)
            execution_time = time.time() - start_time
            
            self.stats["tasks_completed"] += 1
            self.stats["total_execution_time"] += execution_time
            
            self._trigger_hooks("after_execute", task, result)
            
            logger.info(f"[{self.role_id}] 任务完成: {task_id} ({execution_time:.2f}s)")
            
        except Exception as e:
            logger.error(f"[{self.role_id}] 任务执行异常: {task_id} - {e}")
            result = TaskResult(
                success=False,
                error_message=str(e)
            )
            self.stats["tasks_failed"] += 1
            self._trigger_hooks("on_error", e)
        
        # 4. 完成任务上报
        self.layer1.complete_task(
            task_id,
            result.success if result else False,
            result.to_dict() if result else {}
        )
        
        # 5. 释放锁
        self.state = WorkerState.RELEASING
        self._trigger_hooks("before_release", task_id)
        
        self.layer1.release_lock(self.role_id)
        
        self._trigger_hooks("after_release", task_id)
        
        self.current_task = None
        self.state = WorkerState.IDLE
        
        logger.info(f"[{self.role_id}] 释放锁完成: {task_id}")
    
    @abstractmethod
    def execute_task(self, task_data: Dict[str, Any]) -> TaskResult:
        """
        执行任务（子类必须实现）
        
        Args:
            task_data: 任务数据
            
        Returns:
            TaskResult: 任务执行结果
        """
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """获取工作器状态"""
        return {
            "role_id": self.role_id,
            "role_name": self.role_name,
            "state": self.state.value,
            "capabilities": self.capabilities,
            "current_task": self.current_task,
            "stats": self.stats,
            "running": self.running
        }


class WorkerPool:
    """
    工作器池
    
    管理多个角色工作器的生命周期
    """
    
    def __init__(self):
        self.workers: Dict[str, BaseRoleWorker] = {}
        self._lock = threading.Lock()
    
    def register(self, worker: BaseRoleWorker) -> bool:
        """注册工作器"""
        with self._lock:
            if worker.role_id in self.workers:
                logger.warning(f"工作器已存在: {worker.role_id}")
                return False
            
            self.workers[worker.role_id] = worker
            logger.info(f"注册工作器: {worker.role_id}")
            return True
    
    def unregister(self, role_id: str) -> bool:
        """注销工作器"""
        with self._lock:
            if role_id not in self.workers:
                return False
            
            worker = self.workers.pop(role_id)
            worker.stop()
            logger.info(f"注销工作器: {role_id}")
            return True
    
    def start_all(self):
        """启动所有工作器"""
        for worker in self.workers.values():
            worker.start()
    
    def stop_all(self, timeout: float = 10.0):
        """停止所有工作器"""
        for worker in self.workers.values():
            worker.stop(timeout)
    
    def get_status(self) -> Dict[str, Any]:
        """获取所有工作器状态"""
        return {
            role_id: worker.get_status()
            for role_id, worker in self.workers.items()
        }
    
    def get_worker(self, role_id: str) -> Optional[BaseRoleWorker]:
        """获取指定工作器"""
        return self.workers.get(role_id)
