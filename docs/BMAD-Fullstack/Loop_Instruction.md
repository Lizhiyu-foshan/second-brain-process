# BMAD-Fullstack 迭代开发闭环流程

## 概述

本文档描述使用 BMAD-Fullstack 进行日常迭代开发的完整闭环流程，包含需求评估、开发、审计、测试、Bug修复。

---

## 完整流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                     阶段 0: 需求输入与评估                         │
├─────────────────────────────────────────────────────────────────┤
│  1. 新需求/需求变更 → 2. 影响评估 → 3. 更新契约文档                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     迭代循环 (单次功能开发)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │ 后端开发     │ → │ 后端审计     │ → │ 后端测试     │         │
│  │ (Pydantic)  │    │ (BMAD-EVO)  │    │ (Pytest)    │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│        ↓                  ↓                  ↓                  │
│   修Bug/重构 ←── 不通过 ──┘           不通过 ──┘                 │
│        ↓                                                        │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │ 生成前端类型 │ → │ 前端开发     │ → │ 前端审计     │         │
│  │(BMAD-FS)   │    │ (React)     │    │ (ESLint/TS) │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│        ↓                  ↓                  ↓                  │
│   修Bug/重构 ←── 类型错误 ──┘          不通过 ──┘                 │
│        ↓                                                        │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │ 契约一致性   │ → │ 集成测试     │ → │ 联调测试     │         │
│  │ 检查       │    │ (API Test)  │    │ (E2E)       │         │
│  │(BMAD-FS)   │    │             │    │             │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│        ↓                  ↓                  ↓                  │
│   修Bug/重构 ←── 不通过 ──┘           不通过 ──┘                 │
│        ↓                                                        │
│  ┌─────────────┐                                               │
│  │   ✅ 完成   │ ──→ 合并到主分支 → 部署到测试环境               │
│  └─────────────┘                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     阶段 N: 滚动需求输入                          │
│                     (回到阶段 0，开始下一次迭代)                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 阶段 0：需求输入与评估

### 0.1 创建功能需求文档

`.bmad/features/feature-XXX.yaml`：

```yaml
feature:
  id: "FEAT-001"
  name: "用户认证系统"
  status: "ready"  # draft → ready → in_progress → done
  
  description: |
    实现用户注册、登录、JWT Token 认证
  
  # API 契约变更
  api_changes:
    new_schemas:
      - name: "UserRegister"
        fields:
          username: string (required, 3-50字符)
          email: string (required, email格式)
          password: string (required, 6-20字符)
      
      - name: "AuthResponse"
        fields:
          access_token: string (required)
          token_type: string (default: "bearer")
          expires_in: integer (required)
  
  # 影响评估
  impact:
    backend:
      - 新增 auth 模块
      - 新增 JWT 依赖
    frontend:
      - 新增登录页面
      - 新增注册页面
  
  # 验收标准
  acceptance_criteria:
    - 用户可以注册新账号
    - 用户可以用邮箱密码登录
```

### 0.2 评估会议（5-10分钟）

```bash
# 1. 架构师/后端/前端一起评审
# 2. 确认契约变更是否合理
# 3. 确认影响范围
# 4. 更新 .bmad/api-contract.yaml
```

### 0.3 更新 API 契约文档

```yaml
# .bmad/api-contract.yaml
api:
  name: "用户管理系统"
  version: "v1"

endpoints:
  - path: /api/auth/register
    method: POST
    request: UserRegister
    response: AuthResponse
    
  - path: /api/auth/login
    method: POST
    request: UserLogin
    response: AuthResponse
```

---

## 迭代循环详细步骤

### 第 1 步：后端开发 + 审计 + 测试

#### 1.1 开发 Pydantic Schema

```python
# backend/app/schemas/auth.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserRegister(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=20)
```

#### 1.2 BMAD-EVO 代码审计

```bash
# 审计后端代码质量
cd backend
bmad-evo audit --phase development --file app/schemas/auth.py
```

