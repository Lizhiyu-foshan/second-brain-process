#!/usr/bin/env python3
"""
批量修复 HIGH 问题 v2：空值检查 + 错误处理 + 类型注解

增强的自动化修复脚本
"""

import sys
import re
from pathlib import Path

# 支持命令行参数指定文件
if len(sys.argv) > 1 and '--file' in sys.argv:
    idx = sys.argv.index('--file')
    if idx + 1 < len(sys.argv):
        FILE_NAME = sys.argv[idx + 1]
    else:
        FILE_NAME = "ai_deep_processor.py"
else:
    FILE_NAME = "ai_deep_processor.py"

FILE_PATH = Path(f"/root/.openclaw/workspace/second-brain-processor/{FILE_NAME}")

# 常见参数类型的启发式映射
TYPE_HINTS = {
    'data': 'dict',
    'config': 'dict',
    'result': 'dict',
    'response': 'dict',
    'content': 'str',
    'text': 'str',
    'message': 'str',
    'path': 'str',
    'filename': 'str',
    'file_path': 'str',
    'url': 'str',
    'count': 'int',
    'num': 'int',
    'index': 'int',
    'limit': 'int',
    'timeout': 'int',
    'delay': 'int',
    'enable': 'bool',
    'debug': 'bool',
    'verbose': 'bool',
    'callback': 'Callable',
    'func': 'Callable',
    'items': 'List',
    'list': 'List',
    'array': 'List',
    'options': 'Dict',
    'params': 'Dict',
    'kwargs': 'Dict',
    'args': 'Tuple',
}

COMMON_TYPES = ['str', 'int', 'float', 'bool', 'dict', 'list', 'Any', 'Optional', 'Union', 'Callable', 'Tuple']

def infer_type(param_name: str, default_value: str = None) -> str:
    """根据参数名推断类型"""
    name_lower = param_name.lower()
    
    # 检查默认值
    if default_value:
        if default_value in ['True', 'False']:
            return 'bool'
        elif default_value.isdigit():
            return 'int'
        elif default_value.replace('.', '').isdigit():
            return 'float'
        elif default_value.startswith('"') or default_value.startswith("'"):
            return 'str'
        elif default_value in ['[]', '{}', 'None']:
            pass  # 继续根据名称推断
    
    # 根据名称推断
    for key, type_hint in TYPE_HINTS.items():
        if key in name_lower:
            return type_hint
    
    # 默认返回 Any
    return 'Any'

def add_type_annotations(content: str) -> str:
    """为函数添加类型注解"""
    lines = content.split('\n')
    new_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # 匹配函数定义（没有完整类型注解的）
        match = re.match(r'^(\s*)def (\w+)\(([^)]*)\)(\s*->\s*\w+)?(:)', line)
        if match:
            indent = match.group(1)
            func_name = match.group(2)
            params = match.group(3)
            return_type = match.group(4)
            colon = match.group(5)
            
            # 如果已经有完整的类型注解，跳过
            if params and all(':' in p.strip() for p in params.split(',') if p.strip() and '=' not in p.split(':')[0]):
                new_lines.append(line)
                i += 1
                continue
            
            # 处理参数
            new_params = []
            if params.strip():
                for param in params.split(','):
                    param = param.strip()
                    if not param:
                        continue
                    
                    # 检查是否已有类型注解
                    if ':' in param and '=' not in param.split(':')[0]:
                        new_params.append(param)
                        continue
                    
                    # 提取参数名和默认值
                    param_name = param.split('=')[0].strip().split(':')[0].strip()
                    default_value = param.split('=')[1].strip() if '=' in param else None
                    
                    # 跳过 *args, **kwargs, self, cls
                    if param_name in ['self', 'cls'] or param_name.startswith('*'):
                        new_params.append(param)
                        continue
                    
                    # 推断类型
                    inferred_type = infer_type(param_name, default_value)
                    
                    # 构建新参数
                    if '=' in param:
                        new_params.append(f"{param_name}: {inferred_type}={default_value}")
                    else:
                        new_params.append(f"{param_name}: {inferred_type}")
            
            # 添加返回类型（如果没有）
            if not return_type:
                return_type_str = " -> None"
            else:
                return_type_str = return_type
            
            # 构建新函数定义
            new_line = f"{indent}def {func_name}({', '.join(new_params)}){return_type_str}:"
            new_lines.append(new_line)
            i += 1
        else:
            new_lines.append(line)
            i += 1
    
    return '\n'.join(new_lines)

