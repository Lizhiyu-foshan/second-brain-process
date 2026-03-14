#!/usr/bin/env python3
"""
AI驱动的代码改进方案生成器

用AI分析错误并生成具体的代码改进方案，替代硬编码的改进逻辑。
"""

import os
import re
import ast
import json
import subprocess
import urllib.request
import ssl
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

# 从统一配置导入
try:
    from config import (
        ALICLOUD_API_KEY,
        ALICLOUD_BASE_URL,
        ALICLOUD_MODEL_FAST,
        ALICLOUD_MODEL_COMPLEX,
        ALICLOUD_MODEL_CHAT_FAST,
        ALICLOUD_MODEL_CHAT_COMPLEX,
        ERRORS_FILE,
        EVOLUTION_LOG,
        validate_api_key
    )
except ImportError:
    # 降级处理
    ALICLOUD_API_KEY = os.environ.get('ALICLOUD_API_KEY', '')
    ALICLOUD_BASE_URL = os.environ.get('ALICLOUD_BASE_URL', 'https://coding.dashscope.aliyuncs.com/v1')
    ALICLOUD_MODEL_FAST = os.environ.get('ALICLOUD_MODEL_FAST', 'MiniMax-M2.5')
    ALICLOUD_MODEL_COMPLEX = os.environ.get('ALICLOUD_MODEL_COMPLEX', 'glm-5')
    ALICLOUD_MODEL_CHAT_FAST = os.environ.get('ALICLOUD_MODEL_CHAT_FAST', 'qwen3.5-plus')
    ALICLOUD_MODEL_CHAT_COMPLEX = os.environ.get('ALICLOUD_MODEL_CHAT_COMPLEX', 'kimi-k2.5')
    WORKSPACE = Path("/root/.openclaw/workspace")
    ERRORS_FILE = WORKSPACE / ".learnings" / "ERRORS.md"
    EVOLUTION_LOG = WORKSPACE / ".learnings" / "EVOLUTION_LOG.md"
    
    def validate_api_key() -> str:
        key = ALICLOUD_API_KEY.strip()
        if not key:
            raise ValueError("ALICLOUD_API_KEY 未配置")
        return key


def create_ssl_context():
    """创建安全的SSL上下文"""
    return ssl.create_default_context()

# 工作目录
WORKSPACE = Path("/root/.openclaw/workspace")
PROCESSOR_DIR = WORKSPACE / "second-brain-processor"

# 配置
ERROR_RETENTION_DAYS = 30
MAX_DAILY_IMPROVEMENTS = 2  # 每天最多改进次数


