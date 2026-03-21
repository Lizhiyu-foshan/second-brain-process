# BMAD-EVO v3.0 集成角色自动生成模块设计

## 更新后的完整流程

```
用户输入
    ↓
【新增】任务类型检测 (TaskTypeDetector)
    ↓
【新增】复杂度评估 (ComplexityAssessor)
    ↓
【新增】角色流程生成 (RoleFlowGenerator)
    ├── 选择角色序列
    ├── 分配AI模型
    └── 生成执行计划
    ↓
项目生成 (Project Initialization)
    ↓
定义全局约束 (Constraint Definition)
    ├── 项目章程
    ├── 技术约束
    └── 质量标准
    ↓
【阶段网关】启动阶段 N
    ├── phase_name: 动态角色名
    ├── model: 角色对应模型
    └── context: 前置阶段输出
    ↓
【Agent 执行】调用对应模型角色
    ├── 构建角色专用Prompt
    ├── 注入全局约束
    ├── 注入前置阶段Context
    └── 调用模型执行
    ↓
【强制审计】自动触发 (≥85分通过)
    ├── 通过 → 【网关】进入阶段 N+1
    └── 未通过
           ↓
      三次重试循环
           ↓
      仍失败 → 【决策界面】用户决策
```

---

## 架构集成图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           用户输入层                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  $ bmad-evo init --task "开发博客网站"                                          │
│  $ bmad-evo init --type web_app --task "创建API服务"                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Phase 0: 智能分析与规划                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐     │
│  │ 任务类型检测器    │ → │  复杂度评估器     │ → │ 角色流程生成器    │     │
│  │ TaskTypeDetector │    │ ComplexityAssess │    │ RoleFlowGenerator│     │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘     │
│          │                       │                       │                 │
│          ▼                       ▼                       ▼                 │
│    TaskType.WEB_APP        复杂度: 6/10          角色序列 + 模型分配        │
│    (置信度: 0.92)          (中等)               + 执行计划                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Phase 1: 项目初始化                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. 创建项目目录结构                                                          │
│  2. 生成 project-charter.yaml (包含动态生成的角色流程)                          │
│  3. 定义全局约束 (基于任务类型自动选择约束模板)                                   │
│                                                                             │
│  输出: .bmad/project-charter.yaml                                           │
│        .bmad/constraints.yaml                                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Phase 2~N: 动态角色执行流程                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         阶段网关 (PhaseGateway)                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │ 阶段: requirement_analyst                                  │   │   │
│  │  │ 模型: kimi-coding/k2p5                                      │   │   │
│  │  │ 约束: 需求完整性、边界条件检查                               │   │   │
│  │  │ Context: 用户原始需求 + 项目章程                             │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Agent 执行器 (AgentExecutor)                     │   │
│  │                                                                     │   │
│  │  1. 加载角色配置 (RoleDefinition)                                    │   │
│  │     - system_prompt (角色专用)                                       │   │
│  │     - model (k2p5/GLM-5/Qwen3.5)                                    │   │
│  │     - timeout (300s-600s)                                           │   │
│  │                                                                     │   │
│  │  2. 构建完整 Prompt                                                 │   │
│  │     ├── 角色系统提示词                                               │   │
│  │     ├── 全局约束 (强制遵守)                                          │   │
│  │     ├── 前置阶段输出 (Context)                                       │   │
│  │     └── 当前任务指令                                                 │   │
│  │                                                                     │   │
│  │  3. 调用模型执行 (sessions_spawn)                                    │   │
│  │                                                                     │   │
│  │  4. 保存阶段输出 → .bmad/{phase}-output.md                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    强制审计 (ConstraintAuditor)                       │   │
│  │                                                                     │   │
│  │  AST分析 + 正则检查 + 约束验证                                        │   │
│  │                                                                     │   │
│  │  通过标准: 总分 ≥ 85分                                               │   │
│  │                                                                     │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │ 审计维度:                                                     │    │   │
│  │  │   - 空值检查 (15分)                                          │    │   │
│  │  │   - 异常处理 (20分)                                          │    │   │
│  │  │   - 类型注解 (10分)                                          │    │   │
│  │  │   - 文档完整 (15分)                                          │    │   │
│  │  │   - 代码规范 (20分)                                          │    │   │
│  │  │   - 安全合规 (20分)                                          │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                      │
│                    ┌─────────────────┴─────────────────┐                    │
│                    ▼                                   ▼                    │
│              [通过 ≥85分]                        [未通过 <85分]              │
│                    │                                   │                    │
│                    ▼                                   ▼                    │
│           进入下一阶段 N+1                      自动重试机制                 │
│                                                      │                      │
│                                    ┌─────────────────┼─────────────────┐   │
│                                    ▼                 ▼                 ▼   │
│                              第1次重试            第2次重试          第3次重试│
│                              (K2.5)              (K2.5)           (GLM-5) │
│                              +审计反馈           +审计反馈          +审计反馈│
│                                    │                 │                 │   │
│                                    └─────────────────┴────────┬────────┘   │
│                                                               │            │
│                                                               ▼            │
│                                                    ┌─────────────────────┐ │
│                                                    │   仍失败 → 用户决策  │ │
│                                                    │  (DecisionInterface)│ │
│                                                    │                     │ │
│                                                    │  • 手动修复 → 重试   │ │
│                                                    │  • 放宽约束 → 重试   │ │
│                                                    │  • 强制通过 → 继续   │ │
│                                                    │  • 中止 → 退出      │ │
│                                                    └─────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      项目复盘 (Project Retrospective)                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  所有阶段完成后，自动生成：                                                    │
│  1. 执行报告 (execution-report.md)                                           │
│  2. 决策记录 (decisions.md)                                                  │
│  3. 可复用模式 (patterns/{task_type}-{complexity}.yaml)                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 核心组件集成

