# Kimi Claw 用户偏好记录

## 项目恢复偏好

用户希望每次启动 Kimi Claw 时：

### 开屏显示
1. 列出最近 3 天内的项目
2. 显示项目名称、最后修改时间、简介
3. 提供快捷指令选择

### 交互流程
```
用户启动 Kimi Claw
    ↓
显示最近项目列表
    ↓
用户选择：
  ├── [1] 继续开发项目 → 加载 PROJECT_LOG.md → 询问具体操作
  ├── [2] 查看项目详情 → 显示代码结构
  ├── [3] 运行测试     → 执行测试
  ├── [4] 推送到 GitHub → 执行推送
  └── [n] 新项目      → 开始新对话
```

### 快捷指令
- "继续开发" → 加载最近项目
- "加载 [项目名]" → 加载指定项目
- "查看项目" → 显示项目详情
- "测试项目" → 运行测试
- "推送 GitHub" → 推送到远程
- "新项目" → 开始新对话
- "列出所有" → 显示所有历史项目

## 项目位置

所有项目保存在：`/root/.openclaw/workspace/projects/`

当前活跃项目：
- **ecommerce-mvp** (2026-02-21 创建)
  - 位置: `/root/.openclaw/workspace/projects/ecommerce-mvp/`
  - 类型: FastAPI 电商系统 MVP
  - 状态: 多 Agent 开发完成，已整合为单体架构

## 辅助脚本

| 脚本 | 位置 | 用途 |
|------|------|------|
| 欢迎界面 | `/root/.openclaw/workspace/kimi-welcome.sh` | 开屏显示最近项目 |
| 项目选择器 | `/root/.openclaw/workspace/welcome-screen.sh` | 交互式项目选择 |
| 项目加载器 | `/root/.openclaw/workspace/project-loader.sh` | 加载项目并执行操作 |
| 恢复脚本 | `/root/.openclaw/workspace/restore-project.sh` | 一键恢复项目 |

## 重要提示

1. 用户已配置 GitHub Skill，可以推送代码
2. 用户希望有版本控制和回滚能力
3. 用户偏好类似浏览器 cookie 的"恢复会话"体验
4. 项目代码已备份到持久化目录（非 /tmp）

## 下次会话启动时

请执行：
```bash
bash /root/.openclaw/workspace/kimi-welcome.sh
```

然后根据用户输入执行相应操作。
