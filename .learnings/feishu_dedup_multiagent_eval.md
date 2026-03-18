# Feishu 消息去重集成方案 - 多角色协同评估报告

**评估日期**: 2026-03-16  
**评估人员**: 架构师 / 风险评估师 / 运维工程师（多角色协同）  
**版本**: v1.0

---

## 📋 执行摘要

### 问题定义
用户在 Feishu 收到重复回复。已有两个去重机制但未正确集成，导致去重失败。

### 核心发现
| 维度 | 发现 |
|------|------|
| **根本原因** | 脚本层去重（`feishu_receive_dedup.py`）未被插件层调用，形成"孤岛"机制 |
| **当前状态** | 仅插件层内存去重生效（30分钟TTL），脚本层去重处于未激活状态 |
| **风险等级** | 中等 - 影响用户体验但非系统崩溃性风险 |

### 推荐方案
**方案 B：混合去重模式（推荐）** - 在插件层 `dedup.ts` 中集成脚本层调用，形成双重保障机制。

---

## 🔍 问题根因分析

### 1. 现有去重机制现状

```
┌─────────────────────────────────────────────────────────────────┐
│                      当前架构（问题状态）                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Feishu消息 ──▶ 插件层(bot.ts:916)                              │
│                    │                                            │
│                    ▼                                            │
│            ┌─────────────┐      ┌──────────────────────┐       │
│            │ dedup.ts    │      │ feishu_receive_      │       │
│            │ 内存去重    │      │ dedup.py             │       │
│            │ ✓ 已激活   │      │ ✗ 未激活（孤岛）     │       │
│            │             │      │                      │       │
│            │ • message_id│      │ • 内容指纹           │       │
│            │ • 30分钟TTL │      │ • 12小时窗口         │       │
│            │ • 内存存储  │      │ • 文件持久化         │       │
│            └──────┬──────┘      └──────────────────────┘       │
│                   │                                             │
│                   ▼                                             │
│            消息分发到Agent                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2. 为什么有去重还会重复？

#### 场景 A：插件重启导致内存去重失效
```
时间线：
T+0min    用户发送消息 M1
T+1min    插件处理 M1，记录到内存 Map
T+5min    插件重启（部署/崩溃）
T+6min    Feishu 重试发送 M1（认为之前超时）
T+6min    新插件进程 → 内存 Map 为空 → 视为新消息 → 重复回复
```

#### 场景 B：跨账号去重失效
```
场景：同一用户向多个账号发送相同消息
账号A 收到 "测试" → 记录到 dedupAccountId="accountA" 
账号B 收到 "测试" → dedupKey="accountB:测试" → 不重复 → 重复回复
```

#### 场景 C：Message ID 变更（飞书重试机制）
```
飞书重试策略：
- 首次发送：message_id = "om_abc123"
- 5秒后无响应：重试，message_id = "om_def456" （新ID！）
- 插件 dedup.ts：基于 message_id → 视为新消息 → 重复回复
```

#### 场景 D：消息内容相同但 ID 不同
```
用户操作：
- 复制粘贴相同内容多次发送
- 每次 message_id 不同
- 插件层：视为不同消息
- 脚本层（如果启用）：内容指纹匹配 → 识别重复
```

### 3. 代码层面证据

#### 插件层去重调用点（bot.ts:916）
```typescript
// Dedup check: skip if this message was already processed
const messageId = event.message.message_id;
const dedupAccountId = accountId || "default";
if (!tryRecordMessage(messageId, dedupAccountId)) {  // ← 仅调用插件层
  log(`feishu: skipping duplicate message ${messageId}`);
  return;
}
// ❌ 未调用 feishu_receive_dedup.py 的任何函数
```

#### 脚本层去重（未激活）
```python
# feishu_receive_dedup.py 提供以下函数但未被调用：
- is_message_received(content, sender)  # 检查是否重复
- record_message_received(content, sender)  # 记录消息
- check_and_record_message(content, sender)  # 原子操作
```

---

## 🏗️ 架构师角色分析

### 1. 插件层去重 vs 脚本层去重对比

| 对比维度 | 插件层去重 (dedup.ts) | 脚本层去重 (feishu_receive_dedup.py) |
|---------|----------------------|-------------------------------------|
| **去重键** | message_id（精确匹配） | 内容指纹（模糊匹配） |
| **存储方式** | 内存 Map | JSON 文件 |
| **持久化** | ❌ 重启丢失 | ✅ 持久化 |
| **TTL** | 30 分钟 | 12 小时 |
| **容量限制** | 1000 条 | 500 条 |
| **匹配精度** | 100%（ID相同即重复） | 高（内容相同即重复） |
| **跨账号支持** | 需要 scope 参数 | 内置 sender 维度 |
| **性能** | ⚡ 内存操作 O(1) | 🐢 文件 I/O + 锁 |
| **依赖** | 无 | Python 运行时 |
| **维护成本** | 低 | 中等 |

### 2. 两种去重机制的优劣分析

#### 插件层去重优势
1. **高性能**：纯内存操作，微秒级延迟
2. **精确匹配**：message_id 是飞书官方唯一标识，无误判
3. **无依赖**：不依赖外部 Python 环境
4. **实时清理**：5分钟间隔自动清理过期条目

#### 插件层去重劣势
1. **易失性**：进程重启即丢失所有记录
2. **短TTL**：30分钟可能不足以覆盖飞书所有重试场景
3. **ID敏感**：飞书重试可能生成新 message_id
4. **跨进程无效**：多实例部署时无法共享状态

#### 脚本层去重优势
1. **持久化**：文件存储，重启后仍然有效
2. **长窗口**：12小时覆盖飞书重试周期
3. **内容指纹**：不依赖 message_id，识别内容重复
4. **跨账号**：可识别同一用户的多账号重复

#### 脚本层去重劣势
1. **性能开销**：文件 I/O + JSON 解析 + 线程锁
2. **容量限制**：仅保留500条（循环覆盖）
3. **模糊匹配**：可能误判相似内容为重复
4. **维护复杂度**：需要管理 Python 依赖

### 3. 是否有必要集成脚本层去重？

**结论：有必要，但不是替代关系，而是互补关系**

#### 必要性论证

| 场景 | 仅插件层 | 集成脚本层 | 必要性 |
|------|---------|-----------|--------|
| 插件重启后飞书重试 | ❌ 重复回复 | ✅ 去重成功 | **高** |
| 飞书生成新 message_id | ❌ 重复回复 | ✅ 内容指纹识别 | **高** |
| 用户复制粘贴重复发送 | ❌ 重复回复 | ✅ 内容识别 | 中 |
| 正常单实例运行 | ✅ 去重成功 | ✅ 双重保障 | 低 |

#### 集成价值
1. **兜底保障**：当插件层失效时（重启），脚本层作为第二道防线
2. **内容级去重**：捕获 message_id 变化但内容相同的场景
3. **审计追踪**：文件记录可用于事后分析重复模式
4. **符合设计意图**：既然编写了脚本层去重，就应该激活使用

### 4. 最佳集成点分析

#### 选项 A：TypeScript 直接读取 JSON 文件
```typescript
// dedup.ts 中直接读取 received_messages.json
// 劣势：需要维护两套文件解析逻辑
// 复杂度：★★★☆☆
```

#### 选项 B：TypeScript 调用 Python 脚本（推荐）
```typescript
// dedup.ts 中通过 child_process 调用 Python
// 优势：复用现有逻辑，单一事实来源
// 复杂度：★★☆☆☆
```

#### 选项 C：独立去重服务
```
// 启动独立进程提供去重 API
// 优势：解耦，可被多个插件使用
// 劣势：架构复杂度过高
// 复杂度：★★★★☆
```

#### 推荐集成点

**位置**: `dedup.ts` 中的 `tryRecordMessage` 函数

```typescript
// 当前实现
export function tryRecordMessage(messageId: string, scope = "default"): boolean {
  // ... 内存去重逻辑 ...
}

