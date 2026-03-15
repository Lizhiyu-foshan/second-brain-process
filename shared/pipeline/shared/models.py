"""
共享数据模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
import json


@dataclass
class Role:
    """角色定义"""
    id: str
    type: str
    name: str
    capabilities: List[str]
    status: str = "idle"  # idle, busy, error
    queue: List[str] = field(default_factory=list)
    current_task: Optional[str] = None
    metrics: 'RoleMetrics' = None
    config: 'RoleConfig' = None
    
    def __post_init__(self):
        if self.metrics is None:
            self.metrics = RoleMetrics()
        if self.config is None:
            self.config = RoleConfig()


@dataclass
class RoleMetrics:
    """角色指标"""
    total_tasks: int = 0
    success_count: int = 0
    fail_count: int = 0
    avg_duration: float = 0.0  # minutes
    success_rate: float = 1.0
    
    def update(self, duration_minutes: float, success: bool):
        """更新指标"""
        self.total_tasks += 1
        if success:
            self.success_count += 1
        else:
            self.fail_count += 1
        
        # 更新平均耗时
        self.avg_duration = (
            (self.avg_duration * (self.total_tasks - 1) + duration_minutes)
            / self.total_tasks
        )
        
        self.success_rate = self.success_count / self.total_tasks


@dataclass
class RoleConfig:
    """角色配置"""
    poll_interval_minutes: int = 15
    lock_timeout_minutes: int = 30
    max_concurrent: int = 1


@dataclass
class Task:
    """任务定义"""
    id: str = ""
    project_id: str = ""
    role_id: str = ""
    name: str = ""
    description: str = ""
    priority: str = "P2"  # P0, P1, P2, P3
    status: str = "pending"  # pending, processing, completed, failed
    depends_on: List[str] = field(default_factory=list)
    created_at: datetime = None
    started_at: datetime = None
    completed_at: datetime = None
    retry_count: int = 0
    max_retries: int = 3
    result: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.depends_on is None:
            self.depends_on = []
        if self.result is None:
            self.result = {}


@dataclass
class Conflict:
    """冲突定义"""
    type: str
    severity: str  # error, warning, info
    message: str
    suggestion: str
    detected_at: datetime = None
    
    def __post_init__(self):
        if self.detected_at is None:
            self.detected_at = datetime.now()
    
    def to_dict(self) -> Dict:
        return {
            "type": self.type,
            "severity": self.severity,
            "message": self.message,
            "suggestion": self.suggestion,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None
        }


@dataclass
class LockInfo:
    """锁信息"""
    role_id: str
    task_id: str
    acquired_at: datetime
    timeout_ms: int
    
    def to_dict(self) -> Dict:
        return {
            "role_id": self.role_id,
            "task_id": self.task_id,
            "acquired_at": self.acquired_at.isoformat(),
            "timeout_ms": self.timeout_ms
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'LockInfo':
        return cls(
            role_id=data["role_id"],
            task_id=data["task_id"],
            acquired_at=datetime.fromisoformat(data["acquired_at"]),
            timeout_ms=data["timeout_ms"]
        )


class EnhancedJSONEncoder(json.JSONEncoder):
    """支持datetime的JSON编码器"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return super().default(obj)
