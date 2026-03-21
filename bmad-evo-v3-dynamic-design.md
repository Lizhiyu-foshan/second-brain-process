# BMAD-EVO v3.0 全动态智能生成系统设计

## 核心原则

> **零硬编码，全模型驱动**
> 
> 任务类型、复杂度、角色、模型全部由AI分析决策，根据实际需要动态调整。

---

## 系统架构

```
用户输入
    ↓
【智能任务分析器】TaskAnalyzer (调用模型)
    ├── 任务类型识别 (自然语言描述)
    ├── 复杂度评估 (1-10分)
    ├── 建议角色数量 (基于复杂度)
    └── 关键技能需求
    ↓
【动态角色生成器】DynamicRoleGenerator (调用模型)
    ├── 根据类型+复杂度生成角色列表
    ├── 为每个角色定义职责
    ├── 分配执行顺序
    └── 标记可并行角色
    ↓
【模型路由器】ModelRouter (调用模型选择)
    ├── 为每个角色选择最优模型
    ├── 备选模型配置
    └── 失败回退策略
    ↓
执行流程
```

---

## 核心组件设计

### 1. TaskAnalyzer - 智能任务分析器

```python
class TaskAnalyzer:
    """
    智能任务分析器
    调用模型分析任务类型、复杂度和资源需求
    """
    
    PRIMARY_MODEL = "alibaba/qwen3.5-plus"  # 主分析模型
    FALLBACK_MODEL = "kimi-coding/k2p5"      # 失败回退
    
    def analyze(self, task_description: str) -> TaskAnalysis:
        """
        分析任务，返回结构化分析结果
        """
        prompt = f"""你是一个智能任务分析助手。请分析以下开发任务：

## 任务描述
{task_description}

## 分析要求
请从以下维度分析这个任务：

1. **任务类型识别**
   - 从 [全栈应用开发, 后端模块开发, 复杂技术问题解决, 技术写作, 数据分析] 中选择最匹配的类型
   - 给出选择理由
   - 如果有混合类型，说明主次

2. **复杂度评估** (1-10分)
   - 1-3分：简单，单一功能，技术栈简单
   - 4-6分：中等，多个功能模块，标准技术栈
   - 7-10分：复杂，大规模系统，高并发/分布式/复杂算法
   
   评估维度：
   - 功能复杂度
   - 技术难度
   - 集成复杂度
   - 风险程度

3. **建议角色数量**
   - 基于复杂度，建议需要多少AI角色协作
   - 简单(1-3分)：1-2个角色
   - 中等(4-6分)：3-5个角色  
   - 复杂(7-10分)：6-9个角色

4. **关键技能需求**
   - 列出完成任务所需的关键技能
   - 如：API设计、数据库设计、前端框架、算法优化等

5. **特殊考虑**
   - 是否有特殊要求？（性能、安全、兼容性等）
   - 是否有高风险操作？

## 输出格式 (JSON)
```json
{{
  "task_type": "后端模块开发",
  "task_type_reason": "这是一个API服务开发任务...",
  "complexity_score": 4,
  "complexity_assessment": "中等复杂度，因为...",
  "recommended_role_count": 4,
  "key_skills": ["API设计", "错误处理", "日志记录"],
  "special_considerations": ["需要高并发支持"],
  "risks": ["API变更可能影响下游"]
}}
```

只输出JSON，不要其他内容。"""

        # 尝试主模型
        try:
            result = self._call_model(self.PRIMARY_MODEL, prompt)
            return self._parse_analysis(result)
        except Exception as e:
            logger.warning(f"主模型分析失败: {e}，回退到{k2p5}")
            # 回退到k2.5
            result = self._call_model(self.FALLBACK_MODEL, prompt)
            return self._parse_analysis(result)
```

### 2. DynamicRoleGenerator - 动态角色生成器