// 推荐集成方式
export async function tryRecordMessageHybrid(
  messageId: string, 
  content: string,
  sender: string,
  scope = "default"
): Promise<boolean> {
  // 第一层：快速内存去重
  if (!tryRecordMessageMemory(messageId, scope)) {
    return false;
  }
  
  // 第二层：持久化去重（异步）
  const isDuplicate = await checkPythonDedup(content, sender);
  if (isDuplicate) {
    return false;
  }
  
  // 记录到持久化存储
  await recordPythonDedup(content, sender);
  return true;
}
```

**调用位置**: `bot.ts:916`
```typescript
// 修改前
if (!tryRecordMessage(messageId, dedupAccountId)) {
  return;
}

// 修改后
const senderId = ctx.senderOpenId;
const content = ctx.content;
if (!(await tryRecordMessageHybrid(messageId, content, senderId, dedupAccountId))) {
  log(`feishu: skipping duplicate message ${messageId} (hybrid dedup)`);
  return;
}
```

---

## ⚠️ 风险评估师角色分析

### 1. 修改插件代码的风险评估

#### 风险矩阵

| 风险项 | 概率 | 影响 | 风险等级 | 缓解措施 |
|--------|------|------|---------|---------|
| 引入新的重复回复 bug | 中 | 高 | **高** | 充分测试，保留原逻辑 |
| Python 调用失败导致消息丢失 | 低 | 高 | **中** | 异常时降级到仅插件层 |
| 性能下降（Python I/O） | 中 | 中 | **中** | 异步调用，超时机制 |
| 文件锁竞争 | 低 | 中 | **低** | 已有锁机制，监控即可 |
| 向后兼容性问题 | 低 | 中 | **低** | 保持原函数签名 |

#### 详细风险分析

**风险 1：双去重机制冲突**
```
场景：
- 消息 M1 通过插件层去重（新消息）
- 消息 M1 通过脚本层去重（被识别为重复）
- 结果：误判为重复，消息被丢弃

