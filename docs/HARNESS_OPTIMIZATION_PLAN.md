---
date: 2026-03-23
type: 系统优化建议
source: Harness Engineering 分析
status: 待实施
---

# Kimi Claw 系统 Harness 优化建议

**分析基于**：
1. 《模型不是关键，Harness 才是》（兔兔AGI）
2. 《The Anatomy of an Agent Harness》（LangChain）

---

## 一、当前系统 Harness 成熟度评估

| 组件 | 当前状态 | 成熟度 | 优化优先级 |
|------|---------|--------|-----------|
| **文件系统** | Obsidian Vault 结构化存储 | ⭐⭐⭐⭐ | 中 |
| **记忆系统** | AGENTS.md + MEMORY.md | ⭐⭐⭐⭐⭐ | 高 |
| **工具链** | 20+ Skills 已安装 | ⭐⭐⭐⭐ | 中 |
| **反馈循环** | 定时任务监控 + 健康检查 | ⭐⭐⭐ | 高 |
| **约束系统** | AGENTS.md 规则体系 | ⭐⭐⭐⭐⭐ | 高 |
| **上下文管理** | 动态压缩守护 | ⭐⭐⭐⭐ | 中 |
| **自我验证** | 四步整理流程 | ⭐⭐⭐ | 高 |

---

## 二、核心优化建议（按优先级排序）

### 🔴 高优先级：反馈循环与自我验证

#### 1. 建立「错误 → 规则」的 Harness 工程闭环

**参考 Mitchell Hashimoto 的 Ghostty 实践**：
> AGENTS.md 文件里的每一行规则，背后都对应着 Agent 曾经犯过的一个错。

**当前实践**：
- ✅ AGENTS.md 已有规则体系
- ✅ .learnings/ 目录记录错误

**建议改进**：
```
错误发生 → 记录到 .learnings/ERRORS.md → 提炼规则 → 更新 AGENTS.md → 部署验证
     ↑                                                        ↓
     └──────────────── 监控是否再次犯错 ←──────────────────────┘
```

**具体操作**：
1. 每次错误发生后，在 `.learnings/ERRORS.md` 中记录：
   - 错误时间、场景、根因
   - 修复方案
   - 预防措施（即 AGENTS.md 新规则）
2. 每月 review，将高频错误转化为 AGENTS.md 规则
3. 添加「规则有效性检查」定时任务

#### 2. 强化自我验证循环

**当前**：四步整理流程（Step 1-4）

**建议升级为**：
```
Step 1: 识别精华
Step 2: 生成精华
Step 3: 整理剩余
Step 4: 推送GitHub
Step 5: 验证完整性 ← 新增
Step 6: 反馈记录   ← 新增
```

**Step 5 验证内容**：
- [ ] GitHub 文件是否正确生成
- [ ] Dashboard 计数是否更新
- [ ] 链接是否可访问
- [ ] 内容格式是否符合规范

**Step 6 反馈记录**：
- 记录本次处理的问题
- 更新到 `.learnings/LEARNINGS.md`

---

### 🟡 中优先级：上下文管理与状态持久化

#### 3. 优化上下文压缩策略

**当前问题**：
- 上下文压缩触发条件：100条消息或25万Token
- 压缩时机不够智能

**建议改进**：
```python
# 智能压缩触发器
class SmartCompaction:
    def should_compact(self, session):
        # 基础条件
        if session.message_count > 100:
            return True
        if session.token_count > 200000:
            return True
            
        # 智能条件（新增）
        if self.is_task_complete(session):  # 任务已完成
            return True
        if self.is_context_irrelevant(session):  # 上下文已偏离当前任务
            return True
        if session.idle_time > 3600:  # 空闲超过1小时
            return True
            
        return False
```

#### 4. 增强记忆系统（文件即协作接口）

**Harness 原理**：文件系统是最基础的 Harness 原语

**建议**：
1. **标准化记忆文件格式**：
   ```markdown
   ---
   type: memory
   category: [error|learning|decision]
   date: 2026-03-23
   related_rules: [AGENTS.md#rule-4, AGENTS.md#rule-7]
   status: [active|deprecated]
   ---
   
   ## 事件描述
   
   ## 根因分析
   
   ## 解决方案
   
   ## 预防措施
   
   ## 相关链接
   ```

2. **建立记忆索引系统**：
   - `memory/index.md` - 按类别索引所有记忆
   - 定时任务每周更新索引

3. **记忆检索优化**：
   - 使用 `memory_search` 替代全文检索
   - 添加标签系统，便于快速定位

---

### 🟢 低优先级：工具链与编排优化

#### 5. Skill 懒加载机制

**Harness 原理**：按需加载（渐进式披露）

**当前问题**：所有 skill 的 TOOLS.md 可能在启动时加载

**建议**：
```yaml
# skill-manifest.yaml
skills:
  feishu-doc:
    auto_load: false  # 不自动加载
    trigger_keywords: ["飞书", "文档", "docx"]  # 触发词
    
  daily-report:
    auto_load: false
    trigger_keywords: ["日报", "daily report"]
```

#### 6. 多 Agent 协作机制

**Harness 原理**：Harness 提供编排逻辑

**建议场景**：
```
复杂任务分解：
├─ 主 Agent（协调）
│  ├─ 子 Agent A（信息收集）
│  ├─ 子 Agent B（分析）
│  └─ 子 Agent C（输出）
│
└─ 通过文件系统共享状态
   ├─ /tmp/task_123/input.md
   ├─ /tmp/task_123/analysis.md
   └─ /tmp/task_123/output.md
```

---

## 三、具体实施计划

### 第一阶段：建立反馈闭环（1周内）

- [ ] 更新 `.learnings/ERRORS.md` 模板
- [ ] 创建错误 → 规则转化流程
- [ ] 添加 AGENTS.md 规则有效性检查

### 第二阶段：增强自我验证（2周内）

- [ ] 在四步流程中增加 Step 5-6
- [ ] 创建验证脚本 `verify_output.py`
- [ ] 建立反馈记录自动化

### 第三阶段：优化上下文管理（1个月内）

- [ ] 实现智能压缩触发器
- [ ] 优化记忆索引系统
- [ ] 测试懒加载机制

---

## 四、关键度量指标

| 指标 | 当前基线 | 目标 | 测量方式 |
|------|---------|------|---------|
| 重复错误率 | - | < 5% | 统计 .learnings/ERRORS.md 重复问题 |
| 任务完成率 | - | > 95% | 定时任务成功执行比例 |
| 上下文压缩效率 | - | -20% Token | 平均每会话 Token 数 |
| 规则覆盖率 | - | 100% | 错误转化为规则的比例 |

---

## 五、参考引用

1. Mitchell Hashimoto - Engineer the Harness (2026-02)
2. LangChain - The Anatomy of an Agent Harness
3. Nate B Jones - Harness Performance Study (42% → 78%)
4. Terminal Bench 2.0 - Harness Optimization Results

---

*生成时间：2026-03-23*
*状态：待讨论和优先级确认*