def log(message: str):
    """打印带时间戳的日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")


def call_aliyun_ai(prompt: str, model: str = None) -> Optional[Dict]:
    """
    调用阿里云Coding Plan API
    
    Args:
        prompt: 提示词
        model: 模型名称，默认使用ALICLOUD_MODEL_CHAT_COMPLEX (Kimi K2.5)
    
    Returns:
        API响应的JSON数据
    """
    # 验证API Key
    try:
        api_key = validate_api_key()
    except ValueError:
        log("❌ 阿里云API Key未配置，请在 .env 文件中设置 ALICLOUD_API_KEY")
        return None
    
    # 统一使用Kimi K2.5模型
    model = model or ALICLOUD_MODEL_CHAT_COMPLEX
    
    try:
        url = f"{ALICLOUD_BASE_URL}/chat/completions"
        
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": "你是一个代码改进专家，分析错误并生成具体的Python代码改进方案。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 4000
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
        
        with urllib.request.urlopen(req, context=ssl_context, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result
            
    except urllib.error.HTTPError as e:
        log(f"❌ API请求失败 (HTTP {e.code}): {e.reason}")
        return None
    except urllib.error.URLError as e:
        log(f"❌ 网络连接失败: {e.reason}")
        return None
    except json.JSONDecodeError as e:
        log(f"❌ 响应解析失败: {e}")
        return None
    except Exception as e:
        log(f"❌ 阿里云API调用失败: {type(e).__name__}: {e}")
        return None


def parse_ai_improvements(ai_response: Dict) -> List[Dict]:
    """
    解析AI响应，提取改进方案
    
    Args:
        ai_response: API返回的JSON
    
    Returns:
        改进方案列表
    """
    try:
        if not ai_response or 'choices' not in ai_response:
            return []
        
        content = ai_response['choices'][0]['message']['content']
        
        # 尝试从响应中提取JSON
        # 查找代码块中的JSON
        json_match = re.search(r'```json\s*(\{.*?)\s*```', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试直接解析整个内容
            json_str = content
        
        data = json.loads(json_str)
        
        improvements = []
        if 'improvements' in data:
            for imp in data['improvements']:
                improvements.append({
                    'file': imp.get('file', ''),
                    'description': imp.get('description', ''),
                    'old_code': imp.get('old_code', ''),
                    'new_code': imp.get('new_code', '')
                })
        
        return improvements
        
    except Exception as e:
        log(f"❌ 解析AI响应失败: {e}")
        return []


# ═══════════════════════════════════════════════════════════════
# 第一部分：错误收集和分析
# ═══════════════════════════════════════════════════════════════

def get_recent_errors(hours: int = 24) -> List[Dict]:
    """获取最近N小时的错误记录"""
    if not ERRORS_FILE.exists():
        return []
    
    try:
        content = ERRORS_FILE.read_text(encoding='utf-8')
        from datetime import timezone
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # 解析错误记录
        error_pattern = r'## \[(ERR-\d{8}-\d+)\] (.+?)\n.*?\*\*Logged\*\*: ([^\n]+)'
        matches = re.findall(error_pattern, content, re.DOTALL)
        
        errors = []
        for match in matches:
            error_id, title, time_str = match
            try:
                log_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                if log_time > cutoff_time:
                    # 提取详细信息
                    error_block = re.search(
                        rf'## \[{error_id}\].+?(?=## \[ERR-|\Z)', 
                        content, re.DOTALL
                    )
                    details = error_block.group(0) if error_block else ""
                    
                    errors.append({
                        'id': error_id,
                        'title': title,
                        'time': log_time,
                        'details': details
                    })
            except:
                continue
        
        return sorted(errors, key=lambda x: x['time'], reverse=True)
    except Exception as e:
        log(f"读取错误日志失败: {e}")
        return []


def analyze_error_root_cause(error: Dict) -> Dict:
    """分析错误根因（增强版）"""
    title = error['title'].lower()
    details = error.get('details', '').lower()
    
    # 扩展的错误模式库
    patterns = {
        'git_push_timeout': {
            'keywords': ['push', 'timeout', '443', 'connection', 'github', 'port'],
            'root_cause': 'GitHub网络连接不稳定或超时时间过短',
            'affected_files': ['kimiclaw_v2.py', 'run_morning_process.sh'],
            'suggested_fixes': ['添加指数退避重试', '增加网络超时配置', '添加失败重试队列']
        },
        'git_auth_fail': {
            'keywords': ['auth', 'permission', 'denied', '403', '401', 'unauthorized'],
            'root_cause': 'Git认证失效或权限不足',
            'affected_files': ['kimiclaw_v2.py'],
            'suggested_fixes': ['检查认证令牌', '添加认证失败提示', '自动重新认证']
        },
        'file_not_found': {
            'keywords': ['no such file', 'not found', 'enoent', 'filenotfound'],
            'root_cause': '文件路径错误或文件被删除',
            'affected_files': ['processor.py', 'kimiclaw_v2.py'],
            'suggested_fixes': ['添加文件存在性检查', '自动创建缺失目录', '添加路径验证']
        },
        'file_permission': {
            'keywords': ['permission', 'denied', 'eacces', 'access'],
            'root_cause': '文件权限不足',
            'affected_files': ['*.py'],
            'suggested_fixes': ['检查并修复权限', '使用更安全的文件操作']
        },
        'json_decode': {
            'keywords': ['json', 'decode', 'parse', 'invalid', 'syntax'],
            'root_cause': 'JSON格式错误或编码问题',
            'affected_files': ['processor.py', '*.py'],
            'suggested_fixes': ['添加try-except处理', '验证JSON格式', '添加编码声明']
        },
        'api_validation': {
            'keywords': ['validation', 'api', 'request', 'schema', 'invalid'],
            'root_cause': 'API请求格式不符合要求',
            'affected_files': ['*.py'],
            'suggested_fixes': ['验证请求参数', '添加默认值', '增强错误提示']
        },
        'memory_limit': {
            'keywords': ['memory', 'oom', 'killed', 'allocation', 'exhausted'],
            'root_cause': '内存不足或文件过大',
            'affected_files': ['processor.py', 'kimiclaw_v2.py'],
            'suggested_fixes': ['使用流式读取', '添加文件大小限制', '优化内存使用']
        },
        'rate_limit': {
            'keywords': ['rate', 'limit', '429', 'too many', 'throttled'],
            'root_cause': 'API调用频率超过限制',
            'affected_files': ['*.py'],
            'suggested_fixes': ['添加速率限制', '实现指数退避', '添加重试队列']
        }
    }
    
    for pattern_name, pattern_info in patterns.items():
        if any(kw in title or kw in details for kw in pattern_info['keywords']):
            return {
                'pattern': pattern_name,
                'root_cause': pattern_info['root_cause'],
                'affected_files': pattern_info['affected_files'],
                'suggested_fixes': pattern_info['suggested_fixes'],
                'confidence': 'high'
            }
    
    # 无法识别时返回通用分析
    return {
        'pattern': 'unknown',
        'root_cause': f'未知错误: {error["title"]}',
        'affected_files': ['*.py'],
        'suggested_fixes': ['添加详细日志', '增强错误处理', '添加重试机制'],
        'confidence': 'low'
    }


# ═══════════════════════════════════════════════════════════════
# 第二部分：AI驱动的改进方案生成
# ═══════════════════════════════════════════════════════════════

@dataclass
class FileChange:
    """文件变更"""
    file_path: Path
    description: str
    old_code: str
    new_code: str
    
    def to_dict(self) -> Dict:
        return {
            'type': 'file_change',
            'file': self.file_path,
            'description': self.description,
            'old': self.old_code,
            'new': self.new_code
        }


@dataclass
class AIImprovementPlan:
    """AI生成的改进方案"""
    error_pattern: str
    root_cause: str
    improvements: List[FileChange] = field(default_factory=list)
    reasoning: str = ""  # AI的推理过程
    
    def add_improvement(self, file_path: Path, description: str, 
                       old_code: str, new_code: str):
        """添加改进项"""
        self.improvements.append(FileChange(file_path, description, old_code, new_code))


def read_file_content(file_path: Path, max_lines: int = 200) -> str:
    """读取文件内容（限制行数）"""
    if not file_path.exists():
        return f"[文件不存在: {file_path}]"
    
    try:
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        if len(lines) > max_lines:
            return '\n'.join(lines[:max_lines]) + f"\n... ({len(lines) - max_lines} more lines)"
        return content
    except Exception as e:
        return f"[读取失败: {e}]"


def find_code_context(file_path: Path, keyword: str, context_lines: int = 20) -> Optional[str]:
    """在文件中查找代码上下文"""
    if not file_path.exists():
        return None
    
    try:
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            if keyword in line:
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                return '\n'.join(lines[start:end])
        
        return None
    except Exception:
        return None


def generate_ai_prompt(error_analysis: Dict, affected_files: List[str]) -> str:
    """生成AI提示词"""
    # 读取受影响文件的内容
    file_contents = {}
    for pattern in affected_files:
        if pattern == '*.py':
            # 读取所有Python文件
            for py_file in PROCESSOR_DIR.glob('*.py'):
                if py_file.name != 'system_evolution_v2.py':  # 避免自引用
                    file_contents[py_file.name] = read_file_content(py_file, 100)
        else:
            file_path = PROCESSOR_DIR / pattern
            if file_path.exists():
                file_contents[pattern] = read_file_content(file_path, 150)
    
    # 构建提示词
    prompt = f"""你是一个代码改进专家。请分析以下错误并生成具体的代码改进方案。