概率：低（需要内容指纹碰撞）
影响：消息丢失（比重复回复更严重）
```

**风险 2：Python 进程调用开销**
```
场景：
- 每条消息触发 Python 子进程
- 高并发时系统负载飙升

概率：中（取决于消息量）
影响：响应延迟增加
```

**风险 3：文件 I/O 成为瓶颈**
```
场景：
- 消息量 > 100/秒
- 文件锁导致队列堆积

概率：低（当前消息量远低于此）
影响：消息处理延迟
```

### 2. 不修改的风险评估

#### 风险矩阵

| 风险项 | 概率 | 影响 | 风险等级 | 说明 |
|--------|------|------|---------|------|
| 用户持续收到重复回复 | 高 | 中 | **高** | 已发生的问题 |
| 用户体验下降 | 高 | 中 | **高** | 影响产品信任度 |
| 资源浪费（重复处理） | 中 | 低 | **低** | 计算资源浪费 |
| 飞书限流风险 | 低 | 高 | **中** | 重复发送可能触发限流 |

#### 现状风险量化

基于已有代码但未被激活的事实：
- **沉没成本**：已投入开发脚本层去重但未产生价值
- **技术债务**：存在两套独立机制但未整合，增加维护复杂度
- **机会成本**：问题持续存在，用户满意度下降

### 3. 推荐的风险缓解策略

#### 策略 1：渐进式集成（推荐）
```
阶段 1：影子模式（1周）
- 调用脚本层去重但不影响决策
- 仅记录日志对比两种机制差异
- 验证无冲突后进入阶段 2

阶段 2：双轨运行（1周）
- 两个机制都生效，但仅记录不匹配情况
- 人工review不匹配的日志

阶段 3：完全启用
- 两个机制串联，任一识别为重复即丢弃
```

#### 策略 2：降级机制
```typescript
try {
  const isDup = await checkPythonDedup(content, sender);
  if (isDup) return false;
} catch (err) {
  // Python 调用失败，降级到仅插件层
  log.warn('Python dedup failed, falling back to memory dedup');
  // 继续处理（不阻断）
}
```

#### 策略 3：功能开关
```typescript
// 通过环境变量控制
const HYBRID_DEDUP_ENABLED = process.env.FEISHU_HYBRID_DEDUP === 'true';

if (HYBRID_DEDUP_ENABLED) {
  return tryRecordMessageHybrid(...);
} else {
  return tryRecordMessage(...);
}
```

#### 策略 4：回滚方案
```bash
# 紧急回滚脚本
# 1. 恢复到原 dedup.ts
git checkout HEAD -- /root/.openclaw/extensions/feishu/src/dedup.ts

# 2. 重启插件（如果需要）
# 取决于 OpenClaw 的热更新机制
```

---

## 🔧 运维工程师角色分析

### 1. 如何验证当前去重机制是否生效？

#### 验证步骤 1：检查内存去重日志
```bash
# 查看插件日志中是否出现 dedup 相关日志
grep -i "duplicate\|dedup" /var/log/openclaw/feishu.log

