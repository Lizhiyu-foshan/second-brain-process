# 📐 Phase 2: API 契约检查系统设计文档

## 一、系统架构

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     API 契约检查系统                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐         ┌──────────────┐                     │
│  │  后端 Schema  │         │  前端 Schema  │                     │
│  │   提取器     │         │   提取器     │                     │
│  │  (Python)   │         │ (TypeScript) │                     │
│  └──────┬───────┘         └──────┬───────┘                     │
│         │                        │                              │
│         ▼                        ▼                              │
│  ┌──────────────────────────────────────────┐                  │
│  │        统一 Schema 表示层 (Normalized)    │                  │
│  │  ┌────────────────────────────────────┐  │                  │
│  │  │  NormalizedSchema                  │  │                  │
│  │  │  - name: string                    │  │                  │
│  │  │  - fields: Map<name, FieldInfo>    │  │                  │
│  │  │  - nested: List[NormalizedSchema]  │  │                  │
│  │  └────────────────────────────────────┘  │                  │
│  └──────────────────┬───────────────────────┘                  │
│                     │                                          │
│                     ▼                                          │
│  ┌──────────────────────────────────────────┐                  │
│  │        ApiContractChecker                │                  │
│  │  ┌────────────────────────────────────┐  │                  │
│  │  │  检查规则：                         │  │                  │
│  │  │  ✓ 字段名称一致性                   │  │                  │
│  │  │  ✓ 字段类型匹配                     │  │                  │
│  │  │  ✓ 必填/可选一致                    │  │                  │
│  │  │  ✓ 枚举值一致                       │  │                  │
│  │  │  ✓ 嵌套结构一致                     │  │                  │
│  │  │  ✓ 泛型参数一致                     │  │                  │
│  │  └────────────────────────────────────┘  │                  │
│  └──────────────────┬───────────────────────┘                  │
│                     │                                          │
│                     ▼                                          │
│  ┌──────────────────────────────────────────┐                  │
│  │        ContractReport                    │                  │
│  │  - passed: bool                          │                  │
│  │  - score: float (0-100)                  │                  │
│  │  - issues: List[ContractIssue]           │                  │
│  │  - summary: str                          │                  │
│  └──────────────────────────────────────────┘                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 模块结构

```
bmad-evo/
├── lib/
│   ├── api_contract/
│   │   ├── __init__.py
│   │   ├── checker.py              # 核心检查器
│   │   ├── schema_extractor.py     # Schema 提取器
│   │   ├── normalizer.py           # Schema 标准化
│   │   ├── type_mapper.py          # 类型映射规则
│   │   └── reporter.py             # 报告生成器
│   │
│   └── rules/
│       └── contract_rules.py       # 契约检查规则实现
│
├── templates/constraints/
│   └── api-contract.yaml           # 契约约束定义
│
├── scripts/
│   ├── validate_api_contract.py    # CLI 验证工具
│   └── generate_ts_types.py        # 类型生成工具（可选）
│
└── tests/
    └── test_api_contract.py        # 单元测试
```

---

## 二、核心接口设计

### 2.1 数据结构定义

```python
# lib/api_contract/types.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class FieldType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    ENUM = "enum"
    ANY = "any"
    NULL = "null"

@dataclass
class FieldInfo:
    """字段信息（统一前后端表示）"""
    name: str
    field_type: FieldType
    required: bool = True
    nullable: bool = False
    default: Any = None
    description: str = ""
    enum_values: Optional[List[Any]] = None
    nested_schema: Optional['NormalizedSchema'] = None
    array_item_type: Optional['FieldType'] = None  # 数组元素类型
    generic_params: Optional[List['FieldType']] = None  # 泛型参数
    
    # 来源信息
    source_file: str = ""
    source_line: int = 0
    
@dataclass
class NormalizedSchema:
    """标准化的 Schema 表示（消除语言差异）"""
    name: str  # Schema 名称（如 UserCreate, PostResponse）
    fields: Dict[str, FieldInfo] = field(default_factory=dict)
    description: str = ""
    
    # 来源信息
    source_file: str = ""
    source_language: str = ""  # "python" or "typescript"
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ContractIssue:
    """契约检查问题"""
    severity: Severity
    rule: str  # 违反的规则名称
    message: str  # 问题描述
    schema_name: str  # 哪个 Schema 有问题
    field_name: Optional[str] = None  # 哪个字段有问题
    
    # 详细信息
    detail: str = ""
    backend_value: str = ""  # 后端的定义
    frontend_value: str = ""  # 前端的定义
    
    # 修复建议
    suggestion: str = ""
    
    # 位置信息
    backend_file: str = ""
    backend_line: int = 0
    frontend_file: str = ""
    frontend_line: int = 0
    
    def to_dict(self) -> dict:
        return {
            'severity': self.severity.value,
            'rule': self.rule,
            'message': self.message,
            'schema_name': self.schema_name,
            'field_name': self.field_name,
            'detail': self.detail,
            'backend_value': self.backend_value,
            'frontend_value': self.frontend_value,
            'suggestion': self.suggestion,
        }

@dataclass
class ContractReport:
    """契约检查报告"""
    passed: bool
    score: float  # 0-100
    total_checks: int = 0
    passed_checks: int = 0
    issues: List[ContractIssue] = field(default_factory=list)
    
    # 统计信息
    backend_schemas_count: int = 0
    frontend_schemas_count: int = 0
    fields_checked: int = 0
    
    # 总结
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)
    
    def has_critical_issues(self) -> bool:
        return any(i.severity == Severity.CRITICAL for i in self.issues)
    
    def has_blocking_issues(self) -> bool:
        """是否有阻断流程的问题"""
        return self.has_critical_issues() or \
               any(i.severity == Severity.HIGH for i in self.issues)
```

