"""
时间控制API
支持测试场景下的时间操控和状态管理
"""
import time
import json
import shutil
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Callable
from pathlib import Path
from dataclasses import dataclass, asdict
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class TimeState:
    """时间状态"""
    frozen: bool = False
    frozen_at: Optional[datetime] = None
    acceleration_factor: float = 1.0
    base_time: Optional[datetime] = None
    simulated_time: Optional[datetime] = None


@dataclass
class SystemSnapshot:
    """系统状态快照"""
    timestamp: str
    time_state: Dict
    task_queue: Dict
    locks: Dict
    projects: Dict
    workers: Dict
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "time_state": self.time_state,
            "task_queue": self.task_queue,
            "locks": self.locks,
            "projects": self.projects,
            "workers": self.workers
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "SystemSnapshot":
        return cls(
            timestamp=data.get("timestamp", ""),
            time_state=data.get("time_state", {}),
            task_queue=data.get("task_queue", {}),
            locks=data.get("locks", {}),
            projects=data.get("projects", {}),
            workers=data.get("workers", {})
        )


class TimeController:
    """
    时间控制器
    
    单例模式，全局管理时间状态
    用于测试场景下的时间操控
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
        self._state = TimeState()
        self._callbacks: Dict[str, Callable] = {}
        self._role_busy_until: Dict[str, datetime] = {}
        
    def freeze_time(self, timestamp: Optional[datetime] = None) -> None:
        """
        冻结时间
        
        Args:
            timestamp: 冻结到指定时间点，默认为当前时间
        """
        self._state.frozen = True
        self._state.frozen_at = timestamp or datetime.now()
        self._state.base_time = datetime.now()
        self._state.simulated_time = self._state.frozen_at
        
        logger.info(f"⏸️  Time frozen at: {self._state.frozen_at.isoformat()}")
        
        # 触发回调
        self._trigger_callback("freeze", self._state.frozen_at)
    
    def unfreeze_time(self) -> None:
        """解冻时间"""
        if not self._state.frozen:
            return
        
        self._state.frozen = False
        self._state.frozen_at = None
        self._state.simulated_time = None
        
        logger.info("▶️  Time unfrozen")
        
        # 触发回调
        self._trigger_callback("unfreeze", datetime.now())
    
    def accelerate_time(self, factor: float) -> None:
        """
        加速时间
        
        Args:
            factor: 加速倍数，2.0 表示时间流逝速度是正常2倍
        """
        if factor < 0:
            raise ValueError("Acceleration factor must be positive")
        
        old_factor = self._state.acceleration_factor
        self._state.acceleration_factor = factor
        self._state.base_time = datetime.now()
        
        logger.info(f"⏩ Time acceleration: {old_factor}x → {factor}x")
        
        # 触发回调
        self._trigger_callback("accelerate", factor)
    
    def get_current_time(self) -> datetime:
        """
        获取当前时间（考虑冻结和加速）
        
        Returns:
            当前时间
        """
        if self._state.frozen:
            return self._state.frozen_at
        
        if self._state.acceleration_factor != 1.0 and self._state.base_time:
            elapsed = (datetime.now() - self._state.base_time).total_seconds()
            accelerated_elapsed = elapsed * self._state.acceleration_factor
            return self._state.base_time + timedelta(seconds=accelerated_elapsed)
        
        return datetime.now()
    
    def advance_time(self, seconds: float) -> None:
        """
        推进时间（仅在冻结状态下有效）
        
        Args:
            seconds: 推进的秒数
        """
        if not self._state.frozen:
            logger.warning("Cannot advance time when not frozen. Use accelerate_time() instead.")
            return
        
        self._state.simulated_time = self._state.frozen_at + timedelta(seconds=seconds)
        self._state.frozen_at = self._state.simulated_time
        
        logger.info(f"⏩ Time advanced: +{seconds}s → {self._state.frozen_at.isoformat()}")
        
        # 触发回调
        self._trigger_callback("advance", seconds)
    
    def is_frozen(self) -> bool:
        """检查时间是否冻结"""
        return self._state.frozen
    
    def get_acceleration_factor(self) -> float:
        """获取时间加速倍数"""
        return self._state.acceleration_factor
    
    def simulate_role_busy(self, role_id: str, duration_seconds: int) -> None:
        """
        模拟角色忙碌
        
        Args:
            role_id: 角色ID
            duration_seconds: 忙碌时长（秒）
        """
        busy_until = self.get_current_time() + timedelta(seconds=duration_seconds)
        self._role_busy_until[role_id] = busy_until
        
        logger.info(f"🎭 Role {role_id} simulated busy for {duration_seconds}s (until {busy_until.isoformat()})")
        
        # 触发回调
        self._trigger_callback("role_busy", {"role_id": role_id, "until": busy_until.isoformat()})
    
    def is_role_busy(self, role_id: str) -> bool:
        """检查角色是否处于模拟忙碌状态"""
        if role_id not in self._role_busy_until:
            return False
        
        busy_until = self._role_busy_until[role_id]
        return self.get_current_time() < busy_until
    
    def clear_role_busy(self, role_id: str) -> None:
        """清除角色的忙碌状态"""
        if role_id in self._role_busy_until:
            del self._role_busy_until[role_id]
            logger.info(f"🎭 Role {role_id} busy state cleared")
    
    def register_callback(self, event: str, callback: Callable) -> None:
        """
        注册时间事件回调
        
        Args:
            event: 事件类型 (freeze/unfreeze/accelerate/advance/role_busy)
            callback: 回调函数
        """
        self._callbacks[event] = callback
    
    def unregister_callback(self, event: str) -> None:
        """注销时间事件回调"""
        if event in self._callbacks:
            del self._callbacks[event]
    
    def _trigger_callback(self, event: str, data: Any) -> None:
        """触发回调"""
        if event in self._callbacks:
            try:
                self._callbacks[event](data)
            except Exception as e:
                logger.error(f"Time callback error for {event}: {e}")
    
    def reset(self) -> None:
        """重置时间控制器到初始状态"""
        self._state = TimeState()
        self._role_busy_until = {}
        logger.info("🔄 Time controller reset")
    
    def get_state(self) -> Dict:
        """获取时间状态"""
        return {
            "frozen": self._state.frozen,
            "frozen_at": self._state.frozen_at.isoformat() if self._state.frozen_at else None,
            "acceleration_factor": self._state.acceleration_factor,
            "role_busy_states": {
                role_id: until.isoformat()
                for role_id, until in self._role_busy_until.items()
            }
        }


# 全局时间控制器实例
time_controller = TimeController()


# 便捷函数
def freeze_time(timestamp: Optional[datetime] = None) -> None:
    """冻结时间"""
    time_controller.freeze_time(timestamp)


def unfreeze_time() -> None:
    """解冻时间"""
    time_controller.unfreeze_time()


def accelerate_time(factor: float) -> None:
    """加速时间"""
    time_controller.accelerate_time(factor)


def advance_time(seconds: float) -> None:
    """推进时间"""
    time_controller.advance_time(seconds)


def get_current_time() -> datetime:
    """获取当前时间"""
    return time_controller.get_current_time()


def simulate_role_busy(role_id: str, duration_seconds: int) -> None:
    """模拟角色忙碌"""
    time_controller.simulate_role_busy(role_id, duration_seconds)


def is_role_busy(role_id: str) -> bool:
    """检查角色是否忙碌"""
    return time_controller.is_role_busy(role_id)


class StateManager:
    """
    状态管理器
    
    负责系统状态的快照和恢复
    """
    
    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = Path(__file__).parent.parent / "snapshots"
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def get_state_snapshot(self) -> SystemSnapshot:
        """
        获取系统状态快照
        
        Returns:
            SystemSnapshot 对象
        """
        from layer1.task_queue import TaskQueue
        from layer1.lock_manager import LockManager
        from layer2.orchestrator import Orchestrator
        
        timestamp = datetime.now().isoformat()
        
        # 获取时间状态
        time_state = time_controller.get_state()
        
        # 获取任务队列状态
        try:
            task_queue = TaskQueue()
            tasks = {
                task_id: {
                    "status": task.status,
                    "role_id": task.role_id,
                    "priority": task.priority
                }
                for task_id, task in task_queue.tasks.items()
            }
        except Exception as e:
            logger.warning(f"Failed to get task queue state: {e}")
            tasks = {}
        
        # 获取锁状态
        try:
            lock_mgr = LockManager()
            locks = {
                role_id: lock_info.to_dict() if hasattr(lock_info, 'to_dict') else str(lock_info)
                for role_id, lock_info in lock_mgr.get_all_locks().items()
            }
        except Exception as e:
            logger.warning(f"Failed to get lock state: {e}")
            locks = {}
        
        # 获取项目状态
        try:
            orch = Orchestrator()
            projects = {
                proj_id: {
                    "status": proj.status.value if hasattr(proj.status, 'value') else str(proj.status),
                    "task_count": len(proj.tasks)
                }
                for proj_id, proj in orch.projects.items()
            }
        except Exception as e:
            logger.warning(f"Failed to get project state: {e}")
            projects = {}
        
        # 获取工作器状态（简化）
        workers = {
            "architect": {"state": "unknown"},
            "developer": {"state": "unknown"},
            "tester": {"state": "unknown"}
        }
        
        snapshot = SystemSnapshot(
            timestamp=timestamp,
            time_state=time_state,
            task_queue=tasks,
            locks=locks,
            projects=projects,
            workers=workers
        )
        
        logger.info(f"📸 State snapshot created at {timestamp}")
        return snapshot
    
    def save_snapshot(self, name: Optional[str] = None) -> Path:
        """
        保存快照到文件
        
        Args:
            name: 快照名称，默认为时间戳
            
        Returns:
            保存的文件路径
        """
        snapshot = self.get_state_snapshot()
        
        if name is None:
            name = f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        file_path = self.base_dir / f"{name}.json"
        
        with open(file_path, 'w') as f:
            json.dump(snapshot.to_dict(), f, indent=2)
        
        logger.info(f"💾 Snapshot saved: {file_path}")
        return file_path
    
    def restore_state(self, snapshot: SystemSnapshot) -> bool:
        """
        恢复到指定状态
        
        Args:
            snapshot: 状态快照
            
        Returns:
            是否成功
        """
        logger.info(f"🔄 Restoring state from {snapshot.timestamp}")
        
        try:
            # 恢复时间状态
            time_state = snapshot.time_state
            if time_state.get("frozen"):
                frozen_at = datetime.fromisoformat(time_state["frozen_at"])
                time_controller.freeze_time(frozen_at)
            
            if time_state.get("acceleration_factor", 1.0) != 1.0:
                time_controller.accelerate_time(time_state["acceleration_factor"])
            
            # 恢复角色忙碌状态
            for role_id, until_str in time_state.get("role_busy_states", {}).items():
                until = datetime.fromisoformat(until_str)
                now = datetime.now()
                if until > now:
                    duration = int((until - now).total_seconds())
                    time_controller.simulate_role_busy(role_id, duration)
            
            logger.info("✅ State restored successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to restore state: {e}")
            return False
    
    def load_snapshot(self, name: str) -> Optional[SystemSnapshot]:
        """
        从文件加载快照
        
        Args:
            name: 快照名称
            
        Returns:
            SystemSnapshot 对象，不存在返回 None
        """
        file_path = self.base_dir / f"{name}.json"
        
        if not file_path.exists():
            logger.warning(f"Snapshot not found: {file_path}")
            return None
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        snapshot = SystemSnapshot.from_dict(data)
        logger.info(f"📂 Snapshot loaded: {name}")
        return snapshot
    
    def list_snapshots(self) -> list:
        """列出所有可用的快照"""
        snapshots = []
        for file_path in self.base_dir.glob("*.json"):
            stat = file_path.stat()
            snapshots.append({
                "name": file_path.stem,
                "file": str(file_path),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        return sorted(snapshots, key=lambda x: x["modified"], reverse=True)
    
    def delete_snapshot(self, name: str) -> bool:
        """删除快照"""
        file_path = self.base_dir / f"{name}.json"
        
        if not file_path.exists():
            return False
        
        file_path.unlink()
        logger.info(f"🗑️  Snapshot deleted: {name}")
        return True


# 便捷函数
def get_state_snapshot() -> SystemSnapshot:
    """获取系统状态快照"""
    manager = StateManager()
    return manager.get_state_snapshot()


def restore_state(snapshot: SystemSnapshot) -> bool:
    """恢复到指定状态"""
    manager = StateManager()
    return manager.restore_state(snapshot)


@contextmanager
def frozen_time(timestamp: Optional[datetime] = None):
    """
    时间冻结上下文管理器
    
    Usage:
        with frozen_time():
            # 时间被冻结
            pass
        # 时间恢复
    """
    freeze_time(timestamp)
    try:
        yield time_controller
    finally:
        unfreeze_time()


@contextmanager
def accelerated_time(factor: float):
    """
    时间加速上下文管理器
    
    Usage:
        with accelerated_time(10.0):
            # 时间流逝速度是正常10倍
            time.sleep(1)  # 实际只过了0.1秒
    """
    accelerate_time(factor)
    try:
        yield time_controller
    finally:
        accelerate_time(1.0)
