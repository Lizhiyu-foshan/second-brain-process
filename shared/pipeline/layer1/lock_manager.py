"""
文件锁管理器
基于 fcntl 的原子锁实现（Linux/macOS）
"""
import json
import logging
import os
import fcntl
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

from shared.models import LockInfo
from shared.test_hooks import TestHooks, HookPoint
from shared.fault_injection import FaultInjector

logger = logging.getLogger(__name__)


def get_workspace_dir() -> Path:
    """获取工作目录，优先使用环境变量"""
    base = os.getenv("OPENCLAW_WORKSPACE")
    if base:
        return Path(base)
    # 默认使用当前工作目录下的 .openclaw
    return Path.cwd() / ".openclaw" / "workspace"


class LockManager:
    """
    基于 fcntl 的原子锁管理器
    
    特性:
    - 使用操作系统级文件锁（fcntl），保证原子性
    - 自动超时清理
    - 锁状态查询
    - 支持进程崩溃后的 stale lock 检测
    """
    
    def __init__(self, lock_dir: str = None, default_timeout_ms: int = 30000):
        """
        初始化锁管理器
        
        Args:
            lock_dir: 锁文件目录，默认使用环境变量或相对路径
            default_timeout_ms: 默认锁超时时间(毫秒)
        """
        if lock_dir is None:
            lock_dir = get_workspace_dir() / "shared" / "pipeline" / "locks"
        else:
            lock_dir = Path(lock_dir)
        
        self.lock_dir = lock_dir
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        self.default_timeout_ms = default_timeout_ms
        
        # 存储已获取的锁文件句柄 {role_id: file_descriptor}
        self._lock_handles: Dict[str, int] = {}
    
    def acquire(self, role_id: str, task_id: str, timeout_ms: int = None) -> bool:
        """
        获取锁（原子操作）
        
        使用 fcntl.flock 实现操作系统级互斥锁，避免 TOCTOU 竞态条件。
        
        Args:
            role_id: 角色ID
            task_id: 任务ID
            timeout_ms: 锁超时时间(毫秒)，默认30秒
            
        Returns:
            True: 获取成功
            False: 已被占用
        """
        hooks = TestHooks()
        injector = FaultInjector()
        
        # 触发 before_acquire 钩子
        hooks.trigger(HookPoint.LOCK_BEFORE_ACQUIRE, 
                     role_id=role_id, task_id=task_id, timeout_ms=timeout_ms)
        
        # 尝试故障注入
        fault_config = injector.try_inject("lock_manager.acquire", 
                                          {"role_id": role_id, "task_id": task_id})
        if fault_config:
            injector.apply_fault(fault_config)
        
        timeout_ms = timeout_ms or self.default_timeout_ms
        lock_file = self.lock_dir / f"{role_id}.lock"
        
        # 确保目录存在
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # 以读写模式打开（创建）锁文件
            fd = os.open(str(lock_file), os.O_RDWR | os.O_CREAT, 0o644)
            
            # 尝试获取非阻塞独占锁
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except (IOError, OSError):
                # 锁已被占用
                os.close(fd)
                
                # 检查是否是 stale lock（持有进程已死亡）
                if self._is_stale_lock(lock_file):
                    logger.warning(f"Detected stale lock for {role_id}, forcing release")
                    self._force_release_stale(lock_file)
                    # 重试一次
                    return self.acquire(role_id, task_id, timeout_ms)
                
                # 触发 timeout 钩子
                hooks.trigger(HookPoint.LOCK_TIMEOUT, 
                            role_id=role_id, task_id=task_id, reason="busy")
                return False
            
            # 获取锁成功，写入锁信息
            lock_data = {
                "role_id": role_id,
                "task_id": task_id,
                "acquired_at": datetime.now().isoformat(),
                "timeout_ms": timeout_ms,
                "pid": os.getpid()  # 记录 PID 用于 stale lock 检测
            }
            
            # 清空文件并写入新数据
            os.ftruncate(fd, 0)
            os.lseek(fd, 0, os.SEEK_SET)
            os.write(fd, json.dumps(lock_data).encode('utf-8'))
            os.fsync(fd)  # 确保数据落盘
            
            # 保存文件句柄
            self._lock_handles[role_id] = fd
            
            # 触发 after_acquire 钩子
            hooks.trigger(HookPoint.LOCK_AFTER_ACQUIRE, 
                         role_id=role_id, task_id=task_id, success=True)
            
            logger.info(f"Lock acquired: {role_id} for task {task_id} (pid: {os.getpid()})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to acquire lock for {role_id}: {e}")
            # 触发 after_acquire 钩子（失败）
            hooks.trigger(HookPoint.LOCK_AFTER_ACQUIRE, 
                         role_id=role_id, task_id=task_id, success=False, error=str(e))
            return False
    
    def release(self, role_id: str) -> bool:
        """
        释放锁
        
        Args:
            role_id: 角色ID
            
        Returns:
            True: 释放成功或锁不存在
        """
        hooks = TestHooks()
        injector = FaultInjector()
        
        # 触发 before_release 钩子
        hooks.trigger(HookPoint.LOCK_BEFORE_RELEASE, role_id=role_id)
        
        # 尝试故障注入
        fault_config = injector.try_inject("lock_manager.release", {"role_id": role_id})
        if fault_config:
            injector.apply_fault(fault_config)
        
        fd = self._lock_handles.pop(role_id, None)
        
        success = False
        
        if fd is None:
            # 可能是其他进程持有的锁，尝试查找并释放
            lock_file = self.lock_dir / f"{role_id}.lock"
            if not lock_file.exists():
                success = True
            else:
                try:
                    fd = os.open(str(lock_file), os.O_RDWR)
                    fcntl.flock(fd, fcntl.LOCK_UN)
                    os.close(fd)
                    lock_file.unlink()
                    logger.info(f"Lock released (external): {role_id}")
                    success = True
                except Exception as e:
                    logger.error(f"Failed to release external lock for {role_id}: {e}")
                    success = False
        else:
            try:
                # 释放文件锁
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)
                
                # 删除锁文件
                lock_file = self.lock_dir / f"{role_id}.lock"
                if lock_file.exists():
                    lock_file.unlink()
                
                logger.info(f"Lock released: {role_id}")
                success = True
                
            except Exception as e:
                logger.error(f"Failed to release lock for {role_id}: {e}")
                success = False
        
        # 触发 after_release 钩子
        hooks.trigger(HookPoint.LOCK_AFTER_RELEASE, role_id=role_id, success=success)
        
        return success
    
    def _is_stale_lock(self, lock_file: Path) -> bool:
        """
        检查是否是 stale lock（持有进程已死亡）
        
        Args:
            lock_file: 锁文件路径
            
        Returns:
            True: 是 stale lock
        """
        try:
            with open(lock_file, 'r') as f:
                lock_data = json.load(f)
            
            # 检查 PID 是否存在
            pid = lock_data.get("pid")
            if pid:
                try:
                    os.kill(pid, 0)  # 信号 0 用于检测进程是否存在
                    return False  # 进程存在，不是 stale
                except (OSError, ProcessLookupError):
                    return True  # 进程不存在，是 stale
            
            # 没有 PID 信息，检查超时
            locked_at = datetime.fromisoformat(lock_data["acquired_at"])
            timeout_ms = lock_data.get("timeout_ms", self.default_timeout_ms)
            
            if datetime.now() - locked_at > timedelta(milliseconds=timeout_ms):
                return True
                
        except Exception as e:
            logger.warning(f"Error checking stale lock: {e}")
        
        return False
    
    def _force_release_stale(self, lock_file: Path):
        """强制释放 stale lock"""
        try:
            # 打开文件获取句柄
            fd = os.open(str(lock_file), os.O_RDWR)
            # 尝试获取锁（阻塞）
            fcntl.flock(fd, fcntl.LOCK_EX)
            # 释放并删除
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
            lock_file.unlink()
            logger.info(f"Force released stale lock: {lock_file.name}")
        except Exception as e:
            logger.error(f"Failed to force release stale lock: {e}")
    
    def get_lock_info(self, role_id: str) -> Optional[LockInfo]:
        """获取锁信息"""
        lock_file = self.lock_dir / f"{role_id}.lock"
        
        if not lock_file.exists():
            return None
        
        try:
            with open(lock_file, 'r') as f:
                # 使用共享锁读取，不阻塞其他进程
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    lock_data = json.load(f)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            return LockInfo.from_dict(lock_data)
        except Exception as e:
            logger.error(f"Failed to read lock info for {role_id}: {e}")
            return None
    
    def is_locked(self, role_id: str) -> bool:
        """检查角色是否被锁定"""
        # 首先检查当前进程是否持有锁
        if role_id in self._lock_handles:
            return True
        
        # 检查文件锁
        lock_file = self.lock_dir / f"{role_id}.lock"
        if not lock_file.exists():
            return False
        
        try:
            # 尝试获取非阻塞锁
            fd = os.open(str(lock_file), os.O_RDWR)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                # 获取成功，说明没有其他进程持有锁
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)
                return False
            except (IOError, OSError):
                # 锁被占用
                os.close(fd)
                return True
        except Exception:
            return False
    
    def get_all_locks(self) -> Dict[str, LockInfo]:
        """获取所有锁信息"""
        locks = {}
        for lock_file in self.lock_dir.glob("*.lock"):
            role_id = lock_file.stem
            lock_info = self.get_lock_info(role_id)
            if lock_info:
                locks[role_id] = lock_info
        return locks
    
    def cleanup_expired(self) -> int:
        """清理所有过期锁"""
        cleaned = 0
        
        for lock_file in self.lock_dir.glob("*.lock"):
            try:
                if self._is_stale_lock(lock_file):
                    self._force_release_stale(lock_file)
                    cleaned += 1
            except Exception as e:
                logger.warning(f"Error cleaning lock {lock_file.name}: {e}")
        
        return cleaned
    
    def force_release_all(self) -> int:
        """强制释放所有锁"""
        released = 0
        
        # 先释放当前进程持有的锁
        for role_id in list(self._lock_handles.keys()):
            if self.release(role_id):
                released += 1
        
        # 再尝试释放其他锁
        for lock_file in self.lock_dir.glob("*.lock"):
            try:
                self._force_release_stale(lock_file)
                released += 1
            except:
                pass
        
        return released
    
    def __del__(self):
        """析构时释放所有持有的锁"""
        for role_id in list(self._lock_handles.keys()):
            try:
                self.release(role_id)
            except:
                pass
