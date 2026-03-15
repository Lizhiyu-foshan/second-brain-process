#!/usr/bin/env python3
"""
调度器守护进程
系统监控、告警、任务调度管理
"""
import sys
import os
import time
import json
import signal
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from layer1.task_queue import TaskQueue
from layer1.lock_manager import LockManager
from layer1.role_registry import RoleRegistry
from layer2.orchestrator import Orchestrator, ProjectStatus

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """告警记录"""
    id: str
    timestamp: str
    level: AlertLevel
    component: str
    message: str
    details: Optional[Dict] = None
    acknowledged: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "level": self.level.value,
            "component": self.component,
            "message": self.message,
            "details": self.details,
            "acknowledged": self.acknowledged
        }


@dataclass
class HealthStatus:
    """健康状态"""
    timestamp: str
    overall: str  # healthy, degraded, unhealthy
    components: Dict[str, str]
    metrics: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "overall": self.overall,
            "components": self.components,
            "metrics": self.metrics
        }


class AlertManager:
    """告警管理器"""
    
    def __init__(self, max_alerts: int = 1000):
        self.alerts: List[Alert] = []
        self.max_alerts = max_alerts
        self._handlers: Dict[AlertLevel, List[Callable]] = {
            level: [] for level in AlertLevel
        }
        self._lock = threading.Lock()
    
    def add_alert(self, level: AlertLevel, component: str, 
                  message: str, details: Optional[Dict] = None) -> Alert:
        """添加告警"""
        alert = Alert(
            id=f"ALT_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.alerts)}",
            timestamp=datetime.now().isoformat(),
            level=level,
            component=component,
            message=message,
            details=details
        )
        
        with self._lock:
            self.alerts.append(alert)
            # 限制历史记录数量
            if len(self.alerts) > self.max_alerts:
                self.alerts.pop(0)
        
        # 触发处理程序
        self._trigger_handlers(alert)
        
        # 记录日志
        log_msg = f"[{level.value.upper()}] {component}: {message}"
        if level == AlertLevel.CRITICAL:
            logger.critical(log_msg)
        elif level == AlertLevel.ERROR:
            logger.error(log_msg)
        elif level == AlertLevel.WARNING:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
        
        return alert
    
    def acknowledge(self, alert_id: str) -> bool:
        """确认告警"""
        with self._lock:
            for alert in self.alerts:
                if alert.id == alert_id:
                    alert.acknowledged = True
                    logger.info(f"Alert acknowledged: {alert_id}")
                    return True
        return False
    
    def get_alerts(self, level: Optional[AlertLevel] = None, 
                   unacknowledged_only: bool = False) -> List[Alert]:
        """获取告警列表"""
        with self._lock:
            alerts = self.alerts
            if level:
                alerts = [a for a in alerts if a.level == level]
            if unacknowledged_only:
                alerts = [a for a in alerts if not a.acknowledged]
            return alerts.copy()
    
    def register_handler(self, level: AlertLevel, handler: Callable) -> None:
        """注册告警处理程序"""
        self._handlers[level].append(handler)
    
    def _trigger_handlers(self, alert: Alert) -> None:
        """触发告警处理程序"""
        for handler in self._handlers.get(alert.level, []):
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")
    
    def clear_alerts(self) -> None:
        """清除所有告警"""
        with self._lock:
            self.alerts = []
        logger.info("All alerts cleared")


