#!/usr/bin/env python3
"""
BMAD-EVO AI伪代码扫描器
扫描所有skills和projects目录中的伪AI处理代码
"""

import ast
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Set
from collections import defaultdict
import sys

@dataclass
class FakeAIHit:
    """伪AI代码命中"""
    file: str
    line: int
    category: str  # mock_return, placeholder, todo_ai, pseudo_code
    severity: str  # critical, high, medium, low
    content: str
    context: str = ""  # 前后文
    
    def to_dict(self):
        return {
            "file": self.file,
            "line": self.line,
            "category": self.category,
            "severity": self.severity,
            "content": self.content,
            "context": self.context
        }


class FakeAIFinder(ast.NodeVisitor):
    """AST分析器：查找伪AI代码模式"""
    
    # 伪代码模式定义
    PATTERNS = {
        "mock_return": {
            "keywords": ["模拟", "mock", "模拟结果", "测试数据", "示例数据", "假数据"],
            "severity": "critical",
            "description": "返回模拟数据而非真实AI调用"
        },
        "placeholder": {
            "keywords": ["placeholder", "stub", "TODO", "FIXME", "待实现", "未实现"],
            "severity": "high", 
            "description": "占位符/未实现代码"
        },
        "todo_ai": {
            "keywords": ["TODO.*AI", "FIXME.*AI", "待调用AI", "实际应调用", "实际应该调用"],
            "severity": "high",
            "description": "标记需要AI调用但未实现"
        },
        "pseudo_code": {
            "keywords": ["伪代码", "pseudocode", "简化版", "简化实现"],
            "severity": "high",
            "description": "伪代码/简化实现"
        },
        "commented_ai": {
            "keywords": ["#.*AI", "#.*模型", "#.*调用", "#.*请求"],
            "severity": "medium",
            "description": "注释掉的AI相关代码"
        }
    }
    
    def __init__(self, filename: str, content: str):
        self.filename = filename
        self.content = content
        self.lines = content.split('\n')
        self.hits: List[FakeAIHit] = []
        self.current_function = None
        
    def visit_FunctionDef(self, node):
        """检查函数定义"""
        old_func = self.current_function
        self.current_function = node.name
        
        # 检查函数名是否包含可疑关键词（排除测试相关）
        func_lower = node.name.lower()
        suspicious_names = ['mock', 'stub', 'fake', 'demo']
        # 排除正常的测试函数
        if any(s in func_lower for s in suspicious_names):
            # 检查函数体是否直接返回硬编码数据
            if self._is_mock_function(node):
                self._add_hit(
                    node.lineno,
                    "mock_return",
                    "critical",
                    f"函数 '{node.name}' 可能是模拟函数",
                    self._get_context(node.lineno)
                )
        
        self.generic_visit(node)
        self.current_function = old_func
    
    def _is_mock_function(self, node) -> bool:
        """检查函数是否是模拟函数（返回硬编码数据）"""
        for item in node.body:
            if isinstance(item, ast.Return):
                # 返回字面量字典/列表/字符串
                if isinstance(item.value, (ast.Dict, ast.List, ast.Constant, ast.Str)):
                    return True
                # 返回三引号字符串
                if isinstance(item.value, ast.Expr) and isinstance(item.value.value, ast.Constant):
                    if isinstance(item.value.value.value, str) and '"""' in ast.dump(item.value):
                        return True
        return False
        
    def visit_Return(self, node):
        """检查return语句"""
        # 获取return语句所在的函数体
        if self.current_function:
            line_content = self.lines[node.lineno - 1] if node.lineno <= len(self.lines) else ""
            
            # 检查是否是直接返回字面量（可能是模拟数据）
            if isinstance(node.value, (ast.Dict, ast.List, ast.Constant)):
                if self._is_ai_function():
                    self._add_hit(
                        node.lineno,
                        "mock_return",
                        "high",
                        f"AI相关函数返回硬编码数据: {line_content.strip()[:50]}",
                        self._get_context(node.lineno)
                    )
        
        self.generic_visit(node)
    
    def visit_Comment(self, node):
        """检查注释（通过字符串扫描）"""
        pass  # 注释通过文本扫描处理
    
    def _is_ai_function(self) -> bool:
        """判断当前函数是否是AI相关函数"""
        if not self.current_function:
            return False
        ai_keywords = ['ai', 'llm', 'model', 'generate', 'chat', 'completion', 'embedding']
        return any(k in self.current_function.lower() for k in ai_keywords)
    
    def _get_context(self, lineno: int, window: int = 2) -> str:
        """获取代码上下文"""
        start = max(0, lineno - window - 1)
        end = min(len(self.lines), lineno + window)
        return '\n'.join(f"{i+1}: {self.lines[i]}" for i in range(start, end))
    
    def _add_hit(self, line: int, category: str, severity: str, content: str, context: str = ""):
        self.hits.append(FakeAIHit(
            file=self.filename,
            line=line,
            category=category,
            severity=severity,
            content=content,
            context=context
        ))


