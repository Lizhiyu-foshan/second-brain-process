"""
Layer 1 API
整合所有Layer 1组件，提供统一的API接口
"""
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from shared.models import Task, Conflict
from layer1.role_registry import RoleRegistry, get_workspace_dir
from layer1.lock_manager import LockManager
from layer1.task_queue import TaskQueue
from layer1.conflict_detector import ConflictDetector
from layer1.priority_manager import PriorityManager

logger = logging.getLogger(__name__)


class ResourceSchedulerAPI:
    """
    Layer 1 资源调度API
    
    提供给 Layer 2 (Orchestrator) 的接口:
    - get_roles_status(): 查询角色状态
    - submit_task(): 提交任务
    - query_schedule(): 查询可行时间窗口
    
    提供给 Role Workers 的接口:
    - acquire_lock(): 申请锁
    - release_lock(): 释放锁
    - poll_task(): 轮询获取任务
    - complete_task(): 完成任务
    
    维护接口:
    - cleanup(): 清理过期锁
    - detect_deadlock(): 检测死锁
    """
    
    def __init__(self, 
                 state_dir: str = None,
                 lock_dir: str = None):
        """
        初始化资源调度API
        
        Args:
            state_dir: 状态文件目录，默认使用环境变量或相对路径
            lock_dir: 锁文件目录，默认使用环境变量或相对路径
        """
        if state_dir is None:
            workspace = get_workspace_dir()
            state_dir = workspace / "shared" / "pipeline" / "state"
            lock_dir = workspace / "shared" / "pipeline" / "locks"
        
        self.registry = RoleRegistry(f"{state_dir}/layer1_state.json")
        self.lock_manager = LockManager(lock_dir)
        self.task_queue = TaskQueue(f"{state_dir}/task_queue.json")
        self.conflict_detector = ConflictDetector(self.task_queue, self.registry)
        self.priority_manager = PriorityManager()
    
    # ========== 提供给 Layer 2 (Orchestrator) 的接口 ==========
    
    def get_roles_status(self) -> Dict[str, Any]:
        """
        查询所有角色状态
        
        Returns:
            {
                "roles": {...},
                "timestamp": "..."
            }
        """
        return {
            "roles": self.registry.get_status(),
            "timestamp": datetime.now().isoformat()
        }
    
    def submit_task(self, task_data) -> Dict[str, Any]:
        """
        提交新任务
        
        Args:
            task_data: 任务数据 (Task对象或字典) {
                "project_id": "...",
                "role_id": "...",
                "name": "...",
                "description": "...",
                "priority": "P0/P1/P2/P3",
                "depends_on": [...]
            }
            
        Returns:
            {
                "success": True/False,
                "task_id": "...",
                "conflicts": [...],
                "message": "..."
            }
        """
        # 处理 Task 对象或字典
        if isinstance(task_data, Task):
            task = task_data
        else:
            # 创建任务对象
            task = Task(
                project_id=task_data.get("project_id", ""),
                role_id=task_data.get("role_id", ""),
                name=task_data.get("name", ""),
                description=task_data.get("description", ""),
                priority=task_data.get("priority", "P2"),
                depends_on=task_data.get("depends_on", [])
            )
        
        # 验证角色存在
        if not self.registry.get(task.role_id):
            return {
                "success": False,
                "task_id": None,
                "conflicts": [],
                "message": f"角色 {task.role_id} 不存在"
            }
        
        # 验证优先级
        if not self.priority_manager.validate_priority(task.priority):
            return {
                "success": False,
                "task_id": None,
                "conflicts": [],
                "message": f"无效的优先级: {task.priority}"
            }
        
        # 冲突检测
        conflicts = self.conflict_detector.check_task_submit(task)
        errors = [c for c in conflicts if c.severity == "error"]
        
        if errors:
            return {
                "success": False,
                "task_id": None,
                "conflicts": [c.to_dict() for c in conflicts],
                "message": "提交失败，存在严重冲突"
            }
        
        # 提交任务
        task_id = self.task_queue.submit(task)
        
        # 添加到角色队列
        self.registry.add_to_queue(task.role_id, task_id)
        
        # 如果是P0任务且角色正忙，考虑抢占
        if task.priority == "P0":
            role = self.registry.get(task.role_id)
            if role and role.status == "busy":
                current_task = self.task_queue.get(role.current_task)
                if current_task and self.priority_manager.should_preempt(task, current_task):
                    logger.info(f"P0 task {task_id} will preempt current task {current_task.id}")
                    # 实际抢占逻辑在worker层处理
        
        return {
            "success": True,
            "task_id": task_id,
            "conflicts": [c.to_dict() for c in conflicts if c.severity != "error"],
            "message": "任务已提交"
        }
    
    def query_schedule(self, required_roles: List[str], duration_minutes: int) -> Dict[str, Any]:
        """
        查询可行时间窗口
        
        Args:
            required_roles: 所需角色ID列表
            duration_minutes: 预计持续时间（分钟）
            
        Returns:
            {
                "earliest_start": "...",
                "estimated_duration_minutes": ...,
                "role_availability": [...],
                "feasible": True/False
            }
        """
        status = self.registry.get_status()
        
        # 检查所需角色是否都有空闲时段
        available_slots = []
        max_wait_minutes = 0
        
        for role_id in required_roles:
            if role_id in status:
                role_status = status[role_id]
                
                if role_status["status"] == "idle":
                    available_slots.append({
                        "role_id": role_id,
                        "role_type": role_status["type"],
                        "available": "now"
                    })
                else:
                    # 估算等待时间
                    queue_depth = role_status["queue_depth"]
                    avg_duration = role_status["metrics"]["avg_duration"]
                    wait_minutes = queue_depth * avg_duration
                    
                    available_slots.append({
                        "role_id": role_id,
                        "role_type": role_status["type"],
                        "available": f"in_{int(wait_minutes)}_minutes",
                        "wait_minutes": int(wait_minutes)
                    })
                    
                    max_wait_minutes = max(max_wait_minutes, wait_minutes)
            else:
                available_slots.append({
                    "role_id": role_id,
                    "available": "unknown",
                    "error": "角色不存在"
                })
        
        # 判断可行性
        feasible = all(
            s.get("available") == "now" or 
            s.get("wait_minutes", 999) < 60  # 等待少于1小时认为可行
            for s in available_slots
            if "error" not in s
        )
        
        earliest_start = datetime.now()
        if max_wait_minutes > 0:
            from datetime import timedelta
            earliest_start += timedelta(minutes=max_wait_minutes)
        
        return {
            "earliest_start": earliest_start.isoformat(),
            "estimated_duration_minutes": duration_minutes,
            "role_availability": available_slots,
            "feasible": feasible
        }
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态字典，不存在返回None
        """
        task = self.task_queue.get(task_id)
        if not task:
            return None
        
        return {
            "task_id": task.id,
            "name": task.name,
            "status": task.status,
            "priority": task.priority,
            "role_id": task.role_id,
            "project_id": task.project_id,
            "depends_on": task.depends_on,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "retry_count": task.retry_count
        }
    
    # ========== 提供给 Role Workers 的接口 ==========
    
    def acquire_lock(self, role_id: str, task_id: str) -> Dict[str, Any]:
        """
        角色申请锁
        
        Args:
            role_id: 角色ID
            task_id: 任务ID
            
        Returns:
            {
                "acquired": True/False,
                "role_id": "...",
                "task_id": "...",
                "timestamp": "..."
            }
        """
        acquired = self.lock_manager.acquire(role_id, task_id)
        
        if acquired:
            # 更新角色状态
            self.registry.update_status(role_id, "busy", task_id)
            # 更新任务状态
            self.task_queue.update_status(task_id, "processing")
        
        return {
            "acquired": acquired,
            "role_id": role_id,
            "task_id": task_id,
            "timestamp": datetime.now().isoformat()
        }
    
    def release_lock(self, role_id: str) -> Dict[str, Any]:
        """
        角色释放锁
        
        Args:
            role_id: 角色ID
            
        Returns:
            {
                "released": True/False,
                "role_id": "...",
                "timestamp": "..."
            }
        """
        released = self.lock_manager.release(role_id)
        
        if released:
            # 更新角色状态
            self.registry.update_status(role_id, "idle", None)
        
        return {
            "released": released,
            "role_id": role_id,
            "timestamp": datetime.now().isoformat()
        }
    
    def poll_task(self, role_id: str) -> Optional[Dict[str, Any]]:
        """
        角色轮询获取任务
        
        Args:
            role_id: 角色ID
            
        Returns:
            任务数据字典，无任务返回None
        """
        # 检查是否有锁
        lock_info = self.lock_manager.get_lock_info(role_id)
        if not lock_info:
            logger.debug(f"Role {role_id} has no lock, cannot poll task")
            return None
        
        # 获取下一个任务
        task = self.task_queue.get_next_for_role(role_id)
        
        if task:
            return {
                "task_id": task.id,
                "project_id": task.project_id,
                "name": task.name,
                "description": task.description,
                "priority": task.priority,
                "depends_on": task.depends_on
            }
        
        return None
    
    def complete_task(self, task_id: str, success: bool, result: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        角色完成任务
        
        Args:
            task_id: 任务ID
            success: 是否成功
            result: 任务结果
            
        Returns:
            {
                "task_id": "...",
                "status": "completed"/"failed",
                "timestamp": "..."
            }
        """
        status = "completed" if success else "failed"
        self.task_queue.update_status(task_id, status, result)
        
        # 更新角色指标
        task = self.task_queue.get(task_id)
        if task:
            role = self.registry.get(task.role_id)
            if role and task.started_at and task.completed_at:
                duration = (task.completed_at - task.started_at).total_seconds() / 60
                self.registry.update_metrics(task.role_id, duration, success)
            
            # 从角色队列移除
            self.registry.remove_from_queue(task.role_id, task_id)
        
        return {
            "task_id": task_id,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
    
    # ========== 维护接口 ==========
    
    def cleanup(self) -> Dict[str, Any]:
        """
        清理过期锁和状态
        
        Returns:
            清理结果统计
        """
        # 清理过期锁
        cleaned_locks = self.lock_manager.cleanup_expired()
        
        # 检测死锁
        deadlock = self.conflict_detector.detect_deadlock()
        
        result = {
            "cleaned_locks": cleaned_locks,
            "deadlock_detected": deadlock is not None,
            "deadlock_tasks": deadlock,
            "timestamp": datetime.now().isoformat()
        }
        
        if deadlock:
            logger.error(f"Deadlock detected: {deadlock}")
        
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取系统统计信息
        
        Returns:
            综合统计信息
        """
        return {
            "roles": {
                "total": len(self.registry.list_all()),
                "idle": len(self.registry.get_idle_roles()),
                "busy": len([r for r in self.registry.list_all() if r.status == "busy"]),
                "by_type": self._count_roles_by_type()
            },
            "tasks": self.task_queue.get_statistics(),
            "locks": {
                "active": len(self.lock_manager.get_all_locks())
            },
            "conflicts": self.conflict_detector.get_conflict_summary(),
            "timestamp": datetime.now().isoformat()
        }
    
    def _count_roles_by_type(self) -> Dict[str, int]:
        """按类型统计角色数量"""
        counts = {}
        for role in self.registry.list_all():
            counts[role.type] = counts.get(role.type, 0) + 1
        return counts