```python
class DynamicRoleGenerator:
    """
    动态角色生成器
    根据任务分析结果，动态生成最适合的角色流程
    """
    
    PRIMARY_MODEL = "alibaba/qwen3.5-plus"
    FALLBACK_MODEL = "kimi-coding/k2p5"
    
    def generate_roles(self, task_description: str, analysis: TaskAnalysis) -> RoleFlow:
        """
        动态生成角色流程
        """
        prompt = f"""你是一个专业的软件开发团队规划师。

## 任务描述
{task_description}

## 任务分析
- 类型: {analysis.task_type}
- 复杂度: {analysis.complexity_score}/10
- 建议角色数: {analysis.recommended_role_count}
- 关键技能: {', '.join(analysis.key_skills)}

## 角色生成要求

请为这个任务设计最优的AI角色协作流程。

**原则：**
1. 不要为了流程而设定流程，只设计必要的角色
2. 简单任务(1-3分)可能只需要1-2个角色
3. 中等任务(4-6分)需要3-5个角色
4. 复杂任务(7-10分)才需要完整流程
5. 角色之间要有清晰的输入输出关系
6. 可以并行的角色要标记出来

**示例：**

简单API开发(复杂度3)的最小角色：
- 需求理解+设计 (1个角色)
- 开发实现 (1个角色)

复杂电商平台(复杂度8)的完整角色：
- 需求分析师
- 产品设计师
- 架构师
- 数据库设计师
- 前端开发
- 后端开发 (可与前端并行)
- 安全专家
- 测试工程师
- 部署工程师

## 输出格式 (JSON)
```json
{{
  "roles": [
    {{
      "name": "需求设计师",
      "title": "需求分析与设计师",
      "description": "理解需求并设计解决方案",
      "responsibilities": ["需求分析", "接口设计", "数据模型设计"],
      "input_from": [],  // 第一个角色无输入
      "output_to": ["开发工程师"],
      "can_parallel": false,
      "estimated_time": "10-15分钟",
      "model_requirement": "强逻辑推理能力，代码理解"
    }},
    {{
      "name": "开发工程师",
      "title": "全栈开发工程师",
      "description": "实现完整功能",
      "responsibilities": ["代码实现", "单元测试", "文档注释"],
      "input_from": ["需求设计师"],
      "output_to": [],
      "can_parallel": false,
      "estimated_time": "20-30分钟",
      "model_requirement": "强代码能力，工程经验"
    }}
  ],
  "execution_order": ["需求设计师", "开发工程师"],
  "parallel_groups": [],  // 无可并行角色
  "total_roles": 2,
  "rationale": "这是一个简单API开发任务，只需2个角色：一个负责设计，一个负责实现"
}}
```

只输出JSON，不要其他内容。"""

        try:
            result = self._call_model(self.PRIMARY_MODEL, prompt, timeout=120)
            return self._parse_roles(result)
        except Exception as e:
            logger.warning(f"主模型角色生成失败: {e}，回退到k2.5")
            result = self._call_model(self.FALLBACK_MODEL, prompt, timeout=120)
            return self._parse_roles(result)
```

### 3. ModelRouter - 模型智能路由器

```python
class ModelRouter:
    """
    模型智能路由器
    为每个角色选择最适合的模型，并配置失败回退
    """
    
    # 可用模型池
    MODEL_POOL = {
        "coding": [
            ("kimi-coding/k2p5", "首选"),
            ("anthropic/claude-sonnet-4", "备选1"),
            ("google/gemini-3-pro", "备选2"),
        ],
        "reasoning": [
            ("zhipu/glm-5", "首选"),
            ("alibaba/qwen3.5-plus", "备选1"),
            ("deepseek/deepseek-chat", "备选2"),
        ],
        "qa": [
            ("alibaba/qwen3.5-plus", "首选"),
            ("kimi-coding/k2p5", "备选"),
        ]
    }
    
    def select_model_for_role(self, role: RoleDefinition) -> ModelConfig:
        """
        为角色选择模型
        """
        prompt = f"""为以下AI角色选择最适合的模型：

## 角色信息
- 名称: {role.title}
- 职责: {', '.join(role.responsibilities)}
- 模型要求: {role.model_requirement}

## 可用模型
1. kimi-coding/k2.5 - 代码能力强，适合开发任务
2. zhipu/glm-5 - 逻辑推理强，适合设计任务
3. alibaba/qwen3.5-plus - 速度快成本低，适合QA/审查
4. anthropic/claude-sonnet-4 - 综合能力均衡
5. google/gemini-3-pro - 长上下文，适合复杂分析

## 输出格式 (JSON)
```json
{{
  "primary_model": "kimi-coding/k2.5",
  "primary_reason": "该角色主要负责代码实现，需要强代码能力",
  "fallback_model": "anthropic/claude-sonnet-4",
  "fallback_reason": "备选模型，代码能力同样出色"
}}
```

只输出JSON。"""

        try:
            result = self._call_model("alibaba/qwen3.5-plus", prompt, timeout=30)
            config = self._parse_model_selection(result)
            return ModelConfig(
                primary=config["primary_model"],
                fallback=config["fallback_model"],
                timeout=self._estimate_timeout(role)
            )
        except Exception as e:
            # 失败时使用默认配置
            logger.warning(f"模型选择失败，使用默认: {e}")
            return ModelConfig(
                primary="kimi-coding/k2p5",
                fallback="kimi-coding/k2p5",
                timeout=300
            )
```

---

## 完整执行流程示例

### 示例1: 简单数据处理任务