### 1. WorkflowOrchestrator 扩展

```python
class WorkflowOrchestrator:
    def __init__(self, project_path: str, task_description: str = None, ...):
        # 初始化已有组件
        self.gateway = PhaseGateway(project_path, config)
        self.auditor = ConstraintAuditor(project_path)
        self.decision_interface = DecisionInterface(project_path, interactive)
        self.agent_executor = AgentExecutor(project_path, mode)
        
        # 新增：角色自动生成组件
        if task_description:
            self.role_generator = RoleFlowGenerator()
            self.phases = self.role_generator.generate_flow(task_description)
            self.role_configs = self.role_generator.get_role_configs()
        else:
            # 回退到默认流程
            self.phases = DEFAULT_SOFTWARE_FLOW
            self.role_configs = DEFAULT_AGENT_CONFIGS
    
    def _run_phase(self, phase: str, strict: bool) -> bool:
        """执行单个阶段 - 集成角色自动生成"""
        
        # 1. 获取动态角色配置
        role_config = self.role_configs.get(phase)
        if not role_config:
            role_config = self._get_default_role_config(phase)
        
        # 2. 启动阶段网关
        if not self.gateway.start_phase(phase, role_config):
            return False
        
        # 3. Agent执行（使用角色专用配置）
        print(f"\n🤖 执行角色: {role_config.title} (Model: {role_config.model})")
        output = self._execute_phase_with_role(phase, role_config)
        
        # 4. 审计检查
        return self._audit_with_retry(phase, output)
```

### 2. 角色生成器集成

```python
class RoleFlowGenerator:
    """
    角色流程生成器
    根据任务描述自动生成角色序列和配置
    """
    
    def __init__(self):
        self.detector = TaskTypeDetector()
        self.complexity_assessor = ComplexityAssessor()
        self.template_library = RoleTemplateLibrary()
        self.model_selector = ModelSelector()
    
    def generate_flow(self, task_description: str) -> Tuple[List[str], Dict]:
        """
        生成角色流程
        
        Returns:
            phases: 角色序列 ["requirement_analyst", "product_designer", ...]
            configs: 角色配置 {"requirement_analyst": RoleDefinition, ...}
        """
        # 1. 检测任务类型
        task_type, confidence = self.detector.detect(task_description)
        
        # 2. 评估复杂度
        complexity = self.complexity_assessor.assess(task_description)
        
        # 3. 加载基础角色模板
        base_roles = self.template_library.get_roles_for_task_type(task_type)
        
        # 4. 根据复杂度调整
        if complexity <= 3:
            roles = self._simplify_roles(base_roles)
        elif complexity >= 7:
            roles = self._expand_roles(base_roles, task_description)
        else:
            roles = base_roles
        
        # 5. 为每个角色选择模型
        configs = {}
        for role in roles:
            configs[role.name] = RoleDefinition(
                name=role.name,
                title=role.title,
                description=role.description,
                model=self.model_selector.select(role, complexity),
                system_prompt=role.system_prompt,
                timeout=role.timeout,
                input_context=role.input_context,
                output_deliverable=role.output_deliverable
            )
        
        phase_names = [r.name for r in roles]
        return phase_names, configs
```

### 3. 模型选择器

