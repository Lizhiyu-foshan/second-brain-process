# 全栈开发约束检查系统 - 实现计划

**基于设计文档**: `/root/.openclaw/workspace/docs/fullstack-constraint-checker-architecture.md`  
**创建时间**: 2026-03-17  
**优先级**: ⭐⭐⭐⭐⭐ BMAD-EVO 核心创新功能

---

## 📊 总体概览

### 系统定位
BMAD-EVO 对前端开发的支持扩展，实现**前后端全栈开发约束检查**，核心价值：
1. **前后端契约自动验证** - 避免 80% 的前后端联调问题
2. **类型安全端到端** - Python Pydantic ↔ TypeScript 类型同步
3. **框架无关性** - 同时支持 React/Vue + FastAPI/Flask
4. **AST 级精度** - 比 ESLint/Prettier 更深层的语义检查
5. **流程阻断** - 契约不一致时自动阻断，防止问题流入生产

### 技术栈矩阵
```
前端层 (Frontend)
├── React + TypeScript (Next.js 支持)
└── Vue 3 + TypeScript (Nuxt 3 支持)
        ↓ API Contract Check
后端层 (Backend)
├── FastAPI (Pydantic 模型)
└── Flask (Marshmallow)
```

---

## 🎯 分阶段实施路线图

### Phase 1: 核心 API 契约检查器（2 周）⭐ **最高优先级**

**目标**: 实现 `ApiContractChecker` 核心模块，这是 BMAD-EVO 独有的创新功能

#### 1.1 数据结构定义（Day 1-2）
**文件**: `bmad-evo/lib/api_contract/types.py`

- [ ] `Severity` 枚举（CRITICAL/HIGH/MEDIUM/LOW）
- [ ] `FieldType` 枚举（string/number/boolean/array/object/enum）
- [ ] `FieldInfo` 数据类（字段信息统一表示）
- [ ] `NormalizedSchema` 数据类（标准化 Schema）
- [ ] `ContractIssue` 数据类（问题描述）
- [ ] `ContractReport` 数据类（检查报告）

**验收标准**:
```python
# 能正确创建和序列化所有数据类型
from bmad_evo.api_contract.types import *

field = FieldInfo(name='user_name', field_type=FieldType.STRING, required=True)
schema = NormalizedSchema(name='UserCreate', fields={'user_name': field})
issue = ContractIssue(severity=Severity.CRITICAL, rule='field_name_match', ...)
report = ContractReport(passed=False, score=78.5, issues=[issue])
```

---

#### 1.2 类型映射器（Day 3-4）
**文件**: `bmad-evo/lib/api_contract/type_mapper.py`

- [ ] 默认类型映射表（Python str → TS string 等）
- [ ] `python_to_typescript()` 方法
- [ ] `typescript_to_python()` 方法
- [ ] `are_types_compatible()` 方法
- [ ] `get_type_mismatch_reason()` 方法
- [ ] 支持自定义映射覆盖

**类型映射规则**:
```python
DEFAULT_MAPPING = {
    'str': 'string',
    'int': 'number',
    'float': 'number',
    'bool': 'boolean',
    'list': 'array',
    'dict': 'object',
    'Optional': 'optional',
    'datetime': 'string (ISO8601)',
    'UUID': 'string',
}
```

**验收标准**:
```python
mapper = TypeMapper()
assert mapper.python_to_typescript('str') == 'string'
assert mapper.python_to_typescript('List[int]') == 'array<number>'
assert mapper.are_types_compatible('str', 'string') == True
```

---

#### 1.3 Schema 提取器（Day 5-8）
**文件**: 
- `bmad-evo/lib/api_contract/schema_extractor.py`
- `bmad-evo/lib/parsers/python_ast_parser.py`
- `bmad-evo/lib/parsers/typescript_ast_parser.py`

**后端提取器** (Python AST):
- [ ] `BackendSchemaExtractor` 类
- [ ] `extract_from_file()` 方法
- [ ] `extract_from_directory()` 方法
- [ ] `_parse_pydantic_model()` 方法（解析 FastAPI Pydantic 模型）
- [ ] `_parse_marshmallow_schema()` 方法（解析 Flask Marshmallow）

