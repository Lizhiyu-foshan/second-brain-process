# 双层任务编排系统 - 完整版设计文档

## 版本信息
- 版本: 2.0 (完整版)
- 设计日期: 2026-03-15
- 锁机制: 文件锁 (后续可升级Redis)
- 开发周期: 高密度4天

---

## 架构确认

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

---

## Layer 1: 资源调度层详细设计

### 1.1 核心组件

#### RoleRegistry (角色注册表)
```python
class RoleRegistry:
    """管理所有角色实例"""
    
    def __init__(self, state_file: str):
        self.state_file = state_file
        self.roles: Dict[str, Role] = {}
        self._load()
    
    def register(self, role_type: str, name: str, capabilities: List[str]) -> str:
        """注册新角色，返回role_id"""
        role_id = f"{role_type}_{uuid4().hex[:6]}"
        self.roles[role_id] = Role(
            id=role_id,
            type=role_type,
            name=name,
            capabilities=capabilities,
            status="idle",
            queue=[],
            metrics=RoleMetrics()
        )
        self._save()
        return role_id
    
    def get_status(self) -> Dict:
        """供Layer2查询所有角色状态"""
        return {
            role_id: {
                "type": role.type,
                "status": role.status,
                "queue_depth": len(role.queue),
                "current_task": role.current_task,
                "metrics": {
                    "avg_duration": role.metrics.avg_duration,
                    "success_rate": role.metrics.success_rate
                }
            }
            for role_id, role in self.roles.items()
        }
```

#### LockManager (文件锁管理器)
```python
class LockManager:
    """基于文件系统的分布式锁"""
    
    def __init__(self, lock_dir: str = "/root/.openclaw/workspace/shared/pipeline/locks"):
        self.lock_dir = Path(lock_dir)
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        self.default_timeout_ms = 30000  # 30秒
    
    def acquire(self, role_id: str, task_id: str, timeout_ms: int = None) -> bool:
        """
        获取锁
        返回: True=获取成功, False=已被占用
        """
        lock_file = self.lock_dir / f"{role_id}.lock"
        timeout_ms = timeout_ms or self.default_timeout_ms
        
        # 检查现有锁
        if lock_file.exists():
            try:
                lock_data = json.loads(lock_file.read_text())
                locked_at = datetime.fromisoformat(lock_data["acquired_at"])
                
                # 检查是否超时
                if datetime.now() - locked_at > timedelta(milliseconds=timeout_ms):
                    # 锁超时，强制释放
                    lock_file.unlink()
                    logging.warning(f"Lock timeout released for {role_id}")
                else:
                    return False
            except (json.JSONDecodeError, KeyError, ValueError):
                # 锁文件损坏，强制删除
                lock_file.unlink()
        
        # 创建新锁
        lock_data = {
            "role_id": role_id,
            "task_id": task_id,
            "acquired_at": datetime.now().isoformat(),
            "timeout_ms": timeout_ms
        }
        
        # 原子写入
        tmp_file = lock_file.with_suffix('.tmp')
        tmp_file.write_text(json.dumps(lock_data))
        tmp_file.rename(lock_file)
        
        return True
    
    def release(self, role_id: str) -> bool:
        """释放锁"""
        lock_file = self.lock_dir / f"{role_id}.lock"
        if lock_file.exists():
            lock_file.unlink()
            return True
        return False
    
    def get_lock_info(self, role_id: str) -> Optional[Dict]:
        """获取锁信息"""
        lock_file = self.lock_dir / f"{role_id}.lock"
        if lock_file.exists():
            try:
                return json.loads(lock_file.read_text())
            except:
                return None
        return None
    
    def cleanup_expired(self):
        """清理所有过期锁"""
        for lock_file in self.lock_dir.glob("*.lock"):
            try:
                lock_data = json.loads(lock_file.read_text())
                locked_at = datetime.fromisoformat(lock_data["acquired_at"])
                timeout_ms = lock_data.get("timeout_ms", self.default_timeout_ms)
                
                if datetime.now() - locked_at > timedelta(milliseconds=timeout_ms):
                    lock_file.unlink()
                    logging.info(f"Cleaned expired lock: {lock_file.name}")
            except:
                # 损坏的锁文件直接删除
                lock_file.unlink()
```

#### ConflictDetector (冲突检测器)
```python
class ConflictDetector:
    """检测任务调度冲突"""
    
    def __init__(self, task_queue: TaskQueue, role_registry: RoleRegistry):
        self.task_queue = task_queue
        self.role_registry = role_registry
        self.conflict_log: List[Conflict] = []
    
    def check_task_submit(self, task: Task) -> List[Conflict]:
        """
        检查任务提交时的冲突
        返回冲突列表，空列表表示无冲突
        """
        conflicts = []
        
        # 1. 检查同一角色多任务冲突
        role = self.role_registry.get(task.role_id)
        if role.status == "busy" and len(role.queue) > 0:
            conflicts.append(Conflict(
                type="ROLE_OVERLOAD",
                severity="warning",
                message=f"角色 {role.name} 已有 {len(role.queue)} 个排队任务",
                suggestion="考虑错峰安排或增加角色实例"
            ))
        
        # 2. 检查依赖冲突
        for dep_task_id in task.depends_on:
            dep_task = self.task_queue.get(dep_task_id)
            if not dep_task:
                conflicts.append(Conflict(
                    type="MISSING_DEPENDENCY",
                    severity="error",
                    message=f"依赖任务 {dep_task_id} 不存在",
                    suggestion="检查任务ID或重新规划"
                ))
            elif dep_task.status not in ["completed", "failed"]:
                conflicts.append(Conflict(
                    type="INCOMPLETE_DEPENDENCY", 
                    severity="warning",
                    message=f"依赖任务 {dep_task_id} 状态为 {dep_task.status}",
                    suggestion="任务将等待依赖完成"
                ))
        
        # 3. 检查时间窗口冲突
        # (简化版，完整版可添加时间窗口逻辑)
        
        # 4. 检查优先级反转
        if task.priority == "P0":
            # P0任务检查是否有低优先级任务占用资源
            if role.status == "busy":
                current_task = self.task_queue.get(role.current_task)
                if current_task and current_task.priority != "P0":
                    conflicts.append(Conflict(
                        type="PRIORITY_INVERSION",
                        severity="info",
                        message="P0任务将抢占当前执行中的低优先级任务",
                        suggestion="当前任务将被暂停，P0任务优先执行"
                    ))
        
        self.conflict_log.extend(conflicts)
        return conflicts
    
    def detect_deadlock(self) -> Optional[List[str]]:
        """
        检测死锁
        返回: 死锁涉及的任务ID列表，None表示无死锁
        """
        # 构建等待图
        wait_graph = defaultdict(set)
        
        for task in self.task_queue.get_processing():
            if task.depends_on:
                for dep_id in task.depends_on:
                    dep_task = self.task_queue.get(dep_id)
                    if dep_task and dep_task.status != "completed":
                        wait_graph[task.id].add(dep_id)
        
        # 检测环
        visited = set()
        rec_stack = set()
        
        def has_cycle(node, path):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in wait_graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, path):
                        return True
                elif neighbor in rec_stack:
                    # 发现环
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:]
            
            path.pop()
            rec_stack.remove(node)
            return False
        
        for node in wait_graph:
            if node not in visited:
                cycle = has_cycle(node, [])
                if cycle:
                    return cycle
        
        return None
```

#### PriorityManager (优先级管理器)
```python
class PriorityManager:
    """管理任务优先级"""
    
    PRIORITY_LEVELS = {
        "P0": {"name": "紧急", "weight": 100, "preempt": True},
        "P1": {"name": "高", "weight": 50, "preempt": False},
        "P2": {"name": "中", "weight": 10, "preempt": False},
        "P3": {"name": "低", "weight": 1, "preempt": False}
    }
    
    def calculate_priority_score(self, task: Task) -> int:
        """
        计算任务优先级分数
        考虑: 优先级权重 + 等待时间 + 依赖链长度
        """
        base_weight = self.PRIORITY_LEVELS[task.priority]["weight"]
        
        # 等待时间加成 (每等待1小时+1分)
        wait_hours = (datetime.now() - task.created_at).total_seconds() / 3600
        wait_bonus = min(int(wait_hours), 20)  # 最多+20
        
        # 依赖链长度惩罚 (依赖越多优先级略微降低)
        dep_penalty = len(task.depends_on) * 2
        
        return base_weight + wait_bonus - dep_penalty
    
    def sort_queue(self, tasks: List[Task]) -> List[Task]:
        """按优先级排序队列"""
        return sorted(tasks, key=lambda t: self.calculate_priority_score(t), reverse=True)
    
    def should_preempt(self, new_task: Task, current_task: Task) -> bool:
        """
        判断新任务是否应该抢占当前任务
        只有P0任务可以抢占，且只能抢占P1/P2/P3
        """
        if new_task.priority != "P0":
            return False
        if current_task.priority == "P0":
            return False
        return self.PRIORITY_LEVELS["P0"]["preempt"]
```

