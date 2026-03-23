# BMAD-Kimi v3.0 增强设计方案

> 基于用户需求的三大改进：HTML快速原型、迭代优化、EVO无缝对接

---

## 一、改进总览

| 改进点 | 当前状态 | 目标状态 | 价值 |
|--------|---------|---------|------|
| **快速原型** | ASCII线框图 | 可运行的HTML demo | 客户可点击体验 |
| **迭代优化** | 单轮设计 | 多轮需求变更支持 | 持续优化原型 |
| **EVO对接** | 手动交接 | 自动生成约束文件 | 开发无缝对接 |

---

## 二、详细设计

### 改进1：HTML Demo快速原型

#### 新增命令
```bash
bk prototype [--format html|react|vue] [--iterations N]
```

#### 输出规格
- **文件格式**: 单文件 HTML (内联 CSS/JS)
- **CSS框架**: Tailwind CSS (CDN引入)
- **响应式**: 适配桌面/平板/手机
- **交互**: 关键流程可点击跳转
- **内容**: 使用模拟数据填充

#### 流程设计
```
需求输入
    ↓
[Phase 1] 结构分析 (K2.5)
- 识别页面层级
- 确定导航结构
- 定义路由关系
    ↓
[Phase 2] 原型生成 (K2.5)
- 生成HTML骨架
- 应用Tailwind样式
- 实现基础交互
    ↓
[Phase 3] 交互增强 (K2.5)
- 页面间跳转逻辑
- 表单验证反馈
- 状态变化模拟
    ↓
输出: demo-v1.html
```

#### 示例输出结构
```html
<!DOCTYPE html>
<html>
<head>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>/* 自定义样式 */</style>
</head>
<body>
  <!-- 页面1: 首页 -->
  <div id="page-home" class="page active">...</div>
  
  <!-- 页面2: 详情页 -->
  <div id="page-detail" class="page hidden">...</div>
  
  <!-- 页面3: 表单页 -->
  <div id="page-form" class="page hidden">...</div>
  
  <script>
    // 路由切换逻辑
    // 模拟数据
    // 交互处理
  </script>
</body>
</html>
```

---

### 改进2：支持多次交互的需求变更

#### 新增命令
```bash
bk refine [--from demo-v{N}.html] [--feedback "变更描述"]
```

#### 迭代流程
```
用户查看 demo-v1.html
    ↓
提供反馈: "调整导航栏样式，增加搜索功能"
    ↓
bk refine --from demo-v1.html --feedback "..."
    ↓
[Change Analyzer] 解析变更需求
- 识别新增/修改/删除
- 评估影响范围
- 确定保持不变的元素
    ↓
[Prototype Evolver] 生成新版本
- 继承已有结构
- 应用增量变更
- 保持视觉一致性
    ↓
输出: demo-v2.html + changelog.md
```

#### 变更追踪
```yaml
# changelog.md
version: 2
previous: demo-v1.html
changes:
  - type: modify
    element: "导航栏"
    description: "改为悬浮样式，增加搜索框"
  - type: add
    element: "搜索功能"
    description: "增加全局搜索，支持实时建议"
  - type: keep
    element: "商品列表"
    description: "保持原有布局和交互"
```

#### 迭代计数器
```bash
# 自动生成版本号
demo-v1.html  # 初版
demo-v2.html  # 第1次迭代
demo-v3.html  # 第2次迭代
...
```

---

### 改进3：输出功能需求和约束文件（EVO对接）

#### 新增命令
```bash
bk handoff [--from demo-v{N}.html] [--to ./evolution-project/]
```

#### 输出文件

**1. 功能需求文档 (functional-requirements.md)**
```markdown
# 功能需求文档

## 页面清单
| 页面ID | 名称 | 路由 | 说明 |
|--------|------|------|------|
| page-home | 首页 | / | 商品展示入口 |
| page-detail | 详情 | /detail/:id | 商品详情页 |
| page-cart | 购物车 | /cart | 购物车管理 |

## 功能列表

### F001: 商品搜索
- **优先级**: P0
- **来源**: demo-v2.html 导航栏
- **功能描述**: 全局搜索框，支持关键词搜索
- **输入**: 关键词字符串
- **输出**: 商品列表
- **约束**: 响应时间 < 500ms

### F002: 商品详情
- **优先级**: P0
- **来源**: demo-v2.html 详情页
- **功能描述**: 展示商品图片、价格、描述
- **约束**: 图片懒加载、支持放大查看

## 非功能需求
- 响应式: 适配 320px-1920px
- 性能: 首屏加载 < 2s
- 兼容性: Chrome/Firefox/Safari 最新2版本
```

