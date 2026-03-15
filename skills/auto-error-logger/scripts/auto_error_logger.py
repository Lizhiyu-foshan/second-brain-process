#!/usr/bin/env python3
"""
自动错误捕获与记录模块

提供装饰器和上下文管理器，自动捕获错误并写入 .learnings/ERRORS.md

使用方式：
1. 作为装饰器：
   @catch_errors(context="api_call")
   def my_function():
       ...

2. 作为上下文管理器：
   with error_context("database_query"):
       ...

3. 手动记录：
   log_error(exception, context="operation", metadata={...})
"""

import os
import sys
import json
import traceback
from datetime import datetime
from pathlib import Path
from functools import wraps
from typing import Optional, Dict, Any, Callable

# 配置
WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE", "/root/.openclaw/workspace"))
ERRORS_FILE = WORKSPACE / ".learnings" / "ERRORS.md"
LEARNINGS_DIR = WORKSPACE / ".learnings"

# 确保目录存在
LEARNINGS_DIR.mkdir(parents=True, exist_ok=True)

# 错误ID计数器
_error_counter = 0


def generate_error_id() -> str:
    """生成唯一错误ID"""
    global _error_counter
    _error_counter += 1
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"ERR-{timestamp}-{_error_counter:04d}"


def log_error(
    exception: Exception,
    context: str = "unknown",
    metadata: Optional[Dict[str, Any]] = None,
    notify: bool = False,
    retry_count: int = 0
) -> str:
    """
    记录错误到 ERRORS.md
    
    Args:
        exception: 异常对象
        context: 操作上下文/描述
        metadata: 额外的元数据
        notify: 是否需要通知用户
        retry_count: 已重试次数
    
    Returns:
        error_id: 生成的错误ID
    """
    error_id = generate_error_id()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 获取异常信息
    error_type = type(exception).__name__
    error_message = str(exception)
    
    # 获取调用栈
    tb_lines = traceback.format_exception(type(exception), exception, exception.__traceback__)
    stack_trace = "".join(tb_lines[-5:])  # 只保留最后5行
    
    # 格式化元数据
    metadata_str = ""
    if metadata:
        try:
            metadata_str = json.dumps(metadata, ensure_ascii=False, indent=2)
        except:
            metadata_str = str(metadata)
    
    # 构建错误记录
    error_entry = f"""
## {error_id}
- **时间**: {timestamp}
- **操作**: {context}
- **错误类型**: {error_type}
- **错误信息**: {error_message}
- **状态**: pending
- **重试次数**: {retry_count}
"""
    
    if metadata:
        error_entry += f"- **上下文数据**:\n```\n{metadata_str}\n```\n"
    
    if stack_trace:
        error_entry += f"- **调用栈**:\n```\n{stack_trace}\n```\n"
    
    if notify:
        error_entry += f"- **需要通知**: 是\n"
    
    error_entry += "\n---\n"
    
    # 写入文件
    try:
        # 如果文件不存在，创建并添加头部
        if not ERRORS_FILE.exists():
            header = "# ERRORS.md\n\n系统错误自动记录文件。此文件由 auto-error-logger 自动维护。\n\n---\n"
            ERRORS_FILE.write_text(header, encoding="utf-8")
        
        # 追加错误记录
        with open(ERRORS_FILE, "a", encoding="utf-8") as f:
            f.write(error_entry)
        
        print(f"[auto-error-logger] 错误已记录: {error_id} ({error_type}: {error_message})")
        
    except Exception as e:
        print(f"[auto-error-logger] 无法写入错误文件: {e}")
        # 如果连写入都失败了，至少打印到控制台
        print(error_entry)
    
    return error_id