### 2.2 核心检查器接口

```python
# lib/api_contract/checker.py

from typing import List, Union, Optional
from pathlib import Path
from .types import ContractReport, NormalizedSchema, ContractIssue

class ApiContractChecker:
    """
    API 契约一致性检查器
    
    使用方式:
        checker = ApiContractChecker()
        report = checker.check_contract(
            backend_schemas=['backend/app/schemas/user.py'],
            frontend_schemas=['frontend/src/types/api.ts'],
        )
    """
    
    def __init__(self, config: Optional[dict] = None):
        """
        初始化检查器
        
        Args:
            config: 配置选项
                - type_mapping: 自定义类型映射规则
                - naming_convention: 命名约定 (snake_case, camelCase)
                - strict_mode: 严格模式（任何不匹配都是 CRITICAL）
        """
        self.config = config or {}
        self.type_mapping = self._load_type_mapping()
        self.naming_convention = self.config.get('naming_convention', 'camelCase')
    
    def check_contract(
        self,
        backend_schemas: Union[List[str], str],
        frontend_schemas: Union[List[str], str],
        schema_pairs: Optional[List[tuple]] = None,
    ) -> ContractReport:
        """
        检查前后端契约一致性
        
        Args:
            backend_schemas: 后端 Schema 文件路径（支持目录）
            frontend_schemas: 前端 Schema 文件路径（支持目录）
            schema_pairs: 显式指定配对的 Schema [(backend_file, frontend_file), ...]
                         如果不指定，自动按名称匹配
        
        Returns:
            ContractReport: 检查报告
        
        检查流程:
            1. 提取后端 Schema（Python AST → NormalizedSchema）
            2. 提取前端 Schema（TypeScript AST → NormalizedSchema）
            3. Schema 配对（按名称或显式指定）
            4. 逐对检查契约一致性
            5. 生成报告
        """
        pass
    
    def check_single_pair(
        self,
        backend_schema: NormalizedSchema,
        frontend_schema: NormalizedSchema,
    ) -> List[ContractIssue]:
        """
        检查单个 Schema 对的契约一致性
        
        检查项:
            1. 字段名称一致性
            2. 字段类型匹配
            3. 必填/可选一致
            4. 枚举值一致
            5. 嵌套结构一致
        """
        pass
```

### 2.3 Schema 提取器接口

```python
# lib/api_contract/schema_extractor.py

from .types import NormalizedSchema
from typing import List

class BackendSchemaExtractor:
    """后端 Schema 提取器（Python AST）"""
    
    def __init__(self, framework: str = 'fastapi'):
        """
        Args:
            framework: 后端框架 ('fastapi', 'flask', 'django')
        """
        self.framework = framework
    
    def extract_from_file(self, file_path: str) -> List[NormalizedSchema]:
        """从单个 Python 文件提取 Schema"""
        pass
    
    def extract_from_directory(self, dir_path: str) -> List[NormalizedSchema]:
        """从目录提取所有 Schema"""
        pass
    
    def _parse_pydantic_model(self, node: ast.ClassDef) -> NormalizedSchema:
        """解析 Pydantic 模型"""
        pass
    
    def _parse_marshmallow_schema(self, node: ast.ClassDef) -> NormalizedSchema:
        """解析 Marshmallow Schema"""
        pass


class FrontendSchemaExtractor:
    """前端 Schema 提取器（TypeScript AST）"""
    
    def __init__(self, framework: str = 'react'):
        """
        Args:
            framework: 前端框架 ('react', 'vue', 'nextjs', 'nuxt')
        """
        self.framework = framework
    
    def extract_from_file(self, file_path: str) -> List[NormalizedSchema]:
        """从单个 TypeScript 文件提取 Schema"""
        pass
    
    def extract_from_directory(self, dir_path: str) -> List[NormalizedSchema]:
        """从目录提取所有 Schema"""
        pass
    
    def _parse_ts_interface(self, node: dict) -> NormalizedSchema:
        """解析 TypeScript Interface"""
        pass
    
    def _parse_type_alias(self, node: dict) -> NormalizedSchema:
        """解析 TypeScript Type Alias"""
        pass
    
    def _parse_zod_schema(self, node: dict) -> NormalizedSchema:
        """解析 Zod Schema（如果使用）"""
        pass
```

### 2.4 类型映射器

