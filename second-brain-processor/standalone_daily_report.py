#!/usr/bin/env python3
"""
每日复盘报告 - 独立执行脚本
用于 Cron 直接调用，无需 AI 参与
"""

import sys
import os
from datetime import datetime, timedelta

WORKSPACE = "/root/.openclaw/workspace"
PROCESSOR_DIR = f"{WORKSPACE}/second-brain-processor"

sys.path.insert(0, PROCESSOR_DIR)

def generate_report():
    """生成每日复盘报告内容（带真实统计）"""
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    yesterday_str = yesterday.strftime('%Y-%m-%d')
    
    # 统计数据初始化
    stats = {
        'new_articles': 0,
        'processed': 0,
        'pending': 0,
        'conversations': 0,
        'articles': 0,
        'total': 0
    }
    
    try:
        # 统计对话记录
        conv_dir = f"{WORKSPACE}/obsidian-vault/02-Conversations"
        if os.path.exists(conv_dir):
            # 昨天的对话文件
            conv_files = [f for f in os.listdir(conv_dir) if f.startswith(yesterday_str)]
            stats['conversations'] = len(conv_files)
            
            # 统计30天内总对话数
            import glob
            all_conv = glob.glob(f"{conv_dir}/*.md")
            stats['total_conversations'] = len(all_conv)
        
        # 统计文章剪藏
        article_dir = f"{WORKSPACE}/obsidian-vault/03-Articles"
        if os.path.exists(article_dir):
            # 遍历所有子目录
            article_count = 0
            for root, dirs, files in os.walk(article_dir):
                article_count += len([f for f in files if f.endswith('.md')])
            stats['articles'] = article_count
        
        # 统计待处理队列
        queue_file = f"{WORKSPACE}/second-brain-processor/queue.json"
        if os.path.exists(queue_file):
            import json
            with open(queue_file, 'r', encoding='utf-8') as f:
                queue = json.load(f)
            stats['pending'] = len(queue.get('pending', []))
            stats['processed'] = len(queue.get('completed', []))
        
        # 计算总计
        stats['total'] = stats['conversations'] + stats['articles']
        stats['new_articles'] = stats['conversations']  # 昨天的对话作为新增
        
    except Exception as e:
        print(f"[WARNING] 统计时出错: {e}")
    
    # 构建报告
    report = f"""📊 每日复盘报告（{yesterday_str}）

📅 昨日动态
  • 新增文章：{stats['new_articles']} 篇
  • 已处理：{stats['processed']} 条
  • 待处理：{stats['pending']} 条

📚 知识库统计
  • 对话记录：{stats['conversations']} 篇（昨日）/ {stats.get('total_conversations', 0)} 篇（总计）
  • 文章剪藏：{stats['articles']} 篇
  • 总计：{stats['total']} 篇

💡 今日建议
  • 发送链接给我，自动添加到待处理队列
  • 回复'队列'查看待处理列表
  • 回复'统计'查看详细统计

⏰ 报告时间：{today.strftime('%H:%M')}
"""
    return report

def send_report():
    """发送报告到飞书"""
    try:
        from feishu_guardian import send_feishu_safe
        
        content = generate_report()
        target = "ou_363105a68ee112f714ed44e12c802051"
        
        print(f"[INFO] 生成报告内容 ({len(content)} 字符)")
        print(f"[INFO] 正在发送到飞书...")
        
        result = send_feishu_safe(content, target=target, msg_type="daily_report", max_retries=2)
        
        if result["success"]:
            print(f"[SUCCESS] 每日复盘报告已发送到飞书")
            print(f"[INFO] 指纹: {result.get('fingerprint', 'N/A')}")
            return 0
        else:
            print(f"[FAILED] 发送失败: {result['message']}")
            return 1
            
    except Exception as e:
        print(f"[ERROR] 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    print(f"=" * 50)
    print(f"每日复盘报告 - 独立执行脚本")
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=" * 50)
    
    exit_code = send_report()
    
    print(f"=" * 50)
    print(f"执行完成，退出码: {exit_code}")
    print(f"=" * 50)
    
    sys.exit(exit_code)