# 预期输出：
# feishu: skipping duplicate message om_xxx
```

#### 验证步骤 2：检查脚本层去重状态
```bash
# 查看 received_messages.json 文件
ls -la /root/.openclaw/workspace/.learnings/received_messages.json

# 检查内容
cat /root/.openclaw/workspace/.learnings/received_messages.json | jq '.messages | length'
```

#### 验证步骤 3：模拟重复消息测试
```python
# test_dedup.py
import requests
import time

# 发送相同内容两次
message = "DEDUP_TEST_" + str(int(time.time()))

# 第一次发送（预期：正常回复）
# ... 调用飞书 API 发送消息 ...

# 立即第二次发送（预期：应被去重）
# ... 调用飞书 API 发送相同消息 ...

# 检查是否收到两次回复
```

#### 验证步骤 4：重启测试
```bash
# 1. 发送测试消息并确认收到回复

# 2. 重启 OpenClaw 服务
systemctl restart openclaw  # 或相应重启命令

# 3. 等待飞书重试机制触发（或手动重发相同消息）

# 4. 检查是否收到重复回复
# 如果收到 → 证明脚本层去重未生效
```

### 2. 需要增加哪些日志来排查问题？

#### 推荐日志增强

**位置 1：dedup.ts**
```typescript
export function tryRecordMessage(messageId: string, scope = "default"): boolean {
  const now = Date.now();
  const dedupKey = `${scope}:${messageId}`;

  // 增加详细日志
  console.log(`[DEDUP] Checking message: ${dedupKey}, cache_size: ${processedMessageIds.size}`);

  if (processedMessageIds.has(dedupKey)) {
    console.log(`[DEDUP] REJECTED (memory): ${dedupKey}`);
    return false;
  }

  processedMessageIds.set(dedupKey, now);
  console.log(`[DEDUP] ACCEPTED: ${dedupKey}`);
  return true;
}
```

**位置 2：bot.ts（集成点后）**
```typescript
// 记录去重决策上下文
log(`[DEDUP_CONTEXT] messageId=${messageId}, sender=${ctx.senderOpenId}, content_hash=${hashContent(ctx.content)}`);
```

**位置 3：feishu_receive_dedup.py**
```python
def is_message_received(content: str, sender: str = "") -> bool:
    fingerprint = generate_message_fingerprint(content, sender)
    print(f"[DEDUP_PY] Checking fingerprint: {fingerprint}")
    # ... 原有逻辑 ...
    if found:
        print(f"[DEDUP_PY] REJECTED (file): {fingerprint}")
        return True
    print(f"[DEDUP_PY] ACCEPTED: {fingerprint}")
    return False
```

#### 日志分析查询
```bash
# 查找被拒绝的重复消息
grep "REJECTED" /var/log/openclaw/feishu.log

# 统计每小时去重情况
grep "DEDUP" /var/log/openclaw/feishu.log | awk '{print $1}' | sort | uniq -c

# 查找可能的去重失效（相同 content_hash 但不同结果）
grep "DEDUP_CONTEXT" /var/log/openclaw/feishu.log | sort -k3 | uniq -d
```

### 3. 监控指标应该包括什么？

#### 核心指标

| 指标名 | 类型 | 说明 | 告警阈值 |
|--------|------|------|---------|
| `feishu_message_total` | Counter | 接收消息总数 | - |
| `feishu_message_dedup_memory` | Counter | 内存层去重拦截数 | - |
| `feishu_message_dedup_file` | Counter | 文件层去重拦截数 | - |
| `feishu_message_dedup_ratio` | Gauge | 去重比例（被去重/总数）| > 50% |
| `feishu_dedup_latency_ms` | Histogram | 去重检查耗时 | > 100ms |
| `feishu_dedup_file_size` | Gauge | 去重文件大小 | > 10MB |
| `feishu_dedup_python_failures` | Counter | Python 调用失败数 | > 0 |

#### 监控面板设计

```yaml
# 建议的 Grafana 面板配置

panels:
  - title: "消息去重统计"
    type: "stat"
    targets:
      - expr: 'rate(feishu_message_dedup_memory[5m])'
        legend: "内存去重"
      - expr: 'rate(feishu_message_dedup_file[5m])'
        legend: "文件去重"
  
  - title: "去重延迟分布"
    type: "heatmap"
    target:
      expr: 'feishu_dedup_latency_ms_bucket'
  
  - title: "Python 调用失败率"
    type: "graph"
    target:
      expr: 'rate(feishu_dedup_python_failures[5m]) / rate(feishu_message_total[5m])'
      alert:
        condition: "> 0.01"  # 失败率 > 1%
