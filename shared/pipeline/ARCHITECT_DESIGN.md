# 任务队列系统 - 架构师设计文档

## 设计目标
建立支持多项目并行、角色轮询、工作锁防冲突的任务队列系统

## 核心组件

### 1. 任务队列存储
- 文件: `shared/pipeline/task_queue.json`
- 结构: 按角色分3个队列，每个队列包含任务列表和锁状态

### 2. 工作锁机制
- 每个角色有独立锁
- 锁状态: idle / busy
- 获取锁后才能执行任务

### 3. 轮询调度器
- 频率: 每15分钟
- 逻辑: 检查队列 → 获取锁 → 执行 → 释放锁

### 4. 守护流程
- 频率: 每30分钟
- 功能: 汇报项目状态、待决策事项

## 数据结构设计

### 动态角色设计
```json
{
  "roles": {
    "architect": {
      "lock": {"status": "idle", "since": null, "task_id": null},
      "queue": [],
      "config": {"poll_interval_minutes": 15, "lock_timeout_minutes": 30}
    },
    "developer": {
      "lock": {"status": "idle", "since": null, "task_id": null},
      "queue": [],
      "config": {"poll_interval_minutes": 15, "lock_timeout_minutes": 60}
    },
    "tester": {
      "lock": {"status": "idle", "since": null, "task_id": null},
      "queue": [],
      "config": {"poll_interval_minutes": 15, "lock_timeout_minutes": 20}
    }
  }
}
```

**新增角色接口**：
- 在 `roles` 对象中添加新角色配置
- 新角色自动继承：锁机制 + 队列 + 轮询配置
- 无需修改核心逻辑代码

### 新增角色示例
```bash
# 添加新角色（如：部署员）
python3 pipeline_admin.py add-role deployer \
  --name "部署员" \
  --description "部署skill到生产环境" \
  --poll-interval 15 \
  --lock-timeout 10

# 自动创建：
# - roles.deployer.lock
# - roles.deployer.queue  
# - roles.deployer.config
# - 更新 role_sequence
```

**角色流水线顺序**：`role_sequence` 数组定义处理顺序
- 当前: ["architect", "developer", "tester"]
- 未来: ["architect", "developer", "tester", "deployer", "monitor"]

## 任务状态流转

### 跨角色流转
```
 architect设计完成
       ↓
 developer接手开发
       ↓
 tester接手验证
       ↓
 用户决策安装
```

### 任务对象结构
```json
{
  "task_id": "task-uuid",
  "project_id": "PROJ-20260315-GAP",
  "gap_id": "GAP-002",
  "skill_name": "skill-factory",
  "status": "pending",  // pending/processing/completed/failed
  "assigned_role": "developer",
  "depends_on": "arch-task-001",  // 前置任务ID
  "created_at": "2026-03-15T10:00:00+08:00",
  "started_at": null,
  "completed_at": null,
  "retry_count": 0,
  "result": null
}
```

## 冲突解决
- 锁超时: 30分钟自动释放
- 失败重试: 最多3次
- 死锁检测: 守护流程检查
