#!/usr/bin/env python3
"""
系统论自动进化引擎 v2.0 - 真正实施改进

核心功能：
1. 错误模式分析 - 深度分析错误根因
2. 代码自动修复 - 真正修改代码文件
3. 版本管理与回滚 - git-based版本控制
4. 效果验证测试 - 执行验证脚本
5. 持续学习积累 - 从错误中学习模式

使用：
    python3 system_evolution_v2.py --daily-review    # 凌晨5点复盘
    python3 system_evolution_v2.py --analyze-only    # 仅分析不实施
    python3 system_evolution_v2.py --rollback [hash] # 回滚到指定版本
"""

import json
import re
import subprocess
import sys
import ast
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# 路径配置
WORKSPACE = Path("/root/.openclaw/workspace")
PROCESSOR_DIR = WORKSPACE / "second-brain-processor"
LEARNINGS_DIR = WORKSPACE / ".learnings"
ERRORS_FILE = LEARNINGS_DIR / "ERRORS.md"
EVOLUTION_LOG = LEARNINGS_DIR / "EVOLUTION_LOG.md"
IMPROVEMENTS_FILE = LEARNINGS_DIR / "IMPROVEMENTS.md"

# 保留配置
ERROR_RETENTION_DAYS = 30
MAX_DAILY_IMPROVEMENTS = 2  # 每天最多2次改进，避免过度修改