**可能输出**：
```
🔍 审计结果: 85/100 ✅ 通过

发现 1 个中等问题:
- [异常处理] UserRegister 缺少输入验证异常处理
建议: 添加 try-except 处理 ValidationError
```

**修复代码**：

```python
from pydantic import BaseModel, EmailStr, Field, ValidationError
from fastapi import HTTPException

class UserRegister(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=20)
    
    @validator('username')
    def validate_username(cls, v):
        if not v.isalnum():
            raise ValueError('用户名只能包含字母和数字')
        return v

# 在路由中添加异常处理
@router.post("/auth/register")
async def register(user: UserRegister):
    try:
        # 业务逻辑...
        return AuthResponse(access_token="xxx", expires_in=3600)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"注册失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")
```

#### 1.3 后端单元测试

```python
# backend/tests/test_auth.py
import pytest
from app.schemas.auth import UserRegister, UserLogin, AuthResponse

def test_user_register_schema():
    """测试用户注册 Schema"""
    # 正常情况
    data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "123456"
    }
    user = UserRegister(**data)
    assert user.username == "testuser"
    
    # 边界情况 - 用户名太短
    with pytest.raises(ValueError):
        UserRegister(username="ab", email="test@example.com", password="123456")

# 运行测试
# pytest backend/tests/test_auth.py -v
```

**通过标准**：审计 ≥85分 + 单元测试全部通过

---

### 第 2 步：生成前端类型 + 前端开发 + 审计

#### 2.1 生成 TypeScript 类型

```bash
# 后端审计和测试通过后，生成前端类型
bmad-fullstack generate-ts \
  --input backend/app/schemas \
  --output frontend/src/types/api.ts
```

#### 2.2 前端开发

```tsx
// frontend/src/pages/Register.tsx
import { useState } from 'react';
import { UserRegister } from '../types/api';  // 使用生成的类型
import { authApi } from '../api/auth';

export function RegisterPage() {
  const [form, setForm] = useState<UserRegister>({
    username: '',
    email: '',
    password: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const response = await authApi.register(form);
    localStorage.setItem('token', response.accessToken);
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        value={form.username}
        onChange={e => setForm({...form, username: e.target.value})}
        placeholder="用户名"
      />
      <button type="submit">注册</button>
    </form>
  );
}
```

#### 2.3 前端审计

```bash
cd frontend

# TypeScript 类型检查
npx tsc --noEmit

# ESLint 代码检查
npm run lint
```

**通过标准**：TypeScript 无错误 + ESLint 无警告

---

### 第 3 步：契约一致性检查

```bash
# 前后端都开发完成后，进行最终契约检查
bmad-fullstack check \
  --backend backend/app/schemas \
  --frontend frontend/src/types \
  --strict
```

**可能发现的问题**：

```
❌ 契约不一致发现:

1. [类型不匹配] AuthResponse.expires_in
   - 后端: expires_in: int
   - 前端: expiresIn: string
   建议: 前端类型应为 number
```

**修复流程**：

```bash
# 重新生成前端类型
bmad-fullstack generate-ts \
  --input backend/app/schemas \
  --output frontend/src/types/api.ts \
  --naming camelCase

# 重新检查
bmad-fullstack check --strict
```

---

### 第 4 步：集成测试 + 联调

#### 4.1 集成测试

```python
# backend/tests/test_integration_auth.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_register_and_login():
    """测试注册和登录流程"""
    # 1. 注册
    register_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "123456"
    }
    response = client.post("/api/auth/register", json=register_data)
    assert response.status_code == 200
    assert "access_token" in response.json()
    
    # 2. 登录
    login_data = {
        "email": "test@example.com",
        "password": "123456"
    }
    response = client.post("/api/auth/login", json=login_data)
    assert response.status_code == 200

# 运行集成测试
# pytest backend/tests/test_integration_auth.py -v
```

#### 4.2 联调测试

