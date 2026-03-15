"""
Orchestrator (编排器)
项目生命周期管理、用户交互主入口
"""
import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from shared.models import Task, Role, Conflict
from layer1.api import ResourceSchedulerAPI
from layer2.planner import Planner, Blueprint
from layer2.estimator import Estimator

logger = logging.getLogger(__name__)


class ProjectStatus(Enum):
    """项目状态"""
    DRAFT = "draft"           # 草稿，规划中
    PLANNING = "planning"     # 规划中，等待用户确认
    RUNNING = "running"       # 运行中
    PAUSED = "paused"         # 暂停
    CHECKING = "checking"     # 检查阶段 (PDCA Check)
    DECIDING = "deciding"     # 决策阶段 (PDCA Act)
    COMPLETED = "completed"   # 已完成
    CANCELLED = "cancelled"   # 已取消


class UserDecision(Enum):
    """用户决策选项"""
    CONTINUE = "continue"     # 继续 (忽略小问题，下一轮PDCA)
    ADJUST = "adjust"         # 调整 (修复问题后重新Check)
    COMPLETE = "complete"     # 完成 (标记项目完成)
    PAUSE = "pause"           # 暂停 (等待后续决策)


class Project:
    """项目实体"""
    def __init__(self, project_id: str, name: str, description: str):
        self.id = project_id
        self.name = name
        self.description = description
        self.status = ProjectStatus.DRAFT
        self.blueprint: Optional[Blueprint] = None
        self.tasks: List[str] = []          # 任务ID列表
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.completed_at: Optional[datetime] = None
        self.pdca_cycle = 0                 # PDCA循环次数
        self.decision_history: List[Dict] = []  # 决策历史
        self.metadata: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict:
        """序列化为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "blueprint": self.blueprint.to_dict() if self.blueprint else None,
            "tasks": self.tasks,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "pdca_cycle": self.pdca_cycle,
            "decision_history": self.decision_history,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Project":
        """从字典反序列化"""
        project = cls(data["id"], data["name"], data["description"])
        project.status = ProjectStatus(data["status"])
        if data.get("blueprint"):
            project.blueprint = Blueprint.from_dict(data["blueprint"])
        project.tasks = data.get("tasks", [])
        project.created_at = datetime.fromisoformat(data["created_at"])
        project.updated_at = datetime.fromisoformat(data["updated_at"])
        if data.get("completed_at"):
            project.completed_at = datetime.fromisoformat(data["completed_at"])
        project.pdca_cycle = data.get("pdca_cycle", 0)
        project.decision_history = data.get("decision_history", [])
        project.metadata = data.get("metadata", {})
        return project


class Orchestrator:
    """
    编排器 - Layer 2 核心
    
    职责:
    1. 项目生命周期管理
    2. 用户交互协调
    3. PDCA循环驱动
    4. 状态监控和决策触发
    """
    
    def __init__(self, 
                 layer1_api: ResourceSchedulerAPI,
                 state_dir: str = "./state",
                 planner: Optional[Planner] = None,
                 estimator: Optional[Estimator] = None):
        """
        初始化编排器
        
        Args:
            layer1_api: Layer 1 API 实例
            state_dir: 状态文件存储目录
            planner: 规划器实例（可选，默认创建）
            estimator: 估算器实例（可选，默认创建）
        """
        self.layer1 = layer1_api
        self.state_dir = state_dir
        self.projects: Dict[str, Project] = {}
        
        # 子组件
        self.planner = planner or Planner(layer1_api)
        self.estimator = estimator or Estimator(layer1_api)
        
        # 确保状态目录存在
        os.makedirs(state_dir, exist_ok=True)
        self.projects_file = os.path.join(state_dir, "projects.json")
        
        # 初始化固定角色
        self._initialize_fixed_roles()
        
        # 加载已有项目
        self._load_projects()
    
    def _initialize_fixed_roles(self):
        """初始化固定角色（architect, developer, tester等）"""
        # 定义固定角色配置
        fixed_roles = {
            "architect": {
                "name": "架构师",
                "capabilities": ["architecture", "design", "tech_selection", "planning", "api_design"]
            },
            "developer": {
                "name": "开发者", 
                "capabilities": ["coding", "implementation", "debugging", "skill_development"]
            },
            "tester": {
                "name": "测试员",
                "capabilities": ["testing", "validation", "quality_assurance", "test_automation"]
            },
            "analyst": {
                "name": "分析师",
                "capabilities": ["analysis", "requirements", "research"]
            },
            "auditor": {
                "name": "代码审计员",
                "capabilities": ["security_audit", "code_review", "vulnerability_detection"]
            }
        }
        
        # 注册所有固定角色
        for role_id, config in fixed_roles.items():
            self.layer1.registry.register(
                role_type=role_id,
                name=config["name"],
                capabilities=config["capabilities"]
            )
        
        logger.info(f"Initialized {len(fixed_roles)} fixed roles")
    
    def _load_projects(self):
        """从文件加载项目状态"""
        if os.path.exists(self.projects_file):
            try:
                with open(self.projects_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for pid, pdata in data.items():
                        self.projects[pid] = Project.from_dict(pdata)
                logger.info(f"Loaded {len(self.projects)} projects from {self.projects_file}")
            except Exception as e:
                logger.error(f"Failed to load projects: {e}")
    
    def _save_projects(self):
        """保存项目状态到文件"""
        try:
            data = {pid: p.to_dict() for pid, p in self.projects.items()}
            with open(self.projects_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save projects: {e}")
    
    def create_project(self, description: str, name: Optional[str] = None) -> Tuple[Project, str]:
        """
        创建新项目
        
        Args:
            description: 项目描述
            name: 项目名称（可选，自动生成）
            
        Returns:
            (项目对象, 用户确认消息)
        """
        # 生成项目ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_id = f"PROJ_{timestamp}_{hash(description) % 10000:04d}"
        
        # 自动生成名称
        if not name:
            # 提取描述前20字符作为名称
            name = description[:30] + "..." if len(description) > 30 else description
        
        # 创建项目
        project = Project(project_id, name, description)
        self.projects[project_id] = project
        
        # 进入规划阶段
        project.status = ProjectStatus.PLANNING
        
        # 生成蓝图
        blueprint = self.planner.create_blueprint(description)
        project.blueprint = blueprint
        
        # 估算时间
        estimate = self.estimator.estimate_project(blueprint)
        blueprint.estimated_duration = estimate["total_hours"]
        blueprint.estimated_roles = estimate["roles"]
        
        # 生成用户确认消息
        message = self._format_planning_message(project, estimate)
        
        self._save_projects()
        
        logger.info(f"Created project {project_id}: {name}")
        return project, message
    
    def _format_planning_message(self, project: Project, estimate: Dict) -> str:
        """格式化规划确认消息"""
        lines = [
            f"📋 项目规划完成: {project.name}",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"",
            f"📝 项目描述: {project.description[:100]}...",
            f"",
            f"🎯 任务分解 ({len(project.blueprint.tasks)} 个任务):"
        ]
        
        for i, task in enumerate(project.blueprint.tasks[:10], 1):
            role = task.role if hasattr(task, 'role') else task.get("role", "unknown")
            name = task.name if hasattr(task, 'name') else task.get("name", "unnamed")
            lines.append(f"   {i}. [{role}] {name}")
        
        if len(project.blueprint.tasks) > 10:
            lines.append(f"   ... 还有 {len(project.blueprint.tasks) - 10} 个任务")
        
        lines.extend([
            f"",
            f"⏱️  时间估算:",
            f"   预计总工时: {estimate['total_hours']:.1f} 小时",
            f"   预计完成: {estimate['estimated_completion']}",
            f"",
            f"👥 所需角色: {', '.join(estimate['roles'])}",
            f"",
            f"❓ 请选择执行方案:",
            f"   [A] 正常执行 - 按估算时间推进",
            f"   [B] 加急处理 - 提高优先级，压缩工期",
            f"   [C] 宽松安排 - 降低优先级，灵活调度",
            f"   [D] 取消 - 暂不启动",
            f"",
            f"💬 确认格式: 确认 {project.id} [A/B/C/D]"
        ])
        
        return "\n".join(lines)
    
    def confirm_project(self, project_id: str, choice: str) -> Tuple[bool, str]:
        """
        用户确认项目方案
        
        Args:
            project_id: 项目ID
            choice: 用户选择 (A/B/C/D)
            
        Returns:
            (是否成功, 消息)
        """
        project = self.projects.get(project_id)
        if not project:
            return False, f"❌ 项目不存在: {project_id}"
        
        if project.status != ProjectStatus.PLANNING:
            return False, f"❌ 项目状态错误: {project.status.value}"
        
        choice = choice.upper()
        
        if choice == "D":
            # 取消项目
            project.status = ProjectStatus.CANCELLED
            self._save_projects()
            return True, f"✅ 项目已取消: {project.name}"
        
        # A/B/C 都是启动项目，只是优先级不同
        priority_map = {
            "A": "normal",      # 正常
            "B": "urgent",      # 加急
            "C": "relaxed"      # 宽松
        }
        
        priority_mode = priority_map.get(choice, "normal")
        
        # 提交任务到 Layer 1
        task_ids = self._submit_tasks_to_layer1(project, priority_mode)
        project.tasks = task_ids
        
        # 更新状态
        project.status = ProjectStatus.RUNNING
        project.updated_at = datetime.now()
        
        # 记录决策
        project.decision_history.append({
            "phase": "planning",
            "decision": choice,
            "timestamp": datetime.now().isoformat()
        })
        
        self._save_projects()
        
        logger.info(f"Project {project_id} started with mode {priority_mode}")
        
        return True, self._format_start_message(project, task_ids)
    
    def _submit_tasks_to_layer1(self, project: Project, priority_mode: str) -> List[str]:
        """提交任务到 Layer 1"""
        task_ids = []
        
        # 优先级映射
        priority_map = {
            "urgent": {"base": "P0", "boost": 100},
            "normal": {"base": "P1", "boost": 50},
            "relaxed": {"base": "P2", "boost": 0}
        }
        
        mode = priority_map.get(priority_mode, priority_map["normal"])
        
        for task_def in project.blueprint.tasks:
            # 注册角色（如果不存在）
            role_type = task_def.role
            role_id = self._ensure_role_exists(role_type)
            
            # 构建任务数据
            task_data = {
                "project_id": project.id,
                "role_id": role_id,
                "name": task_def.name,
                "description": task_def.description,
                "priority": mode["base"],
                "depends_on": task_def.depends_on,
                "metadata": {
                    "pdca_phase": task_def.pdca_phase,
                    "original_priority": mode["base"]
                }
            }
            
            # 提交任务
            result = self.layer1.submit_task(task_data)
            task_ids.append(result["task_id"])
        
        return task_ids
    
    def _ensure_role_exists(self, role_type: str) -> str:
        """
        确保角色存在，返回角色ID
        
        由于角色是固定的，直接返回role_type作为ID
        如果角色未注册，会自动创建
        """
        # 检查角色是否已注册
        role = self.layer1.registry.get(role_type)
        if role:
            return role_type
        
        # 如果未注册，创建角色（这种情况不应该发生，因为初始化时已创建）
        role_names = {
            "architect": "架构师",
            "developer": "开发者",
            "tester": "测试员",
            "analyst": "分析师",
            "auditor": "代码审计员",
            "planner": "规划师"
        }
        
        capabilities_map = {
            "architect": ["design", "architecture", "planning"],
            "developer": ["coding", "implementation", "debugging"],
            "tester": ["testing", "validation", "quality_assurance"],
            "analyst": ["analysis", "requirements", "research"],
            "auditor": ["security_audit", "code_review"],
            "planner": ["planning", "coordination"]
        }
        
        name = role_names.get(role_type, role_type.capitalize())
        caps = capabilities_map.get(role_type, ["general"])
        
        return self.layer1.registry.register(role_type, name, caps)
    
    def _format_start_message(self, project: Project, task_ids: List[str]) -> str:
        """格式化启动消息"""
        lines = [
            f"🚀 项目已启动: {project.name}",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"",
            f"📋 项目ID: {project.id}",
            f"📝 任务数: {len(task_ids)}",
            f"⏱️  预计工时: {project.blueprint.estimated_duration:.1f} 小时",
            f"",
            f"✅ 所有任务已提交到调度系统",
            f"🔄 工作器将自动获取并执行任务",
            f"",
            f"💡 常用命令:",
            f"   查询 {project.id}  - 查看项目状态",
            f"   状态              - 查看所有项目"
        ]
        return "\n".join(lines)
    
    def check_project_status(self, project_id: str) -> Optional[str]:
        """
        查询项目状态
        
        Args:
            project_id: 项目ID
            
        Returns:
            格式化状态消息
        """
        project = self.projects.get(project_id)
        if not project:
            return None
        
        # 获取任务状态
        task_statuses = {}
        for tid in project.tasks:
            status = self.layer1.get_task_status(tid)
            if status:
                task_statuses[tid] = status
        
        # 统计
        status_counts = {"pending": 0, "processing": 0, "completed": 0, "failed": 0}
        for status in task_statuses.values():
            status_counts[status["status"]] = status_counts.get(status["status"], 0) + 1
        
        # 计算进度
        total = len(project.tasks)
        completed = status_counts.get("completed", 0) + status_counts.get("failed", 0)
        progress = (completed / total * 100) if total > 0 else 0
        
        lines = [
            f"📊 项目状态: {project.name}",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"",
            f"📋 项目ID: {project.id}",
            f"🔄 当前状态: {self._status_emoji(project.status)} {project.status.value}",
            f"📅 创建时间: {project.created_at.strftime('%Y-%m-%d %H:%M')}",
            f"",
            f"📈 进度: {progress:.1f}% ({completed}/{total})",
            f"   ✅ 已完成: {status_counts.get('completed', 0)}",
            f"   🔄 进行中: {status_counts.get('processing', 0)}",
            f"   ⏳ 待执行: {status_counts.get('pending', 0)}",
            f"   ❌ 失败: {status_counts.get('failed', 0)}",
            f"",
            f"🔄 PDCA循环: 第 {project.pdca_cycle} 轮"
        ]
        
        # 显示最近任务
        if task_statuses:
            lines.append(f"")
            lines.append(f"📋 最近任务:")
            for tid, status in list(task_statuses.items())[:5]:
                emoji = {"completed": "✅", "processing": "🔄", "pending": "⏳", "failed": "❌"}.get(status["status"], "⭕")
                name = status.get("name", tid[:12])
                lines.append(f"   {emoji} {name}")
        
        return "\n".join(lines)
    
    def _status_emoji(self, status: ProjectStatus) -> str:
        """状态表情"""
        return {
            ProjectStatus.DRAFT: "📝",
            ProjectStatus.PLANNING: "📋",
            ProjectStatus.RUNNING: "🔄",
            ProjectStatus.PAUSED: "⏸️",
            ProjectStatus.CHECKING: "🧪",
            ProjectStatus.DECIDING: "❓",
            ProjectStatus.COMPLETED: "✅",
            ProjectStatus.CANCELLED: "❌"
        }.get(status, "⭕")
    
    def list_projects(self) -> str:
        """列出所有项目"""
        if not self.projects:
            return "暂无项目\n使用 '启动 [描述]' 创建新项目"
        
        lines = [
            f"📋 项目列表 ({len(self.projects)} 个)",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f""
        ]
        
        for pid, project in sorted(self.projects.items(), 
                                    key=lambda x: x[1].created_at, 
                                    reverse=True):
            emoji = self._status_emoji(project.status)
            created = project.created_at.strftime("%m-%d %H:%M")
            lines.append(f"{emoji} {project.name[:30]:<30} | {project.status.value:<10} | {created}")
            lines.append(f"   ID: {pid}")
        
        lines.append(f"")
        lines.append(f"💡 使用 '查询 [项目ID]' 查看详情")
        
        return "\n".join(lines)
    
    def pause_project(self, project_id: str) -> Tuple[bool, str]:
        """暂停项目"""
        project = self.projects.get(project_id)
        if not project:
            return False, f"❌ 项目不存在: {project_id}"
        
        if project.status not in [ProjectStatus.RUNNING, ProjectStatus.PLANNING, ProjectStatus.DECIDING]:
            return False, f"❌ 项目当前状态无法暂停: {project.status.value}"
        
        project.status = ProjectStatus.PAUSED
        project.updated_at = datetime.now()
        self._save_projects()
        
        return True, f"⏸️ 项目已暂停: {project.name}\n使用 '恢复 {project_id}' 继续"
    
    def resume_project(self, project_id: str) -> Tuple[bool, str]:
        """恢复项目"""
        project = self.projects.get(project_id)
        if not project:
            return False, f"❌ 项目不存在: {project_id}"
        
        if project.status != ProjectStatus.PAUSED:
            return False, f"❌ 项目未暂停: {project.status.value}"
        
        project.status = ProjectStatus.RUNNING
        project.updated_at = datetime.now()
        self._save_projects()
        
        return True, f"▶️ 项目已恢复: {project.name}"
    
    def complete_project(self, project_id: str) -> Tuple[bool, str]:
        """标记项目完成"""
        project = self.projects.get(project_id)
        if not project:
            return False, f"❌ 项目不存在: {project_id}"
        
        project.status = ProjectStatus.COMPLETED
        project.completed_at = datetime.now()
        project.updated_at = datetime.now()
        self._save_projects()
        
        return True, f"✅ 项目已完成: {project.name}"
    
    def handle_pdca_check(self, project_id: str) -> Optional[str]:
        """
        处理PDCA检查阶段
        当一轮Do完成后调用
        """
        project = self.projects.get(project_id)
        if not project:
            return None
        
        project.status = ProjectStatus.CHECKING
        project.pdca_cycle += 1
        
        # 获取检查结果
        check_result = self._perform_check(project)
        
        # 生成用户决策消息
        message = self._format_check_message(project, check_result)
        
        project.status = ProjectStatus.DECIDING
        self._save_projects()
        
        return message
    
    def _perform_check(self, project: Project) -> Dict:
        """执行检查"""
        task_statuses = []
        issues = []
        
        for tid in project.tasks:
            status = self.layer1.get_task_status(tid)
            if status:
                task_statuses.append(status)
                if status["status"] == "failed":
                    issues.append({
                        "task_id": tid,
                        "task_name": status.get("name", "unknown"),
                        "error": status.get("result", {}).get("error", "Unknown error")
                    })
        
        completed = sum(1 for t in task_statuses if t["status"] == "completed")
        failed = sum(1 for t in task_statuses if t["status"] == "failed")
        total = len(task_statuses)
        
        return {
            "total_tasks": total,
            "completed": completed,
            "failed": failed,
            "success_rate": (completed / total * 100) if total > 0 else 0,
            "issues": issues
        }
    
    def _format_check_message(self, project: Project, check: Dict) -> str:
        """格式化检查消息"""
        lines = [
            f"🧪 PDCA检查 - 第 {project.pdca_cycle} 轮",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"",
            f"📊 检查结果:",
            f"   总任务: {check['total_tasks']}",
            f"   ✅ 成功: {check['completed']}",
            f"   ❌ 失败: {check['failed']}",
            f"   📈 成功率: {check['success_rate']:.1f}%"
        ]
        
        if check["issues"]:
            lines.extend([
                f"",
                f"⚠️  发现问题:"
            ])
            for issue in check["issues"][:5]:
                lines.append(f"   • {issue['task_name']}: {issue['error'][:50]}")
        
        lines.extend([
            f"",
            f"❓ 请选择处置方式:",
            f"   [A] 继续 - 忽略问题，进入下一轮PDCA",
            f"   [B] 调整 - 修复问题后重新检查",
            f"   [C] 完成 - 标记项目完成",
            f"   [D] 暂停 - 暂停项目，等待后续决策",
            f"",
            f"💬 格式: PDCA {project.id} [A/B/C/D]"
        ])
        
        return "\n".join(lines)
    
    def handle_pdca_decision(self, project_id: str, decision: str) -> Tuple[bool, str]:
        """
        处理PDCA决策
        
        Args:
            project_id: 项目ID
            decision: A/B/C/D
        """
        project = self.projects.get(project_id)
        if not project:
            return False, f"❌ 项目不存在: {project_id}"
        
        decision = decision.upper()
        
        # 记录决策
        project.decision_history.append({
            "phase": "pdca_act",
            "cycle": project.pdca_cycle,
            "decision": decision,
            "timestamp": datetime.now().isoformat()
        })
        
        if decision == "A":  # 继续
            project.status = ProjectStatus.RUNNING
            self._save_projects()
            return True, f"▶️ 继续执行 - 进入第 {project.pdca_cycle + 1} 轮PDCA"
        
        elif decision == "B":  # 调整
            # 创建修复任务
            fix_tasks = self._create_fix_tasks(project)
            project.status = ProjectStatus.RUNNING
            self._save_projects()
            return True, f"🔧 开始调整 - 创建了 {len(fix_tasks)} 个修复任务"
        
        elif decision == "C":  # 完成
            return self.complete_project(project_id)
        
        elif decision == "D":  # 暂停
            return self.pause_project(project_id)
        
        else:
            return False, f"❌ 无效选项: {decision}"
    
    def _create_fix_tasks(self, project: Project) -> List[str]:
        """创建修复任务"""
        fix_task_ids = []
        
        for tid in project.tasks:
            status = self.layer1.get_task_status(tid)
            if status and status["status"] == "failed":
                # 创建重试任务
                fix_task = self.layer1.submit_task({
                    "project_id": project.id,
                    "role_id": status["role_id"],
                    "name": f"[Fix] {status.get('name', 'unknown')}",
                    "description": f"修复失败任务: {status.get('result', {}).get('error', '')}",
                    "priority": "P0"  # 修复任务高优先级
                })
                fix_task_ids.append(fix_task["task_id"])
        
        return fix_task_ids
    
    def process_command(self, command: str) -> str:
        """
        处理用户命令
        
        支持的命令:
        - 启动 [描述] - 创建新项目
        - 确认 [ID] [A/B/C/D] - 确认项目方案
        - 查询 [ID] - 查询项目状态
        - 状态 - 列出所有项目
        - 暂停 [ID] - 暂停项目
        - 恢复 [ID] - 恢复项目
        - PDCA [ID] [A/B/C/D] - PDCA决策
        """
        parts = command.strip().split(maxsplit=2)
        if not parts:
            return "❌ 空命令"
        
        cmd = parts[0].lower()
        
        if cmd == "启动":
            if len(parts) < 2:
                return "❌ 用法: 启动 [项目描述]"
            description = parts[1]
            project, message = self.create_project(description)
            return message
        
        elif cmd == "确认":
            if len(parts) < 3:
                return "❌ 用法: 确认 [项目ID] [A/B/C/D]"
            project_id = parts[1]
            choice = parts[2]
            success, message = self.confirm_project(project_id, choice)
            return message
        
        elif cmd == "查询":
            if len(parts) < 2:
                return "❌ 用法: 查询 [项目ID]"
            project_id = parts[1]
            result = self.check_project_status(project_id)
            return result or f"❌ 项目不存在: {project_id}"
        
        elif cmd == "状态":
            return self.list_projects()
        
        elif cmd == "暂停":
            if len(parts) < 2:
                return "❌ 用法: 暂停 [项目ID]"
            project_id = parts[1]
            success, message = self.pause_project(project_id)
            return message
        
        elif cmd == "恢复":
            if len(parts) < 2:
                return "❌ 用法: 恢复 [项目ID]"
            project_id = parts[1]
            success, message = self.resume_project(project_id)
            return message
        
        elif cmd == "pdca":
            if len(parts) < 3:
                return "❌ 用法: PDCA [项目ID] [A/B/C/D]"
            project_id = parts[1]
            decision = parts[2]
            success, message = self.handle_pdca_decision(project_id, decision)
            return message
        
        else:
            return f"❌ 未知命令: {cmd}\n支持: 启动, 确认, 查询, 状态, 暂停, 恢复, PDCA"
