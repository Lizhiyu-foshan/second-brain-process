#!/usr/bin/env python3
"""
AI API 配置验证工具
"""
import os
import sys
import json
import urllib.request
import urllib.error

print("=" * 60)
print("🔑 AI API 配置验证")
print("=" * 60)
print()

# 检查环境变量
api_key = os.getenv("DASHSCOPE_API_KEY")

if not api_key:
    print("❌ DASHSCOPE_API_KEY 未设置")
    print()
    print("请设置环境变量:")
    print("  export DASHSCOPE_API_KEY='sk-...'")
    print()
    print("可以将上述命令添加到 ~/.bashrc 或 ~/.zshrc 中")
    sys.exit(1)

print(f"✓ API Key 已配置")
print(f"  前缀: {api_key[:15]}...")
print()

# 测试 API 调用
print("🧪 测试 API 连接...")

try:
    # 尝试 coding endpoint（如果配置了 ALICLOUD_API_KEY）
    url = "https://coding.dashscope.aliyuncs.com/v1/chat/completions"
    
    payload = {
        "model": "kimi-k2.5",  # 使用简化的模型名称
        "messages": [
            {"role": "system", "content": "你是一个测试助手。"},
            {"role": "user", "content": "回复'API测试成功'，不要添加其他内容。"}
        ],
        "max_tokens": 50,
        "temperature": 0.1
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = json.dumps(payload).encode('utf-8')
    request = urllib.request.Request(url, data=data, headers=headers, method='POST')
    
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode('utf-8'))
        content = result["choices"][0]["message"]["content"]
        
        print(f"✓ API 调用成功")
        print(f"  响应: {content[:50]}")
        print(f"  模型: {result.get('model', 'unknown')}")
        print(f"  Token用量: {result.get('usage', {})}")
        print()
        print("=" * 60)
        print("✅ AI API 配置验证通过！")
        print("=" * 60)
        sys.exit(0)
        
except urllib.error.HTTPError as e:
    print(f"❌ API 调用失败: HTTP {e.code}")
    try:
        error_body = json.loads(e.read().decode('utf-8'))
        print(f"  错误详情: {error_body}")
    except:
        print(f"  错误信息: {e.reason}")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ API 调用失败: {e}")
    sys.exit(1)
