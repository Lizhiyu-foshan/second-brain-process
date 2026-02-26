# Kimi Claw 自动启动配置
# 将此文件内容添加到 Kimi Claw 的系统提示中

## 会话启动自动执行

每次会话开始时，请执行以下操作：

### 1. 运行开屏项目选择器
```bash
bash /root/.openclaw/workspace/welcome-screen.sh
```

### 2. 根据输出决定下一步

**如果有项目：**
- 显示项目列表
- 询问用户选择哪个项目
- 或者是否开始新对话

**如果没有项目：**
- 正常开始新对话

### 3. 如果用户选择继续开发项目

请执行：
```bash
bash /root/.openclaw/workspace/project-loader.sh
```

然后按照用户选择执行相应操作。

### 4. 快捷命令

用户可以直接说：
- "继续开发项目" → 列出最近项目
- "加载 [项目名称]" → 直接加载指定项目
- "查看所有项目" → 列出所有历史项目
- "新项目" → 跳过项目选择，开始新对话

## 项目数据结构

项目位置：`/root/.openclaw/workspace/projects/`
每个项目应包含：
- `PROJECT_LOG.md` - 项目历史和上下文
- `.git/` - Git 版本控制
- 代码文件

## 恢复机制

如果项目选择器失效，备用方案：
1. 检查 `/root/.openclaw/workspace/projects/` 目录
2. 查找最近修改的项目
3. 询问用户是否继续开发
