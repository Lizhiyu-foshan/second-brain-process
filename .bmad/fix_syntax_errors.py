#!/usr/bin/env python3
"""
紧急修复语法错误：空的 try/except 块
"""

import sys
from pathlib import Path

FILES_TO_FIX = [
    'evolution_analyzer.py',
    'kimiclaw_v2.py',
    'process_all.py',
    'run_daily_report_progress.py',
    'suggestion_dedup.py',
    'system_evolution.py',
    'system_evolution_ai.py',
]

def fix_syntax_errors(content: str) -> str:
    """修复空的 try/except 块"""
    lines = content.split('\n')
    new_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # 检查是否是空的 try 块
        if line.strip().endswith('try:'):
            # 检查下一行是否有代码
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                # 如果下一行不是缩进的，或者也是 try/except/finally
                if next_line.strip() and not next_line.startswith(' ') and not next_line.startswith('\t'):
                    # 空的 try 块，删除 try:
                    print(f"  修复空 try 块 (行 {i+1})")
                    i += 1
                    continue
                # 如果下一行缩进了，保持 try:
                new_lines.append(line)
                i += 1
                continue
        
        # 检查是否是空的 except 块
        if line.strip().startswith('except') and line.strip().endswith(':'):
            # 检查下一行是否有代码
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                # 如果下一行不是缩进的
                if next_line.strip() and not next_line.startswith(' ') and not next_line.startswith('\t'):
                    # 空的 except 块，添加 pass
                    print(f"  修复空 except 块 (行 {i+1})")
                    indent = line[:len(line) - len(line.lstrip())]
                    new_lines.append(line)
                    new_lines.append(f"{indent}    pass  # TODO: 添加异常处理")
                    i += 1
                    continue
        
        new_lines.append(line)
        i += 1
    
    return '\n'.join(new_lines)

def main():
    base_path = Path('/root/.openclaw/workspace/second-brain-processor')
    
    for file_name in FILES_TO_FIX:
        file_path = base_path / file_name
        if not file_path.exists():
            print(f"❌ 文件不存在：{file_name}")
            continue
        
        print(f"🔧 修复 {file_name}...")
        content = file_path.read_text(encoding='utf-8')
        new_content = fix_syntax_errors(content)
        
        if new_content != content:
            backup_path = file_path.with_suffix('.py.syntax_backup')
            backup_path.write_text(content, encoding='utf-8')
            file_path.write_text(new_content, encoding='utf-8')
            print(f"  ✅ 已修复（备份到 .syntax_backup）")
        else:
            print(f"  ⚠️ 无需修复")
        print()

if __name__ == '__main__':
    main()
