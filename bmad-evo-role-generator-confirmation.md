# BMAD-EVO 角色自动生成模块 - 架构设计确认版

## 📊 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           用户输入层                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  $ bmad-evo run --task "开发一个博客网站"                                       │
│  $ bmad-evo run --type web_app --task "创建REST API"                         │
│  $ bmad-evo run --type tech_doc "编写部署指南"                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        任务类型检测器 (TaskTypeDetector)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  输入: "开发一个博客网站，支持Markdown编辑和标签功能"                            │
│  分析: 关键词匹配 → 置信度计算                                                  │
│  输出: TaskType.WEB_APP (置信度: 0.92)                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        复杂度评估器 (ComplexityAssessor)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  评估维度: 功能点数量 | 技术栈数量 | 集成复杂度 | 数据复杂度                        │
│  评估结果: 中等复杂度 (5/10)                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      角色流程生成器 (RoleFlowGenerator)                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  加载模板 → 根据复杂度调整 → 生成角色流程                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
         ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
         │   WEB_APP    │   │   TECH_DOC   │   │DATA_ANALYSIS│
         └──────┬───────┘   └──────┬───────┘   └──────┬───────┘
                │                  │                  │
                ▼                  ▼                  ▼
```

## 🔄 不同任务类型的角色流程对比

### 1. WEB_APP (Web应用开发)

```
需求分析师(requirement_analyst)
    ↓
产品设计师(product_designer)
    ↓
UI/UX设计师(ui_designer)
    ↓
架构师(architect)
    ↓
┌─────────────────┐
│ 前端工程师        │ ←→ 可并行（复杂项目）
│ (frontend_dev)  │
└────────┬────────┘
         ↓
┌─────────────────┐
│ 后端工程师        │ ←→ 可并行（复杂项目）
│ (backend_dev)   │
└────────┬────────┘
         ↓
测试工程师(qa_engineer)
    ↓
部署工程师(deployment_engineer)
```

### 2. TECH_DOC (技术文档编写)

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

### 3. DATA_ANALYSIS (数据分析)

```
数据分析师(data_analyst)
    ↓
┌─────────────────┐
│ 数据清洗工程师     │ ←→ 可并行
│ (data_cleaner)  │
└────────┬────────┘
         ↓
┌─────────────────┐
│ 可视化设计师      │ ←→ 可并行
│ (visual_designer)│
└────────┬────────┘
         ↓
洞察提炼师(insight_extractor)
    ↓
报告撰写师(report_writer)
```

### 4. API_SERVICE (API服务开发)

```
需求分析师(requirement_analyst)
    ↓
API设计师(api_designer)
    ↓
架构师(architect)
    ↓
后端工程师(backend_dev)
    ↓
API测试工程师(api_tester)
    ↓
部署工程师(deployment_engineer)
```

---

## 📋 复杂度调整规则

| 复杂度 | 调整策略 | 角色数量 | 示例 |
|--------|---------|---------|------|
| **简单 (1-3)** | 合并前后端 → 全栈工程师 | 3-4 | 单页工具、脚本 |
| **中等 (4-6)** | 标准流程 | 5-7 | 一般Web应用、API |
| **复杂 (7-10)** | 添加专家角色 | 8+ | 企业级系统、平台 |

### 简单项目角色合并示例

```
Before (标准流程):
  requirement_analyst → product_designer → ui_designer → 
  architect → frontend_dev → backend_dev → qa_engineer

After (简化流程):
  requirement_analyst → product_designer → 
  fullstack_dev (合并前后端) → qa_engineer
```

### 复杂项目角色扩展示例

```
Before (标准流程):
  ... → backend_dev → qa_engineer → deployment_engineer

After (扩展流程):
  ... → backend_dev → security_expert → performance_expert 
      → qa_engineer → deployment_engineer → monitoring_expert