## 错误信息
- 错误类型: {error_analysis['pattern']}
- 根因: {error_analysis['root_cause']}
- 置信度: {error_analysis['confidence']}

## 建议修复方向
{chr(10).join(f"- {fix}" for fix in error_analysis.get('suggested_fixes', []))}

## 相关文件内容
"""
    
    for filename, content in file_contents.items():
        prompt += f"\n### {filename}\n```python\n{content}\n```\n"
    
    prompt += """
## 任务
请生成1-3个具体的代码改进方案。每个方案必须包含:
1. 目标文件路径
2. 改进描述
3. 要替换的原始代码（必须完全匹配文件中的代码）
4. 新代码（必须是有效的Python代码）

## 输出格式
请以JSON格式返回，格式如下:
```json
{
  "reasoning": "你的分析和推理过程",
  "improvements": [
    {
      "file": "文件名.py",
      "description": "改进描述",
      "old_code": "原始代码片段（多行）",
      "new_code": "新代码片段（多行）"
    }
  ]
}
```

注意:
- old_code 必须完全匹配文件中的代码，包括空格和缩进
- new_code 必须是语法正确的Python代码
- 改进应该是具体的、可实施的
"""
    
    return prompt


def generate_improvement_plan_ai(error_analysis: Dict, errors: List[Dict]) -> Optional[AIImprovementPlan]:
    """
    使用AI生成改进方案（优先调用阿里云API，失败则回退到基于规则）
    """
    plan = AIImprovementPlan(
        error_pattern=error_analysis['pattern'],
        root_cause=error_analysis['root_cause']
    )
    
    # 首先尝试调用阿里云AI API - 使用GLM-5处理复杂任务
    log("🧠 尝试调用阿里云AI (GLM-5) 生成改进方案...")
    
    # 读取受影响文件
    affected_files = error_analysis.get('affected_files', ['*.py'])
    file_contents = {}
    for pattern in affected_files:
        if pattern == '*.py':
            for py_file in PROCESSOR_DIR.glob('*.py'):
                if py_file.name not in ['system_evolution_v2.py', 'system_evolution_ai.py']:
                    file_contents[py_file.name] = read_file_content(py_file, 100)
        else:
            file_path = PROCESSOR_DIR / pattern
            if file_path.exists():
                file_contents[pattern] = read_file_content(file_path, 150)
    
    # 构建提示词
    prompt = f"""你是一个代码改进专家。请分析以下错误并生成具体的代码改进方案。

