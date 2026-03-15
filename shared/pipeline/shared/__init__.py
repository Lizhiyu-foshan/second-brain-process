"""
Shared Components
共享组件 - 数据模型、工具函数
"""

from shared.models import (
    Role, RoleMetrics, RoleConfig,
    Task, Conflict, LockInfo,
    EnhancedJSONEncoder
)

__all__ = [
    'Role', 'RoleMetrics', 'RoleConfig',
    'Task', 'Conflict', 'LockInfo',
    'EnhancedJSONEncoder'
]
