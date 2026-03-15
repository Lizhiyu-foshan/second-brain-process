"""
AI驱动的Planner (规划器)
任务分解、蓝图生成、DAG构建 - 使用AI理解需求
"""
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from layer0.ai_client import get_ai_client

logger = logging.getLogger(__name__)


@dataclass
class TaskDefinition:
    """任务定义"""
    name: str
    description: str
    role: str                           # 角色类型
    pdca_phase: str = "do"             # PDCA阶段: plan/do/check
    depends_on: List[int] = field(default_factory=list)  # 依赖的任务索引
    estimated_hours: float = 1.0
    capabilities_required: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "role": self.role,
            "pdca_phase": self.pdca_phase,
            "depends_on": self.depends_on,
            "estimated_hours": self.estimated_hours,
            "capabilities_required": self.capabilities_required
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "TaskDefinition":
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            role=data.get("role", "developer"),
            pdca_phase=data.get("pdca_phase", "do"),
            depends_on=data.get("depends_on", []),
            estimated_hours=data.get("estimated_hours", 1.0),
            capabilities_required=data.get("capabilities_required", [])
        )


@dataclass
class Blueprint:
    """项目蓝图"""
    project_type: str                   # 项目类型标识
    name: str
    description: str
    tasks: List[TaskDefinition] = field(default_factory=list)
    workflow: List[str] = field(default_factory=list)  # 角色执行顺序
    estimated_duration: float = 0.0    # 预计总工时
    estimated_roles: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "project_type": self.project_type,
            "name": self.name,
            "description": self.description,
            "tasks": [t.to_dict() for t in self.tasks],
            "workflow": self.workflow,
            "estimated_duration": self.estimated_duration,
            "estimated_roles": self.estimated_roles,
            "risk_factors": self.risk_factors,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Blueprint":
        return cls(
            project_type=data.get("project_type", "unknown"),
            name=data.get("name", ""),
            description=data.get("description", ""),
            tasks=[TaskDefinition.from_dict(t) for t in data.get("tasks", [])],
            workflow=data.get("workflow", []),
            estimated_duration=data.get("estimated_duration", 0.0),
            estimated_roles=data.get("estimated_roles", []),
            risk_factors=data.get("risk_factors", []),
            created_at=data.get("created_at", datetime.now().isoformat())
        )


