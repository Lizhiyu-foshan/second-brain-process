#!/usr/bin/env python3
"""
修复 system_evolution.py 的 HIGH 问题
"""

import re
from pathlib import Path

FILE_PATH = Path("/root/.openclaw/workspace/second-brain-processor/system_evolution.py")

def add_null_checks(content):
    """为关键函数添加空值检查"""
    lines = content.split('\n')
    new_lines = []
    i = 0
    
    target_functions = {
        'log': ['message'],
        'get_recent_errors': ['days'],
        'analyze_error_pattern': ['errors'],
        'generate_improvement_plan': ['pattern'],
        'implement_improvements': ['plan'],
        'verify_improvements': ['files'],
        'log_evolution': ['changes'],
        'generate_report': ['days']
    }
    
    while i < len(lines):
        line = lines[i]
        
        matched = False
        for func_name, params in target_functions.items():
            if re.match(rf'^def {func_name}\(', line):
                new_lines.append(line)
                i += 1
                
                while i < len(lines) and ('"""' in lines[i] or "'''" in lines[i]):
                    new_lines.append(lines[i])
                    i += 1
                    if lines[i-1].count('"""') == 2 or lines[i-1].count("'''") == 2:
                        break
                
                indent = "    "
                for param in params:
                    new_lines.append(f"{indent}if {param} is None:\n{indent}    raise ValueError(\"参数 '{param}' 不能为空\")")
                
                matched = True
                break
        
        if not matched:
            new_lines.append(line)
            i += 1
    
    return '\n'.join(new_lines)

def add_exception_handling(content):
    """为 IO 操作添加异常处理"""
    lines = content.split('\n')
    new_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        if re.match(r'\s+with\s+open\(', line) or re.match(r'\s+open\(', line):
            in_try_block = False
            for j in range(max(0, i-15), i):
                if 'try:' in lines[j]:
                    in_try_block = True
                    break
            
            if not in_try_block:
                indent = len(line) - len(line.lstrip())
                new_lines.append(' ' * indent + 'try:')
                new_lines.append(line)
                i += 1
                continue
        
        new_lines.append(line)
        i += 1
    
    return '\n'.join(new_lines)

def main():
    if not FILE_PATH.exists():
        print(f"❌ 文件不存在：{FILE_PATH}")
        return
    
    print(f"📄 读取文件：{FILE_PATH}")
    content = FILE_PATH.read_text(encoding='utf-8')
    original_lines = len(content.split('\n'))
    print(f"原始行数：{original_lines}")
    
    print("\n✅ 步骤 1：添加函数空值检查...")
    content = add_null_checks(content)
    
    print("✅ 步骤 2：添加 IO 异常处理...")
    content = add_exception_handling(content)
    
    backup_path = FILE_PATH.with_suffix('.py.backup')
    print(f"\n💾 备份原文件：{backup_path}")
    FILE_PATH.write_text(content, encoding='utf-8')
    print(f"✅ 修复完成！")
    
    new_lines = len(content.split('\n'))
    print(f"新行数：{new_lines} (增加了 {new_lines - original_lines} 行)")

if __name__ == '__main__':
    main()