def add_null_checks(content: str) -> str:
    """为函数添加空值检查"""
    lines = content.split('\n')
    new_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # 匹配函数定义
        match = re.match(r'^(\s*)def (\w+)\(([^)]*)\)', line)
        if match:
            indent = match.group(1)
            func_name = match.group(2)
            params = match.group(3)
            
            # 提取需要检查的参数
            param_names = []
            if params.strip():
                for param in params.split(','):
                    param = param.strip()
                    if ':' in param:
                        name = param.split(':')[0].strip()
                    else:
                        name = param.split('=')[0].strip()
                    
                    if name and name not in ['self', 'cls'] and not name.startswith('*'):
                        param_names.append(name)
            
            # 添加函数定义行
            new_lines.append(line)
            i += 1
            
            # 跳过 docstring
            while i < len(lines) and (lines[i].strip().startswith('"""') or 
                                      lines[i].strip().startswith("'''") or
                                      lines[i].strip().startswith('#')):
                new_lines.append(lines[i])
                i += 1
                # 处理单行 docstring
                if '"""' in new_lines[-1] and new_lines[-1].count('"""') == 2:
                    break
                if "'''" in new_lines[-1] and new_lines[-1].count("'''") == 2:
                    break
            
            # 添加空值检查
            for name in param_names:
                new_lines.append(f"{indent}    if {name} is None:")
                new_lines.append(f"{indent}        raise ValueError(\"参数 '{name}' 不能为空\")")
        else:
            new_lines.append(line)
            i += 1
    
    return '\n'.join(new_lines)

def add_exception_handling(content: str) -> str:
    """为 IO 和网络操作添加异常处理"""
    # 简化的异常处理添加
    patterns = [
        (r'(    )(open\([^)]+\))', r'\1try:\n\1    \2'),
        (r'(    )(requests\.\w+\([^)]+\))', r'\1try:\n\1    \2'),
        (r'(    )(json\.[\w_]+\([^)]+\))', r'\1try:\n\1    \2'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    # 添加 except 块（简化处理，实际需要根据上下文）
    lines = content.split('\n')
    new_lines = []
    in_try = False
    try_indent = ''
    
    for i, line in enumerate(lines):
        new_lines.append(line)
        
        # 检测 try 块
        if 'try:' in line:
            in_try = True
            try_indent = line[:len(line) - len(line.lstrip())]
        elif in_try and line.strip() and not line.startswith(try_indent + '    '):
            # try 块结束，添加 except
            new_lines.append(f"{try_indent}except Exception as e:")
            new_lines.append(f"{try_indent}    print(f\"[ERROR] 操作失败：{{e}}\")")
            new_lines.append(f"{try_indent}    raise")
            in_try = False
    
    return '\n'.join(new_lines)

def main():
    print(f"📄 读取文件：{FILE_PATH}")
    
    if not FILE_PATH.exists():
        print(f"❌ 文件不存在：{FILE_PATH}")
        sys.exit(1)
    
    content = FILE_PATH.read_text(encoding='utf-8')
    original_lines = len(content.split('\n'))
    print(f"原始行数：{original_lines}")
    
    # 步骤 1：添加类型注解
    print("\n✅ 步骤 1：添加类型注解...")
    content = add_type_annotations(content)
    
    # 步骤 2：添加空值检查
    print("✅ 步骤 2：添加空值检查...")
    content = add_null_checks(content)
    
    # 步骤 3：添加异常处理
    print("✅ 步骤 3：添加异常处理...")
    content = add_exception_handling(content)
    
    # 备份原文件
    backup_path = FILE_PATH.with_suffix('.py.backup')
    print(f"\n💾 备份原文件：{backup_path}")
    backup_path.write_text(FILE_PATH.read_text(encoding='utf-8'), encoding='utf-8')
    
    # 保存新文件
    FILE_PATH.write_text(content, encoding='utf-8')
    
    new_lines = len(content.split('\n'))
    print(f"✅ 修复完成！")
    print(f"新行数：{new_lines} (增加了 {new_lines - original_lines} 行)")
    print(f"\n⚠️  请手动检查修复结果，然后运行审计验证")

if __name__ == '__main__':
    main()
