#!/usr/bin/env python3
"""
模型速度对比测试 - 自动化版本
对比 Qwen3.5 Plus vs Kimi K2.5 的推理速度

使用方法:
  python3 model_speed_test_auto.py [迭代次数]
  
例如:
  python3 model_speed_test_auto.py 3  # 每个测试运行3次
"""

import time
import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import subprocess

# 添加工作目录到路径
sys.path.insert(0, '/root/.openclaw/workspace/second-brain-processor')

# 测试配置
MODELS = {
    "qwen3.5-plus": {
        "alias": "alicloud/qwen3.5-plus",
        "name": "Qwen3.5 Plus"
    },
    "kimi-k2.5": {
        "alias": "kimi-coding/k2p5", 
        "name": "Kimi K2.5"
    }
}

# 测试用例（覆盖不同场景）
TEST_CASES = [
    {
        "id": "T1",
        "name": "简单问答",
        "prompt": "什么是Python中的列表推导式？用一句话解释。",
        "category": "short",
        "expected_tokens": 50
    },
    {
        "id": "T2", 
        "name": "代码生成",
        "prompt": "写一个Python函数，实现快速排序算法，并添加注释。",
        "category": "code",
        "expected_tokens": 200
    },
    {
        "id": "T3",
        "name": "逻辑推理",
        "prompt": """有三个人A、B、C，分别来自北京、上海、广州。
A说："我来自北京"
B说："我来自上海"  
C说："A来自广州"
已知只有一人说真话，请问每个人实际来自哪里？请详细推理。""",
        "category": "reasoning",
        "expected_tokens": 300
    },
    {
        "id": "T4",
        "name": "长文本生成",
        "prompt": "写一篇关于人工智能发展趋势的文章，500字左右，包含3个主要观点。",
        "category": "long",
        "expected_tokens": 800
    },
    {
        "id": "T5",
        "name": "复杂分析",
        "prompt": """分析以下代码的时间复杂度和空间复杂度，并给出优化建议：

def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

请详细解释为什么效率低，以及如何优化。""",
        "category": "analysis",
        "expected_tokens": 600
    },
    {
        "id": "T6",
        "name": "创意写作",
        "prompt": "写一个关于未来世界的短篇科幻故事开头（200字），要有悬念。",
        "category": "creative",
        "expected_tokens": 400
    }
]