#### TaskQueue (任务队列)
```python
class TaskQueue:
    """管理全局任务队列"""
    
    def __init__(self, state_file: str):
        self.state_file = state_file
        self.tasks: Dict[str, Task] = {}
        self._load()
    
    def submit(self, task: Task) -> str:
        """提交新任务"""
        task.id = f"task_{uuid4().hex[:8]}"
        task.status = "pending"
        task.created_at = datetime.now()
        self.tasks[task.id] = task
        self._save()
        return task.id
    
    def get_next_for_role(self, role_id: str) -> Optional[Task]:
        """获取角色下一个可执行任务"""
        # 获取该角色的pending任务
        role_tasks = [
            t for t in self.tasks.values()
            if t.role_id == role_id and t.status == "pending"
        ]
        
        # 过滤掉依赖未完成的任务
        ready_tasks = []
        for task in role_tasks:
            deps_completed = all(
                self.tasks.get(dep_id, Task()).status == "completed"
                for dep_id in task.depends_on
            )
            if deps_completed:
                ready_tasks.append(task)
        
        if not ready_tasks:
            return None
        
        # 按优先级排序
        priority_manager = PriorityManager()
        sorted_tasks = priority_manager.sort_queue(ready_tasks)
        
        return sorted_tasks[0]
    
    def update_status(self, task_id: str, status: str, result: Dict = None):
        """更新任务状态"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = status
            
            if status == "processing":
                task.started_at = datetime.now()
            elif status in ["completed", "failed"]:
                task.completed_at = datetime.now()
                if result:
                    task.result = result
            
            self._save()
    
    def get_statistics(self) -> Dict:
        """获取队列统计"""
        stats = defaultdict(int)
        for task in self.tasks.values():
            stats[task.status] += 1
        return dict(stats)
```

### 1.2 数据模型

```python
@dataclass
class Role:
    id: str
    type: str
    name: str
    capabilities: List[str]
    status: str  # idle, busy, error
    queue: List[str]  # task_ids
    current_task: Optional[str] = None
    metrics: 'RoleMetrics' = None
    config: 'RoleConfig' = None

@dataclass
class RoleMetrics:
    total_tasks: int = 0
    success_count: int = 0
    fail_count: int = 0
    avg_duration: float = 0.0  # minutes
    success_rate: float = 1.0
    
    def update(self, duration_minutes: float, success: bool):
        self.total_tasks += 1
        if success:
            self.success_count += 1
        else:
            self.fail_count += 1
        
        # 更新平均耗时
        self.avg_duration = (
            (self.avg_duration * (self.total_tasks - 1) + duration_minutes)
            / self.total_tasks
        )
        
        self.success_rate = self.success_count / self.total_tasks

@dataclass
class Task:
    id: str = ""
    project_id: str = ""
    role_id: str = ""
    name: str = ""
    description: str = ""
    priority: str = "P2"  # P0, P1, P2, P3
    status: str = "pending"  # pending, processing, completed, failed
    depends_on: List[str] = None
    created_at: datetime = None
    started_at: datetime = None
    completed_at: datetime = None
    retry_count: int = 0
    max_retries: int = 3
    result: Dict = None
    
    def __post_init__(self):
        if self.depends_on is None:
            self.depends_on = []
        if self.result is None:
            self.result = {}

@dataclass
class Conflict:
    type: str
    severity: str  # error, warning, info
    message: str
    suggestion: str
    detected_at: datetime = None
    
    def __post_init__(self):
        if self.detected_at is None:
            self.detected_at = datetime.now()

@dataclass
class RoleConfig:
    poll_interval_minutes: int = 15
    lock_timeout_minutes: int = 30
    max_concurrent: int = 1
```

### 1.3 API接口

```python
class ResourceSchedulerAPI:
    """Layer 1 提供的API接口"""
    
    def __init__(self):
        self.registry = RoleRegistry("/root/.openclaw/workspace/shared/pipeline/layer1_state.json")
        self.lock_manager = LockManager()
        self.task_queue = TaskQueue("/root/.openclaw/workspace/shared/pipeline/task_queue.json")
        self.conflict_detector = ConflictDetector(self.task_queue, self.registry)
        self.priority_manager = PriorityManager()
    
    # ========== 提供给 Layer 2 (Orchestrator) 的接口 ==========
    
    def get_roles_status(self) -> Dict:
        """
        GET /roles/status
        查询所有角色状态（供规划者评估用）
        """
        return {
            "roles": self.registry.get_status(),
            "timestamp": datetime.now().isoformat()
        }
    
    def submit_task(self, task_data: Dict) -> Dict:
        """
        POST /tasks/submit
        提交新任务
        """
        task = Task(**task_data)
        
        # 冲突检测
        conflicts = self.conflict_detector.check_task_submit(task)
        errors = [c for c in conflicts if c.severity == "error"]
        
        if errors:
            return {
                "success": False,
                "task_id": None,
                "conflicts": [c.__dict__ for c in conflicts],
                "message": "提交失败，存在严重冲突"
            }
        
        # 提交任务
        task_id = self.task_queue.submit(task)
        
        return {
            "success": True,
            "task_id": task_id,
            "conflicts": [c.__dict__ for c in conflicts if c.severity != "error"],
            "message": "任务已提交"
        }
    
    def query_schedule(self, required_roles: List[str], duration_minutes: int) -> Dict:
        """
        GET /schedule/query
        查询可行时间窗口
        """
        status = self.registry.get_status()
        
        # 检查所需角色是否都有空闲时段
        available_slots = []
        for role_id in required_roles:
            if role_id in status:
                role_status = status[role_id]
                if role_status["status"] == "idle":
                    available_slots.append({
                        "role_id": role_id,
                        "available": "now"
                    })
                else:
                    # 估算等待时间
                    queue_depth = role_status["queue_depth"]
                    avg_duration = role_status["metrics"]["avg_duration"]
                    wait_minutes = queue_depth * avg_duration
                    available_slots.append({
                        "role_id": role_id,
                        "available": f"in_{wait_minutes}_minutes"
                    })
        
        # 找出最晚可用时间
        max_wait = max(
            (int(s["available"].split("_")[1]) if "in_" in s["available"] else 0)
            for s in available_slots
        )
        
        return {
            "earliest_start": (datetime.now() + timedelta(minutes=max_wait)).isoformat(),
            "estimated_duration_minutes": duration_minutes,
            "role_availability": available_slots,
            "feasible": all(s["available"] == "now" or int(s["available"].split("_")[1]) < 60 
                          for s in available_slots)
        }
    
    # ========== 提供给 Role Workers 的接口 ==========
    
    def acquire_lock(self, role_id: str, task_id: str) -> Dict:
        """
        POST /lock/acquire
        角色申请锁
        """
        acquired = self.lock_manager.acquire(role_id, task_id)
        
        if acquired:
            # 更新角色状态
            role = self.registry.roles.get(role_id)
            if role:
                role.status = "busy"
                role.current_task = task_id
                self.registry._save()
            
            # 更新任务状态
            self.task_queue.update_status(task_id, "processing")
        
        return {
            "acquired": acquired,
            "role_id": role_id,
            "task_id": task_id,
            "timestamp": datetime.now().isoformat()
        }
    
    def release_lock(self, role_id: str) -> Dict:
        """
        POST /lock/release
        角色释放锁
        """
        released = self.lock_manager.release(role_id)
        
        if released:
            # 更新角色状态
            role = self.registry.roles.get(role_id)
            if role:
                role.status = "idle"
                role.current_task = None
                self.registry._save()
        
        return {
            "released": released,
            "role_id": role_id,
            "timestamp": datetime.now().isoformat()
        }
    
    def poll_task(self, role_id: str) -> Optional[Dict]:
        """
        GET /tasks/poll
        角色轮询获取任务
        """
        # 检查是否有锁
        lock_info = self.lock_manager.get_lock_info(role_id)
        if not lock_info:
            return None
        
        # 获取下一个任务
        task = self.task_queue.get_next_for_role(role_id)
        
        if task:
            return {
                "task_id": task.id,
                "project_id": task.project_id,
                "name": task.name,
                "description": task.description,
                "priority": task.priority,
                "depends_on": task.depends_on
            }
        
        return None
    
    def complete_task(self, task_id: str, success: bool, result: Dict) -> Dict:
        """
        POST /tasks/complete
        角色完成任务
        """
        status = "completed" if success else "failed"
        self.task_queue.update_status(task_id, status, result)
        
        # 更新角色指标
        task = self.task_queue.tasks.get(task_id)
        if task:
            role = self.registry.roles.get(task.role_id)
            if role:
                duration = 0
                if task.started_at and task.completed_at:
                    duration = (task.completed_at - task.started_at).total_seconds() / 60
                role.metrics.update(duration, success)
                self.registry._save()
        
        return {
            "task_id": task_id,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
    
    # ========== 维护接口 ==========
    
    def cleanup(self):
        """清理过期锁和状态"""
        self.lock_manager.cleanup_expired()
        
        # 检测死锁
        deadlock = self.conflict_detector.detect_deadlock()
        if deadlock:
            logging.error(f"Deadlock detected: {deadlock}")
            # 可以选择自动解除或告警
```