```

#### 健康检查脚本
```bash
#!/bin/bash
# /root/.openclaw/workspace/scripts/check_dedup_health.sh

LEARNINGS_DIR="/root/.openclaw/workspace/.learnings"
RECEIVED_MSG_FILE="$LEARNINGS_DIR/received_messages.json"

# 检查文件是否存在
if [ ! -f "$RECEIVED_MSG_FILE" ]; then
    echo "ERROR: received_messages.json not found"
    exit 1
fi

# 检查文件是否可读写
if [ ! -r "$RECEIVED_MSG_FILE" ] || [ ! -w "$RECEIVED_MSG_FILE" ]; then
    echo "ERROR: received_messages.json not readable/writable"
    exit 1
fi

# 检查文件大小（超过 10MB 告警）
FILE_SIZE=$(stat -f%z "$RECEIVED_MSG_FILE" 2>/dev/null || stat -c%s "$RECEIVED_MSG_FILE" 2>/dev/null)
if [ "$FILE_SIZE" -gt 10485760 ]; then
    echo "WARNING: received_messages.json is too large: $FILE_SIZE bytes"
fi

# 检查 JSON 格式
if ! jq empty "$RECEIVED_MSG_FILE" 2>/dev/null; then
    echo "ERROR: received_messages.json is not valid JSON"
    exit 1
fi

echo "OK: Deduplication system is healthy"
exit 0
```

---

## 📊 方案对比

### 方案 A：保持现状（不推荐）

| 维度 | 评估 |
|------|------|
| **实现成本** | 零 |
| **风险** | 高（问题持续）|
| **效果** | 无效 |
| **维护成本** | 低 |

**适用场景**：资源极度受限，可接受重复回复问题

---

### 方案 B：混合去重模式（推荐）

**描述**：在插件层 `dedup.ts` 中集成脚本层调用，形成双重保障

| 维度 | 评估 |
|------|------|
| **实现成本** | 中（2-3天开发+测试）|
| **风险** | 中（可控）|
| **效果** | 高（解决所有已知场景）|
| **维护成本** | 中 |

**架构图**：
```
Feishu消息 ──▶ bot.ts
                 │
                 ▼
         ┌───────────────┐
         │  tryRecord    │
         │  MessageHybrid│
         └───────┬───────┘
                 │
       ┌─────────┴─────────┐
       ▼                   ▼
┌─────────────┐    ┌─────────────────┐
│ 内存去重     │    │ 调用 Python 脚本 │
│ dedup.ts    │    │ feishu_receive_ │
│             │    │ dedup.py        │
│ • message_id│    │                 │
│ • 30分钟TTL │    │ • 内容指纹      │
│ • O(1)速度  │    │ • 12小时窗口    │
└──────┬──────┘    │ • 持久化存储    │
       │           └────────┬────────┘
       │                    │
       └────────┬───────────┘
                ▼
          任一拒绝 → 丢弃消息
          都通过  → 继续处理
```

**优点**：
1. 双重保障，单点失效仍有另一机制兜底
2. 保留高性能内存去重，仅新增持久化层
3. 渐进式部署，可灰度开启

**缺点**：
1. 实现复杂度增加
2. 每条消息增加 Python 调用开销
3. 需要维护两套机制

---

### 方案 C：替换为仅脚本层去重

**描述**：完全移除插件层内存去重，仅使用脚本层

| 维度 | 评估 |
|------|------|
| **实现成本** | 低（修改调用点即可）|
| **风险** | 高（性能下降）|
| **效果** | 中（解决持久化问题）|
| **维护成本** | 低 |

**缺点**：
1. 每条消息触发 Python 进程，性能开销大
2. 高频消息时可能成为瓶颈
3. 文件 I/O 在高并发下可能竞争

---

### 方案 D：统一去重服务

**描述**：启动独立去重服务，通过 HTTP/gRPC 提供去重 API

| 维度 | 评估 |
|------|------|
| **实现成本** | 高（需要新服务开发）|
| **风险** | 中（新增依赖）|
| **效果** | 高（可复用给其他插件）|
| **维护成本** | 高 |

**架构图**：
```
Feishu插件 ──▶ 去重服务 ◀─── 其他插件
                  │
                  ▼
             Redis/DB
           （持久化存储）