## 错误信息
- 错误类型: {error_analysis['pattern']}
- 根因: {error_analysis['root_cause']}
- 置信度: {error_analysis['confidence']}
- 建议修复方向: {', '.join(error_analysis.get('suggested_fixes', []))}

## 相关文件内容
"""
    for filename, content in file_contents.items():
        prompt += f"\n### {filename}\n```python\n{content}\n```\n"
    
    prompt += """
## 任务
请生成1-3个具体的代码改进方案。每个方案必须包含:
1. 目标文件路径
2. 改进描述
3. 要替换的原始代码（必须完全匹配文件中的代码）
4. 新代码（必须是有效的Python代码）

## 输出格式
请以JSON格式返回，格式如下:
```json
{
  "reasoning": "你的分析和推理过程",
  "improvements": [
    {
      "file": "文件名.py",
      "description": "改进描述",
      "old_code": "原始代码片段（多行）",
      "new_code": "新代码片段（多行）"
    }
  ]
}
```

注意:
- old_code 必须完全匹配文件中的代码，包括空格和缩进
- new_code 必须是语法正确的Python代码
- 改进应该是具体的、可实施的
"""
    
    # 调用阿里云API - 使用GLM-5处理复杂任务
    ai_response = call_aliyun_ai(prompt, model=ALICLOUD_MODEL_COMPLEX)
    
    if ai_response:
        improvements = parse_ai_improvements(ai_response)
        if improvements:
            log(f"✅ GLM-5生成了 {len(improvements)} 个改进项")
            
            # 解析reasoning
            try:
                content = ai_response['choices'][0]['message']['content']
                json_match = re.search(r'```json\s*(\{.*?)\s*```', content, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(1))
                    plan.reasoning = data.get('reasoning', '阿里云AI生成改进方案')
            except:
                plan.reasoning = '阿里云AI生成改进方案'
            
            # 添加改进项
            for imp in improvements:
                file_path = PROCESSOR_DIR / imp['file']
                plan.add_improvement(
                    file_path,
                    imp['description'],
                    imp['old_code'],
                    imp['new_code']
                )
            
            return plan
        else:
            log("⚠️ GLM-5响应解析失败，回退到基于规则的生成")
    else:
        log("⚠️ GLM-5调用失败，回退到基于规则的生成")
    
    # 回退到基于规则的生成
    log("🔄 使用基于规则的改进生成...")
    return _generate_rule_based_improvements(error_analysis, plan)


def _generate_rule_based_improvements(error_analysis: Dict, plan: AIImprovementPlan) -> Optional[AIImprovementPlan]:
    """基于规则的改进生成（回退方案）"""
    
    if error_analysis['pattern'] == 'git_push_timeout':
        _generate_git_push_improvements(plan)
    elif error_analysis['pattern'] == 'file_not_found':
        _generate_file_check_improvements(plan)
    elif error_analysis['pattern'] == 'rate_limit':
        _generate_rate_limit_improvements(plan)
    elif error_analysis['pattern'] == 'json_decode':
        _generate_error_handling_improvements(plan)
    else:
        _generate_generic_improvements(plan)
    
    return plan if plan.improvements else None


def _generate_git_push_improvements(plan: AIImprovementPlan):
    """生成Git推送改进（智能版本）"""
    kimiclaw_file = PROCESSOR_DIR / "kimiclaw_v2.py"
    
    if not kimiclaw_file.exists():
        return
    
    # 读取实际文件内容，找到准确的代码片段
    content = kimiclaw_file.read_text(encoding='utf-8')
    
    # 改进1: 添加指数退避（使用实际代码）
    old_code = find_code_context(kimiclaw_file, "def commit_and_push")
    if old_code and "base_delay" not in content:  # 避免重复修改
        # 找到函数定义到try之间的代码
        match = re.search(
            r'(def commit_and_push\(message\):.*?max_retries = 3)(\s+for i in range\(max_retries\):\s+try:)',
            content, re.DOTALL
        )
        if match:
            old_section = match.group(1) + match.group(2)
            new_section = '''def commit_and_push(message):
    """提交并推送到GitHub，带重试和指数退避"""
    max_retries = 3
    base_delay = 2  # 基础延迟2秒
    
    for i in range(max_retries):
        try:
            # 每次重试增加延迟（指数退避）
            if i > 0:
                delay = base_delay * (2 ** i)
                log(f"第{i+1}次重试，等待{delay}秒...")
                time.sleep(delay)'''
            
            plan.add_improvement(
                kimiclaw_file,
                "增强Git推送重试逻辑，添加指数退避",
                old_section,
                new_section
            )
            plan.reasoning = "检测到GitHub推送超时错误，添加指数退避机制减少网络波动影响"


def _generate_file_check_improvements(plan: AIImprovementPlan):
    """生成文件检查改进"""
    # 为常见文件操作添加存在性检查
    for py_file in PROCESSOR_DIR.glob('*.py'):
        if py_file.name == 'system_evolution_v2.py':
            continue
        
        content = py_file.read_text(encoding='utf-8')
        
        # 查找 open(..., 'w') 但没有目录创建的情况
        if 'with open(' in content and '.parent.mkdir' not in content:
            # 找到第一个文件写入操作
            match = re.search(
                r'(with open\([^)]+, [\'"]w[\'"]\) as f:\s+f\.write)',
                content
            )
            if match:
                old_code = match.group(1)
                new_code = '''# 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            f.write'''
                
                plan.add_improvement(
                    py_file,
                    f"添加文件目录自动创建: {py_file.name}",
                    old_code,
                    new_code
                )
                plan.reasoning = "检测到文件不存在错误，添加目录自动创建机制"


def _generate_rate_limit_improvements(plan: AIImprovementPlan):
    """生成速率限制改进"""
    # 为API调用添加速率限制
    for py_file in PROCESSOR_DIR.glob('*.py'):
        if py_file.name == 'system_evolution_v2.py':
            continue
        
        content = py_file.read_text(encoding='utf-8')
        
        # 查找API调用但没有延迟的情况
        if 'requests.' in content or 'http' in content.lower():
            if 'time.sleep' not in content:
                plan.add_improvement(
                    py_file,
                    f"添加API调用速率限制: {py_file.name}",
                    "import ",
                    "import time\nimport "
                )
                plan.reasoning = "检测到API速率限制错误，建议添加延迟和重试机制"


def _generate_error_handling_improvements(plan: AIImprovementPlan):
    """生成错误处理改进"""
    for py_file in PROCESSOR_DIR.glob('*.py'):
        if py_file.name == 'system_evolution_v2.py':
            continue
        
        content = py_file.read_text(encoding='utf-8')
        
        # 查找JSON解析但没有try的情况
        if 'json.loads' in content:
            matches = list(re.finditer(r'(^\s+)(data = json\.loads\([^)]+\))', content, re.MULTILINE))
            if matches:
                for match in matches[:1]:  # 只处理第一个
                    indent = match.group(1)
                    old_code = match.group(2)
                    new_code = f"""{indent}try:
{indent}    data = json.loads(line)
{indent}except json.JSONDecodeError as e:
{indent}    log(f"[WARN] JSON解析失败，跳过: {{e}}")
{indent}    continue"""
                    
                    plan.add_improvement(
                        py_file,
                        f"增强JSON解析错误处理: {py_file.name}",
                        old_code,
                        new_code
                    )
                    plan.reasoning = "检测到JSON解析错误，添加异常处理"


def _generate_generic_improvements(plan: AIImprovementPlan):
    """生成通用改进"""
    plan.reasoning = "无法确定具体改进方案，建议添加日志和监控"


# ═══════════════════════════════════════════════════════════════
# 第三部分：改进实施（与原版兼容）
# ═══════════════════════════════════════════════════════════════

def create_backup() -> Optional[str]:
    """创建版本备份"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_msg = f"backup: 系统进化前自动备份 {timestamp}"
        
        # 只备份代码文件，不备份结果
        subprocess.run(
            ['git', 'add', 'second-brain-processor/*.py', 
             'second-brain-processor/*.sh', 
             'second-brain-processor/*.md'],
            cwd=WORKSPACE, capture_output=True, timeout=30
        )
        
        # 检查是否有可提交的文件
        status_result = subprocess.run(
            ['git', 'diff', '--cached', '--quiet'],
            cwd=WORKSPACE, capture_output=True, timeout=10
        )
        
        if status_result.returncode == 0:
            # 没有可提交的文件，创建空提交
            log("⚠️ 没有可提交的文件，创建空提交")
        
        result = subprocess.run(
            ['git', 'commit', '-m', backup_msg, '--allow-empty'],
            cwd=WORKSPACE, capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            hash_result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=WORKSPACE, capture_output=True, text=True, timeout=10
            )
            commit_hash = hash_result.stdout.strip()[:8] if hash_result.returncode == 0 else "unknown"
            log(f"✅ 备份成功: {commit_hash}")
            return commit_hash
        return None
    except Exception as e:
        log(f"❌ 备份失败: {e}")
        return None


