# BMAD-EVO 角色自动生成模块 - 流程图

## 1. 主流程图

```mermaid
flowchart TD
    Start([开始]) --> Input[接收任务描述]
    Input --> Detect{任务类型检测}
    
    Detect -->|WEB_APP| WebFlow[Web应用开发流程]
    Detect -->|API_SERVICE| ApiFlow[API服务开发流程]
    Detect -->|TECH_DOC| DocFlow[技术文档编写流程]
    Detect -->|DATA_ANALYSIS| DataFlow[数据分析流程]
    Detect -->|GENERAL| DefaultFlow[默认软件开发流程]
    
    WebFlow --> Complexity[评估复杂度]
    ApiFlow --> Complexity
    DocFlow --> Complexity
    DataFlow --> Complexity
    DefaultFlow --> Complexity
    
    Complexity -->|简单| Simple[精简角色流程<br/>3-4个角色]
    Complexity -->|中等| Medium[标准角色流程<br/>5-7个角色]
    Complexity -->|复杂| Complex[扩展角色流程<br/>8+个角色]
    
    Simple --> Generate[生成Agent配置]
    Medium --> Generate
    Complex --> Generate
    
    Generate --> Parallel{是否有<br/>可并行角色?}
    Parallel -->|是| Optimize[优化执行顺序<br/>并行执行可并行角色]
    Parallel -->|否| Sequential[串行执行]
    
    Optimize --> Execute[执行角色流程]
    Sequential --> Execute
    
    Execute --> Audit[约束检查]
    Audit --> Pass{检查通过?}
    
    Pass -->|是| Next{还有更多<br/>角色?}
    Pass -->|否| Retry{可重试?}
    
    Retry -->|是| Feedback[添加审计反馈<br/>重新执行]
    Feedback --> Execute
    Retry -->|否| Decision[用户决策]
    
    Decision --> Force[强制继续]
    Decision --> Abort[中止流程]
    Decision --> Fix[人工修复]
    Fix --> Audit
    
    Force --> Next
    
    Next -->|是| Execute
    Next -->|否| Complete[流程完成]
    
    Complete --> Output[输出所有交付物]
    Output --> End([结束])
    
    Abort --> End
```

---

## 2. 任务类型检测流程

```mermaid
flowchart TD
    Start([任务描述]) --> Preprocess[文本预处理<br/>分词/标准化]
    
    Preprocess --> Match[关键词匹配]
    
    Match --> Web{匹配Web相关<br/>关键词?}
    Match --> Api{匹配API相关<br/>关键词?}
    Match --> Doc{匹配文档相关<br/>关键词?}
    Match --> Data{匹配数据相关<br/>关键词?}
    
    Web -->|是| ScoreWeb[Web得分 +1]
    Api -->|是| ScoreApi[API得分 +1]
    Doc -->|是| ScoreDoc[Doc得分 +1]
    Data -->|是| ScoreData[Data得分 +1]
    
    ScoreWeb --> Normalize[计算置信度<br/>得分/总模式数]
    ScoreApi --> Normalize
    ScoreDoc --> Normalize
    ScoreData --> Normalize
    
    Normalize --> Best[选择最高<br/>置信度类型]
    Best --> Threshold{置信度 >=<br/>阈值?}
    
    Threshold -->|是| Return[返回任务类型<br/>+ 置信度]
    Threshold -->|否| General[返回GENERAL类型]
    
    Return --> End([结束])
    General --> End
```

---

## 3. 角色流程生成流程

