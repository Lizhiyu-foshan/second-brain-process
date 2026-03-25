#!/usr/bin/env python3
"""
user_verify.py - 用户验证脚本
你可以随时运行这个脚本，验证我是否在写伪代码
"""

import ast
import sys
import re
from pathlib import Path
from datetime import datetime

class FakeCodeDetector(ast.NodeVisitor):
    """AST检测器：识别伪代码模式"""
    
    def __init__(self):
        self.violations = []
        self.has_api_call = False
        self.current_function = None
        
    def visit_FunctionDef(self, node):
        self.current_function = node.name
        
        # 检查函数名是否暗示AI调用
        ai_indicators = ['ai', 'llm', 'model', 'analyze', 'generate', 'identify']
        if any(ind in node.name.lower() for ind in ai_indicators):
            # 检查函数体内是否有API调用
            self.has_api_call = False
            self.generic_visit(node)
            
            if not self.has_api_call:
                self.violations.append({
                    'type': 'FAKE_AI_FUNCTION',
                    'function': node.name,
                    'line': node.lineno,
                    'message': f'函数名暗示AI调用，但无API请求代码',
                    'severity': 'CRITICAL'
                })
        
        self.current_function = None
        
    def visit_Call(self, node):
        # 检查是否有API调用
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in ['get', 'post', 'request', 'urlopen']:
                self.has_api_call = True
        elif isinstance(node.func, ast.Name):
            if node.func.id in ['requests', 'urlopen', 'post']:
                self.has_api_call = True
        
        # 检查是否有硬编码append
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == 'append':
                # 检查是否在循环外
                self.violations.append({
                    'type': 'SUSPICIOUS_APPEND',
                    'line': node.lineno,
                    'message': '发现append调用，请确认不是硬编码数据',
                    'severity': 'WARNING'
                })
        
        self.generic_visit(node)


def check_hardcoded_strings(filepath: Path, content: str) -> list:
    """检查硬编码字符串模式"""
    violations = []
    
    # 模式1: 硬编码的主题名称
    hardcoded_themes = [
        r'"name":\s*"AI深度整理的标准与规范"',
        r'"name":\s*"Second Brain系统优化"',
        r'"name":\s*"Skill系统化验证方法论"',
    ]
    
    for pattern in hardcoded_themes:
        if re.search(pattern, content):
            violations.append({
                'type': 'HARDCODED_THEME',
                'pattern': pattern,
                'message': '发现硬编码主题名称，这是伪代码标志',
                'severity': 'CRITICAL'
            })
    
    # 模式2: 硬编码key_takeaway
    if '"key_takeaway": "' in content:
        # 检查是否是变量赋值还是硬编码字符串
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if '"key_takeaway": "聊天记录整理应遵循' in line:
                violations.append({
                    'type': 'HARDCODED_CONTENT',
                    'line': i,
                    'message': '发现硬编码的key_takeaway内容',
                    'severity': 'CRITICAL'
                })
    
    return violations


def verify_file(filepath: Path) -> dict:
    """验证单个文件"""
    result = {
        'file': str(filepath),
        'passed': True,
        'violations': []
    }
    
    try:
        content = filepath.read_text(encoding='utf-8')
        
        # AST分析
        tree = ast.parse(content)
        detector = FakeCodeDetector()
        detector.visit(tree)
        
        result['violations'].extend(detector.violations)
        
        # 硬编码字符串检查
        hardcoded = check_hardcoded_strings(filepath, content)
        result['violations'].extend(hardcoded)
        
        # 检查是否有注释欺骗
        docstrings = [node.body[0].value.s for node in ast.walk(tree) 
                     if isinstance(node, ast.FunctionDef) and node.body 
                     and isinstance(node.body[0], ast.Expr)
                     and isinstance(node.body[0].value, ast.Constant)]
        
        for doc in docstrings:
            if '调用AI' in doc or 'AI分析' in doc or 'OpenClaw' in doc:
                # 检查函数内是否有真正的API调用
                if not detector.has_api_call:
                    result['violations'].append({
                        'type': 'DOC_DECEPTION',
                        'message': '文档字符串承诺AI调用，但代码中没有',
                        'severity': 'CRITICAL'
                    })
        
        # 判断是否通过
        critical = [v for v in result['violations'] if v.get('severity') == 'CRITICAL']
        if critical:
            result['passed'] = False
            
    except Exception as e:
        result['passed'] = False
        result['violations'].append({
            'type': 'PARSE_ERROR',
            'message': f'解析失败: {e}',
            'severity': 'ERROR'
        })
    
    return result


def main():
    """主函数"""
    print("=" * 60)
    print("🔍 伪代码检测器 - 用户验证版")
    print("=" * 60)
    print()
    
    # 扫描目录
    target_dirs = [
        Path('/root/.openclaw/workspace/second-brain-processor'),
        Path('/root/.openclaw/workspace/skills'),
    ]
    
    all_passed = True
    total_files = 0
    total_violations = 0
    
    for dir_path in target_dirs:
        if not dir_path.exists():
            continue
            
        print(f"\n📁 扫描目录: {dir_path}")
        print("-" * 60)
        
        for pyfile in dir_path.rglob('*.py'):
            # 跳过测试文件和备份
            if 'test' in pyfile.name or 'backup' in str(pyfile):
                continue
                
            total_files += 1
            result = verify_file(pyfile)
            
            if not result['passed']:
                all_passed = False
                total_violations += len(result['violations'])
                
                print(f"\n❌ {result['file']}")
                for v in result['violations']:
                    emoji = "🔴" if v['severity'] == 'CRITICAL' else "🟡"
                    print(f"   {emoji} [{v['severity']}] {v['type']}: {v['message']}")
            else:
                print(f"✅ {pyfile.name}")
    
    print()
    print("=" * 60)
    print("📊 扫描结果")
    print("=" * 60)
    print(f"扫描文件数: {total_files}")
    print(f"发现问题: {total_violations}")
    
    if all_passed:
        print("\n🎉 所有检查通过！未发现伪代码。")
        return 0
    else:
        print("\n🚨 发现伪代码！请立即修复。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