def scan_file(filepath: Path) -> List[FakeAIHit]:
    """扫描单个文件"""
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        return []
    
    hits = []
    lines = content.split('\n')
    
    # 只进行文本模式扫描（针对注释中的伪代码标记）
    # 这些是真正的伪代码/模拟实现问题
    patterns = {
        # 匹配中文模拟结果注释（关键模式）
        r'#\s*简化版本.*模拟|#\s*直接返回.*模拟': ("mock_return", "critical"),
        r'#\s*模拟.*结果|#\s*模拟.*返回': ("mock_return", "critical"),
        # 匹配伪代码标记
        r'伪代码|pseudocode': ("pseudo_code", "high"),
        # 匹配TODO AI调用
        r'TODO.*调用AI|FIXME.*调用|实际应调用|实际应该调用': ("todo_ai", "high"),
        # 匹配简化版实现（带"实际应"的才是真正的伪代码）
        r'简化版.*实际应|简化版本.*实际应': ("pseudo_code", "high"),
    }
    
    for i, line in enumerate(lines, 1):
        for pattern, (category, severity) in patterns.items():
            if re.search(pattern, line, re.I):
                hits.append(FakeAIHit(
                    file=str(filepath),
                    line=i,
                    category=category,
                    severity=severity,
                    content=line.strip(),
                    context='\n'.join(lines[max(0,i-3):min(len(lines),i+2)])
                ))
                break  # 每行只报告一次
    
    return hits


def scan_directory(directory: Path, exclude_patterns: List[str] = None) -> Dict[str, List[FakeAIHit]]:
    """扫描整个目录"""
    if exclude_patterns is None:
        exclude_patterns = ['__pycache__', '.git', 'node_modules', '.venv', 'venv']
    
    all_hits = defaultdict(list)
    py_files = list(directory.rglob('*.py'))
    
    print(f"🔍 扫描目录: {directory}")
    print(f"📁 发现 {len(py_files)} 个 Python 文件")
    print()
    
    for filepath in py_files:
        # 跳过排除目录
        if any(p in str(filepath) for p in exclude_patterns):
            continue
            
        hits = scan_file(filepath)
        if hits:
            all_hits[str(filepath)] = hits
    
    return dict(all_hits)


def print_report(results: Dict[str, List[FakeAIHit]]):
    """打印扫描报告"""
    if not results:
        print("✅ 未发现伪AI代码问题")
        return
    
    # 统计
    total_hits = sum(len(h) for h in results.values())
    severity_count = defaultdict(int)
    category_count = defaultdict(int)
    
    for hits in results.values():
        for h in hits:
            severity_count[h.severity] += 1
            category_count[h.category] += 1
    
    print("=" * 80)
    print("📊 BMAD-EVO AI伪代码扫描报告")
    print("=" * 80)
    print()
    print(f"涉及文件: {len(results)} 个")
    print(f"问题总数: {total_hits} 处")
    print()
    print("严重程度分布:")
    for sev in ['critical', 'high', 'medium', 'low']:
        if sev in severity_count:
            emoji = "🔴" if sev == "critical" else "🟠" if sev == "high" else "🟡"
            print(f"  {emoji} {sev.upper()}: {severity_count[sev]} 处")
    print()
    print("问题类型分布:")
    for cat, count in sorted(category_count.items(), key=lambda x: -x[1]):
        print(f"  • {cat}: {count} 处")
    print()
    print("=" * 80)
    print()
    
    # 详细列表（按严重程度排序）
    severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    all_hits = []
    for file, hits in results.items():
        for h in hits:
            all_hits.append(h)
    
    all_hits.sort(key=lambda h: severity_order.get(h.severity, 99))
    
    print("详细问题列表:")
    print()
    
    current_severity = None
    for hit in all_hits:
        if hit.severity != current_severity:
            current_severity = hit.severity
            emoji = "🔴" if hit.severity == "critical" else "🟠" if hit.severity == "high" else "🟡"
            print(f"\n{emoji} {hit.severity.upper()} 级别")
            print("-" * 40)
        
        print(f"\n📄 {hit.file}:{hit.line}")
        print(f"   类别: {hit.category}")
        print(f"   内容: {hit.content[:80]}")
        if hit.context:
            print(f"   上下文:\n{hit.context}")
    
    print()
    print("=" * 80)


def main():
    """主函数"""
    # 扫描路径
    scan_paths = [
        Path('/root/.openclaw/workspace/skills'),
        Path('/root/.openclaw/workspace/projects'),
    ]
    
    all_results = {}
    
    for path in scan_paths:
        if path.exists():
            results = scan_directory(path)
            all_results.update(results)
    
    print_report(all_results)
    
    # 返回码：有问题返回1
    critical_count = sum(1 for hits in all_results.values() for h in hits if h.severity == 'critical')
    high_count = sum(1 for hits in all_results.values() for h in hits if h.severity == 'high')
    
    if critical_count > 0 or high_count > 0:
        print(f"\n⚠️  发现 {critical_count} 个 CRITICAL 和 {high_count} 个 HIGH 级别问题")
        sys.exit(1)
    else:
        print("\n✅ 扫描完成，未发现严重问题")
        sys.exit(0)


if __name__ == "__main__":
    main()