---

## Layer 2: 规划者/调度层详细设计

### 2.1 核心组件

#### Orchestrator (规划者主类)
```python
class Orchestrator:
    """
    规划者/调度者
    用户唯一入口，负责项目规划、时间评估、用户交互
    """
    
    def __init__(self):
        self.scheduler_api = ResourceSchedulerAPI()
        self.planner = Planner(self.scheduler_api)
        self.estimator = Estimator(self.scheduler_api)
        self.projects: Dict[str, Project] = {}
        self._load_projects()
    
    def create_project(self, description: str, user_constraints: Dict = None) -> ProjectPlan:
        """
        创建新项目
        
        流程:
        1. 任务类型识别
        2. 查询资源状态
        3. 生成蓝图
        4. 时间评估
        5. 生成规划建议
        """
        # Step 1: 识别任务类型
        project_type = self._identify_project_type(description)
        
        # Step 2: 查询资源状态
        resource_status = self.scheduler_api.get_roles_status()
        
        # Step 3: 生成蓝图
        blueprint = self.planner.create_blueprint(
            description=description,
            project_type=project_type,
            user_constraints=user_constraints
        )
        
        # Step 4: 时间评估
        time_estimate = self.estimator.estimate_duration(
            blueprint=blueprint,
            resource_status=resource_status
        )
        
        # Step 5: 生成规划建议
        plan = ProjectPlan(
            project_id=f"PROJ_{datetime.now().strftime('%Y%m%d')}_{uuid4().hex[:4]}",
            name=blueprint.name,
            type=project_type,
            description=description,
            blueprint=blueprint,
            time_estimate=time_estimate,
            resource_status=resource_status,
            alternatives=self._generate_alternatives(blueprint, time_estimate)
        )
        
        return plan
    
    def _identify_project_type(self, description: str) -> str:
        """识别项目类型"""
        keywords = {
            "system_dev": ["GAP", "skill", "bug", "优化", "系统改进", "开发"],
            "content_creation": ["文章", "视频", "创作", "写作", "内容"],
            "course_design": ["课程", "教学", "学习路径", "教程"],
            "data_analysis": ["数据", "分析", "报告", "可视化"]
        }
        
        scores = {}
        for ptype, words in keywords.items():
            score = sum(1 for w in words if w in description)
            scores[ptype] = score
        
        return max(scores, key=scores.get) if max(scores.values()) > 0 else "general"
    
    def _generate_alternatives(self, blueprint: Blueprint, estimate: TimeEstimate) -> List[PlanAlternative]:
        """生成替代方案"""
        alternatives = []
        
        # 方案A: 正常节奏
        alternatives.append(PlanAlternative(
            name="正常节奏",
            duration_days=estimate.normal_days,
            description=f"按正常节奏完成，预计{estimate.normal_days}天",
            risk_level="低",
            confidence="高"
        ))
        
        # 方案B: 加急
        if estimate.normal_days > 2:
            alternatives.append(PlanAlternative(
                name="加急处理",
                duration_days=max(1, estimate.normal_days - 2),
                description="压缩时间，增加并行度",
                risk_level="中",
                confidence="中"
            ))
        
        # 方案C: 宽松
        alternatives.append(PlanAlternative(
            name="宽松节奏",
            duration_days=estimate.normal_days + 2,
            description="延长时间，确保高质量",
            risk_level="低",
            confidence="极高"
        ))
        
        return alternatives
    
    def submit_project(self, plan: ProjectPlan, user_choice: str) -> Project:
        """
        用户确认后提交项目
        
        user_choice: "正常节奏" | "加急处理" | "宽松节奏" | 自定义调整
        """
        # 根据用户选择调整
        if user_choice == "加急处理":
            plan.blueprint.compress_timeline()
        elif user_choice == "宽松节奏":
            plan.blueprint.extend_timeline()
        
        # 动态创建角色
        role_mapping = {}
        for role_def in plan.blueprint.required_roles:
            role_id = self.scheduler_api.registry.register(
                role_type=role_def["type"],
                name=role_def["name"],
                capabilities=role_def["capabilities"]
            )
            role_mapping[role_def["name"]] = role_id
        
        # 创建项目
        project = Project(
            id=plan.project_id,
            name=plan.name,
            type=plan.type,
            status="active",
            blueprint=plan.blueprint,
            role_mapping=role_mapping,
            pdca=PDCAState()
        )
        
        # 分解任务并提交到Layer 1
        for task_def in plan.blueprint.tasks:
            role_name = task_def["assigned_role"]
            role_id = role_mapping.get(role_name)
            
            if role_id:
                task_data = {
                    "project_id": project.id,
                    "role_id": role_id,
                    "name": task_def["name"],
                    "description": task_def["description"],
                    "priority": task_def.get("priority", "P2"),
                    "depends_on": [
                        dep_id for dep_id in task_def.get("depends_on", [])
                    ]
                }
                
                result = self.scheduler_api.submit_task(task_data)
                if result["success"]:
                    project.task_ids.append(result["task_id"])
        
        self.projects[project.id] = project
        self._save_projects()
        
        return project
    
    def get_project_status(self, project_id: str) -> ProjectStatus:
        """获取项目状态"""
        project = self.projects.get(project_id)
        if not project:
            return None
        
        # 查询所有任务状态
        task_stats = defaultdict(int)
        for task_id in project.task_ids:
            task = self.scheduler_api.task_queue.tasks.get(task_id)
            if task:
                task_stats[task.status] += 1
        
        return ProjectStatus(
            project_id=project_id,
            name=project.name,
            status=project.status,
            task_summary=dict(task_stats),
            pdca_state=project.pdca,
            next_actions=self._determine_next_actions(project)
        )
    
    def _determine_next_actions(self, project: Project) -> List[str]:
        """确定下一步行动"""
        actions = []
        
        # 检查PDCA状态
        if project.pdca.plan.status != "completed":
            actions.append("规划阶段进行中")
        elif project.pdca.do.status == "in_progress":
            actions.append("执行阶段进行中")
        elif project.pdca.check.status == "pending":
            actions.append("等待验证")
        elif project.pdca.act.status == "pending":
            actions.append("需要用户决策")
        
        # 检查是否有完成的任务需要决策
        completed_tasks = [
            task_id for task_id in project.task_ids
            if self.scheduler_api.task_queue.tasks.get(task_id, Task()).status == "completed"
        ]
        
        if completed_tasks:
            actions.append(f"有 {len(completed_tasks)} 个任务完成，需要用户决策")
        
        return actions
    
    def adjust_project(self, project_id: str, adjustments: Dict) -> Project:
        """
        调整项目
        
        adjustments: {
            "extend_days": 2,  # 延长2天
            "add_role": {...},  # 添加新角色
            "reprioritize": ["task_id_1", "task_id_2"],  # 重新排序
            "pause": True  # 暂停项目
        }
        """
        project = self.projects.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        if adjustments.get("pause"):
            project.status = "paused"
        
        if "extend_days" in adjustments:
            project.blueprint.extend_timeline(adjustments["extend_days"])
        
        # 其他调整逻辑...
        
        self._save_projects()
        return project
    
    def _load_projects(self):
        """加载项目"""
        state_file = "/root/.openclaw/workspace/shared/pipeline/orchestrator_projects.json"
        if os.path.exists(state_file):
            with open(state_file) as f:
                data = json.load(f)
                self.projects = {
                    pid: Project(**pdata) 
                    for pid, pdata in data.get("projects", {}).items()
                }
    
    def _save_projects(self):
        """保存项目"""
        state_file = "/root/.openclaw/workspace/shared/pipeline/orchestrator_projects.json"
        with open(state_file, 'w') as f:
            json.dump({
                "projects": {
                    pid: p.__dict__ for pid, p in self.projects.items()
                },
                "last_updated": datetime.now().isoformat()
            }, f, indent=2, default=str)
```