```python
# lib/api_contract/type_mapper.py

from typing import Dict, Optional

class TypeMapper:
    """
    Python ↔ TypeScript 类型映射
    
    默认映射规则:
        Python str         → TypeScript string
        Python int         → TypeScript number
        Python float       → TypeScript number
        Python bool        → TypeScript boolean
        Python list[T]     → TypeScript T[]
        Python dict[K,V]   → TypeScript Record<K, V>
        Python Optional[T] → TypeScript T | null
        Python datetime    → TypeScript string (ISO8601)
        Python UUID        → TypeScript string
        Python Enum        → TypeScript enum
    """
    
    DEFAULT_MAPPING: Dict[str, str] = {
        'str': 'string',
        'int': 'number',
        'float': 'number',
        'bool': 'boolean',
        'list': 'array',
        'List': 'array',
        'dict': 'object',
        'Dict': 'object',
        'Optional': 'optional',
        'Union': 'union',
        'datetime': 'string',
        'date': 'string',
        'UUID': 'string',
        'Any': 'any',
    }
    
    def __init__(self, custom_mapping: Optional[Dict[str, str]] = None):
        self.mapping = {**self.DEFAULT_MAPPING, **(custom_mapping or {})}
    
    def python_to_typescript(self, python_type: str) -> str:
        """Python 类型 → TypeScript 类型"""
        pass
    
    def typescript_to_python(self, ts_type: str) -> str:
        """TypeScript 类型 → Python 类型"""
        pass
    
    def are_types_compatible(self, python_type: str, ts_type: str) -> bool:
        """检查两个类型是否兼容"""
        pass
    
    def get_type_mismatch_reason(
        self,
        python_type: str,
        ts_type: str,
    ) -> str:
        """获取类型不匹配的详细原因"""
        pass
```

---

## 三、检查规则详细设计

### 3.1 规则清单

| 规则名称 | 严重性 | 说明 | 示例 |
|---------|--------|------|------|
| `field_name_match` | CRITICAL | 字段名称必须一致 | 后端 `user_name` ↔ 前端 `userName` ❌ |
| `field_type_match` | CRITICAL | 字段类型必须匹配 | 后端 `str` ↔ 前端 `number` ❌ |
| `required_match` | HIGH | 必填/可选必须一致 | 后端必填 ↔ 前端可选 ❌ |
| `nullable_match` | HIGH | 可空性必须一致 | 后端可空 ↔ 前端不可空 ❌ |
| `enum_values_match` | CRITICAL | 枚举值必须完全一致 | 后端 `[A,B,C]` ↔ 前端 `[A,B]` ❌ |
| `nested_structure_match` | HIGH | 嵌套结构必须一致 | 后端嵌套对象 ↔ 前端平铺 ❌ |
| `array_item_type_match` | HIGH | 数组元素类型必须一致 | 后端 `List[int]` ↔ 前端 `string[]` ❌ |
| `generic_params_match` | MEDIUM | 泛型参数必须一致 | 后端 `Dict[str,int]` ↔ 前端 `Record<string,string>` ❌ |
| `naming_convention` | LOW | 命名约定一致性 | 建议统一 camelCase 或 snake_case |
| `description_sync` | LOW | 字段描述同步 | 后端有描述 ↔ 前端无描述 ⚠️ |

### 3.2 规则实现示例

```python
# lib/rules/contract_rules.py

from typing import List, Optional
from api_contract.types import (
    ContractIssue, Severity, FieldInfo, NormalizedSchema
)

class ContractRules:
    """契约检查规则实现"""
    
    @staticmethod
    def check_field_name_match(
        backend_field: FieldInfo,
        frontend_field: FieldInfo,
        schema_name: str,
    ) -> Optional[ContractIssue]:
        """检查字段名称一致性"""
        
        # 标准化名称（处理 snake_case ↔ camelCase）
        backend_normalized = ContractRules._normalize_name(backend_field.name)
        frontend_normalized = ContractRules._normalize_name(frontend_field.name)
        
        if backend_normalized != frontend_normalized:
            return ContractIssue(
                severity=Severity.CRITICAL,
                rule='field_name_match',
                message=f"字段名称不一致",
                schema_name=schema_name,
                field_name=f"{backend_field.name} ↔ {frontend_field.name}",
                detail=f"后端使用 '{backend_field.name}', 前端使用 '{frontend_field.name}'",
                backend_value=backend_field.name,
                frontend_value=frontend_field.name,
                suggestion=f"统一使用 '{frontend_field.name}' (camelCase) 或 '{backend_field.name}' (snake_case)",
                backend_file=backend_field.source_file,
                backend_line=backend_field.source_line,
                frontend_file=frontend_field.source_file,
                frontend_line=frontend_field.source_line,
            )
        return None
    
    @staticmethod
    def check_field_type_match(
        backend_field: FieldInfo,
        frontend_field: FieldInfo,
        schema_name: str,
        type_mapper: 'TypeMapper',
    ) -> Optional[ContractIssue]:
        """检查字段类型匹配"""
        
        if not type_mapper.are_types_compatible(
            backend_field.field_type.value,
            frontend_field.field_type.value,
        ):
            return ContractIssue(
                severity=Severity.CRITICAL,
                rule='field_type_match',
                message=f"字段类型不匹配",
                schema_name=schema_name,
                field_name=backend_field.name,
                detail=f"后端类型 '{backend_field.field_type.value}' ≠ 前端类型 '{frontend_field.field_type.value}'",
                backend_value=backend_field.field_type.value,
                frontend_value=frontend_field.field_type.value,
                suggestion=type_mapper.get_type_mismatch_reason(
                    backend_field.field_type.value,
                    frontend_field.field_type.value,
                ),
            )
        return None
    
    @staticmethod
    def check_required_match(
        backend_field: FieldInfo,
        frontend_field: FieldInfo,
        schema_name: str,
    ) -> Optional[ContractIssue]:
        """检查必填/可选一致性"""
        
        if backend_field.required != frontend_field.required:
            return ContractIssue(
                severity=Severity.HIGH,
                rule='required_match',
                message=f"字段必填性不一致",
                schema_name=schema_name,
                field_name=backend_field.name,
                detail=f"后端定义为 {'必填' if backend_field.required else '可选'}, "
                       f"前端定义为 {'必填' if frontend_field.required else '可选'}",
                backend_value='required' if backend_field.required else 'optional',
                frontend_value='required' if frontend_field.required else 'optional',
                suggestion=f"统一 {'设为必填' if backend_field.required else '设为可选'}",
            )
        return None
    
    @staticmethod
    def _normalize_name(name: str) -> str:
        """标准化字段名称（转为 camelCase）"""
        if '_' in name:
            # snake_case → camelCase
            parts = name.split('_')
            return parts[0] + ''.join(word.capitalize() for word in parts[1:])
        return name
```

