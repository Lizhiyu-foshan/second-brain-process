"""
Layer 0: 角色工作器 (Role Workers)

架构师、开发者、测试员工作器的集合
"""
from layer0.base import BaseRoleWorker, WorkerPool, WorkerState, TaskResult
from layer0.architect import ArchitectWorker
from layer0.developer import DeveloperWorker
from layer0.tester import TesterWorker
from layer0.ai_client import AliyunAIClient, get_ai_client, set_ai_client

__all__ = [
    'BaseRoleWorker',
    'WorkerPool', 
    'WorkerState',
    'TaskResult',
    'ArchitectWorker',
    'DeveloperWorker',
    'TesterWorker',
    'AliyunAIClient',
    'get_ai_client',
    'set_ai_client'
]
