#!/usr/bin/env python3
"""
四模型策略综合测试

测试场景：
1. MiniMax M2.5 - 快速编码修复
2. GLM-5 - 复杂架构设计
3. Qwen 3.5 Plus - 快速对话
4. Kimi 2.5 - 深度思考
"""

import sys
import time
sys.path.insert(0, '/root/.openclaw/workspace/second-brain-processor')

from model_router import select_model_for_prompt, router


def test_model_selection():
    """测试模型选择逻辑"""
    print("=" * 60)
    print("🧪 测试1: 模型选择逻辑")
    print("=" * 60)
    
    test_cases = [
        ("修复Python列表越界bug", None, "MiniMax M2.5"),
        ("设计一个支持百万并发的微服务架构", None, "GLM-5"),
        ("你好，解释一下什么是递归", None, "Qwen 3.5 Plus"),
        ("请深入分析人工智能对人类社会结构的长期影响", None, "Kimi 2.5"),
        ("写一个快速排序算法", "coding", "MiniMax M2.5"),
        ("讨论自由意志是否存在", "chat", "Kimi 2.5"),
    ]
    
    results = []
    for prompt, task_type, expected in test_cases:
        result = select_model_for_prompt(prompt, task_type)
        actual = result['model_name']
        status = "✅" if actual == expected else "❌"
        print(f"{status} {prompt[:30]}... -> {actual}")
        results.append((prompt, expected, actual, actual == expected))
    
    passed = sum(1 for _, _, _, ok in results if ok)
    print(f"\n结果: {passed}/{len(results)} 通过")
    return passed == len(results)


def test_api_connectivity():
    """测试API连接"""
    print("\n" + "=" * 60)
    print("🧪 测试2: API连接测试")
    print("=" * 60)
    
    import os
    import urllib.request
    import json
    import ssl
    
    ALICLOUD_API_KEY = os.environ.get('ALICLOUD_API_KEY', '')
    ALICLOUD_BASE_URL = os.environ.get('ALICLOUD_BASE_URL', '')
    
    if not ALICLOUD_API_KEY:
        print("❌ API Key未配置")
        return False
    
    models_to_test = [
        ("minimax-m2-5", "MiniMax M2.5"),
        ("glm-5", "GLM-5"),
    ]
    
    results = []
    for model_id, name in models_to_test:
        try:
            url = f"{ALICLOUD_BASE_URL}/chat/completions"
            data = {
                "model": model_id,
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 10
            }
            
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {ALICLOUD_API_KEY}'
                },
                method='POST'
            )
            
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            with urllib.request.urlopen(req, context=ssl_context, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                if 'choices' in result or 'error' in result:
                    print(f"✅ {name} - 连接正常")
                    results.append(True)
                else:
                    print(f"⚠️ {name} - 响应异常")
                    results.append(False)
                    
        except Exception as e:
            print(f"❌ {name} - 连接失败: {str(e)[:50]}")
            results.append(False)
    
    passed = sum(results)
    print(f"\n结果: {passed}/{len(results)} 通过")
    return passed > 0


def test_env_configuration():
    """测试环境变量配置"""
    print("\n" + "=" * 60)
    print("🧪 测试3: 环境变量配置")
    print("=" * 60)
    
    import os
    
    configs = [
        ('ALICLOUD_API_KEY', 'API密钥'),
        ('ALICLOUD_BASE_URL', '基础URL'),
        ('ALICLOUD_MODEL_FAST', '快速编码模型'),
        ('ALICLOUD_MODEL_COMPLEX', '复杂编码模型'),
        ('ALICLOUD_MODEL_CHAT_FAST', '快速对话模型'),
        ('ALICLOUD_MODEL_CHAT_COMPLEX', '复杂对话模型'),
    ]
    
    results = []
    for key, desc in configs:
        value = os.environ.get(key, '')
        if value:
            # 隐藏敏感信息
            display = value[:20] + "..." if len(value) > 20 else value
            print(f"✅ {desc}: {display}")
            results.append(True)
        else:
            print(f"❌ {desc}: 未配置")
            results.append(False)
    
    passed = sum(results)
    print(f"\n结果: {passed}/{len(results)} 通过")
    return passed == len(results)


def test_error_analysis():
    """测试错误分析和任务类型检测"""
    print("\n" + "=" * 60)
    print("🧪 测试4: 错误分析与任务类型检测")
    print("=" * 60)
    
    test_errors = [
        ("git_push_timeout", "coding", "fast"),
        ("file_not_found", "coding", "fast"),
        ("memory_limit", "coding", "complex"),
        ("architecture_issue", "coding", "complex"),
    ]
    
    # 模拟错误分析
    from ai_async_generator import analyze_error
    
    results = []
    for error_type, expected_task, expected_complexity in test_errors:
        # 构造模拟错误
        mock_error = {
            'id': f'ERR-20260307-001',
            'title': error_type,
            'details': f'Test {error_type}',
            'time': None
        }
        
        analysis = analyze_error(mock_error)
        actual_task = analysis.get('task_type', 'unknown')
        
        # 映射到预期
        task_mapping = {
            'fast': 'fast',
            'complex': 'complex'
        }
        
        status = "✅" if actual_task == expected_complexity else "❌"
        print(f"{status} {error_type} -> 任务类型: {actual_task}")
        results.append(actual_task == expected_complexity)
    
    passed = sum(results)
    print(f"\n结果: {passed}/{len(results)} 通过")
    return passed == len(results)


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("🔬 四模型策略综合测试开始")
    print("=" * 60)
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tests = [
        ("环境变量配置", test_env_configuration),
        ("API连接测试", test_api_connectivity),
        ("模型选择逻辑", test_model_selection),
        ("错误分析", test_error_analysis),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"❌ {name} 测试异常: {e}")
            results.append((name, False))
        print()
    
    # 汇总
    print("=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {name}")
    
    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    
    print(f"\n总计: {total_passed}/{total_tests} 通过 ({total_passed/total_tests*100:.0f}%)")
    
    if total_passed == total_tests:
        print("\n🎉 所有测试通过！四模型策略配置正常。")
    else:
        print("\n⚠️ 部分测试失败，请检查配置。")
    
    return total_passed == total_tests


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