#### Planner (规划引擎)
```python
class Planner:
    """项目规划引擎"""
    
    def __init__(self, scheduler_api: ResourceSchedulerAPI):
        self.scheduler_api = scheduler_api
        self.role_templates = self._load_role_templates()
    
    def _load_role_templates(self) -> Dict:
        """加载角色模板"""
        return {
            "system_dev": {
                "roles": [
                    {"type": "architect", "name": "系统架构师", "capabilities": ["gap_analysis", "solution_design"]},
                    {"type": "developer", "name": "Skill开发者", "capabilities": ["skill_creation", "code_implementation"]},
                    {"type": "tester", "name": "质量验证员", "capabilities": ["testing", "validation"]}
                ],
                "workflow": ["architect", "developer", "tester"]
            },
            "content_creation": {
                "roles": [
                    {"type": "researcher", "name": "研究员", "capabilities": ["research", "analysis"]},
                    {"type": "creator", "name": "创作者", "capabilities": ["writing", "creation"]},
                    {"type": "editor", "name": "编辑", "capabilities": ["editing", "review"]},
                    {"type": "publisher", "name": "发布员", "capabilities": ["publishing", "distribution"]}
                ],
                "workflow": ["researcher", "creator", "editor", "publisher"]
            },
            "course_design": {
                "roles": [
                    {"type": "course_designer", "name": "课程设计师", "capabilities": ["curriculum_design", "learning_path"]},
                    {"type": "content_developer", "name": "内容开发者", "capabilities": ["content_creation", "material_development"]},
                    {"type": "instructional_validator", "name": "教学验证员", "capabilities": ["instructional_review", "validation"]}
                ],
                "workflow": ["course_designer", "content_developer", "instructional_validator"]
            }
        }
    
    def create_blueprint(self, description: str, project_type: str, user_constraints: Dict = None) -> Blueprint:
        """创建项目蓝图"""
        template = self.role_templates.get(project_type, self.role_templates["system_dev"])
        
        # 解析项目范围
        scope = self._parse_scope(description, project_type)
        
        # 生成任务列表
        tasks = self._generate_tasks(scope, template["workflow"], user_constraints)
        
        return Blueprint(
            name=self._extract_name(description),
            description=description,
            project_type=project_type,
            required_roles=template["roles"],
            workflow=template["workflow"],
            tasks=tasks,
            milestones=self._generate_milestones(tasks)
        )
    
    def _parse_scope(self, description: str, project_type: str) -> Dict:
        """解析项目范围"""
        # 简化版：基于关键词解析
        scope = {"items": [], "complexity": "medium"}
        
        if "GAP" in description:
            # 提取GAP编号
            import re
            gaps = re.findall(r'GAP-?0*(\d+)', description)
            scope["items"] = [f"GAP-{g.zfill(3)}" for g in gaps]
            scope["complexity"] = "high" if len(gaps) > 5 else "medium"
        
        return scope
    
    def _generate_tasks(self, scope: Dict, workflow: List[str], constraints: Dict = None) -> List[Dict]:
        """生成任务列表"""
        tasks = []
        
        for i, item in enumerate(scope["items"]):
            # 为每个项目条目创建完整的workflow任务链
            prev_task_id = None
            
            for j, role_type in enumerate(workflow):
                task_id = f"task_{i}_{j}"
                
                task = {
                    "id": task_id,
                    "name": f"{role_type.capitalize()} - {item}",
                    "description": f"{role_type}处理{item}",
                    "assigned_role": role_type,
                    "priority": "P1" if scope["complexity"] == "high" else "P2",
                    "depends_on": [prev_task_id] if prev_task_id else [],
                    "estimated_duration": 30  # 分钟
                }
                
                tasks.append(task)
                prev_task_id = task_id
        
        return tasks
    
    def _generate_milestones(self, tasks: List[Dict]) -> List[Dict]:
        """生成里程碑"""
        milestones = []
        
        # 按角色分组任务
        by_role = defaultdict(list)
        for task in tasks:
            by_role[task["assigned_role"]].append(task)
        
        for role, role_tasks in by_role.items():
            milestones.append({
                "name": f"完成所有{role}任务",
                "tasks": [t["id"] for t in role_tasks],
                "criteria": f"所有{len(role_tasks)}个{role}任务完成"
            })
        
        return milestones
    
    def _extract_name(self, description: str) -> str:
        """提取项目名称"""
        # 取前20个字符或第一个句号前
        if len(description) > 20:
            return description[:20] + "..."
        return description
```

#### Estimator (时间评估器)
```python
class Estimator:
    """时间评估引擎"""
    
    def __init__(self, scheduler_api: ResourceSchedulerAPI):
        self.scheduler_api = scheduler_api
        self.historical_data = self._load_historical_data()
    
    def _load_historical_data(self) -> Dict:
        """加载历史执行数据"""
        # 从之前的执行记录中学习
        history_file = "/root/.openclaw/workspace/shared/pipeline/execution_history.json"
        if os.path.exists(history_file):
            with open(history_file) as f:
                return json.load(f)
        return {}
    
    def estimate_duration(self, blueprint: Blueprint, resource_status: Dict) -> TimeEstimate:
        """
        评估项目时间
        
        考虑因素:
        1. 任务数量和复杂度
        2. 角色可用性和队列深度
        3. 历史执行效率
        4. 依赖链长度
        """
        total_tasks = len(blueprint.tasks)
        
        # 1. 基础时间估算 (每个任务平均30分钟)
        base_minutes = total_tasks * 30
        
        # 2. 角色队列等待时间
        wait_minutes = 0
        for role_def in blueprint.required_roles:
            role_type = role_def["type"]
            # 找到对应的role_id
            for rid, rstatus in resource_status["roles"].items():
                if rstatus["type"] == role_type:
                    queue_depth = rstatus["queue_depth"]
                    avg_duration = rstatus["metrics"]["avg_duration"]
                    wait_minutes += queue_depth * avg_duration
                    break
        
        # 3. 依赖链开销 (每个依赖链增加10%时间)
        dependency_overhead = 1.0
        max_chain_length = self._calculate_max_chain_length(blueprint.tasks)
        dependency_overhead += max_chain_length * 0.1
        
        # 4. 历史效率调整
        efficiency_factor = self._get_efficiency_factor(blueprint.project_type)
        
        # 总时间
        total_minutes = (base_minutes + wait_minutes) * dependency_overhead / efficiency_factor
        
        # 转换为天数 (假设每天有效工作时间8小时 = 480分钟)
        work_day_minutes = 480
        estimated_days = max(1, int(total_minutes / work_day_minutes) + 1)
        
        return TimeEstimate(
            normal_days=estimated_days,
            optimistic_days=max(1, estimated_days - 1),
            pessimistic_days=estimated_days + 2,
            breakdown={
                "base_execution_hours": base_minutes / 60,
                "wait_hours": wait_minutes / 60,
                "dependency_overhead": f"{dependency_overhead:.1f}x",
                "efficiency_factor": f"{efficiency_factor:.2f}"
            },
            reasoning=[
                f"总共{total_tasks}个任务，基础执行时间{base_minutes/60:.1f}小时",
                f"角色队列等待时间约{wait_minutes/60:.1f}小时",
                f"依赖链最大长度{max_chain_length}，增加{dependency_overhead:.1f}x开销",
                f"历史效率因子{efficiency_factor:.2f}"
            ],
            risks=self._identify_risks(resource_status, estimated_days)
        )
    
    def _calculate_max_chain_length(self, tasks: List[Dict]) -> int:
        """计算最大依赖链长度"""
        # 构建依赖图
        task_map = {t["id"]: t for t in tasks}
        
        def get_chain_length(task_id, visited=None):
            if visited is None:
                visited = set()
            
            if task_id in visited:
                return 0  # 环
            
            visited.add(task_id)
            task = task_map.get(task_id)
            
            if not task or not task.get("depends_on"):
                return 1
            
            max_dep = max(
                get_chain_length(dep_id, visited.copy())
                for dep_id in task["depends_on"]
            )
            
            return max_dep + 1
        
        return max(get_chain_length(t["id"]) for t in tasks) if tasks else 0
    
    def _get_efficiency_factor(self, project_type: str) -> float:
        """获取效率因子"""
        # 基于历史数据
        history = self.historical_data.get(project_type, {})
        success_rate = history.get("success_rate", 0.8)
        return success_rate
    
    def _identify_risks(self, resource_status: Dict, estimated_days: int) -> List[Dict]:
        """识别风险"""
        risks = []
        
        # 检查是否有忙碌角色
        busy_roles = [
            rid for rid, r in resource_status["roles"].items()
            if r["status"] == "busy" and r["queue_depth"] > 2
        ]
        
        if busy_roles:
            risks.append({
                "type": "RESOURCE_OVERLOAD",
                "severity": "medium",
                "description": f"{len(busy_roles)}个角色负载较高",
                "mitigation": "建议错峰启动或增加角色实例"
            })
        
        # 时间风险
        if estimated_days > 7:
            risks.append({
                "type": "LONG_DURATION",
                "severity": "low",
                "description": "项目周期较长，可能受外部因素影响",
                "mitigation": "建议设置检查点，分阶段交付"
            })
        
        return risks
```

