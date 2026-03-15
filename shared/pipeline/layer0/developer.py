"""
Layer 0: 开发者工作器 (Developer Worker)
负责代码实现、Skill开发、功能开发
使用 GLM-5 模型
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from layer0.base import BaseRoleWorker, TaskResult
from layer0.ai_client import get_ai_client

logger = logging.getLogger(__name__)


class DeveloperWorker(BaseRoleWorker):
    """
    开发者工作器
    
    职责:
    1. Skill开发
    2. 功能实现
    3. 代码重构
    4. Bug修复
    5. 文档编写
    6. API实现
    
    使用模型: GLM-5 (alicloud/glm-5)
    
    能力标签:
    - coding: 编码实现
    - skill_development: Skill开发
    - refactoring: 代码重构
    - bug_fix: Bug修复
    - documentation: 文档编写
    - api_implementation: API实现
    """
    
    DEFAULT_CAPABILITIES = [
        "coding",
        "skill_development",
        "refactoring",
        "bug_fix",
        "documentation",
        "api_implementation"
    ]
    
    def __init__(self, layer1_api, workspace_dir: str = None, poll_interval: float = 5.0):
        """
        初始化开发者工作器
        
        Args:
            layer1_api: Layer 1 API 实例
            workspace_dir: 工作目录，默认使用 pipeline 目录
            poll_interval: 轮询间隔
        """
        super().__init__(
            role_id="developer",
            role_name="开发者",
            capabilities=self.DEFAULT_CAPABILITIES,
            layer1_api=layer1_api,
            poll_interval=poll_interval
        )
        
        # 设置工作目录
        if workspace_dir is None:
            workspace_dir = "/root/.openclaw/workspace/shared/pipeline"
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        
        self.ai_client = get_ai_client()
        logger.info(f"[{self.role_id}] 使用模型: alicloud/glm-5")
    
    def execute_task(self, task_data: Dict[str, Any]) -> TaskResult:
        """
        执行开发任务
        
        任务类型:
        - skill_creation: Skill开发
        - feature_implementation: 功能实现
        - code_refactoring: 代码重构
        - bug_fix: Bug修复
        - documentation: 文档编写
        - api_implementation: API实现
        """
        task_type = task_data.get("task_type", "feature_implementation")
        project_id = task_data.get("project_id", "unknown")
        
        logger.info(f"[Developer] 执行任务: {task_type} for {project_id}")
        
        try:
            # 构建任务描述
            task_description = self._build_task_description(task_data)
            
            # 调用 AI
            ai_response = self.ai_client.call(
                role="developer",
                task_description=task_description,
                context={
                    "task_type": task_type,
                    "project_id": project_id,
                    "skill_name": task_data.get("skill_name"),
                    "feature_name": task_data.get("feature_name"),
                    "requirements": task_data.get("requirements")
                },
                model="glm-5",
                temperature=0.3,  # 代码生成用较低温度
                max_tokens=6000
            )
            
            if not ai_response["success"]:
                logger.error(f"[Developer] AI 调用失败: {ai_response.get('error')}")
                return TaskResult(
                    success=False,
                    error_message=ai_response.get("error", "AI 调用失败")
                )
            
            ai_output = ai_response["content"]
            
            # 根据任务类型处理输出
            if task_type == "skill_creation":
                return self._process_skill_creation(task_data, ai_output, ai_response)
            elif task_type == "feature_implementation":
                return self._process_feature_implementation(task_data, ai_output, ai_response)
            elif task_type == "api_implementation":
                return self._process_api_implementation(task_data, ai_output, ai_response)
            elif task_type == "bug_fix":
                return self._process_bug_fix(task_data, ai_output, ai_response)
            else:
                return self._process_generic(task_data, ai_output, ai_response)
            
        except Exception as e:
            logger.error(f"[Developer] 任务执行失败: {e}")
            return TaskResult(
                success=False,
                error_message=str(e)
            )
    
    def _build_task_description(self, task_data: Dict[str, Any]) -> str:
        """构建任务描述"""
        task_type = task_data.get("task_type", "feature_implementation")
        
        descriptions = {
            "skill_creation": self._build_skill_creation_prompt,
            "feature_implementation": self._build_feature_prompt,
            "code_refactoring": self._build_refactoring_prompt,
            "bug_fix": self._build_bugfix_prompt,
            "documentation": self._build_doc_prompt,
            "api_implementation": self._build_api_prompt
        }
        
        builder = descriptions.get(task_type, self._build_generic_prompt)
        return builder(task_data)
    
    def _build_skill_creation_prompt(self, task_data: Dict) -> str:
        """构建Skill创建提示词"""
        skill_name = task_data.get("skill_name", "my_skill")
        description = task_data.get("description", "")
        requirements = task_data.get("requirements", {})
        
        prompt = f"""请开发一个名为「{skill_name}」的OpenClaw Skill。

