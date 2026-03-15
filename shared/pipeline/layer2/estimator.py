"""
Estimator (估算器)
工作量估算、工期预测、资源可用性查询
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

from layer2.planner import Blueprint, TaskDefinition

logger = logging.getLogger(__name__)


class Estimator:
    """
    估算器
    
    职责:
    1. 估算单个任务工时
    2. 估算项目总工期
    3. 查询资源可用性
    4. 预测完成时间
    """
    
    # 角色效率系数（基于历史数据）
    ROLE_EFFICIENCY = {
        "analyst": 1.0,      # 分析师：标准效率
        "architect": 0.9,    # 架构师：需要更多思考时间
        "developer": 1.1,    # 开发者：效率略高
        "tester": 1.0,       # 测试员：标准效率
        "planner": 0.95      # 规划师：略低于标准
    }
    
    # 复杂度系数
    COMPLEXITY_MULTIPLIER = {
        "简单": 0.8,
        "中等": 1.0,
        "复杂": 1.5
    }
    
    # 风险缓冲系数
    RISK_BUFFER = {
        "低风险": 1.0,
        "中等风险": 1.2,
        "高风险": 1.5
    }
    
    def __init__(self, layer1_api):
        """
        初始化估算器
        
        Args:
            layer1_api: Layer 1 API 实例
        """
        self.layer1 = layer1_api
    
    def estimate_task(self, task: TaskDefinition, 
                     role_availability: Optional[Dict] = None) -> Dict[str, Any]:
        """
        估算单个任务
        
        Args:
            task: 任务定义
            role_availability: 角色可用性信息
            
        Returns:
            估算结果
        """
        base_hours = task.estimated_hours
        
        # 应用角色效率系数
        role_eff = self.ROLE_EFFICIENCY.get(task.role, 1.0)
        adjusted_hours = base_hours / role_eff
        
        # 应用复杂度系数
        complexity = self._estimate_complexity(task)
        complexity_mult = self.COMPLEXITY_MULTIPLIER.get(complexity, 1.0)
        adjusted_hours *= complexity_mult
        
        # 等待时间估算
        wait_hours = 0.0
        if role_availability:
            wait_hours = role_availability.get("queue_depth", 0) * 0.5
        
        return {
            "task_name": task.name,
            "base_hours": base_hours,
            "adjusted_hours": round(adjusted_hours, 1),
            "wait_hours": round(wait_hours, 1),
            "total_hours": round(adjusted_hours + wait_hours, 1),
            "complexity": complexity,
            "role_efficiency": role_eff
        }
    
    def estimate_project(self, blueprint: Blueprint) -> Dict[str, Any]:
        """
        估算整个项目
        
        Args:
            blueprint: 项目蓝图
            
        Returns:
            估算结果
        """
        task_estimates = []
        total_hours = 0.0
        
        # 获取当前资源状态
        roles_status = self.layer1.registry.get_status()
        
        for task in blueprint.tasks:
            # 查询该角色的可用性
            role_status = None
            for rid, status in roles_status.items():
                if status["type"] == task.role:
                    role_status = status
                    break
            
            availability = None
            if role_status:
                availability = {
                    "status": role_status["status"],
                    "queue_depth": len(role_status.get("queue", []))
                }
            
            estimate = self.estimate_task(task, availability)
            task_estimates.append(estimate)
            total_hours += estimate["total_hours"]
        
        # 应用风险缓冲
        risk_level = self._assess_risk(blueprint)
        risk_mult = self.RISK_BUFFER.get(risk_level, 1.0)
        
        buffered_hours = total_hours * risk_mult
        
        # 计算日历时间（假设每天有效工作8小时）
        calendar_days = buffered_hours / 8.0
        
        # 预测完成时间
        estimated_completion = datetime.now() + timedelta(days=calendar_days)
        
        return {
            "project_name": blueprint.name,
            "total_hours": round(total_hours, 1),
            "buffered_hours": round(buffered_hours, 1),
            "calendar_days": round(calendar_days, 1),
            "estimated_completion": estimated_completion.strftime("%Y-%m-%d %H:%M"),
            "risk_level": risk_level,
            "risk_multiplier": risk_mult,
            "roles": list(set(t["task_name"].split("]")[0].replace("[", "") 
                            for t in task_estimates)),
            "task_breakdown": task_estimates[:5]  # 前5个任务详情
        }
    
    def query_feasible_window(self, role_ids: List[str], 
                             duration_hours: float) -> Dict[str, Any]:
        """
        查询可行时间窗口
        
        Args:
            role_ids: 需要的角色ID列表
            duration_hours: 所需持续时间（小时）
            
        Returns:
            可行窗口信息
        """
        roles_status = self.layer1.registry.get_status()
        
        role_availability = []
        all_available = True
        max_wait_minutes = 0
        
        for rid in role_ids:
            status = roles_status.get(rid)
            if not status:
                role_availability.append({
                    "role_id": rid,
                    "available": False,
                    "reason": "角色未注册"
                })
                all_available = False
                continue
            
            if status["status"] == "idle":
                role_availability.append({
                    "role_id": rid,
                    "role_type": status["type"],
                    "available": True,
                    "wait_minutes": 0
                })
            else:
                # 估算等待时间
                queue_len = len(status.get("queue", []))
                # 假设每个任务平均30分钟
                wait_minutes = queue_len * 30
                
                role_availability.append({
                    "role_id": rid,
                    "role_type": status["type"],
                    "available": False,
                    "current_task": status.get("current_task"),
                    "queue_length": queue_len,
                    "wait_minutes": wait_minutes
                })
                
                max_wait_minutes = max(max_wait_minutes, wait_minutes)
                all_available = False
        
        # 计算最早开始时间
        if all_available:
            earliest_start = datetime.now()
        else:
            earliest_start = datetime.now() + timedelta(minutes=max_wait_minutes)
        
        # 计算预计完成时间
        estimated_end = earliest_start + timedelta(hours=duration_hours)
        
        return {
            "feasible": all_available,
            "duration_hours": duration_hours,
            "earliest_start": earliest_start.isoformat(),
            "estimated_end": estimated_end.isoformat(),
            "role_availability": role_availability,
            "max_wait_minutes": max_wait_minutes
        }
    
    def predict_bottleneck(self, blueprint: Blueprint) -> Optional[Dict[str, Any]]:
        """
        预测项目瓶颈
        
        Returns:
            瓶颈信息，无瓶颈返回None
        """
        # 统计每个角色的总工时
        role_hours = {}
        for task in blueprint.tasks:
            role = task.role
            role_hours[role] = role_hours.get(role, 0) + task.estimated_hours
        
        # 找出工作量最大的角色
        if not role_hours:
            return None
        
        bottleneck_role = max(role_hours.items(), key=lambda x: x[1])
        
        # 获取该角色的当前状态
        roles_status = self.layer1.registry.get_status()
        role_status = None
        for rid, status in roles_status.items():
            if status["type"] == bottleneck_role[0]:
                role_status = status
                break
        
        if not role_status:
            return None
        
        # 判断是否可能成为瓶颈
        is_bottleneck = (
            bottleneck_role[1] > 20 or  # 工时超过20小时
            role_status["status"] == "busy" or  # 当前忙碌
            len(role_status.get("queue", [])) > 5  # 队列深度大
        )
        
        if is_bottleneck:
            return {
                "role": bottleneck_role[0],
                "estimated_hours": bottleneck_role[1],
                "current_status": role_status["status"],
                "queue_length": len(role_status.get("queue", [])),
                "suggestion": self._suggest_bottleneck_mitigation(
                    bottleneck_role[0], bottleneck_role[1]
                )
            }
        
        return None
    
    def _suggest_bottleneck_mitigation(self, role: str, hours: float) -> str:
        """建议瓶颈缓解措施"""
        if hours > 30:
            return f"{role}工作量过大({hours:.1f}h)，建议拆分项目或增加该角色实例"
        elif hours > 15:
            return f"{role}工作量较重({hours:.1f}h)，建议优先调度该角色"
        else:
            return f"{role}当前忙碌，建议等待或提高任务优先级"
    
    def _estimate_complexity(self, task: TaskDefinition) -> str:
        """估算任务复杂度"""
        desc = task.description.lower()
        
        # 简单指标
        simple_indicators = ["简单", "基础", "标准", "常规", "basic", "simple", "standard"]
        complex_indicators = ["复杂", "困难", "算法", "优化", "重构", "complex", "algorithm", "optimization"]
        
        if any(w in desc for w in complex_indicators):
            return "复杂"
        elif any(w in desc for w in simple_indicators):
            return "简单"
        else:
            # 根据工时判断
            if task.estimated_hours <= 2:
                return "简单"
            elif task.estimated_hours <= 6:
                return "中等"
            else:
                return "复杂"
    
    def _assess_risk(self, blueprint: Blueprint) -> str:
        """评估项目风险等级"""
        risk_count = len(blueprint.risk_factors)
        
        # 检查是否有高风险关键词
        high_risk_keywords = ["紧急", "立即", "关键", "urgent", "critical"]
        desc_lower = blueprint.description.lower()
        has_high_risk = any(kw in desc_lower for kw in high_risk_keywords)
        
        if has_high_risk or risk_count >= 3:
            return "高风险"
        elif risk_count >= 1:
            return "中等风险"
        else:
            return "低风险"
    
    def generate_schedule(self, blueprint: Blueprint, 
                         start_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        生成项目进度表
        
        Args:
            blueprint: 项目蓝图
            start_date: 开始日期（默认现在）
            
        Returns:
            进度表
        """
        if not start_date:
            start_date = datetime.now()
        
        schedule = []
        current_time = start_date
        
        # 按执行顺序排序
        from layer2.planner import Planner
        planner = Planner()
        execution_order = planner.get_execution_order(blueprint)
        
        for idx in execution_order:
            task = blueprint.tasks[idx]
            
            # 计算工期
            estimate = self.estimate_task(task)
            duration_hours = estimate["total_hours"]
            
            # 计算结束时间
            end_time = current_time + timedelta(hours=duration_hours)
            
            schedule.append({
                "task_index": idx,
                "task_name": task.name,
                "role": task.role,
                "pdca_phase": task.pdca_phase,
                "start_time": current_time.strftime("%Y-%m-%d %H:%M"),
                "end_time": end_time.strftime("%Y-%m-%d %H:%M"),
                "duration_hours": duration_hours
            })
            
            current_time = end_time
        
        total_duration = (current_time - start_date).total_seconds() / 3600
        
        return {
            "project_name": blueprint.name,
            "start_date": start_date.strftime("%Y-%m-%d %H:%M"),
            "end_date": current_time.strftime("%Y-%m-%d %H:%M"),
            "total_duration_hours": round(total_duration, 1),
            "tasks": schedule
        }
    
    def compare_estimates(self, blueprint: Blueprint, 
                         actual_hours: Dict[str, float]) -> Dict[str, Any]:
        """
        对比估算与实际
        
        Args:
            blueprint: 项目蓝图
            actual_hours: 实际工时 {任务名: 实际工时}
            
        Returns:
            对比分析
        """
        comparisons = []
        total_estimated = 0.0
        total_actual = 0.0
        
        for task in blueprint.tasks:
            task_name = task.name
            estimated = task.estimated_hours
            actual = actual_hours.get(task_name, estimated)
            
            diff = actual - estimated
            diff_pct = (diff / estimated * 100) if estimated > 0 else 0
            
            comparisons.append({
                "task_name": task_name,
                "estimated": estimated,
                "actual": actual,
                "diff": round(diff, 1),
                "diff_pct": round(diff_pct, 1)
            })
            
            total_estimated += estimated
            total_actual += actual
        
        total_diff = total_actual - total_estimated
        total_diff_pct = (total_diff / total_estimated * 100) if total_estimated > 0 else 0
        
        # 偏差分析
        if abs(total_diff_pct) <= 10:
            accuracy = "准确"
        elif abs(total_diff_pct) <= 20:
            accuracy = "基本准确"
        else:
            accuracy = "偏差较大"
        
        return {
            "project_name": blueprint.name,
            "total_estimated": round(total_estimated, 1),
            "total_actual": round(total_actual, 1),
            "total_diff": round(total_diff, 1),
            "total_diff_pct": round(total_diff_pct, 1),
            "accuracy": accuracy,
            "task_comparisons": comparisons
        }
