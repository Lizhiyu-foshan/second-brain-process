#!/usr/bin/env python3
"""
AI深度整理批量处理器 - 支持定时触发和补整理

功能：
1. 定时触发：每天凌晨自动处理队列中的内容
2. 补整理机制：可以重新整理指定日期范围的内容
3. 深度AI处理：使用子Agent进行真正的理解
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

# 路径配置
WORKSPACE = Path("/root/.openclaw/workspace")
PROCESSOR_DIR = WORKSPACE / "second-brain-processor"
QUEUE_DIR = PROCESSOR_DIR / "queue"
VAULT_DIR = WORKSPACE / "obsidian-vault"
MEMORY_DIR = WORKSPACE / "memory"

def log(message: str):
    """日志输出"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def get_queue_files() -> List[Dict]:
    """获取队列中的文件列表"""
    files = []
    if not QUEUE_DIR.exists():
        return files
    
    for md_file in QUEUE_DIR.glob("*.md"):
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析 frontmatter
            frontmatter = {}
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    fm_text = parts[1]
                    for line in fm_text.strip().split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            frontmatter[key.strip()] = value.strip().strip('"').strip("'")
            
            title = frontmatter.get('title', md_file.stem)
            source = frontmatter.get('source', '未知')
            tags = json.loads(frontmatter.get('tags', '[]'))
            
            files.append({
                'path': str(md_file),
                'title': title,
                'source': source,
                'tags': tags,
                'filename': md_file.name
            })
        except Exception as e:
            log(f"解析文件失败 {md_file}: {e}")
    
    return files

def process_file_with_ai(file_info: Dict, mode: str = "deep") -> Dict:
    """
    使用AI深度处理单个文件
    
    Args:
        file_info: 文件信息
        mode: 处理模式 (deep=深度处理, reprocess=重新处理)
    """
    file_path = Path(file_info['path'])
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        log(f"处理文件: {file_info['title']}")
        
        # 导入深度处理模块
        sys.path.insert(0, str(PROCESSOR_DIR))
        from ai_deep_processor import process_chat_record, ai_deep_process, generate_obsidian_note
        
        # 判断来源类型
        source = file_info.get('source', '未知')
        tags = file_info.get('tags', [])
        
        # 根据类型选择处理方式
        if '聊天记录' in tags or source == '聊天记录':
            result = process_chat_record(original_content, file_info['title'], 
                                        datetime.now().strftime('%Y-%m-%d'))
            source_type = "聊天记录"
            target_dir = VAULT_DIR / '02-Conversations'
        elif source == '知乎':
            result = ai_deep_process(original_content, file_info['title'], 'article')
            source_type = "文章剪藏"
            target_dir = VAULT_DIR / '03-Articles/Zhihu'
        elif source == '微信':
            result = ai_deep_process(original_content, file_info['title'], 'article')
            source_type = "文章剪藏"
            target_dir = VAULT_DIR / '03-Articles/WeChat'
        else:
            result = ai_deep_process(original_content, file_info['title'], 'note')
            source_type = "笔记"
            target_dir = VAULT_DIR / '03-Articles'
        
        # 生成Obsidian笔记
        note_content = generate_obsidian_note(
            result, original_content, file_info['title'], 
            source=source_type, tags=tags
        )
        
        # 保存到目标目录
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / file_path.name
        
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(note_content)
        
        # 删除队列文件
        file_path.unlink()
        
        log(f"  ✓ 已保存到: {target_file}")
        
        return {
            'success': True,
            'title': file_info['title'],
            'target_file': str(target_file),
            'themes': result.get('themes', []),
            'key_takeaway': result.get('key_takeaway', '')
        }
        
    except Exception as e:
        log(f"  ✗ 处理失败: {e}")
        return {
            'success': False,
            'title': file_info['title'],
            'error': str(e)
        }

def sync_to_github(commit_msg: str = None) -> bool:
    """同步到GitHub"""
    try:
        sys.path.insert(0, str(PROCESSOR_DIR))
        from git_sync import commit_and_sync
        
        result = commit_and_sync(commit_msg)
        return result.get('success', False)
    except Exception as e:
        log(f"GitHub同步失败: {e}")
        return False

