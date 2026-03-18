#!/usr/bin/env python3
import sys
import traceback

# 添加 workspace 到路径
sys.path.insert(0, '/root/.openclaw/workspace')

print("=== 测试配置导入 ===")
print(f"Python 路径：{sys.path[:3]}")

try:
    from config.config_loader import Config
    print("✅ 导入 config.config_loader 成功")
    
    config = Config()
    print(f"✅ 创建 Config 实例成功：{config.workspace}")
    print(f"✅ Vault Dir: {config.get_path('directories.obsidian_vault')}")
    print(f"✅ API Key: {'已配置' if config.get_api_key('alicloud') else '未配置'}")
    
except Exception as e:
    print(f"❌ 导入失败：{e}")
    traceback.print_exc()

print("\n=== 测试 from second-brain-processor.config 导入 ===")
try:
    import second_brain_processor.config as sb_config
    print(f"✅ 导入 second_brain_processor.config 成功")
    print(f"   NEW_CONFIG_AVAILABLE: {sb_config.NEW_CONFIG_AVAILABLE}")
    print(f"   WORKSPACE: {sb_config.WORKSPACE}")
except Exception as e:
    print(f"❌ 导入失败：{e}")
    traceback.print_exc()
