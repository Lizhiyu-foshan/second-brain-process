# 清理脚本

# 清理 Python 缓存文件
cd /root/.openclaw/workspace/projects/ecommerce-mvp

# 删除 __pycache__ 目录
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# 删除 .pyc 文件
find . -type f -name "*.pyc" -delete 2>/dev/null

# 删除 .pytest_cache
rm -rf .pytest_cache 2>/dev/null

# 删除测试数据库
cd /root/.openclaw/workspace/projects/ecommerce-mvp/tests
find . -name "*.db" -delete 2>/dev/null

echo "清理完成"