def implement_improvements(plan: AIImprovementPlan) -> Dict:
    """实施AI生成的改进方案"""
    results = []
    
    for improvement in plan.improvements:
        try:
            result = _apply_file_change(improvement)
            results.append({
                'description': improvement.description,
                **result
            })
        except Exception as e:
            results.append({
                'description': improvement.description,
                'success': False,
                'error': str(e)
            })
    
    return {
        'success': all(r.get('success') for r in results),
        'changes': results
    }


def _apply_file_change(improvement: FileChange) -> Dict:
    """应用文件修改"""
    file_path = improvement.file_path
    old_code = improvement.old_code
    new_code = improvement.new_code
    
    # 处理字符串路径
    if isinstance(file_path, str):
        file_path = Path(file_path)
    
    if not file_path.exists():
        return {'success': False, 'error': f'文件不存在: {file_path}'}
    
    content = file_path.read_text(encoding='utf-8')
    
    if old_code not in content:
        return {'success': False, 'error': '找不到要替换的代码'}
    
    new_content = content.replace(old_code, new_code, 1)
    
    # 验证新代码语法
    if file_path.suffix == '.py':
        try:
            ast.parse(new_content)
        except SyntaxError as e:
            return {'success': False, 'error': f'新代码语法错误: {e}'}
    
    file_path.write_text(new_content, encoding='utf-8')
    return {'success': True}