def log(msg):
    """打印日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {msg}")


# ═══════════════════════════════════════════════════════════════
# 第一部分：错误分析
# ═══════════════════════════════════════════════════════════════

def get_recent_errors(hours=24) -> List[Dict]:
    """获取最近N小时的错误记录"""
    if not ERRORS_FILE.exists():
        return []
    
    try:
        content = ERRORS_FILE.read_text(encoding='utf-8')
        error_pattern = r'## \[(ERR-\d{8}-\d+)\] (.+?)\n\n\*\*Logged\*\*: ([^\n]+)'
        matches = re.findall(error_pattern, content, re.DOTALL)
        
        errors = []
        # 修复：使用带时区的当前时间
        cutoff_time = datetime.now().astimezone() - timedelta(hours=hours)
        
        for error_id, title, logged_time in matches:
            try:
                # 修复：正确处理带时区的时间
                log_dt = datetime.fromisoformat(logged_time.replace('Z', '+00:00'))
                if log_dt > cutoff_time:
                    # 提取详细内容
                    error_section = re.search(
                        rf'## \[{error_id}\].+?(?=## \[ERR-|\Z)',
                        content,
                        re.DOTALL
                    )
                    details = error_section.group(0) if error_section else ""
                    
                    errors.append({
                        'id': error_id,
                        'title': title,
                        'time': log_dt,
                        'details': details
                    })
            except Exception as e:
                print(f"[WARN] 解析错误时间失败 {error_id}: {e}")
                continue
        
        return errors
    except Exception as e:
        log(f"读取错误日志失败: {e}")
        return []


def analyze_error_root_cause(error: Dict) -> Dict:
    """深度分析错误的根本原因"""
    title = error['title'].lower()
    details = error.get('details', '').lower()
    
    # 错误模式识别
    patterns = {
        'git_push_timeout': {
            'keywords': ['push', 'timeout', '443', 'connection', 'github'],
            'root_cause': 'GitHub网络连接不稳定或超时时间过短',
            'solution_type': 'network_resilience'
        },
        'git_auth_fail': {
            'keywords': ['auth', 'permission', 'denied', '403'],
            'root_cause': 'Git认证失效或权限不足',
            'solution_type': 'git_auth'
        },
        'file_not_found': {
            'keywords': ['no such file', 'not found', 'enoent'],
            'root_cause': '文件路径错误或文件被删除',
            'solution_type': 'file_check'
        },
        'file_permission': {
            'keywords': ['permission', 'denied', 'eacces'],
            'root_cause': '文件权限不足',
            'solution_type': 'permission_fix'
        },
        'json_decode': {
            'keywords': ['json', 'decode', 'parse'],
            'root_cause': 'JSON格式错误或编码问题',
            'solution_type': 'error_handling'
        },
        'api_validation': {
            'keywords': ['validation', 'api', 'request'],
            'root_cause': 'API请求格式不符合要求',
            'solution_type': 'api_fix'
        },
        'memory_limit': {
            'keywords': ['memory', 'oom', 'killed'],
            'root_cause': '内存不足或文件过大',
            'solution_type': 'memory_optimization'
        }
    }
    
    for pattern_name, pattern_info in patterns.items():
        if any(kw in title or kw in details for kw in pattern_info['keywords']):
            return {
                'pattern': pattern_name,
                'root_cause': pattern_info['root_cause'],
                'solution_type': pattern_info['solution_type'],
                'confidence': 'high'
            }
    
    return {
        'pattern': 'unknown',
        'root_cause': '未识别的错误类型',
        'solution_type': 'general_improvement',
        'confidence': 'low'
    }


# ═══════════════════════════════════════════════════════════════
# 第二部分：改进方案生成
# ═══════════════════════════════════════════════════════════════

class CodeImprovement:
    """代码改进方案"""
    
    def __init__(self, error_pattern: str, root_cause: str):
        self.error_pattern = error_pattern
        self.root_cause = root_cause
        self.improvements = []
    
    def add_file_change(self, file_path: Path, description: str, 
                        old_code: str, new_code: str):
        """添加文件修改"""
        self.improvements.append({
            'type': 'file_change',
            'file': file_path,
            'description': description,
            'old': old_code,
            'new': new_code
        })
    
    def add_new_file(self, file_path: Path, description: str, content: str):
        """添加新文件"""
        self.improvements.append({
            'type': 'new_file',
            'file': file_path,
            'description': description,
            'content': content
        })
    
    def generate_plan(self) -> Dict:
        """生成改进计划"""
        return {
            'error_pattern': self.error_pattern,
            'root_cause': self.root_cause,
            'improvements': self.improvements,
            'estimated_time': len(self.improvements) * 5  # 每个改进5秒
        }


def generate_improvement_plan(error_analysis: Dict, errors: List[Dict]) -> Optional[CodeImprovement]:
    """根据错误分析生成改进方案"""
    solution_type = error_analysis['solution_type']
    
    plan = CodeImprovement(
        error_pattern=error_analysis['pattern'],
        root_cause=error_analysis['root_cause']
    )
    
    # 根据错误类型生成具体改进
    if solution_type == 'network_resilience':
        _add_network_improvements(plan)
    elif solution_type == 'git_auth':
        _add_git_auth_improvements(plan)
    elif solution_type == 'file_check':
        _add_file_check_improvements(plan)
    elif solution_type == 'error_handling':
        _add_error_handling_improvements(plan)
    elif solution_type == 'memory_optimization':
        _add_memory_improvements(plan)
    else:
        _add_general_improvements(plan)
    
    return plan if plan.improvements else None


def _add_network_improvements(plan: CodeImprovement):
    """添加网络弹性改进"""
    kimiclaw_file = PROCESSOR_DIR / "kimiclaw_v2.py"
    
    # 改进1: 增强git推送重试逻辑
    plan.add_file_change(
        kimiclaw_file,
        "增强Git推送重试逻辑，添加指数退避",
        """def commit_and_push(message):
    \"\"\"提交并推送到GitHub，带重试\"\"\"
    max_retries = 3
    for i in range(max_retries):
        try:""",
        """def commit_and_push(message):
    \"\"\"提交并推送到GitHub，带重试和指数退避\"\"\"
    max_retries = 3
    base_delay = 2  # 基础延迟2秒
    
    for i in range(max_retries):
        try:
            # 每次重试增加延迟（指数退避）
            if i > 0:
                delay = base_delay * (2 ** i)
                log(f"第{i+1}次重试，等待{delay}秒...")
                time.sleep(delay)"""
    )
    
    # 改进2: 添加网络超时配置
    run_script = PROCESSOR_DIR / "run_morning_process.sh"
    if run_script.exists():
        plan.add_file_change(
            run_script,
            "添加网络超时环境变量",
            "#!/bin/bash",
            """#!/bin/bash
