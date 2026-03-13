#!/usr/bin/env python3
"""
模型切换安全检查工具
切换模型前自动验证上下文配置兼容性
"""
import json
import sys
from pathlib import Path

def get_model_context_window(model_id):
    """获取指定模型的上下文窗口"""
    config_file = Path('/root/.openclaw/openclaw.json')
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    providers = config.get('models', {}).get('providers', {})
    for provider_id, provider in providers.items():
        models = provider.get('models', [])
        for model in models:
            if model.get('id') == model_id:
                return model.get('contextWindow', 128000)
    return 128000  # 默认值

def get_current_compaction_config():
    """获取当前压缩配置"""
    config_file = Path('/root/.openclaw/openclaw.json')
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    agents = config.get('agents', {})
    if isinstance(agents, dict):
        defaults = agents.get('defaults', {})
        return defaults.get('compaction', {})
    return {}

def calculate_safe_thresholds(context_window):
    """计算安全的阈值配置"""
    return {
        'reserveTokensFloor': min(50000, int(context_window * 0.2)),
        'maxHistoryShare': 0.5,
        'softThresholdTokens': int(context_window * 0.75)  # 75% 时触发压缩
    }

def check_compatibility(model_id):
    """检查模型与当前压缩配置的兼容性"""
    context_window = get_model_context_window(model_id)
    compaction = get_current_compaction_config()
    
    print(f"\n=== 模型切换安全检查: {model_id} ===")
    print(f"模型上下文窗口: {context_window:,} tokens")
    print()
    
    # 当前配置
    soft_threshold = compaction.get('memoryFlush', {}).get('softThresholdTokens', 200000)
    reserve_floor = compaction.get('reserveTokensFloor', 50000)
    
    # 计算比例
    soft_ratio = soft_threshold / context_window * 100
    reserve_ratio = reserve_floor / context_window * 100
    
    print("当前配置检查:")
    print(f"  softThresholdTokens: {soft_threshold:,} ({soft_ratio:.1f}%)")
    print(f"  reserveTokensFloor: {reserve_floor:,} ({reserve_ratio:.1f}%)")
    print()
    
    issues = []
    
    if soft_threshold >= context_window:
        issues.append(f"❌ softThresholdTokens ({soft_threshold:,}) >= 上下文窗口 ({context_window:,})")
    elif soft_ratio > 80:
        issues.append(f"⚠️ softThresholdTokens 比例过高 ({soft_ratio:.1f}% > 80%)")
    
    if reserve_floor >= context_window * 0.5:
        issues.append(f"❌ reserveTokensFloor ({reserve_floor:,}) >= 50% 上下文")
    elif reserve_ratio > 30:
        issues.append(f"⚠️ reserveTokensFloor 比例过高 ({reserve_ratio:.1f}% > 30%)")
    
    if issues:
        print("发现的问题:")
        for issue in issues:
            print(f"  {issue}")
        print()
        
        # 建议配置
        safe_config = calculate_safe_thresholds(context_window)
        print("建议的配置:")
        print(f"  reserveTokensFloor: {safe_config['reserveTokensFloor']:,}")
        print(f"  maxHistoryShare: {safe_config['maxHistoryShare']}")
        print(f"  softThresholdTokens: {safe_config['softThresholdTokens']:,}")
        print()
        
        return False, safe_config
    else:
        print("✅ 配置兼容，可以安全切换")
        return True, None

def update_compaction_config(safe_config):
    """更新压缩配置"""
    config_file = Path('/root/.openclaw/openclaw.json')
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 更新 defaults
    if 'agents' in config and isinstance(config['agents'], dict):
        if 'defaults' in config['agents']:
            config['agents']['defaults']['compaction'] = {
                'mode': 'default',
                'reserveTokensFloor': safe_config['reserveTokensFloor'],
                'maxHistoryShare': safe_config['maxHistoryShare'],
                'memoryFlush': {
                    'enabled': True,
                    'softThresholdTokens': safe_config['softThresholdTokens']
                }
            }
    
    # 写回文件
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print("✅ 配置已更新")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python3 check_model_switch.py <model_id>")
        print("\n支持的模型:")
        print("  - k2p5 (262k context)")
        print("  - glm-5 (128k context)")
        print("  - qwen3.5-plus (128k context)")
        print("  - minimax-m2.5 (200k context)")
        sys.exit(1)
    
    model_id = sys.argv[1]
    is_safe, safe_config = check_compatibility(model_id)
    
    if not is_safe and safe_config:
        response = input("\n是否自动更新配置? (y/n): ")
        if response.lower() == 'y':
            update_compaction_config(safe_config)
            print("\n⚠️  请重启 OpenClaw 使配置生效")
        else:
            print("\n⚠️  请手动修改配置后再切换模型")
            sys.exit(1)