class HealthChecker:
    """健康检查器"""
    
    def __init__(self, alert_manager: AlertManager):
        self.alert_manager = alert_manager
        self._last_check: Optional[datetime] = None
        self._check_results: List[HealthStatus] = []
        self._max_results = 100
    
    def check_all(self) -> HealthStatus:
        """执行所有健康检查"""
        timestamp = datetime.now().isoformat()
        components = {}
        metrics = {}
        
        # 检查任务队列
        try:
            task_queue = TaskQueue()
            pending_count = len([t for t in task_queue.tasks.values() if t.status == "pending"])
            processing_count = len([t for t in task_queue.tasks.values() if t.status == "processing"])
            failed_count = len([t for t in task_queue.tasks.values() if t.status == "failed"])
            
            metrics["tasks_pending"] = pending_count
            metrics["tasks_processing"] = processing_count
            metrics["tasks_failed"] = failed_count
            metrics["tasks_total"] = len(task_queue.tasks)
            
            # 如果有大量失败任务，触发告警
            if failed_count > 10:
                components["task_queue"] = "degraded"
                self.alert_manager.add_alert(
                    AlertLevel.WARNING,
                    "task_queue",
                    f"High number of failed tasks: {failed_count}",
                    {"failed_count": failed_count}
                )
            else:
                components["task_queue"] = "healthy"
                
        except Exception as e:
            components["task_queue"] = "unhealthy"
            self.alert_manager.add_alert(
                AlertLevel.ERROR,
                "task_queue",
                f"Health check failed: {e}"
            )
        
        # 检查锁状态
        try:
            lock_mgr = LockManager()
            locks = lock_mgr.get_all_locks()
            metrics["active_locks"] = len(locks)
            
            # 检查是否有长时间持有的锁
            stale_locks = 0
            for role_id, lock_info in locks.items():
                if hasattr(lock_info, 'acquired_at') and lock_info.acquired_at:
                    try:
                        acquired_time = datetime.fromisoformat(lock_info.acquired_at)
                        if datetime.now() - acquired_time > timedelta(minutes=10):
                            stale_locks += 1
                    except:
                        pass
            
            metrics["stale_locks"] = stale_locks
            
            if stale_locks > 0:
                components["lock_manager"] = "degraded"
                self.alert_manager.add_alert(
                    AlertLevel.WARNING,
                    "lock_manager",
                    f"Detected {stale_locks} stale locks",
                    {"stale_locks": stale_locks}
                )
            else:
                components["lock_manager"] = "healthy"
                
        except Exception as e:
            components["lock_manager"] = "unhealthy"
            self.alert_manager.add_alert(
                AlertLevel.ERROR,
                "lock_manager",
                f"Health check failed: {e}"
            )
        
        # 检查编排器
        try:
            orch = Orchestrator()
            running_projects = len([p for p in orch.projects.values() 
                                   if p.status == ProjectStatus.RUNNING])
            completed_projects = len([p for p in orch.projects.values() 
                                     if p.status == ProjectStatus.COMPLETED])
            
            metrics["projects_running"] = running_projects
            metrics["projects_completed"] = completed_projects
            metrics["projects_total"] = len(orch.projects)
            
            components["orchestrator"] = "healthy"
            
        except Exception as e:
            components["orchestrator"] = "unhealthy"
            self.alert_manager.add_alert(
                AlertLevel.ERROR,
                "orchestrator",
                f"Health check failed: {e}"
            )
        
        # 确定总体状态
        if any(s == "unhealthy" for s in components.values()):
            overall = "unhealthy"
        elif any(s == "degraded" for s in components.values()):
            overall = "degraded"
        else:
            overall = "healthy"
        
        status = HealthStatus(
            timestamp=timestamp,
            overall=overall,
            components=components,
            metrics=metrics
        )
        
        # 保存结果
        self._check_results.append(status)
        if len(self._check_results) > self._max_results:
            self._check_results.pop(0)
        
        self._last_check = datetime.now()
        
        return status
    
    def get_latest(self) -> Optional[HealthStatus]:
        """获取最新的健康状态"""
        if self._check_results:
            return self._check_results[-1]
        return None
    
    def get_history(self, count: int = 10) -> List[HealthStatus]:
        """获取健康检查历史"""
        return self._check_results[-count:]


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, alert_manager: AlertManager):
        self.alert_manager = alert_manager
        self._scheduled_tasks: Dict[str, Dict] = {}
        self._lock = threading.Lock()
    
    def schedule_task(self, task_id: str, execute_at: datetime, 
                      callback: Callable, **kwargs) -> bool:
        """
        调度任务在指定时间执行
        
        Args:
            task_id: 任务ID
            execute_at: 执行时间
            callback: 回调函数
            **kwargs: 传递给回调的参数
        
        Returns:
            是否成功调度
        """
        with self._lock:
            if task_id in self._scheduled_tasks:
                logger.warning(f"Task {task_id} already scheduled")
                return False
            
            self._scheduled_tasks[task_id] = {
                "task_id": task_id,
                "execute_at": execute_at,
                "callback": callback,
                "kwargs": kwargs,
                "scheduled_at": datetime.now().isoformat()
            }
        
        logger.info(f"Task scheduled: {task_id} at {execute_at.isoformat()}")
        return True
    
    def cancel_task(self, task_id: str) -> bool:
        """取消调度的任务"""
        with self._lock:
            if task_id not in self._scheduled_tasks:
                return False
            del self._scheduled_tasks[task_id]
        
        logger.info(f"Task cancelled: {task_id}")
        return True
    
    def check_and_execute(self) -> List[str]:
        """
        检查并执行到期的任务
        
        Returns:
            执行的任务ID列表
        """
        now = datetime.now()
        executed = []
        
        with self._lock:
            tasks_to_execute = []
            for task_id, task_info in list(self._scheduled_tasks.items()):
                if task_info["execute_at"] <= now:
                    tasks_to_execute.append((task_id, task_info))
            
            for task_id, task_info in tasks_to_execute:
                try:
                    callback = task_info["callback"]
                    kwargs = task_info["kwargs"]
                    callback(**kwargs)
                    executed.append(task_id)
                    del self._scheduled_tasks[task_id]
                    logger.info(f"Scheduled task executed: {task_id}")
                except Exception as e:
                    logger.error(f"Failed to execute scheduled task {task_id}: {e}")
                    self.alert_manager.add_alert(
                        AlertLevel.ERROR,
                        "scheduler",
                        f"Failed to execute scheduled task {task_id}",
                        {"error": str(e)}
                    )
        
        return executed
    
    def get_scheduled_tasks(self) -> List[Dict]:
        """获取所有调度的任务"""
        with self._lock:
            return [
                {
                    "task_id": t["task_id"],
                    "execute_at": t["execute_at"].isoformat(),
                    "scheduled_at": t["scheduled_at"]
                }
                for t in self._scheduled_tasks.values()
            ]


