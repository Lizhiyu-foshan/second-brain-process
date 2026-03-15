#!/usr/bin/env python3
"""
时间控制API和调度器守护进程测试
"""
import sys
import os
import time
import json
import threading
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.time_control import (
    TimeController, StateManager,
    freeze_time, unfreeze_time, accelerate_time, advance_time,
    get_current_time, simulate_role_busy, is_role_busy,
    frozen_time, accelerated_time, get_state_snapshot
)
from scheduler_daemon import (
    SchedulerDaemon, AlertManager, HealthChecker, TaskScheduler,
    Alert, AlertLevel, HealthStatus
)


def test_time_controller_freeze():
    """测试时间冻结"""
    print("\n=== Test 1: Time Freeze ===")
    
    controller = TimeController()
    controller.reset()
    
    # 冻结时间
    freeze_at = datetime(2026, 3, 15, 12, 0, 0)
    controller.freeze_time(freeze_at)
    
    assert controller.is_frozen(), "Time should be frozen"
    assert controller.get_current_time() == freeze_at, "Current time should be frozen time"
    
    # 等待一下，时间应该不变
    time.sleep(0.1)
    assert controller.get_current_time() == freeze_at, "Time should not advance"
    
    # 解冻
    controller.unfreeze_time()
    assert not controller.is_frozen(), "Time should be unfrozen"
    
    print("  ✅ Time freeze test passed")
    return True


def test_time_controller_advance():
    """测试时间推进"""
    print("\n=== Test 2: Time Advance ===")
    
    controller = TimeController()
    controller.reset()
    
    # 冻结时间
    freeze_at = datetime(2026, 3, 15, 12, 0, 0)
    controller.freeze_time(freeze_at)
    
    # 推进时间
    controller.advance_time(3600)  # 推进1小时
    
    expected = freeze_at + timedelta(seconds=3600)
    assert controller.get_current_time() == expected, f"Time should be {expected}"
    
    # 再推进
    controller.advance_time(1800)  # 再推进30分钟
    expected = expected + timedelta(seconds=1800)
    assert controller.get_current_time() == expected
    
    controller.unfreeze_time()
    print("  ✅ Time advance test passed")
    return True


def test_time_controller_accelerate():
    """测试时间加速"""
    print("\n=== Test 3: Time Acceleration ===")
    
    controller = TimeController()
    controller.reset()
    
    # 加速10倍
    controller.accelerate_time(10.0)
    
    start = datetime.now()
    time.sleep(0.1)  # 实际等待0.1秒
    elapsed = (datetime.now() - start).total_seconds()
    
    # 由于加速，elapsed应该约等于0.1秒
    assert elapsed >= 0.09, f"Expected ~0.1s, got {elapsed}s"
    
    # 恢复
    controller.accelerate_time(1.0)
    
    print(f"  ✅ Time acceleration test passed (elapsed: {elapsed:.3f}s)")
    return True


def test_simulate_role_busy():
    """测试角色忙碌模拟"""
    print("\n=== Test 4: Role Busy Simulation ===")
    
    controller = TimeController()
    controller.reset()
    
    # 模拟角色忙碌3秒
    simulate_role_busy("developer", 3)
    
    assert is_role_busy("developer"), "Developer should be busy"
    assert not is_role_busy("architect"), "Architect should not be busy"
    
    # 等待3秒
    time.sleep(3.1)
    
    assert not is_role_busy("developer"), "Developer should not be busy after duration"
    
    print("  ✅ Role busy simulation test passed")
    return True


def test_frozen_time_context():
    """测试冻结时间上下文管理器"""
    print("\n=== Test 5: Frozen Time Context ===")
    
    controller = TimeController()
    controller.reset()
    
    freeze_at = datetime(2026, 1, 1, 0, 0, 0)
    
    with frozen_time(freeze_at):
        assert controller.is_frozen()
        assert get_current_time() == freeze_at
    
    assert not controller.is_frozen()
    
    print("  ✅ Frozen time context test passed")
    return True