### 2.2 数据模型

```python
@dataclass
class Project:
    id: str
    name: str
    type: str
    status: str  # planning, active, paused, completed
    blueprint: 'Blueprint' = None
    role_mapping: Dict[str, str] = None  # role_name -> role_id
    task_ids: List[str] = None
    pdca: 'PDCAState' = None
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.role_mapping is None:
            self.role_mapping = {}
        if self.task_ids is None:
            self.task_ids = []
        if self.pdca is None:
            self.pdca = PDCAState()
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class Blueprint:
    name: str
    description: str
    project_type: str
    required_roles: List[Dict]
    workflow: List[str]
    tasks: List[Dict]
    milestones: List[Dict]
    
    def compress_timeline(self, factor: float = 0.7):
        """压缩时间线"""
        for task in self.tasks:
            task["estimated_duration"] *= factor
    
    def extend_timeline(self, days: int = 2):
        """延长时间线"""
        for task in self.tasks:
            task["estimated_duration"] *= (1 + days * 0.2)

@dataclass
class TimeEstimate:
    normal_days: int
    optimistic_days: int
    pessimistic_days: int
    breakdown: Dict
    reasoning: List[str]
    risks: List[Dict]

@dataclass
class ProjectPlan:
    project_id: str
    name: str
    type: str
    description: str
    blueprint: Blueprint
    time_estimate: TimeEstimate
    resource_status: Dict
    alternatives: List['PlanAlternative']

@dataclass
class PlanAlternative:
    name: str
    duration_days: int
    description: str
    risk_level: str
    confidence: str

@dataclass
class PDCAState:
    plan: 'PDCAStep' = None
    do: 'PDCAStep' = None
    check: 'PDCAStep' = None
    act: 'PDCAStep' = None
    
    def __post_init__(self):
        if self.plan is None:
            self.plan = PDCAStep(name="Plan", status="pending")
        if self.do is None:
            self.do = PDCAStep(name="Do", status="pending")
        if self.check is None:
            self.check = PDCAStep(name="Check", status="pending")
        if self.act is None:
            self.act = PDCAStep(name="Act", status="pending")

@dataclass
class PDCAStep:
    name: str
    status: str  # pending, in_progress, completed
    output: str = ""
    started_at: datetime = None
    completed_at: datetime = None

@dataclass
class ProjectStatus:
    project_id: str
    name: str
    status: str
    task_summary: Dict[str, int]
    pdca_state: PDCAState
    next_actions: List[str]
```

### 2.3 用户交互接口

```python
class UserInterface:
    """用户交互接口"""
    
    def __init__(self, orchestrator: Orchestrator):
        self.orchestrator = orchestrator
    
    def handle_command(self, command: str, **kwargs) -> str:
        """处理用户命令"""
        
        if command.startswith("启动"):
            # 启动新项目
            description = command[2:].strip() or kwargs.get("description", "")
            plan = self.orchestrator.create_project(description)
            
            return self._format_plan_proposal(plan)
        
        elif command.startswith("确认"):
            # 用户确认方案
            plan_id = kwargs.get("plan_id")
            choice = kwargs.get("choice", "正常节奏")
            
            # 找到对应的plan并提交
            # (实际实现需要存储pending plans)
            
            return f"项目已提交，开始执行..."
        
        elif command.startswith("查询"):
            # 查询项目状态
            project_id = kwargs.get("project_id")
            status = self.orchestrator.get_project_status(project_id)
            
            return self._format_status(status)
        
        elif command.startswith("调整"):
            # 调整项目
            project_id = kwargs.get("project_id")
            adjustments = kwargs.get("adjustments", {})
            
            project = self.orchestrator.adjust_project(project_id, adjustments)
            
            return f"项目 {project.name} 已调整"
        
        elif command.startswith("暂停"):
            project_id = kwargs.get("project_id")
            self.orchestrator.adjust_project(project_id, {"pause": True})
            return f"项目 {project_id} 已暂停"
        
        elif command.startswith("恢复"):
            project_id = kwargs.get("project_id")
            self.orchestrator.adjust_project(project_id, {"pause": False})
            return f"项目 {project_id} 已恢复"
        
        elif command.startswith("状态"):
            # 查看所有项目状态
            return self._format_all_projects()
        
        else:
            return f"未知命令: {command}\n可用命令: 启动、确认、查询、调整、暂停、恢复、状态"
    
    def _format_plan_proposal(self, plan: ProjectPlan) -> str:
        """格式化规划建议"""
        lines = [
            f"📋 项目规划建议: {plan.name}",
            f"ID: {plan.project_id}",
            f"",
            f"⏱️ 时间评估:",
            f"  • 预计周期: {plan.time_estimate.normal_days} 天",
            f"  • 乐观估计: {plan.time_estimate.optimistic_days} 天",
            f"  • 保守估计: {plan.time_estimate.pessimistic_days} 天",
            f"",
            f"📊 资源状态:",
        ]
        
        for role_id, status in plan.resource_status.get("roles", {}).items():
            emoji = "🟢" if status["status"] == "idle" else "🟡" if status["queue_depth"] < 3 else "🔴"
            lines.append(f"  {emoji} {status['type']}: {status['status']} (队列:{status['queue_depth']})")
        
        lines.extend([
            f"",
            f"💡 评估理由:",
        ])
        for reason in plan.time_estimate.reasoning:
            lines.append(f"  • {reason}")
        
        if plan.time_estimate.risks:
            lines.extend([
                f"",
                f"⚠️ 风险提示:",
            ])
            for risk in plan.time_estimate.risks:
                lines.append(f"  • [{risk['severity']}] {risk['description']}")
        
        lines.extend([
            f"",
            f"📋 可选方案:",
        ])
        for alt in plan.alternatives:
            lines.append(f"  • {alt.name}: {alt.duration_days}天 ({alt.risk_level}风险, {alt.confidence}置信)")
        
        lines.extend([
            f"",
            f"请回复确认方案:",
            f"  '确认 {plan.project_id} 正常节奏'",
            f"  '确认 {plan.project_id} 加急处理'",
            f"  '确认 {plan.project_id} 宽松节奏'",
        ])
        
        return "\n".join(lines)
    
    def _format_status(self, status: ProjectStatus) -> str:
        """格式化状态报告"""
        if not status:
            return "项目不存在"
        
        lines = [
            f"📊 项目状态: {status.name}",
            f"ID: {status.project_id}",
            f"状态: {status.status}",
            f"",
            f"📈 任务统计:",
        ]
        
        for state, count in status.task_summary.items():
            lines.append(f"  • {state}: {count}")
        
        lines.extend([
            f"",
            f"🔄 PDCA状态:",
            f"  • Plan: {status.pdca_state.plan.status}",
            f"  • Do: {status.pdca_state.do.status}",
            f"  • Check: {status.pdca_state.check.status}",
            f"  • Act: {status.pdca_state.act.status}",
        ])
        
        if status.next_actions:
            lines.extend([
                f"",
                f"➡️ 下一步行动:",
            ])
            for action in status.next_actions:
                lines.append(f"  • {action}")
        
        return "\n".join(lines)
    
    def _format_all_projects(self) -> str:
        """格式化所有项目"""
        if not self.orchestrator.projects:
            return "当前没有活跃项目"
        
        lines = ["📁 所有项目:", ""]
        
        for pid, project in self.orchestrator.projects.items():
            emoji = "🟢" if project.status == "active" else "🟡" if project.status == "paused" else "🔴"
            lines.append(f"{emoji} {project.name} ({pid}) - {project.status}")
        
        return "\n".join(lines)
```

---

## Layer 0: 角色工作器详细设计

### 3.1 基础工作器类