def rollback_to_commit(commit_hash: str) -> bool:
    """回滚到指定版本"""
    try:
        log(f"回滚到版本: {commit_hash}")
        result = subprocess.run(
            ['git', 'reset', '--hard', commit_hash],
            cwd=WORKSPACE, capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            log("✅ 回滚成功")
            return True
        else:
            log(f"❌ 回滚失败: {result.stderr}")
            return False
    except Exception as e:
        log(f"❌ 回滚异常: {e}")
        return False


def verify_improvements(plan: AIImprovementPlan) -> Dict:
    """验证改进效果"""
    verification_results = []
    
    for improvement in plan.improvements:
        file_path = improvement.file_path
        if isinstance(file_path, str):
            file_path = Path(file_path)
        
        if file_path.suffix == '.py':
            result = subprocess.run(
                ['python3', '-m', 'py_compile', str(file_path)],
                capture_output=True, timeout=30
            )
            if result.returncode == 0:
                verification_results.append(f"{file_path.name}: 语法正确")
            else:
                return {
                    'success': False,
                    'message': f"语法检查失败: {file_path.name}"
                }
    
    return {
        'success': True,
        'message': '; '.join(verification_results) if verification_results else '基础验证通过'
    }


def log_evolution(plan: AIImprovementPlan, commit_hash: str, 
                  implementation: Dict, verification: Dict):
    """记录进化日志"""
    try:
        timestamp = datetime.now()
        evolution_id = f"EVO-{timestamp.strftime('%Y%m%d')}-{timestamp.strftime('%H%M')}"
        
        # 构建改进详情
        changes_text = []
        for change in implementation.get('changes', []):
            status = "✅" if change.get('success') else "❌"
            changes_text.append(f"{status} {change['description']}")
        
        log_entry = f"""
## [{evolution_id}] {plan.error_pattern}

**时间**: {timestamp.strftime('%Y-%m-%d %H:%M')}
**类型**: AI驱动的自动代码改进
**状态**: {'成功' if implementation.get('success') else '失败'}

### 问题根因
{plan.root_cause}

### AI推理过程
{plan.reasoning}

### 改进实施
{chr(10).join(changes_text)}

### 回滚点
- Git commit: {commit_hash}
- 回滚命令: `git reset --hard {commit_hash}`

### 验证结果
- 结果: {'通过' if verification.get('success') else '失败'}
- 详情: {verification.get('message', 'N/A')}

### 总结
{'AI驱动的改进成功实施' if implementation.get('success') and verification.get('success') else '改进遇到问题，已回滚或需人工介入'}

---
"""
        
        with open(EVOLUTION_LOG, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        log(f"✅ 进化记录已保存: {evolution_id}")
    except Exception as e:
        log(f"❌ 记录进化日志失败: {e}")


def generate_report(plan: Optional[AIImprovementPlan], 
                   implementation: Dict, verification: Dict) -> str:
    """生成结构化报告"""
    
    improvements_text = "今日无需改进"
    if plan and implementation.get('changes'):
        improvements_text = chr(10).join([
            f"- {imp['description']}: {'成功' if imp.get('success') else '失败'}"
            for imp in implementation.get('changes', [])
        ])
    
    reasoning_text = plan.reasoning if plan else "无"
    
    report = f"""
🤖 AI驱动的系统论每日复盘报告
═══════════════════════════════════

📊 错误统计（过去24小时）
- 总错误数: 见详细日志
- 主要问题: {plan.error_pattern if plan else '无'}
- 根因分析: {plan.root_cause if plan else '无需改进'}

🧠 AI推理
{reasoning_text}

🔧 改进方案
{improvements_text}

✅ 验证结果
- 实施状态: {'成功' if implementation.get('success') else '失败'}
- 验证详情: {verification.get('message', 'N/A')}

📋 建议
{verification.get('message', '系统运行良好，继续保持')}

═══════════════════════════════════
*报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""
    return report


# ═══════════════════════════════════════════════════════════════
# 第四部分：主流程
# ═══════════════════════════════════════════════════════════════

def daily_review():
    """AI驱动的每日复盘主流程"""
    log("=== 🤖 AI驱动的系统论每日复盘开始 ===")
    
    # 1. 收集错误
    errors = get_recent_errors(24)
    log(f"发现 {len(errors)} 个错误记录")
    
    if not errors:
        log("✅ 今日无错误，系统运行良好")
        return generate_report(None, {'success': True, 'changes': []}, 
                             {'success': True, 'message': '无错误需要处理'})
    
    # 2. 分析根因（取最新错误）
    latest_error = errors[0]
    analysis = analyze_error_root_cause(latest_error)
    log(f"🔍 错误模式: {analysis['pattern']} (置信度: {analysis['confidence']})")
    log(f"🔍 根因: {analysis['root_cause']}")
    log(f"🔍 受影响文件: {', '.join(analysis.get('affected_files', []))}")
    
    # 3. AI生成改进方案
    log("🧠 AI正在分析并生成改进方案...")
    plan = generate_improvement_plan_ai(analysis, errors)
    
    if not plan or not plan.improvements:
        log("⚠️ AI无法生成改进方案，跳过实施")
        return generate_report(None, {'success': False, 'changes': []},
                             {'success': False, 'message': 'AI无法生成改进方案'})
    
    log(f"📝 AI生成了 {len(plan.improvements)} 个改进项")
    log(f"🧠 AI推理: {plan.reasoning}")
    
    # 4. 创建备份
    commit_hash = create_backup()
    if not commit_hash:
        log("⚠️ 备份失败，跳过改进")
        return generate_report(plan, {'success': False, 'changes': []},
                             {'success': False, 'message': '备份失败'})
    
    # 5. 实施改进
    log("🔨 实施AI生成的改进...")
    implementation = implement_improvements(plan)
    
    if not implementation.get('success'):
        log("❌ 改进实施失败，执行回滚...")
        rollback_to_commit(commit_hash)
        log_evolution(plan, commit_hash, implementation, 
                     {'success': False, 'message': '实施失败，已回滚'})
        return generate_report(plan, implementation,
                             {'success': False, 'message': '实施失败，已回滚'})
    
    log(f"✅ 改进实施完成: {len([c for c in implementation['changes'] if c.get('success')])}/{len(implementation['changes'])}")
    
    # 6. 验证改进
    log("🔍 验证改进效果...")
    verification = verify_improvements(plan)
    
    # 7. 评估和回滚决策
    should_rollback = not verification.get('success')
    if should_rollback:
        log("⚠️ 验证失败，执行回滚...")
        rollback_to_commit(commit_hash)
    
    # 8. 记录日志
    log_evolution(plan, commit_hash, implementation, verification)
    
    # 9. 生成报告
    report = generate_report(plan, implementation, verification)
    
    log("=== 🤖 AI驱动的系统论每日复盘完成 ===")
    return report


def cleanup_old_errors():
    """清理30天前的错误记录"""
    if not ERRORS_FILE.exists():
        return
    
    try:
        content = ERRORS_FILE.read_text(encoding='utf-8')
        cutoff_time = datetime.now() - timedelta(days=ERROR_RETENTION_DAYS)
        
        error_pattern = r'(## \[ERR-\d{8}-\d+\] .+?)(?=## \[ERR-|\Z)'
        matches = re.findall(error_pattern, content + '\n## [', re.DOTALL)
        
        kept_errors = []
        for match in matches:
            time_match = re.search(r'\*\*Logged\*\*: ([^\n]+)', match)
            if time_match:
                try:
                    log_time = datetime.fromisoformat(time_match.group(1).replace('Z', '+00:00').replace('+00:00', ''))
                    if log_time > cutoff_time:
                        kept_errors.append(match.rstrip())
                except:
                    kept_errors.append(match.rstrip())
            else:
                kept_errors.append(match.rstrip())
        
        # 重建文件
        header = "# 错误日志\n\n记录系统运行中遇到的错误、失败操作及解决方案。\n\n---\n\n"
        new_content = header + "\n---\n\n".join(kept_errors)
        
        ERRORS_FILE.write_text(new_content, encoding='utf-8')
        log(f"✅ 清理完成，保留 {len(kept_errors)} 条错误记录")
    except Exception as e:
        log(f"❌ 清理错误日志失败: {e}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--daily-review":
        report = daily_review()
        print(report)
    else:
        print("用法: python3 system_evolution_ai.py --daily-review")
