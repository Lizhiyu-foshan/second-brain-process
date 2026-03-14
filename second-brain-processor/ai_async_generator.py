#!/usr/bin/env python3
"""
异步AI改进方案生成器

后台调用GLM5生成改进方案，完成后通知或记录结果。
"""

import os
import sys
import json
import re
import time
import urllib.request
import ssl
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# 从统一配置导入
try:
    from config import (
        ALICLOUD_API_KEY,
        ALICLOUD_BASE_URL,
        ALICLOUD_MODEL_CHAT_COMPLEX,
        ERRORS_FILE,
        AI_PENDING_FILE,
        AI_RESULTS_FILE,
        validate_api_key
    )
    # 统一使用Kimi K2.5模型
    ALICLOUD_MODEL_FAST = ALICLOUD_MODEL_CHAT_COMPLEX
    ALICLOUD_MODEL_COMPLEX = ALICLOUD_MODEL_CHAT_COMPLEX
except ImportError:
    # 降级处理
    ALICLOUD_API_KEY = os.environ.get('ALICLOUD_API_KEY', '')
    ALICLOUD_BASE_URL = os.environ.get('ALICLOUD_BASE_URL', 'https://coding.dashscope.aliyuncs.com/v1')
    # 统一使用Kimi K2.5模型
    ALICLOUD_MODEL_FAST = 'kimi-2.5'
    ALICLOUD_MODEL_COMPLEX = 'kimi-2.5'
    WORKSPACE = Path("/root/.openclaw/workspace")
    ERRORS_FILE = WORKSPACE / ".learnings" / "ERRORS.md"
    AI_PENDING_FILE = WORKSPACE / ".learnings" / "AI_PENDING.json"
    AI_RESULTS_FILE = WORKSPACE / ".learnings" / "AI_RESULTS.json"
    
    def validate_api_key() -> str:
        key = ALICLOUD_API_KEY.strip()
        if not key:
            raise ValueError("❌ ALICLOUD_API_KEY 未配置")
        return key


def create_ssl_context():
    """创建安全的SSL上下文"""
    # 使用系统默认的SSL配置，不禁用证书验证
    return ssl.create_default_context()


