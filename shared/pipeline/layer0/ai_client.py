"""
AI 客户端模块
支持阿里百炼 API，为不同角色配置不同模型
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)


class AliyunAIClient:
    """
    阿里百炼 AI 客户端
    
    支持模型:
    - kimi-coding/k2p5 (架构师)
    - alicloud/glm-5 (开发者)
    - alicloud/qwen3.5-plus (测试员)
    """
    
    BASE_URL = "https://coding.dashscope.aliyuncs.com/v1/chat/completions"
    
    MODEL_MAPPING = {
        "kimi-k2.5": "kimi-k2.5",
        "glm-5": "glm-5",
        "qwen3.5-plus": "qwen3.5-plus"
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 AI 客户端
        
        Args:
            api_key: 阿里百炼 API Key，默认从环境变量获取
        """
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            logger.warning("DASHSCOPE_API_KEY 未设置，AI 功能将不可用")
        
        self.system_prompts = self._load_system_prompts()
    
    def _load_system_prompts(self) -> Dict[str, str]:
        """加载各角色的系统提示词"""
        return {
            "architect": """你是资深的系统架构师，拥有15年以上的架构设计经验。

职责:
1. 系统架构设计 - 设计可扩展、高可用的系统架构
2. API设计 - 设计清晰、一致的接口
3. 技术选型 - 选择合适的技术栈
4. 模块划分 - 合理拆分系统模块

设计原则:
- 优先考虑可维护性和可扩展性
- 关注性能瓶颈和安全风险
- 提供清晰的架构图和数据流说明
- 给出具体的技术方案，而非泛泛而谈

输出要求:
- 结构化的设计文档
- 具体的技术选型理由
- 潜在的架构风险及缓解方案""",

            "developer": """你是资深的全栈开发者，精通Python、TypeScript等多种语言。

职责:
1. Skill开发 - 开发可复用的工具组件
2. 功能实现 - 实现具体的业务功能
3. 代码重构 - 优化现有代码结构
4. 文档编写 - 编写清晰的技术文档

编码原则:
- 代码简洁、可读性强
- 遵循PEP8等编码规范
- 添加适当的错误处理和日志
- 编写单元测试

输出要求:
- 完整的、可直接运行的代码
- 必要的注释说明
- 使用示例
- 依赖清单""",

            "tester": """你是资深的QA工程师，精通各种测试方法和工具。

职责:
1. 测试用例设计 - 设计全面的测试用例
2. 功能测试 - 验证功能正确性
3. 集成测试 - 验证模块间协作
4. 质量报告 - 生成测试报告

测试原则:
- 覆盖正常路径和异常路径
- 关注边界条件
- 考虑性能和安全测试
- 自动化优先

输出要求:
- 结构化的测试用例
- 清晰的测试步骤和预期结果
- 测试覆盖度分析
- 缺陷报告（如有）""",

            "auditor": """你是资深的代码审计与安全专家，精通Python代码安全分析、漏洞检测和安全最佳实践。

职责:
1. 安全漏洞扫描 - SQL注入、XSS、命令注入、路径遍历、不安全的反序列化等
2. 代码质量审计 - 代码规范、异常处理、日志记录、边界条件
3. 敏感信息检测 - API密钥、密码、令牌等硬编码检测
4. 依赖安全 - 检查不安全的第三方库使用
5. 架构风险 - 识别架构层面的安全隐患

审计原则:
- 严格遵循安全最佳实践（OWASP、CWE标准）
- 提供具体的代码位置和修复建议
- 按严重程度分级：Critical/High/Medium/Low
- 不仅发现问题，还要提供修复代码示例

输出要求:
- 结构化的审计报告，包含发现的问题清单
- 每个问题包含：位置、严重程度、问题描述、修复建议、修复代码
- 总体安全评分和改进建议
- 优先级排序的修复清单"""
        }
    
    def call(self, 
             role: str, 
             task_description: str, 
             context: Optional[Dict] = None,
             model: Optional[str] = None,
             temperature: float = 0.7,
             max_tokens: int = 4000) -> Dict[str, Any]:
        """
        调用 AI 模型
        
        Args:
            role: 角色类型 (architect/developer/tester)
            task_description: 任务描述
            context: 额外的上下文信息
            model: 指定模型，默认根据角色选择
            temperature: 温度参数
            max_tokens: 最大输出token数
            
        Returns:
            包含响应结果的字典
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "API Key 未配置",
                "content": None
            }
        
        # 选择模型
        if model is None:
            model = self._select_model_by_role(role)
        else:
            model = self.MODEL_MAPPING.get(model, model)
        
        # 构建消息
        system_prompt = self.system_prompts.get(role, "你是专业的软件工程师。")
        user_prompt = self._build_user_prompt(task_description, context)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # 构建请求
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = self._make_request(payload)
            return {
                "success": True,
                "content": response["choices"][0]["message"]["content"],
                "usage": response.get("usage", {}),
                "model": model
            }
        except Exception as e:
            logger.error(f"AI 调用失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "content": None
            }
    
    def _select_model_by_role(self, role: str) -> str:
        """根据角色选择默认模型"""
        role_model_map = {
            "architect": self.MODEL_MAPPING["kimi-k2.5"],
            "developer": self.MODEL_MAPPING["glm-5"],
            "tester": self.MODEL_MAPPING["qwen3.5-plus"]
        }
        return role_model_map.get(role, self.MODEL_MAPPING["glm-5"])
    
    def _build_user_prompt(self, task_description: str, context: Optional[Dict]) -> str:
        """构建用户提示词"""
        prompt = f"任务描述:\n{task_description}\n"
        
        if context:
            prompt += "\n上下文信息:\n"
            for key, value in context.items():
                if isinstance(value, (dict, list)):
                    prompt += f"- {key}: {json.dumps(value, ensure_ascii=False)}\n"
                else:
                    prompt += f"- {key}: {value}\n"
        
        prompt += "\n请按要求完成任务，并输出结构化的结果。"
        return prompt
    
    def _make_request(self, payload: Dict) -> Dict:
        """发送 HTTP 请求"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = json.dumps(payload).encode('utf-8')
        request = urllib.request.Request(
            self.BASE_URL,
            data=data,
            headers=headers,
            method='POST'
        )
        
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode('utf-8'))


# 全局 AI 客户端实例
_ai_client: Optional[AliyunAIClient] = None


def get_ai_client() -> AliyunAIClient:
    """获取全局 AI 客户端实例"""
    global _ai_client
    if _ai_client is None:
        _ai_client = AliyunAIClient()
    return _ai_client


def set_ai_client(client: AliyunAIClient):
    """设置全局 AI 客户端实例"""
    global _ai_client
    _ai_client = client
