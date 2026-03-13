#!/usr/bin/env python3
"""
模型切换自动测试脚本
模拟每个模型切换，自动调整配置并验证压缩机制
"""
import json
import subprocess
from pathlib import Path
from datetime import datetime

# 模型配置数据库
MODEL_CONFIGS = {
    'k2p5': {
        'provider': 'kimi-coding',
        'context_window': 262144,
        'name': 'k2p5',
        'description': 'Kimi K2.5 (深度思考)'
    },
    'glm-5': {
        'provider': 'alicloud',
        'context_window': 128000,
        'name': 'GLM-5',
        'description': 'GLM-5 (复杂编码/架构)'
    },
    'qwen3.5-plus': {
        'provider': 'alicloud',
        'context_window': 128000,
        'name': 'qwen3.5-plus',
        'description': 'Qwen 3.5 Plus (快速对话)'
    },
    'MiniMax-M2.5': {
        'provider': 'alicloud',
        'context_window': 204800,
        'name': 'MiniMax-M2.5',
        'description': 'MiniMax M2.5 (快速编码)'
    }
}

def get_current_config():
    """获取当前配置"""
    config_file = Path('/root/.openclaw/openclaw.json')
    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def calculate_safe_config(context_window):
    """计算安全的压缩配置"""
    return {
        'mode': 'default',
        'reserveTokensFloor': min(50000, int(context_window * 0.2)),
        'maxHistoryShare': 0.5,
        'memoryFlush': {
            'enabled': True,
            'softThresholdTokens': int(context_window * 0.75)  # 75% 时触发压缩
        }
    }

def validate_config(compaction, context_window):
    """验证配置是否兼容"""
    issues = []
    warnings = []
    
    soft_threshold = compaction.get('memoryFlush', {}).get('softThresholdTokens', 0)
    reserve_floor = compaction.get('reserveTokensFloor', 0)
    
    soft_ratio = soft_threshold / context_window * 100 if context_window > 0 else 0
    reserve_ratio = reserve_floor / context_window * 100 if context_window > 0 else 0
    
    if soft_threshold >= context_window:
        issues.append(f"softThresholdTokens ({soft_threshold:,}) >= 上下文窗口 ({context_window:,})")
    elif soft_ratio > 80:
        warnings.append(f"softThresholdTokens 比例过高 ({soft_ratio:.1f}% > 80%)")
    
    if reserve_floor >= context_window * 0.5:
        issues.append(f"reserveTokensFloor ({reserve_floor:,}) >= 50% 上下文")
    elif reserve_ratio > 30:
        warnings.append(f"reserveTokensFloor 比例过高 ({reserve_ratio:.1f}% > 30%)")
    
    return issues, warnings, soft_ratio, reserve_ratio

def simulate_model_switch(model_id, config):
    """模拟模型切换并测试配置"""
    print(f"\n{'='*60}")
    print(f"🧪 模拟切换模型: {model_id}")
    print(f"{'='*60}")
    
    if model_id not in MODEL_CONFIGS:
        print(f"❌ 未知模型: {model_id}")
        return False
    
    model_info = MODEL_CONFIGS[model_id]
    context_window = model_info['context_window']
    
    print(f"模型: {model_info['description']}")
    print(f"上下文窗口: {context_window:,} tokens")
    print()
    
    # 获取当前压缩配置
    compaction = config.get('agents', {}).get('defaults', {}).get('compaction', {})
    
    print("📊 当前配置检查:")
    current_soft = compaction.get('memoryFlush', {}).get('softThresholdTokens', 0)
    current_reserve = compaction.get('reserveTokensFloor', 0)
    print(f"  softThresholdTokens: {current_soft:,}")
    print(f"  reserveTokensFloor: {current_reserve:,}")
    print()
    
    # 验证配置兼容性
    issues, warnings, soft_ratio, reserve_ratio = validate_config(compaction, context_window)
    
    if issues:
        print("❌ 配置不兼容:")
        for issue in issues:
            print(f"  - {issue}")
        print()
        
        # 计算建议配置
        safe_config = calculate_safe_config(context_window)
        print("📋 建议调整为:")
        print(f"  reserveTokensFloor: {safe_config['reserveTokensFloor']:,} ({safe_config['reserveTokensFloor']/context_window*100:.1f}%)")
        print(f"  maxHistoryShare: {safe_config['maxHistoryShare']}")
        print(f"  softThresholdTokens: {safe_config['memoryFlush']['softThresholdTokens']:,} ({safe_config['memoryFlush']['softThresholdTokens']/context_window*100:.1f}%)")
        print()
        
        return safe_config
    
    if warnings:
        print("⚠️ 警告:")
        for warning in warnings:
            print(f"  - {warning}")
        print()
    
    print(f"✅ 配置兼容")
    print(f"  softThresholdTokens: {current_soft:,} / {context_window:,} = {soft_ratio:.1f}%")
    print(f"  reserveTokensFloor: {current_reserve:,} / {context_window:,} = {reserve_ratio:.1f}%")
    print()
    
    return True

def test_compression_mechanism():
    """测试压缩机制是否正常工作"""
    print(f"\n{'='*60}")
    print("🗜️  测试压缩机制")
    print(f"{'='*60}")
    
    session_file = Path('/root/.openclaw/agents/main/sessions/25bf8b77-2428-4984-9efa-0b108cfdecab.jsonl')
    
    # 检查会话文件
    if session_file.exists():
        size_mb = session_file.stat().st_size / 1024 / 1024
        print(f"会话文件大小: {size_mb:.2f} MB")
        
        # 统计消息数
        msg_count = 0
        compaction_count = 0
        with open(session_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get('type') == 'message':
                        msg_count += 1
                    elif data.get('type') == 'compaction':
                        compaction_count += 1
                except:
                    continue
        
        print(f"消息数量: {msg_count}")
        print(f"历史压缩次数: {compaction_count}")
        
        if compaction_count > 0:
            print("✅ 压缩机制正常工作")
        else:
            print("ℹ️  尚未触发压缩（可能需要更多消息积累）")
    else:
        print("❌ 会话文件不存在")

def generate_report(results):
    """生成测试报告"""
    print(f"\n{'='*60}")
    print("📊 模型切换测试报告")
    print(f"{'='*60}")
    print()
    
    print("| 模型 | 上下文窗口 | 当前配置 | 建议操作 |")
    print("|------|-----------|---------|---------|")
    
    for model_id, result in results.items():
        model_info = MODEL_CONFIGS[model_id]
        context = model_info['context_window']
        
        if result is True:
            status = "✅ 兼容"
            action = "无需调整"
        elif result is False:
            status = "❌ 未知"
            action = "检查配置"
        else:
            status = "⚠️ 需调整"
            action = "更新配置"
        
        print(f"| {model_id} | {context:,} | {status} | {action} |")
    
    print()
    print("💡 使用建议:")
    print("1. 切换模型前运行此检查")
    print("2. 根据建议自动调整配置")
    print("3. 重启 OpenClaw 使配置生效")
    print("4. 监控压缩机制是否正常工作")

if __name__ == '__main__':
    print("🚀 OpenClaw 模型切换自动测试")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 获取当前配置
    config = get_current_config()
    
    # 测试每个模型
    results = {}
    for model_id in MODEL_CONFIGS.keys():
        result = simulate_model_switch(model_id, config)
        results[model_id] = result
    
    # 测试压缩机制
    test_compression_mechanism()
    
    # 生成报告
    generate_report(results)
    
    print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
