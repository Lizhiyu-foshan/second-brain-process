#!/usr/bin/env python3
"""
OpenClaw 模型切换自动化脚本
功能：检查 → 调整配置 → 切换模型 → 验证
"""
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

MODEL_CONFIGS = {
    'k2p5': {'context_window': 262144, 'description': 'Kimi K2.5'},
    'glm-5': {'context_window': 128000, 'description': 'GLM-5'},
    'qwen3.5-plus': {'context_window': 128000, 'description': 'Qwen 3.5 Plus'},
    'MiniMax-M2.5': {'context_window': 204800, 'description': 'MiniMax M2.5'}
}

def get_config():
    """获取当前配置"""
    with open('/root/.openclaw/openclaw.json', 'r') as f:
        return json.load(f)

def save_config(config):
    """保存配置"""
    with open('/root/.openclaw/openclaw.json', 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def calculate_compression_config(context_window):
    """计算最佳压缩配置"""
    return {
        'mode': 'default',
        'reserveTokensFloor': min(50000, int(context_window * 0.2)),
        'maxHistoryShare': 0.5,
        'memoryFlush': {
            'enabled': True,
            'softThresholdTokens': int(context_window * 0.75)
        }
    }

def update_model_config(config, model_id, provider):
    """更新模型配置"""
    # 更新 agents.defaults.model
    config['agents']['defaults']['model'] = {
        'provider': provider,
        'model': model_id
    }
    return config

def update_compression_config(config, model_id):
    """更新压缩配置"""
    if model_id not in MODEL_CONFIGS:
        print(f"❌ 未知模型: {model_id}")
        return None
    
    context_window = MODEL_CONFIGS[model_id]['context_window']
    compression_config = calculate_compression_config(context_window)
    
    config['agents']['defaults']['compaction'] = compression_config
    return config

def switch_model(model_id, provider=None, auto_restart=False):
    """
    切换模型（完整流程）
    
    Args:
        model_id: 模型ID
        provider: 提供商（可选，自动检测）
        auto_restart: 是否自动重启
    """
    print(f"\n🚀 开始切换模型: {model_id}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 1. 验证模型
    if model_id not in MODEL_CONFIGS:
        print(f"❌ 错误: 未知模型 '{model_id}'")
        print(f"支持的模型: {', '.join(MODEL_CONFIGS.keys())}")
        return False
    
    model_info = MODEL_CONFIGS[model_id]
    print(f"\n📋 模型信息:")
    print(f"  名称: {model_info['description']}")
    print(f"  上下文窗口: {model_info['context_window']:,} tokens")
    
    # 2. 获取当前配置
    config = get_config()
    
    # 3. 更新压缩配置
    print(f"\n🔧 步骤1: 调整压缩配置...")
    config = update_compression_config(config, model_id)
    if not config:
        return False
    
    new_config = config['agents']['defaults']['compaction']
    print(f"  ✅ 压缩配置已更新:")
    print(f"     mode: {new_config['mode']}")
    print(f"     reserveTokensFloor: {new_config['reserveTokensFloor']:,}")
    print(f"     softThresholdTokens: {new_config['memoryFlush']['softThresholdTokens']:,}")
    
    # 4. 更新模型配置
    print(f"\n🔧 步骤2: 更新模型配置...")
    if not provider:
        # 自动检测提供商
        if model_id in ['k2p5']:
            provider = 'kimi-coding'
        else:
            provider = 'alicloud'
    
    config = update_model_config(config, model_id, provider)
    print(f"  ✅ 模型配置已更新:")
    print(f"     model: {model_id}")
    print(f"     provider: {provider}")
    
    # 5. 保存配置
    print(f"\n💾 步骤3: 保存配置...")
    save_config(config)
    print(f"  ✅ 配置已保存到 openclaw.json")
    
    # 6. 重启（如果需要）
    if auto_restart:
        print(f"\n🔄 步骤4: 重启 OpenClaw...")
        result = subprocess.run(['openclaw', 'gateway', 'restart'], 
                              capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print(f"  ✅ OpenClaw 已重启")
        else:
            print(f"  ⚠️ 重启可能失败: {result.stderr}")
    else:
        print(f"\n⚠️  请手动重启 OpenClaw 使配置生效:")
        print(f"   openclaw gateway restart")
    
    # 7. 验证
    print(f"\n✅ 切换完成!")
    print(f"\n📊 新配置摘要:")
    print(f"  模型: {model_id} ({model_info['description']})")
    print(f"  上下文窗口: {model_info['context_window']:,} tokens")
    print(f"  压缩触发阈值: {new_config['memoryFlush']['softThresholdTokens']:,} tokens (75%)")
    print(f"  预留空间: {new_config['reserveTokensFloor']:,} tokens")
    
    return True

def verify_current_model():
    """验证当前模型配置"""
    print(f"\n🔍 验证当前配置")
    print("="*60)
    
    config = get_config()
    
    # 获取当前模型
    current_model = config.get('agents', {}).get('defaults', {}).get('model', 'unknown')
    if isinstance(current_model, dict):
        current_model = current_model.get('model', 'unknown')
    
    print(f"当前模型: {current_model}")
    
    # 获取压缩配置
    compaction = config.get('agents', {}).get('defaults', {}).get('compaction', {})
    print(f"压缩模式: {compaction.get('mode', 'not set')}")
    print(f"softThresholdTokens: {compaction.get('memoryFlush', {}).get('softThresholdTokens', 'not set')}")
    print(f"reserveTokensFloor: {compaction.get('reserveTokensFloor', 'not set')}")
    
    # 验证兼容性
    if current_model in MODEL_CONFIGS:
        context_window = MODEL_CONFIGS[current_model]['context_window']
        soft = compaction.get('memoryFlush', {}).get('softThresholdTokens', 0)
        reserve = compaction.get('reserveTokensFloor', 0)
        
        soft_ratio = soft / context_window * 100 if context_window > 0 else 0
        reserve_ratio = reserve / context_window * 100 if context_window > 0 else 0
        
        print(f"\n兼容性检查:")
        print(f"  softThresholdTokens: {soft:,} / {context_window:,} = {soft_ratio:.1f}%")
        print(f"  reserveTokensFloor: {reserve:,} / {context_window:,} = {reserve_ratio:.1f}%")
        
        if soft_ratio < 80 and reserve_ratio < 30:
            print(f"  ✅ 配置兼容")
        else:
            print(f"  ⚠️ 配置可能需要调整")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("OpenClaw 模型切换自动化脚本")
        print("\n用法:")
        print(f"  {sys.argv[0]} <model_id> [--restart]")
        print(f"\n支持的模型:")
        for mid, info in MODEL_CONFIGS.items():
            print(f"  {mid:20} - {info['description']} ({info['context_window']:,} tokens)")
        print(f"\n示例:")
        print(f"  {sys.argv[0]} glm-5           # 切换并手动重启")
        print(f"  {sys.argv[0]} glm-5 --restart # 切换并自动重启")
        print(f"  {sys.argv[0]} --verify        # 验证当前配置")
        sys.exit(1)
    
    if sys.argv[1] == '--verify':
        verify_current_model()
    else:
        model_id = sys.argv[1]
        auto_restart = '--restart' in sys.argv
        
        success = switch_model(model_id, auto_restart=auto_restart)
        sys.exit(0 if success else 1)
