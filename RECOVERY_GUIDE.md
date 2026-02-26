# Kimi Claw 会话恢复指南

## 如果你发现对话记录丢失

### 方式 1：直接访问代码（推荐）
告诉 Kimi Claw：
```
请读取 /root/.openclaw/workspace/projects/ecommerce-mvp/PROJECT_LOG.md
然后继续开发这个项目
```

### 方式 2：重新加载上下文
```
我正在开发一个电商系统 MVP，项目位置在
/root/.openclaw/workspace/projects/ecommerce-mvp/

请帮我：
1. 读取 PROJECT_LOG.md 了解项目历史
2. 检查当前代码结构
3. 继续优化功能
```

### 方式 3：完整恢复
```
请执行以下操作：
1. 查看 /root/.openclaw/workspace/projects/ 目录
2. 读取 ecommerce-mvp/PROJECT_LOG.md
3. 加载项目并继续开发
```

## 重要文件位置

| 文件 | 位置 | 用途 |
|------|------|------|
| 项目代码 | `/root/.openclaw/workspace/projects/ecommerce-mvp/` | 主项目目录 |
| 项目日志 | `PROJECT_LOG.md` | 开发历史和上下文 |
| 数据库 | `ecommerce.db` | SQLite 数据文件 |
| 原始模块 | `/tmp/module-*` | 多 Agent 开发原始输出 |

## 避免数据丢失的建议

1. **定期提交到 Git**
   ```bash
   cd /root/.openclaw/workspace/projects/ecommerce-mvp
   git init
   git add .
   git commit -m "里程碑: 多 Agent 开发完成"
   ```

2. **推送到远程仓库**
   - GitHub / GitLab / Gitee
   - 即使 Kimi Claw 重置，代码也不会丢失

3. **本地备份**
   - 下载项目压缩包
   - 保存到本地电脑

4. **文档化关键决策**
   - 在 PROJECT_LOG.md 中记录
   - 下次会话可快速恢复上下文

## 如果 Kimi Claw 完全重置

1. 重新安装 OpenCode: `curl -fsSL https://opencode.ai/install | bash`
2. 恢复项目: `git clone your-repo-url`
3. 恢复依赖: `pip install -r requirements.txt`
4. 继续开发

## 联系支持

如果遇到问题，可以：
- 查看 OpenClaw 文档: https://docs.openclaw.ai
- 社区支持: https://discord.com/invite/clawd