```

---

## 🎯 系统交互流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         完整执行流程                                      │
└─────────────────────────────────────────────────────────────────────────┘

用户: bmad-evo run --task "帮我开发一个博客网站"
    │
    ▼
┌───────────────────────────────────────────────────────────────────────┐
│ Step 1: 任务类型检测                                                    │
│ Input:  "帮我开发一个博客网站"                                           │
│ Match:  "开发" + "网站" → TaskType.WEB_APP                              │
│ Confidence: 0.95                                                        │
└───────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────────────────────────────────────┐
│ Step 2: 复杂度评估                                                      │
│ Features: 文章管理、Markdown编辑、标签系统、用户认证                         │
│ Tech Stack: React + Node.js + MongoDB                                  │
│ Complexity Score: 6/10 (中等)                                           │
└───────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────────────────────────────────────┐
│ Step 3: 生成角色流程                                                    │
│ Base Flow: [requirement_analyst, product_designer, ui_designer,        │
│             architect, frontend_dev, backend_dev, qa_engineer]         │
│ Adjustment: 保持标准流程 (复杂度中等)                                      │
│ Final Flow: 同上                                                        │
└───────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────────────────────────────────────┐
│ Step 4: 执行角色流程                                                    │
│                                                                         │
│ ┌─────────────────────────────────────────────────────────────────┐   │
│ │ Phase 1/7: requirement_analyst                                  │   │
│ │ Model: kimi-coding/k2p5                                          │   │
│ │ Task: 分析博客网站需求...                                         │   │
│ │ Status: ✅ 完成                                                   │   │
│ │ Output: requirements.md                                          │   │
│ └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│ ┌─────────────────────────────────────────────────────────────────┐   │
│ │ Phase 2/7: product_designer                                     │   │
│ │ Input: requirements.md                                           │   │
│ │ Status: ✅ 完成                                                   │   │
│ │ Output: product_spec.md                                          │   │
│ └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│ ... (继续执行剩余角色) ...                                              │
│                                                                         │
│ ┌─────────────────────────────────────────────────────────────────┐   │
│ │ Phase 7/7: deployment_engineer                                  │   │
│ │ Status: ✅ 完成                                                   │   │
│ │ Output: deployment_guide.md                                      │   │
│ └─────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────────────────────────────────────┐
│ Step 5: 输出交付物                                                      │
│ Deliverables:                                                          │
│   - requirements.md                                                    │
│   - product_spec.md                                                    │
│   - ui_design.md                                                       │
│   - architecture.md                                                    │
│   - frontend_code/                                                     │
│   - backend_code/                                                      │
│   - test_report.md                                                     │
│   - deployment_guide.md                                                │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 🔧 技术实现要点

### 1. 核心类设计

```python
# 任务类型
class TaskType(Enum):
    WEB_APP = "web_app"
    API_SERVICE = "api_service"
    TECH_DOC = "tech_doc"
    DATA_ANALYSIS = "data_analysis"
    GENERAL = "general"

# 角色定义
@dataclass
class RoleDefinition:
    name: str                # 角色标识
    title: str               # 显示名称
    description: str         # 描述
    model: str               # AI模型
    system_prompt: str       # 系统提示词
    input_context: List[str] # 需要输入
    output_deliverable: str  # 输出交付物
    can_parallel: bool       # 是否可并行

# 角色流程生成器
class RoleFlowGenerator:
    def generate_flow(self, task_description: str) -> List[str]:
        # 1. 检测任务类型
        task_type = self.detector.detect(task_description)
        
        # 2. 评估复杂度
        complexity = self.assess_complexity(task_description)
        
        # 3. 加载基础模板
        base_flow = self.templates.get(task_type)
        
        # 4. 根据复杂度调整
        if complexity <= 3:
            return self._simplify(base_flow)
        elif complexity >= 7:
            return self._expand(base_flow)
        
        return base_flow
```

### 2. 使用方式

```bash
# 方式1：自动检测（推荐）
bmad-evo run --task "帮我开发一个博客网站"

# 方式2：指定任务类型
bmad-evo run --type web_app --task "创建REST API服务"

# 方式3：传统方式（向后兼容）
bmad-evo run --phases analyst architect development

# 方式4：指定复杂度
bmad-evo run --task "开发工具脚本" --complexity simple
```

---

## 📁 文件结构

```
bmad-evo/
├── lib/
│   ├── agent_executor.py           # 已有
│   ├── role_generator.py           # 新增：角色生成器
│   ├── task_type_detector.py       # 新增：任务类型检测
│   ├── role_templates.py           # 新增：角色模板库
│   ├── flow_optimizer.py           # 新增：流程优化器
│   └── complexity_assessor.py      # 新增：复杂度评估
├── agents/
│   ├── workflow_orchestrator.py    # 修改：集成角色生成
│   └── ...
└── templates/
    └── role_flows/                 # 新增：任务类型流程模板
        ├── web_app.yaml
        ├── api_service.yaml
        ├── tech_doc.yaml
        └── data_analysis.yaml
```

---

## ✅ 待确认事项

1. **任务类型覆盖范围**：目前设计4种主要类型，是否需要更多？
2. **角色粒度**：当前设计每个角色专注一个职责，是否需要更粗粒度？
3. **并行执行**：复杂项目支持前后端并行，是否还需要其他并行场景？
4. **复杂度评估**：基于功能点/技术栈评估，是否需要其他维度？
5. **自定义角色**：用户可添加自定义角色，优先级如何？

---

*设计版本：v1.0*
*日期：2026-03-21*
