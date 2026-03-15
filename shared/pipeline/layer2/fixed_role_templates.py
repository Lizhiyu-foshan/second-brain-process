"""
固定角色模板管理器

管理可复用的固定角色模板，新类型首次出现时需用户确认
"""
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

from shared.models import EnhancedJSONEncoder

logger = logging.getLogger(__name__)


@dataclass
class RoleTemplate:
    """固定角色模板"""
    type_id: str
    name: str
    description: str
    roles: List[Dict]  # 角色定义列表
    workflow: List[str]  # 角色执行顺序
    created_at: datetime = None
    usage_count: int = 0
    performance_history: List[Dict] = field(default_factory=list)
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.performance_history is None:
            self.performance_history = []
    
    def to_dict(self) -> Dict:
        return {
            "type_id": self.type_id,
            "name": self.name,
            "description": self.description,
            "roles": self.roles,
            "workflow": self.workflow,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "usage_count": self.usage_count,
            "performance_history": self.performance_history
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'RoleTemplate':
        return cls(
            type_id=data["type_id"],
            name=data["name"],
            description=data["description"],
            roles=data["roles"],
            workflow=data["workflow"],
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            usage_count=data.get("usage_count", 0),
            performance_history=data.get("performance_history", [])
        )


@dataclass
class NewTypeRequest:
    """新类型请求"""
    id: str
    project_type: str
    description: str
    proposed_roles: List[Dict]
    status: str  # pending_user_approval, approved, temporary_only, cancelled
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "project_type": self.project_type,
            "description": self.description,
            "proposed_roles": self.proposed_roles,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class FixedRoleTemplateManager:
    """
    固定角色模板管理器
    
    管理所有已沉淀的固定角色模板
    新任务类型首次出现时，需要用户确认创建
    """
    
    TEMPLATES_FILE = "/root/.openclaw/workspace/shared/pipeline/state/fixed_role_templates.json"
    
    def __init__(self):
        self.templates: Dict[str, RoleTemplate] = {}
        self.pending_approvals: Dict[str, NewTypeRequest] = {}
        self._load_templates()
    
    def _load_templates(self):
        """加载已存在的模板"""
        if os.path.exists(self.TEMPLATES_FILE):
            try:
                with open(self.TEMPLATES_FILE, 'r') as f:
                    data = json.load(f)
                    for type_id, tdata in data.get("templates", {}).items():
                        self.templates[type_id] = RoleTemplate.from_dict(tdata)
                    for req_id, rdata in data.get("pending_approvals", {}).items():
                        self.pending_approvals[req_id] = NewTypeRequest(**rdata)
                logger.info(f"Loaded {len(self.templates)} templates, {len(self.pending_approvals)} pending approvals")
            except Exception as e:
                logger.error(f"Failed to load templates: {e}")
    
    def _save_templates(self):
        """保存模板"""
        try:
            os.makedirs(os.path.dirname(self.TEMPLATES_FILE), exist_ok=True)
            with open(self.TEMPLATES_FILE, 'w') as f:
                json.dump({
                    "templates": {
                        tid: t.to_dict() for tid, t in self.templates.items()
                    },
                    "pending_approvals": {
                        rid: r.to_dict() for rid, r in self.pending_approvals.items()
                    },
                    "last_updated": datetime.now().isoformat()
                }, f, indent=2, cls=EnhancedJSONEncoder)
        except Exception as e:
            logger.error(f"Failed to save templates: {e}")
    
    def check_type_exists(self, project_type: str) -> bool:
        """检查任务类型是否已有固定模板"""
        return project_type in self.templates
    
    def get_template(self, project_type: str) -> Optional[RoleTemplate]:
        """获取固定角色模板"""
        return self.templates.get(project_type)
    
    def request_new_type_approval(self, project_type: str, description: str,
                                   proposed_roles: List[Dict]) -> tuple:
        """
        请求用户批准新任务类型的固定角色模板
        
        Returns:
            (request_id, message)
        """
        request_id = f"REQ_{datetime.now().strftime('%Y%m%d')}_{uuid4().hex[:4]}"
        
        request = NewTypeRequest(
            id=request_id,
            project_type=project_type,
            description=description,
            proposed_roles=proposed_roles,
            status="pending_user_approval"
        )
        
        self.pending_approvals[request_id] = request
        self._save_templates()
        
        message = self._generate_approval_message(request)
        
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
            f"回复格式: '确认 {request.id} A' 或 '确认 {request.id} B: 调整内容'",
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
            del self.pending_approvals[request_id]
            self._save_templates()
            return None
        
        if choice == "C":  # 仅本次使用
            request.status = "temporary_only"
            del self.pending_approvals[request_id]
            self._save_templates()
            return None
        
        # A 或 B: 创建固定模板
        roles = request.proposed_roles
        if choice == "B" and modifications:
            roles = self._apply_modifications(roles, modifications)
        
        # 创建模板
        template = RoleTemplate(
            type_id=request.project_type,
            name=self._generate_type_name(request.project_type),
            description=request.description,
            roles=roles,
            workflow=[r["type"] for r in roles]
        )
        
        # 保存模板
        self.templates[request.project_type] = template
        del self.pending_approvals[request_id]
        self._save_templates()
        
        logger.info(f"Created fixed role template for {request.project_type}")
        return template
    
    def _apply_modifications(self, roles: List[Dict], modifications: Dict) -> List[Dict]:
        """应用用户修改"""
        # 简单实现：添加新角色
        if modifications.get("add_role"):
            roles.append(modifications["add_role"])
        
        # 修改现有角色能力
        if modifications.get("update_capabilities"):
            role_type = modifications["update_capabilities"]["type"]
            new_caps = modifications["update_capabilities"]["capabilities"]
            for role in roles:
                if role["type"] == role_type:
                    role["capabilities"] = new_caps
        
        return roles
    
    def update_template_performance(self, project_type: str,
                                     execution_data: Dict):
        """更新模板性能历史"""
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
        """基于历史数据建议模板优化"""
        template = self.templates.get(project_type)
        if not template or len(template.performance_history) < 5:
            return []
        
        suggestions = []
        
        # 分析成功率
        recent = template.performance_history[-10:]
        success_rate = sum(1 for h in recent if h.get("success")) / len(recent)
        
        if success_rate < 0.8:
            suggestions.append({
                "type": "add_tester",
                "reason": f"近期成功率{success_rate:.1%}，建议增加测试环节",
                "action": "在workflow中添加tester角色"
            })
        
        # 分析平均耗时
        avg_duration = sum(h.get("actual_duration", 0) for h in recent) / len(recent)
        
        if avg_duration > 60:  # 超过1小时
            suggestions.append({
                "type": "extend_time",
                "reason": f"实际耗时({avg_duration:.0f}m)较长",
                "action": "调整时间估算参数"
            })
        
        return suggestions
    
    def _generate_type_name(self, type_id: str) -> str:
        """生成类型显示名称"""
        name_map = {
            "system_dev": "系统开发",
            "content_creation": "内容创作",
            "course_design": "课程设计",
            "data_analysis": "数据分析",
            "market_research": "市场调研"
        }
        return name_map.get(type_id, type_id.replace("_", " ").title())
    
    def list_all_templates(self) -> List[RoleTemplate]:
        """获取所有固定模板"""
        return list(self.templates.values())
    
    def get_pending_requests(self) -> List[NewTypeRequest]:
        """获取待确认的请求"""
        return [
            req for req in self.pending_approvals.values()
            if req.status == "pending_user_approval"
        ]
