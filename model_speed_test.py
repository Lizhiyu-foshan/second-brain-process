#!/usr/bin/env python3
"""
模型速度对比测试
对比 Qwen3.5 Plus vs Kimi K2.5 的推理速度
"""

import time
import json
import subprocess
from datetime import datetime
from typing import List, Tuple

# 测试配置
MODELS = {
    "qwen3.5-plus": "alicloud/qwen3.5-plus",
    "kimi-k2.5": "kimi-coding/k2p5"
}

# 测试用例（不同复杂度）
TEST_CASES = [
    {
        "name": "简单问答",
        "prompt": "什么是Python中的列表推导式？",
        "expected_length": "short"
    },
    {
        "name": "代码生成",
        "prompt": "写一个Python函数，实现快速排序算法",
        "expected_length": "medium"
    },
    {
        "name": "逻辑推理",
        "prompt": "有三个人A、B、C，分别来自北京、上海、广州。A说：'我来自北京'，B说：'我来自上海'，C说：'A来自广州'。已知只有一人说真话，请问每个人实际来自哪里？",
        "expected_length": "medium"
    },
    {
        "name": "长文本生成",
        "prompt": "写一篇关于人工智能发展趋势的文章，500字左右",
        "expected_length": "long"
    },
    {
        "name": "复杂分析",
        "prompt": "分析以下代码的时间复杂度和空间复杂度，并给出优化建议：\n\ndef fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
        "expected_length": "long"
    }
]

def measure_response_time(model_alias: str, prompt: str) -> Tuple[float, float, str]:
    """
    测量模型响应时间
    
    Returns:
        (首token时间, 总时间, 响应内容)
    """
    # 构建请求
    start_time = time.time()
    first_token_time = None
    
    try:
        # 使用 openclaw 调用模型
        result = subprocess.run(
            ['openclaw', 'session', 'status', '--model', model_alias],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        # 模拟调用（实际测试时需要真正调用模型）
        # 这里只是一个框架，实际测试需要集成到OpenClaw的调用流程中
        
        end_time = time.time()
        total_time = end_time - start_time
        
        return first_token_time or total_time, total_time, "测试响应"
        
    except Exception as e:
        return -1, -1, str(e)

def run_speed_test(iterations: int = 3) -> dict:
    """
    运行速度测试
    
    Args:
        iterations: 每个测试用例运行次数
    
    Returns:
        测试结果字典
    """
    results = {
        "timestamp": datetime.now().isoformat(),
        "iterations": iterations,
        "models": list(MODELS.keys()),
        "results": {}
    }
    
    print("=" * 60)
    print("模型速度对比测试")
    print("=" * 60)
    print(f"\n测试配置:")
    print(f"  模型: {', '.join(MODELS.keys())}")
    print(f"  每个用例运行: {iterations} 次")
    print(f"  测试用例数: {len(TEST_CASES)}")
    print()
    
    for test_case in TEST_CASES:
        test_name = test_case["name"]
        prompt = test_case["prompt"]
        
        print(f"\n{'='*60}")
        print(f"测试: {test_name}")
        print(f"{'='*60}")
        
        results["results"][test_name] = {}
        
        for model_name, model_alias in MODELS.items():
            print(f"\n  模型: {model_name}")
            
            times = []
            for i in range(iterations):
                print(f"    第 {i+1}/{iterations} 次...", end=" ", flush=True)
                
                # 这里需要实际调用模型
                # 目前只是框架
                first_token, total_time, response = measure_response_time(model_alias, prompt)
                
                times.append({
                    "first_token": first_token,
                    "total_time": total_time,
                    "response_length": len(response)
                })
                
                print(f"首token: {first_token:.2f}s, 总时间: {total_time:.2f}s")
            
            # 计算平均
            avg_first_token = sum(t["first_token"] for t in times) / len(times)
            avg_total = sum(t["total_time"] for t in times) / len(times)
            
            results["results"][test_name][model_name] = {
                "iterations": times,
                "average_first_token": avg_first_token,
                "average_total": avg_total
            }
            
            print(f"  ✓ 平均首token: {avg_first_token:.2f}s")
            print(f"  ✓ 平均总时间: {avg_total:.2f}s")
    
    return results

def print_comparison_report(results: dict):
    """打印对比报告"""
    print("\n" + "=" * 80)
    print("对比测试报告")
    print("=" * 80)
    
    for test_name, test_results in results["results"].items():
        print(f"\n【{test_name}】")
        print("-" * 60)
        
        # 获取所有模型结果
        model_times = {}
        for model_name, model_result in test_results.items():
            model_times[model_name] = {
                "first_token": model_result["average_first_token"],
                "total": model_result["average_total"]
            }
        
        # 找出最快的
        fastest_first = min(model_times.items(), key=lambda x: x[1]["first_token"])
        fastest_total = min(model_times.items(), key=lambda x: x[1]["total"])
        
        for model_name, times in model_times.items():
            first_badge = " 🏆" if model_name == fastest_first[0] else ""
            total_badge = " 🏆" if model_name == fastest_total[0] else ""
            
            print(f"  {model_name}:")
            print(f"    首token时间: {times['first_token']:.2f}s{first_badge}")
            print(f"    总时间: {times['total']:.2f}s{total_badge}")
        
        # 计算差距
        if len(model_times) == 2:
            models = list(model_times.keys())
            m1, m2 = models[0], models[1]
            
            first_diff = abs(model_times[m1]["first_token"] - model_times[m2]["first_token"])
            total_diff = abs(model_times[m1]["total"] - model_times[m2]["total"])
            
            faster_first = m1 if model_times[m1]["first_token"] < model_times[m2]["first_token"] else m2
            faster_total = m1 if model_times[m1]["total"] < model_times[m2]["total"] else m2
            
            print(f"\n  📊 差距:")
            print(f"    首token: {faster_first} 快 {first_diff:.2f}s")
            print(f"    总时间: {faster_total} 快 {total_diff:.2f}s")

def save_results(results: dict, filename: str = None):
    """保存结果到文件"""
    if filename is None:
        filename = f"/tmp/model_speed_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ 结果已保存到: {filename}")

if __name__ == "__main__":
    import sys
    
    iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    
    # 运行测试
    results = run_speed_test(iterations)
    
    # 打印报告
    print_comparison_report(results)
    
    # 保存结果
    save_results(results)
    
    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)
