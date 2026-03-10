#!/usr/bin/env python3
"""
智能模型处理器（带持续模式）

整合功能：
1. 自动检测任务类型（model_router）
2. 手动声明切换（model_session_manager）
3. 持续模式（保持当前模型直到切换）
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/second-brain-processor')

from model_router import select_model_for_prompt, TaskType
from model_session_manager import (
    process_message_with_mode,
    get_current_model,
    get_model_display_name,
    DEFAULT_MODEL
)


def smart_model_select(user_message: str, has_link: bool = False) -> dict:
    """
    智能选择模型（考虑持续模式）
    
    优先级：
    1. 检测是否包含模式切换指令
    2. 获取当前持续模式
    3. 如果是默认模式，自动检测任务类型
    
    Returns:
        {
            'model_id': 模型ID,
            'model_name': 模型名称,
            'reason': 选择原因,
            'switched': 是否刚切换,
            'switch_message': 切换提示消息,
            'clean_message': 清理后的用户消息
        }
    """
    # 第1步：检测模式切换指令
    clean_message, switched, switch_message = process_message_with_mode(user_message)
    
    # 第2步：获取当前模型（可能是刚切换的）
    current_model = get_current_model()
    
    # 第3步：构建返回结果
    result = {
        'model_id': current_model,
        'model_name': get_model_display_name(current_model),
        'switched': switched,
        'switch_message': switch_message,
        'clean_message': clean_message
    }
    
    # 构建选择原因
    if switched:
        result['reason'] = switch_message
    elif current_model != DEFAULT_MODEL:
        result['reason'] = f"持续模式：使用 {get_model_display_name(current_model)}"
    else:
        # 默认模式，进行自动检测
        auto_result = select_model_for_prompt(clean_message, has_link=has_link)
        result['model_id'] = auto_result['model_id']
        result['model_name'] = auto_result['model_name']
        result['reason'] = f"自动检测：{auto_result['reasoning']}"
    
    return result


def process_with_current_mode(user_message: str, has_link: bool = False) -> tuple[str, str, bool]:
    """
    处理用户消息，返回应使用的模型和清理后的消息
    
    Returns:
        (model_id, clean_message, show_switch_message)
    """
    result = smart_model_select(user_message, has_link)
    
    # 如果是切换指令，返回切换提示
    if result['switched']:
        return result['model_id'], result['clean_message'], True
    
    return result['model_id'], result['clean_message'], False


if __name__ == "__main__":
    # 测试持续模式
    test_conversation = [
        "你好，介绍一下自己",
        "切换到MiniMax模式",
        "帮我写个快速排序算法",
        "再写一个二分查找",
        "分析一下这个代码的复杂度",
        "切换回默认模型",
        "深入讨论一下算法优化",
    ]
    
    print("=== 持续模式测试 ===\n")
    
    for msg in test_conversation:
        result = smart_model_select(msg)
        
        print(f"用户: {msg}")
        
        if result['switched']:
            print(f"系统: {result['switch_message']}")
        
        print(f"模型: {result['model_name']}")
        print(f"原因: {result['reason']}")
        
        if result['clean_message'] and result['clean_message'] != msg:
            print(f"处理: {result['clean_message']}")
        
        print()
