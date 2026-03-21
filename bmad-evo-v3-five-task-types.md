# BMAD-EVO v3.0 五类任务类型设计

## 任务类型定义 (v3.0 Final)

| 编号 | 类型标识 | 名称 | 适用场景 |
|------|----------|------|----------|
| 1 | `FULLSTACK_APP` | 网站或应用全栈开发 | Web应用、移动应用、桌面应用等完整产品 |
| 2 | `BACKEND_MODULE` | 小规模后端开发 | API服务、Skill开发、Agent开发、CLI工具 |
| 3 | `HARD_TECH` | 复杂技术问题解决 | 顽固Bug修复、性能优化、架构重构、高风险操作 |
| 4 | `TECH_WRITING` | 技术博客/文章写作 | 技术文档、教程、博客文章、最佳实践指南 |
| 5 | `DATA_PROCESSING` | 数据分析或处理 | 数据清洗、可视化、洞察提取、报告生成 |

---

## 各类型的角色流程设计

### 类型1: FULLSTACK_APP (网站或应用全栈开发)

**适用场景**：完整的Web应用、移动应用、桌面应用开发

**关键词**：网站、应用、平台、系统、产品、前后端、全栈

```
需求分析师 (requirement_analyst)
    ↓
产品设计师 (product_designer)
    ↓
UI/UX设计师 (ui_designer)
    ↓
架构师 (architect)
    ↓
数据库设计师 (database_designer)
    ↓
┌─────────────────────────────────────┐
│         可并行开发阶段                │
├─────────────────────────────────────┤
│  前端工程师 (frontend_dev)           │
│  后端工程师 (backend_dev)            │
│  (根据复杂度可合并为fullstack_dev)    │
└─────────────────────────────────────┘
    ↓
集成测试工程师 (integration_tester)
    ↓
部署运维工程师 (devops_engineer)
```

**角色详情**：

| 角色 | 模型 | 职责 | 交付物 |
|------|------|------|--------|
| requirement_analyst | K2.5 | 需求分析、功能拆解 | requirements.md |
| product_designer | GLM-5 | 产品规划、功能优先级 | product_spec.md |
| ui_designer | GLM-5 | 界面设计、交互流程 | ui_design.md |
| architect | K2.5 | 系统架构、技术选型 | architecture.md |
| database_designer | K2.5 | 数据模型、Schema设计 | database_schema.md |
| frontend_dev | K2.5 | 前端实现 | frontend/ |
| backend_dev | K2.5 | 后端API实现 | backend/ |
| integration_tester | Qwen3.5 | 端到端测试 | test_report.md |
| devops_engineer | K2.5 | 部署配置、CI/CD | deployment_guide.md |

---

### 类型2: BACKEND_MODULE (小规模后端开发)

**适用场景**：单一API服务、Skill功能、Agent能力、CLI工具、小模块开发

**关键词**：API、接口、skill、agent、工具、脚本、模块、服务、CLI、命令行

```
需求分析师 (requirement_analyst)
    ↓
API/模块设计师 (module_designer)
    ↓
架构师 (architect) [轻量级]
    ↓
开发工程师 (backend_dev)
    ↓
单元测试工程师 (unit_tester)
    ↓
集成验证工程师 (integration_validator)
```

**特点**：
- 流程精简，专注于后端逻辑
- 前后端分离，无UI设计阶段
- 强调接口设计和测试覆盖
- 适合快速迭代的小功能开发

**角色详情**：

| 角色 | 模型 | 职责 | 交付物 |
|------|------|------|--------|
| requirement_analyst | K2.5 | 需求梳理、接口需求 | api_requirements.md |
| module_designer | GLM-5 | 模块设计、接口定义 | api_spec.md |
| architect | K2.5 | 轻量级架构设计 | mini_architecture.md |
| backend_dev | K2.5 | 代码实现 | src/ |
| unit_tester | Qwen3.5 | 单元测试、覆盖率 | unit_tests/ |
| integration_validator | Qwen3.5 | 集成验证、文档 | validation_report.md |

**与FULLSTACK_APP的区别**：

