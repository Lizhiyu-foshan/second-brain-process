"""
故障注入器
支持模拟各种故障场景，用于测试系统容错能力
"""
import logging
import random
import time
from typing import Dict, List, Callable, Optional, Any
from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class FaultType(Enum):
    """故障类型"""
    CRASH = "crash"           # 抛出异常
    DELAY = "delay"           # 延迟响应
    ERROR = "error"           # 返回错误结果
    CORRUPTION = "corruption" # 数据损坏
    TIMEOUT = "timeout"       # 超时
    OMISSION = "omission"     # 消息丢失/操作跳过


@dataclass
class FaultConfig:
    """故障配置"""
    fault_type: FaultType
    target: str                          # 目标组件/函数
    probability: float = 1.0             # 触发概率 (0.0-1.0)
    duration_ms: Optional[int] = None    # 延迟时长(DELAY)或超时时长(TIMEOUT)
    exception_type: Optional[type] = None # 异常类型(CRASH)
    error_message: Optional[str] = None  # 错误消息
    corruption_func: Optional[Callable] = None  # 数据损坏函数
    trigger_count: Optional[int] = None  # 触发次数限制
    
    # 内部状态
    _triggered_count: int = field(default=0, init=False)
    _created_at: datetime = field(default_factory=datetime.now, init=False)
    
    def should_trigger(self) -> bool:
        """检查是否应该触发故障"""
        # 检查触发次数限制
        if self.trigger_count is not None and self._triggered_count >= self.trigger_count:
            return False
        
        # 检查概率
        return random.random() < self.probability
    
    def record_trigger(self) -> None:
        """记录一次触发"""
        self._triggered_count += 1