---

## 四、约束模板设计

```yaml
# templates/constraints/api-contract.yaml

name: 前后端 API 契约一致性检查
version: 1.0.0
description: 确保前后端 API Schema 定义完全一致

# 适用场景
applicable_to:
  - fullstack
  - api-first

# 检查配置
config:
  # 命名约定（推荐 camelCase 作为前后端统一标准）
  naming_convention: camelCase
  
  # 严格模式（任何不匹配都是 CRITICAL）
  strict_mode: false
  
  # 类型映射（自定义覆盖默认映射）
  type_mapping:
    custom:
      Decimal: number
      ObjectId: string
  
  # 忽略的字段（全局）
  ignored_fields:
    - createdAt
    - updatedAt
    - __typename

# 检查规则
rules:
  # CRITICAL 级别（必须修复）
  - name: field_name_match
    enabled: true
    severity: CRITICAL
    message: "前后端字段名称必须一致"
    description: "字段名经过 snake_case ↔ camelCase 转换后必须相同"
    
  - name: field_type_match
    enabled: true
    severity: CRITICAL
    message: "前后端字段类型必须匹配"
    description: "Python 类型和 TypeScript 类型必须符合映射规则"
    
  - name: enum_values_match
    enabled: true
    severity: CRITICAL
    message: "枚举值必须完全一致"
    description: "枚举值的数量、顺序、内容都必须相同"
  
  # HIGH 级别（应该修复）
  - name: required_match
    enabled: true
    severity: HIGH
    message: "字段必填性必须一致"
    description: "必填/可选定义在前后端必须相同"
    
  - name: nullable_match
    enabled: true
    severity: HIGH
    message: "字段可空性必须一致"
    
  - name: nested_structure_match
    enabled: true
    severity: HIGH
    message: "嵌套结构必须一致"
    
  - name: array_item_type_match
    enabled: true
    severity: HIGH
    message: "数组元素类型必须一致"
  
  # MEDIUM 级别（建议修复）
  - name: generic_params_match
    enabled: true
    severity: MEDIUM
    message: "泛型参数必须一致"
  
  # LOW 级别（可选优化）
  - name: naming_convention
    enabled: false
    severity: LOW
    message: "建议统一命名约定"
    
  - name: description_sync
    enabled: false
    severity: LOW
    message: "建议同步字段描述"

# 阈值配置
thresholds:
  # 最低分数（低于则阻断流程）
  min_score: 85
  
  # 阻断的严重性级别
  block_on_severity:
    - CRITICAL
    - HIGH
  
  # 允许的最大问题数
  max_issues:
    CRITICAL: 0
    HIGH: 3
    MEDIUM: 10
    LOW: 999

# 检查范围
scope:
  # 后端 Schema 位置
  backend:
    paths:
      - "backend/app/schemas/**/*.py"
      - "backend/app/models/**/*.py"
    include:
      - "**/pydantic/**/*.py"
    exclude:
      - "**/test_*.py"
      - "**/__pycache__/**"
  
  # 前端 Schema 位置
  frontend:
    paths:
      - "frontend/src/types/**/*.ts"
      - "frontend/src/types/**/*.tsx"
    include:
      - "**/api/**/*.ts"
    exclude:
      - "**/*.test.ts"
      - "**/node_modules/**"

# 报告配置
report:
  format: markdown
  output_file: ".bmad-evo/reports/api-contract-report.md"
  include_suggestions: true
  include_code_snippets: true
```

---

## 五、使用示例

### 5.1 命令行工具

```bash
# 基本用法
python -m bmad_evo validate_api_contract \
  --backend backend/app/schemas \
  --frontend frontend/src/types \
  --output report.md

# 指定配置文件
python -m bmad_evo validate_api_contract \
  --config .bmad-evo/constraints/api-contract.yaml

# 严格模式（任何问题都阻断）
python -m bmad_evo validate_api_contract \
  --strict \
  --block-on-failure

# 仅检查特定 Schema
python -m bmad_evo validate_api_contract \
  --schema-pair UserCreate:user.ts \
  --schema-pair PostResponse:post.ts
```

### 5.2 Python API

