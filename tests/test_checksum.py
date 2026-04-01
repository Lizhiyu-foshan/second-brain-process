#!/usr/bin/env python3
"""
索引校验和测试套件
验证 IndexManager 的校验和机制正确工作
"""

import json
import hashlib
import tempfile
from pathlib import Path
from datetime import datetime, timezone
import sys

# 添加 lib 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from message_index import IndexManager


class TestChecksum:
    """校验和测试类"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.temp_dir = None
        self.index_path = None
        
    def setup(self):
        """创建临时目录"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.index_path = self.temp_dir / "test_index.json"
        
    def teardown(self):
        """清理临时目录"""
        if self.temp_dir and self.temp_dir.exists():
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def assert_true(self, condition, message):
        """断言为真"""
        if condition:
            print(f"  ✓ {message}")
            self.passed += 1
        else:
            print(f"  ✗ {message}")
            self.failed += 1
    
    def assert_equal(self, a, b, message):
        """断言相等"""
        if a == b:
            print(f"  ✓ {message}: {a}")
            self.passed += 1
        else:
            print(f"  ✗ {message}: expected {b}, got {a}")
            self.failed += 1
    
    def test_basic_save_and_validate(self):
        """测试1: 基本保存和验证"""
        print("\n[Test 1] 基本保存和验证")
        
        self.setup()
        try:
            # 创建索引管理器
            manager = IndexManager(str(self.index_path))
            
            # 创建一个测试索引
            test_index = {
                "version": "1.0",
                "last_processed": {
                    "timestamp_ms": 1234567890000,
                    "iso_time": "2009-02-13T23:31:30+00:00",
                    "date_str": "2009-02-13"
                },
                "statistics": {
                    "total_messages_processed": 100,
                    "total_files_scanned": 10
                },
                "daily_history": []
            }
            
            # 保存
            result = manager.save(test_index)
            self.assert_true(result, "保存索引成功")
            
            # 重新加载并验证
            loaded = manager.load()
            self.assert_true(loaded is not None, "加载索引成功")
            self.assert_true('checksum' in loaded, "索引包含校验和")
            self.assert_true('_meta' in loaded, "索引包含元数据")
            
            # 验证校验和正确
            is_valid = manager.validate(loaded)
            self.assert_true(is_valid, "索引校验和验证通过")
            
        finally:
            self.teardown()
    
    def test_checksum_consistency(self):
        """测试2: 校验和一致性 - 多次保存结果一致"""
        print("\n[Test 2] 校验和一致性")
        
        self.setup()
        try:
            manager = IndexManager(str(self.index_path))
            
            # 第一次保存
            test_index1 = {
                "version": "1.0",
                "last_processed": {"timestamp_ms": 1000},
                "statistics": {"count": 1},
                "daily_history": []
            }
            manager.save(test_index1.copy())
            
            with open(self.index_path) as f:
                content1 = f.read()
                data1 = json.loads(content1)
            
            checksum1 = data1['checksum']
            
            # 第二次保存相同内容（不同的 Python 字典实例）
            test_index2 = {
                "version": "1.0",
                "last_processed": {"timestamp_ms": 1000},
                "statistics": {"count": 1},
                "daily_history": []
            }
            manager.save(test_index2.copy())
            
            with open(self.index_path) as f:
                content2 = f.read()
                data2 = json.loads(content2)
            
            checksum2 = data2['checksum']
            
            # 校验和应该不同（因为时间戳不同）
            self.assert_true(checksum1 != checksum2, "不同时间保存的校验和不同（预期）")
            
            # 但两个都应该能验证通过
            self.assert_true(manager.validate(data1), "第一次保存的数据验证通过")
            self.assert_true(manager.validate(data2), "第二次保存的数据验证通过")
            
        finally:
            self.teardown()
    
    def test_validate_without_checksum(self):
        """测试3: 验证无校验和的索引"""
        print("\n[Test 3] 无校验和索引验证")
        
        self.setup()
        try:
            manager = IndexManager(str(self.index_path))
            
            # 创建没有校验和的索引（模拟旧版本）
            test_index = {
                "version": "1.0",
                "last_processed": {"timestamp_ms": 1000},
                "statistics": {"count": 1},
                "daily_history": []
            }
            
            # 直接写入文件，不通过 save()
            with open(self.index_path, 'w') as f:
                json.dump(test_index, f)
            
            # 验证应该通过（因为没有校验和，跳过校验）
            loaded = manager.load()
            self.assert_true(loaded is not None, "加载无校验和索引成功")
            
            # 验证会失败，因为缺少必需字段
            # 实际上，我们的 validate 需要 checksum 字段存在才检查
            # 所以这个测试验证的是：没有 checksum 时不会报错
            
        finally:
            self.teardown()
    
    def test_corrupted_checksum(self):
        """测试4: 校验和损坏检测"""
        print("\n[Test 4] 校验和损坏检测")
        
        self.setup()
        try:
            manager = IndexManager(str(self.index_path))
            
            # 先保存一个正确的索引
            test_index = {
                "version": "1.0",
                "last_processed": {"timestamp_ms": 1000},
                "statistics": {"count": 1},
                "daily_history": []
            }
            manager.save(test_index.copy())
            
            # 读取并篡改校验和
            with open(self.index_path) as f:
                data = json.load(f)
            
            original_checksum = data['checksum']
            data['checksum'] = '0000000000000000'  # 错误校验和
            
            with open(self.index_path, 'w') as f:
                json.dump(data, f)
            
            # 加载应该触发重建
            loaded = manager.load()
            self.assert_true(loaded is not None, "损坏的索引被重建")
            
            # 重建后的索引应该包含正确的校验和
            self.assert_true('checksum' in loaded, "重建的索引包含校验和")
            self.assert_true(loaded['checksum'] != '0000000000000000', "重建后的校验和已更新")
            
        finally:
            self.teardown()
    
    def test_json_serialization_format(self):
        """测试5: JSON序列化格式一致性"""
        print("\n[Test 5] JSON序列化格式一致性")
        
        # 测试数据
        data = {
            "version": "1.0",
            "daily_history": [],
            "statistics": {
                "total_messages": 100,
                "rebuilt_at": "2026-01-01T00:00:00+00:00"
            }
        }
        
        # json.dump 和 json.dumps 应该产生相同的格式
        import io
        buffer = io.StringIO()
        json.dump(data, buffer, sort_keys=True, indent=2, ensure_ascii=False)
        dump_result = buffer.getvalue()
        
        dumps_result = json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False)
        
        self.assert_equal(dump_result, dumps_result, "json.dump 和 json.dumps 产生相同格式")
    
    def test_file_content_integrity(self):
        """测试6: 文件内容完整性"""
        print("\n[Test 6] 文件内容完整性")
        
        self.setup()
        try:
            manager = IndexManager(str(self.index_path))
            
            # 保存索引
            test_index = {
                "version": "1.0",
                "last_processed": {"timestamp_ms": 9999999999999},
                "statistics": {"count": 999},
                "daily_history": []
            }
            manager.save(test_index.copy())
            
            # 读取文件内容
            with open(self.index_path) as f:
                file_content = f.read()
            
            # 解析并重新序列化（验证一致性）
            data = json.loads(file_content)
            data_copy = {k: v for k, v in data.items() if k != 'checksum'}
            reserialized = json.dumps(data_copy, sort_keys=True, indent=2, ensure_ascii=False)
            
            # 从文件内容中移除 checksum 字段
            import re
            file_no_checksum = re.sub(r'"checksum":\s*"[^"]+",\n\s*', '', file_content)
            
            self.assert_equal(file_no_checksum.strip(), reserialized.strip(), 
                            "文件内容与重新序列化结果一致")
            
        finally:
            self.teardown()
    
    def run_all(self):
        """运行所有测试"""
        print("=" * 60)
        print("IndexManager 校验和测试套件")
        print("=" * 60)
        
        tests = [
            self.test_basic_save_and_validate,
            self.test_checksum_consistency,
            self.test_validate_without_checksum,
            self.test_corrupted_checksum,
            self.test_json_serialization_format,
            self.test_file_content_integrity,
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                print(f"  ✗ 测试异常: {e}")
                import traceback
                traceback.print_exc()
                self.failed += 1
        
        print("\n" + "=" * 60)
        print(f"测试结果: {self.passed} 通过, {self.failed} 失败")
        print("=" * 60)
        
        return self.failed == 0


if __name__ == "__main__":
    test = TestChecksum()
    success = test.run_all()
    sys.exit(0 if success else 1)