def log(message: str):
    """打印带时间戳的日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")


def select_model_by_task(task_type: str) -> str:
    """
    根据任务类型选择模型
    
    Args:
        task_type: 任务类型 - 'fast'(快速编码/修复) 或 'complex'(复杂任务/review)
    
    Returns:
        模型名称
    """
    if task_type == 'fast':
        return ALICLOUD_MODEL_FAST      # MiniMax M2.5 - 快速、高吞吐量
    else:
        return ALICLOUD_MODEL_COMPLEX   # GLM-5 - 复杂任务、架构设计


def call_ai_async(prompt: str, task_type: str = 'complex', timeout: int = 300) -> Optional[Dict]:
    """
    异步调用AI模型（支持双模型策略）
    
    Args:
        prompt: 提示词
        task_type: 任务类型 - 'fast'(快速编码/修复) 或 'complex'(复杂任务/review)
        timeout: 超时时间（秒），默认5分钟
    
    Returns:
        API响应或None
    """
    # 验证API Key
    try:
        api_key = validate_api_key()
    except ValueError as e:
        log(str(e))
        return None
    
    # 选择模型
    model = select_model_by_task(task_type)
    model_name = "MiniMax M2.5" if task_type == 'fast' else "GLM-5"
    
    try:
        url = f"{ALICLOUD_BASE_URL}/chat/completions"
        
        # 根据任务类型调整系统提示词
        if task_type == 'fast':
            system_prompt = "你是资深代码修复专家，专注快速定位问题、高效生成修复代码，注重代码简洁性和执行效率。"
        else:
            system_prompt = "你是资深软件架构师，专注复杂代码设计、架构优化、边界条件处理和代码review，注重代码质量和可维护性。"
        
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 3000
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            },
            method='POST'
        )
        
        # 使用安全的SSL上下文
        ssl_context = create_ssl_context()
        
        log(f"🤖 调用{model_name}生成改进方案（任务类型: {task_type}, 最长等待{timeout}秒）...")
        start_time = time.time()
        
        with urllib.request.urlopen(req, context=ssl_context, timeout=timeout) as response:
            result = json.loads(response.read().decode('utf-8'))
            elapsed = time.time() - start_time
            log(f"✅ {model_name}响应完成（耗时{elapsed:.1f}秒）")
            return result
            
    except urllib.error.URLError as e:
        log(f"❌ 网络请求失败: {e}")
        return None
    except json.JSONDecodeError as e:
        log(f"❌ JSON解析失败: {e}")
        return None
    except Exception as e:
        log(f"❌ {model_name}调用失败: {type(e).__name__}: {e}")
        return None


def get_recent_errors(hours: int = 24) -> List[Dict]:
    """获取最近N小时的错误记录"""
    if not ERRORS_FILE.exists():
        return []
    
    try:
        content = ERRORS_FILE.read_text(encoding='utf-8')
        from datetime import timezone
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        error_pattern = r'## \[(ERR-\d{8}-\d+)\] (.+?)\n.*?\*\*Logged\*\*: ([^\n]+)'
        matches = re.findall(error_pattern, content, re.DOTALL)
        
        errors = []
        for match in matches:
            error_id, title, time_str = match
            try:
                log_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                if log_time > cutoff_time:
                    errors.append({
                        'id': error_id,
                        'title': title,
                        'time': log_time
                    })
            except:
                continue
        
        return sorted(errors, key=lambda x: x['time'], reverse=True)
    except Exception as e:
        log(f"读取错误日志失败: {e}")
        return []


def analyze_error(error: Dict) -> Dict:
    """分析错误并确定任务类型"""
    title = error['title'].lower()
    
    patterns = {
        'git_push_timeout': {
            'root_cause': 'GitHub网络连接不稳定或超时时间过短',
            'affected_files': ['kimiclaw_v2.py'],
            'task_type': 'fast'  # MiniMax M2.5 - 快速修复
        },
        'file_not_found': {
            'root_cause': '文件路径错误或文件被删除',
            'affected_files': ['*.py'],
            'task_type': 'fast'  # MiniMax M2.5 - 快速修复
        },
        'rate_limit': {
            'root_cause': 'API调用频率超过限制',
            'affected_files': ['*.py'],
            'task_type': 'fast'  # MiniMax M2.5 - 业务流程优化
        },
        'json_decode': {
            'root_cause': 'JSON格式错误或编码问题',
            'affected_files': ['*.py'],
            'task_type': 'fast'  # MiniMax M2.5 - 快速修复
        },
        'memory_limit': {
            'root_cause': '内存不足或文件过大',
            'affected_files': ['processor.py', 'kimiclaw_v2.py'],
            'task_type': 'complex'  # GLM-5 - 复杂架构优化
        },
        'architecture_issue': {
            'root_cause': '架构设计问题',
            'affected_files': ['*.py'],
            'task_type': 'complex'  # GLM-5 - 架构设计
        }
    }
    
    for pattern_name, info in patterns.items():
        if pattern_name in title:
            return {
                'pattern': pattern_name,
                'root_cause': info['root_cause'],
                'affected_files': info['affected_files'],
                'task_type': info['task_type']
            }
    
    # 默认根据描述判断
    details = error.get('details', '').lower()
    if any(kw in details for kw in ['架构', 'design', 'refactor', '重构', '边界']):
        return {
            'pattern': 'complex_issue',
            'root_cause': f'复杂问题: {error["title"]}',
            'affected_files': ['*.py'],
            'task_type': 'complex'  # GLM-5
        }
    
    return {
        'pattern': 'unknown',
        'root_cause': f'未知错误: {error["title"]}',
        'affected_files': ['*.py'],
        'task_type': 'fast'  # 默认使用MiniMax快速处理
    }


def read_file_content(file_path: Path, max_lines: int = 100) -> str:
    """读取文件内容"""
    if not file_path.exists():
        return ""
    
    try:
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        if len(lines) > max_lines:
            return '\n'.join(lines[:max_lines]) + f"\n... ({len(lines) - max_lines} more lines)"
        return content
    except:
        return ""


def generate_glm5_prompt(error_analysis: Dict) -> str:
    """生成GLM5提示词"""
    # 读取受影响文件
    file_contents = {}
    for pattern in error_analysis.get('affected_files', ['*.py']):
        if pattern == '*.py':
            for py_file in PROCESSOR_DIR.glob('*.py'):
                if py_file.name not in ['system_evolution_v2.py', 'system_evolution_ai.py']:
                    file_contents[py_file.name] = read_file_content(py_file, 80)
        else:
            file_path = PROCESSOR_DIR / pattern
            if file_path.exists():
                file_contents[pattern] = read_file_content(file_path, 100)
    
    prompt = f"""分析以下错误并生成代码改进方案。

