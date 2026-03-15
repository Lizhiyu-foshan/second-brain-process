"""
测试钩子系统
支持在关键注入点注册钩子函数，用于测试和监控
"""
import logging
import functools
from typing import Dict, List, Callable, Any, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class HookPoint(Enum):
    """钩子注入点枚举"""
    # LockManager 钩子
    LOCK_BEFORE_ACQUIRE = "lock:before_acquire"
    LOCK_AFTER_ACQUIRE = "lock:after_acquire"
    LOCK_BEFORE_RELEASE = "lock:before_release"
    LOCK_AFTER_RELEASE = "lock:after_release"
    LOCK_TIMEOUT = "lock:timeout"
    
    # TaskQueue 钩子
    TASK_BEFORE_SUBMIT = "task:before_submit"
    TASK_AFTER_SUBMIT = "task:after_submit"
    TASK_BEFORE_COMPLETE = "task:before_complete"
    TASK_AFTER_COMPLETE = "task:after_complete"
    TASK_POLL = "task:poll"
    
    # Orchestrator 钩子
    ORCH_BEFORE_CREATE = "orchestrator:before_create"
    ORCH_AFTER_CREATE = "orchestrator:after_create"
    ORCH_BEFORE_DECISION = "orchestrator:before_decision"
    ORCH_AFTER_DECISION = "orchestrator:after_decision"
    ORCH_PDCA_CYCLE = "orchestrator:pdca_cycle"
    
    # Worker 钩子
    WORKER_BEFORE_EXECUTE = "worker:before_execute"
    WORKER_AFTER_EXECUTE = "worker:after_execute"
    WORKER_ERROR = "worker:error"


@dataclass
class HookContext:
    """钩子上下文"""
    hook_point: HookPoint
    timestamp: datetime
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "hook_point": self.hook_point.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data
        }


class TestHooks:
    """
    测试钩子管理器
    
    单例模式，全局管理所有钩子注册和触发
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._hooks: Dict[HookPoint, List[Callable]] = {point: [] for point in HookPoint}
        self._enabled = True
        self._call_history: List[HookContext] = []
        self._max_history = 1000
        
    def register(self, hook_point: HookPoint, callback: Callable[[HookContext], None]) -> None:
        """
        注册钩子函数
        
        Args:
            hook_point: 钩子注入点
            callback: 回调函数，接收 HookContext 参数
        """
        if hook_point not in self._hooks:
            self._hooks[hook_point] = []
        self._hooks[hook_point].append(callback)
        logger.debug(f"Registered hook for {hook_point.value}")
    
    def unregister(self, hook_point: HookPoint, callback: Callable) -> bool:
        """
        注销钩子函数
        
        Returns:
            True if found and removed, False otherwise
        """
        if hook_point in self._hooks and callback in self._hooks[hook_point]:
            self._hooks[hook_point].remove(callback)
            logger.debug(f"Unregistered hook for {hook_point.value}")
            return True
        return False
    
    def unregister_all(self, hook_point: Optional[HookPoint] = None) -> None:
        """
        注销所有钩子
        
        Args:
            hook_point: 如果指定，只清除该点的钩子；否则清除所有
        """
        if hook_point:
            self._hooks[hook_point] = []
            logger.debug(f"Unregistered all hooks for {hook_point.value}")
        else:
            for point in HookPoint:
                self._hooks[point] = []
            logger.debug("Unregistered all hooks")
    
    def trigger(self, hook_point: HookPoint, **data) -> None:
        """
        触发钩子
        
        Args:
            hook_point: 钩子注入点
            **data: 传递给钩子的数据
        """
        if not self._enabled:
            return
            
        context = HookContext(
            hook_point=hook_point,
            timestamp=datetime.now(),
            data=data
        )
        
        # 记录调用历史
        self._call_history.append(context)
        if len(self._call_history) > self._max_history:
            self._call_history.pop(0)
        
        # 调用所有注册的钩子
        for callback in self._hooks.get(hook_point, []):
            try:
                callback(context)
            except Exception as e:
                logger.error(f"Hook {hook_point.value} callback failed: {e}")
    
    def enable(self) -> None:
        """启用钩子系统"""
        self._enabled = True
        logger.info("Test hooks enabled")
    
    def disable(self) -> None:
        """禁用钩子系统"""
        self._enabled = False
        logger.info("Test hooks disabled")
    
    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self._enabled
    
    def get_call_history(self, hook_point: Optional[HookPoint] = None) -> List[HookContext]:
        """
        获取调用历史
        
        Args:
            hook_point: 如果指定，只返回该点的历史
        """
        if hook_point:
            return [ctx for ctx in self._call_history if ctx.hook_point == hook_point]
        return self._call_history.copy()
    
    def clear_history(self) -> None:
        """清空调用历史"""
        self._call_history = []
        logger.debug("Hook call history cleared")
    
    def get_registered_hooks(self) -> Dict[str, int]:
        """
        获取已注册的钩子统计
        
        Returns:
            {hook_point_value: count}
        """
        return {point.value: len(callbacks) for point, callbacks in self._hooks.items() if callbacks}


def with_hook(hook_point: HookPoint, **context_data):
    """
    装饰器：在函数执行前后触发钩子
    
    Usage:
        @with_hook(HookPoint.LOCK_BEFORE_ACQUIRE, operation="acquire")
        def acquire_lock(self, ...):
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            hooks = TestHooks()
            
            # 构建上下文数据
            data = {
                "function": func.__name__,
                "args": str(args),
                "kwargs": str(kwargs),
                **context_data
            }
            
            # 触发前置钩子
            hooks.trigger(hook_point, **data)
            
            try:
                result = func(*args, **kwargs)
                # 触发后置钩子（成功后）
                hooks.trigger(
                    HookPoint(hook_point.value.replace("before", "after")),
                    **{**data, "result": str(result), "success": True}
                )
                return result
            except Exception as e:
                # 触发错误钩子
                hooks.trigger(
                    HookPoint(hook_point.value.replace("before", "error")),
                    **{**data, "error": str(e), "success": False}
                )
                raise
        
        return wrapper
    return decorator


# 全局钩子实例
hooks = TestHooks()
