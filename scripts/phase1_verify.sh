#!/bin/bash
# 阶段 1 准备验证脚本

echo "=== Feishu 混合去重模式 - 阶段 1 准备验证 ==="
echo ""

# 1. 检查备份文件
echo "1. 检查备份文件..."
DEDUP_BACKUP=$(ls -t /root/.openclaw/extensions/feishu/src/dedup.ts.backup.* 2>/dev/null | head -1)
BOT_BACKUP=$(ls -t /root/.openclaw/extensions/feishu/src/bot.ts.backup.* 2>/dev/null | head -1)

if [ -n "$DEDUP_BACKUP" ] && [ -n "$BOT_BACKUP" ]; then
    echo "   ✓ 备份文件存在"
    echo "     - dedup.ts: $(basename $DEDUP_BACKUP)"
    echo "     - bot.ts: $(basename $BOT_BACKUP)"
else
    echo "   ✗ 备份文件缺失"
    exit 1
fi
echo ""

# 2. 测试 Python 脚本命令行接口
echo "2. 测试 Python 脚本命令行接口..."
TEST_MSG="测试消息_$(date +%s)"
TEST_SENDER="test_user"

CLI_SCRIPT="/root/.openclaw/workspace/second-brain-processor/feishu_receive_dedup_cli.py"

if [ ! -f "$CLI_SCRIPT" ]; then
    echo "   ✗ 脚本文件不存在：$CLI_SCRIPT"
    exit 1
fi

# 测试 --check（新消息）
RESULT1=$(python3 "$CLI_SCRIPT" --check "$TEST_MSG" "$TEST_SENDER" 2>/dev/null)
if [ "$RESULT1" = "NEW" ]; then
    echo "   ✓ --check 新消息测试通过"
else
    echo "   ✗ --check 新消息测试失败：$RESULT1"
    exit 1
fi

# 测试 --record
RESULT2=$(python3 "$CLI_SCRIPT" --record "$TEST_MSG" "$TEST_SENDER" 2>/dev/null)
if echo "$RESULT2" | grep -q "已记录"; then
    echo "   ✓ --record 记录测试通过"
else
    echo "   ✗ --record 记录测试失败：$RESULT2"
    exit 1
fi

# 测试 --check（重复消息）
RESULT3=$(python3 "$CLI_SCRIPT" --check "$TEST_MSG" "$TEST_SENDER" 2>&1 | grep -E "^(DUPLICATE|NEW)$")
if [ "$RESULT3" = "DUPLICATE" ]; then
    echo "   ✓ --check 重复消息测试通过"
else
    echo "   ✗ --check 重复消息测试失败：$RESULT3"
    exit 1
fi
echo ""

# 3. 检查文件权限
echo "3. 检查文件权限..."
RECORDS_FILE="/root/.openclaw/workspace/.learnings/received_messages.json"
if [ -w "$RECORDS_FILE" ] || [ -w "$(dirname "$RECORDS_FILE")" ]; then
    echo "   ✓ 去重记录文件可写"
else
    echo "   ✗ 去重记录文件不可写"
    exit 1
fi
echo ""

# 4. 检查功能开关配置
echo "4. 检查功能开关配置..."
CONFIG_FILE="/root/.openclaw/workspace/.learnings/feishu_hybrid_dedup_config.md"
if [ -f "$CONFIG_FILE" ]; then
    echo "   ✓ 配置文件存在"
else
    echo "   ✗ 配置文件缺失"
    exit 1
fi
echo ""

# 5. 检查 TypeScript 文件是否存在
echo "5. 检查 TypeScript 源文件..."
if [ -f "/root/.openclaw/extensions/feishu/src/dedup.ts" ] && [ -f "/root/.openclaw/extensions/feishu/src/bot.ts" ]; then
    echo "   ✓ TypeScript 源文件存在"
else
    echo "   ✗ TypeScript 源文件缺失"
    exit 1
fi
echo ""

echo "=== 阶段 1 准备验证完成 - 所有检查通过 ✓ ==="
echo ""
echo "下一步：执行阶段 2 - 开发（修改 dedup.ts 和 bot.ts）"
echo ""