| 维度 | FULLSTACK_APP | BACKEND_MODULE |
|------|---------------|----------------|
| 角色数量 | 9个 | 6个 |
| UI设计 | 有 | 无 |
| 前后端分离 | 是 | 只有后端 |
| 数据库设计 | 独立阶段 | 合并到架构 |
| 测试重点 | 集成测试 | 单元测试 |
| 部署复杂度 | 完整DevOps | 简单部署 |

---

### 类型3: HARD_TECH (复杂技术问题解决)

**适用场景**：顽固Bug、性能瓶颈、架构重构、技术债务清理、高风险操作

**关键词**：Bug、修复、优化、性能、重构、解决、问题、疑难、顽固、架构升级、迁移

```
问题诊断师 (problem_diagnostician)
    ↓
根因分析师 (root_cause_analyst)
    ↓
方案设计师 (solution_designer)
    ↓
┌─────────────────────────────────────┐
│      风险评估与决策点                │
│  (高风险操作需用户确认)              │
└─────────────────────────────────────┘
    ↓
重构/修复工程师 (fix_engineer)
    ↓
回归测试工程师 (regression_tester)
    ↓
性能验证工程师 (performance_validator)
```

**特点**：
- 强调问题诊断和根因分析
- 增加风险评估节点
- 可能需要多次迭代
- 重视回归测试和性能验证
- 有决策检查点（高风险操作）

**角色详情**：

| 角色 | 模型 | 职责 | 交付物 |
|------|------|------|--------|
| problem_diagnostician | K2.5 | 问题诊断、现象分析 | diagnosis_report.md |
| root_cause_analyst | K2.5 | 根因定位、影响分析 | root_cause_analysis.md |
| solution_designer | GLM-5 | 方案设计、风险评估 | solution_design.md |
| fix_engineer | K2.5 | 代码修复/重构 | fix_patch/ |
| regression_tester | Qwen3.5 | 回归测试、兼容性 | regression_report.md |
| performance_validator | K2.5 | 性能验证、基准测试 | performance_report.md |

**特殊机制**：

```yaml
# HARD_TECH 类型特殊配置
hard_tech_config:
  # 风险评估检查点
  risk_checkpoints:
    - before: "fix_engineer"
      condition: "高风险操作"
      action: "require_user_approval"
  
  # 强制双重审计
  audit:
    pass_threshold: 90  # 更高标准
    require_secondary_review: true
  
  # 扩展重试机制
  retry:
    max_attempts: 5  # 更多重试机会
    escalation_models: ["k2p5", "k2p5", "k2p5", "glm-5", "k2p5-deep"]
```

---

### 类型4: TECH_WRITING (技术博客/文章写作)

**适用场景**：技术博客、教程、文档、最佳实践、架构分享

**关键词**：博客、文章、教程、文档、指南、写作、分享、总结、最佳实践

```
选题分析师 (topic_analyst)
    ↓
大纲规划师 (outline_planner)
    ↓
资料研究员 (researcher)
    ↓
内容撰写师 (content_writer)
    ↓
代码示例工程师 (code_example_writer) [如需要]
    ↓
技术审查员 (tech_reviewer)
    ↓
文字编辑 (copy_editor)
    ↓
排版优化师 (format_optimizer)
```

**特点**：
- 强调内容结构和读者体验
- 包含研究阶段
- 重视代码示例质量
- 双重审查（技术+文字）

**角色详情**：

| 角色 | 模型 | 职责 | 交付物 |
|------|------|------|--------|
| topic_analyst | GLM-5 | 选题分析、受众定位 | topic_analysis.md |
| outline_planner | GLM-5 | 结构设计、章节规划 | outline.md |
| researcher | K2.5 | 资料收集、技术验证 | research_notes.md |
| content_writer | GLM-5 | 正文撰写 | draft.md |
| code_example_writer | K2.5 | 代码示例、Demo | examples/ |
| tech_reviewer | Qwen3.5 | 技术准确性审查 | tech_review.md |
| copy_editor | Qwen3.5 | 文字润色、可读性 | edited_draft.md |
| format_optimizer | GLM-5 | 排版优化、发布格式 | final_article.md |

---

### 类型5: DATA_PROCESSING (数据分析或处理)

**适用场景**：数据清洗、探索性分析、可视化、洞察提取、报告生成