class FaultInjector:
    """
    故障注入器
    
    单例模式，全局管理故障注入配置
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
        self._faults: Dict[str, List[FaultConfig]] = {}  # target -> [FaultConfig]
        self._enabled = False
        self._injection_history: List[Dict] = []
        self._max_history = 500
        
    def enable(self) -> None:
        """启用故障注入"""
        self._enabled = True
        logger.warning("⚠️  Fault injection ENABLED - System may behave unexpectedly!")
    
    def disable(self) -> None:
        """禁用故障注入"""
        self._enabled = False
        logger.info("Fault injection disabled")
    
    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self._enabled
    
    def inject(self, fault_type: FaultType, target: str, 
               probability: float = 1.0, **kwargs) -> FaultConfig:
        """
        注入故障
        
        Args:
            fault_type: 故障类型
            target: 目标组件/函数名
            probability: 触发概率 (0.0-1.0)
            **kwargs: 额外参数
                - duration_ms: 延迟/超时时长
                - exception_type: 异常类型 (CRASH)
                - error_message: 错误消息
                - corruption_func: 数据损坏函数
                - trigger_count: 触发次数限制
        
        Returns:
            FaultConfig 对象
        """
        config = FaultConfig(
            fault_type=fault_type,
            target=target,
            probability=probability,
            **kwargs
        )
        
        if target not in self._faults:
            self._faults[target] = []
        self._faults[target].append(config)
        
        logger.info(f"Injected {fault_type.value} fault into {target} (prob={probability})")
        return config
    
    def remove(self, target: str, fault_type: Optional[FaultType] = None) -> int:
        """
        移除故障注入
        
        Args:
            target: 目标组件
            fault_type: 如果指定，只移除该类型的故障
        
        Returns:
            移除的故障配置数量
        """
        if target not in self._faults:
            return 0
        
        if fault_type is None:
            count = len(self._faults[target])
            del self._faults[target]
        else:
            original_count = len(self._faults[target])
            self._faults[target] = [f for f in self._faults[target] if f.fault_type != fault_type]
            count = original_count - len(self._faults[target])
        
        logger.info(f"Removed {count} fault(s) from {target}")
        return count
    
    def clear(self) -> None:
        """清除所有故障注入"""
        self._faults = {}
        logger.info("All fault injections cleared")
    
    def try_inject(self, target: str, context: Optional[Dict] = None) -> Optional[FaultConfig]:
        """
        尝试注入故障
        
        Args:
            target: 目标组件
            context: 当前上下文数据
        
        Returns:
            如果触发故障，返回 FaultConfig；否则返回 None
        """
        if not self._enabled or target not in self._faults:
            return None
        
        for config in self._faults[target]:
            if config.should_trigger():
                config.record_trigger()
                self._record_injection(config, context)
                return config
        
        return None
    
    def _record_injection(self, config: FaultConfig, context: Optional[Dict]) -> None:
        """记录故障注入历史"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "fault_type": config.fault_type.value,
            "target": config.target,
            "context": context
        }
        self._injection_history.append(record)
        if len(self._injection_history) > self._max_history:
            self._injection_history.pop(0)
    
    def apply_fault(self, config: FaultConfig, data: Any = None) -> Any:
        """
        应用故障效果
        
        Args:
            config: 故障配置
            data: 要处理的数据
        
        Returns:
            如果故障是 CORRUPTION，返回损坏后的数据
        
        Raises:
            根据故障类型抛出相应异常
        """
        fault_type = config.fault_type
        
        if fault_type == FaultType.CRASH:
            exc_type = config.exception_type or RuntimeError
            msg = config.error_message or f"Injected {fault_type.value} fault"
            logger.warning(f"💥 Injecting CRASH: {msg}")
            raise exc_type(msg)
        
        elif fault_type == FaultType.DELAY:
            duration = config.duration_ms or 1000
            logger.warning(f"⏱️  Injecting DELAY: {duration}ms")
            time.sleep(duration / 1000)
            return data
        
        elif fault_type == FaultType.TIMEOUT:
            duration = config.duration_ms or 5000
            logger.warning(f"⏰ Injecting TIMEOUT: {duration}ms")
            time.sleep(duration / 1000)
            raise TimeoutError(f"Injected timeout after {duration}ms")
        
        elif fault_type == FaultType.ERROR:
            msg = config.error_message or "Injected error result"
            logger.warning(f"❌ Injecting ERROR: {msg}")
            return {"success": False, "error": msg}
        
        elif fault_type == FaultType.CORRUPTION:
            if config.corruption_func:
                corrupted = config.corruption_func(data)
                logger.warning(f"🔧 Injecting CORRUPTION")
                return corrupted
            else:
                logger.warning(f"🔧 Injecting CORRUPTION (no func, returning None)")
                return None
        
        elif fault_type == FaultType.OMISSION:
            logger.warning(f"👻 Injecting OMISSION: skipping operation")
            return None
        
        return data
    
    def get_active_faults(self) -> Dict[str, List[Dict]]:
        """
        获取当前活动的故障配置
        
        Returns:
            {target: [fault_config_dict, ...]}
        """
        result = {}
        for target, configs in self._faults.items():
            result[target] = [
                {
                    "type": c.fault_type.value,
                    "probability": c.probability,
                    "triggered": c._triggered_count,
                    "limit": c.trigger_count
                }
                for c in configs
            ]
        return result
    
    def get_injection_history(self) -> List[Dict]:
        """获取故障注入历史"""
        return self._injection_history.copy()
    
    def clear_history(self) -> None:
        """清除历史记录"""
        self._injection_history = []
        logger.debug("Fault injection history cleared")


# 全局故障注入器实例
injector = FaultInjector()


class FaultContext:
    """
    故障注入上下文管理器
    
    用于在 with 语句中临时启用故障注入
    
    Usage:
        with FaultContext() as f:
            f.inject(FaultType.DELAY, "lock_manager.acquire", duration_ms=5000)
            # 执行测试...
    """
    
    def __init__(self):
        self.injector = FaultInjector()
        self._injected_faults: List[tuple] = []
    
    def __enter__(self):
        self.injector.enable()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.injector.disable()
        # 清除本上下文注入的所有故障
        for target, fault_type in self._injected_faults:
            self.injector.remove(target, fault_type)
    
    def inject(self, fault_type: FaultType, target: str, **kwargs) -> FaultConfig:
        """注入故障"""
        config = self.injector.inject(fault_type, target, **kwargs)
        self._injected_faults.append((target, fault_type))
        return config


def simulate_role_busy(role_id: str, duration_ms: int) -> FaultConfig:
    """
    模拟角色忙碌的便捷函数
    
    Args:
        role_id: 角色ID
        duration_ms: 忙碌时长(毫秒)
    """
    return injector.inject(
        FaultType.DELAY,
        f"worker.{role_id}.execute",
        probability=1.0,
        duration_ms=duration_ms
    )


def simulate_network_partition(target: str, duration_ms: int = 5000) -> FaultConfig:
    """
    模拟网络分区的便捷函数
    
    Args:
        target: 目标组件
        duration_ms: 超时时长
    """
    return injector.inject(
        FaultType.TIMEOUT,
        target,
        probability=1.0,
        duration_ms=duration_ms
    )