```

**优点**：
1. 去重逻辑中心化
2. 可被多个插件复用
3. 使用专业存储（Redis）性能更好

**缺点**：
1. 架构复杂度过高
2. 引入新的依赖和故障点
3. 开发和维护成本高

---

### 方案对比总结

| 方案 | 实现成本 | 运行性能 | 可靠性 | 可维护性 | 推荐度 |
|------|---------|---------|--------|---------|--------|
| A 保持现状 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ |
| B 混合模式 | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ✅ 推荐 |
| C 仅脚本层 | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⚠️ |
| D 独立服务 | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐ 未来考虑 |

---

## ✅ 实施步骤和风险缓解

### 阶段 1：准备（1天）

1. **代码审查**
   - [ ] 审查 `dedup.ts` 现有逻辑
   - [ ] 审查 `feishu_receive_dedup.py` 接口
   - [ ] 确定集成点

2. **环境准备**
   - [ ] 备份现有代码
   - [ ] 创建功能分支
   - [ ] 准备测试环境

3. **日志增强（前置）**
   - [ ] 添加 `dedup.ts` 详细日志
   - [ ] 添加 `bot.ts` 上下文日志
   - [ ] 验证日志输出

### 阶段 2：开发（1-2天）

1. **修改 `dedup.ts`**
   ```typescript
   // 新增函数
   export async function tryRecordMessageHybrid(
     messageId: string,
     content: string, 
     sender: string,
     scope = "default"
   ): Promise<boolean> {
     // 内存去重
     if (!tryRecordMessage(messageId, scope)) {
       return false;
     }
     
     // Python 去重（带超时和降级）
     try {
       const { execSync } = require('child_process');
       const scriptPath = '/root/.openclaw/workspace/second-brain-processor/feishu_receive_dedup.py';
       const result = execSync(
         `python3 ${scriptPath} --check "${content}" "${sender}"`,
         { timeout: 1000, encoding: 'utf-8' }
       );
       
       if (result.trim() === 'DUPLICATE') {
         return false;
       }
       
       // 记录消息
       execSync(
         `python3 ${scriptPath} --record "${content}" "${sender}"`,
         { timeout: 1000 }
       );
       
     } catch (err) {
       console.warn('[DEDUP] Python dedup failed, using memory only:', err);
     }
     
     return true;
   }
   ```

2. **修改 `bot.ts`**
   ```typescript
   // 修改调用点（916行附近）
   const senderId = ctx.senderOpenId;
   const content = ctx.content;
   
   if (!(await tryRecordMessageHybrid(messageId, content, senderId, dedupAccountId))) {
     log(`feishu: skipping duplicate message ${messageId}`);
     return;
   }
   ```

3. **添加命令行接口到 Python 脚本**
   ```python
   # feishu_receive_dedup.py 末尾添加
   if __name__ == "__main__":
       import argparse
       parser = argparse.ArgumentParser()
       parser.add_argument('--check', nargs=2, help='Check if message is duplicate')
       parser.add_argument('--record', nargs=2, help='Record message as received')
       args = parser.parse_args()
       
       if args.check:
           content, sender = args.check
           result = is_message_received(content, sender)
           print('DUPLICATE' if result else 'NEW')
       elif args.record:
           content, sender = args.record
           record_message_received(content, sender)
   ```

### 阶段 3：测试（1天）

1. **单元测试**
   - [ ] 测试内存去重逻辑
   - [ ] 测试 Python 脚本接口
   - [ ] 测试混合模式

2. **集成测试**
   - [ ] 模拟重复消息发送
   - [ ] 模拟插件重启
   - [ ] 验证去重效果

3. **性能测试**
   - [ ] 测量消息处理延迟
   - [ ] 验证高并发场景
   - [ ] 检查资源使用

### 阶段 4：部署（1天）

1. **灰度发布**
   ```typescript
   // 通过环境变量控制
   const hybridDedupEnabled = process.env.FEISHU_HYBRID_DEDUP === 'true';
   ```

2. **监控验证**
   - [ ] 观察去重指标
   - [ ] 检查错误日志
   - [ ] 确认用户体验改善

3. **全量发布**
   - [ ] 移除功能开关
   - [ ] 更新文档
   - [ ] 通知相关人员

### 风险缓解清单

| 风险 | 缓解措施 | 验证方法 |
|------|---------|---------|
| Python 调用失败 | 添加 try-catch 降级到内存去重 | 模拟 Python 进程崩溃 |
| 性能下降 | 设置 1 秒超时，异步执行 | 压力测试对比 |
| 误判重复 | 影子模式运行一周，人工 review | 对比日志 |
| 回滚需求 | 保留原函数，可配置切换 | 验证回滚脚本 |

---

## 🧪 验证方法

### 验证清单

#### 部署前验证
- [ ] `dedup.ts` 修改通过代码审查
- [ ] `bot.ts` 修改通过代码审查
- [ ] Python 脚本命令行接口测试通过
- [ ] 单元测试覆盖率 > 80%
- [ ] 集成测试通过（重复消息被正确拦截）

#### 部署后验证
- [ ] 观察 24 小时，无重复回复投诉
- [ ] 去重指标正常上报
- [ ] 错误日志无异常
- [ ] 消息处理延迟增加 < 50ms

#### 持续监控
- [ ] 每周 review 去重比例
- [ ] 每月检查文件大小增长
- [ ] 每季度评估是否需要调整策略

### 自动化测试脚本

```bash
#!/bin/bash
# test_dedup_integration.sh