class Planner:
    """
    AI驱动的规划器
    
    职责:
    1. 使用AI解析用户需求
    2. AI动态分解任务（不是硬编码模板）
    3. AI构建DAG依赖图
    4. AI识别所需角色
    5. AI评估风险和复杂度
    
    使用模型: Kimi K2.5 (kimi-coding/k2p5) - 最强的理解能力
    """
    
    # 可用角色定义
    AVAILABLE_ROLES = {
        "architect": {
            "name": "架构师",
            "capabilities": ["architecture", "design", "tech_selection", "planning"],
            "description": "负责系统架构设计、技术选型、模块划分"
        },
        "developer": {
            "name": "开发者",
            "capabilities": ["coding", "implementation", "debugging", "skill_development"],
            "description": "负责代码实现、功能开发、Bug修复"
        },
        "tester": {
            "name": "测试员",
            "capabilities": ["testing", "validation", "quality_assurance"],
            "description": "负责测试验证、质量报告、测试用例生成"
        },
        "analyst": {
            "name": "分析师",
            "capabilities": ["analysis", "requirements", "research"],
            "description": "负责需求分析、现状调研、可行性分析"
        },
        "auditor": {
            "name": "代码审计员",
            "capabilities": ["security_audit", "code_review", "vulnerability_detection"],
            "description": "负责代码审计、安全检测、漏洞分析"
        }
    }
    
    def __init__(self, layer1_api=None):
        """
        初始化规划器
        
        Args:
            layer1_api: Layer 1 API 实例（可选，用于查询角色状态）
        """
        self.layer1 = layer1_api
        self.ai_client = get_ai_client()
    
    def create_blueprint(self, description: str, name: Optional[str] = None) -> Blueprint:
        """
        使用AI根据描述创建项目蓝图
        
        Args:
            description: 项目描述
            name: 项目名称（可选）
            
        Returns:
            项目蓝图
        """
        logger.info(f"AI分析项目需求: {description[:100]}...")
        
        # 1. 使用AI分析需求并生成任务分解
        ai_response = self._call_ai_for_decomposition(description)
        
        if not ai_response["success"]:
            logger.error(f"AI分解失败: {ai_response.get('error')}")
            # 降级为简单默认分解
            return self._create_fallback_blueprint(description, name)
        
        ai_result = ai_response["result"]
        
        # 2. 解析AI输出
        project_type = ai_result.get("project_type", "general")
        project_name = name or ai_result.get("name", self._generate_name(description))
        
        # 3. 创建蓝图
        blueprint = Blueprint(
            project_type=project_type,
            name=project_name,
            description=description
        )
        
        # 4. 从AI输出构建任务
        tasks_data = ai_result.get("tasks", [])
        for i, task_data in enumerate(tasks_data):
            task = TaskDefinition(
                name=task_data.get("name", f"任务{i+1}"),
                description=task_data.get("description", ""),
                role=task_data.get("role", "developer"),
                pdca_phase=task_data.get("pdca_phase", "do"),
                depends_on=task_data.get("depends_on", []),
                estimated_hours=task_data.get("estimated_hours", 1.0),
                capabilities_required=task_data.get("capabilities_required", [])
            )
            blueprint.tasks.append(task)
        
        # 5. 从AI输出获取其他信息
        blueprint.workflow = ai_result.get("workflow", self._derive_workflow(blueprint.tasks))
        blueprint.estimated_roles = list(set(t.role for t in blueprint.tasks))
        blueprint.risk_factors = ai_result.get("risk_factors", [])
        blueprint.estimated_duration = sum(t.estimated_hours for t in blueprint.tasks)
        
        logger.info(f"AI生成蓝图: {blueprint.name} ({len(blueprint.tasks)} 个任务, 角色: {blueprint.estimated_roles})")
        
        return blueprint
    
    def _call_ai_for_decomposition(self, description: str) -> Dict:
        """调用AI进行任务分解"""
        
        # 构建提示词
        roles_info = json.dumps(self.AVAILABLE_ROLES, ensure_ascii=False, indent=2)
        
        prompt = f"""你是一位资深的项目规划专家。请分析以下项目需求，并生成详细的任务分解方案。

## 可用角色
{roles_info}

## 项目需求
{description}

## 要求
请分析需求并输出JSON格式的任务分解方案：

{{
    "project_type": "项目类型标识",
    "name": "建议的项目名称",
    "tasks": [
        {{
            "name": "任务名称",
            "description": "任务详细描述",
            "role": "负责角色（从可用角色中选择）",
            "pdca_phase": "plan/do/check 之一",
            "depends_on": [依赖的任务索引列表],
            "estimated_hours": 预估工时（数字）,
            "capabilities_required": ["需要的能力"]
        }}
    ],
    "workflow": ["角色执行顺序"],
    "risk_factors": ["识别的风险因素"]
}}

## 注意事项
1. 任务分解要合理，每个任务应有明确的交付物
2. 依赖关系要正确，形成合理的DAG
3. 角色分配要根据任务性质，不要一个角色做所有事
4. 预估工时要实际可行
5. 必须输出合法的JSON格式"""

        try:
            response = self.ai_client.call(
                role="architect",  # 使用architect配置（Kimi K2.5）
                task_description=prompt,
                model="kimi-k2.5",
                temperature=0.7,
                max_tokens=4000
            )
            
            if not response["success"]:
                return {"success": False, "error": response.get("error")}
            
            # 解析AI返回的JSON
            content = response["content"]
            
            # 尝试从Markdown代码块中提取JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            result = json.loads(content)
            
            return {
                "success": True,
                "result": result,
                "raw_response": response["content"]
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"AI返回的JSON解析失败: {e}")
            return {"success": False, "error": f"JSON解析失败: {e}"}
        except Exception as e:
            logger.error(f"AI调用失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _create_fallback_blueprint(self, description: str, name: Optional[str] = None) -> Blueprint:
        """创建降级蓝图（当AI失败时使用）"""
        blueprint = Blueprint(
            project_type="general",
            name=name or self._generate_name(description),
            description=description
        )
        
        # 简单的默认任务
        blueprint.tasks = [
            TaskDefinition(
                name="[Plan] 需求分析与规划",
                description=f"分析项目需求: {description[:100]}",
                role="architect",
                pdca_phase="plan",
                estimated_hours=2.0
            ),
            TaskDefinition(
                name="[Do] 核心功能开发",
                description="实现核心功能",
                role="developer",
                pdca_phase="do",
                depends_on=[0],
                estimated_hours=8.0
            ),
            TaskDefinition(
                name="[Check] 测试验证",
                description="执行测试验证",
                role="tester",
                pdca_phase="check",
                depends_on=[1],
                estimated_hours=3.0
            )
        ]
        
        blueprint.workflow = ["architect", "developer", "tester"]
        blueprint.estimated_roles = ["architect", "developer", "tester"]
        blueprint.estimated_duration = 13.0
        
        return blueprint
    
    def _generate_name(self, description: str) -> str:
        """生成项目名称"""
        prefix = description[:30].strip()
        if len(prefix) > 30:
            prefix = prefix[:27] + "..."
        return f"项目: {prefix}"
    
    def _derive_workflow(self, tasks: List[TaskDefinition]) -> List[str]:
        """从任务推导执行顺序"""
        role_order = []
        seen = set()
        
        for task in tasks:
            if task.role not in seen:
                role_order.append(task.role)
                seen.add(task.role)
        
        return role_order
    
    def build_dependency_graph(self, blueprint: Blueprint) -> Dict[int, List[int]]:
        """
        构建任务依赖图
        
        Returns:
            依赖图 {任务索引: [依赖任务索引列表]}
        """
        graph = {}
        
        for i, task in enumerate(blueprint.tasks):
            graph[i] = task.depends_on
        
        return graph
    
    def get_execution_order(self, blueprint: Blueprint) -> List[int]:
        """
        获取任务执行顺序（拓扑排序）
        
        Returns:
            按执行顺序排列的任务索引列表
        """
        graph = self.build_dependency_graph(blueprint)
        n = len(blueprint.tasks)
        
        # 计算每个任务的入度（依赖数量）
        in_degree = {i: 0 for i in range(n)}
        for task_idx, deps in graph.items():
            in_degree[task_idx] = len(deps)
        
        # 初始化队列（入度为0的节点，即无依赖的任务）
        queue = [i for i, d in in_degree.items() if d == 0]
        result = []
        
        while queue:
            # 按PDCA阶段优先级排序：plan > do > check
            queue.sort(key=lambda i: (
                0 if blueprint.tasks[i].pdca_phase == "plan" else
                1 if blueprint.tasks[i].pdca_phase == "do" else 2
            ))
            
            node = queue.pop(0)
            result.append(node)
            
            # 找到依赖当前节点的任务，减少它们的入度
            for i, deps in graph.items():
                if node in deps:
                    in_degree[i] -= 1
                    if in_degree[i] == 0:
                        queue.append(i)
        
        if len(result) != n:
            logger.warning(f"Dependency cycle detected: {n} tasks, {len(result)} sorted")
        
        return result
    
    def analyze_complexity(self, description: str) -> Dict[str, Any]:
        """
        使用AI分析项目复杂度
        
        Returns:
            复杂度分析结果
        """
        prompt = f"""分析以下项目需求的复杂度：

{description}

请输出JSON格式：
{{
    "level": "简单/中等/复杂",
    "score": 1-10的数字,
    "factors": ["复杂度因素1", "因素2"],
    "suggested_roles": ["建议的角色列表"],
    "estimated_tasks": 预估任务数量
}}"""
        
        try:
            response = self.ai_client.call(
                role="architect",
                task_description=prompt,
                model="kimi-k2.5",
                temperature=0.5,
                max_tokens=1000
            )
            
            if not response["success"]:
                return {
                    "level": "中等",
                    "score": 5,
                    "factors": ["无法分析复杂度"],
                    "suggested_roles": ["developer", "tester"],
                    "estimated_tasks": 3
                }
            
            content = response["content"]
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"复杂度分析失败: {e}")
            return {
                "level": "中等",
                "score": 5,
                "factors": ["分析失败"],
                "suggested_roles": ["developer", "tester"],
                "estimated_tasks": 3
            }
    
    def suggest_optimization(self, blueprint: Blueprint) -> List[Dict]:
        """
        使用AI建议蓝图优化
        
        Returns:
            优化建议列表
        """
        blueprint_json = json.dumps(blueprint.to_dict(), ensure_ascii=False, indent=2)
        
        prompt = f"""分析以下项目蓝图并提供优化建议：

{blueprint_json}

请输出JSON格式的优化建议列表：
[
    {{
        "type": "建议类型",
        "reason": "原因说明",
        "action": "建议操作"
    }}
]"""
        
        try:
            response = self.ai_client.call(
                role="architect",
                task_description=prompt,
                model="kimi-k2.5",
                temperature=0.5,
                max_tokens=1000
            )
            
            if not response["success"]:
                return []
            
            content = response["content"]
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"优化建议生成失败: {e}")
            return []