def catch_errors(
    context: str = "unknown",
    metadata: Optional[Dict[str, Any]] = None,
    notify: bool = False,
    retry: int = 0,
    retry_delay: float = 1.0,
    on_error: Optional[Callable] = None
) -> Callable:
    """
    错误捕获装饰器
    
    Args:
        context: 操作上下文/描述
        metadata: 额外的元数据
        notify: 是否需要通知用户
        retry: 重试次数
        retry_delay: 重试间隔（秒）
        on_error: 错误回调函数
    
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            retry_count = 0
            
            for attempt in range(retry + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    retry_count = attempt
                    
                    if attempt < retry:
                        import time
                        time.sleep(retry_delay)
                        print(f"[auto-error-logger] 重试 {attempt + 1}/{retry}...")
                    else:
                        # 最后一次尝试失败，记录错误
                        error_id = log_error(
                            exception=e,
                            context=context,
                            metadata=metadata,
                            notify=notify,
                            retry_count=retry_count
                        )
                        
                        # 调用错误回调
                        if on_error:
                            try:
                                on_error(e, error_id, context)
                            except Exception as callback_error:
                                print(f"[auto-error-logger] 错误回调失败: {callback_error}")
                        
                        # 重新抛出异常
                        raise
            
            # 理论上不应该到达这里
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


class error_context:
    """
    错误捕获上下文管理器
    
    使用方式：
        with error_context("database_query"):
            # 数据库操作
            pass
    """
    
    def __init__(
        self,
        context: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None,
        notify: bool = False,
        reraise: bool = True
    ):
        self.context = context
        self.metadata = metadata
        self.notify = notify
        self.reraise = reraise
        self.error_id = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            # 有异常发生
            self.error_id = log_error(
                exception=exc_val,
                context=self.context,
                metadata=self.metadata,
                notify=self.notify
            )
            
            if self.reraise:
                return False  # 重新抛出异常
            else:
                return True   # 抑制异常


def analyze_error_patterns(days: int = 7) -> Dict[str, Any]:
    """
    分析错误模式
    
    Args:
        days: 分析最近几天的错误
    
    Returns:
        错误模式分析结果
    """
    if not ERRORS_FILE.exists():
        return {"status": "no_errors", "message": "没有错误记录"}
    
    content = ERRORS_FILE.read_text(encoding="utf-8")
    
    # 简单分析：统计错误类型
    error_types = {}
    error_contexts = {}
    
    import re
    
    # 提取错误类型
    type_pattern = r"\*\*错误类型\*\*:\s*(\w+)"
    for match in re.finditer(type_pattern, content):
        error_type = match.group(1)
        error_types[error_type] = error_types.get(error_type, 0) + 1
    
    # 提取操作上下文
    context_pattern = r"\*\*操作\*\*:\s*(.+)"
    for match in re.finditer(context_pattern, content):
        ctx = match.group(1)
        error_contexts[ctx] = error_contexts.get(ctx, 0) + 1
    
    return {
        "status": "analyzed",
        "total_types": len(error_types),
        "error_types": error_types,
        "error_contexts": error_contexts,
        "recommendations": [
            f"关注高频错误类型: {t}" for t, c in sorted(error_types.items(), key=lambda x: -x[1])[:3]
        ]
    }


# 测试代码
if __name__ == "__main__":
    print("=== 测试 auto-error-logger ===\n")
    
    # 测试1：装饰器
    @catch_errors(context="test_function", notify=True, retry=2, retry_delay=0.5)
    def test_function(should_fail=True):
        if should_fail:
            raise ValueError("测试错误")
        return "success"
    
    print("\n1. 测试装饰器（带重试）:")
    try:
        result = test_function(should_fail=True)
    except ValueError:
        print("   错误被正确捕获并重新抛出")
    
    # 测试2：上下文管理器
    print("\n2. 测试上下文管理器:")
    with error_context("test_context", metadata={"key": "value"}):
        pass  # 没有错误
    
    print("   无错误的情况正常")
    
    # 测试3：手动记录
    print("\n3. 测试手动记录:")
    try:
        raise ConnectionError("测试连接错误")
    except Exception as e:
        error_id = log_error(e, context="manual_test", metadata={"url": "https://example.com"})
        print(f"   错误ID: {error_id}")
    
    # 测试4：错误模式分析
    print("\n4. 测试错误模式分析:")
    analysis = analyze_error_patterns()
    print(f"   状态: {analysis['status']}")
    if 'error_types' in analysis:
        print(f"   错误类型: {analysis['error_types']}")
    
    print("\n=== 测试完成 ===")
    print(f"错误记录文件: {ERRORS_FILE}")