**关键词**：数据、分析、清洗、可视化、报告、统计、洞察、处理、挖掘

```
数据理解师 (data_understander)
    ↓
数据质量分析师 (data_quality_analyst)
    ↓
清洗策略设计师 (cleaning_strategist)
    ↓
┌─────────────────────────────────────┐
│         可并行处理阶段                │
├─────────────────────────────────────┤
│  数据清洗工程师 (data_cleaner)        │
│  特征工程师 (feature_engineer)        │
└─────────────────────────────────────┘
    ↓
数据分析师 (data_analyst)
    ↓
可视化设计师 (visualization_designer)
    ↓
洞察提炼师 (insight_extractor)
    ↓
报告撰写师 (report_writer)
```

**特点**：
- 强调数据质量前置
- 清洗和特征工程可并行
- 重视可视化呈现
- 最终输出为数据报告

**角色详情**：

| 角色 | 模型 | 职责 | 交付物 |
|------|------|------|--------|
| data_understander | K2.5 | 数据探索、Schema分析 | data_profile.md |
| data_quality_analyst | Qwen3.5 | 质量评估、问题识别 | quality_report.md |
| cleaning_strategist | K2.5 | 清洗策略、规则设计 | cleaning_strategy.md |
| data_cleaner | Qwen3.5 | 数据清洗、转换 | cleaned_data/ |
| feature_engineer | K2.5 | 特征构建、工程化 | features/ |
| data_analyst | K2.5 | 统计分析、建模 | analysis_results.md |
| visualization_designer | GLM-5 | 图表设计、可视化 | visualizations/ |
| insight_extractor | K2.5 | 洞察提取、结论 | insights.md |
| report_writer | GLM-5 | 报告撰写、呈现 | data_report.md |

---

## 任务类型检测规则

```python
TASK_TYPE_PATTERNS = {
    TaskType.FULLSTACK_APP: {
        "keywords": [
            r"网站|web|应用|app|平台|系统|产品",
            r"全栈|full.?stack|前后端",
            r"网页|页面|界面|用户端",
            r"平台开发|系统开发|产品开发",
        ],
        "weight": 1.0
    },
    
    TaskType.BACKEND_MODULE: {
        "keywords": [
            r"API|接口|服务|service",
            r"skill|agent|工具|tool",
            r"脚本|script|CLI|命令行",
            r"模块|module|组件|component",
            r"后端|backend|server",
        ],
        "weight": 1.0,
        "negative_keywords": [  # 排除全栈场景
            r"网站|web页面|前端界面|用户界面",
        ]
    },
    
    TaskType.HARD_TECH: {
        "keywords": [
            r"Bug|bug|修复|fix",
            r"优化|optimize|性能|performance",
            r"重构|refactor|架构升级|migration",
            r"疑难|顽固|问题|issue|troubleshoot",
            r"解决|解决|排查|诊断|diagnose",
            r"高风险|critical|紧急|urgent",
        ],
        "weight": 1.2  # 高优先级匹配
    },
    
    TaskType.TECH_WRITING: {
        "keywords": [
            r"博客|blog|文章|article",
            r"教程|tutorial|指南|guide",
            r"文档|documentation|doc",
            r"写作|write|撰写|总结|summary",
            r"分享|分享|最佳实践|best practice",
        ],
        "weight": 1.0
    },
    
    TaskType.DATA_PROCESSING: {
        "keywords": [
            r"数据|data|分析|analysis",
            r"清洗|clean|处理|processing",
            r"可视化|visualization|图表|chart",
            r"报告|report|洞察|insight",
            r"统计|statistics|挖掘|mining",
        ],
        "weight": 1.0
    }
}

# 类型优先级（解决重叠问题）
TYPE_PRIORITY = [
    TaskType.HARD_TECH,      # 最高优先级（问题修复优先）
    TaskType.BACKEND_MODULE, # 其次（区分全栈和纯后端）
    TaskType.FULLSTACK_APP,
    TaskType.TECH_WRITING,
    TaskType.DATA_PROCESSING,
]
```

---

## 复杂度调整策略

### 类型1 (FULLSTACK_APP) 复杂度调整

