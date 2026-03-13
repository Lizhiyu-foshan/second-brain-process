#!/usr/bin/env python3
"""
Second Brain 统一处理入口
整合所有处理流程，确保完整一致的执行

流程：
1. 解析用户选择（批量A1/A2/A3 或 差异化B+1/2/3）
2. 逐篇处理文章（每篇处理后立即展示结果）
3. 双向同步到 GitHub（fetch -> merge -> push，失败重试3次）
4. 反馈同步结果（成功/失败+重试次数+建议操作）
"""

import json
import sys
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from processor import get_queue_list, extract_title
from ai_processor import ai_process_content
from git_sync import commit_and_sync

QUEUE_DIR = Path("/root/.openclaw/workspace/second-brain-processor/queue")
VAULT_DIR = Path("/root/.openclaw/workspace/obsidian-vault")

def process_single_file(file_info: dict, mode: str = "summary") -> dict:
    """处理单个文件并返回结果"""
    try:
        file_path = Path(file_info['path'])
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        content_length = len(content)
        preview = content[:200] + "..." if len(content) > 200 else content
        
        # AI 处理
        ai_result = ai_process_content(content, file_info['title'])
        
        # 更新内容
        content = content.replace('待 AI 提炼一句话核心观点', ai_result['key_takeaway'])
        
        if ai_result['core_points']:
            points_str = '\n'.join([f'- {p}' for p in ai_result['core_points']])
            content = content.replace('- 待提炼要点', points_str)
        
        if ai_result['related_thoughts']:
            thoughts_str = '\n'.join([f'- {t}' for t in ai_result['related_thoughts']])
            content = content.replace('- 与 [[待补充]] 的关联：...', thoughts_str)
        
        content = content.replace('#待整理', '#已处理')
        content = content.replace('tags: [文章剪藏', 'tags: [文章剪藏, 已处理')
        
        # 确定目标目录
        source = file_info.get('source', '未知')
        tags = file_info.get('tags', [])
        
        # 检查是否是聊天记录
        if '聊天记录' in tags or source == '聊天记录':
            target_dir = VAULT_DIR / '02-Conversations'
        elif source == '知乎':
            target_dir = VAULT_DIR / '03-Articles/Zhihu'
        elif source == '微信':
            target_dir = VAULT_DIR / '03-Articles/WeChat'
        else:
            target_dir = VAULT_DIR / '03-Articles'
        
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / file_path.name
        
        # 根据模式保存
        if mode == 'full':
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(original_content)
            result_data = {
                "mode": "full",
                "content_length": content_length,
                "preview": preview
            }
        else:
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(content)
            result_data = {
                "mode": "summary",
                "key_takeaway": ai_result['key_takeaway'],
                "core_points": ai_result['core_points'][:5]
            }
        
        # 删除队列文件
        file_path.unlink()
        
        return {
            "success": True,
            "title": file_info['title'],
            "target_file": str(target_file),
            "data": result_data
        }
        
    except Exception as e:
        return {
            "success": False,
            "title": file_info.get('title', '未知'),
            "error": str(e)
        }

def format_result_for_display(result: dict) -> str:
    """格式化结果用于展示"""
    if not result.get('success'):
        return f"❌ 《{result.get('title', '未知')}》处理失败：{result.get('error', '未知错误')}"
    
    title = result['title']
    data = result.get('data', {})
    mode = data.get('mode', 'summary')
    
    if mode == 'full':
        return f"""✅ 《{title}》
📊 文章长度：{data['content_length']} 字

📝 开头预览：
{data['preview']}
---"""
    else:
        key_takeaway = data.get('key_takeaway', '待提炼')
        core_points = data.get('core_points', [])
        points_text = '\n'.join([f"• {p}" for p in core_points]) if core_points else "• 待提炼"
        
        return f"""✅ 《{title}》

🔑 Key Takeaway：
{key_takeaway}

📋 核心要点：
{points_text}
---"""

def process_batch(modes: list) -> dict:
    """
    批量处理流程
    modes: 每篇的处理模式列表，长度等于文件数
    """
    files = get_queue_list()
    
    if not files:
        return {"success": True, "has_content": False, "message": "队列为空"}
    
    if len(modes) != len(files):
        # 如果模式数量不匹配，使用第一个模式处理所有
        modes = [modes[0]] * len(files)
    
    results = []
    
    # 1. 逐篇处理并展示
    for i, (file_info, mode) in enumerate(zip(files, modes), 1):
        result = process_single_file(file_info, mode)
        results.append(result)
        
        # 立即展示
        print(f"\n📄 第 {i}/{len(files)} 篇处理完成：")
        print(format_result_for_display(result))
    
    # 2. 双向同步
    print("\n🔄 开始双向同步到 GitHub...")
    success_count = sum(1 for r in results if r.get('success'))
    commit_msg = f"处理 {success_count} 篇笔记 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    sync_result = commit_and_sync(commit_msg)
    
    # 3. 反馈结果
    retry_count = sync_result.get('retry_count', 0)
    
    # 4. 检查 Dashboard 更新状态
    dashboard_updated = sync_result.get('dashboard_updated', False)
    if not dashboard_updated and sync_result.get('success'):
        dashboard_error = sync_result.get('dashboard_error', '未知错误')
        print(f"⚠️ Dashboard 更新失败: {dashboard_error}")
    
    if sync_result.get('success'):
        sync_status = "✅ 已成功同步到 GitHub"
        needs_action = False
    elif retry_count >= 3:
        sync_status = f"❌ 同步失败（已重试3次）\n请检查网络连接或手动执行同步"
        needs_action = True
    else:
        sync_status = f"❌ 同步失败（重试{retry_count}次）\n错误：{sync_result.get('steps', [])[-1].get('error', '未知错误')}"
        needs_action = True
    
    # 输出最终结果
    print("\n" + "="*40)
    print(sync_status)
    
    if needs_action:
        print("\n💡 建议操作：")
        print("1. 检查网络连接")
        print("2. 手动运行：cd /root/.openclaw/workspace/obsidian-vault && git push")
        print("3. 或稍后再试")
    
    return {
        "success": sync_result.get('success', False),
        "has_content": True,
        "processed_count": len(results),
        "success_count": success_count,
        "sync_status": sync_status,
        "needs_action": needs_action
    }

def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Second Brain 统一处理')
    parser.add_argument('mode', nargs='?', default='summary',
                       choices=['full', 'summary', 'brief'],
                       help='处理模式：full=原文保存, summary=主体+核心观点, brief=精简摘要')
    parser.add_argument('--batch', action='store_true',
                       help='批量处理所有队列中的文件')
    
    args = parser.parse_args()
    
    if args.batch:
        # 批量处理
        files = get_queue_list()
        if files:
            modes = [args.mode] * len(files)
            result = process_batch(modes)
        else:
            print("队列为空，无需处理")
    else:
        # 单文件处理（用于差异化模式）
        files = get_queue_list()
        if files:
            result = process_batch([args.mode])
        else:
            print("队列为空，无需处理")

if __name__ == "__main__":
    main()
