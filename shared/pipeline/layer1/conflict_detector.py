"""
冲突检测器
检测任务调度冲突：角色过载、依赖冲突、优先级反转、死锁
"""
import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Set, Any

from shared.models import Task, Conflict
from layer1.task_queue import TaskQueue
from layer1.role_registry import RoleRegistry

logger = logging.getLogger(__name__)


class ConflictDetector:
    """
    冲突检测器
    
    检测类型:
    - ROLE_OVERLOAD: 角色队列过载
    - MISSING_DEPENDENCY: 依赖任务不存在
    - INCOMPLETE_DEPENDENCY: 依赖任务未完成
    - PRIORITY_INVERSION: 优先级反转
    - DEADLOCK: 循环依赖死锁
    """
    
    def __init__(self, task_queue: TaskQueue, role_registry: RoleRegistry):
        """
        初始化冲突检测器
        
        Args:
            task_queue: 任务队列
            role_registry: 角色注册表
        """
        self.task_queue = task_queue
        self.role_registry = role_registry
        self.conflict_log: List[Conflict] = []
    
    def check_task_submit(self, task: Task) -> List[Conflict]:
        """
        检查任务提交时的冲突
        
        Args:
            task: 待提交的任务
            
        Returns:
            冲突列表（空列表表示无冲突）
        """
        conflicts = []
        
        # 1. 检查同一角色多任务冲突（角色过载）
        role = self.role_registry.get(task.role_id)
        if role:
            if role.status == "busy" and len(role.queue) > 0:
                conflicts.append(Conflict(
                    type="ROLE_OVERLOAD",
                    severity="warning",
                    message=f"角色 {role.name} 已有 {len(role.queue)} 个排队任务，当前正忙",
                    suggestion="考虑错峰安排或增加角色实例"
                ))
            
            # 检查队列深度
            role_tasks = self.task_queue.get_by_role(task.role_id)
            pending_count = len([t for t in role_tasks if t.status == "pending"])
            if pending_count >= 5:
                conflicts.append(Conflict(
                    type="ROLE_OVERLOAD",
                    severity="warning",
                    message=f"角色 {role.name} 队列中有 {pending_count} 个待处理任务",
                    suggestion="建议增加该角色实例或延后提交"
                ))
        
        # 2. 检查依赖冲突
        for dep_task_id in task.depends_on:
            dep_task = self.task_queue.get(dep_task_id)
            
            if not dep_task:
                conflicts.append(Conflict(
                    type="MISSING_DEPENDENCY",
                    severity="error",
                    message=f"依赖任务 {dep_task_id} 不存在",
                    suggestion="检查任务ID是否正确，或确保依赖任务先提交"
                ))
            elif dep_task.status == "failed":
                conflicts.append(Conflict(
                    type="FAILED_DEPENDENCY",
                    severity="error",
                    message=f"依赖任务 {dep_task_id} 已失败",
                    suggestion="需要先修复依赖任务或移除依赖关系"
                ))
            elif dep_task.status not in ["completed"]:
                conflicts.append(Conflict(
                    type="INCOMPLETE_DEPENDENCY",
                    severity="info",
                    message=f"依赖任务 {dep_task_id} 状态为 {dep_task.status}，当前任务将等待其完成",
                    suggestion="任务将自动排队，等待依赖完成后执行"
                ))
        
        # 3. 检查优先级反转
        if task.priority == "P0":
            # P0任务检查是否有低优先级任务占用资源
            if role and role.status == "busy":
                current_task = self.task_queue.get(role.current_task)
                if current_task and current_task.priority != "P0":
                    conflicts.append(Conflict(
                        type="PRIORITY_INVERSION",
                        severity="info",
                        message=f"P0任务将抢占当前执行中的低优先级任务 {current_task.id}",
                        suggestion="当前任务将被暂停，P0任务优先执行"
                    ))
        
        # 4. 检查循环依赖（简单检查）
        if self._has_circular_dependency(task):
            conflicts.append(Conflict(
                type="CIRCULAR_DEPENDENCY",
                severity="error",
                message="检测到循环依赖",
                suggestion="检查任务依赖关系，确保无循环"
            ))
        
        # 记录冲突
        self.conflict_log.extend(conflicts)
        
        return conflicts
    
    def _has_circular_dependency(self, task: Task) -> bool:
        """
        检查任务是否有循环依赖
        
        Args:
            task: 任务
            
        Returns:
            True: 有循环依赖
        """
        visited = set()
        
        def has_cycle(task_id, path):
            if task_id in path:
                return True
            if task_id in visited:
                return False
            
            visited.add(task_id)
            path.add(task_id)
            
            dep_task = self.task_queue.get(task_id)
            if dep_task:
                for dep_id in dep_task.depends_on:
                    if has_cycle(dep_id, path):
                        return True
            
            path.remove(task_id)
            return False
        
        # 检查新任务的依赖链
        for dep_id in task.depends_on:
            if has_cycle(dep_id, {task.id}):
                return True
        
        # 检查是否有其他任务依赖此任务形成环
        for existing_task in self.task_queue.list_all():
            if task.id in existing_task.depends_on:
                # 检查新任务是否依赖现有任务
                if existing_task.id in self._get_all_deps(task):
                    return True
        
        return False
    
    def _get_all_deps(self, task: Task) -> Set[str]:
        """获取任务的所有依赖（递归）"""
        all_deps = set()
        
        def collect(tid):
            t = self.task_queue.get(tid)
            if t:
                for dep_id in t.depends_on:
                    if dep_id not in all_deps:
                        all_deps.add(dep_id)
                        collect(dep_id)
        
        collect(task.id)
        return all_deps
    
    def detect_deadlock(self) -> Optional[List[str]]:
        """
        检测系统中的死锁
        
        死锁定义: 多个任务互相等待依赖完成，形成循环
        
        Returns:
            死锁涉及的任务ID列表，None表示无死锁
        """
        # 构建等待图
        # 边: task_id -> dep_id (task等待dep完成)
        wait_graph = defaultdict(set)
        
        processing_tasks = self.task_queue.get_by_status("processing")
        pending_tasks = self.task_queue.get_by_status("pending")
        
        for task in processing_tasks + pending_tasks:
            if task.depends_on:
                for dep_id in task.depends_on:
                    dep_task = self.task_queue.get(dep_id)
                    if dep_task and dep_task.status != "completed":
                        wait_graph[task.id].add(dep_id)
        
        # 使用DFS检测环
        visited = set()
        rec_stack = set()
        
        def dfs(node, path):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in wait_graph.get(node, []):
                if neighbor not in visited:
                    cycle = dfs(neighbor, path)
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    # 发现环
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:]
            
            path.pop()
            rec_stack.remove(node)
            return None
        
        for node in list(wait_graph.keys()):
            if node not in visited:
                cycle = dfs(node, [])
                if cycle:
                    logger.error(f"Deadlock detected: {cycle}")
                    return cycle
        
        return None
    
    def resolve_deadlock(self, cycle: List[str]) -> Dict[str, Any]:
        """
        自动解决死锁
        
        策略: 取消死锁环中优先级最低的任务
        
        Args:
            cycle: 死锁涉及的任务ID列表
            
        Returns:
            解决结果
        """
        if not cycle:
            return {"resolved": False, "reason": "No deadlock cycle provided"}
        
        # 获取死锁环中所有任务
        cycle_tasks = []
        for task_id in cycle:
            task = self.task_queue.get(task_id)
            if task:
                cycle_tasks.append(task)
        
        if not cycle_tasks:
            return {"resolved": False, "reason": "No tasks found in deadlock cycle"}
        
        # 优先级排序 (P3最低，最容易被取消)
        priority_order = {"P3": 0, "P2": 1, "P1": 2, "P0": 3}
        cycle_tasks.sort(key=lambda t: priority_order.get(t.priority, 1))
        
        # 选择优先级最低的任务取消
        victim = cycle_tasks[0]
        
        # 取消任务（标记为失败）
        self.task_queue.update_status(victim.id, "failed", {
            "error": "Auto-cancelled to resolve deadlock",
            "deadlock_cycle": cycle,
            "resolution_strategy": "cancel_lowest_priority"
        })
        
        logger.warning(f"Deadlock resolved: Cancelled task {victim.id} (priority: {victim.priority})")
        
        return {
            "resolved": True,
            "cancelled_task": victim.id,
            "cancelled_task_name": victim.name,
            "priority": victim.priority,
            "deadlock_cycle": cycle,
            "resolution_strategy": "cancel_lowest_priority"
        }
    
    def detect_and_resolve_deadlock(self) -> Dict[str, Any]:
        """
        检测并自动解决死锁
        
        Returns:
            检测结果和解决操作
        """
        deadlock = self.detect_deadlock()
        
        if not deadlock:
            return {
                "deadlock_detected": False,
                "resolved": False
            }
        
        # 检测到死锁，尝试解决
        resolution = self.resolve_deadlock(deadlock)
        
        return {
            "deadlock_detected": True,
            "deadlock_cycle": deadlock,
            "resolved": resolution.get("resolved", False),
            "resolution": resolution
        }
    
    def detect_resource_starvation(self, threshold_minutes: int = 60) -> List[Dict]:
        """
        检测资源饥饿（长时间等待的任务）
        
        Args:
            threshold_minutes: 饥饿阈值（分钟）
            
        Returns:
            饥饿任务列表
        """
        starved = []
        
        for task in self.task_queue.get_by_status("pending"):
            if task.created_at:
                wait_minutes = (datetime.now() - task.created_at).total_seconds() / 60
                
                if wait_minutes > threshold_minutes:
                    # 检查是否因为依赖阻塞
                    blocked_by = []
                    for dep_id in task.depends_on:
                        dep_task = self.task_queue.get(dep_id)
                        if dep_task and dep_task.status != "completed":
                            blocked_by.append(dep_id)
                    
                    starved.append({
                        "task_id": task.id,
                        "task_name": task.name,
                        "wait_minutes": round(wait_minutes, 1),
                        "blocked_by": blocked_by,
                        "priority": task.priority
                    })
        
        return starved
    
    def get_conflict_summary(self) -> Dict[str, Any]:
        """
        获取冲突汇总
        
        Returns:
            冲突统计信息
        """
        error_count = len([c for c in self.conflict_log if c.severity == "error"])
        warning_count = len([c for c in self.conflict_log if c.severity == "warning"])
        info_count = len([c for c in self.conflict_log if c.severity == "info"])
        
        # 按类型统计
        by_type = defaultdict(int)
        for c in self.conflict_log:
            by_type[c.type] += 1
        
        return {
            "total": len(self.conflict_log),
            "errors": error_count,
            "warnings": warning_count,
            "info": info_count,
            "by_type": dict(by_type),
            "recent": [c.to_dict() for c in self.conflict_log[-10:]]
        }
    
    def clear_log(self):
        """清空冲突日志"""
        self.conflict_log.clear()
