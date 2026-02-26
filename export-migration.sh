#!/bin/bash
#
# Kimi Claw 迁移脚本
# 将当前Kimi Claw配置迁移到新的OpenClaw本地部署
#

set -e

MIGRATION_DIR="${1:-./kimi-claw-migration-$(date +%Y%m%d)}"

echo "🚀 Kimi Claw 迁移工具"
echo "====================="
echo ""
echo "目标目录: $MIGRATION_DIR"
echo ""

# 创建迁移目录
mkdir -p "$MIGRATION_DIR"

echo "📦 正在收集配置..."

# 1. 核心配置
echo "  ✓ 复制 openclaw.json (主配置)"
cp /root/.openclaw/openclaw.json "$MIGRATION_DIR/" 2>/dev/null || echo "  ⚠️  openclaw.json 不存在"

# 2. Skills
echo "  ✓ 复制自定义 Skills"
mkdir -p "$MIGRATION_DIR/skills"
cp -r /root/.openclaw/skills/* "$MIGRATION_DIR/skills/" 2>/dev/null || echo "  ⚠️  无自定义skills"

# 3. Workspace (项目文件)
echo "  ✓ 复制 Workspace"
mkdir -p "$MIGRATION_DIR/workspace"
cp -r /root/.openclaw/workspace/* "$MIGRATION_DIR/workspace/" 2>/dev/null || echo "  ⚠️  workspace为空"

# 4. Session 历史
echo "  ✓ 复制 Session 历史"
mkdir -p "$MIGRATION_DIR/sessions"
cp /root/.openclaw/agents/main/sessions/*.jsonl "$MIGRATION_DIR/sessions/" 2>/dev/null || echo "  ⚠️  无session文件"

# 5. Cron 任务
echo "  ✓ 复制 Cron 配置"
mkdir -p "$MIGRATION_DIR/cron"
cp -r /root/.openclaw/cron/* "$MIGRATION_DIR/cron/" 2>/dev/null || echo "  ⚠️  无cron配置"

# 6. 生成迁移说明
echo "  ✓ 生成迁移说明"
cat > "$MIGRATION_DIR/MIGRATION_GUIDE.md" << EOF
# Kimi Claw 迁移指南

## 迁移包内容

此包包含从 Kimi Claw 导出的所有配置和数据。

### 文件结构

```
$MIGRATION_DIR/
├── openclaw.json          # 主配置文件 (包含API密钥、模型配置)
├── skills/                # 自定义 Skills
│   ├── bmad-method/
│   └── channels-setup/
├── workspace/             # 工作区文件
│   ├── AGENTS.md          # 代理配置
│   ├── SOUL.md            # 人格设定
│   ├── MEMORY.md          # 长期记忆
│   ├── IDENTITY.md        # 身份配置
│   ├── USER.md            # 用户信息
│   ├── projects/          # 项目文件
│   └── ...
├── sessions/              # 对话历史
├── cron/                  # 定时任务
└── MIGRATION_GUIDE.md     # 本文件
```

## 迁移步骤

### 1. 在新机器上安装 OpenClaw

```bash
# 安装 OpenClaw
npm install -g openclaw

# 或使用 pnpm
pnpm add -g openclaw
```

### 2. 恢复配置

```bash
# 复制配置文件
cp openclaw.json ~/.openclaw/

# 复制 skills
cp -r skills/* ~/.openclaw/skills/

# 复制 workspace
cp -r workspace/* ~/.openclaw/workspace/

# 复制 sessions (可选)
cp -r sessions/* ~/.openclaw/agents/main/sessions/

# 复制 cron (可选)
cp -r cron/* ~/.openclaw/cron/
```

### 3. 安装依赖

```bash
# 安装系统 skills
openclaw skill install github
openclaw skill install weather
# ... 其他需要的 skills

# 安装插件
openclaw plugins install @m1heng-clawd/feishu
```

### 4. 验证

```bash
openclaw status
openclaw skills list
```

## 注意事项

1. **API密钥**: openclaw.json 中包含你的 Kimi API 密钥，请确保安全传输
2. **绝对路径**: 配置中的路径是绝对路径，可能需要手动调整为新环境
3. **插件**: 部分插件可能需要重新安装
4. **浏览器**: 浏览器配置可能需要重新设置

## 需要手动迁移的内容

以下配置可能需要手动调整：

- 浏览器路径 (如果不同系统)
- 文件系统绝对路径
- 环境变量
- 系统特定的配置

## 验证清单

- [ ] OpenClaw 正常运行
- [ ] Skills 加载正确
- [ ] 模型配置正确
- [ ] API密钥有效
- [ ] Workspace 文件完整
- [ ] 历史对话可访问

---

迁移时间: $(date)
源环境: Kimi Claw
EOF

echo ""
echo "✅ 迁移包创建完成!"
echo ""
echo "位置: $MIGRATION_DIR"
echo ""
echo "内容摘要:"
echo "  - openclaw.json (主配置)"
echo "  - skills/ ($(ls -1 $MIGRATION_DIR/skills 2>/dev/null | wc -l) 个skill)"
echo "  - workspace/ (项目文件和记忆)"
echo "  - sessions/ ($(ls -1 $MIGRATION_DIR/sessions 2>/dev/null | wc -l) 个session)"
echo "  - cron/ (定时任务)"
echo ""
echo "下一步:"
echo "  1. 将 $MIGRATION_DIR 复制到目标机器"
echo "  2. 按照 MIGRATION_GUIDE.md 进行恢复"
echo ""
echo "打包命令:"
echo "  tar -czvf kimi-claw-migration.tar.gz $MIGRATION_DIR"