Skill描述: {description}

要求:
{json.dumps(requirements, ensure_ascii=False, indent=2)}

请生成完整的Skill代码，包括:
1. SKILL.md - Skill说明文档
2. __init__.py - 主要实现代码
3. config.json - 配置文件

代码要求:
- 遵循Python最佳实践
- 包含适当的错误处理
- 提供使用示例
- 包含必要的注释"""
        
        return prompt
    
    def _build_feature_prompt(self, task_data: Dict) -> str:
        """构建功能实现提示词"""
        feature_name = task_data.get("feature_name", "新功能")
        requirements = task_data.get("requirements", {})
        
        return f"""请实现功能「{feature_name}」。

需求:
{json.dumps(requirements, ensure_ascii=False, indent=2)}

请提供:
1. 完整的实现代码
2. 必要的单元测试
3. 使用示例
4. 实现说明"""
    
    def _build_api_prompt(self, task_data: Dict) -> str:
        """构建API实现提示词"""
        feature_name = task_data.get("feature_name", "API")
        requirements = task_data.get("requirements", {})
        
        return f"""请实现API「{feature_name}」。

API规范:
{json.dumps(requirements, ensure_ascii=False, indent=2)}

请提供:
1. API端点实现
2. 请求/响应模型
3. 错误处理
4. API文档"""
    
    def _build_refactoring_prompt(self, task_data: Dict) -> str:
        """构建重构提示词"""
        return f"""请对以下代码进行重构:

{task_data.get('description', '')}

重构目标:
{json.dumps(task_data.get('requirements', {}), ensure_ascii=False)}

请提供:
1. 重构后的代码
2. 重构说明
3. 改进点列表"""
    
    def _build_bugfix_prompt(self, task_data: Dict) -> str:
        """构建Bug修复提示词"""
        return f"""请修复以下Bug:

Bug描述: {task_data.get('description', '')}

相关信息:
{json.dumps(task_data.get('requirements', {}), ensure_ascii=False)}

请提供:
1. Bug原因分析
2. 修复方案
3. 修复后的代码
4. 预防措施"""
    
    def _build_doc_prompt(self, task_data: Dict) -> str:
        """构建文档编写提示词"""
        return f"""请编写技术文档:

主题: {task_data.get('description', '')}

要求:
{json.dumps(task_data.get('requirements', {}), ensure_ascii=False)}

请提供结构清晰、内容完整的技术文档。"""
    
    def _build_generic_prompt(self, task_data: Dict) -> str:
        """构建通用提示词"""
        return f"""请完成以下开发任务:

{task_data.get('description', '')}

