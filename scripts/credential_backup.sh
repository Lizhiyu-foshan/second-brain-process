#!/bin/bash
# credential_backup.sh - 凭据自动备份脚本
# 位置: /root/.openclaw/workspace/scripts/credential_backup.sh
# 用途: 在任何凭据修改前自动创建备份

set -euo pipefail

BACKUP_DIR="/root/.openclaw/backups/credentials"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="backup_${TIMESTAMP}"

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 备份环境变量中的凭据
echo "=== 环境变量凭据备份 ($TIMESTAMP) ===" > "$BACKUP_DIR/env_${BACKUP_NAME}.txt"
env | grep -E "(TOKEN|KEY|SECRET|PASSWORD|GITHUB|GIT)" >> "$BACKUP_DIR/env_${BACKUP_NAME}.txt" 2>/dev/null || true

# 备份 git 凭据
if [ -f ~/.git-credentials ]; then
    cp ~/.git-credentials "$BACKUP_DIR/git_credentials_${BACKUP_NAME}" 2>/dev/null || true
fi

# 备份 .netrc
if [ -f ~/.netrc ]; then
    cp ~/.netrc "$BACKUP_DIR/netrc_${BACKUP_NAME}" 2>/dev/null || true
fi

# 备份 SSH 密钥（元数据，不含私钥内容）
if [ -d ~/.ssh ]; then
    ls -la ~/.ssh/ > "$BACKUP_DIR/ssh_keys_${BACKUP_NAME}.txt" 2>/dev/null || true
fi

# 创建恢复脚本
cat > "$BACKUP_DIR/restore_${BACKUP_NAME}.sh" << 'EOF'
#!/bin/bash
# 恢复凭据脚本 - 由 credential_backup.sh 自动生成
# 使用方法: ./restore_YYYYMMDD_HHMMSS.sh

echo "恢复凭据..."
echo "注意: 请确认您要恢复到这个时间点的凭据状态"
read -p "确认恢复? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "已取消"
    exit 1
fi

# 恢复逻辑根据实际备份文件调整
echo "请手动恢复以下文件:"
ls -la "$BACKUP_DIR/" | grep "${BACKUP_NAME}"
EOF
chmod +x "$BACKUP_DIR/restore_${BACKUP_NAME}.sh"

# 清理旧备份（保留最近30个）
cd "$BACKUP_DIR"
ls -t | grep "^backup_" | tail -n +31 | xargs -r rm -f 2>/dev/null || true

echo "✅ 凭据备份完成: $BACKUP_NAME"
echo "📁 备份位置: $BACKUP_DIR"
