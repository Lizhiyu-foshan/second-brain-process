#!/usr/bin/env python3
"""
模型会话状态管理器

实现持续模式功能：
- 切换到指定模型后，后续对话持续使用该模型
- 直到明确切换回默认模型
"""

import os
import json
import fcntl
import threading
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

# 从统一配置导入
try:
    from config import MODEL_STATE_FILE, ensure_directories, MODEL_MAPPING, DEFAULT_MODEL
except ImportError:
    # 降级处理
    WORKSPACE = Path("/root/.openclaw/workspace")
    MODEL_STATE_FILE = WORKSPACE / ".learnings" / "model_session_state.json"
    DEFAULT_MODEL = "kimi-coding/k2p5"
    MODEL_MAPPING = {
        "minimax": "alicloud/MiniMax-M2.5",
        "MiniMax": "alicloud/MiniMax-M2.5",
        "glm": "alicloud/glm-5",
        "GLM": "alicloud/glm-5",
        "glm-5": "alicloud/glm-5",
        "qwen": "alicloud/qwen3.5-plus",
        "Qwen": "alicloud/qwen3.5-plus",
        "qwen3.5-plus": "alicloud/qwen3.5-plus",
        "通义": "alicloud/qwen3.5-plus",
        "kimi": "kimi-coding/k2p5",
        "Kimi": "kimi-coding/k2p5",
        "kimi-2.5": "kimi-coding/k2p5",
        "default": "kimi-coding/k2p5",
        "默认": "kimi-coding/k2p5",
    }
    def ensure_directories():
        MODEL_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

# 状态文件路径
STATE_FILE = MODEL_STATE_FILE

# 线程锁（用于多线程环境）
_state_lock = threading.Lock()

# 模型映射
MODEL_MAPPING = {
    "minimax": "alicloud/MiniMax-M2.5",
    "MiniMax": "alicloud/MiniMax-M2.5",
    "glm": "alicloud/glm-5",
    "GLM": "alicloud/glm-5",
    "glm-5": "alicloud/glm-5",
    "qwen": "alicloud/qwen3.5-plus",
    "Qwen": "alicloud/qwen3.5-plus",
    "qwen3.5-plus": "alicloud/qwen3.5-plus",
    "通义": "alicloud/qwen3.5-plus",
    "kimi": "kimi-coding/k2p5",
    "Kimi": "kimi-coding/k2p5",
    "kimi-2.5": "kimi-coding/k2p5",
    "default": DEFAULT_MODEL,
    "默认": DEFAULT_MODEL,
}


