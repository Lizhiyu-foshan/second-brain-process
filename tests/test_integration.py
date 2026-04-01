#!/usr/bin/env python3
"""
增量处理集成测试
验证整个增量处理流程，包括索引校验和机制
"""

import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone
import sys
import os

# 创建临时工作目录进行测试
TEST_DIR = Path(tempfile.mkdtemp(prefix="second_brain_test_"))
DATA_DIR = TEST_DIR / ".data"
OBSIDIAN_DIR = TEST_DIR / "obsidian-vault" / "02-Conversations"
SESSIONS_DIR = TEST_DIR / "sessions"

# 设置环境变量
os.environ["SECOND_BRAIN_DATA_DIR"] = str(DATA_DIR)
os.environ["SECOND_BRAIN_OBSIDIAN_DIR"] = str(OBSIDIAN_DIR)

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from message_index import IndexManager


def create_mock_session(session_id: str, messages: list):
    """创建模拟会话文件"""
    session_file = SESSIONS_DIR / f"{session_id}.jsonl"
    session_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(session_file, 'w') as f:
        for msg in messages:
            f.write(json.dumps(msg) + '\n')
    
    return session_file


def test_incremental_processing():
    """测试增量处理流程"""
    print("\n[集成测试] 增量处理流程")
    print("-" * 50)
    
    # 创建必要的目录
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OBSIDIAN_DIR.mkdir(parents=True, exist_ok=True)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 创建索引管理器
    index_path = DATA_DIR / "message_index.json"
    manager = IndexManager(str(index_path))
    
    # 测试1: 首次运行（无索引）
    print("\n1. 首次运行（无索引文件）...")
    
    # 创建一些模拟消息
    base_time = int(datetime(2026, 4, 1, 10, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
    
    messages_batch1 = [
        {"type": "message", "timestamp": datetime.fromtimestamp(base_time / 1000, tz=timezone.utc).isoformat(), "content": "Message 1"},
        {"type": "message", "timestamp": datetime.fromtimestamp((base_time + 1000) / 1000, tz=timezone.utc).isoformat(), "content": "Message 2"},
    ]
    
    create_mock_session("session_001", messages_batch1)
    
    # 保存初始索引
    initial_index = {
        "version": "1.0",
        "last_processed": {
            "timestamp_ms": 0,
            "iso_time": "1970-01-01T00:00:00+00:00",
            "date_str": "1970-01-01"
        },
        "statistics": {
            "total_messages_processed": 0,
            "total_files_scanned": 0
        },
        "daily_history": []
    }
    manager.save(initial_index)
    
    # 加载索引（应该成功）
    loaded = manager.load()
    assert loaded is not None, "首次运行应成功创建索引"
    assert 'checksum' in loaded, "索引应包含校验和"
    print("  ✓ 首次运行成功，索引已创建并验证")
    
    # 测试2: 正常增量运行
    print("\n2. 正常增量运行...")
    
    # 添加更多消息
    messages_batch2 = [
        {"type": "message", "timestamp": datetime.fromtimestamp((base_time + 2000) / 1000, tz=timezone.utc).isoformat(), "content": "Message 3"},
    ]
    create_mock_session("session_002", messages_batch2)
    
    # 更新索引时间戳
    loaded['last_processed']['timestamp_ms'] = base_time + 2000
    manager.save(loaded)
    
    # 重新加载验证
    reloaded = manager.load()
    assert reloaded is not None, "增量运行应成功"
    assert reloaded['last_processed']['timestamp_ms'] == base_time + 2000, "时间戳应已更新"
    print("  ✓ 增量运行成功，索引已更新")
    
    # 测试3: 校验和损坏后自动重建
    print("\n3. 校验和损坏后自动重建...")
    
    # 篡改校验和
    with open(index_path) as f:
        data = json.load(f)
    
    original_checksum = data['checksum']
    data['checksum'] = 'invalid_checksum_12345'
    
    with open(index_path, 'w') as f:
        json.dump(data, f)
    
    # 重新加载（应该触发重建）
    reloaded = manager.load()
    assert reloaded is not None, "损坏的索引应被重建"
    assert reloaded['checksum'] != 'invalid_checksum_12345', "重建后校验和应已更新"
    assert reloaded['checksum'] != original_checksum, "重建后校验和应与原校验和不同"
    print("  ✓ 损坏的索引已自动重建")
    
    # 测试4: 验证重建后的索引可正常加载
    print("\n4. 验证重建后的索引可正常加载...")
    
    final_load = manager.load()
    assert final_load is not None, "重建后的索引应能正常加载"
    # 使用内部方法验证校验和
    is_valid = manager.validate(final_load)
    assert is_valid, "重建后的索引应通过验证"
    print("  ✓ 重建后的索引验证通过")
    
    # 测试5: 多次保存验证一致性
    print("\n5. 多次保存验证一致性...")
    
    for i in range(3):
        loaded = manager.load()
        loaded['statistics']['test_counter'] = i
        manager.save(loaded)
        
        # 立即验证
        reloaded = manager.load()
        is_valid = manager.validate(reloaded)
        assert is_valid, f"第 {i+1} 次保存后应通过验证"
    
    print("  ✓ 多次保存验证通过")
    
    # 清理
    shutil.rmtree(TEST_DIR)
    print("\n" + "=" * 50)
    print("集成测试全部通过！")
    print("=" * 50)
    
    return True


if __name__ == "__main__":
    try:
        success = test_incremental_processing()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        # 清理
        if TEST_DIR.exists():
            shutil.rmtree(TEST_DIR)
        sys.exit(1)