**2. 项目约束文件 (constraints.yaml)**
```yaml
name: 项目约束
version: 1.0.0
source: BMAD-Kimi原型 handoff

architecture:
  - id: A001
    level: critical
    name: 单页应用架构
    description: 必须使用SPA架构，支持前端路由
    evidence: demo-v2.html 使用div切换模拟多页

  - id: A002
    level: high
    name: Tailwind CSS
    description: 使用Tailwind作为CSS框架
    evidence: demo-v2.html 已验证设计系统

design:
  - id: D001
    level: high
    name: 响应式布局
    description: 必须支持移动端/桌面端自适应
    evidence: demo-v2.html 包含响应式断点

  - id: D002
    level: medium
    name: 导航栏悬浮
    description: 导航栏始终置顶
    evidence: demo-v2.html 第2版修改

functionality:
  - id: F001
    level: critical
    name: 页面路由
    description: 实现前端路由，支持浏览器前进/后退
    evidence: demo-v2.html 路由切换逻辑

  - id: F002
    level: high
    name: 表单验证
    description: 所有表单必须有客户端验证
    evidence: demo-v2.html 表单页交互

performance:
  - id: P001
    level: medium
    name: 首屏加载
    description: 首屏加载时间 < 2s
    target: 2000ms
```

**3. 设计资产 (design-assets/)**
```
design-assets/
├── color-system.md      # 色彩系统
├── typography.md        # 字体规范
├── spacing.md           # 间距系统
├── components.md        # 组件清单
└── screens/             # 页面截图
    ├── home.png
    ├── detail.png
    └── cart.png
```

---

## 三、增强后的完整流程

```
Day 1: 快速原型阶段
├── bk analyst          → 项目简报
├── bk prototype        → demo-v1.html (初版)
└── 客户反馈

Day 2-3: 迭代优化阶段
├── bk refine           → demo-v2.html (第1轮)
├── 客户反馈
├── bk refine           → demo-v3.html (第2轮)
└── 客户确认 ✅

Day 4: 开发交接阶段
├── bk handoff          → 功能需求 + 约束文件
└── 复制到 EVO 项目

Day 5+: BMAD-EVO 开发
├── bmad-evo run-v3     → 基于约束自动开发
└── 持续集成
```

---

## 四、命令对照表

| 原命令 | 新命令 | 变更说明 |
|--------|--------|---------|
| `bk ux-wireframe` | `bk prototype` | 输出从ASCII改为HTML |
| `bk ux-visual` | `bk refine` | 支持多轮迭代 |
| - | `bk handoff` | 新增EVO对接命令 |

---

## 五、技术实现要点

### 1. HTML生成Prompt模板
```
基于以下需求，生成可运行的单文件HTML demo：

需求: {user_requirement}

要求：
1. 单文件HTML，内联所有CSS和JS
2. 使用Tailwind CSS CDN
3. 响应式：支持移动端/桌面端
4. 包含3-5个核心页面
5. 页面间可跳转（使用JS模拟路由）
6. 使用模拟数据填充内容
7. 关键交互可点击（按钮、链接、表单）

输出格式：
```html
<!DOCTYPE html>
...
```
```

### 2. 变更分析Prompt模板
```
分析以下原型变更需求：

当前版本: {current_demo}
用户反馈: {feedback}

任务：
1. 识别具体变更点（新增/修改/删除）
2. 评估对现有结构的影响
3. 确定保持不变的元素

输出JSON格式：
{
  "changes": [
    {"type": "add|modify|delete", "element": "...", "description": "..."}
  ],
  "keep": ["保持不变的元素"],
  "risk": "变更风险等级"
}
```

### 3. 约束提取Prompt模板
```
从HTML原型中提取项目约束：

原型文件: {demo_file}

提取：
1. 架构约束（SPA/多页、技术栈）
2. 设计约束（响应式、色彩、布局）
3. 功能约束（路由、表单、交互）
4. 性能约束（加载时间、动画要求）

输出标准BMAD-EVO约束YAML格式
```

---

## 六、验收标准

- [ ] `bk prototype` 可在5分钟内生成可运行HTML
- [ ] HTML包含至少3个可跳转页面
- [ ] 响应式布局在Chrome DevTools中验证通过
- [ ] `bk refine` 支持3次以上迭代
- [ ] 每次迭代保留变更历史
- [ ] `bk handoff` 生成标准EVO约束文件
- [ ] 约束文件可通过BMAD-EVO的验证

---

请审阅此设计文档，确认后我将开始实现。