```python
class BaseRoleWorker(ABC):
    """角色工作器基类"""
    
    def __init__(self, role_id: str, scheduler_api: ResourceSchedulerAPI):
        self.role_id = role_id
        self.scheduler_api = scheduler_api
        self.running = False
    
    def start(self):
        """启动工作器"""
        self.running = True
        logger.info(f"Worker {self.role_id} started")
        
        while self.running:
            try:
                self._poll_and_execute()
            except Exception as e:
                logger.error(f"Worker {self.role_id} error: {e}")
                time.sleep(60)  # 出错后等待1分钟
    
    def stop(self):
        """停止工作器"""
        self.running = False
        logger.info(f"Worker {self.role_id} stopped")
    
    def _poll_and_execute(self):
        """轮询并执行任务"""
        # 1. 获取任务
        task_data = self.scheduler_api.poll_task(self.role_id)
        
        if not task_data:
            # 无任务，等待
            time.sleep(60)  # 1分钟后再次轮询
            return
        
        task_id = task_data["task_id"]
        logger.info(f"Worker {self.role_id} got task {task_id}")
        
        # 2. 获取锁
        lock_result = self.scheduler_api.acquire_lock(self.role_id, task_id)
        
        if not lock_result["acquired"]:
            logger.warning(f"Failed to acquire lock for task {task_id}")
            time.sleep(10)
            return
        
        try:
            # 3. 执行任务
            logger.info(f"Executing task {task_id}")
            result = self.execute_task(task_data)
            
            # 4. 完成任务
            success = result.get("success", False)
            self.scheduler_api.complete_task(task_id, success, result)
            
            logger.info(f"Task {task_id} completed: {success}")
            
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            self.scheduler_api.complete_task(
                task_id, 
                False, 
                {"error": str(e), "traceback": traceback.format_exc()}
            )
        finally:
            # 5. 释放锁
            self.scheduler_api.release_lock(self.role_id)
    
    @abstractmethod
    def execute_task(self, task_data: Dict) -> Dict:
        """
        执行任务，子类必须实现
        
        返回: {
            "success": bool,
            "output": str,
            "artifacts": [...],  # 生成的文件等
            "metrics": {...}
        }
        """
        pass
```

### 3.2 具体角色实现

#### ArchitectWorker (架构师)
```python
class ArchitectWorker(BaseRoleWorker):
    """架构师工作器"""
    
    def execute_task(self, task_data: Dict) -> Dict:
        """执行架构设计任务"""
        description = task_data["description"]
        
        # 这里调用实际的架构分析逻辑
        # 可以是调用LLM生成设计文档
        
        result = {
            "success": True,
            "output": f"架构设计完成: {description}",
            "artifacts": [
                f"/shared/pipeline/designs/{task_data['task_id']}_design.md"
            ],
            "metrics": {
                "design_complexity": "medium",
                "components_count": 5
            }
        }
        
        return result
```

#### DeveloperWorker (开发者)
```python
class DeveloperWorker(BaseRoleWorker):
    """开发者工作器"""
    
    def execute_task(self, task_data: Dict) -> Dict:
        """执行开发任务"""
        description = task_data["description"]
        
        # 这里调用实际的开发逻辑
        # 可以是代码生成、skill创建等
        
        result = {
            "success": True,
            "output": f"开发完成: {description}",
            "artifacts": [
                f"/shared/pipeline/skills/{task_data['task_id']}/"
            ],
            "metrics": {
                "lines_of_code": 200,
                "test_coverage": 0.85
            }
        }
        
        return result
```

#### TesterWorker (测试员)
```python
class TesterWorker(BaseRoleWorker):
    """测试员工作器"""
    
    def execute_task(self, task_data: Dict) -> Dict:
        """执行测试任务"""
        description = task_data["description"]
        
        # 这里调用实际的测试逻辑
        # 运行测试、生成报告
        
        result = {
            "success": True,
            "output": f"测试完成: {description}",
            "artifacts": [
                f"/shared/pipeline/reports/{task_data['task_id']}_report.md"
            ],
            "metrics": {
                "tests_passed": 15,
                "tests_failed": 0,
                "coverage": 0.90
            },
            "user_decision_required": True,
            "decision_prompt": "测试通过，是否安装到生产环境？"
        }
        
        return result
```

---

## 开发计划 (高密度4天)

### Day 1: Layer 1 核心
| 时间 | 任务 | 产出 |
|------|------|------|
| 0-4h | RoleRegistry + LockManager | 角色管理 + 文件锁实现 |
| 4-8h | TaskQueue + ConflictDetector | 任务队列 + 冲突检测 |
| 8-10h | PriorityManager + API接口 | 优先级管理 + API封装 |
| 10-12h | 单元测试 | Layer 1 测试覆盖 |

### Day 2: Layer 2 核心
| 时间 | 任务 | 产出 |
|------|------|------|
| 0-4h | Orchestrator + Planner | 规划者主类 + 规划引擎 |
| 4-8h | Estimator + UserInterface | 时间评估 + 用户交互 |
| 8-10h | PDCA管理 + 项目状态 | 状态机 + 状态查询 |
| 10-12h | 集成测试 | Layer 1+2 集成测试 |

### Day 3: 角色工作器 + 集成
| 时间 | 任务 | 产出 |
|------|------|------|
| 0-4h | BaseRoleWorker + ArchitectWorker | 基础工作器 + 架构师 |
| 4-8h | DeveloperWorker + TesterWorker | 开发者 + 测试员 |
| 8-10h | 角色轮询调度 | 工作器启动/停止管理 |
| 10-12h | E2E测试 | 完整流程测试 |

### Day 4: 优化 + GAP迁移准备
| 时间 | 任务 | 产出 |
|------|------|------|
| 0-4h | 性能优化 + 错误处理 | 锁超时优化、故障恢复 |
| 4-8h | 监控/日志 + 文档 | 运维工具 + 使用文档 |
| 8-10h | GAP-002~006迁移准备 | 迁移脚本 + 任务创建 |
| 10-12h | 最终测试 + 上线 | 生产环境部署 |

---

## GAP-002~006 迁移计划

### 迁移内容
将未完成的 GAP-002 到 GAP-006 迁移到新框架：

| GAP | 名称 | 状态 | 迁移方式 |
|-----|------|------|----------|
| GAP-001 | openclaw-version-adapter | ✅ 已完成 | 已完成，无需迁移 |
| GAP-002 | skill-factory | ⏳ 待开发 | 创建新项目，自动分配角色 |
| GAP-003 | feishu-context-manager | ⏳ 待开发 | 创建新项目，自动分配角色 |
| GAP-004 | config-validator | ⏳ 待开发 | 创建新项目，自动分配角色 |
| GAP-005 | git-push-recovery | ⏳ 待开发 | 创建新项目，自动分配角色 |
| GAP-006 | skill-market-metadata | ⏳ 待开发 | 创建新项目，自动分配角色 |
| GAP-007 | auto-error-logger | ✅ 已完成 | 已完成，无需迁移 |

### 迁移步骤
1. **系统自动创建项目**:
   ```
   项目ID: PROJ-20260315-GAP-MIGRATION
   名称: GAP-002到006批量迁移
   类型: system_dev
   ```

2. **自动分解任务**:
   - 每个GAP创建完整的架构→开发→测试任务链
   - 共 5个GAP × 3个角色 = 15个任务

3. **自动提交到Layer 1**:
   - 任务进入各角色队列
   - 按依赖关系自动调度执行

4. **用户只需决策**:
   - 每个GAP测试完成后，通知用户"是否安装"
   - 用户回复后，继续下一个

---

## 附录A: 测试钩子设计

### A.1 设计目标
支持测试员评估报告中提出的测试需求：
- 状态驱动测试
- 故障注入
- 契约测试
- 并发测试

### A.2 测试钩子接口

```python
# shared/test_hooks.py

class TestHooks:
    """测试钩子系统，用于测试时注入控制点"""
    
    def __init__(self):
        self.enabled = False
        self.hooks = defaultdict(list)
    
    def enable(self):
        """启用测试模式"""
        self.enabled = True
        logger.info("Test hooks enabled")
    
    def disable(self):
        """禁用测试模式"""
        self.enabled = False
        logger.info("Test hooks disabled")
    
    def register(self, hook_point: str, callback: Callable):
        """注册钩子回调"""
        self.hooks[hook_point].append(callback)
    
    def trigger(self, hook_point: str, context: Dict = None) -> Dict:
        """触发钩子，返回可能被修改的context"""
        if not self.enabled:
            return context or {}
        
        context = context or {}
        for callback in self.hooks.get(hook_point, []):
            try:
                result = callback(context)
                if result:
                    context.update(result)
            except Exception as e:
                logger.error(f"Hook {hook_point} error: {e}")
        
        return context

# 全局测试钩子实例
test_hooks = TestHooks()
```

### A.3 Layer 1 测试钩子点

```python
# layer1/lock_manager.py

class LockManager:
    def acquire(self, role_id: str, task_id: str, timeout_ms: int = None) -> bool:
        # 测试钩子: 锁获取前
        test_hooks.trigger("lock:before_acquire", {
            "role_id": role_id,
            "task_id": task_id,
            "timeout_ms": timeout_ms
        })
        
        # ... 原有逻辑 ...
        
        # 测试钩子: 锁获取后
        test_hooks.trigger("lock:after_acquire", {
            "role_id": role_id,
            "task_id": task_id,
            "acquired": acquired
        })
        
        return acquired
    
    def release(self, role_id: str) -> bool:
        # 测试钩子: 锁释放前
        test_hooks.trigger("lock:before_release", {
            "role_id": role_id
        })
        
        # ... 原有逻辑 ...
        
        # 测试钩子: 锁释放后
        test_hooks.trigger("lock:after_release", {
            "role_id": role_id,
            "released": released
        })
        
        return released
```