def test_accelerated_time_context():
    """测试加速时间上下文管理器"""
    print("\n=== Test 6: Accelerated Time Context ===")
    
    controller = TimeController()
    controller.reset()
    
    start = datetime.now()
    with accelerated_time(5.0):
        time.sleep(0.1)
    
    elapsed = (datetime.now() - start).total_seconds()
    assert elapsed >= 0.09
    
    # 恢复后应该是正常速度
    assert controller.get_acceleration_factor() == 1.0
    
    print(f"  ✅ Accelerated time context test passed (elapsed: {elapsed:.3f}s)")
    return True


def test_state_snapshot():
    """测试状态快照"""
    print("\n=== Test 7: State Snapshot ===")
    
    manager = StateManager()
    
    # 冻结时间并模拟忙碌
    freeze_time(datetime(2026, 3, 15, 12, 0, 0))
    simulate_role_busy("tester", 60)
    
    # 获取快照
    snapshot = get_state_snapshot()
    
    assert snapshot.timestamp is not None
    assert snapshot.time_state["frozen"] == True
    assert "tester" in snapshot.time_state["role_busy_states"]
    
    # 保存快照
    file_path = manager.save_snapshot("test_snapshot")
    assert file_path.exists()
    
    # 加载快照
    loaded = manager.load_snapshot("test_snapshot")
    assert loaded is not None
    assert loaded.time_state["frozen"] == True
    
    # 恢复状态
    result = manager.restore_state(loaded)
    assert result == True
    
    # 清理
    unfreeze_time()
    manager.delete_snapshot("test_snapshot")
    
    print("  ✅ State snapshot test passed")
    return True


def test_alert_manager():
    """测试告警管理器"""
    print("\n=== Test 8: Alert Manager ===")
    
    manager = AlertManager()
    
    # 添加告警
    alert1 = manager.add_alert(AlertLevel.WARNING, "test", "Test warning")
    alert2 = manager.add_alert(AlertLevel.ERROR, "test", "Test error")
    alert3 = manager.add_alert(AlertLevel.INFO, "test", "Test info")
    
    # 验证
    assert len(manager.get_alerts()) == 3
    assert len(manager.get_alerts(AlertLevel.WARNING)) == 1
    assert len(manager.get_alerts(AlertLevel.ERROR)) == 1
    
    # 确认告警
    manager.acknowledge(alert1.id)
    assert alert1.acknowledged == True
    
    # 未确认告警
    unack = manager.get_alerts(unacknowledged_only=True)
    assert len(unack) == 2
    
    # 清空
    manager.clear_alerts()
    assert len(manager.alerts) == 0
    
    print("  ✅ Alert manager test passed")
    return True


def test_health_checker():
    """测试健康检查器"""
    print("\n=== Test 9: Health Checker ===")
    
    alert_mgr = AlertManager()
    checker = HealthChecker(alert_mgr)
    
    # 执行健康检查
    status = checker.check_all()
    
    assert status is not None
    assert status.overall in ["healthy", "degraded", "unhealthy"]
    assert "task_queue" in status.components
    assert "lock_manager" in status.components
    assert "orchestrator" in status.components
    assert "tasks_pending" in status.metrics or status.metrics.get("tasks_total") is not None
    
    # 历史记录
    history = checker.get_history()
    assert len(history) >= 1
    
    print(f"  ✅ Health checker test passed (status: {status.overall})")
    return True


def test_task_scheduler():
    """测试任务调度器"""
    print("\n=== Test 10: Task Scheduler ===")
    
    alert_mgr = AlertManager()
    scheduler = TaskScheduler(alert_mgr)
    
    executed = []
    
    def callback(arg):
        executed.append(arg)
    
    # 调度任务（1秒后执行）
    execute_at = datetime.now() + timedelta(seconds=1)
    scheduler.schedule_task("test_task", execute_at, callback, arg="test_value")
    
    # 等待
    time.sleep(1.5)
    
    # 检查并执行
    result = scheduler.check_and_execute()
    
    assert "test_task" in result
    assert "test_value" in executed
    
    print("  ✅ Task scheduler test passed")
    return True