```python
class ModelSelector:
    """
    为角色智能选择最合适的AI模型
    """
    
    MODEL_MAP = {
        # 分析类角色 - 需要强逻辑推理
        "requirement_analyst": "kimi-coding/k2p5",
        "data_analyst": "kimi-coding/k2p5",
        "content_planner": "zhipu/glm-5",
        
        # 设计类角色 - 需要创意和规划
        "product_designer": "zhipu/glm-5",
        "ui_designer": "zhipu/glm-5",
        "architect": "kimi-coding/k2p5",
        "api_designer": "kimi-coding/k2p5",
        
        # 开发类角色 - 需要强代码能力
        "frontend_dev": "kimi-coding/k2p5",
        "backend_dev": "kimi-coding/k2p5",
        "fullstack_dev": "kimi-coding/k2p5",
        "technical_writer": "zhipu/glm-5",
        "code_example_writer": "kimi-coding/k2p5",
        
        # 数据处理类
        "data_cleaner": "alibaba/qwen3.5-plus",
        "visual_designer": "zhipu/glm-5",
        "insight_extractor": "kimi-coding/k2p5",
        "report_writer": "zhipu/glm-5",
        
        # 质量类角色
        "qa_engineer": "alibaba/qwen3.5-plus",
        "doc_reviewer": "alibaba/qwen3.5-plus",
        "api_tester": "alibaba/qwen3.5-plus",
        
        # 发布类角色
        "deployment_engineer": "kimi-coding/k2p5",
        "format_optimizer": "alibaba/qwen3.5-plus",
    }
    
    def select(self, role: RoleTemplate, complexity: int) -> str:
        """为角色选择模型"""
        # 基础模型
        base_model = self.MODEL_MAP.get(role.name, "kimi-coding/k2p5")
        
        # 根据复杂度调整
        if complexity >= 8 and role.name in ["architect", "development"]:
            # 复杂任务使用最强模型
            return "kimi-coding/k2p5"
        
        return base_model
```

---

## CLI 更新

```bash
# 方式1：自然语言描述（自动检测类型和生成角色）
bmad-evo init --task "开发一个支持Markdown的博客网站，包含文章管理和标签功能"

# 方式2：指定任务类型
bmad-evo init --type web_app --task "创建REST API服务"
bmad-evo init --type tech_doc --task "编写OpenClaw部署指南"
bmad-evo init --type data_analysis --task "分析用户行为数据并生成报告"

# 方式3：指定复杂度
bmad-evo init --task "开发脚本工具" --complexity simple
bmad-evo init --task "开发企业级微服务平台" --complexity complex

# 方式4：查看生成的角色流程（预览模式）
bmad-evo init --task "开发博客网站" --preview

# 执行工作流
bmad-evo run --strict
```

---

## 项目章程扩展

```yaml
# .bmad/project-charter.yaml

project:
  name: "博客网站开发"
  description: "支持Markdown编辑和标签功能的博客系统"
  
  # 新增：自动生成
  task_type: "web_app"
  complexity: 6
  confidence: 0.92

# 动态生成的角色流程
workflow:
  phases:
    - name: "requirement_analyst"
      title: "需求分析师"
      model: "kimi-coding/k2p5"
      description: "分析需求并提取关键信息"
      input: ["用户原始需求"]
      output: "requirements.md"
      
    - name: "product_designer"
      title: "产品设计师"
      model: "zhipu/glm-5"
      description: "设计产品功能和交互流程"
      input: ["requirements.md"]
      output: "product_spec.md"
      
    - name: "ui_designer"
      title: "UI/UX设计师"
      model: "zhipu/glm-5"
      description: "设计用户界面和交互细节"
      input: ["product_spec.md"]
      output: "ui_design.md"
      
    - name: "architect"
      title: "架构师"
      model: "kimi-coding/k2p5"
      description: "设计系统架构和技术选型"
      input: ["requirements.md", "product_spec.md"]
      output: "architecture.md"
      
    - name: "frontend_dev"
      title: "前端工程师"
      model: "kimi-coding/k2p5"
      description: "开发前端界面"
      input: ["ui_design.md", "architecture.md"]
      output: "frontend/"
      parallel: true
      
    - name: "backend_dev"
      title: "后端工程师"
      model: "kimi-coding/k2p5"
      description: "开发后端API"
      input: ["architecture.md"]
      output: "backend/"
      parallel: true
      
    - name: "qa_engineer"
      title: "测试工程师"
      model: "alibaba/qwen3.5-plus"
      description: "设计测试用例并执行"
      input: ["frontend/", "backend/"]
      output: "test_report.md"
      
    - name: "deployment_engineer"
      title: "部署工程师"
      model: "kimi-coding/k2p5"
      description: "编写部署文档和脚本"
      input: ["architecture.md", "test_report.md"]
      output: "deployment_guide.md"

# 全局约束
constraints:
  - id: "null_check"
    description: "所有函数必须有输入验证"
    severity: "high"
    weight: 15
    
  - id: "exception_flow"
    description: "所有IO操作必须有异常处理"
    severity: "high" 
    weight: 20
    
  # ... 其他约束

# 审计配置
audit:
  pass_threshold: 85
  max_retries: 3
  retry_models: ["kimi-coding/k2p5", "kimi-coding/k2p5", "zhipu/glm-5"]
```

---

*设计版本：v3.0-集成版*
*日期：2026-03-21*
