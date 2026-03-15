"""
任务队列
管理全局任务队列的提交、获取和状态更新
"""
import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import uuid4

from shared.models import Task, EnhancedJSONEncoder

logger = logging.getLogger(__name__)


def get_workspace_dir() -> Path:
    """获取工作目录，优先使用环境变量"""
    base = os.getenv("OPENCLAW_WORKSPACE")
    if base:
        return Path(base)
    return Path.cwd() / ".openclaw" / "workspace"


class TaskQueue:
    """
    任务队列
    
    职责:
    - 提交新任务
    - 获取角色下一个可执行任务
    - 更新任务状态
    - 任务统计查询
    """
    
    def __init__(self, state_file: str = None):
        """
        初始化任务队列
        
        Args:
            state_file: 状态文件路径
        """
        if state_file is None:
            state_file = get_workspace_dir() / "shared" / "pipeline" / "state" / "task_queue.json"
        else:
            state_file = Path(state_file)
        
        self.state_file = state_file
        self.tasks: Dict[str, Task] = {}
        self._load()
    
    def _load(self):
        """从文件加载任务"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    for task_id, task_data in data.get("tasks", {}).items():
                        self.tasks[task_id] = self._deserialize_task(task_data)
                logger.info(f"Loaded {len(self.tasks)} tasks from {self.state_file}")
            except json.JSONDecodeError as e:
                logger.error(f"State file corrupted: {e}")
                # 备份损坏的文件
                self._backup_corrupted_file()
                self.tasks = {}
            except PermissionError as e:
                logger.error(f"Permission denied reading state: {e}")
                raise
            except Exception as e:
                logger.error(f"Failed to load tasks: {e}")
                self.tasks = {}
    
    def _save(self):
        """
        保存任务到文件（原子写入）
        
        使用临时文件 + os.replace 实现原子写入，避免多进程写入冲突。
        """
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            
            data = {
                "tasks": {
                    task_id: self._serialize_task(task)
                    for task_id, task in self.tasks.items()
                },
                "last_updated": datetime.now().isoformat()
            }
            
            # 原子写入：先写入临时文件，再原子替换
            dir_name = os.path.dirname(self.state_file)
            fd, temp_path = tempfile.mkstemp(dir=dir_name, suffix='.json.tmp')
            
            try:
                with os.fdopen(fd, 'w') as f:
                    json.dump(data, f, indent=2, cls=EnhancedJSONEncoder)
                    f.flush()
                    os.fsync(fd)  # 确保数据落盘
                
                # 原子替换原文件
                os.replace(temp_path, self.state_file)
                
            except Exception:
                # 清理临时文件
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise
                
        except Exception as e:
            logger.error(f"Failed to save tasks: {e}")
            raise
    
    def _backup_corrupted_file(self):
        """备份损坏的状态文件"""
        try:
            if os.path.exists(self.state_file):
                backup_path = f"{self.state_file}.corrupted.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.rename(self.state_file, backup_path)
                logger.warning(f"Corrupted state file backed up to: {backup_path}")
        except Exception as e:
            logger.error(f"Failed to backup corrupted file: {e}")
    
    def _serialize_task(self, task: Task) -> Dict:
        """序列化任务"""
        return {
            "id": task.id,
            "project_id": task.project_id,
            "role_id": task.role_id,
            "name": task.name,
            "description": task.description,
            "priority": task.priority,
            "status": task.status,
            "depends_on": task.depends_on,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "retry_count": task.retry_count,
            "max_retries": task.max_retries,
            "result": task.result
        }
    
    def _deserialize_task(self, data: Dict) -> Task:
        """反序列化任务"""
        task = Task(
            id=data["id"],
            project_id=data.get("project_id", ""),
            role_id=data.get("role_id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            priority=data.get("priority", "P2"),
            status=data.get("status", "pending"),
            depends_on=data.get("depends_on", []),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            result=data.get("result", {})
        )
        
        # 恢复时间字段
        if data.get("created_at"):
            task.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("started_at"):
            task.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            task.completed_at = datetime.fromisoformat(data["completed_at"])
        
        return task
    
    def submit(self, task: Task) -> str:
        """
        提交新任务
        
        Args:
            task: 任务对象
            
        Returns:
            任务ID
        """
        # 生成任务ID
        if not task.id:
            task.id = f"task_{uuid4().hex[:8]}"
        
        task.status = "pending"
        task.created_at = datetime.now()
        
        self.tasks[task.id] = task
        self._save()
        
        logger.info(f"Submitted task: {task.id} ({task.name}) for role {task.role_id}")
        return task.id
    
    def get(self, task_id: str) -> Optional[Task]:
        """
        获取任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            Task对象，不存在则返回None
        """
        return self.tasks.get(task_id)
    
    def get_next_for_role(self, role_id: str) -> Optional[Task]:
        """
        获取角色下一个可执行任务
        
        逻辑:
        1. 获取该角色的pending任务
        2. 过滤掉依赖未完成的任务
        3. 按优先级排序
        4. 返回优先级最高的任务
        
        Args:
            role_id: 角色ID
            
        Returns:
            Task对象，没有可执行任务则返回None
        """
        # 获取该角色的pending任务
        role_tasks = [
            task for task in self.tasks.values()
            if task.role_id == role_id and task.status == "pending"
        ]
        
        if not role_tasks:
            return None
        
        # 过滤掉依赖未完成的任务
        ready_tasks = []
        for task in role_tasks:
            deps_completed = True
            for dep_id in task.depends_on:
                dep_task = self.tasks.get(dep_id)
                if not dep_task or dep_task.status != "completed":
                    deps_completed = False
                    break
            
            if deps_completed:
                ready_tasks.append(task)
        
        if not ready_tasks:
            return None
        
        # 按优先级排序 (P0 > P1 > P2 > P3)
        priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        ready_tasks.sort(key=lambda t: priority_order.get(t.priority, 2))
        
        # 同优先级按创建时间排序
        ready_tasks.sort(key=lambda t: (priority_order.get(t.priority, 2), t.created_at or datetime.min))
        
        return ready_tasks[0]
    
    def update_status(self, task_id: str, status: str, result: Dict = None):
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态 (pending, processing, completed, failed)
            result: 任务结果
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found for status update")
            return
        
        old_status = task.status
        task.status = status
        
        if status == "processing":
            task.started_at = datetime.now()
        elif status in ["completed", "failed"]:
            task.completed_at = datetime.now()
            if result:
                task.result = result
        
        self._save()
        logger.info(f"Task {task_id} status: {old_status} -> {status}")
    
    def increment_retry(self, task_id: str) -> bool:
        """
        增加重试计数
        
        Args:
            task_id: 任务ID
            
        Returns:
            True: 还可以重试
            False: 超过最大重试次数
        """
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        task.retry_count += 1
        
        if task.retry_count >= task.max_retries:
            logger.warning(f"Task {task_id} exceeded max retries ({task.max_retries})")
            return False
        
        # 重置为pending状态以便重试
        task.status = "pending"
        self._save()
        
        logger.info(f"Task {task_id} retry {task.retry_count}/{task.max_retries}")
        return True
    
    def get_statistics(self) -> Dict[str, int]:
        """
        获取队列统计
        
        Returns:
            状态到数量的映射
        """
        stats = {"pending": 0, "processing": 0, "completed": 0, "failed": 0}
        for task in self.tasks.values():
            stats[task.status] = stats.get(task.status, 0) + 1
        return stats
    
    def get_by_project(self, project_id: str) -> List[Task]:
        """
        获取项目的所有任务
        
        Args:
            project_id: 项目ID
            
        Returns:
            任务列表
        """
        return [task for task in self.tasks.values() if task.project_id == project_id]
    
    def get_by_role(self, role_id: str) -> List[Task]:
        """
        获取角色的所有任务
        
        Args:
            role_id: 角色ID
            
        Returns:
            任务列表
        """
        return [task for task in self.tasks.values() if task.role_id == role_id]
    
    def get_by_status(self, status: str) -> List[Task]:
        """
        获取指定状态的所有任务
        
        Args:
            status: 任务状态
            
        Returns:
            任务列表
        """
        return [task for task in self.tasks.values() if task.status == status]
    
    def list_all(self) -> List[Task]:
        """
        获取所有任务
        
        Returns:
            所有任务的列表
        """
        return list(self.tasks.values())
    
    def delete(self, task_id: str) -> bool:
        """
        删除任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            True: 删除成功
            False: 任务不存在
        """
        if task_id in self.tasks:
            del self.tasks[task_id]
            self._save()
            logger.info(f"Deleted task: {task_id}")
            return True
        return False
    
    def get_dependency_chain(self, task_id: str) -> List[str]:
        """
        获取任务的依赖链
        
        Args:
            task_id: 任务ID
            
        Returns:
            依赖任务ID列表（按依赖顺序）
        """
        chain = []
        visited = set()
        
        def collect_deps(tid):
            if tid in visited:
                return
            visited.add(tid)
            
            task = self.tasks.get(tid)
            if task:
                for dep_id in task.depends_on:
                    collect_deps(dep_id)
                    if dep_id not in chain:
                        chain.append(dep_id)
        
        collect_deps(task_id)
        return chain