```python
from bmad_evo.api_contract import ApiContractChecker, Config

# 配置检查器
config = Config(
    naming_convention='camelCase',
    strict_mode=False,
    type_mapping={
        'Decimal': 'number',
        'ObjectId': 'string',
    }
)

checker = ApiContractChecker(config=config)

# 执行检查
report = checker.check_contract(
    backend_schemas=['backend/app/schemas'],
    frontend_schemas=['frontend/src/types/api'],
)

# 查看结果
print(f"检查通过：{report.passed}")
print(f"得分：{report.score}/100")
print(f"问题数：{len(report.issues)}")

# 输出报告
report.save_to_file('api-contract-report.md')
report.save_to_json('api-contract-report.json')

# 在 Phase Gateway 中使用
if report.has_blocking_issues():
    print("❌ API 契约验证失败，阻断流程")
    for issue in report.issues:
        if issue.severity in ['CRITICAL', 'HIGH']:
            print(f"  - {issue.message}")
    exit(1)
else:
    print("✅ API 契约验证通过，继续流程")
```

### 5.3 集成到 Phase Gateway

```python
# phases/fullstack_development.py

from bmad_evo.api_contract import ApiContractChecker

class FullStackPhaseGateway(PhaseGateway):
    
    def validate_contract_phase(self) -> PhaseResult:
        """API 契约验证阶段"""
        
        checker = ApiContractChecker()
        report = checker.check_contract(
            backend_schemas=self.config.backend_schema_path,
            frontend_schemas=self.config.frontend_schema_path,
        )
        
        # 生成报告
        report.save_to_file(f'{self.output_dir}/api-contract-report.md')
        
        # 决定是否阻断
        if report.has_blocking_issues():
            return PhaseResult(
                passed=False,
                reason=f"API 契约验证失败 (得分：{report.score}/100)",
                issues=report.issues,
                suggestions=report.recommendations,
            )
        else:
            return PhaseResult(
                passed=True,
                score=report.score,
                message=f"API 契约验证通过 (得分：{report.score}/100)",
            )
```

---

## 六、报告输出示例

### 6.1 Markdown 报告

```markdown
# API 契约检查报告

**生成时间**: 2026-03-17 22:30:00  
**检查模式**: camelCase 命名约定  
**总体结果**: ❌ 失败 (得分：78/100)

## 统计摘要

- 后端 Schema 数量：5
- 前端 Schema 数量：5
- Schema 配对成功：5
- 检查字段总数：47
- 发现问题总数：8

### 问题分布

| 严重性 | 数量 | 状态 |
|--------|------|------|
| CRITICAL | 2 | ❌ 必须修复 |
| HIGH | 3 | ⚠️ 应该修复 |
| MEDIUM | 2 | 💡 建议修复 |
| LOW | 1 | 📝 可选优化 |

---

## ❌ CRITICAL 问题（2 个）

### 1. 字段类型不匹配

**规则**: `field_type_match`  
**Schema**: `UserCreate`  
**字段**: `age`

**问题描述**:  
后端类型 `int` ≠ 前端类型 `string`

**位置**:
- 后端：`backend/app/schemas/user.py:15`
- 前端：`frontend/src/types/api.ts:23`

**当前定义**:
```python
# backend/app/schemas/user.py
class UserCreate(BaseModel):
    age: int  # ← 后端定义为 int
```

```typescript
// frontend/src/types/api.ts
interface UserCreate {
    age: string;  // ← 前端定义为 string
}
```

**修复建议**:  
将前端类型改为 `number`（TypeScript 中 Python int 对应 number）

```typescript
interface UserCreate {
    age: number;  // ✅ 修复后
}
```

---

### 2. 枚举值不一致

**规则**: `enum_values_match`  
**Schema**: `PostStatus`  
**字段**: `status`

**问题描述**:  
后端枚举值 `[draft, published, archived]` ≠ 前端枚举值 `[draft, published]`

**位置**:
- 后端：`backend/app/schemas/post.py:42`
- 前端：`frontend/src/types/api.ts:58`

**修复建议**:  
前端添加缺失的枚举值 `archived`

```typescript
type PostStatus = 'draft' | 'published' | 'archived';  // ✅ 修复后
```

---

## ⚠️ HIGH 问题（3 个）

### 3. 字段必填性不一致

**规则**: `required_match`  
**Schema**: `UserProfile`  
**字段**: `bio`

**问题描述**:  
后端定义为 **必填**, 前端定义为 **可选**

**修复建议**:  
统一为必填（或都改为可选）

---

## 💡 MEDIUM 问题（2 个）

（略）

---

## 📝 LOW 问题（1 个）

（略）

---

## ✅ 通过的 Schema（3 个）

- `UserResponse` - 完全匹配
- `PostCreate` - 完全匹配
- `CommentBase` - 完全匹配

---

## 建议

1. **立即修复** 2 个 CRITICAL 问题，否则会阻断流程
2. 建议统一使用 `camelCase` 命名约定
3. 考虑启用 `description_sync` 规则，保持文档同步

## 下一步

修复问题后重新运行:
```bash
python -m bmad_evo validate_api_contract --config .bmad-evo/constraints/api-contract.yaml
```
```

### 6.2 JSON 报告（机器可读）

```json
{
  "passed": false,
  "score": 78.5,
  "total_checks": 47,
  "passed_checks": 39,
  "issues": [
    {
      "severity": "CRITICAL",
      "rule": "field_type_match",
      "message": "字段类型不匹配",
      "schema_name": "UserCreate",
      "field_name": "age",
      "detail": "后端类型 'int' ≠ 前端类型 'string'",
      "backend_value": "int",
      "frontend_value": "string",
      "suggestion": "将前端类型改为 number",
      "backend_file": "backend/app/schemas/user.py",
      "backend_line": 15,
      "frontend_file": "frontend/src/types/api.ts",
      "frontend_line": 23
    }
  ],
  "recommendations": [
    "立即修复 2 个 CRITICAL 问题",
    "统一使用 camelCase 命名约定",
    "考虑启用 description_sync 规则"
  ]
}
```

