#!/bin/bash
#
# 代码部署前检查脚本
# 确保代码质量后再上线
#

set -e

SCRIPT_DIR="/root/.openclaw/workspace/second-brain-processor"
LEARNINGS_DIR="/root/.openclaw/workspace/.learnings"
LOG_FILE="/tmp/deploy_check_$(date +%Y%m%d_%H%M%S).log"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[✓]${NC} $1" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[!]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[✗]${NC} $1" | tee -a "$LOG_FILE"
}

# 记录失败到学习日志
record_failure() {
    local component="$1"
    local error_msg="$2"
    local timestamp=$(date -Iseconds)
    
    mkdir -p "$LEARNINGS_DIR"
    
    cat >> "$LEARNINGS_DIR/DEPLOY_FAILURES.md" << EOF
## [$timestamp] $component

**错误**: $error_msg

**代码**: \`$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')\`

**改进建议**:
- [ ] 修复问题
- [ ] 添加测试用例
- [ ] 更新文档

---
EOF
    
    log "失败已记录到 DEPLOY_FAILURES.md"
}

echo "========================================"
echo "代码部署前检查"
echo "时间: $(date)"
echo "========================================"
echo ""

FAILED=0

# 1. Python 语法检查
echo "【1/6】Python 语法检查..."
for pyfile in "$SCRIPT_DIR"/*.py; do
    if [ -f "$pyfile" ]; then
        if python3 -m py_compile "$pyfile" 2>/dev/null; then
            log "  $(basename $pyfile) - 语法正确"
        else
            error "  $(basename $pyfile) - 语法错误"
            record_failure "Syntax Check" "$(basename $pyfile) 语法错误"
            FAILED=1
        fi
    fi
done
echo ""

# 2. 导入检查
echo "【2/6】模块导入检查..."
for pyfile in "$SCRIPT_DIR"/*.py; do
    if [ -f "$pyfile" ]; then
        # 尝试导入模块
        if python3 -c "import sys; sys.path.insert(0, '$SCRIPT_DIR'); exec(open('$pyfile').read().split('if __name__')[0])" 2>/dev/null; then
            log "  $(basename $pyfile) - 导入成功"
        else
            warn "  $(basename $pyfile) - 导入可能有依赖问题（运行时检查）"
        fi
    fi
done
echo ""

# 3. 关键函数存在性检查
echo "【3/6】关键函数检查..."
KEY_FUNCTIONS=(
    "wechat_fetcher.py:WeChatArticleFetcher"
    "wechat_fetcher.py:fetch"
    "processor.py:process_link"
)

for item in "${KEY_FUNCTIONS[@]}"; do
    file="${item%%:*}"
    func="${item##*:}"
    
    if grep -q "def $func\|class $func" "$SCRIPT_DIR/$file" 2>/dev/null; then
        log "  $file::$func - 存在"
    else
        error "  $file::$func - 缺失"
        record_failure "Function Check" "$file::$func 缺失"
        FAILED=1
    fi
done
echo ""

# 4. 配置文件检查
echo "【4/6】配置文件检查..."
if [ -f "$SCRIPT_DIR/../museum-collector/trigger_museum_push.sh" ]; then
    log "  trigger_museum_push.sh - 存在"
else
    warn "  trigger_museum_push.sh - 不存在（可选）"
fi
echo ""

# 5. 测试运行（小样例）
echo "【5/6】快速功能测试..."

# 测试缓存目录可写
if mkdir -p /tmp/wechat_fetch_cache 2>/dev/null; then
    log "  缓存目录 - 可写"
else
    error "  缓存目录 - 不可写"
    record_failure "Directory Check" "缓存目录不可写"
    FAILED=1
fi

# 测试 Playwright 可用
if python3 -c "from playwright.sync_api import sync_playwright; print('OK')" 2>/dev/null; then
    log "  Playwright - 可用"
else
    error "  Playwright - 不可用"
    record_failure "Dependency Check" "Playwright 不可用"
    FAILED=1
fi
echo ""

# 6. 代码规范检查
echo "【6/6】代码规范检查..."

# 检查是否有硬编码的敏感信息
if grep -r "sk-[a-zA-Z0-9]\{20,\}" "$SCRIPT_DIR"/*.py 2>/dev/null | grep -v "DASHSCOPE_API_KEY"; then
    warn "  发现可能的硬编码 API Key"
else
    log "  无硬编码敏感信息"
fi

# 检查文件大小（防止超大文件）
for pyfile in "$SCRIPT_DIR"/*.py; do
    if [ -f "$pyfile" ]; then
        size=$(stat -f%z "$pyfile" 2>/dev/null || stat -c%s "$pyfile" 2>/dev/null)
        if [ "$size" -gt 102400 ]; then  # 100KB
            warn "  $(basename $pyfile) - 文件较大(${size}字节)，建议拆分"
        fi
    fi
done
echo ""

# 总结
echo "========================================"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ 所有检查通过，可以部署${NC}"
    echo "日志: $LOG_FILE"
    exit 0
else
    echo -e "${RED}✗ 检查失败，请修复后再部署${NC}"
    echo "日志: $LOG_FILE"
    echo "失败记录: $LEARNINGS_DIR/DEPLOY_FAILURES.md"
    exit 1
fi
