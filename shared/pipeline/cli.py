#!/usr/bin/env python3
"""
Pipeline CLI
双层任务编排系统命令行入口
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, '/root/.openclaw/workspace/shared/pipeline')

from layer1.api import ResourceSchedulerAPI


def main():
    """主函数"""
    print("=" * 60)
    print("双层任务编排系统 - Pipeline CLI")
    print("=" * 60)
    
    # 初始化API
    api = ResourceSchedulerAPI()
    
    # 获取统计信息
    stats = api.get_statistics()
    
    print(f"\n📊 系统状态:")
    print(f"  角色总数: {stats['roles']['total']}")
    print(f"  空闲角色: {stats['roles']['idle']}")
    print(f"  忙碌角色: {stats['roles']['busy']}")
    print(f"  活跃锁: {stats['locks']['active']}")
    
    print(f"\n📋 任务统计:")
    for status, count in stats['tasks'].items():
        print(f"  {status}: {count}")
    
    print("\n" + "=" * 60)
    print("可用命令:")
    print("  status  - 查看系统状态")
    print("  cleanup - 清理过期锁")
    print("  help    - 显示帮助")
    print("=" * 60)


if __name__ == "__main__":
    main()