**用户输入**: "帮我清洗一个CSV文件，删除空行和重复数据"

**TaskAnalyzer分析**:
```json
{
  "task_type": "数据分析",
  "complexity_score": 2,
  "recommended_role_count": 2,
  "key_skills": ["数据清洗", "Python/Pandas"],
  "rationale": "简单的数据清洗任务，标准化操作"
}
```

**DynamicRoleGenerator生成**:
```json
{
  "roles": [
    {
      "name": "数据分析师",
      "title": "数据清洗分析师",
      "description": "分析数据质量并制定清洗策略",
      "responsibilities": ["数据探查", "质量分析", "清洗策略"],
      "estimated_time": "5分钟"
    },
    {
      "name": "数据工程师",
      "title": "数据清洗工程师", 
      "description": "执行数据清洗并验证结果",
      "responsibilities": ["代码实现", "数据清洗", "结果验证"],
      "estimated_time": "10分钟"
    }
  ],
  "rationale": "简单数据清洗只需2个角色：分析+执行"
}
```

**ModelRouter分配**:
- 数据分析师: GLM-5 (推理)
- 数据工程师: K2.5 (代码)

### 示例2: 复杂全栈应用

**用户输入**: "开发一个电商平台，包含用户系统、商品管理、购物车、支付集成、订单管理，支持高并发"

**TaskAnalyzer分析**:
```json
{
  "task_type": "全栈应用开发",
  "complexity_score": 8,
  "recommended_role_count": 7,
  "key_skills": ["分布式架构", "数据库设计", "支付集成", "高并发", "安全防护"],
  "special_considerations": ["高并发", "支付安全", "数据一致性"],
  "risks": ["支付安全", "性能瓶颈"]
}
```

**DynamicRoleGenerator生成**:
```json
{
  "roles": [
    {"name": "需求分析师", "title": "需求分析师"},
    {"name": "产品设计师", "title": "产品设计师"},
    {"name": "架构师", "title": "系统架构师"},
    {"name": "数据库设计师", "title": "数据库设计师"},
    {"name": "前端工程师", "title": "前端开发工程师", "can_parallel": true},
    {"name": "后端工程师", "title": "后端开发工程师", "can_parallel": true},
    {"name": "安全专家", "title": "安全架构师"},
    {"name": "测试工程师", "title": "测试工程师"},
    {"name": "部署工程师", "title": "DevOps工程师"}
  ],
  "parallel_groups": [["前端工程师", "后端工程师"]],
  "rationale": "复杂电商平台需要完整流程，前后端可并行开发"
}
```

---

## 失败回退策略

```python
class ResilientExecutor:
    """
    弹性执行器
    确保模型调用失败时有优雅回退
    """
    
    async def execute_with_fallback(self, role: RoleDefinition, context: str) -> AgentResult:
        """
        带失败回退的执行
        """
        models_to_try = [
            role.model_config.primary,
            role.model_config.fallback,
            "kimi-coding/k2p5",  # 终极回退
        ]
        
        last_error = None
        for model in models_to_try:
            try:
                logger.info(f"尝试使用模型: {model}")
                result = await self._execute_model(model, role, context)
                return AgentResult(
                    success=True,
                    output=result,
                    model_used=model
                )
            except Exception as e:
                logger.warning(f"模型 {model} 失败: {e}")
                last_error = e
                continue
        
        # 所有模型都失败
        return AgentResult(
            success=False,
            error=f"所有模型都失败: {last_error}",
            model_used="none"
        )
```

---

## 配置示例

```yaml
# .bmad/config.yaml

# 模型配置
models:
  primary_provider: "alibaba"  # 百炼
  fallback_provider: "moonshot"  # kimi
  
  # 模型优先级
  coding:
    - "kimi-coding/k2p5"
    - "anthropic/claude-sonnet-4"
  
  reasoning:
    - "zhipu/glm-5"
    - "alibaba/qwen3.5-plus"
  
  fast:
    - "alibaba/qwen3.5-plus"
    - "google/gemini-3-flash"

# 动态生成配置
dynamic_generation:
  enabled: true
  
  # 分析阶段模型
  analysis_model: "alibaba/qwen3.5-plus"
  analysis_timeout: 60
  
  # 角色生成模型
  role_generation_model: "alibaba/qwen3.5-plus"
  role_generation_timeout: 120
  
  # 失败回退
  fallback_model: "kimi-coding/k2p5"
  
  # 复杂度阈值
  complexity_thresholds:
    simple: {max: 3, max_roles: 2}
    medium: {max: 6, max_roles: 5}
    complex: {max: 10, max_roles: 9}
```

---

*设计版本：v3.0-全动态智能*
*日期：2026-03-21*
