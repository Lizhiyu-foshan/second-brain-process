"""
角色注册表
管理所有角色实例的注册、状态查询和持久化
"""
import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import uuid4

from shared.models import Role, RoleMetrics, RoleConfig, EnhancedJSONEncoder

logger = logging.getLogger(__name__)


def get_workspace_dir() -> Path:
    """获取工作目录，优先使用环境变量"""
    base = os.getenv("OPENCLAW_WORKSPACE")
    if base:
        return Path(base)
    return Path.cwd() / ".openclaw" / "workspace"


class RoleRegistry:
    """
    角色注册表
    
    职责:
    - 注册新角色
    - 查询角色状态
    - 更新角色指标
    - 持久化到文件
    """
    
    def __init__(self, state_file: str = None):
        """
        初始化角色注册表
        
        Args:
            state_file: 状态文件路径
        """
        if state_file is None:
            state_file = get_workspace_dir() / "shared" / "pipeline" / "state" / "layer1_state.json"
        else:
            state_file = Path(state_file)
        
        self.state_file = state_file
        self.roles: Dict[str, Role] = {}
        self._load()
    
    def _load(self):
        """从文件加载角色状态"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    for role_id, role_data in data.get("roles", {}).items():
                        self.roles[role_id] = self._deserialize_role(role_data)
                logger.info(f"Loaded {len(self.roles)} roles from {self.state_file}")
            except json.JSONDecodeError as e:
                logger.error(f"State file corrupted: {e}")
                self._backup_corrupted_file()
                self.roles = {}
            except PermissionError as e:
                logger.error(f"Permission denied reading state: {e}")
                raise
            except Exception as e:
                logger.error(f"Failed to load roles: {e}")
                self.roles = {}
    
    def _save(self):
        """
        保存角色状态到文件（原子写入）
        
        使用临时文件 + os.replace 实现原子写入，避免多进程写入冲突。
        """
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            
            data = {
                "roles": {
                    role_id: self._serialize_role(role)
                    for role_id, role in self.roles.items()
                },
                "last_updated": datetime.now().isoformat()
            }
            
            # 原子写入：先写入临时文件，再原子替换
            dir_name = os.path.dirname(self.state_file)
            fd, temp_path = tempfile.mkstemp(dir=dir_name, suffix='.json.tmp')
            
            try:
                with os.fdopen(fd, 'w') as f:
                    json.dump(data, f, indent=2, cls=EnhancedJSONEncoder)
                    f.flush()
                    os.fsync(fd)  # 确保数据落盘
                
                # 原子替换原文件
                os.replace(temp_path, self.state_file)
                
            except Exception:
                # 清理临时文件
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise
                
        except Exception as e:
            logger.error(f"Failed to save roles: {e}")
            raise
    
    def _backup_corrupted_file(self):
        """备份损坏的状态文件"""
        try:
            if os.path.exists(self.state_file):
                backup_path = f"{self.state_file}.corrupted.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.rename(self.state_file, backup_path)
                logger.warning(f"Corrupted state file backed up to: {backup_path}")
        except Exception as e:
            logger.error(f"Failed to backup corrupted file: {e}")
    
    def _serialize_role(self, role: Role) -> Dict:
        """序列化角色"""
        return {
            "id": role.id,
            "type": role.type,
            "name": role.name,
            "capabilities": role.capabilities,
            "status": role.status,
            "queue": role.queue,
            "current_task": role.current_task,
            "metrics": {
                "total_tasks": role.metrics.total_tasks,
                "success_count": role.metrics.success_count,
                "fail_count": role.metrics.fail_count,
                "avg_duration": role.metrics.avg_duration,
                "success_rate": role.metrics.success_rate
            },
            "config": {
                "poll_interval_minutes": role.config.poll_interval_minutes,
                "lock_timeout_minutes": role.config.lock_timeout_minutes,
                "max_concurrent": role.config.max_concurrent
            }
        }
    
    def _deserialize_role(self, data: Dict) -> Role:
        """反序列化角色"""
        role = Role(
            id=data["id"],
            type=data["type"],
            name=data["name"],
            capabilities=data.get("capabilities", []),
            status=data.get("status", "idle"),
            queue=data.get("queue", []),
            current_task=data.get("current_task")
        )
        
        # 恢复指标
        metrics_data = data.get("metrics", {})
        role.metrics.total_tasks = metrics_data.get("total_tasks", 0)
        role.metrics.success_count = metrics_data.get("success_count", 0)
        role.metrics.fail_count = metrics_data.get("fail_count", 0)
        role.metrics.avg_duration = metrics_data.get("avg_duration", 0.0)
        role.metrics.success_rate = metrics_data.get("success_rate", 1.0)
        
        # 恢复配置
        config_data = data.get("config", {})
        role.config.poll_interval_minutes = config_data.get("poll_interval_minutes", 15)
        role.config.lock_timeout_minutes = config_data.get("lock_timeout_minutes", 30)
        role.config.max_concurrent = config_data.get("max_concurrent", 1)
        
        return role
    
    def register(self, role_type: str, name: str, capabilities: List[str],
                 config: RoleConfig = None) -> str:
        """
        注册新角色
        
        角色ID与role_type相同，确保固定角色实体。
        如果角色已存在，直接返回现有ID。
        
        Args:
            role_type: 角色类型 (architect, developer, tester等)，同时作为角色ID
            name: 角色名称
            capabilities: 能力列表
            config: 角色配置，默认使用默认配置
            
        Returns:
            角色ID（与role_type相同）
        """
        role_id = role_type  # 使用固定ID，不生成UUID
        
        # 如果角色已存在，直接返回
        if role_id in self.roles:
            logger.debug(f"Role already exists: {role_id}")
            return role_id
        
        role = Role(
            id=role_id,
            type=role_type,
            name=name,
            capabilities=capabilities,
            config=config or RoleConfig()
        )
        
        self.roles[role_id] = role
        self._save()
        
        logger.info(f"Registered role: {role_id} ({name})")
        return role_id
    
    def get(self, role_id: str) -> Optional[Role]:
        """
        获取角色
        
        Args:
            role_id: 角色ID
            
        Returns:
            Role对象，不存在则返回None
        """
        return self.roles.get(role_id)
    
    def get_by_type(self, role_type: str) -> List[Role]:
        """
        按类型获取角色
        
        Args:
            role_type: 角色类型
            
        Returns:
            该类型的所有角色列表
        """
        return [role for role in self.roles.values() if role.type == role_type]
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取所有角色状态
        
        Returns:
            角色ID到状态信息的映射
        """
        return {
            role_id: {
                "id": role.id,
                "type": role.type,
                "name": role.name,
                "status": role.status,
                "queue_depth": len(role.queue),
                "current_task": role.current_task,
                "capabilities": role.capabilities,
                "metrics": {
                    "total_tasks": role.metrics.total_tasks,
                    "avg_duration": round(role.metrics.avg_duration, 2),
                    "success_rate": round(role.metrics.success_rate, 2)
                }
            }
            for role_id, role in self.roles.items()
        }
    
    def update_status(self, role_id: str, status: str, current_task: str = None):
        """
        更新角色状态
        
        Args:
            role_id: 角色ID
            status: 新状态
            current_task: 当前任务ID
        """
        role = self.roles.get(role_id)
        if role:
            role.status = status
            if current_task is not None:
                role.current_task = current_task
            self._save()
            logger.debug(f"Updated role {role_id} status to {status}")
    
    def add_to_queue(self, role_id: str, task_id: str):
        """
        添加任务到角色队列
        
        Args:
            role_id: 角色ID
            task_id: 任务ID
        """
        role = self.roles.get(role_id)
        if role:
            if task_id not in role.queue:
                role.queue.append(task_id)
                self._save()
    
    def remove_from_queue(self, role_id: str, task_id: str):
        """
        从角色队列移除任务
        
        Args:
            role_id: 角色ID
            task_id: 任务ID
        """
        role = self.roles.get(role_id)
        if role:
            if task_id in role.queue:
                role.queue.remove(task_id)
                self._save()
    
    def update_metrics(self, role_id: str, duration_minutes: float, success: bool):
        """
        更新角色指标
        
        Args:
            role_id: 角色ID
            duration_minutes: 任务耗时(分钟)
            success: 是否成功
        """
        role = self.roles.get(role_id)
        if role:
            role.metrics.update(duration_minutes, success)
            self._save()
    
    def list_all(self) -> List[Role]:
        """
        获取所有角色
        
        Returns:
            所有角色的列表
        """
        return list(self.roles.values())
    
    def unregister(self, role_id: str) -> bool:
        """
        注销角色
        
        Args:
            role_id: 角色ID
            
        Returns:
            True: 成功注销
            False: 角色不存在
        """
        if role_id in self.roles:
            del self.roles[role_id]
            self._save()
            logger.info(f"Unregistered role: {role_id}")
            return True
        return False
    
    def get_idle_roles(self, role_type: str = None) -> List[Role]:
        """
        获取空闲角色
        
        Args:
            role_type: 可选，指定角色类型
            
        Returns:
            空闲角色列表
        """
        idle_roles = [role for role in self.roles.values() if role.status == "idle"]
        
        if role_type:
            idle_roles = [role for role in idle_roles if role.type == role_type]
        
        return idle_roles
