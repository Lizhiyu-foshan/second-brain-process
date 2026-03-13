#!/usr/bin/env python3
"""
周一美术馆展览推送 - 子会话执行脚本
创建一个独立的子会话来执行搜索和推送
"""
import subprocess
import sys

def main():
    """创建子会话执行展览推送"""
    
    task_description = """【定时任务】周一美术馆展览推送

你必须执行以下步骤：

**步骤1**：搜索展览信息
- 使用 kimi_search 搜索"和美术馆 展览 2026"
- 使用 kimi_search 搜索"广东美术馆 展览 2026"
- 使用 kimi_search 搜索"另一个美术馆 展览 2026"

**步骤2**：整理搜索结果
- 只展示结束日期 >= 2026-03-16 的展览
- 已结束的展览（如毕加索与达利展 2026.2.8已结束）不展示
- 7天内结束的展览置顶标注"还剩X天，抓紧去看！"

**步骤3**：发送推送
- 使用 message 工具发送整理后的展览信息给用户 ou_363105a68ee112f714ed44e12c802051
- 消息标题必须包含"🎨 周一美术馆展览推送"

**临期展览提醒**：
- 另一个美术馆《光·束》3月10日结束（还剩X天）
- 广东美术馆黄永玉展 3月15日结束（还剩X天）
- 广东美术馆德化瓷展 3月15日结束（还剩X天）

重要：
- 必须实际调用 message 工具发送
- 不能只生成文字不发送
- 完成后静默（NO_REPLY）
"""
    
    # 使用 sessions_spawn 创建子会话执行任务
    result = subprocess.run(
        [
            "openclaw", "sessions", "spawn",
            "--task", task_description,
            "--agentId", "main",
            "--runTimeoutSeconds", "120",
            "--cleanup", "delete"
        ],
        capture_output=True,
        text=True
    )
    
    print(f"子会话执行结果:")
    print(f"返回码: {result.returncode}")
    print(f"输出: {result.stdout}")
    if result.stderr:
        print(f"错误: {result.stderr}")
    
    return result.returncode == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
