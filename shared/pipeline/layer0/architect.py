"""
Layer 0: 架构师工作器 (Architect Worker)
负责架构设计、技术选型、API设计
使用 Kimi K2.5 模型
"""
import logging
import json
from typing import Dict, Any, List, Optional

from layer0.base import BaseRoleWorker, TaskResult
from layer0.ai_client import get_ai_client

logger = logging.getLogger(__name__)


class ArchitectWorker(BaseRoleWorker):
    """
    架构师工作器
    
    职责:
    1. 系统架构设计
    2. API接口设计
    3. 模块划分
    4. 技术选型
    5. 设计评审
    
    使用模型: Kimi K2.5 (kimi-coding/k2p5)
    
    能力标签:
    - architecture: 架构设计
    - design: 系统设计
    - tech_selection: 技术选型
    - planning: 规划
    - api_design: API设计
    """
    
    DEFAULT_CAPABILITIES = [
        "architecture",
        "design", 
        "tech_selection",
        "planning",
        "api_design",
        "module_design",
        "design_review"
    ]
    
    def __init__(self, layer1_api, poll_interval: float = 5.0):
        """初始化架构师工作器"""
        super().__init__(
            role_id="architect",
            role_name="架构师",
            capabilities=self.DEFAULT_CAPABILITIES,
            layer1_api=layer1_api,
            poll_interval=poll_interval
        )
        self.ai_client = get_ai_client()
        logger.info(f"[{self.role_id}] 使用模型: kimi-coding/k2p5")
    
    def execute_task(self, task_data: Dict[str, Any]) -> TaskResult:
        """
        执行架构任务
        
        任务类型:
        - system_design: 系统架构设计
        - api_design: API接口设计
        - module_design: 模块划分设计
        - tech_selection: 技术选型
        - design_review: 设计评审
        """
        task_type = task_data.get("task_type", "system_design")
        project_id = task_data.get("project_id", "unknown")
        
        logger.info(f"[Architect] 执行任务: {task_type} for {project_id}")
        
        try:
            # 构建任务描述
            task_description = self._build_task_description(task_data)
            
            # 调用 AI
            ai_response = self.ai_client.call(
                role="architect",
                task_description=task_description,
                context={
                    "task_type": task_type,
                    "project_id": project_id,
                    "project_name": task_data.get("project_name"),
                    "requirements": task_data.get("requirements")
                },
                model="kimi-k2.5",
                temperature=0.7,
                max_tokens=4000
            )
            
            if not ai_response["success"]:
                logger.error(f"[Architect] AI 调用失败: {ai_response.get('error')}")
                return TaskResult(
                    success=False,
                    error_message=ai_response.get("error", "AI 调用失败")
                )
            
            # 解析 AI 输出
            ai_output = ai_response["content"]
            
            # 构建结构化输出
            output = self._parse_ai_output(task_type, ai_output, task_data)
            
            return TaskResult(
                success=True,
                output=output,
                artifacts={
                    "design_document": output,
                    "raw_ai_response": ai_output,
                    "model_used": ai_response.get("model"),
                    "usage": ai_response.get("usage")
                }
            )
            
        except Exception as e:
            logger.error(f"[Architect] 任务执行失败: {e}")
            return TaskResult(
                success=False,
                error_message=str(e)
            )
    
    def _build_task_description(self, task_data: Dict[str, Any]) -> str:
        """构建任务描述"""
        task_type = task_data.get("task_type", "system_design")
        project_name = task_data.get("project_name", "未命名项目")
        requirements = task_data.get("requirements", {})
        
        descriptions = {
            "system_design": f"为项目「{project_name}」设计系统架构",
            "api_design": f"为项目「{project_name}」设计API接口",
            "module_design": f"为项目「{project_name}」进行模块划分",
            "tech_selection": f"为项目「{project_name}」进行技术选型",
            "design_review": f"评审项目「{project_name}」的设计方案"
        }
        
        description = descriptions.get(task_type, descriptions["system_design"])
        
        if requirements:
            description += f"\n\n需求:\n{json.dumps(requirements, ensure_ascii=False, indent=2)}"
        
        return description
    
    def _parse_ai_output(self, task_type: str, ai_output: str, task_data: Dict) -> Dict:
        """解析 AI 输出为结构化数据"""
        project_name = task_data.get("project_name", "未命名项目")
        project_id = task_data.get("project_id", "unknown")
        
        # 尝试从 AI 输出中提取结构化信息
        # 这里使用简单的规则，实际可以做得更智能
        
        if task_type == "system_design":
            return {
                "project_name": project_name,
                "architecture_style": self._extract_section(ai_output, "架构风格"),
                "components": self._extract_list(ai_output, "组件"),
                "data_flow": self._extract_section(ai_output, "数据流"),
                "integration_points": self._extract_list(ai_output, "集成点"),
                "scalability_considerations": self._extract_section(ai_output, "可扩展性"),
                "security_considerations": self._extract_section(ai_output, "安全性"),
                "design_summary": ai_output[:500] + "..." if len(ai_output) > 500 else ai_output
            }
        
        elif task_type == "api_design":
            return {
                "version": "1.0.0",
                "endpoints": self._extract_list(ai_output, "端点"),
                "data_models": self._extract_section(ai_output, "数据模型"),
                "authentication": self._extract_section(ai_output, "认证"),
                "error_handling": self._extract_section(ai_output, "错误处理"),
                "api_summary": ai_output[:500] + "..." if len(ai_output) > 500 else ai_output
            }
        
        elif task_type == "module_design":
            return {
                "modules": self._extract_list(ai_output, "模块"),
                "dependencies": self._extract_section(ai_output, "依赖"),
                "interfaces": self._extract_section(ai_output, "接口"),
                "module_summary": ai_output[:500] + "..." if len(ai_output) > 500 else ai_output
            }
        
        elif task_type == "tech_selection":
            return {
                "stack": self._extract_section(ai_output, "技术栈"),
                "justification": self._extract_section(ai_output, "选型理由"),
                "alternatives": self._extract_list(ai_output, "备选方案"),
                "risks": self._extract_list(ai_output, "风险"),
                "selection_summary": ai_output[:500] + "..." if len(ai_output) > 500 else ai_output
            }
        
        else:
            return {
                "task_type": task_type,
                "result": ai_output[:1000] + "..." if len(ai_output) > 1000 else ai_output
            }
    
    def _extract_section(self, text: str, section_name: str) -> str:
        """从文本中提取章节内容"""
        # 简单的章节提取逻辑
        lines = text.split('\n')
        result = []
        in_section = False
        
        for line in lines:
            if section_name in line and (':' in line or '：' in line or '#' in line):
                in_section = True
                continue
            
            if in_section:
                # 如果到达下一个章节，停止
                if line.strip() and (line.startswith('#') or 
                                     (':' in line and len(line.split(':')[0]) < 20)):
                    break
                result.append(line)
        
        return '\n'.join(result).strip() or f"请查看完整设计文档"
    
    def _extract_list(self, text: str, list_name: str) -> List[str]:
        """从文本中提取列表"""
        # 简单的列表提取逻辑
        lines = text.split('\n')
        result = []
        in_list = False
        
        for line in lines:
            if list_name in line and (':' in line or '：' in line or '#' in line):
                in_list = True
                continue
            
            if in_list:
                # 列表项通常以 - 或数字开头
                stripped = line.strip()
                if stripped.startswith('-') or stripped.startswith('*') or \
                   (len(stripped) > 2 and stripped[0].isdigit() and stripped[1] == '.'):
                    result.append(stripped.lstrip('- *').strip())
                elif stripped and not stripped.startswith('#'):
                    # 如果到达空行或新章节，停止
                    if not stripped[0].isalnum():
                        break
        
        return result or ["请查看完整设计文档"]