---

## 七、技术实现细节

### 7.1 依赖库

```python
# requirements.txt (新增)

# Python AST（内置）
# ast, inspect, typing

# TypeScript AST 解析
esprima-python==4.0.1  # 或使用 subprocess 调用 tsc

# Vue SFC 解析（可选）
vue-file-parser==0.1.0

# 工具库
pydantic>=2.0.0  # 用于验证配置
rich>=13.0.0     # 终端报告美化
```

### 7.2 命名转换工具

```python
# lib/api_contract/naming.py

def snake_to_camel(name: str) -> str:
    """snake_case → camelCase"""
    parts = name.split('_')
    return parts[0] + ''.join(word.capitalize() for word in parts[1:])

def camel_to_snake(name: str) -> str:
    """camelCase → snake_case"""
    import re
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def normalize_name(name: str, target: str = 'camelCase') -> str:
    """标准化字段名称"""
    if target == 'camelCase':
        if '_' in name:
            return snake_to_camel(name)
        return name
    elif target == 'snake_case':
        if '_' not in name and any(c.isupper() for c in name):
            return camel_to_snake(name)
        return name
    else:
        raise ValueError(f"Unsupported naming convention: {target}")
```

### 7.3 类型解析（Python）

```python
# lib/api_contract/python_type_parser.py

import ast
from typing import Optional, Tuple

def parse_type_annotation(node: ast.AST) -> Tuple[str, dict]:
    """
    解析 Python 类型注解
    
    示例:
        Optional[str] → ('Optional', {'inner': 'str'})
        List[int] → ('List', {'inner': 'int'})
        Dict[str, int] → ('Dict', {'key': 'str', 'value': 'int'})
        Union[str, int] → ('Union', {'options': ['str', 'int']})
    """
    
    if isinstance(node, ast.Name):
        return (node.id, {})
    
    elif isinstance(node, ast.Subscript):
        # 泛型类型
        value = parse_type_annotation(node.value)
        slice_val = parse_type_annotation(node.slice)
        
        return (value[0], {'inner': slice_val[0]})
    
    elif isinstance(node, ast.Attribute):
        # module.Type
        return (f"{node.value.id}.{node.attr}", {})
    
    else:
        return ('Any', {})
```

---

## 八、验收标准

### 8.1 功能验收

- [ ] 能正确提取 Pydantic Model 和 TypeScript Interface
- [ ] 能检测字段名称不一致（包括 snake_case ↔ camelCase）
- [ ] 能检测字段类型不匹配
- [ ] 能检测必填/可选不一致
- [ ] 能检测枚举值不一致
- [ ] 能生成 Markdown 和 JSON 格式报告
- [ ] 报告包含修复建议
- [ ] 在 Phase Gateway 中能正确阻断流程

### 8.2 性能验收

- [ ] 检查 100 个 Schema 耗时 < 5 秒
- [ ] 单个 Schema 检查耗时 < 100ms
- [ ] 内存占用 < 200MB

### 8.3 准确性验收

- [ ] 零误报（正确的定义不报告问题）
- [ ] 零漏报（所有问题都能检测）
- [ ] 类型映射准确率 100%

---

## 九、风险与限制

### 9.1 技术复杂度

#### 9.1.1 前后端差异

- **Python 对异构数据生成的类型定义无法确定**
  ```python
  # 无法静态推断
  def get_data(source: str) -> Union[User, Product, Order]:
      if source == 'user':
          return User(...)
      elif source == 'product':
          return Product(...)
      else:
          return Order(...)
  ```

- **TypeScript 的 `any` 类型无法检查**
  ```typescript
  // 无法检查
  interface LooseSchema {
      data: any;
  }
  ```

- **TypeScript 高级类型（Union、Omit、Partial）需要特殊处理**
  ```typescript
  // 需要解析联合类型
  type UserOrProduct = User | Product;
  
  // 需要解析类型操作
  type PartialUser = Partial<User>;
  type UserWithoutId = Omit<User, 'id'>;
  ```

- **如果 Schema 分散在多个文件中，需要手动指定或搜索**
  ```bash
  # 方案 1：手动指定
  validate_api_contract --backend src/backend/schemas.py --frontend src/frontend/types.ts
  
  # 方案 2：自动搜索（推荐）
  validate_api_contract --auto-discover
  ```

#### 9.1.2 类型系统映射

某些类型映射需要开发者确认：

| Python | TypeScript | 注意事项 |
|--------|-----------|----------|
| `datetime` | `string` | 需要约定格式（ISO8601、时间戳） |
| `bytes` | `string` | Base64 编码 |
| `Decimal` | `number` | 精度丢失风险 |
| `UUID` | `string` | 格式验证 |
| `EmailStr` | `string` | 需要正则验证 |
| `HttpUrl` | `string` | 需要 URL 验证 |

**建议**：在配置文件中显式声明类型映射规则。

#### 9.1.3 抽象语法树 (AST) 复杂性

Python AST 解析对以下情况需要特殊处理：

- **动态类型注解**：`from __future__ import annotations`
- **字符串类型引用**：`field: "ForwardRef"`
- **循环导入**：需要正确的导入顺序
- **泛型参数**：`List[User]`, `Dict[str, Any]`