def load_session_state() -> Dict:
    """加载会话状态（带文件锁，支持并发）"""
    if not STATE_FILE.exists():
        return {
            "current_model": DEFAULT_MODEL,
            "switched_at": None,
            "reason": None
        }
    
    # 获取线程锁
    with _state_lock:
        lock_file = STATE_FILE.with_suffix('.lock')
        try:
            # 创建锁文件
            with open(lock_file, 'w') as lock:
                try:
                    # 获取共享锁（读锁）
                    fcntl.flock(lock.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
                except (IOError, OSError):
                    # 如果无法获取非阻塞锁，使用阻塞锁
                    fcntl.flock(lock.fileno(), fcntl.LOCK_SH)
                
                # 读取状态文件
                try:
                    with open(STATE_FILE, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except json.JSONDecodeError as e:
                    print(f"⚠️ 状态文件JSON解析失败: {e}，使用默认状态")
                    return {
                        "current_model": DEFAULT_MODEL,
                        "switched_at": None,
                        "reason": None
                    }
                except IOError as e:
                    print(f"⚠️ 状态文件读取失败: {e}，使用默认状态")
                    return {
                        "current_model": DEFAULT_MODEL,
                        "switched_at": None,
                        "reason": None
                    }
        except Exception as e:
            print(f"⚠️ 获取文件锁失败: {e}，使用默认状态")
            return {
                "current_model": DEFAULT_MODEL,
                "switched_at": None,
                "reason": None
            }


def save_session_state(state: Dict):
    """保存会话状态（带文件锁，支持并发）"""
    ensure_directories()
    
    # 获取线程锁
    with _state_lock:
        lock_file = STATE_FILE.with_suffix('.lock')
        try:
            with open(lock_file, 'w') as lock:
                try:
                    # 获取独占锁（写锁）
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except (IOError, OSError):
                    # 如果无法获取非阻塞锁，使用阻塞锁
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                
                # 写入状态文件（原子操作）
                temp_file = STATE_FILE.with_suffix('.tmp')
                try:
                    with open(temp_file, 'w', encoding='utf-8') as f:
                        json.dump(state, f, indent=2, ensure_ascii=False)
                    # 原子重命名
                    temp_file.replace(STATE_FILE)
                except IOError as e:
                    print(f"⚠️ 保存状态失败: {e}")
                    # 清理临时文件
                    if temp_file.exists():
                        temp_file.unlink()
        except Exception as e:
            print(f"⚠️ 获取文件锁失败: {e}")


def detect_mode_switch(message: str) -> tuple[bool, Optional[str], Optional[str]]:
    """
    检测是否包含模式切换指令
    
    Returns:
        (是否切换, 目标模型, 原因)
    """
    message_lower = message.lower()
    
    # 切换到默认模型
    if any(kw in message for kw in ["切换回默认", "切换回kimi", "使用默认", "用默认", "回到默认"]):
        return True, DEFAULT_MODEL, "用户切换回默认模型"
    
    # 检测切换指令
    switch_patterns = ["切换到", "使用", "用", "切换为", "换成", "转换到", "转换成"]
    
    for pattern in switch_patterns:
        if pattern in message:
            # 提取模型名称
            for model_name, model_id in MODEL_MAPPING.items():
                if model_name in message:
                    return True, model_id, f"用户切换到 {model_name}"
    
    return False, None, None


def get_current_model() -> str:
    """获取当前模型"""
    state = load_session_state()
    return state.get("current_model", DEFAULT_MODEL)


def switch_model(model_id: str, reason: str = "") -> str:
    """
    切换模型
    
    Returns:
        切换结果消息
    """
    state = {
        "current_model": model_id,
        "switched_at": datetime.now().isoformat(),
        "reason": reason
    }
    save_session_state(state)
    
    # 获取模型友好名称
    model_names = {
        "alicloud/MiniMax-M2.5": "MiniMax M2.5 (快速编码)",
        "alicloud/glm-5": "GLM-5 (复杂编码/架构)",
        "alicloud/qwen3.5-plus": "Qwen 3.5 Plus (快速对话)",
        "kimi-coding/k2p5": "Kimi 2.5 (深度思考)"
    }
    
    model_name = model_names.get(model_id, model_id)
    
    return f"✅ 已切换至 **{model_name}** 模式\n\n后续对话将使用该模型，直到你切换回默认模型。"


def reset_to_default() -> str:
    """重置为默认模型"""
    state = {
        "current_model": DEFAULT_MODEL,
        "switched_at": datetime.now().isoformat(),
        "reason": "用户重置为默认模型"
    }
    save_session_state(state)
    return "✅ 已切换回 **默认模型 (Kimi 2.5)**"


def process_message_with_mode(message: str) -> tuple[str, bool, str]:
    """
    处理消息，检测模式切换
    
    Returns:
        (处理后的消息, 是否切换了模式, 切换结果消息)
    """
    is_switch, target_model, reason = detect_mode_switch(message)
    
    if is_switch:
        if target_model == DEFAULT_MODEL:
            result = reset_to_default()
        else:
            result = switch_model(target_model, reason)
        
        # 返回清空后的消息（移除切换指令）
        clean_message = message
        for pattern in ["切换到", "使用", "用", "切换为", "换成", "切换回"]:
            clean_message = clean_message.replace(pattern, "")
        for model_name in MODEL_MAPPING.keys():
            clean_message = clean_message.replace(model_name, "")
        
        return clean_message.strip(), True, result
    
    # 没有切换指令，返回原消息
    return message, False, ""


def get_model_display_name(model_id: str) -> str:
    """获取模型的显示名称"""
    names = {
        "alicloud/MiniMax-M2.5": "MiniMax M2.5",
        "alicloud/glm-5": "GLM-5",
        "alicloud/qwen3.5-plus": "Qwen 3.5 Plus",
        "kimi-coding/k2p5": "Kimi 2.5"
    }
    return names.get(model_id, model_id)


if __name__ == "__main__":
    # 测试
    test_messages = [
        "切换到MiniMax模式",
        "用GLM分析这个架构",
        "使用Qwen快速回答",
        "切换到Kimi深度讨论",
        "切换回默认模型",
        "这是一个普通消息"
    ]
    
    print("=== 模式切换测试 ===\n")
    
    for msg in test_messages:
        clean_msg, switched, result = process_message_with_mode(msg)
        if switched:
            print(f"输入: {msg}")
            print(f"{result}")
            print(f"清理后消息: {clean_msg}")
            print(f"当前模型: {get_current_model()}")
            print()
        else:
            print(f"输入: {msg}")
            print(f"无切换，当前模型: {get_current_model()}")
            print()
