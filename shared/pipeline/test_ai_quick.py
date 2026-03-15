#!/usr/bin/env python3
"""
快速 AI 集成测试 - 15秒超时
"""
import os
os.environ["DASHSCOPE_API_KEY"] = "sk-sp-68f6997fc9924babb9f6b50c03a5a529"
os.environ["PYTHONUNBUFFERED"] = "1"

import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# 重定向输出到文件
log_file = "/tmp/ai_test_output.log"
f = open(log_file, "w")
sys.stdout = f
sys.stderr = f

print("=" * 70)
print("🧪 AI 驱动任务分解集成测试")
print("=" * 70)
print()

tmp_dir = tempfile.mkdtemp()
state_dir = os.path.join(tmp_dir, 'state')
lock_dir = os.path.join(tmp_dir, 'locks')
os.makedirs(state_dir, exist_ok=True)
os.makedirs(lock_dir, exist_ok=True)

def run_test():
    from layer1.api import ResourceSchedulerAPI
    from layer2 import Orchestrator
    
    print("📋 步骤1: 初始化系统")
    layer1 = ResourceSchedulerAPI(state_dir, lock_dir)
    orchestrator = Orchestrator(layer1, state_dir)
    print("  ✓ 初始化完成\n")
    
    print("📋 步骤2: AI 驱动任务分解")
    print("  等待 AI 分析 (最多15秒)...")
    
    import urllib.request
    
    # 直接测试 API 调用
    url = "https://coding.dashscope.aliyuncs.com/v1/chat/completions"
    payload = {
        "model": "kimi-k2.5",
        "messages": [
            {"role": "system", "content": "你是一个项目规划专家。请分析需求并输出JSON格式的任务分解。"},
            {"role": "user", "content": "开发一个Python日志分析工具，解析多种格式日志，生成统计报告。请分解为3-5个任务，每个任务指定负责角色(architect/developer/tester)和依赖关系。输出JSON格式: {tasks: [{name, role, depends_on: []}]"}
        ],
        "max_tokens": 2000,
        "temperature": 0.7
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ['DASHSCOPE_API_KEY']}"
    }
    
    import json
    data = json.dumps(payload).encode('utf-8')
    request = urllib.request.Request(url, data=data, headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode('utf-8'))
            content = result["choices"][0]["message"]["content"]
            print(f"  ✓ AI 响应成功")
            print(f"  响应长度: {len(content)} 字符")
            print(f"  预览: {content[:200]}...")
    except Exception as e:
        print(f"  ✗ API 调用失败: {e}")
        return
    
    print("\n📋 步骤3: 使用 Planner 进行完整分解")
    description = "开发一个Python日志分析工具，可以解析多种格式的日志文件，生成统计报告"
    blueprint = orchestrator.planner.create_blueprint(description)
    
    print(f"  ✓ 分解完成")
    print(f"    项目: {blueprint.name}")
    print(f"    任务数: {len(blueprint.tasks)}")
    print(f"    角色: {', '.join(blueprint.estimated_roles)}")
    print()
    
    for i, task in enumerate(blueprint.tasks, 1):
        deps = f" 依赖:{task.depends_on}" if task.depends_on else ""
        print(f"    {i}. [{task.role}] {task.name}{deps}")
    
    print("\n" + "=" * 70)
    print("✅ 测试通过！")
    print("=" * 70)

try:
    run_test()
except Exception as e:
    import traceback
    print(f"\n❌ 测试失败: {e}")
    traceback.print_exc()
finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)
    f.close()