需求:
{json.dumps(task_data.get('requirements', {}), ensure_ascii=False)}"""
    
    def _process_skill_creation(self, task_data: Dict, ai_output: str, ai_response: Dict) -> TaskResult:
        """处理Skill创建结果"""
        skill_name = task_data.get("skill_name", "my_skill")
        project_id = task_data.get("project_id", "unknown")
        
        # 创建Skill目录
        skill_dir = self.workspace_dir / "skills" / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        
        # 解析AI输出，提取各个文件
        files_created = []
        
        # 尝试提取代码块
        import re
        
        # 提取 SKILL.md
        skill_md = self._extract_code_block(ai_output, "markdown") or ai_output
        skill_md_path = skill_dir / "SKILL.md"
        skill_md_path.write_text(skill_md, encoding='utf-8')
        files_created.append(str(skill_md_path))
        
        # 提取 Python 代码
        python_code = self._extract_code_block(ai_output, "python")
        if python_code:
            init_path = skill_dir / "__init__.py"
            init_path.write_text(python_code, encoding='utf-8')
            files_created.append(str(init_path))
        
        # 提取 JSON 配置
        json_code = self._extract_code_block(ai_output, "json")
        if json_code:
            try:
                config = json.loads(json_code)
                config_path = skill_dir / "config.json"
                config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding='utf-8')
                files_created.append(str(config_path))
            except json.JSONDecodeError:
                pass
        
        return TaskResult(
            success=True,
            output={
                "task_type": "skill_creation",
                "skill_name": skill_name,
                "project_id": project_id,
                "files_created": len(files_created),
                "skill_dir": str(skill_dir)
            },
            artifacts={
                "skill_code": ai_output,
                "files_created": files_created,
                "model_used": ai_response.get("model"),
                "usage": ai_response.get("usage")
            }
        )
    
    def _process_feature_implementation(self, task_data: Dict, ai_output: str, ai_response: Dict) -> TaskResult:
        """处理功能实现结果"""
        feature_name = task_data.get("feature_name", "feature")
        
        return TaskResult(
            success=True,
            output={
                "task_type": "feature_implementation",
                "feature_name": feature_name,
                "code_generated": len(ai_output) > 100
            },
            artifacts={
                "implementation_code": ai_output,
                "model_used": ai_response.get("model"),
                "usage": ai_response.get("usage")
            }
        )
    
    def _process_api_implementation(self, task_data: Dict, ai_output: str, ai_response: Dict) -> TaskResult:
        """处理API实现结果"""
        return TaskResult(
            success=True,
            output={
                "task_type": "api_implementation",
                "api_name": task_data.get("feature_name", "api"),
                "implemented": True
            },
            artifacts={
                "api_code": ai_output,
                "model_used": ai_response.get("model"),
                "usage": ai_response.get("usage")
            }
        )
    
    def _process_bug_fix(self, task_data: Dict, ai_output: str, ai_response: Dict) -> TaskResult:
        """处理Bug修复结果"""
        return TaskResult(
            success=True,
            output={
                "task_type": "bug_fix",
                "fixed": True,
                "analysis": "请查看详细修复说明"
            },
            artifacts={
                "fix_code": ai_output,
                "model_used": ai_response.get("model"),
                "usage": ai_response.get("usage")
            }
        )
    
    def _process_generic(self, task_data: Dict, ai_output: str, ai_response: Dict) -> TaskResult:
        """处理通用任务结果"""
        return TaskResult(
            success=True,
            output={
                "task_type": task_data.get("task_type", "unknown"),
                "completed": True,
                "summary": ai_output[:200] + "..." if len(ai_output) > 200 else ai_output
            },
            artifacts={
                "output": ai_output,
                "model_used": ai_response.get("model"),
                "usage": ai_response.get("usage")
            }
        )
    
    def _extract_code_block(self, text: str, language: str) -> Optional[str]:
        """从文本中提取代码块"""
        import re
        
        # 匹配 ```language ... ``` 格式的代码块
        pattern = rf'```{language}\s*\n(.*?)```'
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        
        if match:
            return match.group(1).strip()
        
        # 如果没有特定语言标记，尝试匹配 ``` ... ```
        if language == "python":
            pattern = r'```\s*\n(.*?)```'
            matches = re.findall(pattern, text, re.DOTALL)
            for m in matches:
                # 寻找看起来像Python代码的块
                if 'def ' in m or 'import ' in m or 'class ' in m:
                    return m.strip()
        
        return None