def process_all_queue(mode: str = "deep", dry_run: bool = False) -> Dict:
    """
    处理队列中所有文件
    
    Args:
        mode: deep=深度处理, reprocess=重新处理
        dry_run: 仅预览，不实际执行
    """
    log(f"\n{'='*50}")
    log(f"开始批量处理 (模式: {mode})")
    log(f"{'='*50}")
    
    files = get_queue_files()
    
    if not files:
        log("队列为空，无需处理")
        return {'success': True, 'processed': 0, 'failed': 0}
    
    log(f"发现 {len(files)} 个待处理文件\n")
    
    results = []
    success_count = 0
    fail_count = 0
    
    for i, file_info in enumerate(files, 1):
        log(f"[{i}/{len(files)}] {file_info['title']}")
        
        if dry_run:
            log(f"  [预览模式] 跳过处理")
            continue
        
        result = process_file_with_ai(file_info, mode)
        results.append(result)
        
        if result['success']:
            success_count += 1
        else:
            fail_count += 1
        
        # 添加小延迟避免过载
        time.sleep(1)
    
    # 同步到GitHub
    if not dry_run and success_count > 0:
        log("\n同步到GitHub...")
        sync_result = sync_to_github(f"AI深度整理: {success_count} 个文件")
        if sync_result:
            log("  ✓ 同步成功")
        else:
            log("  ✗ 同步失败，将在下次补推")
    
    log(f"\n{'='*50}")
    log(f"处理完成: 成功 {success_count}, 失败 {fail_count}")
    log(f"{'='*50}\n")
    
    return {
        'success': fail_count == 0,
        'processed': success_count,
        'failed': fail_count,
        'results': results
    }

def reprocess_date_range(from_date: str, to_date: str = None) -> Dict:
    """
    补整理机制：重新处理指定日期范围的内容
    
    Args:
        from_date: 开始日期 (YYYY-MM-DD)
        to_date: 结束日期 (YYYY-MM-DD)，默认为今天
    """
    if to_date is None:
        to_date = datetime.now().strftime('%Y-%m-%d')
    
    log(f"\n{'='*50}")
    log(f"补整理模式: {from_date} 至 {to_date}")
    log(f"{'='*50}\n")
    
    # 查找该日期范围内的文件
    from_dt = datetime.strptime(from_date, '%Y-%m-%d')
    to_dt = datetime.strptime(to_date, '%Y-%m-%d')
    
    # 查找已处理的文件（在Vault中）
    files_to_reprocess = []
    
    for search_dir in [VAULT_DIR / '02-Conversations', VAULT_DIR / '03-Articles']:
        if not search_dir.exists():
            continue
        
        for md_file in search_dir.rglob("*.md"):
            try:
                # 检查文件日期
                file_stat = md_file.stat()
                file_mtime = datetime.fromtimestamp(file_stat.st_mtime)
                
                if from_dt <= file_mtime <= to_dt:
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 检查是否是旧格式（#待整理 标签）
                    if '#待整理' in content or 'status: 待整理' in content:
                        files_to_reprocess.append({
                            'path': str(md_file),
                            'title': md_file.stem,
                            'source': '待重新处理',
                            'tags': ['聊天记录', '待整理']
                        })
            except Exception as e:
                continue
    
    log(f"找到 {len(files_to_reprocess)} 个需要重新处理的文件")
    
    if not files_to_reprocess:
        return {'success': True, 'processed': 0, 'message': '无需重新处理'}
    
    # 重新处理
    success_count = 0
    for file_info in files_to_reprocess:
        result = process_file_with_ai(file_info, mode="reprocess")
        if result['success']:
            success_count += 1
        time.sleep(1)
    
    # 同步
    if success_count > 0:
        sync_to_github(f"补整理: {from_date} 至 {to_date}")
    
    return {
        'success': True,
        'processed': success_count,
        'total': len(files_to_reprocess)
    }

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AI深度整理处理器')
    parser.add_argument('--mode', choices=['deep', 'reprocess'], default='deep',
                       help='处理模式: deep=深度处理, reprocess=重新处理')
    parser.add_argument('--dry-run', action='store_true',
                       help='预览模式，不实际执行')
    parser.add_argument('--reprocess-from', type=str,
                       help='补整理起始日期 (YYYY-MM-DD)')
    parser.add_argument('--reprocess-to', type=str,
                       help='补整理结束日期 (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    if args.reprocess_from:
        # 补整理模式
        result = reprocess_date_range(args.reprocess_from, args.reprocess_to)
    else:
        # 正常处理模式
        result = process_all_queue(mode=args.mode, dry_run=args.dry_run)
    
    # 输出结果摘要
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    return 0 if result['success'] else 1

if __name__ == "__main__":
    sys.exit(main())