```bash
# 1. 启动后端
cd backend && uvicorn app.main:app --reload --port 8000

# 2. 启动前端
cd frontend && npm run dev

# 3. 打开浏览器测试 http://localhost:5173/register
```

---

## Bug 修复闭环流程

```
发现 Bug
    ↓
┌────────────────────────────────────────────────────────┐
│  分类 Bug 类型                                          │
│  1. 契约不一致 (前后端类型不匹配) → 修改 Schema + 重新生成 │
│  2. 后端逻辑错误 → 修改后端代码 + 重新审计 + 测试          │
│  3. 前端逻辑错误 → 修改前端代码 + 重新审计                │
│  4. 需求理解错误 → 更新契约文档 + 重新开发                │
└────────────────────────────────────────────────────────┘
    ↓
执行修复
    ↓
重新执行完整的迭代循环 (从对应步骤开始)
    ↓
验证修复
    ↓
✅ 关闭 Bug
```

### Bug 修复示例

```bash
# Bug 报告: 注册时用户名可以包含特殊字符

# 1. 分析: 这是后端验证不完善，属于类型 2 Bug

# 2. 修改后端 Schema
# backend/app/schemas/auth.py
class UserRegister(BaseModel):
    username: str = Field(
        ..., 
        min_length=3, 
        max_length=50,
        pattern=r'^[a-zA-Z0-9_]+$'  # 新增正则验证
    )

# 3. 重新审计
bmad-evo audit --file backend/app/schemas/auth.py

# 4. 重新测试
pytest backend/tests/test_auth.py -v

# 5. 重新生成前端类型
bmad-fullstack generate-ts \
  --input backend/app/schemas \
  --output frontend/src/types/api.ts

# 6. 重新检查契约一致性
bmad-fullstack check --strict

# 7. 集成测试
pytest backend/tests/test_integration_auth.py -v

# 8. 联调验证
# 手动测试注册功能，确认特殊字符被阻止
```

---

## 日常开发命令速查表

```bash
# ========== 日常开发迭代 ==========

# 1. 拉取最新代码
git pull origin main

# 2. 查看待办需求
cat .bmad/features/feature-XXX.yaml

# 3. 开始开发前：检查当前契约状态
bmad-fullstack check --backend backend/app/schemas

# 4. 后端开发...
vim backend/app/schemas/xxx.py

# 5. 后端开发完成：审计 + 测试
bmad-evo audit --file backend/app/schemas/xxx.py
pytest backend/tests/test_xxx.py -v

# 6. 生成前端类型
bmad-fullstack generate-ts \
  --input backend/app/schemas \
  --output frontend/src/types/api.ts

# 7. 前端开发...
vim frontend/src/pages/Xxx.tsx

# 8. 前端开发完成：审计
cd frontend && npx tsc --noEmit && npm run lint

# 9. 最终契约检查
bmad-fullstack check --strict

# 10. 集成测试
pytest backend/tests/test_integration_xxx.py -v

# 11. 提交代码
git add .
git commit -m "feat: 实现 XXX 功能

- 新增 Xxx Schema
- 实现 API 端点
- 前端页面开发
- 通过 BMAD-EVO 审计
- 通过 BMAD-Fullstack 契约检查"

# 12. CI 自动执行审计和测试
git push origin feature/xxx
```

---

## 关键原则

| 原则 | 说明 |
|------|------|
| **契约优先** | 任何需求变更先更新契约文档，再开发 |
| **审计驱动** | 后端代码必须通过 BMAD-EVO 审计（85分） |
| **类型生成** | 前端类型必须从后端自动生成，禁止手撕 |
| **一致性检查** | 每次提交前必须检查前后端契约一致性 |
| **测试覆盖** | 每个 Schema 必须有单元测试，每个 API 必须有集成测试 |
| **Bug闭环** | 发现 Bug → 分类 → 修复 → 重新走完整流程 |

---

## 下一步

完成阅读本文档后，参考 `Setting.md` 进行项目初始化配置。