def test_scheduler_daemon_status():
    """测试调度器守护进程状态"""
    print("\n=== Test 11: Scheduler Daemon Status ===")
    
    daemon = SchedulerDaemon(check_interval=5)
    
    # 获取状态（未启动）
    status = daemon.get_status()
    
    assert status["running"] == False
    assert "stats" in status
    assert "health" in status
    assert "alerts" in status
    
    print("  ✅ Scheduler daemon status test passed")
    return True


def test_alert_handler():
    """测试告警处理程序"""
    print("\n=== Test 12: Alert Handler ===")
    
    manager = AlertManager()
    triggered = []
    
    def handler(alert):
        triggered.append(alert.level.value)
    
    # 注册处理程序
    manager.register_handler(AlertLevel.ERROR, handler)
    
    # 触发告警
    manager.add_alert(AlertLevel.ERROR, "test", "Test error")
    manager.add_alert(AlertLevel.WARNING, "test", "Test warning")  # 不会触发
    
    assert "error" in triggered
    assert len(triggered) == 1
    
    print("  ✅ Alert handler test passed")
    return True


def test_time_controller_callbacks():
    """测试时间控制器回调"""
    print("\n=== Test 13: Time Controller Callbacks ===")
    
    controller = TimeController()
    controller.reset()
    
    events = []
    
    def on_freeze(data):
        events.append("freeze")
    
    def on_accelerate(data):
        events.append(f"accelerate:{data}")
    
    controller.register_callback("freeze", on_freeze)
    controller.register_callback("accelerate", on_accelerate)
    
    freeze_time()
    accelerate_time(2.0)
    
    assert "freeze" in events
    assert "accelerate:2.0" in events
    
    unfreeze_time()
    controller.reset()
    
    print("  ✅ Time controller callbacks test passed")
    return True


def test_concurrent_time_control():
    """测试并发时间控制"""
    print("\n=== Test 14: Concurrent Time Control ===")
    
    controller = TimeController()
    controller.reset()
    
    results = []
    
    def worker(worker_id):
        for i in range(5):
            t = get_current_time()
            results.append((worker_id, t))
            time.sleep(0.01)
    
    # 冻结时间
    freeze_time()
    
    # 并发执行
    threads = []
    for i in range(3):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    # 所有结果的时间应该相同（因为时间被冻结）
    times = [r[1] for r in results]
    assert all(t == times[0] for t in times), "All times should be equal when frozen"
    
    unfreeze_time()
    
    print(f"  ✅ Concurrent time control test passed ({len(results)} results)")
    return True


def run_all_tests():
    """运行所有测试"""
    print("=" * 70)
    print("🧪 时间控制API与调度器守护进程测试套件")
    print("=" * 70)
    
    tests = [
        ("Time Freeze", test_time_controller_freeze),
        ("Time Advance", test_time_controller_advance),
        ("Time Acceleration", test_time_controller_accelerate),
        ("Role Busy Simulation", test_simulate_role_busy),
        ("Frozen Time Context", test_frozen_time_context),
        ("Accelerated Time Context", test_accelerated_time_context),
        ("State Snapshot", test_state_snapshot),
        ("Alert Manager", test_alert_manager),
        ("Health Checker", test_health_checker),
        ("Task Scheduler", test_task_scheduler),
        ("Scheduler Daemon Status", test_scheduler_daemon_status),
        ("Alert Handler", test_alert_handler),
        ("Time Controller Callbacks", test_time_controller_callbacks),
        ("Concurrent Time Control", test_concurrent_time_control),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            failed += 1
            print(f"  ❌ Test '{name}' failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print(f"📊 测试结果: {passed}/{len(tests)} 通过, {failed} 失败")
    print("=" * 70)
    
    # 清理
    try:
        controller = TimeController()
        controller.reset()
    except:
        pass
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
