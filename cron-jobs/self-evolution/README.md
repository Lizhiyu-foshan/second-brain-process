# 自我进化流水线 - 多Agent协作系统

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                     全局基础设施层                            │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────────┐  │
│  │ 上下文自动压缩  │ │ 重复消息检查    │ │ 共享配置目录       │  │
│  │ (所有Agent共用)│ │ (所有Agent共用)│ │ shared/config/    │  │
│  └───────────────┘ └───────────────┘ └───────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        Agent层                              │
│                                                              │
│  ┌────────────────┐   ┌────────────────┐   ┌───────────────┐│
│  │   架构师        │   │   开发者        │   │   测试员       ││
│  │  Architect     │ → │  Developer     │ → │   Tester      ││
│  │  (K2.5)        │   │  (GLM-5)       │   │  (Qwen3.5)    ││
│  └────────────────┘   └────────────────┘   └───────────────┘│
│           │                    │                   │        │
│           └────────────────────┴───────────────────┘        │
│                              │                              │
│                              ▼                              │
│                  ┌──────────────────────┐                   │
│                  │  shared/pipeline/    │                   │
│                  │  - plan_YYYYMMDD.json│                   │
│                  │  - dev_report_*.json │                   │
│                  │  - test_report_*.json│                   │
│                  └──────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

## Agent角色定义

### 架构师 (Architect)
- **模型**: Kimi K2.5 (深度思考)
- **职责**: 分析系统缺口、制定改进方案、评估优先级
- **工作目录**: `/root/.openclaw/agents/architect/`
- **输出**: `shared/pipeline/plan_YYYYMMDD.json`

### 开发者 (Developer)
- **模型**: GLM-5 (复杂编码)
- **职责**: 创建Skills、编写代码、生成文档
- **工作目录**: `/root/.openclaw/agents/developer/`
- **输入**: `plan_YYYYMMDD.json`
- **输出**: `shared/pipeline/dev_report_YYYYMMDD.json`

### 测试员 (Tester)
- **模型**: Qwen 3.5 Plus (快速验证)
- **职责**: 验证文件结构、运行基础测试、输出报告
- **工作目录**: `/root/.openclaw/agents/tester/`
- **输入**: `dev_report_YYYYMMDD.json`
- **输出**: `shared/pipeline/test_report_YYYYMMDD.json`

## 共享配置

### 全局规则
**位置**: `shared/config/global-rules.md`

所有Agent必须遵守的共享规则：
- 默认安全优先（删除操作保留）
- GitHub推送四确认检查
- 文件操作规范（trash替代rm）
- 沟通风格（简洁直接）

### 用户偏好
**位置**: `shared/config/user-preferences.json`

包含：
- Agent模型配置
- Pipeline阶段定义
- 全局功能开关（自动压缩、去重等）

## 执行流程

### 定时任务

| 时间 | 任务 | Agent |
|------|------|-------|
| 04:00 | 架构分析 | 架构师 (K2.5) |
| 04:40 | 开发实施 | 开发者 (GLM-5) |
| 05:30 | 测试验证 | 测试员 (Qwen3.5) |

### 数据流转

```
04:00 架构师
  ↓ 读取 .learnings/*
  ↓ 分析缺口
  ↓ 输出 plan_YYYYMMDD.json
  
04:40 开发者
  ↓ 读取 plan_YYYYMMDD.json
  ↓ 创建Skills
  ↓ 输出 dev_report_YYYYMMDD.json
  
05:30 测试员
  ↓ 读取 dev_report_YYYYMMDD.json
  ↓ 验证Skills
  ↓ 输出 test_report_YYYYMMDD.json
```

## 启用/禁用

### 查看任务状态
```bash
openclaw cron list
```

### 启用流水线
```bash
openclaw cron update bc1e430c-b55b-4188-8d2c-03804f121ac2 --enabled true
openclaw cron update bbc6b233-105c-4ee3-9f53-791fc21bf56d --enabled true
openclaw cron update 73f3a81e-9b16-4d8f-8e02-5903f2ecfc50 --enabled true
```

### 禁用流水线
```bash
openclaw cron update bc1e430c-b55b-4188-8d2c-03804f121ac2 --enabled false
openclaw cron update bbc6b233-105c-4ee3-9f53-791fc21bf56d --enabled false
openclaw cron update 73f3a81e-9b16-4d8f-8e02-5903f2ecfc50 --enabled false
```

### 手动触发
```bash
openclaw cron run bc1e430c-b55b-4188-8d2c-03804f121ac2
```

## 文件结构

```
/root/.openclaw/
├── agents/
│   ├── architect/
│   │   ├── AGENTS.md
│   │   ├── SOUL.md
│   │   └── memory/
│   ├── developer/
│   │   ├── AGENTS.md
│   │   ├── SOUL.md
│   │   └── memory/
│   └── tester/
│       ├── AGENTS.md
│       ├── SOUL.md
│       └── memory/
├── workspace/
│   ├── shared/
│   │   ├── config/
│   │   │   ├── global-rules.md
│   │   │   └── user-preferences.json
│   │   └── pipeline/
│   │       ├── plan_YYYYMMDD.json
│   │       ├── dev_report_YYYYMMDD.json
│   │       └── test_report_YYYYMMDD.json
│   └── cron-jobs/
│       └── self-evolution/
│           └── README.md
```

## 全局功能

### 上下文自动压缩
- 作用于: 所有Agent
- 触发条件: Token数 > 200000
- 目标: 压缩到 50000 Token

### 重复消息检查
- 作用于: 所有Agent
- 窗口: 12小时
- 覆盖渠道: Feishu, Kimi-Claw

## 注意事项

1. **Agent隔离**: 每个Agent有自己的memory目录，但共享文件系统
2. **配置继承**: 所有Agent启动时必须读取 `shared/config/`
3. **失败处理**: 任一阶段失败，后续阶段会自动跳过
4. **人工介入**: 复杂决策仍需人工确认，Agent负责执行层面

## 演进计划

当前是**Phase 1**: 固定Pipeline，串行执行

未来**Phase 2**: 
- 架构师发现高优先级gap时，即时触发开发者
- 开发者完成后，即时触发测试员
- 减少等待时间

未来**Phase 3**:
- 架构师评估通过的改进，自动部署
- 仅需人工审核重大变更
