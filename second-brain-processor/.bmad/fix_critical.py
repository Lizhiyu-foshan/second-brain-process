#!/usr/bin/env python3
"""
CRITICAL 问题自动修复脚本
修复两类问题：
1. 硬编码密钥 → 改为环境变量
2. 空异常处理器 → 添加日志记录
"""

import re
from pathlib import Path

# 项目路径
PROJECT_DIR = Path('/root/.openclaw/workspace/second-brain-processor')

def fix_hardcoded_secrets():
    """修复硬编码密钥问题"""
    print("🔐 修复硬编码密钥...\n")
    
    files_to_fix = {
        'model_router.py': [
            (264, r'["\']sk-\w+["\']', 'DEEPSEEK_API_KEY'),
            (266, r'["\']sk-\w+["\']', 'GLM_API_KEY'),
            (280, r'["\']sk-\w+["\']', 'MINIMAX_API_KEY'),
            (283, r'["\']sk-\w+["\']', 'QWEN_API_KEY'),
            (287, r'["\']sk-\w+["\']', 'OPENAI_API_KEY'),
            (290, r'["\']sk-\w+["\']', 'ANTHROPIC_API_KEY'),
        ],
        'ai_summarizer.py': [
            (80, r'["\']sk-\w+["\']', 'SUMMARIZER_API_KEY'),
        ],
    }
    
    total_fixed = 0
    
    for filename, fixes in files_to_fix.items():
        filepath = PROJECT_DIR / filename
        if not filepath.exists():
            print(f"  ⚠️  {filename} 不存在")
            continue
        
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        modified = False
        for line_num, pattern, env_var in fixes:
            if line_num <= len(lines):
                line_idx = line_num - 1
                if re.search(pattern, lines[line_idx]):
                    # 替换为环境变量
                    old_line = lines[line_idx]
                    new_line = f"        {env_var} = os.getenv('{env_var}')  # TODO: 设置环境变量\n"
                    lines[line_idx] = new_line
                    modified = True
                    total_fixed += 1
                    print(f"  ✅ {filename}:{line_num} - 硬编码密钥 → {env_var}")
        
        if modified:
            # 添加 import os（如果还没有）
            if not any(line.strip().startswith('import os') for line in lines):
                for i, line in enumerate(lines):
                    if line.strip().startswith('import '):
                        lines.insert(i+1, 'import os\n')
                        break
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(lines)
    
    print(f"\n硬编码密钥修复完成：{total_fixed} 个\n")
    return total_fixed


def fix_empty_except_blocks():
    """修复空异常处理器"""
    print("🛡️ 修复空异常处理器...\n")
    
    # 需要修复的文件和行号
    files_to_fix = {
        'daily_report.py': [219],
        'daily_task.py': [281, 293, 305],
        'kimiclaw_v2.py': [72, 74, 736],
        'processor.py': [301, 313, 325],
        'task_executor.py': [181, 183],
        'update_dashboard.py': [60],
        'wechat_fetcher.py': [60],
        'zhihu_crawler.py': [142],
    }
    
    total_fixed = 0
    
    for filename, line_nums in files_to_fix.items():
        filepath = PROJECT_DIR / filename
        if not filepath.exists():
            print(f"  ⚠️  {filename} 不存在")
            continue
        
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        modified = False
        for line_num in line_nums:
            if line_num <= len(lines):
                line_idx = line_num - 1
                line = lines[line_idx].rstrip()
                
                # 检查是否是空的 except 块
                if line == 'except:' or line == 'except Exception:':
                    # 获取下一行的缩进
                    next_line = lines[line_idx + 1] if line_idx + 1 < len(lines) else ''
                    indent = len(next_line) - len(next_line.lstrip())
                    
                    # 替换为带日志的异常处理
                    indent_str = ' ' * indent
                    new_lines = [
                        f"{line}  # 捕获异常\n",
                        f"{indent_str}    import logging\n",
                        f"{indent_str}    logging.exception('异常发生')  # 记录异常堆栈\n",
                        f"{indent_str}    raise  # 重新抛出异常，避免静默吞掉\n",
                    ]
                    
                    lines[line_idx:line_idx+1] = new_lines
                    modified = True
                    total_fixed += 1
                    print(f"  ✅ {filename}:{line_num} - 空 except → 日志记录 + 重新抛出")
        
        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(lines)
    
    print(f"\n空异常处理器修复完成：{total_fixed} 个\n")
    return total_fixed


if __name__ == '__main__':
    print("="*60)
    print("CRITICAL 问题自动修复")
    print("="*60 + "\n")
    
    secrets_fixed = fix_hardcoded_secrets()
    except_fixed = fix_empty_except_blocks()
    
    print("="*60)
    print(f"修复完成！")
    print(f"  硬编码密钥：{secrets_fixed} 个")
    print(f"  空异常处理器：{except_fixed} 个")
    print(f"  总计：{secrets_fixed + except_fixed} 个 CRITICAL 问题")
    print("="*60)