# 网络超时配置（防止GitHub连接超时）
export GIT_HTTP_TIMEOUT=120
export GIT_HTTP_LOW_SPEED_LIMIT=1000
export GIT_HTTP_LOW_SPEED_TIME=60"""
        )
    
    # 改进3: 修复备份函数，处理无可提交文件的情况
    plan.add_file_change(
        PROCESSOR_DIR / "system_evolution_v2.py",
        "修复备份函数，处理无可提交文件的情况",
        """def create_backup() -> Optional[str]:
    \"\"\"创建版本备份\"\"\"
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
        
        result = subprocess.run(
            ['git', 'commit', '-m', backup_msg],
            cwd=WORKSPACE, capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:""",
        """def create_backup() -> Optional[str]:
    \"\"\"创建版本备份\"\"\"
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_msg = f"backup: 系统进化前自动备份 {timestamp}"
        
        # 只备份代码文件，不备份结果
        add_result = subprocess.run(
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
            # 没有可提交的文件，创建一个空提交
            log("⚠️ 没有可提交的文件，创建空提交")
        
        result = subprocess.run(
            ['git', 'commit', '-m', backup_msg, '--allow-empty'],
            cwd=WORKSPACE, capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:"""
    )


def _add_file_check_improvements(plan: CodeImprovement):
    """添加文件存在性检查改进"""
    kimiclaw_file = PROCESSOR_DIR / "kimiclaw_v2.py"
    
    plan.add_file_change(
        kimiclaw_file,
        "添加文件存在性检查和自动创建目录",
        """def save_last_process_time(dt=None):
    \"\"\"保存本次整理时间\"\"\"
    if dt is None:
        dt = datetime.now()
    with open(LAST_PROCESS_FILE, 'w') as f:
        f.write(dt.isoformat())""",
        """def save_last_process_time(dt=None):
    \"\"\"保存本次整理时间\"\"\"
    if dt is None:
        dt = datetime.now()
    try:
        # 确保目录存在
        LAST_PROCESS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LAST_PROCESS_FILE, 'w') as f:
            f.write(dt.isoformat())
    except Exception as e:
        log(f"[WARN] 保存处理时间失败: {e}")"""
    )


def _add_error_handling_improvements(plan: CodeImprovement):
    """添加错误处理改进"""
    processor_file = PROCESSOR_DIR / "processor.py" if (PROCESSOR_DIR / "processor.py").exists() else None
    
    if processor_file:
        plan.add_file_change(
            processor_file,
            "增强JSON解析错误处理",
            """data = json.loads(line)""",
            """try:
    data = json.loads(line)
except json.JSONDecodeError as e:
    log(f"[WARN] JSON解析失败，跳过该行: {e}")
    continue"""
        )


def _add_memory_improvements(plan: CodeImprovement):
    """添加内存优化改进"""
    kimiclaw_file = PROCESSOR_DIR / "kimiclaw_v2.py"
    
    plan.add_file_change(
        kimiclaw_file,
        "优化大文件处理，使用生成器减少内存占用",
        """with open(session_file, 'r', encoding='utf-8') as f:
    content = f.read()""",
        """# 对于大文件，使用分块读取
file_size = session_file.stat().st_size
if file_size > 1024 * 1024:  # 大于1MB
    log(f"大文件使用流式读取: {session_file.name}")
    content = _read_large_file(session_file)
else:
    with open(session_file, 'r', encoding='utf-8') as f:
        content = f.read()

def _read_large_file(file_path, chunk_size=8192):
    \"\"\"流式读取大文件\"\"\"
    chunks = []
    with open(file_path, 'r', encoding='utf-8') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            chunks.append(chunk)
    return ''.join(chunks)"""
    )


def _add_general_improvements(plan: CodeImprovement):
    """添加通用改进"""
    # 创建健康检查脚本
    health_script = PROCESSOR_DIR / "health_check.py"
    if not health_script.exists():
        plan.add_new_file(
            health_script,
            "创建系统健康检查脚本",
            '''#!/usr/bin/env python3
"""系统健康检查脚本"""

import subprocess
import sys
from pathlib import Path

WORKSPACE = Path("/root/.openclaw/workspace")

def check_python_syntax():
    """检查Python语法"""
    processor_dir = WORKSPACE / "second-brain-processor"
    errors = []
    for py_file in processor_dir.glob("*.py"):
        result = subprocess.run(
            ["python3", "-m", "py_compile", str(py_file)],
            capture_output=True
        )
        if result.returncode != 0:
            errors.append(py_file.name)
    return errors

def check_critical_paths():
    """检查关键路径"""
    paths = [
        WORKSPACE / "obsidian-vault",
        WORKSPACE / ".learnings",
        Path("/root/.openclaw/agents/main/sessions")
    ]
    missing = []
    for p in paths:
        if not p.exists():
            missing.append(str(p))
    return missing

if __name__ == "__main__":
    print("=== 系统健康检查 ===")
    
    syntax_errors = check_python_syntax()
    if syntax_errors:
        print(f"❌ Python语法错误: {syntax_errors}")
        sys.exit(1)
    else:
        print("✅ Python语法检查通过")
    
    missing_paths = check_critical_paths()
    if missing_paths:
        print(f"⚠️ 缺失路径: {missing_paths}")
    else:
        print("✅ 所有关键路径存在")
    
    print("=== 检查完成 ===")
'''
        )


# ═══════════════════════════════════════════════════════════════
# 第三部分：改进实施
# ═══════════════════════════════════════════════════════════════

def create_backup() -> Optional[str]:
    """创建版本备份"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_msg = f"backup: 系统进化前自动备份 {timestamp}"
        
        # 只备份代码文件，不备份结果
        add_result = subprocess.run(
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
            # 没有可提交的文件，创建一个空提交
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


def implement_improvements(plan: CodeImprovement) -> Dict:
    """实施改进方案"""
    results = []
    
    for improvement in plan.improvements:
        try:
            if improvement['type'] == 'file_change':
                result = _apply_file_change(improvement)
            elif improvement['type'] == 'new_file':
                result = _create_new_file(improvement)
            else:
                result = {'success': False, 'error': '未知改进类型'}
            
            results.append({
                'description': improvement['description'],
                **result
            })
        except Exception as e:
            results.append({
                'description': improvement['description'],
                'success': False,
                'error': str(e)
            })
    
    return {
        'success': all(r.get('success') for r in results),
        'changes': results
    }


def _apply_file_change(improvement: Dict) -> Dict:
    """应用文件修改"""
    file_path = improvement['file']
    
    # 🔧 修复：将字符串转换为 Path 对象
    if isinstance(file_path, str):
        file_path = Path(file_path)
    
    old_code = improvement['old']
    new_code = improvement['new']
    
    if not file_path.exists():
        return {'success': False, 'error': f'文件不存在: {file_path}'}
    
    content = file_path.read_text(encoding='utf-8')
    
    if old_code not in content:
        return {'success': False, 'error': '找不到要替换的代码'}
    
    new_content = content.replace(old_code, new_code, 1)
    
    # 验证新代码语法
    try:
        ast.parse(new_content)
    except SyntaxError as e:
        return {'success': False, 'error': f'新代码语法错误: {e}'}
    
    file_path.write_text(new_content, encoding='utf-8')
    return {'success': True}


def _create_new_file(improvement: Dict) -> Dict:
    """创建新文件"""
    file_path = improvement['file']
    
    # 🔧 修复：将字符串转换为 Path 对象
    if isinstance(file_path, str):
        file_path = Path(file_path)
    
    content = improvement['content']
    
    if file_path.exists():
        return {'success': False, 'error': f'文件已存在: {file_path}'}
    
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 验证代码语法
    if file_path.suffix == '.py':
        try:
            ast.parse(content)
        except SyntaxError as e:
            return {'success': False, 'error': f'代码语法错误: {e}'}
    
    file_path.write_text(content, encoding='utf-8')
    file_path.chmod(0o755)  # 添加执行权限
    
    return {'success': True}


# ═══════════════════════════════════════════════════════════════
# 第四部分：验证和记录
# ═══════════════════════════════════════════════════════════════

def verify_improvements(plan: CodeImprovement) -> Dict:
    """验证改进效果"""
    verification_results = []
    
    # 验证1: 语法检查
    for improvement in plan.improvements:
        if improvement['type'] == 'file_change':
            file_path = improvement['file']
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
    
    # 验证2: 关键函数存在性检查
    if (PROCESSOR_DIR / "kimiclaw_v2.py").exists():
        content = (PROCESSOR_DIR / "kimiclaw_v2.py").read_text(encoding='utf-8')
        required_functions = ['get_fixed_daily_window', 'categorize_content']
        for func in required_functions:
            if f'def {func}(' in content:
                verification_results.append(f"函数 {func}: 存在")
    
    return {
        'success': True,
        'message': '; '.join(verification_results) if verification_results else '基础验证通过'
    }


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


def log_evolution(plan: CodeImprovement, commit_hash: str, 
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
**类型**: 自动代码改进
**状态**: {'成功' if implementation.get('success') else '失败'}

### 问题根因
{plan.root_cause}

### 改进实施
{chr(10).join(changes_text)}

### 回滚点
- Git commit: {commit_hash}
- 回滚命令: `git reset --hard {commit_hash}`

### 验证结果
- 结果: {'通过' if verification.get('success') else '失败'}
- 详情: {verification.get('message', 'N/A')}

### 总结
{'改进成功，代码质量提升' if implementation.get('success') and verification.get('success') else '改进遇到问题，已回滚或需人工介入'}

---
"""
        
        with open(EVOLUTION_LOG, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        log(f"✅ 进化记录已保存: {evolution_id}")
    except Exception as e:
        log(f"❌ 记录进化日志失败: {e}")


def generate_report(errors: List[Dict], plan: Optional[CodeImprovement], 
                   implementation: Dict, verification: Dict) -> str:
    """生成结构化报告"""
    report = f"""
🔄 系统论每日复盘报告
═══════════════════════════════════

📊 错误统计（过去24小时）
- 总错误数: {len(errors)}
- 主要问题: {plan.error_pattern if plan else '无'}
- 根因分析: {plan.root_cause if plan else '无需改进'}

🔧 改进方案
{chr(10).join([f"- {imp['description']}: {'成功' if imp.get('success') else '失败'}" 
               for imp in implementation.get('changes', [])]) if implementation.get('changes') else '今日无需改进'}

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
# 第五部分：主流程
# ═══════════════════════════════════════════════════════════════

def daily_review():
    """每日复盘主流程"""
    log("=== 系统论每日复盘开始 ===")
    
    # 1. 收集错误
    errors = get_recent_errors(24)
    log(f"发现 {len(errors)} 个错误记录")
    
    if not errors:
        log("✅ 今日无错误，系统运行良好")
        return generate_report([], None, {'success': True, 'changes': []}, 
                             {'success': True, 'message': '无错误需要处理'})
    
    # 2. 分析根因（取最新错误）
    latest_error = errors[0]
    analysis = analyze_error_root_cause(latest_error)
    log(f"🔍 错误模式: {analysis['pattern']} (置信度: {analysis['confidence']})")
    log(f"🔍 根因: {analysis['root_cause']}")
    
    # 3. 生成改进方案
    plan = generate_improvement_plan(analysis, errors)
    
    if not plan:
        log("⚠️ 无法生成改进方案，跳过实施")
        return generate_report(errors, None, {'success': False, 'changes': []},
                             {'success': False, 'message': '无法生成改进方案'})
    
    log(f"📝 生成 {len(plan.improvements)} 个改进项")
    
    # 4. 创建备份
    commit_hash = create_backup()
    if not commit_hash:
        log("⚠️ 备份失败，跳过改进")
        return generate_report(errors, plan, {'success': False, 'changes': []},
                             {'success': False, 'message': '备份失败'})
    
    # 5. 实施改进
    log("🔨 实施改进...")
    implementation = implement_improvements(plan)
    
    if not implementation.get('success'):
        log("❌ 改进实施失败，执行回滚...")
        rollback_to_commit(commit_hash)
        log_evolution(plan, commit_hash, implementation, 
                     {'success': False, 'message': '实施失败，已回滚'})
        return generate_report(errors, plan, implementation,
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
    report = generate_report(errors, plan, implementation, verification)
    
    log("=== 系统论每日复盘完成 ===")
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
        
        header = "# 错误日志\n\n记录系统运行中遇到的错误、失败操作及解决方案。\n\n---\n\n"
        new_content = header + "\n\n".join(kept_errors)
        
        with open(ERRORS_FILE, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        removed_count = len(matches) - len(kept_errors)
        if removed_count > 0:
            log(f"🧹 清理了 {removed_count} 条30天前的错误记录")
    except Exception as e:
        log(f"⚠️ 清理错误日志失败: {e}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--daily-review', action='store_true', help='执行每日复盘')
    parser.add_argument('--analyze-only', action='store_true', help='仅分析不实施')
    parser.add_argument('--rollback', type=str, help='回滚到指定commit')
    args = parser.parse_args()
    
    if args.rollback:
        success = rollback_to_commit(args.rollback)
        sys.exit(0 if success else 1)
    elif args.daily_review:
        cleanup_old_errors()
        report = daily_review()
        print("\n" + report)
    elif args.analyze_only:
        errors = get_recent_errors(24)
        if errors:
            analysis = analyze_error_root_cause(errors[0])
            print(json.dumps(analysis, indent=2, default=str))
        else:
            print("无错误记录")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