**前端提取器** (TypeScript AST):
- [ ] `FrontendSchemaExtractor` 类
- [ ] `extract_from_file()` 方法
- [ ] `extract_from_directory()` 方法
- [ ] `_parse_ts_interface()` 方法（解析 TypeScript Interface）
- [ ] `_parse_type_alias()` 方法（解析 Type Alias）
- [ ] `_parse_zod_schema()` 方法（可选：解析 Zod Schema）

**依赖**:
```bash
pip install esprima-python  # TypeScript AST 解析
```

**验收标准**:
```python
# 后端
backend_extractor = BackendSchemaExtractor(framework='fastapi')
schemas = backend_extractor.extract_from_directory('backend/app/schemas')
assert len(schemas) > 0
assert schemas[0].name == 'UserCreate'

# 前端
frontend_extractor = FrontendSchemaExtractor(framework='react')
schemas = frontend_extractor.extract_from_directory('frontend/src/types')
assert len(schemas) > 0
assert 'user_name' in schemas[0].fields
```

---

#### 1.4 契约检查器核心（Day 9-12）
**文件**: `bmad-evo/lib/api_contract/checker.py`

- [ ] `ApiContractChecker` 类
- [ ] `__init__()` 配置加载
- [ ] `check_contract()` 主方法（检查前后端契约）
- [ ] `check_single_pair()` 方法（检查单个 Schema 对）
- [ ] Schema 配对逻辑（按名称匹配或显式指定）
- [ ] 检查流程编排

**检查规则实现** (`bmad-evo/lib/rules/contract_rules.py`):
- [ ] `check_field_name_match()` - 字段名称一致性（CRITICAL）
- [ ] `check_field_type_match()` - 字段类型匹配（CRITICAL）
- [ ] `check_required_match()` - 必填/可选一致（HIGH）
- [ ] `check_nullable_match()` - 可空性一致（HIGH）
- [ ] `check_enum_values_match()` - 枚举值一致（CRITICAL）
- [ ] `check_nested_structure_match()` - 嵌套结构一致（HIGH）
- [ ] `check_array_item_type_match()` - 数组元素类型一致（HIGH）
- [ ] `check_generic_params_match()` - 泛型参数一致（MEDIUM）

**命名转换工具** (`bmad-evo/lib/api_contract/naming.py`):
- [ ] `snake_to_camel()` - snake_case → camelCase
- [ ] `camel_to_snake()` - camelCase → snake_case
- [ ] `normalize_name()` - 标准化字段名称

**验收标准**:
```python
checker = ApiContractChecker()
report = checker.check_contract(
    backend_schemas=['backend/app/schemas'],
    frontend_schemas=['frontend/src/types/api']
)

assert report.passed == False
assert len(report.issues) > 0
assert any(i.severity == Severity.CRITICAL for i in report.issues)
```

---

#### 1.5 报告生成器（Day 13-14）
**文件**: `bmad-evo/lib/api_contract/reporter.py`

- [ ] `ContractReporter` 类
- [ ] `generate_markdown_report()` - Markdown 格式报告
- [ ] `generate_json_report()` - JSON 格式报告（机器可读）
- [ ] `save_to_file()` - 保存到文件
- [ ] 报告包含修复建议
- [ ] 报告包含代码片段示例

**报告结构**:
```markdown
# API 契约检查报告

**总体结果**: ❌ 失败 (得分：78/100)

## 统计摘要
- 后端 Schema 数量：5
- 前端 Schema 数量：5
- 检查字段总数：47
- 发现问题总数：8

## ❌ CRITICAL 问题（2 个）
### 1. 字段类型不匹配
**规则**: `field_type_match`
**Schema**: `UserCreate`
**字段**: `age`
**问题**: 后端类型 `int` ≠ 前端类型 `string`
**修复建议**: 将前端类型改为 `number`
```

**验收标准**:
```python
reporter = ContractReporter(report)
reporter.save_to_file('api-contract-report.md')
reporter.save_to_json('api-contract-report.json')

# 验证报告内容
assert 'CRITICAL 问题' in markdown_content
assert '修复建议' in markdown_content
assert json_report['passed'] == False
```

---

### Phase 2: 约束模板与配置（1 周）

**目标**: 创建约束模板文件和配置系统

#### 2.1 约束模板文件（Day 1-3）
**目录**: `bmad-evo/templates/constraints/`