### A.4 Layer 2 测试钩子点

```python
# layer2/orchestrator.py

class Orchestrator:
    def create_project(self, description: str, user_constraints: Dict = None):
        # 测试钩子: 项目创建前
        test_hooks.trigger("orchestrator:before_create", {
            "description": description,
            "constraints": user_constraints
        })
        
        # ... 原有逻辑 ...
        
        # 测试钩子: 项目创建后
        test_hooks.trigger("orchestrator:after_create", {
            "plan": plan.__dict__
        })
        
        return plan
```

### A.5 故障注入钩子

```python
# shared/fault_injection.py

class FaultInjector:
    """故障注入器，用于测试容错能力"""
    
    def __init__(self):
        self.faults = {}
    
    def inject(self, fault_type: str, target: str, probability: float = 1.0):
        """
        注入故障
        
        fault_type: crash, delay, error, corruption
        target: 目标组件
        probability: 触发概率 (0-1)
        """
        self.faults[target] = {
            "type": fault_type,
            "probability": probability
        }
    
    def maybe_trigger(self, target: str) -> Optional[Dict]:
        """可能触发故障"""
        if target not in self.faults:
            return None
        
        fault = self.faults[target]
        if random.random() > fault["probability"]:
            return None
        
        if fault["type"] == "crash":
            raise RuntimeError(f"Injected crash at {target}")
        elif fault["type"] == "delay":
            time.sleep(5)  # 延迟5秒
            return {"type": "delay", "duration": 5}
        elif fault["type"] == "error":
            return {"type": "error", "message": f"Injected error at {target}"}
        elif fault["type"] == "corruption":
            return {"type": "corruption", "data": "garbage"}
        
        return None

# 注册到测试钩子
def setup_fault_injection():
    injector = FaultInjector()
    
    # 示例: 注入Layer1崩溃故障
    test_hooks.register("lock:before_acquire", lambda ctx: 
        injector.maybe_trigger("lock_manager")
    )
    
    return injector
```

### A.6 测试API

```python
# tests/api.py

class TestAPI:
    """提供给测试的专用API"""
    
    def __init__(self, scheduler_api: ResourceSchedulerAPI):
        self.scheduler_api = scheduler_api
    
    def freeze_time(self):
        """冻结时间，用于测试时间相关逻辑"""
        test_hooks.register("time:get_now", lambda ctx: {
            "frozen_at": ctx.get("frozen_time", datetime.now())
        })
    
    def accelerate_time(self, factor: int = 100):
        """加速时间流逝"""
        self.time_acceleration = factor
    
    def get_state_snapshot(self) -> Dict:
        """获取完整状态快照"""
        return {
            "layer1": self.scheduler_api.registry.get_status(),
            "locks": self.scheduler_api.lock_manager.get_all_locks(),
            "tasks": self.scheduler_api.task_queue.get_statistics(),
            "timestamp": datetime.now().isoformat()
        }
    
    def restore_state(self, snapshot: Dict):
        """恢复到指定状态"""
        # 恢复Layer1状态
        with open(self.scheduler_api.registry.state_file, 'w') as f:
            json.dump(snapshot["layer1"], f)
        
        # 重新加载
        self.scheduler_api.registry._load()
    
    def simulate_role_busy(self, role_id: str, duration_minutes: int):
        """模拟角色忙碌状态"""
        # 创建虚拟任务
        fake_task = Task(
            id=f"fake_{uuid4().hex[:8]}",
            role_id=role_id,
            name="模拟任务",
            status="processing"
        )
        
        # 获取锁
        self.scheduler_api.lock_manager.acquire(role_id, fake_task.id)
        
        # 设置自动释放
        def release_after():
            time.sleep(duration_minutes * 60)
            self.scheduler_api.lock_manager.release(role_id)
        
        threading.Thread(target=release_after, daemon=True).start()
```

---

## 附录B: 固定角色模板机制

### B.1 设计目标
当规划者遇到新的主题任务类型时：
1. 识别为新类型
2. 暂停自动创建临时角色
3. 通过主对话与用户沟通
4. 用户确认后创建**固定角色模板**（可复用，经验沉淀）
5. 后续同类任务自动使用此模板

### B.2 固定角色 vs 临时角色

| 特性 | 固定角色模板 | 临时角色 |
|------|-------------|----------|
| 生命周期 | 长期存在，可复用 | 随项目创建和销毁 |
| 经验沉淀 | ✅ 积累历史数据 | ❌ 项目结束即清除 |
| 配置优化 | ✅ 可根据历史优化 | ❌ 每次重新配置 |
| 创建方式 | 用户通过主会话确认 | 规划者自动创建 |
| 适用场景 | 高频重复任务类型 | 一次性特殊项目 |

### B.3 固定角色模板管理