class SchedulerDaemon:
    """
    调度器守护进程
    
    负责：
    - 系统健康监控
    - 告警管理
    - 定时任务调度
    - 状态报告
    """
    
    def __init__(self, state_dir: str = None, check_interval: int = 60):
        """
        初始化守护进程
        
        Args:
            state_dir: 状态文件目录
            check_interval: 健康检查间隔（秒）
        """
        base_dir = Path(__file__).parent
        self.state_dir = Path(state_dir) if state_dir else base_dir / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        self.check_interval = check_interval
        self.running = False
        
        # 子组件
        self.alert_manager = AlertManager()
        self.health_checker = HealthChecker(self.alert_manager)
        self.task_scheduler = TaskScheduler(self.alert_manager)
        
        # 统计
        self._stats = {
            "health_checks": 0,
            "alerts_triggered": 0,
            "scheduled_tasks_executed": 0,
            "started_at": None
        }
        
        # 信号处理
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def start(self) -> None:
        """启动守护进程"""
        logger.info("=" * 80)
        logger.info("Scheduler Daemon Starting")
        logger.info("=" * 80)
        
        self.running = True
        self._stats["started_at"] = datetime.now().isoformat()
        
        # 初始健康检查
        self._run_health_check()
        
        logger.info(f"Health check interval: {self.check_interval}s")
        logger.info("Press Ctrl+C to stop")
        
        try:
            while self.running:
                time.sleep(1)
                
                # 执行调度的任务
                executed = self.task_scheduler.check_and_execute()
                self._stats["scheduled_tasks_executed"] += len(executed)
                
                # 定期健康检查
                if self._stats["health_checks"] == 0 or \
                   (datetime.now() - datetime.fromisoformat(
                       self.health_checker.get_latest().timestamp)).total_seconds() >= self.check_interval:
                    self._run_health_check()
                    
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            self.stop()
    
    def stop(self) -> None:
        """停止守护进程"""
        if not self.running:
            return
        
        self.running = False
        logger.info("Scheduler Daemon stopped")
        
        # 保存最终状态
        self._save_state()
    
    def _run_health_check(self) -> None:
        """执行健康检查"""
        try:
            status = self.health_checker.check_all()
            self._stats["health_checks"] += 1
            
            # 记录状态
            if status.overall != "healthy":
                logger.warning(f"Health status: {status.overall}")
                for comp, state in status.components.items():
                    if state != "healthy":
                        logger.warning(f"  [{comp}] {state}")
            else:
                logger.info(f"Health check #{self._stats['health_checks']}: healthy")
                logger.debug(f"  Metrics: {status.metrics}")
            
            # 保存状态
            self._save_state()
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
    
    def _save_state(self) -> None:
        """保存守护进程状态"""
        try:
            state_file = self.state_dir / "scheduler_state.json"
            state = {
                "timestamp": datetime.now().isoformat(),
                "stats": self._stats,
                "health_status": self.health_checker.get_latest().to_dict() if self.health_checker.get_latest() else None,
                "alerts_count": len(self.alert_manager.alerts),
                "scheduled_tasks_count": len(self.task_scheduler.get_scheduled_tasks())
            }
            
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def get_status(self) -> Dict:
        """获取守护进程状态"""
        latest_health = self.health_checker.get_latest()
        
        return {
            "running": self.running,
            "started_at": self._stats["started_at"],
            "stats": self._stats,
            "health": latest_health.to_dict() if latest_health else None,
            "alerts": {
                "total": len(self.alert_manager.alerts),
                "unacknowledged": len(self.alert_manager.get_alerts(unacknowledged_only=True))
            },
            "scheduled_tasks": len(self.task_scheduler.get_scheduled_tasks())
        }
    
    def schedule_maintenance(self, maintenance_time: Optional[datetime] = None) -> str:
        """
        调度系统维护
        
        Args:
            maintenance_time: 维护时间，默认为明天凌晨2点
            
        Returns:
            维护任务ID
        """
        if maintenance_time is None:
            # 默认明天凌晨2点
            tomorrow = datetime.now() + timedelta(days=1)
            maintenance_time = tomorrow.replace(hour=2, minute=0, second=0, microsecond=0)
        
        task_id = f"MAINT_{maintenance_time.strftime('%Y%m%d_%H%M%S')}"
        
        def maintenance_callback():
            logger.info("🔧 Scheduled maintenance starting...")
            # 清理过期锁
            try:
                lock_mgr = LockManager()
                cleaned = lock_mgr.cleanup_expired()
                if cleaned > 0:
                    logger.info(f"Cleaned {cleaned} expired locks")
            except Exception as e:
                logger.error(f"Maintenance error (lock cleanup): {e}")
            
            logger.info("🔧 Maintenance completed")
        
        self.task_scheduler.schedule_task(task_id, maintenance_time, maintenance_callback)
        
        self.alert_manager.add_alert(
            AlertLevel.INFO,
            "scheduler",
            f"Maintenance scheduled for {maintenance_time.isoformat()}",
            {"task_id": task_id}
        )
        
        return task_id


def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Scheduler Daemon')
    parser.add_argument('--state-dir', help='State file directory')
    parser.add_argument('--check-interval', type=int, default=60, 
                       help='Health check interval in seconds (default: 60)')
    parser.add_argument('--maintenance', action='store_true',
                       help='Schedule immediate maintenance')
    
    args = parser.parse_args()
    
    daemon = SchedulerDaemon(
        state_dir=args.state_dir,
        check_interval=args.check_interval
    )
    
    if args.maintenance:
        task_id = daemon.schedule_maintenance(datetime.now() + timedelta(minutes=1))
        print(f"Maintenance scheduled: {task_id}")
        return
    
    daemon.start()


if __name__ == "__main__":
    main()
