#!/usr/bin/env python3
"""
智能模型路由器

根据任务类型和复杂度自动选择最优模型：
- 编码任务: MiniMax M2.5 (快速) / GLM-5 (复杂)
- 对话任务: Qwen 3.5 Plus (快速) / Kimi 2.5 (复杂)

支持手动声明切换模型。
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# 从统一配置导入
try:
    from config import (
        ALICLOUD_MODEL_FAST,
        ALICLOUD_MODEL_COMPLEX,
        ALICLOUD_MODEL_CHAT_FAST,
        ALICLOUD_MODEL_CHAT_COMPLEX,
        MODEL_MAPPING
    )
except ImportError:
    # 降级处理
    ALICLOUD_MODEL_FAST = os.environ.get('ALICLOUD_MODEL_FAST', 'MiniMax-M2.5')
    ALICLOUD_MODEL_COMPLEX = os.environ.get('ALICLOUD_MODEL_COMPLEX', 'glm-5')
    ALICLOUD_MODEL_CHAT_FAST = os.environ.get('ALICLOUD_MODEL_CHAT_FAST', 'qwen3.5-plus')
    ALICLOUD_MODEL_CHAT_COMPLEX = os.environ.get('ALICLOUD_MODEL_CHAT_COMPLEX', 'kimi-2.5')


class TaskType(Enum):
    """任务类型"""
    CODING = "coding"
    CHAT = "chat"
    UNKNOWN = "unknown"


class TaskComplexity(Enum):
    """任务复杂度"""
    FAST = "fast"
    COMPLEX = "complex"


@dataclass
class ModelConfig:
    """模型配置"""
    name: str
    model_id: str
    role: str
    strengths: List[str]
    context_window: int
    speed: str


# 模型配置
MODELS = {
    "MiniMax-M2.5": ModelConfig(
        name="MiniMax M2.5",
        model_id=ALICLOUD_MODEL_FAST,
        role="快速编码专家",
        strengths=["代码修复", "业务流程编码", "自动化任务", "高吞吐量"],
        context_window=204800,
        speed="快 (100 token/s)"
    ),
    "glm-5": ModelConfig(
        name="GLM-5",
        model_id=ALICLOUD_MODEL_COMPLEX,
        role="架构设计专家",
        strengths=["代码review", "架构设计", "边界处理", "复杂任务"],
        context_window=128000,
        speed="中等"
    ),
    "qwen3.5-plus": ModelConfig(
        name="Qwen 3.5 Plus",
        model_id=ALICLOUD_MODEL_CHAT_FAST,
        role="快速对话助手",
        strengths=["简单对话", "多模态理解", "快速响应", "日常问答"],
        context_window=32000,
        speed="快"
    ),
    "kimi-2.5": ModelConfig(
        name="Kimi 2.5",
        model_id=ALICLOUD_MODEL_CHAT_COMPLEX,
        role="深度思考专家",
        strengths=["复杂逻辑", "超长文本", "哲学讨论", "深刻洞悉", "复杂多模态"],
        context_window=200000,
        speed="较慢"
    )
}


class ModelRouter:
    """模型路由器"""
    
    def __init__(self):
        self.task_keywords = {
            TaskType.CODING: [
                '代码', 'coding', 'programming', 'function', 'class', 'def ',
                'bug', '修复', 'debug', 'error', 'exception', 'traceback',
                'git', 'commit', 'push', 'pull', 'merge', 'branch',
                '架构', 'architecture', 'refactor', '重构', '设计模式',
                '优化', 'performance', 'memory', 'leak', '并发', 'async',
                'api', '接口', 'endpoint', 'route', 'handler',
                '数据库', 'database', 'sql', 'query', 'migration',
                '测试', 'test', 'unittest', 'pytest', 'coverage',
                '部署', 'deploy', 'ci/cd', 'pipeline', 'docker',
                'python', 'javascript', 'java', 'rust', 'go', 'cpp',
                'review', 'pr', '代码审查', '代码质量', 'codereview',
                '分析代码', '代码逻辑', '机制实现',
                'microservice', '微服务', '高并发', 'high concurrency',
                '遗留系统', 'legacy', '重构', '高可用', '分布式',
                '定时任务', 'crontab', 'cron', '定时器', 'scheduler',
                '配置', 'config', 'setup', 'install', '部署服务',
                '脚本', 'script', 'shell', 'bash', '命令行',
                '环境变量', 'env', 'settings', 'yaml', 'json配置',
                '系统设置', '服务启动', '后台运行', 'daemon',
                '日志', 'log', '监控', 'alert', '报警',
                '备份', 'backup', '迁移', 'migration', 'upgrade',
            ],
            TaskType.CHAT: [
                '你好', 'hello', 'hi', '在吗', '请问',
                '解释', 'explain', '什么是', 'how to', '为什么',
                '建议', 'suggest', 'recommend', 'advice',
                '讨论', 'discuss', 'debate', 'opinion',
                '哲学', 'philosophy', '思考', 'meaning',
                '情感', 'emotion', '感受', 'feeling',
                '创意', 'creative', '想法', 'idea',
                '总结', 'summarize', '概括', 'conclusion',
                '翻译', 'translate', '语言', 'language'
            ]
        }
        
        self.complexity_indicators = {
            TaskComplexity.COMPLEX: [
                '复杂', 'complex', 'complicated', 'sophisticated',
                '深度', 'deep', '深入', 'profound', 'insight',
                '架构', 'architecture', 'design', 'system',
                '哲学', 'philosophy', '思考', 'thinking',
                '自由意志', 'free will', '存在', 'existence',
                '长文本', 'long context', '大量', 'massive',
                '多模态', 'multimodal', '图像', 'video', 'audio',
                '边界', 'edge case', 'corner case', '极端',
                '多次', 'multiple', '迭代', 'iterate',
                '完整', 'complete', '全面', 'comprehensive',
                '详细', 'detailed', '详尽', 'elaborate',
                '长期', 'long-term', '影响', 'implication',
                '分析', 'analyze', '探讨', 'explore',
                '质量', 'quality', '高并发', 'high concurrency', '分布式', 'distributed'
            ],
            TaskComplexity.FAST: [
                '简单', 'simple', 'quick', '快速', 'fast',
                '基础', 'basic', '入门', 'intro',
                '示例', 'example', 'demo', 'sample',
                '是/否', 'yes/no', '二选一',
                '一句话', 'one sentence', '简短', 'brief'
            ]
        }
    
    def detect_manual_override(self, prompt: str) -> Optional[Tuple[str, ModelConfig, str]]:
        """检测用户手动声明切换模型"""
        prompt_lower = prompt.lower()
        
        manual_patterns = [
            (['使用minimax', '用minimax', '切换minimax', '/model minimax'], 'MiniMax-M2.5', '手动指定: MiniMax M2.5'),
            (['使用glm', '用glm', '切换glm', '/model glm', '使用glm-5', '用glm-5'], 'glm-5', '手动指定: GLM-5'),
            (['使用qwen', '用qwen', '切换qwen', '/model qwen', '使用通义', '用通义'], 'qwen3.5-plus', '手动指定: Qwen 3.5 Plus'),
            (['使用kimi', '用kimi', '切换kimi', '/model kimi'], 'kimi-2.5', '手动指定: Kimi 2.5'),
        ]
        
        for keywords, model_key, reasoning in manual_patterns:
            if any(kw in prompt_lower for kw in keywords):
                config = MODELS[model_key]
                return config.model_id, config, reasoning
        
        return None
    
    def detect_link_intent(self, prompt: str) -> Tuple[TaskType, TaskComplexity, str]:
        """检测链接分享意图"""
        prompt_lower = prompt.lower()
        
        deep_keywords = ['讨论', '分析', '解读', '评价', '看法', '观点', '深度', '深刻', '思考', '哲学']
        tool_keywords = ['学习', '了解', '工具', '使用', '怎么用', '教程', '试用', '体验']
        
        deep_score = sum(1 for kw in deep_keywords if kw in prompt_lower)
        tool_score = sum(1 for kw in tool_keywords if kw in prompt_lower)
        
        if 'github.com' in prompt_lower and ('讨论' in prompt or '分析' in prompt):
            return TaskType.CHAT, TaskComplexity.COMPLEX, "GitHub链接+讨论 -> Kimi 2.5"
        
        if '怎么看' in prompt or '你觉得' in prompt or '如何理解' in prompt:
            return TaskType.CHAT, TaskComplexity.COMPLEX, "询问观点 -> Kimi 2.5"
        
        if '试试' in prompt or '用一下' in prompt or '体验一下' in prompt:
            return TaskType.CHAT, TaskComplexity.FAST, "尝试使用 -> Qwen 3.5 Plus"
        
        if deep_score > tool_score and deep_score >= 2:
            return TaskType.CHAT, TaskComplexity.COMPLEX, "深度创作/讨论 -> Kimi 2.5"
        elif tool_score > deep_score:
            return TaskType.CHAT, TaskComplexity.FAST, "工具学习 -> Qwen 3.5 Plus"
        
        return TaskType.CHAT, TaskComplexity.COMPLEX, "默认深度讨论 -> Kimi 2.5"
    
    def detect_task_type(self, prompt: str) -> TaskType:
        """检测任务类型"""
        prompt_lower = prompt.lower()
        
        explicit_coding = ['定时任务', 'crontab', '部署服务', '写个脚本', 'shell脚本', 'python脚本', '部署']
        if any(kw in prompt for kw in explicit_coding):
            return TaskType.CODING
        
        explanation_patterns = ['快速解释', '简单解释', '解释一下', '什么是']
        if any(p in prompt for p in explanation_patterns) and not any(c in prompt_lower for c in ['bug', '修复', '代码']):
            return TaskType.CHAT
        
        coding_score = sum(1 for kw in self.task_keywords[TaskType.CODING] if kw in prompt_lower)
        chat_score = sum(1 for kw in self.task_keywords[TaskType.CHAT] if kw in prompt_lower)
        
        if '架构' in prompt or 'architecture' in prompt_lower:
            coding_score += 3
        
        if coding_score > chat_score and coding_score >= 2:
            return TaskType.CODING
        elif chat_score > coding_score:
            return TaskType.CHAT
        
        if any(ext in prompt for ext in ['.py', '.js', '.java', '.rs', '.go']):
            return TaskType.CODING
        
        return TaskType.CHAT
    
    def detect_complexity(self, prompt: str) -> TaskComplexity:
        """检测任务复杂度"""
        prompt_lower = prompt.lower()
        
        fast_fix_keywords = ['修复bug', 'fix bug', 'debug', '报错', '帮我debug']
        if any(kw in prompt_lower for kw in fast_fix_keywords):
            return TaskComplexity.FAST
        
        complex_score = sum(1 for kw in self.complexity_indicators[TaskComplexity.COMPLEX] if kw in prompt_lower)
        fast_score = sum(1 for kw in self.complexity_indicators[TaskComplexity.FAST] if kw in prompt_lower)
        
        if len(prompt) > 5000:
            complex_score += 2
        elif len(prompt) > 2000:
            complex_score += 1
        
        if complex_score > fast_score:
            return TaskComplexity.COMPLEX
        return TaskComplexity.FAST
    
    def select_model(self, prompt: str, preferred_task: TaskType = None, has_link: bool = False) -> Tuple[str, ModelConfig, str]:
        """选择最优模型"""
        # 第1优先级：手动声明
        manual_override = self.detect_manual_override(prompt)
        if manual_override:
            return manual_override
        
        # 第2优先级：链接分享
        if has_link:
            task_type, complexity, link_reasoning = self.detect_link_intent(prompt)
            if complexity == TaskComplexity.COMPLEX:
                model_key = "kimi-2.5"
            else:
                model_key = "qwen3.5-plus"
            config = MODELS[model_key]
            return config.model_id, config, f"链接分享: {link_reasoning}"
        
        # 第3优先级：自动检测
        if preferred_task:
            task_type = preferred_task
        else:
            task_type = self.detect_task_type(prompt)
        
        complexity = self.detect_complexity(prompt)
        
        if task_type == TaskType.CODING:
            if complexity == TaskComplexity.FAST:
                model_key = "MiniMax-M2.5"
                reasoning = f"编码任务+快速 -> MiniMax M2.5"
            else:
                model_key = "glm-5"
                reasoning = f"编码任务+复杂 -> GLM-5"
        else:
            if complexity == TaskComplexity.FAST:
                model_key = "qwen3.5-plus"
                reasoning = f"对话任务+快速 -> Qwen 3.5 Plus"
            else:
                model_key = "kimi-2.5"
                reasoning = f"对话任务+复杂 -> Kimi 2.5"
        
        config = MODELS[model_key]
        return config.model_id, config, reasoning
    
    def get_system_prompt(self, model_key: str) -> str:
        """获取系统提示词"""
        prompts = {
            "MiniMax-M2.5": "你是资深代码修复专家，专注快速定位问题、高效生成修复代码。",
            "glm-5": "你是资深软件架构师，专注复杂代码设计、架构优化、边界条件处理。",
            "qwen3.5-plus": "你是智能对话助手，擅长快速理解问题、简洁回答。",
            "kimi-2.5": "你是深度思考专家，擅长复杂逻辑分析、哲学思辨、深度洞察。"
        }
        return prompts.get(model_key, "你是一个AI助手。")


router = ModelRouter()


def select_model_for_prompt(prompt: str, task_type: str = None, has_link: bool = False) -> Dict:
    """为提示词选择模型"""
    preferred = None
    if task_type == 'coding':
        preferred = TaskType.CODING
    elif task_type == 'chat':
        preferred = TaskType.CHAT
    
    model_id, config, reasoning = router.select_model(prompt, preferred, has_link=has_link)
    
    return {
        'model_id': model_id,
        'model_name': config.name,
        'role': config.role,
        'strengths': config.strengths,
        'speed': config.speed,
        'reasoning': reasoning,
        'system_prompt': router.get_system_prompt(config.model_id)
    }


if __name__ == "__main__":
    test_prompts = [
        ("修复Python代码bug", None, False),
        ("设计微服务架构", None, False),
        ("你好", None, False),
        ("分析AI哲学意义", None, False),
        ("https://xxx 讨论", None, True),
        ("https://xxx 试用工具", None, True),
        ("使用MiniMax写排序", None, False),
        ("用GLM设计架构", None, False),
        ("使用Qwen解释", None, False),
        ("用Kimi深度讨论", None, False),
    ]
    
    print("=== 模型路由测试 ===\n")
    for prompt, task_type, has_link in test_prompts:
        result = select_model_for_prompt(prompt, task_type, has_link)
        
        tag = ""
        if has_link:
            tag = "[链接] "
        elif any(kw in prompt.lower() for kw in ['使用', '用']):
            tag = "[手动] "
        
        print(f"{tag}{prompt}")
        print(f"   -> {result['model_name']}")
        print(f"   原因: {result['reasoning']}")
        print()