错误类型: {error_analysis['pattern']}
根因: {error_analysis['root_cause']}

相关文件:
"""
    for filename, content in file_contents.items():
        if content:
            prompt += f"\n=== {filename} ===\n{content}\n"
    
    prompt += """
请生成1-2个具体的代码改进方案。每个方案包含:
1. file: 文件名
2. description: 改进描述  
3. old_code: 要替换的原始代码（必须精确匹配）
4. new_code: 新代码

输出严格JSON格式:
{"reasoning": "分析过程", "improvements": [{"file": "", "description": "", "old_code": "", "new_code": ""}]}
"""
    
    return prompt


def parse_glm5_response(response: Dict) -> Optional[Dict]:
    """解析GLM5响应"""
    try:
        if not response or 'choices' not in response:
            return None
        
        content = response['choices'][0]['message']['content']
        
        # 提取JSON
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        
        return None
    except Exception as e:
        log(f"解析响应失败: {e}")
        return None


def save_ai_result(error_id: str, error_pattern: str, result: Dict):
    """保存AI生成结果"""
    try:
        results = {}
        if AI_RESULTS_FILE.exists():
            with open(AI_RESULTS_FILE, 'r') as f:
                results = json.load(f)
        
        results[error_id] = {
            'error_pattern': error_pattern,
            'timestamp': datetime.now().isoformat(),
            'result': result
        }
        
        with open(AI_RESULTS_FILE, 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        log(f"✅ AI结果已保存: {error_id}")
    except Exception as e:
        log(f"❌ 保存结果失败: {e}")


def process_pending_ai_tasks():
    """处理待处理的AI任务"""
    log("=== 开始异步AI改进生成（双模型策略） ===")
    
    # 获取最近错误
    errors = get_recent_errors(24)
    if not errors:
        log("无错误需要处理")
        return
    
    # 处理最新错误
    latest_error = errors[0]
    log(f"处理错误: {latest_error['id']} - {latest_error['title']}")
    
    # 分析错误（包含任务类型）
    analysis = analyze_error(latest_error)
    task_type = analysis.get('task_type', 'complex')
    
    model_name = "MiniMax M2.5" if task_type == 'fast' else "GLM-5"
    log(f"错误模式: {analysis['pattern']}")
    log(f"任务类型: {task_type} -> 使用{model_name}")
    
    # 生成提示词
    prompt = generate_glm5_prompt(analysis)
    log(f"提示词长度: {len(prompt)} 字符")
    
    # 调用AI（根据任务类型选择模型）
    response = call_ai_async(prompt, task_type=task_type, timeout=300)
    
    if response:
        # 解析响应
        result = parse_glm5_response(response)
        if result:
            log(f"✅ 成功生成改进方案（使用{model_name}）")
            if 'reasoning' in result:
                log(f"🧠 AI推理: {result['reasoning'][:100]}...")
            if 'improvements' in result:
                log(f"📝 改进项数: {len(result['improvements'])}")
            
            # 保存结果
            save_ai_result(latest_error['id'], analysis['pattern'], result)
        else:
            log("❌ 无法解析AI响应")
    else:
        log(f"❌ {model_name}调用失败")
    
    log("=== 异步AI改进生成完成 ===")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--process":
        process_pending_ai_tasks()
    else:
        print("用法: python3 ai_async_generator.py --process")