创建以下模板:
- [ ] `api-contract.yaml` - 前后端 API 契约一致性检查（核心）
- [ ] `ast-react-app.yaml` - React 专属规则
- [ ] `ast-vue3-app.yaml` - Vue 3 专属规则
- [ ] `ast-nextjs-app.yaml` - Next.js 专属规则
- [ ] `ast-nuxt3-app.yaml` - Nuxt 3 专属规则
- [ ] `ast-fastapi-service.yaml` - FastAPI 专属规则
- [ ] `ast-flask-service.yaml` - Flask 专属规则
- [ ] `ast-typescript-strict.yaml` - TypeScript 通用规则

**模板结构**:
```yaml
name: 前后端 API 契约一致性检查
version: 1.0.0
description: 确保前后端 API Schema 定义完全一致

config:
  naming_convention: camelCase
  strict_mode: false
  type_mapping:
    custom:
      Decimal: number
      ObjectId: string

rules:
  - name: field_name_match
    enabled: true
    severity: CRITICAL
    message: "前后端字段名称必须一致"
  
  - name: field_type_match
    enabled: true
    severity: CRITICAL
    message: "前后端字段类型必须匹配"

thresholds:
  min_score: 85
  block_on_severity:
    - CRITICAL
    - HIGH
```

---

#### 2.2 配置系统（Day 4-5）
**文件**: `bmad-evo/lib/api_contract/config.py`

- [ ] `ContractConfig` 类
- [ ] 从 YAML 加载配置
- [ ] 配置验证
- [ ] 默认配置
- [ ] 配置覆盖机制

---

#### 2.3 项目结构检测器（Day 6-7）
**文件**: `bmad-evo/lib/project_structure_detector.py`

- [ ] `FullStackProjectDetector` 类
- [ ] `detect()` 方法（扫描项目识别技术栈）
- [ ] 检测前端框架（React/Vue/Next.js/Nuxt）
- [ ] 检测后端框架（FastAPI/Flask/Django）
- [ ] 检测语言（TypeScript/JavaScript/Python）
- [ ] 检测包管理器（npm/yarn/pnpm/pip/poetry）

**验收标准**:
```python
detector = FullStackProjectDetector()
config = detector.detect('/path/to/fullstack-project')

assert config.frontend_framework == 'react'
assert config.backend_framework == 'fastapi'
assert config.typescript == True
```

---

### Phase 3: CLI 工具与集成（1 周）

**目标**: 创建命令行工具和 Phase Gateway 集成

#### 3.1 CLI 验证工具（Day 1-3）
**文件**: `bmad-evo/scripts/validate_api_contract.py`

- [ ] 命令行参数解析
- [ ] 支持目录和文件路径
- [ ] 支持配置文件
- [ ] 支持严格模式
- [ ] 支持输出格式选择（markdown/json）
- [ ] 支持退出码（用于 CI/CD）

**使用方式**:
```bash
# 基本用法
python -m bmad_evo validate_api_contract \
  --backend backend/app/schemas \
  --frontend frontend/src/types \
  --output report.md

# 指定配置文件
python -m bmad_evo validate_api_contract \
  --config .bmad-evo/constraints/api-contract.yaml

# 严格模式（阻断 CI/CD）
python -m bmad_evo validate_api_contract \
  --strict \
  --block-on-failure

echo $?  # 0=通过，1=失败
```

---

#### 3.2 Phase Gateway 集成（Day 4-5）
**文件**: `bmad-evo/phases/fullstack_development.py`

- [ ] `FullStackPhaseGateway` 类
- [ ] 新增全栈开发阶段:
  - `backend_schema_design` - 设计 Pydantic 模型
  - `backend_api_implementation` - 实现 API 路由
  - `api_contract_export` - 导出 OpenAPI Schema
  - `frontend_type_generation` - 生成 TypeScript 类型
  - `frontend_component_dev` - 前端组件开发
  - `integration_testing` - 前后端集成测试
  - `contract_validation` - API 契约验证 ⭐
  - `deployment` - 部署

- [ ] `validate_contract_phase()` 方法
- [ ] 契约验证阻断逻辑
- [ ] 自动生成报告

**集成方式**:
```python
class FullStackPhaseGateway(PhaseGateway):
    def validate_contract_phase(self) -> PhaseResult:
        checker = ApiContractChecker()
        report = checker.check_contract(
            backend_schemas=self.config.backend_schema_path,
            frontend_schemas=self.config.frontend_schema_path,
        )
        
        report.save_to_file(f'{self.output_dir}/api-contract-report.md')
        
        if report.has_blocking_issues():
            return PhaseResult(
                passed=False,
                reason=f"API 契约验证失败 (得分：{report.score}/100)",
                issues=report.issues,
            )
        else:
            return PhaseResult(
                passed=True,
                score=report.score,
            )
```