| 复杂度 | 调整策略 | 角色变化 |
|--------|---------|---------|
| 简单 (1-3) | 合并前后端 | frontend_dev + backend_dev → fullstack_dev |
| 中等 (4-6) | 标准流程 | 9个角色 |
| 复杂 (7-10) | 增加专家 | + security_expert + performance_expert |

### 类型2 (BACKEND_MODULE) 复杂度调整

| 复杂度 | 调整策略 | 角色变化 |
|--------|---------|---------|
| 简单 (1-3) | 超级精简 | 合并 design + architect → designer_architect |
| 中等 (4-6) | 标准流程 | 6个角色 |
| 复杂 (7-10) | 增加专家 | + api_gateway_designer + cache_specialist |

### 类型3 (HARD_TECH) 特殊处理

无论复杂度如何，保持完整诊断流程，但调整审计严格度：

| 复杂度 | 审计阈值 | 重试次数 |
|--------|---------|---------|
| 简单 | 85分 | 3次 |
| 中等 | 90分 | 4次 |
| 复杂 | 95分 | 5次 + 专家模型 |

---

## CLI 使用示例

```bash
# 类型1: 全栈应用
bmad-evo init --task "开发一个支持Markdown的博客网站，包含用户系统和标签功能"
# 检测为: FULLSTACK_APP

# 类型2: 小规模后端
bmad-evo init --task "开发一个飞书Webhook消息发送Skill"
bmad-evo init --task "创建一个REST API用于用户认证"
bmad-evo init --task "写一个CLI工具批量处理图片"
# 检测为: BACKEND_MODULE

# 类型3: 复杂技术问题
bmad-evo init --task "解决系统性能瓶颈，API响应超过5秒"
bmad-evo init --task "重构legacy代码，解决技术债务"
bmad-evo init --task "排查内存泄漏问题"
# 检测为: HARD_TECH

# 类型4: 技术写作
bmad-evo init --task "写一篇关于BMAD框架的技术博客"
bmad-evo init --task "编写OpenClaw部署指南"
# 检测为: TECH_WRITING

# 类型5: 数据分析
bmad-evo init --task "分析用户行为数据，生成周报"
bmad-evo init --task "清洗销售数据并可视化"
# 检测为: DATA_PROCESSING

# 手动指定类型（覆盖自动检测）
bmad-evo init --type hard_tech --task "性能优化"
```

---

## 项目章程示例 (类型2: BACKEND_MODULE)

```yaml
# .bmad/project-charter.yaml

project:
  name: "飞书消息发送Skill"
  description: "通过Webhook发送飞书消息的Skill模块"
  
  # 自动生成
  task_type: "BACKEND_MODULE"
  complexity: 3
  confidence: 0.94

workflow:
  phases:
    - name: "requirement_analyst"
      title: "需求分析师"
      model: "kimi-coding/k2p5"
      description: "分析Skill功能需求"
      output: "api_requirements.md"
      
    - name: "module_designer"
      title: "模块设计师"
      model: "zhipu/glm-5"
      description: "设计模块接口"
      output: "module_spec.md"
      
    - name: "architect"
      title: "架构师"
      model: "kimi-coding/k2p5"
      description: "轻量级架构设计"
      output: "mini_architecture.md"
      
    - name: "backend_dev"
      title: "开发工程师"
      model: "kimi-coding/k2p5"
      description: "实现Skill代码"
      output: "src/"
      
    - name: "unit_tester"
      title: "单元测试工程师"
      model: "alibaba/qwen3.5-plus"
      description: "编写单元测试"
      output: "tests/"
      
    - name: "integration_validator"
      title: "集成验证工程师"
      model: "alibaba/qwen3.5-plus"
      description: "集成测试和验证"
      output: "validation_report.md"

constraints:
  # 后端模块专用约束
  - id: "api_contract"
    description: "API契约必须明确"
    severity: "critical"
    
  - id: "error_handling"
    description: "所有外部调用必须有错误处理"
    severity: "high"
    
  - id: "logging"
    description: "关键操作必须有日志记录"
    severity: "medium"

audit:
  pass_threshold: 85
  max_retries: 3
```

---

*设计版本：v3.0-五类任务*
*日期：2026-03-21*