```mermaid
flowchart TD
    Start([任务类型<br/>+ 复杂度]) --> SelectTemplate[选择对应<br/>角色模板]
    
    SelectTemplate --> WebTemplate{WEB_APP?}
    SelectTemplate --> ApiTemplate{API_SERVICE?}
    SelectTemplate --> DocTemplate{TECH_DOC?}
    SelectTemplate --> DataTemplate{DATA_ANALYSIS?}
    
    WebTemplate -->|是| WebRoles[加载Web角色<br/>→ requirement_analyst<br/>→ product_designer<br/>→ ui_designer<br/>→ architect<br/>→ frontend_dev<br/>→ backend_dev<br/>→ qa_engineer<br/>→ deployment_engineer]
    
    ApiTemplate -->|是| ApiRoles[加载API角色<br/>→ requirement_analyst<br/>→ api_designer<br/>→ architect<br/>→ backend_dev<br/>→ api_tester<br/>→ deployment_engineer]
    
    DocTemplate -->|是| DocRoles[加载Doc角色<br/>→ content_planner<br/>→ technical_writer<br/>→ code_example_writer<br/>→ doc_reviewer<br/>→ format_optimizer]
    
    DataTemplate -->|是| DataRoles[加载Data角色<br/>→ data_analyst<br/>→ data_cleaner<br/>→ visual_designer<br/>→ insight_extractor<br/>→ report_writer]
    
    WebRoles --> Adjust[根据复杂度调整]
    ApiRoles --> Adjust
    DocRoles --> Adjust
    DataRoles --> Adjust
    
    Adjust --> Simple{复杂度<br/>简单?}
    Adjust --> Medium{复杂度<br/>中等?}
    Adjust --> Complex{复杂度<br/>复杂?}
    
    Simple --> Merge[合并部分角色<br/>frontend+backend<br/>→ fullstack]
    Medium --> Keep[保持标准流程]
    Complex --> Add[添加专业角色<br/>+ security_expert<br/>+ performance_expert]
    
    Merge --> Config[生成每个角色的<br/>AgentConfig]
    Keep --> Config
    Add --> Config
    
    Config --> Connect[建立角色连接<br/>定义上下文传递]
    Connect --> Output[输出角色流程列表]
    
    Output --> End([结束])
```

---

## 4. 角色执行流程

```mermaid
flowchart TD
    Start([开始执行]) --> Load[加载当前角色<br/>AgentConfig]
    
    Load --> Context[构建上下文<br/>收集前置角色输出]
    
    Context --> BuildPrompt[构建完整提示词<br/>系统提示 + 上下文 + 任务]
    
    BuildPrompt --> SelectModel[选择AI模型<br/>根据角色配置]
    
    SelectModel --> Execute[执行Agent<br/>调用模型API]
    
    Execute --> Result{执行结果?}
    
    Result -->|成功| Save[保存输出<br/>记录执行信息]
    Result -->|失败| Error{可重试?}
    
    Error -->|是| Retry[增加重试计数<br/>重新执行]
    Retry --> Execute
    Error -->|否| Fail[标记失败<br/>等待用户决策]
    
    Save --> Audit[执行约束检查]
    
    Audit --> AuditResult{检查结果?}
    AuditResult -->|通过| Complete[角色执行完成]
    AuditResult -->|失败| Fixable{可修复?}
    
    Fixable -->|是| Feedback[生成修复反馈<br/>添加到上下文]
    Feedback --> Execute
    Fixable -->|否| Blocked[角色阻塞<br/>等待用户决策]
    
    Complete --> Next{还有更多<br/>角色?}
    Blocked --> UserDecision{用户决策?}
    Fail --> UserDecision
    
    UserDecision --> Force[强制继续]
    UserDecision --> Abort[中止整个流程]
    UserDecision --> ManualFix[人工修复后<br/>重新审计]
    
    ManualFix --> Audit
    Force --> Next
    
    Next -->|是| Load
    Next -->|否| Done[所有角色完成]
    Abort --> End([结束])
    Done --> End
```

---

## 5. 并行执行优化流程

```mermaid
flowchart TD
    Start([角色流程列表]) --> Analyze[分析角色依赖]
    
    Analyze --> BuildGraph[构建依赖图<br/>哪些角色依赖<br/>前置角色输出]
    
    BuildGraph --> Independent{识别无依赖<br/>角色}
    
    Independent --> Group[将可并行角色<br/>分组]
    
    Group --> Batch1[批次1: 独立角色<br/>同时执行]
    Batch1 --> Wait1[等待全部完成]
    
    Wait1 --> Collect1[收集所有输出]
    Collect1 --> Batch2[批次2: 依赖批次1的<br/>角色]
    
    Batch2 --> Wait2[等待全部完成]
    Wait2 --> Collect2[收集所有输出]
    
    Collect2 --> More{还有更多<br/>批次?}
    
    More -->|是| NextBatch[下一批次]
    NextBatch --> Wait2
    
    More -->|否| Merge[合并所有输出<br/>按角色顺序]
    
    Merge --> Output[输出最终交付物]
    
    Output --> End([结束])
```