### 9.2 边界情况

#### Python 边界情况

```python
# ❌ 无法处理：动态类型
class DynamicModel(BaseModel):
    class Config:
        arbitrary_types_allowed = True
    
    callback: Callable  # 无法提取类型信息

# ❌ 无法处理：运行时生成的类
def create_model():
    return type('DynamicModel', (BaseModel,), {'name': str})

# ✅ 可以处理：泛型
class Response(BaseModel, Generic[T]):
    data: T
    status: str
```

#### TypeScript 边界情况

```typescript
// ❌ 无法处理：条件类型
type Conditional<T> = T extends string ? string : number;

// ❌ 无法处理：模板字面量类型
type EventName = `on${Capitalize<string>}`;

// ✅ 可以处理：泛型接口
interface Response<T> {
    data: T;
    status: string;
}

// ✅ 可以处理：映射类型
type Readonly<T> = {
    readonly [P in keyof T]: T[P];
};
```

### 9.3 性能考虑

- **AST 解析**：建议只检查修改的文件（增量检查）
- **CI/CD 集成**：可设定上次提交基线，仅检查变更文件
- **内存优化**：大文件流式解析，避免一次性加载
- **缓存机制**：已检查的文件缓存结果，避免重复检查

---

## 十、后续扩展计划

### Phase 2.5: 自动生成（可选）

**自动生成 TypeS cript 类型定义**

```python
# 输入：Python Pydantic Model
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    email: str

# 输出：TypeScript Interface
# 自动生成到 frontend/src/types/generated.ts
export interface User {
    id: number;
    name: string;
    email: string;
}
```

**实现方式**：
1. 解析 Python AST 提取 Pydantic Model
2. 使用类型映射表转换为 TypeScript 类型
3. 生成 TypeScript 文件并格式化

**扩展功能**：
- 支持生成 Zod Schema（运行时验证）
- 支持生成 API Client（基于 OpenAPI Spec）
- 支持生成 Mock 数据

### Phase 3: API 文档自动化（未来）

**集成 OpenAPI 文档生成**

1. **提取 Pydantic Model** → 生成 OpenAPI Schema
2. **自动同步更新** → 文档即代码
3. **自动生成测试用例** → 基于 Schema 生成

**扩展功能**：
- 集成 Swagger UI
- 自动生成 Postman Collection
- 自动生成 API 测试脚本

---

## 十一、文件清单与总量

### 后端核心模块

| 文件 | 代码行数 |
|------|----------|
| `lib/api_contract/checker.py` | 300 |
| `lib/api_contract/schema_extractor.py` | 150 |
| `lib/api_contract/normalizer.py` | 250 |
| `lib/api_contract/type_mapper.py` | 180 |
| `lib/api_contract/reporter.py` | 200 |
| `lib/api_contract/cli.py` | 180 |
| `lib/api_contract/config.py` | 80 |
| `lib/api_contract/exceptions.py` | 80 |
| `lib/api_contract/utils.py` | 80 |
| `lib/api_contract/__init__.py` | 20 |
| `templates/constraints/api-contract.yaml` | 100 |
| `tests/test_api_contract.py` | 200 |
| `tests/test_contract_check.py` | 300 |
| **后端小计** | **~2120 行** |

### 前端核心模块

| 文件 | 代码行数 |
|------|----------|
| `frontend/src/api-contract/api-contract-checker.ts` | 250 |
| `frontend/src/api-contract/schema-extractor.ts` | 200 |
| `frontend/src/api-contract/normalizer.ts` | 120 |
| `frontend/src/api-contract/type-mapper.ts` | 180 |
| `frontend/src/api-contract/reporter.ts` | 150 |
| `frontend/src/api-contract/cli.ts` | 100 |
| `frontend/src/api-contract/config.ts` | 100 |
| `frontend/src/api-contract/index.ts` | 50 |
| `frontend/src/api-contract/types.ts` | 100 |
| `frontend/tests/api-contract.test.ts` | 200 |
| `frontend/tests/api-contract-check.test.ts` | 250 |
| **前端小计** | **~1700 行** |

### 总计

- **后端**：~2120 行 Python
- **前端**：~1700 行 TypeScript
- **总计**：**~3820 行代码**
- **预计开发周期**：11.5-15.5 天

---

## 十二、时间估算

| 模块 | 任务 | 预计天数 |
|------|------|----------|
| **后端** | Pydantic 解析 + 类型映射 | 1.5-2 天 |
| | Python Schema 提取器 | 2-3 天 |
| | TypeScript Schema 提取器 | 2.5-3 天 |
| | 契约检查器核心实现 | 2-3 天 |
| | 报告生成 | 2 天 |
| | CLI 工具 + 集成测试 | 1.5-2 天 |
| **前端** | AST 解析 + 类型提取 | 1.5-2 天 |
| **文档** | 文档生成 + 集成测试 | 1 天 |
| **集成** | 与 Phase Gateway 集成 | 1-1.5 天 |
| **总计** | | **11.5-15.5 天** |

**备注**：
- 乐观估计基于熟悉 AST 和类型系统的开发者
- 保守估计考虑学习曲线和调试时间
- 可根据优先级分阶段交付

---

## 十三、需要明确确认的事项

### 13.1 设计确认

