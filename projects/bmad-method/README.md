# BMAD-METHOD 项目

**项目位置**: `/root/.openclaw/workspace/projects/bmad-method/`  
**创建时间**: 2026-02-23  
**版本**: v2.0

---

## 什么是 BMAD

**BMAD** = **B**ased on **M**ulti-**A**gent **D**evelopment  
基于多 Agent 的并行开发方法论

---

## 核心思想

将大型项目拆分为多个独立模块，由多个 AI Agent 并行开发，最后整合为统一系统。

### 工作流程

```
需求分析
    ↓
模块拆分 (按业务边界)
    ↓
Agent 分配 (每个模块 1 个 Agent)
    ↓
并行开发 (同时进行)
    ↓
代码整合 (统一架构)
    ↓
联调测试 (修复冲突)
    ↓
缺陷修复 (并行修复)
    ↓
发布上线
```

---

## 成功验证案例

### ecommerce-mvp (2026-02-21)

| 指标 | 数据 |
|------|------|
| Agent 数量 | 9 个 |
| 开发时间 | 约 4 小时 |
| 代码行数 | 约 6500 行 |
| 测试用例 | 201 个 |
| 测试通过率 | 99.4% |
| 文档字数 | 约 96000 字 |

**成果**: 完整的电商 MVP 系统，达到生产环境标准

---

## 方法论文档

### 1. 模块拆分原则
- 按业务边界拆分（非技术分层）
- 每个模块有明确的输入/输出接口
- 模块间通过标准协议通信

### 2. Agent 分配策略
- 每个模块分配 1 个开发 Agent
- 每个模块分配 1 个测试 Agent
- 1 个整合 Agent 负责代码合并

### 3. 通信协议
- 单体架构: 进程内函数调用 (< 1ms)
- 模块化单体: HTTP localhost
- 微服务: HTTP + 服务发现

### 4. 质量保证
- 单元测试覆盖率 > 95%
- 集成测试通过率 > 80%
- 代码审查 checklist

---

## 工具链

| 工具 | 用途 |
|------|------|
| FastAPI | API 框架 |
| SQLAlchemy | ORM |
| pytest | 测试框架 |
| Git | 版本控制 |
| OpenClaw | Agent 调度 |

---

## 演进路线

### v1.0 (概念验证)
- 3 个 Agent 并行
- 简单模块拆分

### v2.0 (当前)
- 9 个 Agent 并行
- 完整的开发-测试-修复闭环
- 标准化文档输出

### v3.0 (规划中)
- 自动模块拆分
- 智能 Agent 调度
- 自适应通信协议

---

## 使用方式

### 启动新项目

```
1. 需求分析 → 确定模块边界
2. 创建 bmad-project.md 规划文档
3. 为每个模块创建独立目录
4. 启动开发 Agent 并行工作
5. 整合代码并测试
```

### 参考案例

查看 `ecommerce-mvp` 项目的完整实施过程：
- `/root/.openclaw/workspace/projects/ecommerce-mvp/PROJECT_LOG.md`
- `/root/.openclaw/workspace/projects/ecommerce-mvp/FINAL_PROJECT_COMPLETION.md`

---

## 待完善内容

- [ ] 详细的模块拆分指南
- [ ] Agent 提示词模板
- [ ] 整合 checklist
- [ ] 常见问题 FAQ
- [ ] 视频教程

---

**BMAD-METHOD: 让多 Agent 协作开发成为标准实践**
