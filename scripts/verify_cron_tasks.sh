#!/bin/bash
# verify_cron_tasks.sh - 定时任务部署前验证脚本
# 用法: ./verify_cron_tasks.sh

set -e

echo "=== 定时任务部署前验证 ==="
echo "时间: $(date)"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0

# 1. 检查定时任务引用的文件是否存在
echo "[1/4] 检查定时任务文件引用..."
python3 << 'EOF'
import json
import subprocess
from pathlib import Path

# 获取定时任务列表
result = subprocess.run(
    ["openclaw", "cron", "list", "--json"],
    capture_output=True,
    text=True
)

if result.returncode != 0:
    print("❌ 无法获取定时任务列表")
    exit(1)

tasks = json.loads(result.stdout)
errors = []

for task in tasks:
    if not task.get("enabled"):
        continue
    
    payload = task.get("payload", {})
    if payload.get("kind") != "systemEvent":
        continue
    
    text = payload.get("text", "")
    
    # 提取 python3 命令中的文件路径
    import re
    matches = re.findall(r'python3\s+(\S+\.py)', text)
    
    for filepath in matches:
        path = Path(filepath)
        if not path.exists():
            errors.append(f"  ❌ 任务 '{task.get('name')}' 引用的文件不存在: {filepath}")
        else:
            print(f"  ✅ {filepath}")

if errors:
    print("\n".join(errors))
    exit(1)
else:
    print("  所有文件引用正常")
EOF

if [ $? -ne 0 ]; then
    ERRORS=$((ERRORS + 1))
fi

echo ""

# 2. 语法检查 Python 文件
echo "[2/4] 语法检查 Python 文件..."
for file in /root/.openclaw/workspace/second-brain-processor/*.py; do
    if python3 -m py_compile "$file" 2>/dev/null; then
        echo "  ✅ $(basename $file)"
    else
        echo "  ❌ $(basename $file) 语法错误"
        ERRORS=$((ERRORS + 1))
    fi
done

echo ""

# 3. 检查关键函数存在性
echo "[3/4] 检查关键函数存在性..."
python3 << 'EOF'
import ast
from pathlib import Path

key_files = [
    ("daily_complete_report.py", ["main", "generate_report", "verify_and_send"]),
    ("verify_send_link.py", ["verify_send_link"]),
]

errors = []

for filename, required_funcs in key_files:
    filepath = Path(f"/root/.openclaw/workspace/second-brain-processor/{filename}")
    if not filepath.exists():
        errors.append(f"  ❌ {filename} 不存在")
        continue
    
    content = filepath.read_text(encoding='utf-8')
    try:
        tree = ast.parse(content)
        found_funcs = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                found_funcs.append(node.name)
        
        missing = [f for f in required_funcs if f not in found_funcs]
        if missing:
            errors.append(f"  ❌ {filename} 缺少函数: {', '.join(missing)}")
        else:
            print(f"  ✅ {filename} 函数完整")
    except SyntaxError as e:
        errors.append(f"  ❌ {filename} 语法错误: {e}")

if errors:
    print("\n".join(errors))
    exit(1)
EOF

if [ $? -ne 0 ]; then
    ERRORS=$((ERRORS + 1))
fi

echo ""

# 4. Dry-run 测试关键任务
echo "[4/4] Dry-run 测试关键任务..."
if python3 /root/.openclaw/workspace/second-brain-processor/daily_complete_report.py --dry-run >/dev/null 2>&1; then
    echo "  ✅ daily_complete_report.py --dry-run 通过"
else
    echo "  ❌ daily_complete_report.py --dry-run 失败"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# 总结
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ 所有检查通过，可以部署${NC}"
    exit 0
else
    echo -e "${RED}❌ 发现 $ERRORS 个问题，请修复后再部署${NC}"
    exit 1
fi
