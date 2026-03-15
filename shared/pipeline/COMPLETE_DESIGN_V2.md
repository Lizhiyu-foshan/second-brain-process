# 双层任务编排系统 - 完整设计文档 V2.0

**版本**: 2.0 (完整版)  
**日期**: 2026-03-15  
**开发周期**: 4天高密度  
**锁机制**: 文件锁 (可升级Redis)  

---

## 目录

1. [架构总览](#1-架构总览)
2. [Layer 1: 资源调度层](#2-layer-1-资源调度层)
3. [Layer 2: 规划者/调度层](#3-layer-2-规划者调度层)
4. [Layer 0: 角色工作器](#4-layer-0-角色工作器)
5. [测试钩子系统](#5-测试钩子系统)
6. [固定角色模板机制](#6-固定角色模板机制)
7. [开发计划](#7-开发计划)
8. [GAP迁移计划](#8-gap迁移计划)
9. [文件清单](#9-文件清单)
10. [确认清单](#10-确认清单)

---

## 1. 架构总览

### 1.1 三层架构

```
┌─────────────────────────────────────────────────────────┐
│  Layer 2: Orchestrator (规划者/调度者)                   │
│  ─────────────────────────────────────────────────────  │
│  职责: 项目规划、蓝图设计、时间评估、用户交互             │
│  关键: 必须先查询Layer1状态，再生成规划建议               │
└────────────────────────┬────────────────────────────────┘
                         │ 查询/提交
┌────────────────────────▼────────────────────────────────┐
│  Layer 1: Resource Scheduler (资源调度层)                │
│  ─────────────────────────────────────────────────────  │
│  职责: 角色管理、锁机制、冲突检测、优先级调度             │
│  存储: 文件系统 (JSON状态文件 + 锁文件)                   │
└────────────────────────┬────────────────────────────────┘
                         │ 驱动
┌────────────────────────▼────────────────────────────────┐
│  Layer 0: Role Workers (角色工作器)                      │
│  ─────────────────────────────────────────────────────  │
│  架构师Worker → 开发者Worker → 测试员Worker              │
│  (可扩展: 部署员、监控员、审核员等)                       │
└─────────────────────────────────────────────────────────┘
```

### 1.2 数据流向

```
用户输入 → Orchestrator (Layer2)
              ↓
         查询资源状态 (get_roles_status)
              ↓
         生成蓝图 → 时间评估 → 用户确认
              ↓
         提交任务 (submit_task) → Layer1
              ↓
         角色获取锁 → 执行任务 → 释放锁
              ↓
         用户决策点 (Act阶段)
```

---

## 2. Layer 1: 资源调度层

### 2.1 核心组件

| 组件 | 职责 | 关键功能 |
|------|------|----------|
| **RoleRegistry** | 角色注册表 | 注册/查询角色状态 |
| **LockManager** | 文件锁管理 | acquire/release/超时清理 |
| **TaskQueue** | 任务队列 | submit/get_next/update_status |
| **ConflictDetector** | 冲突检测 | 角色过载/依赖冲突/死锁检测 |
| **PriorityManager** | 优先级管理 | P0抢占/优先级分数计算 |

### 2.2 锁机制设计

```python
class LockManager:
    def acquire(self, role_id, task_id, timeout_ms=30000) -> bool:
        """
        文件锁实现:
        1. 检查锁文件是否存在
        2. 检查是否超时（默认30秒）
        3. 原子写入锁数据
        4. 返回获取结果
        """
        
    def release(self, role_id) -> bool:
        """删除锁文件"""
        
    def cleanup_expired(self):
        """清理所有过期锁"""
```

### 2.3 API接口 (提供给Layer2)

| 接口 | 方法 | 用途 |
|------|------|------|
| `/roles/status` | GET | 查询所有角色状态 |
| `/tasks/submit` | POST | 提交新任务 |
| `/schedule/query` | GET | 查询可行时间窗口 |
| `/lock/acquire` | POST | 角色申请锁 |
| `/lock/release` | POST | 角色释放锁 |
| `/tasks/poll` | GET | 角色轮询获取任务 |
| `/tasks/complete` | POST | 角色完成任务 |

---

## 3. Layer 2: 规划者/调度层

### 3.1 核心组件

| 组件 | 职责 | 关键功能 |
|------|------|----------|
| **Orchestrator** | 规划者主类 | 项目生命周期管理、用户交互 |
| **Planner** | 规划引擎 | 蓝图生成、任务分解、角色映射 |
| **Estimator** | 时间评估 | 基于资源状态和历史的工期估算 |
| **UserInterface** | 用户接口 | 命令处理、状态格式化输出 |

### 3.2 固定角色模板机制 ⭐

**新类型首次出现时**：

```
用户: "启动市场调研报告"
          ↓
规划者识别: market_research (新类型，无固定模板)
          ↓
暂停自动创建，发送确认消息:

━━━━━━━━━━━━━━━━━━━━━━━━━━
🆕 发现新的任务类型，需要创建固定角色模板

类型ID: market_research

📋 建议的角色配置:
  1. 市场研究员 (researcher)
     能力: data_collection, survey_design
  2. 数据分析师 (analyst)
     能力: statistical_analysis
  3. 报告撰写员 (writer)
     能力: report_writing

❓ 请确认:
  A. 确认创建 - 创建固定模板（长期复用）
  B. 修改后创建 - 调整角色或能力
  C. 仅本次使用 - 临时角色（项目结束销毁）
  D. 取消 - 暂不处理
━━━━━━━━━━━━━━━━━━━━━━━━━━

用户: "确认 REQ_XXXX B: 增加可视化设计师"
          ↓
创建固定模板 (4个角色) + 继续项目
          ↓
后续同类任务自动使用此模板
```

**固定角色 vs 临时角色对比**：

| 特性 | 固定角色模板 | 临时角色 |
|------|-------------|----------|
| 生命周期 | 长期存在，跨项目复用 | 随项目创建和销毁 |
| 经验沉淀 | ✅ 积累历史数据 | ❌ 项目结束清除 |
| 配置优化 | ✅ 基于历史自动优化 | ❌ 每次重新配置 |
| 创建触发 | 新类型→主会话确认 | 规划者自动创建 |

### 3.3 用户命令

| 命令 | 功能 |
|------|------|
| `启动 [描述]` | 创建新项目，获取规划建议 |
| `确认 [ID] [方案]` | 确认方案（正常/加急/宽松） |
| `查询 [项目ID]` | 查看项目状态和进度 |
| `调整 [项目ID] [调整项]` | 调整项目（延长/暂停/恢复） |
| `状态` | 查看所有项目列表 |
| `暂停 [项目ID]` | 暂停项目执行 |
| `恢复 [项目ID]` | 恢复项目执行 |

### 3.4 PDCA循环

每个项目遵循PDCA循环：

```
Plan (规划) → Do (执行) → Check (检查) → Act (决策)
                                              ↓
用户决策点: 继续/调整/完成/暂停
```

---

## 4. Layer 0: 角色工作器

### 4.1 基础工作器

```python
class BaseRoleWorker(ABC):
    def start(self):
        """轮询循环:"""
        while running:
            1. poll_task()      # 获取任务
            2. acquire_lock()   # 获取锁
            3. execute_task()   # 执行任务
            4. complete_task()  # 完成上报
            5. release_lock()   # 释放锁
    
    @abstractmethod
    def execute_task(self, task_data) -> Dict:
        """子类实现具体逻辑"""
```

### 4.2 角色实现

| 角色 | 文件 | 职责 |
|------|------|------|
| **ArchitectWorker** | `workers/architect.py` | 架构设计、方案规划 |
| **DeveloperWorker** | `workers/developer.py` | 代码实现、skill创建 |
| **TesterWorker** | `workers/tester.py` | 测试验证、质量报告 |

---

## 5. 测试钩子系统 ⭐

### 5.1 设计目标

覆盖测试员评估报告中的所有需求：
- ✅ 状态驱动测试
- ✅ 故障注入测试
- ✅ 并发测试
- ✅ 契约测试

### 5.2 钩子注入点

| 层级 | 注入点 | 时机 |
|------|--------|------|
| **LockManager** | `lock:before_acquire` | 锁获取前 |
| | `lock:after_acquire` | 锁获取后 |
| | `lock:before_release` | 锁释放前 |
| | `lock:after_release` | 锁释放后 |
| **Orchestrator** | `orchestrator:before_create` | 项目创建前 |
| | `orchestrator:after_create` | 项目创建后 |
| **TaskQueue** | `task:before_submit` | 任务提交前 |
| | `task:after_complete` | 任务完成后 |

### 5.3 故障注入器

```python
class FaultInjector:
    def inject(self, fault_type, target, probability=1.0):
        """
        fault_type:
        - crash: 抛出异常
        - delay: 延迟响应
        - error: 返回错误
        - corruption: 数据损坏
        """
```

### 5.4 测试专用API

| API | 功能 |
|-----|------|
| `freeze_time()` | 冻结时间 |
| `accelerate_time(factor)` | 加速时间 |
| `get_state_snapshot()` | 获取完整状态快照 |
| `restore_state(snapshot)` | 恢复到指定状态 |
| `simulate_role_busy(role_id, duration)` | 模拟角色忙碌 |

---

## 6. GAP迁移计划

### 6.1 迁移内容

| GAP | 名称 | 状态 | 迁移方式 |
|-----|------|------|----------|
| GAP-002 | skill-factory | ⏳ 待开发 | 创建项目，自动分配角色 |
| GAP-003 | feishu-context-manager | ⏳ 待开发 | 创建项目，自动分配角色 |
| GAP-004 | config-validator | ⏳ 待开发 | 创建项目，自动分配角色 |
| GAP-005 | git-push-recovery | ⏳ 待开发 | 创建项目，自动分配角色 |
| GAP-006 | skill-market-metadata | ⏳ 待开发 | 创建项目，自动分配角色 |

### 6.2 自动迁移流程

```
系统上线后自动执行:

1. 创建迁移项目:
   项目ID: PROJ-20260315-GAP-MIGRATION
   名称: GAP-002到006批量迁移

2. 自动分解任务:
   5个GAP × 3个角色 = 15个子任务
   每个GAP: 架构→开发→测试完整链

3. 自动提交到Layer1:
   任务进入各角色队列
   按依赖关系自动调度

4. 用户只需决策:
   每GAP测试完成后 → 通知用户"是否安装"
   用户回复 → 继续下一个
```

---

## 7. 开发计划 (4天高密度)

### Day 1: Layer 1 核心 (12小时)

| 时间 | 任务 | 产出 |
|------|------|------|
| 0-4h | RoleRegistry + LockManager | 角色管理 + 文件锁实现 |
| 4-8h | TaskQueue + ConflictDetector | 任务队列 + 冲突检测 |
| 8-10h | PriorityManager + API接口 | 优先级管理 + API封装 |
| 10-12h | 单元测试 | Layer 1 测试覆盖 |

### Day 2: Layer 2 核心 (12小时)

| 时间 | 任务 | 产出 |
|------|------|------|
| 0-4h | Orchestrator + Planner | 规划者主类 + 规划引擎 |
| 4-8h | Estimator + UserInterface | 时间评估 + 用户交互 |
| 8-10h | 固定角色模板机制 | FixedRoleTemplateManager |
| 10-12h | 集成测试 | Layer 1+2 集成测试 |

### Day 3: 角色工作器 + 集成 (12小时)

| 时间 | 任务 | 产出 |
|------|------|------|
| 0-4h | BaseRoleWorker + ArchitectWorker | 基础工作器 + 架构师 |
| 4-8h | DeveloperWorker + TesterWorker | 开发者 + 测试员 |
| 8-10h | 测试钩子系统 | TestHooks + FaultInjector |
| 10-12h | E2E测试 | 完整流程测试 |

### Day 4: 优化 + GAP迁移 + 上线 (12小时)

| 时间 | 任务 | 产出 |
|------|------|------|
| 0-4h | 性能优化 + 错误处理 | 锁超时优化、故障恢复 |
| 4-8h | 监控/日志 + 文档 | 运维工具 + 使用文档 |
| 8-10h | GAP迁移准备 | 迁移脚本 + 任务创建 |
| 10-12h | 最终测试 + 上线 | 生产环境部署 |

---

## 8. 文件清单

### 8.1 代码文件

```
/shared/pipeline/
├── layer1/
│   ├── __init__.py
│   ├── role_registry.py
│   ├── lock_manager.py
│   ├── task_queue.py
│   ├── conflict_detector.py
│   ├── priority_manager.py
│   └── api.py
├── layer2/
│   ├── __init__.py
│   ├── orchestrator.py
│   ├── planner.py
│   ├── estimator.py
│   ├── user_interface.py
│   └── fixed_role_templates.py  ⭐
├── workers/
│   ├── __init__.py
│   ├── base.py
│   ├── architect.py
│   ├── developer.py
│   └── tester.py
├── shared/
│   ├── __init__.py
│   ├── models.py
│   ├── utils.py
│   ├── test_hooks.py            ⭐
│   └── fault_injection.py       ⭐
├── tests/
│   └── api.py                   ⭐
├── cli.py
└── scheduler_daemon.py
```

### 8.2 状态文件

```
/shared/pipeline/
├── state/
│   ├── layer1_state.json
│   ├── task_queue.json
│   ├── orchestrator_state.json
│   ├── execution_history.json
│   └── fixed_role_templates.json  ⭐
└── locks/
    └── *.lock
```

---

## 9. 确认清单

### 9.1 架构确认

| 检查项 | 状态 |
|--------|------|
| 双层解耦架构 (Layer1调度 + Layer2规划) | ✅ |
| 完全解耦设计 (仅通过API交互) | ✅ |
| 用户决策权保留 (PDCA Act阶段) | ✅ |
| 支持扩展新角色 | ✅ |

### 9.2 技术选型确认

| 检查项 | 选型 | 状态 |
|--------|------|------|
| 锁机制 | 文件锁 (可升级Redis) | ✅ |
| 开发范围 | 完整版 | ✅ |
| 开发周期 | 4天高密度 | ✅ |
| 开发顺序 | Layer1 → Layer2 → Workers | ✅ |

### 9.3 特殊机制确认

| 检查项 | 状态 |
|--------|------|
| 测试钩子系统 (支持故障注入、状态测试) | ✅ |
| 固定角色模板机制 (新类型→主会话确认) | ✅ |
| 临时角色机制 (一次性项目自动创建) | ✅ |
| GAP-002~006自动迁移 | ✅ |

### 9.4 风险确认

| 风险 | 缓解方案 | 状态 |
|------|----------|------|
| 4天开发周期紧张 | 高密度开发，每天12小时 | ✅ 接受 |
| 文件锁性能瓶颈 | 初期够用，后续升级Redis | ✅ 接受 |
| GAP迁移复杂性 | 自动化迁移脚本 | ✅ 接受 |

---

## 10. 决策点

### 选项A: 确认进入开发阶段
```
回复: "确认进入开发阶段"
```
→ 立即开始Day 1: Layer 1 资源调度层开发

### 选项B: 调整需求
```
回复: "调整: [具体调整内容]"
```
→ 根据调整内容修改设计

### 选项C: 查看详细设计
```
回复: "查看 [组件名] 详情"
```
→ 展示指定组件的详细设计代码

### 选项D: 暂停/取消
```
回复: "暂停" 或 "取消"
```
→ 保存当前设计，等待后续决策

---

**设计文档已完整，等待你的最终review和决策。**
