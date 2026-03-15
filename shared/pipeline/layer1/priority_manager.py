"""
优先级管理器
管理任务优先级计算和排序
"""
import logging
from datetime import datetime
from typing import List, Dict, Any

from shared.models import Task

logger = logging.getLogger(__name__)


class PriorityManager:
    """
    优先级管理器
    
    优先级等级:
    - P0: 紧急，可抢占 (weight=100)
    - P1: 高 (weight=50)
    - P2: 中 (weight=10)
    - P3: 低 (weight=1)
    """
    
    PRIORITY_LEVELS = {
        "P0": {"name": "紧急", "weight": 100, "preempt": True},
        "P1": {"name": "高", "weight": 50, "preempt": False},
        "P2": {"name": "中", "weight": 10, "preempt": False},
        "P3": {"name": "低", "weight": 1, "preempt": False}
    }
    
    # 等待时间加成上限
    MAX_WAIT_BONUS = 20
    # 依赖惩罚系数
    DEP_PENALTY = 2
    
    def calculate_priority_score(self, task: Task) -> int:
        """
        计算任务优先级分数
        
        计算公式:
        score = base_weight + wait_bonus - dep_penalty
        
        其中:
        - base_weight: 优先级基础权重
        - wait_bonus: 等待时间加成 (每等待1小时+1分，最多+20)
        - dep_penalty: 依赖链长度惩罚 (每个依赖-2分)
        
        Args:
            task: 任务
            
        Returns:
            优先级分数 (越高越优先)
        """
        # 基础权重
        base_weight = self.PRIORITY_LEVELS.get(task.priority, {}).get("weight", 10)
        
        # 等待时间加成
        wait_bonus = 0
        if task.created_at:
            wait_hours = (datetime.now() - task.created_at).total_seconds() / 3600
            wait_bonus = min(int(wait_hours), self.MAX_WAIT_BONUS)
        
        # 依赖链长度惩罚
        dep_penalty = len(task.depends_on) * self.DEP_PENALTY
        
        score = base_weight + wait_bonus - dep_penalty
        
        return max(0, score)  # 确保非负
    
    def sort_queue(self, tasks: List[Task]) -> List[Task]:
        """
        按优先级排序队列
        
        排序规则:
        1. 优先级分数降序
        2. 同分数按创建时间升序（先到先服务）
        
        Args:
            tasks: 任务列表
            
        Returns:
            排序后的任务列表
        """
        # 计算每个任务的分数
        scored_tasks = [(task, self.calculate_priority_score(task)) for task in tasks]
        
        # 排序: 分数降序，同分数按创建时间升序
        scored_tasks.sort(
            key=lambda x: (-x[1], x[0].created_at or datetime.min)
        )
        
        return [task for task, _ in scored_tasks]
    
    def should_preempt(self, new_task: Task, current_task: Task) -> bool:
        """
        判断新任务是否应该抢占当前任务
        
        抢占规则:
        - 只有P0任务可以抢占
        - P0不能抢占另一个P0
        - P0可以抢占P1/P2/P3
        
        Args:
            new_task: 新任务
            current_task: 当前执行的任务
            
        Returns:
            True: 应该抢占
            False: 不应该抢占
        """
        if new_task.priority != "P0":
            return False
        
        if current_task.priority == "P0":
            return False
        
        return self.PRIORITY_LEVELS["P0"]["preempt"]
    
    def get_queue_position(self, task: Task, queue: List[Task]) -> int:
        """
        获取任务在队列中的位置
        
        Args:
            task: 目标任务
            queue: 队列
            
        Returns:
            位置索引（0-based），-1表示不在队列中
        """
        sorted_queue = self.sort_queue(queue)
        
        for i, t in enumerate(sorted_queue):
            if t.id == task.id:
                return i
        
        return -1
    
    def estimate_wait_time(self, task: Task, role_avg_duration: float = 30.0) -> Dict[str, Any]:
        """
        估算任务等待时间
        
        Args:
            task: 任务
            role_avg_duration: 角色平均任务耗时（分钟）
            
        Returns:
            等待时间估算信息
        """
        # 获取同角色的待处理任务
        # 这里简化处理，实际应该查询队列
        
        position = len(task.depends_on)  # 简化: 依赖越多等待越久
        
        estimated_wait_minutes = position * role_avg_duration
        
        return {
            "queue_position": position,
            "estimated_wait_minutes": estimated_wait_minutes,
            "estimated_wait_hours": round(estimated_wait_minutes / 60, 1),
            "priority": task.priority,
            "priority_score": self.calculate_priority_score(task)
        }
    
    def get_priority_info(self, task: Task) -> Dict[str, Any]:
        """
        获取任务优先级信息
        
        Args:
            task: 任务
            
        Returns:
            优先级详细信息
        """
        level_info = self.PRIORITY_LEVELS.get(task.priority, {})
        score = self.calculate_priority_score(task)
        
        return {
            "priority": task.priority,
            "priority_name": level_info.get("name", "未知"),
            "base_weight": level_info.get("weight", 0),
            "can_preempt": level_info.get("preempt", False),
            "score": score,
            "wait_hours": score - level_info.get("weight", 0) if task.created_at else 0
        }
    
    @classmethod
    def validate_priority(cls, priority: str) -> bool:
        """
        验证优先级是否有效
        
        Args:
            priority: 优先级字符串
            
        Returns:
            True: 有效
            False: 无效
        """
        return priority in cls.PRIORITY_LEVELS
    
    @classmethod
    def get_available_priorities(cls) -> Dict[str, str]:
        """
        获取所有可用优先级
        
        Returns:
            优先级到名称的映射
        """
        return {k: v["name"] for k, v in cls.PRIORITY_LEVELS.items()}
