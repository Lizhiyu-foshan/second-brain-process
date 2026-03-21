# BMAD-EVO 角色自动生成模块设计文档

## 1. 问题分析

### 当前限制
- **硬编码流程**：`analyst → pm → architect → development → qa → deployment`
- **固定角色**：7个预定义角色，无法适应不同任务类型
- **缺乏灵活性**：所有任务都走相同的软件开发流程

### 目标
- 根据任务类型自动生成参与角色
- 根据任务复杂度动态调整流程
- 支持多种任务类型：软件开发、文档编写、数据分析、调研报告等

---

## 2. 系统架构设计

### 2.1 新增模块

```
lib/
├── agent_executor.py           # 已有：Agent执行器
├── role_generator.py           # 新增：角色生成器核心
├── task_type_detector.py       # 新增：任务类型识别器
├── role_templates.py           # 新增：角色模板库
└── flow_optimizer.py           # 新增：流程优化器
```

### 2.2 核心组件

| 组件 | 职责 | 输入 | 输出 |
|------|------|------|------|
| TaskTypeDetector | 识别任务类型 | 用户原始需求 | TaskType + 置信度 |
| RoleTemplateLibrary | 管理角色模板 | 任务类型 | 角色模板列表 |
| RoleFlowGenerator | 生成角色流程 | 任务类型 + 复杂度 | 角色执行顺序 |
| DynamicAgentFactory | 创建Agent配置 | 角色定义 | AgentConfig |

---

## 3. 任务类型定义

### 3.1 支持的TaskType

```python
class TaskType(Enum):
    # 软件开发类
    WEB_APP = "web_app"              # Web应用开发
    API_SERVICE = "api_service"       # API服务开发
    CLI_TOOL = "cli_tool"             # 命令行工具
    MOBILE_APP = "mobile_app"         # 移动应用
    
    # 内容创作类
    TECH_DOC = "tech_doc"             # 技术文档编写
    BLOG_POST = "blog_post"           # 博客文章
    RESEARCH_REPORT = "research_report" # 调研报告
    
    # 数据分析类
    DATA_ANALYSIS = "data_analysis"   # 数据分析
    DATA_PIPELINE = "data_pipeline"   # 数据管道
    
    # 其他
    CODE_REVIEW = "code_review"       # 代码审查
    BUG_FIX = "bug_fix"               # Bug修复
    REFACTOR = "refactor"             # 代码重构
    
    # 通用
    GENERAL = "general"               # 通用任务（默认）
```

### 3.2 任务类型识别规则

| 关键词/模式 | 识别为 | 复杂度 |
|------------|--------|--------|
| "网站", "web", "前端", "页面" | WEB_APP | 根据功能点评估 |
| "API", "接口", "服务", "后端" | API_SERVICE | 根据接口数量评估 |
| "工具", "脚本", "cli", "命令行" | CLI_TOOL | 简单 |
| "文档", "说明", "guide", "tutorial" | TECH_DOC | 根据篇幅评估 |
| "博客", "文章", "post" | BLOG_POST | 中等 |
| "调研", "研究", "分析报告" | RESEARCH_REPORT | 高 |
| "数据分析", "可视化", "统计" | DATA_ANALYSIS | 根据数据量评估 |
| "审查", "review", "audit" | CODE_REVIEW | 中等 |
| "修复", "bug", "问题" | BUG_FIX | 简单 |
| "重构", "优化", "clean up" | REFACTOR | 中等 |

---

## 4. 角色模板设计

### 4.1 角色定义结构

```python
@dataclass
class RoleDefinition:
    """角色定义"""
    name: str                       # 角色标识名
    title: str                      # 角色显示名
    description: str                # 角色描述
    model: str                      # 使用的AI模型
    system_prompt: str              # 系统提示词
    required_skills: List[str]      # 所需技能
    input_context: List[str]        # 需要输入的上下文
    output_deliverable: str         # 输出交付物
    estimated_time: int             # 预计耗时(分钟)
    can_parallel: bool              # 是否可并行执行
```

### 4.2 任务类型-角色映射

#### WEB_APP 角色流程
```
需求分析师(requirement_analyst)
    ↓
产品设计师(product_designer)
    ↓
UI/UX设计师(ui_designer)
    ↓
架构师(architect)
    ↓
前端工程师(frontend_dev)
    ↓
后端工程师(backend_dev)
    ↓
测试工程师(qa_engineer)
    ↓
部署工程师(deployment_engineer)
```

#### TECH_DOC 角色流程
```
内容规划师(content_planner)
    ↓
技术作者(technical_writer)
    ↓
代码示例工程师(code_example_writer)
    ↓
文档审查员(doc_reviewer)
    ↓
格式优化师(format_optimizer)
```

#### DATA_ANALYSIS 角色流程
```
数据分析师(data_analyst)
    ↓
数据清洗工程师(data_cleaner) ←→ 可视化设计师(visual_designer)
    ↓
洞察提炼师(insight_extractor)
    ↓
报告撰写师(report_writer)
```

### 4.3 基础角色库