---

#### 3.3 自动化工具（Day 6-7）
**文件**: `bmad-evo/scripts/generate_frontend_types.py`

- [ ] Pydantic → TypeScript 类型生成器
- [ ] 从后端 Schema 自动生成前端 Interface
- [ ] 支持自定义模板
- [ ] 支持增量生成

**使用方式**:
```bash
python scripts/generate_frontend_types.py \
  --backend backend/app/schemas \
  --output frontend/src/types/api \
  --template typescript-interface
```

**生成示例**:
```python
# 后端：backend/app/schemas/user.py
class UserCreate(BaseModel):
    user_name: str
    email: str
    age: Optional[int] = None
```

```typescript
// 前端：frontend/src/types/api.ts (自动生成)
export interface UserCreate {
    userName: string;
    email: string;
    age?: number;
}
```

---

### Phase 4: 测试与文档（1 周）

**目标**: 完善测试覆盖和文档

#### 4.1 单元测试（Day 1-3）
**文件**: `bmad-evo/tests/test_api_contract.py`

- [ ] 测试类型映射器
- [ ] 测试 Schema 提取器
- [ ] 测试契约检查器
- [ ] 测试报告生成器
- [ ] 测试所有检查规则
- [ ] 测试边界条件

**测试覆盖率目标**: >90%

---

#### 4.2 集成测试（Day 4-5）
**文件**: `bmad-evo/tests/test_fullstack_integration.py`

- [ ] 创建示例全栈项目
- [ ] 端到端测试契约检查流程
- [ ] 测试 Phase Gateway 集成
- [ ] 测试自动化工具
- [ ] 性能测试（100 个 Schema < 5 秒）

---

#### 4.3 文档（Day 6-7）
**文件**: `bmad-evo/docs/API_CONTRACT_CHECKER.md`

- [ ] 安装指南
- [ ] 快速入门
- [ ] API 参考
- [ ] 配置选项
- [ ] 检查规则详解
- [ ] 最佳实践
- [ ] 故障排查
- [ ] 示例项目

---

### Phase 5: 生态完善（持续）

**目标**: 扩展支持和优化

#### 5.1 更多框架支持
- [ ] Django REST Framework
- [ ] Express.js (Node.js 后端)
- [ ] Angular (前端)
- [ ] Svelte (前端)

#### 5.2 性能优化
- [ ] 增量检查（只检查变更的文件）
- [ ] 并行检查（多进程/多线程）
- [ ] 缓存机制

#### 5.3 IDE 集成
- [ ] VSCode 插件
- [ ] Git pre-commit hook
- [ ] CI/CD 模板（GitHub Actions, GitLab CI）

---

## 📅 时间表

| Phase | 任务 | 预计工时 | 开始日期 | 结束日期 |
|-------|------|----------|----------|----------|
| Phase 1 | 核心 API 契约检查器 | 2 周 (10 工作日) | 2026-03-18 | 2026-03-31 |
| Phase 2 | 约束模板与配置 | 1 周 (5 工作日) | 2026-04-01 | 2026-04-07 |
| Phase 3 | CLI 工具与集成 | 1 周 (5 工作日) | 2026-04-08 | 2026-04-14 |
| Phase 4 | 测试与文档 | 1 周 (5 工作日) | 2026-04-15 | 2026-04-21 |
| Phase 5 | 生态完善 | 持续 | 2026-04-22 | - |

**总计**: 4 周完成核心功能，后续持续迭代

---

## 🎯 里程碑

### M1: 核心功能可用 (2026-03-31)
- ✅ 能提取 Python 和 TypeScript Schema
- ✅ 能检查字段名称、类型、必填性
- ✅ 能生成 Markdown 和 JSON 报告

### M2: Phase Gateway 集成 (2026-04-14)
- ✅ 能在全栈开发流程中自动阻断
- ✅ CLI 工具可用于 CI/CD

### M3: 发布 v1.0 (2026-04-21)
- ✅ 测试覆盖率 >90%
- ✅ 完整文档
- ✅ 示例项目