1. **系统架构**：如本设计所述，是否同意前后端双向 Schema 提取 + 统一校验的架构？
2. **检查规则**：检查范围是否覆盖完整？是否需要增加其他规则？
3. **类型映射**：类型映射表是否需要调整？

### 13.2 优先级确认

1. **后端优先，还是前后端同步开发？**
   - 后端 Python 解析成熟度更高，建议先完成
   - 前端 TypeScript AST 需要额外学习曲线
2. **Phase 2.5（自动生成 TypeScript）是否需要包含在 Phase 2 中？**

### 13.3 技术选型确认

1. **TypeScript AST 解析器**：使用哪个？
   - 方案 A：官方 `typescript`（推荐 TypeScript 社区）
   - 方案 B：`ts-morph`（更高级的 API）
2. **Python AST 扩展库**：是否需要 `libcst` 或 `astor`？
   - 推荐：只用标准 `ast` + `pydantic` 即可
   - 备选：`libcst` 支持更多 Python 语法
3. **前端框架**：
   - 仅集成 TypeScript Interface，还是也要支持 React/Vue？
   - 建议：只支持 TypeScript Interface，React/Vue 组件需要额外的 AST 解析
4. **报告格式**：
   - Markdown + JSON 是否足够？是否需要 HTML 报告？

### 13.4 资源确认

1. **开发人力**：几人投入？全时还是兼职？
2. **测试覆盖**：是否需要编写完整测试用例？预计额外 3-5 天
3. **代码审查**：是否需要 Code Review 流程？

### 13.5 集成方式确认

1. **CI/CD 集成**：
   - 仅本地开发时检查，还是也要 CI 流水线检查？
   - 建议：两者都支持
2. **Phase Gateway 集成**：
   - 在哪个 Phase 检查？建议在 Development 阶段
   - 检查结果是否要阻断流程？
3. **错误处理**：
   - 发现 CRITICAL 问题时如何处理？
   - 建议：发现 CRITICAL 立即阻断，HIGH/MEDIUM 可配置
4. **与现有约束检查的关系**：
   - 是独立的约束类型，还是集成到现有系统中？
   - 建议：作为独立的约束模板，但可以统一报告

### 13.6 验收标准

1. **性能要求**：是否需要明确的性能指标？
   - 建议：单个 Schema < 100ms, 100 个 Schema < 5s
2. **准确性要求**：是否要求零误报/零漏报？
   - 建议：初期允许少量误报，逐步优化
3. **用户体验**：错误信息是否需要支持中文？

---

## 十四、快速原型（可选）

如果需要快速验证核心功能，我们可以先实现一个**最小可用版本（MVP）**

### MVP 范围

**后端**：
- ✅ 支持 Pydantic Model 提取
- ✅ 支持基础的类型映射（int, str, bool, float, List, Dict）
- ✅ 支持字段名和类型检查
- ✅ 输出 Markdown 报告

**前端**：
- ✅ 支持 TypeScript Interface 提取
- ✅ 支持基础的类型映射
- ✅ 与后端 Schema 对比

**不包含**：
- ❌ 泛型参数深度解析
- ❌ 高级类型（Union、Omit 等）
- ❌ 自动生成 TypeScript
- ❌ CI/CD 集成
- ❌ Phase Gateway 集成

### MVP 开发周期

- **开发**：5-7 天
- **测试**：2-3 天
- **总计**：**7-10 天**

### MVP 验收

1. 能正确提取简单的 Pydantic Model 和 TypeScript Interface
2. 能检测字段名和类型不匹配
3. 能生成基础的 Markdown 报告

---

## 确认

在开始开发之前，请确认：

1. **设计是否符合你的期望？**
   - 是否有需要调整的部分？
2. **优先级如何确定？**
   - 是完整实现 Phase 2，还是先做 MVP？
   - 前后端同步开发，还是后端优先？
3. **技术选型是否有偏好？**
   - TypeScript AST 解析器选择

**约定**：
- 如果**明天早上 8:45 没有收到你的回复**，我默认按照**保守方案**执行：
  - **后端优先**：先完整实现后端 Python Schema 提取和检查
  - **前端后续**：后端完成后再开始前端开发
  - **技术选型**：使用官方 `typescript` 库解析 TypeScript AST
  - **范围**：完整 Phase 2（不包含 Phase 2.5 自动生成）
  - **集成**：包含 Phase Gateway 集成和 CI/CD 支持
- 这样可以在 **11.5-15.5 天** 内交付完整功能

**准备好开始了吗？** 🚀

---

## 八、验收标准

### 8.1 功能验收

- [ ] 能正确提取 Pydantic Model 和 TypeScript Interface
- [ ] 能检测字段名称不一致（包括 snake_case ↔ camelCase）
- [ ] 能检测字段类型不匹配
- [ ] 能检测必填/可选不一致
- [ ] 能检测枚举值不一致
- [ ] 能生成 Markdown 和 JSON 格式报告
- [ ] 报告包含修复建议
- [ ] 在 Phase Gateway 中能正确阻断流程

### 8.2 性能验收

- [ ] 检查 100 个 Schema 耗时 < 5 秒
- [ ] 单个 Schema 检查耗时 < 100ms
- [ ] 内存占用 < 200MB

### 8.3 准确性验收

- [ ] 零误报（正确的定义不报告问题）
- [ ] 零漏报（所有问题都能检测）
- [ ] 类型映射准确率 100%