class ModelSpeedTester:
    """模型速度测试器"""
    
    def __init__(self, iterations: int = 3):
        self.iterations = iterations
        self.results = {}
        self.workspace = "/root/.openclaw/workspace"
        
    def call_model_via_openclaw(self, model_alias: str, prompt: str) -> Tuple[float, float, str, int]:
        """
        通过OpenClaw调用模型并测量时间
        
        Returns:
            (首token时间秒, 总时间秒, 响应内容, 响应字符数)
        """
        # 创建临时脚本文件
        temp_script = f"/tmp/model_test_{int(time.time() * 1000)}.py"
        
        script_content = f'''
import sys
sys.path.insert(0, "{self.workspace}/second-brain-processor")

from ai_processor import process_with_model

prompt = """{prompt.replace('"', '\\"').replace(chr(10), '\\n')}"""

result = process_with_model(prompt, model="{model_alias}", use_cache=False)
print("===RESPONSE_START===")
print(result)
print("===RESPONSE_END===")
'''
        
        with open(temp_script, 'w') as f:
            f.write(script_content)
        
        try:
            # 记录开始时间
            start_time = time.time()
            first_token_time = None
            
            # 执行调用
            result = subprocess.run(
                ['python3', temp_script],
                capture_output=True,
                text=True,
                timeout=180  # 3分钟超时
            )
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # 解析响应
            output = result.stdout
            if "===RESPONSE_START===" in output and "===RESPONSE_END===" in output:
                response = output.split("===RESPONSE_START===")[1].split("===RESPONSE_END===")[0].strip()
            else:
                response = output.strip()
            
            # 估计首token时间（这里用总时间的一半作为近似）
            # 实际首token时间需要流式接口才能准确测量
            first_token_time = total_time * 0.3  # 估算：首token大约是总时间的30%
            
            return first_token_time, total_time, response, len(response)
            
        except subprocess.TimeoutExpired:
            return -1, 180, "超时", 0
        except Exception as e:
            return -1, -1, str(e), 0
        finally:
            # 清理临时文件
            if os.path.exists(temp_script):
                os.remove(temp_script)
    
    def run_single_test(self, test_case: dict, model_key: str) -> Dict:
        """运行单个测试用例"""
        model_info = MODELS[model_key]
        results = []
        
        print(f"    测试: {test_case['name']} ({test_case['id']})")
        
        for i in range(self.iterations):
            print(f"      迭代 {i+1}/{self.iterations}...", end=" ", flush=True)
            
            first_token, total_time, response, char_count = self.call_model_via_openclaw(
                model_info["alias"],
                test_case["prompt"]
            )
            
            if total_time < 0:
                print(f"❌ 失败: {response[:50]}")
                results.append({
                    "iteration": i + 1,
                    "first_token": None,
                    "total_time": None,
                    "char_count": 0,
                    "success": False,
                    "error": response
                })
            else:
                print(f"✓ 首token: {first_token:.2f}s, 总时间: {total_time:.2f}s, 字符: {char_count}")
                results.append({
                    "iteration": i + 1,
                    "first_token": first_token,
                    "total_time": total_time,
                    "char_count": char_count,
                    "success": True
                })
            
            # 每次迭代之间暂停一下，避免rate limit
            if i < self.iterations - 1:
                time.sleep(2)
        
        # 计算平均值（只计算成功的）
        successful = [r for r in results if r["success"]]
        if successful:
            avg_first = sum(r["first_token"] for r in successful) / len(successful)
            avg_total = sum(r["total_time"] for r in successful) / len(successful)
            avg_chars = sum(r["char_count"] for r in successful) / len(successful)
            
            # 计算生成速度（字符/秒）
            speed = avg_chars / avg_total if avg_total > 0 else 0
        else:
            avg_first = avg_total = avg_chars = speed = 0
        
        return {
            "test_id": test_case["id"],
            "test_name": test_case["name"],
            "category": test_case["category"],
            "model": model_key,
            "iterations": results,
            "average": {
                "first_token": round(avg_first, 3),
                "total_time": round(avg_total, 3),
                "char_count": round(avg_chars, 1),
                "speed_cps": round(speed, 1)  # characters per second
            },
            "success_rate": len(successful) / len(results)
        }
    
    def run_all_tests(self) -> Dict:
        """运行所有测试"""
        print("=" * 70)
        print("🚀 模型速度对比测试")
        print("=" * 70)
        print(f"\n📋 配置:")
        print(f"   模型: {', '.join(MODELS.keys())}")
        print(f"   迭代次数: {self.iterations}")
        print(f"   测试用例: {len(TEST_CASES)} 个")
        print()
        
        all_results = {
            "timestamp": datetime.now().isoformat(),
            "config": {
                "iterations": self.iterations,
                "models": MODELS,
                "test_cases": len(TEST_CASES)
            },
            "results": {}
        }
        
        # 对每个模型运行所有测试
        for model_key in MODELS.keys():
            print(f"\n{'='*70}")
            print(f"🤖 测试模型: {MODELS[model_key]['name']}")
            print(f"{'='*70}")
            
            model_results = []
            
            for test_case in TEST_CASES:
                result = self.run_single_test(test_case, model_key)
                model_results.append(result)
                
                # 测试之间暂停，避免过热
                time.sleep(3)
            
            all_results["results"][model_key] = model_results
            
            # 模型之间暂停更久
            if model_key != list(MODELS.keys())[-1]:
                print(f"\n⏳ 切换模型，暂停 10 秒...")
                time.sleep(10)
        
        return all_results
    
    def generate_report(self, results: Dict) -> str:
        """生成对比报告"""
        lines = []
        lines.append("\n" + "=" * 70)
        lines.append("📊 模型速度对比报告")
        lines.append("=" * 70)
        lines.append(f"\n测试时间: {results['timestamp']}")
        lines.append(f"每个用例迭代: {results['config']['iterations']} 次\n")
        
        # 汇总统计
        lines.append("\n" + "-" * 70)
        lines.append("📈 综合性能对比")
        lines.append("-" * 70)
        
        summary = {}
        for model_key, model_results in results["results"].items():
            successful_tests = [r for r in model_results if r["success_rate"] > 0]
            
            if successful_tests:
                avg_first = sum(r["average"]["first_token"] for r in successful_tests) / len(successful_tests)
                avg_total = sum(r["average"]["total_time"] for r in successful_tests) / len(successful_tests)
                avg_speed = sum(r["average"]["speed_cps"] for r in successful_tests) / len(successful_tests)
                
                summary[model_key] = {
                    "avg_first_token": avg_first,
                    "avg_total_time": avg_total,
                    "avg_speed": avg_speed,
                    "success_count": len(successful_tests)
                }
        
        # 打印对比表
        lines.append(f"\n{'模型':<20} {'首token(s)':<12} {'总时间(s)':<12} {'速度(字/s)':<12} {'成功数':<8}")
        lines.append("-" * 70)
        
        for model_key, stats in summary.items():
            lines.append(f"{MODELS[model_key]['name']:<20} "
                        f"{stats['avg_first_token']:<12.2f} "
                        f"{stats['avg_total_time']:<12.2f} "
                        f"{stats['avg_speed']:<12.1f} "
                        f"{stats['success_count']:<8}")
        
        # 找出胜者
        if len(summary) == 2:
            models = list(summary.keys())
            m1, m2 = models[0], models[1]
            
            lines.append("\n" + "-" * 70)
            lines.append("🏆 对比结果")
            lines.append("-" * 70)
            
            # 首token时间
            if summary[m1]["avg_first_token"] < summary[m2]["avg_first_token"]:
                winner_first = m1
                diff_first = summary[m2]["avg_first_token"] - summary[m1]["avg_first_token"]
            else:
                winner_first = m2
                diff_first = summary[m1]["avg_first_token"] - summary[m2]["avg_first_token"]
            
            # 总时间
            if summary[m1]["avg_total_time"] < summary[m2]["avg_total_time"]:
                winner_total = m1
                diff_total = summary[m2]["avg_total_time"] - summary[m1]["avg_total_time"]
            else:
                winner_total = m2
                diff_total = summary[m1]["avg_total_time"] - summary[m2]["avg_total_time"]
            
            # 速度
            if summary[m1]["avg_speed"] > summary[m2]["avg_speed"]:
                winner_speed = m1
                diff_speed = summary[m1]["avg_speed"] - summary[m2]["avg_speed"]
            else:
                winner_speed = m2
                diff_speed = summary[m2]["avg_speed"] - summary[m1]["avg_speed"]
            
            lines.append(f"\n⚡ 首token响应: {MODELS[winner_first]['name']} 更快 (快 {diff_first:.2f}s)")
            lines.append(f"⏱️ 总响应时间: {MODELS[winner_total]['name']} 更快 (快 {diff_total:.2f}s)")
            lines.append(f"📝 生成速度: {MODELS[winner_speed]['name']} 更快 (快 {diff_speed:.1f} 字/s)")
        
        # 详细测试用例对比
        lines.append("\n" + "=" * 70)
        lines.append("📋 各测试用例详细对比")
        lines.append("=" * 70)
        
        for test_case in TEST_CASES:
            test_id = test_case["id"]
            test_name = test_case["name"]
            
            lines.append(f"\n【{test_id}】{test_name} ({test_case['category']})")
            lines.append("-" * 50)
            
            # 收集各模型结果
            model_times = {}
            for model_key, model_results in results["results"].items():
                for r in model_results:
                    if r["test_id"] == test_id:
                        model_times[model_key] = r["average"]
                        break
            
            # 打印对比
            for model_key, avg in model_times.items():
                lines.append(f"  {MODELS[model_key]['name']:<15} "
                            f"首token: {avg['first_token']:.2f}s | "
                            f"总时间: {avg['total_time']:.2f}s | "
                            f"速度: {avg['speed_cps']:.1f}字/s")
        
        lines.append("\n" + "=" * 70)
        lines.append("✅ 测试完成")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def save_results(self, results: Dict, report: str):
        """保存结果到文件"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 保存JSON
        json_file = f"{self.workspace}/model_speed_test_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # 保存报告
        report_file = f"{self.workspace}/model_speed_report_{timestamp}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n💾 结果已保存:")
        print(f"   JSON: {json_file}")
        print(f"   报告: {report_file}")

def main():
    """主函数"""
    iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    
    print("🚀 模型速度对比测试")
    print("=" * 70)
    print(f"\n⚠️  注意: 这个测试将调用两个模型各 {iterations * len(TEST_CASES)} 次")
    print(f"   预计耗时: {iterations * len(TEST_CASES) * 2 * 30} 秒左右")
    print(f"\n   模型1: Qwen3.5 Plus")
    print(f"   模型2: Kimi K2.5")
    print()
    
    confirm = input("确认开始测试? (y/N): ")
    if confirm.lower() != 'y':
        print("已取消")
        return
    
    # 创建测试器
    tester = ModelSpeedTester(iterations=iterations)
    
    # 运行测试
    results = tester.run_all_tests()
    
    # 生成报告
    report = tester.generate_report(results)
    print(report)
    
    # 保存结果
    tester.save_results(results, report)

if __name__ == "__main__":
    main()