---

## 📝 每日开发计划（Phase 1 详细）

### Week 1: 基础架构

**Day 1-2 (2026-03-18~19)**: 数据结构
- [ ] 创建 `lib/api_contract/types.py`
- [ ] 实现所有数据类
- [ ] 编写单元测试
- [ ] 验证序列化/反序列化

**Day 3-4 (2026-03-20~21)**: 类型映射器
- [ ] 创建 `lib/api_contract/type_mapper.py`
- [ ] 实现类型映射逻辑
- [ ] 支持泛型类型（List, Dict, Optional）
- [ ] 编写单元测试

**Day 5 (2026-03-22)**: Python AST 解析器
- [ ] 创建 `lib/parsers/python_ast_parser.py`
- [ ] 解析 Pydantic 模型
- [ ] 提取字段信息

### Week 2: 核心检查逻辑

**Day 6-7 (2026-03-25~26)**: TypeScript AST 解析器
- [ ] 创建 `lib/parsers/typescript_ast_parser.py`
- [ ] 使用 esprima 解析 TypeScript
- [ ] 提取 Interface 定义

**Day 8-10 (2026-03-27~29)**: 契约检查器
- [ ] 创建 `lib/api_contract/checker.py`
- [ ] 实现所有检查规则
- [ ] 实现 Schema 配对逻辑
- [ ] 编写集成测试

**Day 11-12 (2026-03-30~31)**: 报告生成器
- [ ] 创建 `lib/api_contract/reporter.py`
- [ ] 实现 Markdown 报告
- [ ] 实现 JSON 报告
- [ ] 测试报告输出

---

## 🧪 测试策略

### 单元测试
- 每个模块独立测试
-  mocks 外部依赖
- 目标覆盖率：>90%

### 集成测试
- 创建示例全栈项目
- 端到端测试完整流程
- 验证 Phase Gateway 阻断

### 性能测试
- 100 个 Schema 检查 < 5 秒
- 单个 Schema 检查 < 100ms
- 内存占用 < 200MB

### 准确性测试
- 零误报（正确的定义不报告问题）
- 零漏报（所有问题都能检测）
- 类型映射准确率 100%

---

## 📦 交付物清单

### 代码文件
```
bmad-evo/
├── lib/api_contract/
│   ├── __init__.py
│   ├── types.py              # 数据结构
│   ├── checker.py            # 核心检查器
│   ├── schema_extractor.py   # Schema 提取器
│   ├── normalizer.py         # Schema 标准化
│   ├── type_mapper.py        # 类型映射
│   ├── reporter.py           # 报告生成器
│   ├── naming.py             # 命名转换
│   └── config.py             # 配置
│
├── lib/parsers/
│   ├── python_ast_parser.py
│   └── typescript_ast_parser.py
│
├── lib/rules/
│   └── contract_rules.py     # 检查规则
│
├── templates/constraints/
│   ├── api-contract.yaml
│   ├── ast-react-app.yaml
│   ├── ast-vue3-app.yaml
│   ├── ast-fastapi-service.yaml
│   └── ...
│
├── scripts/
│   ├── validate_api_contract.py    # CLI 工具
│   └── generate_frontend_types.py  # 类型生成
│
├── tests/
│   ├── test_api_contract.py
│   └── test_fullstack_integration.py
│
└── docs/
    └── API_CONTRACT_CHECKER.md
```

### 文档
- [x] 架构设计文档（已保存）
- [ ] API 参考文档
- [ ] 用户指南
- [ ] 示例项目 README

### 工具
- [ ] CLI 验证工具
- [ ] 类型生成工具
- [ ] Phase Gateway 集成

---

## 💡 成功标准

### 功能完整性
- [x] 架构设计完成
- [ ] 所有检查规则实现
- [ ] 支持 React/Vue + FastAPI/Flask
- [ ] Phase Gateway 集成

### 质量指标
- [ ] 测试覆盖率 >90%
- [ ] 零误报
- [ ] 零漏报
- [ ] 性能达标

### 用户体验
- [ ] 清晰的错误报告
- [ ] 具体的修复建议
- [ ] 完善的文档
- [ ] 示例项目

---

## 🚀 立即行动

**下一步** (2026-03-18):
1. 创建 `lib/api_contract/types.py`
2. 实现所有数据结构
3. 编写单元测试

**开始开发！** ❤️🔥
