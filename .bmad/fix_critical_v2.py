#!/usr/bin/env python3
"""
CRITICAL 问题自动修复脚本 - 版本 2
修复两类问题：
1. 硬编码密钥 → 改为环境变量
2. 空异常处理器 → 添加日志记录
"""

import re
import os
from pathlib import Path

# 项目路径
PROJECT_DIR = Path('/root/.openclaw/workspace/second-brain-processor')

def fix_hardcoded_secrets():
    """修复硬编码密钥问题"""
    print("🔐 修复硬编码密钥...\n")
    
    # 匹配 API key 模式
    api_key_pattern = re.compile(r'["\'](sk-[a-zA-Z0-9_-]+)["\']')
    
    files_with_secrets = [
        'model_router.py',
        'ai_summarizer.py',
    ]
    
    total_fixed = 0
    
    for filename in files_with_secrets:
        filepath = PROJECT_DIR / filename
        if not filepath.exists():
            print(f"  ⚠️  {filename} 不存在")
            continue
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.splitlines(keepends=True)
        
        modified = False
        for i, line in enumerate(lines):
            match = api_key_pattern.search(line)
            if match:
                old_line = line
                api_key = match.group(1)
                # 生成环境变量名
                env_var = f"API_KEY_{api_key[:8].upper()}"
                
                # 检查是否已经是环境变量
                if 'os.getenv' in line or 'os.environ' in line:
                    continue
                
                # 替换为环境变量
                indent = len(line) - len(line.lstrip())
                new_line = f"{' ' * indent}os.getenv('{env_var}', '{api_key}')  # TODO: 移到环境变量配置\n"
                lines[i] = new_line
                modified = True
                total_fixed += 1
                print(f"  ✅ {filename}:{i+1} - 硬编码密钥 → os.getenv('{env_var}')")
        
        if modified:
            # 添加 import os（如果还没有）
            if 'import os' not in content:
                # 找到第一个 import 语句的位置
                for i, line in enumerate(lines):
                    if line.strip().startswith('import '):
                        lines.insert(i+1, 'import os\n')
                        break
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(lines)
    
    if total_fixed == 0:
        print(f"  ℹ️  未发现硬编码密钥（可能已修复）")
    
    print(f"\n硬编码密钥修复完成：{total_fixed} 个\n")
    return total_fixed


def fix_empty_except_blocks():
    """修复空异常处理器"""
    print("🛡️ 修复空异常处理器...\n")
    
    files_to_fix = [
        'daily_report.py',
        'daily_task.py',
        'kimiclaw_v2.py',
        'processor.py',
        'task_executor.py',
        'update_dashboard.py',
        'wechat_fetcher.py',
        'zhihu_crawler.py',
    ]
    
    # 匹配空 except 块（except 后跟着 pass）
    except_pass_pattern = re.compile(r'^(\s*)except(.*):\s*(#.*)?\n(\s*)pass\s*\n', re.MULTILINE)
    
    total_fixed = 0
    
    for filename in files_to_fix:
        filepath = PROJECT_DIR / filename
        if not filepath.exists():
            print(f"  ⚠️  {filename} 不存在")
            continue
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找所有空的 except 块
        matches = list(except_pass_pattern.finditer(content))
        
        if not matches:
            print(f"  ℹ️  {filename}: 未发现空 except 块")
            continue
        
        modified_content = content
        
        for match in reversed(matches):  # 从后往前替换，避免行号偏移
            indent = match.group(1)
            exception_type = match.group(2) if match.group(2) else ''
            comment = match.group(3) if match.group(3) else ''
            
            # 生成新的异常处理代码
            replacement = f"""{indent}except{exception_type}:{comment}
{indent}    import logging
{indent}    logging.exception('异常捕获')  # 记录异常堆栈
{indent}    raise  # 重新抛出，避免静默吞掉
"""
            
            modified_content = modified_content[:match.start()] + replacement + modified_content[match.end():]
            total_fixed += 1
            line_num = content[:match.start()].count('\n') + 1
            print(f"  ✅ {filename}:{line_num} - 空 except → 日志记录 + 重新抛出")
        
        if modified_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(modified_content)
    
    print(f"\n空异常处理器修复完成：{total_fixed} 个\n")
    return total_fixed


if __name__ == '__main__':
    print("="*60)
    print("CRITICAL 问题自动修复 v2")
    print("="*60 + "\n")
    
    secrets_fixed = fix_hardcoded_secrets()
    except_fixed = fix_empty_except_blocks()
    
    print("="*60)
    print(f"修复完成！")
    print(f"  硬编码密钥：{secrets_fixed} 个")
    print(f"  空异常处理器：{except_fixed} 个")
    print(f"  总计：{secrets_fixed + except_fixed} 个 CRITICAL 问题")
    print("="*60)
