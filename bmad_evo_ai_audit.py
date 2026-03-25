#!/usr/bin/env python3
"""
BMAD-EVO AI代码审计器
0容忍伪代码审计
"""

import ast
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class AIFunctionAudit:
    """AI函数审计结果"""
    file: str
    function: str
    line: int
    has_api_call: bool
    api_call_type: Optional[str]  # 'requests', 'urllib', 'openai', 'subprocess', None
    has_hardcoded_return: bool
    docstring: Optional[str]
    is_deceptive: bool  # 函数名暗示AI但无API调用
    severity: str  # 'PASS', 'WARNING', 'CRITICAL'

class AICodeAuditor(ast.NodeVisitor):
    """AST审计器 - 专门检测AI相关代码"""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.results: List[AIFunctionAudit] = []
        self.current_function = None
        self.current_docstring = None
        self.current_has_api_call = False
        self.current_api_type = None
        self.current_has_hardcoded_return = False
        
    def visit_FunctionDef(self, node):
        """检查函数定义"""
        self.current_function = node.name
        self.current_docstring = None
        self.current_has_api_call = False
        self.current_api_type = None
        self.current_has_hardcoded_return = False
        
        # 检查是否是AI相关函数名
        ai_indicators = ['ai', 'llm', 'model', 'analyze', 'generate', 'identify', 
                        'extract', 'summarize', 'classify', 'predict']
        is_ai_function = any(ind in node.name.lower() for ind in ai_indicators)
        
        # 获取文档字符串
        if node.body and isinstance(node.body[0], ast.Expr):
            if isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
                self.current_docstring = node.body[0].value.value
        
        # 访问函数体
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                self._check_api_call(child)
            if isinstance(child, ast.Return):
                self._check_hardcoded_return(child)
        
        if is_ai_function:
            is_deceptive = is_ai_function and not self.current_has_api_call
            
            if is_deceptive:
                severity = 'CRITICAL'
            elif self.current_has_hardcoded_return:
                severity = 'WARNING'
            else:
                severity = 'PASS'
            
            self.results.append(AIFunctionAudit(
                file=self.filename,
                function=node.name,
                line=node.lineno,
                has_api_call=self.current_has_api_call,
                api_call_type=self.current_api_type,
                has_hardcoded_return=self.current_has_hardcoded_return,
                docstring=self.current_docstring[:100] + '...' if self.current_docstring and len(self.current_docstring) > 100 else self.current_docstring,
                is_deceptive=is_deceptive,
                severity=severity
            ))
        
        self.current_function = None
        self.generic_visit(node)
    
    def _check_api_call(self, node: ast.Call):
        """检查是否有API调用"""
        # 检查requests调用
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in ['get', 'post', 'put', 'delete', 'request']:
                if isinstance(node.func.value, ast.Name) and node.func.value.id == 'requests':
                    self.current_has_api_call = True
                    self.current_api_type = 'requests'
        
        # 检查urllib
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in ['urlopen', 'Request']:
                self.current_has_api_call = True
                self.current_api_type = 'urllib'
        
        # 检查openai
        if isinstance(node.func, ast.Attribute):
            if 'openai' in str(node.func.attr).lower() or 'chat' in str(node.func.attr).lower():
                self.current_has_api_call = True
                self.current_api_type = 'openai'
        
        # 检查subprocess（可能是调用外部AI工具）
        if isinstance(node.func, ast.Name):
            if node.func.id in ['subprocess', 'Popen', 'run']:
                self.current_has_api_call = True
                self.current_api_type = 'subprocess'
    
    def _check_hardcoded_return(self, node: ast.Return):
        """检查是否有硬编码返回"""
        if node.value:
            if isinstance(node.value, (ast.Dict, ast.List, ast.Constant)):
                self.current_has_hardcoded_return = True
            # 检查是否是append后返回
            if isinstance(node.value, ast.Name):
                # 变量返回，可能前面有硬编码append
                pass


def audit_file(filepath: Path) -> List[AIFunctionAudit]:
    """审计单个文件"""
    try:
        content = filepath.read_text(encoding='utf-8')
        tree = ast.parse(content)
        auditor = AICodeAuditor(str(filepath))
        auditor.visit(tree)
        return auditor.results
    except Exception as e:
        return [AIFunctionAudit(
            file=str(filepath),
            function='PARSE_ERROR',
            line=0,
            has_api_call=False,
            api_call_type=None,
            has_hardcoded_return=False,
            docstring=str(e),
            is_deceptive=True,
            severity='CRITICAL'
        )]


def main():
    """主函数 - 审计second-brain-processor"""
    target_dir = Path('/root/.openclaw/workspace/second-brain-processor')
    
    print("=" * 80)
    print("BMAD-EVO AI代码0容忍审计")
    print("=" * 80)
    print(f"审计目录: {target_dir}")
    print()
    
    all_critical = []
    all_warning = []
    all_pass = []
    
    for pyfile in sorted(target_dir.glob('*.py')):
        if pyfile.name.startswith('test'):
            continue
            
        results = audit_file(pyfile)
        
        if results:
            print(f"\n📄 {pyfile.name}")
            print("-" * 80)
            
            for r in results:
                if r.severity == 'CRITICAL':
                    all_critical.append(r)
                    print(f"  🔴 CRITICAL: {r.function} (line {r.line})")
                    print(f"      问题: 函数名暗示AI调用，但无API请求代码")
                    if r.docstring and ('AI' in r.docstring or '模型' in r.docstring):
                        print(f"      文档欺骗: 文档字符串承诺AI功能")
                    print()
                elif r.severity == 'WARNING':
                    all_warning.append(r)
                    print(f"  🟡 WARNING: {r.function} (line {r.line})")
                    print(f"      问题: 有API调用，但有硬编码返回")
                    print()
                else:
                    all_pass.append(r)
                    print(f"  ✅ PASS: {r.function} (line {r.line})")
                    print(f"      API类型: {r.api_call_type}")
                    print()
    
    # 汇总
    print()
    print("=" * 80)
    print("审计汇总")
    print("=" * 80)
    print(f"🔴 CRITICAL (伪代码): {len(all_critical)}")
    print(f"🟡 WARNING (可疑): {len(all_warning)}")
    print(f"✅ PASS (真正调用AI): {len(all_pass)}")
    print()
    
    if all_critical:
        print("🔴 必须立即修复的文件:")
        files = set(r.file for r in all_critical)
        for f in sorted(files):
            funcs = [r.function for r in all_critical if r.file == f]
            print(f"  - {Path(f).name}: {', '.join(funcs)}")
    
    return len(all_critical)


if __name__ == "__main__":
    sys.exit(main())