echo "=== 去重集成测试 ==="

# 测试 1：Python 脚本可用性
echo -n "测试 Python 脚本接口... "
python3 /root/.openclaw/workspace/second-brain-processor/feishu_receive_dedup.py --check "test_msg" "test_sender"
if [ $? -eq 0 ]; then
    echo "✓ 通过"
else
    echo "✗ 失败"
    exit 1
fi

# 测试 2：文件读写权限
echo -n "测试文件权限... "
if [ -w "/root/.openclaw/workspace/.learnings/received_messages.json" ]; then
    echo "✓ 通过"
else
    echo "✗ 失败"
    exit 1
fi

# 测试 3：端到端去重
echo -n "测试去重逻辑... "
python3 << 'EOF'
import sys
sys.path.insert(0, '/root/.openclaw/workspace/second-brain-processor')
from feishu_receive_dedup import check_and_record_message

# 第一次：新消息
result1 = check_and_record_message("TEST_MSG_DEDUP", "test_sender")
assert result1 == True, "首次应该是新消息"

# 第二次：重复消息
result2 = check_and_record_message("TEST_MSG_DEDUP", "test_sender")
assert result2 == False, "第二次应该是重复"

print("✓ 通过")
EOF

echo "=== 所有测试通过 ==="
```

---

## 📝 结论与建议

### 核心结论

1. **问题已确认**：脚本层去重确实未被调用，形成"孤岛"机制
2. **根因清晰**：插件层仅依赖内存去重，在重启、跨账号等场景下失效
3. **方案明确**：推荐采用**混合去重模式（方案 B）**

### 实施建议

| 优先级 | 事项 | 建议时间 |
|--------|------|---------|
| P0 | 实现混合去重模式 | 本周内 |
| P1 | 添加详细日志和监控 | 同步进行 |
| P2 | 创建自动化测试脚本 | 下周 |
| P3 | 评估独立去重服务（方案 D）| 季度规划 |

### 最终建议

**立即行动**：采纳本报告中的「方案 B：混合去重模式」，按照「实施步骤和风险缓解」章节执行。预计 3-4 天完成开发和部署，可显著降低重复回复问题。

**长期规划**：若消息量持续增长或需要支持更多插件，可考虑「方案 D：独立去重服务」，使用 Redis 等专业存储替代文件存储。

---

## 📎 附录

### A. 相关代码文件

| 文件 | 作用 |
|------|------|
| `/root/.openclaw/extensions/feishu/src/dedup.ts` | 插件层内存去重 |
| `/root/.openclaw/extensions/feishu/src/bot.ts` | 消息处理入口 |
| `/root/.openclaw/workspace/second-brain-processor/feishu_receive_dedup.py` | 脚本层持久化去重 |
| `/root/.openclaw/workspace/.learnings/received_messages.json` | 去重记录存储 |

### B. 参考文档

- AGENTS.md 规则 9：消息接收去重检查
- Feishu API 文档：消息重试机制
- OpenClaw 插件开发指南

### C. 变更记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-03-16 | 初始版本 |

---

*报告生成时间: 2026-03-16 20:30*  
*评估人员: AI Assistant (多角色协同)*
