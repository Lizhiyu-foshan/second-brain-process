#!/usr/bin/env python3
"""
检查GLM5异步生成状态
"""

import json
from pathlib import Path
from datetime import datetime

WORKSPACE = Path("/root/.openclaw/workspace")
AI_RESULTS_FILE = WORKSPACE / ".learnings" / "AI_RESULTS.json"


def check_ai_status():
    """检查AI生成状态"""
    print("=== GLM5异步改进生成状态 ===")
    print()
    
    # 检查是否有结果文件
    if not AI_RESULTS_FILE.exists():
        print("❌ 尚无AI生成结果")
        print("   可能GLM5仍在生成中，或未触发")
        return
    
    try:
        with open(AI_RESULTS_FILE, 'r') as f:
            results = json.load(f)
        
        print(f"✅ 找到 {len(results)} 条AI生成记录\n")
        
        for error_id, data in results.items():
            print(f"错误ID: {error_id}")
            print(f"  错误类型: {data.get('error_pattern', '未知')}")
            print(f"  生成时间: {data.get('timestamp', '未知')}")
            
            result = data.get('result', {})
            
            if 'reasoning' in result:
                reasoning = result['reasoning']
                if len(reasoning) > 100:
                    reasoning = reasoning[:100] + "..."
                print(f"  AI推理: {reasoning}")
            
            if 'improvements' in result:
                print(f"  改进项数: {len(result['improvements'])}")
                for i, imp in enumerate(result['improvements'], 1):
                    print(f"    {i}. {imp.get('description', '无描述')}")
            
            print()
    
    except Exception as e:
        print(f"❌ 读取结果失败: {e}")


if __name__ == "__main__":
    check_ai_status()