```python
BASE_ROLES = {
    # 分析类
    "requirement_analyst": RoleDefinition(...),
    "data_analyst": RoleDefinition(...),
    "content_planner": RoleDefinition(...),
    
    # 设计类
    "product_designer": RoleDefinition(...),
    "ui_designer": RoleDefinition(...),
    "architect": RoleDefinition(...),
    
    # 开发类
    "frontend_dev": RoleDefinition(...),
    "backend_dev": RoleDefinition(...),
    "fullstack_dev": RoleDefinition(...),
    "technical_writer": RoleDefinition(...),
    "code_example_writer": RoleDefinition(...),
    
    # 数据处理类
    "data_cleaner": RoleDefinition(...),
    "insight_extractor": RoleDefinition(...),
    
    # 质量类
    "qa_engineer": RoleDefinition(...),
    "doc_reviewer": RoleDefinition(...),
    "code_reviewer": RoleDefinition(...),
    
    # 发布类
    "deployment_engineer": RoleDefinition(...),
    "format_optimizer": RoleDefinition(...),
    "report_writer": RoleDefinition(...),
}
```

---

## 5. 流程图

见下方 Mermaid 流程图

---

## 6. 集成方案

### 6.1 WorkflowOrchestrator 修改

```python
class WorkflowOrchestrator:
    def __init__(self, project_path: str, task_description: str = None, ...):
        # ... 现有代码 ...
        
        # 新增：角色生成器
        self.role_generator = RoleFlowGenerator()
        
        # 如果提供了任务描述，自动生成角色流程
        if task_description:
            self.phases = self.role_generator.generate_flow(task_description)
        else:
            # 回退到默认软件开发流程
            self.phases = DEFAULT_SOFTWARE_FLOW
```

### 6.2 使用方式

```bash
# 方式1：自动检测任务类型
bmad-evo run --task "帮我开发一个博客网站，支持Markdown编辑和标签功能"

# 方式2：指定任务类型
bmad-evo run --type web_app --task "开发REST API服务"

# 方式3：传统方式（保持兼容）
bmad-evo run --phases analyst architect development
```

### 6.3 配置扩展

```yaml
# .bmad/project-config.yaml
project:
  name: "我的博客系统"
  type: "web_app"  # 可选，不指定则自动检测
  
task_detection:
  enabled: true
  confidence_threshold: 0.7
  
role_customization:
  # 覆盖默认角色配置
  requirement_analyst:
    model: "kimi-coding/k2p5"
    timeout: 600
  
  # 添加自定义角色
  custom_roles:
    - name: "security_expert"
      title: "安全专家"
      description: "负责安全审查"
      model: "kimi-coding/k2p5"
      insert_after: "development"
```

---

## 7. 复杂度评估

### 7.1 评估维度

| 维度 | 简单(1-3) | 中等(4-6) | 复杂(7-10) |
|------|----------|----------|-----------|
| 功能点数量 | 1-3个 | 4-7个 | 8+个 |
| 技术栈数量 | 1-2个 | 3-4个 | 5+个 |
| 集成复杂度 | 无外部集成 | 1-2个API | 3+个API/服务 |
| 数据复杂度 | 简单CRUD | 关联查询 | 复杂分析/ML |

### 7.2 角色数量调整

- **简单任务(1-3)**：3-4个角色
- **中等任务(4-6)**：5-7个角色
- **复杂任务(7-10)**：8+个角色，可能并行

---

## 8. 实现优先级

| 优先级 | 功能 | 说明 |
|--------|------|------|
| P0 | TaskTypeDetector | 基础任务类型识别 |
| P0 | RoleTemplateLibrary | 3种任务类型的完整角色定义 |
| P1 | RoleFlowGenerator | 流程生成和连接 |
| P1 | WorkflowOrchestrator集成 | 与现有系统集成 |
| P2 | 复杂度评估 | 自动评估任务复杂度 |
| P2 | 并行执行支持 | 支持可并行的角色同时执行 |
| P3 | 自定义角色 | 支持用户定义新角色 |
| P3 | 流程优化器 | 基于历史数据优化流程 |

---

## 9. 技术实现要点

### 9.1 任务类型识别算法

```python
class TaskTypeDetector:
    def __init__(self):
        self.patterns = {
            TaskType.WEB_APP: [
                r"网站|web|前端|页面|frontend",
                r"界面|UI|用户界面",
            ],
            TaskType.API_SERVICE: [
                r"API|接口|服务|后端|backend",
                r"REST|GraphQL|微服务",
            ],
            # ... 其他模式
        }
    
    def detect(self, description: str) -> Tuple[TaskType, float]:
        scores = {}
        for task_type, patterns in self.patterns.items():
            score = sum(1 for p in patterns if re.search(p, description, re.I))
            scores[task_type] = score / len(patterns)
        
        best_type = max(scores, key=scores.get)
        confidence = scores[best_type]
        
        return best_type, confidence
```

### 9.2 角色流程生成算法

```python
class RoleFlowGenerator:
    def generate_flow(self, task_description: str) -> List[str]:
        # 1. 检测任务类型
        task_type, confidence = self.detector.detect(task_description)
        
        # 2. 评估复杂度
        complexity = self._assess_complexity(task_description)
        
        # 3. 获取基础角色流程
        base_flow = ROLE_FLOW_TEMPLATES[task_type]
        
        # 4. 根据复杂度调整
        if complexity <= 3:
            flow = self._simplify_flow(base_flow)
        elif complexity >= 7:
            flow = self._expand_flow(base_flow, task_description)
        else:
            flow = base_flow
        
        # 5. 添加约束检查节点
        flow = self._add_audit_points(flow)
        
        return flow
```

---

*设计版本：v1.0*
*日期：2026-03-21*