```python
# layer2/fixed_role_templates.py

class FixedRoleTemplateManager:
    """
    固定角色模板管理器
    
    管理所有已沉淀的固定角色模板
    新任务类型首次出现时，需要用户确认创建
    """
    
    TEMPLATES_FILE = "/root/.openclaw/workspace/shared/pipeline/fixed_role_templates.json"
    
    def __init__(self):
        self.templates: Dict[str, RoleTemplate] = {}
        self.pending_approvals: Dict[str, NewTypeRequest] = {}
        self._load_templates()
    
    def _load_templates(self):
        """加载已存在的模板"""
        if os.path.exists(self.TEMPLATES_FILE):
            with open(self.TEMPLATES_FILE) as f:
                data = json.load(f)
                for type_id, tdata in data.get("templates", {}).items():
                    self.templates[type_id] = RoleTemplate(**tdata)
    
    def _save_templates(self):
        """保存模板"""
        with open(self.TEMPLATES_FILE, 'w') as f:
            json.dump({
                "templates": {
                    tid: t.__dict__ for tid, t in self.templates.items()
                },
                "last_updated": datetime.now().isoformat()
            }, f, indent=2, default=str)
    
    def check_type_exists(self, project_type: str) -> bool:
        """检查任务类型是否已有固定模板"""
        return project_type in self.templates
    
    def get_template(self, project_type: str) -> Optional[RoleTemplate]:
        """获取固定角色模板"""
        return self.templates.get(project_type)
    
    def request_new_type_approval(self, project_type: str, description: str, 
                                   proposed_roles: List[Dict]) -> str:
        """
        请求用户批准新任务类型的固定角色模板
        
        返回: request_id，用户需要通过主会话回复确认
        """
        request_id = f"REQ_{datetime.now().strftime('%Y%m%d')}_{uuid4().hex[:4]}"
        
        request = NewTypeRequest(
            id=request_id,
            project_type=project_type,
            description=description,
            proposed_roles=proposed_roles,
            status="pending_user_approval",
            created_at=datetime.now()
        )
        
        self.pending_approvals[request_id] = request
        
        # 生成用户确认消息
        message = self._generate_approval_message(request)
        
        # 这里通过主会话发送给用户
        return request_id, message
    
    def _generate_approval_message(self, request: NewTypeRequest) -> str:
        """生成用户确认消息"""
        lines = [
            f"🆕 发现新的任务类型，需要创建固定角色模板",
            f"",
            f"类型ID: {request.project_type}",
            f"任务描述: {request.description}",
            f"",
            f"📋 建议的角色配置:",
        ]
        
        for i, role in enumerate(request.proposed_roles, 1):
            lines.append(f"  {i}. {role['name']} ({role['type']})")
            lines.append(f"     能力: {', '.join(role['capabilities'])}")
        
        lines.extend([
            f"",
            f"❓ 请确认以下选项:",
            f"  A. 确认创建 - 使用建议配置创建固定角色模板",
            f"  B. 修改后创建 - 告诉我需要调整的角色或能力",
            f"  C. 仅本次使用 - 不创建固定模板，本次临时创建角色",
            f"  D. 取消 - 暂不处理此类型任务",
            f"",
            f"回复格式: '确认 [request_id] A' 或 '确认 [request_id] B: 调整内容'",
        ])
        
        return "\n".join(lines)
    
    def approve_new_type(self, request_id: str, choice: str, 
                         modifications: Dict = None) -> Optional[RoleTemplate]:
        """
        用户确认新类型
        
        choice: A/B/C/D
        modifications: 当choice为B时的修改内容
        """
        request = self.pending_approvals.get(request_id)
        if not request:
            raise ValueError(f"Request {request_id} not found")
        
        if choice == "D":  # 取消
            request.status = "cancelled"
            return None
        
        if choice == "C":  # 仅本次使用
            request.status = "temporary_only"
            return None
        
        # A 或 B: 创建固定模板
        roles = request.proposed_roles
        if choice == "B" and modifications:
            # 应用用户修改
            roles = self._apply_modifications(roles, modifications)
        
        # 创建模板
        template = RoleTemplate(
            type_id=request.project_type,
            name=self._generate_type_name(request.project_type),
            description=request.description,
            roles=roles,
            workflow=[r["type"] for r in roles],
            created_at=datetime.now(),
            usage_count=0,
            performance_history=[]
        )
        
        # 保存模板
        self.templates[request.project_type] = template
        self._save_templates()
        
        request.status = "approved"
        
        return template
    
    def update_template_performance(self, project_type: str, 
                                     execution_data: Dict):
        """
        更新模板性能历史
        用于持续优化固定角色配置
        """
        template = self.templates.get(project_type)
        if not template:
            return
        
        template.usage_count += 1
        template.performance_history.append({
            "timestamp": datetime.now().isoformat(),
            "actual_duration": execution_data.get("duration"),
            "success": execution_data.get("success"),
            "quality_score": execution_data.get("quality_score")
        })
        
        # 保留最近50条记录
        template.performance_history = template.performance_history[-50:]
        
        self._save_templates()
    
    def suggest_template_optimization(self, project_type: str) -> List[Dict]:
        """
        基于历史数据建议模板优化
        """
        template = self.templates.get(project_type)
        if not template or len(template.performance_history) < 5:
            return []
        
        suggestions = []
        
        # 分析成功率
        recent = template.performance_history[-10:]
        success_rate = sum(1 for h in recent if h["success"]) / len(recent)
        
        if success_rate < 0.8:
            suggestions.append({
                "type": "add_tester",
                "reason": f"近期成功率{success_rate:.1%}，建议增加测试环节",
                "action": "在workflow中添加tester角色"
            })
        
        # 分析平均耗时
        avg_duration = sum(h["actual_duration"] for h in recent) / len(recent)
        estimated = self._get_template_estimated_duration(template)
        
        if avg_duration > estimated * 1.5:
            suggestions.append({
                "type": "extend_time",
                "reason": f"实际耗时({avg_duration:.0f}m)远超估计({estimated:.0f}m)",
                "action": "调整时间估算参数"
            })
        
        return suggestions
    
    def _generate_type_name(self, type_id: str) -> str:
        """生成类型显示名称"""
        name_map = {
            "system_dev": "系统开发",
            "content_creation": "内容创作",
            "course_design": "课程设计",
            "data_analysis": "数据分析"
        }
        return name_map.get(type_id, type_id.replace("_", " ").title())
    
    def _apply_modifications(self, roles: List[Dict], modifications: Dict) -> List[Dict]:
        """应用用户修改"""
        # 实现修改逻辑
        return roles
    
    def _get_template_estimated_duration(self, template: RoleTemplate) -> float:
        """获取模板估计耗时"""
        # 基于角色数量和配置计算
        return len(template.roles) * 30  # 每个角色30分钟


@dataclass
class RoleTemplate:
    """固定角色模板"""
    type_id: str
    name: str
    description: str
    roles: List[Dict]  # 角色定义列表
    workflow: List[str]  # 角色执行顺序
    created_at: datetime
    usage_count: int = 0
    performance_history: List[Dict] = None
    
    def __post_init__(self):
        if self.performance_history is None:
            self.performance_history = []


@dataclass
class NewTypeRequest:
    """新类型请求"""
    id: str
    project_type: str
    description: str
    proposed_roles: List[Dict]
    status: str  # pending_user_approval, approved, temporary_only, cancelled
    created_at: datetime
```

### B.4 Planner集成

```python
# layer2/planner.py

class Planner:
    def __init__(self, scheduler_api: ResourceSchedulerAPI):
        self.scheduler_api = scheduler_api
        self.fixed_templates = FixedRoleTemplateManager()
    
    def create_blueprint(self, description: str, project_type: str, 
                         user_constraints: Dict = None) -> Union[Blueprint, Tuple[str, str]]:
        """
        创建项目蓝图
        
        返回:
        - Blueprint: 已有固定模板，直接返回蓝图
        - (request_id, message): 新类型，需要用户确认
        """
        # 检查是否有固定模板
        if self.fixed_templates.check_type_exists(project_type):
            # 使用固定模板
            template = self.fixed_templates.get_template(project_type)
            return self._create_blueprint_from_template(
                description, project_type, template, user_constraints
            )
        
        # 新类型，生成建议并请求用户确认
        proposed_roles = self._infer_roles_for_type(project_type, description)
        
        request_id, message = self.fixed_templates.request_new_type_approval(
            project_type=project_type,
            description=description,
            proposed_roles=proposed_roles
        )
        
        return request_id, message
    
    def _create_blueprint_from_template(self, description: str, 
                                        project_type: str,
                                        template: RoleTemplate,
                                        user_constraints: Dict) -> Blueprint:
        """基于固定模板创建蓝图"""
        # 使用模板中的角色定义
        # ... 创建蓝图逻辑 ...
        pass
    
    def _infer_roles_for_type(self, project_type: str, description: str) -> List[Dict]:
        """推断新类型需要的角色"""
        # 基于描述和类型推断角色
        # 返回建议的角色列表
        pass
```

### B.5 用户交互流程

```
用户: "启动项目：设计一个市场调研报告"

规划者识别:
- 类型: market_research (新类型，无固定模板)
- 推断角色: 研究员、分析师、报告撰写员

规划者暂停，发送确认消息:
━━━━━━━━━━━━━━━━━━━━━━━━━━
🆕 发现新的任务类型，需要创建固定角色模板

类型ID: market_research
任务描述: 设计一个市场调研报告

📋 建议的角色配置:
  1. 市场研究员 (researcher)
     能力: data_collection, survey_design
  2. 数据分析师 (analyst)
     能力: statistical_analysis, insight_extraction
  3. 报告撰写员 (writer)
     能力: report_writing, visualization

❓ 请确认以下选项:
  A. 确认创建 - 使用建议配置创建固定角色模板
  B. 修改后创建 - 告诉我需要调整的角色或能力
  C. 仅本次使用 - 不创建固定模板，本次临时创建角色
  D. 取消 - 暂不处理此类型任务

回复格式: '确认 REQ_20260315_XXXX A'
━━━━━━━━━━━━━━━━━━━━━━━━━━

用户: "确认 REQ_20260315_XXXX B: 增加可视化设计师角色"

规划者:
- 应用修改
- 创建固定模板 (market_research + 4个角色)
- 继续创建项目蓝图
- 后续所有市场调研任务自动使用此模板
```

---

## 两个问题的回答总结

### 1. 测试钩子 ✅ 已处理
- **文件**: `shared/test_hooks.py`
- **功能**: 
  - 测试钩子注册/触发机制
  - Layer 1/2 关键点的钩子注入
  - 故障注入器 (crash/delay/error/corruption)
  - 专用测试API (freeze_time, state_snapshot, simulate_role_busy)

### 2. 固定角色模板机制 ✅ 已设计
- **文件**: `layer2/fixed_role_templates.py`
- **机制**:
  - 新类型自动识别并暂停
  - 通过主会话请求用户确认
  - 用户可选择: 确认/修改/仅本次使用/取消
  - 固定模板长期存在，可复用，积累历史数据
  - 自动性能分析和优化建议

---

**请确认这两个补充设计后，决策是否启动开发。**

### 代码文件
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
│   └── user_interface.py
├── workers/
│   ├── __init__.py
│   ├── base.py
│   ├── architect.py
│   ├── developer.py
│   └── tester.py
├── shared/
│   ├── models.py
│   └── utils.py
├── cli.py  # 命令行入口
└── scheduler_daemon.py  # 调度守护进程
```

### 状态文件
```
/shared/pipeline/
├── state/
│   ├── layer1_state.json      # Layer 1 状态
│   ├── task_queue.json        # 任务队列
│   ├── orchestrator_state.json # 规划者状态
│   └── execution_history.json  # 执行历史
└── locks/                      # 锁文件目录
    ├── arch_xxxxxx.lock
    ├── dev_xxxxxx.lock
    └── test_xxxxxx.lock
```

---

## 确认清单

请确认以下事项：

- [ ] **完整版开发** (4天高密度)
- [ ] **文件锁机制** (后续可升级Redis)
- [ ] **开发顺序**: Layer1 → Layer2 → Workers
- [ ] **上线后立即迁移GAP-002~006**

**确认后请回复"确认进入开发阶段"，我将开始Day 1开发。**
