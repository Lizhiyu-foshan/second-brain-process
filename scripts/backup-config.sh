#!/bin/bash
# 备份关键配置文件
BACKUP_DIR="/root/.openclaw/config-backups"
TIMESTAMP=$(date '+%Y%m%d-%H%M%S')

mkdir -p "$BACKUP_DIR"

# 备份 openclaw.json
cp /root/.openclaw/openclaw.json "$BACKUP_DIR/openclaw.json.$TIMESTAMP"

# 保留最近30个备份
ls -t "$BACKUP_DIR"/openclaw.json.* 2>/dev/null | tail -n +31 | xargs rm -f 2>/dev/null

echo "Config backed up to $BACKUP_DIR/openclaw.json.$TIMESTAMP"
