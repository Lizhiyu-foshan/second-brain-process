#!/usr/bin/env python3
"""
快速集成验证
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path

tmp_dir = tempfile.mkdtemp()
os.environ["OPENCLAW_WORKSPACE"] = tmp_dir
os.environ["DASHSCOPE_API_KEY"] = "sk-test-key"

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("⚡ 快速集成验证")
print("=" * 60)

results = []

def test(name, func):
    print(f"\n📋 {name}")
    try:
        func()
        results.append((name, True))
        print(f"  ✅ 通过")
    except Exception as e:
        results.append((name, False, str(e)))
        print(f"  ❌ 失败: {e}")

# 测试1: Layer 1 API 基础
def test_api_basic():
    from layer1.api import ResourceSchedulerAPI
    from shared.models import Task
    
    api = ResourceSchedulerAPI()
    api.registry.register("architect", "架构师", ["design"])
    
    task = Task(id="t1", project_id="p1", role_id="architect", name="测试", priority="P0")
    result = api.submit_task(task)
    assert result["success"] == True
    
    lock_result = api.acquire_lock("architect", "t1")
    assert lock_result["acquired"] == True
    
    api.complete_task("t1", success=True)
    assert api.task_queue.get("t1").status == "completed"

test("Layer 1 API 基础流程", test_api_basic)

# 测试2: 多角色协调
def test_multi_role():
    from layer1.api import ResourceSchedulerAPI
    from shared.models import Task
    
    api = ResourceSchedulerAPI()
    api.registry.register("arch", "架构", ["design"])
    api.registry.register("dev", "开发", ["code"])
    
    api.submit_task(Task(id="t1", project_id="p1", role_id="arch", name="设计"))
    api.submit_task(Task(id="t2", project_id="p1", role_id="dev", name="开发"))
    
    assert api.task_queue.get_next_for_role("arch").id == "t1"
    assert api.task_queue.get_next_for_role("dev").id == "t2"

test("多角色协调", test_multi_role)

# 测试3: 依赖链
def test_dependencies():
    from layer1.api import ResourceSchedulerAPI
    from shared.models import Task
    
    api = ResourceSchedulerAPI()
    api.registry.register("arch", "架构", ["design"])
    
    api.submit_task(Task(id="a", project_id="p1", role_id="arch", name="A"))
    api.submit_task(Task(id="b", project_id="p1", role_id="arch", name="B", depends_on=["a"]))
    
    # 只有 A 可执行
    next_task = api.task_queue.get_next_for_role("arch")
    assert next_task.id == "a"

test("任务依赖链", test_dependencies)

# 测试4: 持久化
def test_persistence():
    from layer1.api import ResourceSchedulerAPI
    from shared.models import Task
    
    api1 = ResourceSchedulerAPI()
    api1.registry.register("arch", "架构", ["design"])
    api1.submit_task(Task(id="p1", project_id="p1", role_id="arch", name="持久化测试"))
    api1.acquire_lock("arch", "p1")
    
    # 新实例
    api2 = ResourceSchedulerAPI()
    assert api2.task_queue.get("p1") is not None
    assert api2.lock_manager.get_lock_info("arch") is not None

test("数据持久化", test_persistence)

# 测试5: 错误处理
def test_errors():
    from layer1.api import ResourceSchedulerAPI
    from shared.models import Task
    
    api = ResourceSchedulerAPI()
    
    # 不存在任务返回 None
    assert api.task_queue.get("not_exist") is None
    
    # 释放不存在锁（幂等）
    assert api.release_lock("not_exist")["released"] == True
    
    # 向不存在角色提交任务
    result = api.submit_task(Task(id="bad", project_id="p1", role_id="not_exist", name="错误"))
    assert result["success"] == False

test("错误处理", test_errors)

# 清理
shutil.rmtree(tmp_dir, ignore_errors=True)

# 汇总
print("\n" + "=" * 60)
print("📊 测试结果")
print("=" * 60)
passed = sum(1 for r in results if len(r) == 2)
failed = sum(1 for r in results if len(r) == 3)
print(f"通过: {passed}, 失败: {failed}")
for r in results:
    print(f"  {'✅' if len(r) == 2 else '❌'} {r[0]}")
print()
print("🎉 集成验证完成！" if failed == 0 else f"⚠️  {failed} 个失败")