---

## 6. 完整系统集成流程

```mermaid
flowchart TD
    subgraph UserInput [用户输入]
        CLI[命令行] --> Parse[解析参数]
        Parse --> TaskDesc[提取任务描述]
    end
    
    subgraph RoleGeneration [角色自动生成]
        TaskDesc --> Detect[任务类型检测]
        Detect --> TaskType[确定任务类型<br/>+ 置信度]
        TaskType --> Complexity[复杂度评估]
        Complexity --> SelectRoles[选择角色模板]
        SelectRoles --> Customize[根据配置定制角色]
        Customize --> GenerateFlow[生成执行流程]
    end
    
    subgraph Orchestration [工作流编排]
        GenerateFlow --> InitOrchestrator[初始化Orchestrator<br/>传入角色流程]
        InitOrchestrator --> RunWorkflow[执行工作流]
    end
    
    subgraph PhaseExecution [阶段执行]
        RunWorkflow --> ForEachPhase[遍历每个角色]
        ForEachPhase --> ExecuteAgent[执行Agent]
        ExecuteAgent --> Audit[约束检查]
        Audit --> HandleResult[处理结果]
        HandleResult --> CheckComplete{全部完成?}
        CheckComplete -->|否| ForEachPhase
    end
    
    subgraph Output [输出]
        CheckComplete -->|是| CollectDeliverables[收集所有交付物]
        CollectDeliverables --> SaveReport[保存执行报告]
        SaveReport --> NotifyUser[通知用户完成]
    end
    
    NotifyUser --> End([结束])
```

---

## 7. 角色模板数据结构

```mermaid
classDiagram
    class TaskType {
        +WEB_APP
        +API_SERVICE
        +TECH_DOC
        +DATA_ANALYSIS
        +GENERAL
    }
    
    class RoleDefinition {
        +str name
        +str title
        +str description
        +str model
        +str system_prompt
        +List~str~ required_skills
        +List~str~ input_context
        +str output_deliverable
        +int estimated_time
        +bool can_parallel
    }
    
    class RoleFlowTemplate {
        +TaskType task_type
        +List~str~ role_sequence
        +Dict parallel_groups
        +Dict dependencies
    }
    
    class RoleFlowGenerator {
        +TaskTypeDetector detector
        +RoleTemplateLibrary library
        +generate_flow(task_desc) List~str~
        +assess_complexity(task_desc) int
        +optimize_for_parallel(flow) List~List~
    }
    
    class TaskTypeDetector {
        +Dict patterns
        +detect(description) Tuple~TaskType, float~
    }
    
    class RoleTemplateLibrary {
        +Dict~str, RoleDefinition~ base_roles
        +Dict~TaskType, RoleFlowTemplate~ templates
        +get_template(task_type) RoleFlowTemplate
        +get_role(name) RoleDefinition
    }
    
    TaskType --> RoleFlowTemplate
    RoleFlowTemplate --> RoleDefinition
    RoleFlowGenerator --> TaskTypeDetector
    RoleFlowGenerator --> RoleTemplateLibrary
    RoleTemplateLibrary --> RoleDefinition
```

---

## 8. 与现有系统集成

```mermaid
flowchart LR
    subgraph Existing [现有系统]
        CLI[bmad-evo CLI]
        Orchestrator[WorkflowOrchestrator]
        AgentExecutor[AgentExecutor]
        Auditor[ConstraintAuditor]
    end
    
    subgraph NewModule [新增模块]
        Detector[TaskTypeDetector]
        Generator[RoleFlowGenerator]
        Library[RoleTemplateLibrary]
    end
    
    CLI -->|新增: --task参数| Detector
    CLI -->|新增: --type参数| Generator
    
    Detector --> Generator
    Generator --> Library
    Generator -->|生成角色流程| Orchestrator
    
    Orchestrator -->|执行每个角色| AgentExecutor
    AgentExecutor -->|结果检查| Auditor
    Auditor -->|反馈| Orchestrator
```

---

*流程图版本：v1.0*
*日期：2026-03-21*
