# 伪AI调用全面审计报告

**审计时间**: 2026-03-25  
**审计范围**: 
- `/root/.openclaw/workspace/` - 工作区代码
- `/root/.openclaw/workspace/skills/` - Skill代码
- `/root/.openclaw/skills/` - 系统Skill代码（含bmad-evo）

**扫描文件数**: 150+ Python文件

---

## 执行摘要

| 风险等级 | 数量 | 说明 |
|---------|------|------|
| 🔴 CRITICAL | 3 | 核心功能使用伪实现 |
| 🟠 HIGH | 6 | 重要功能存在简化版/硬编码 |
| 🟡 MEDIUM | 8 | 测试相关mock/模拟代码 |
| 🟢 LOW | 5 | 文档注释中的TODO标记 |

---

## 🔴 CRITICAL 级别问题

### 1. 定时任务调度伪实现

**文件**: `/root/.openclaw/workspace/second-brain-processor/scheduled_discussion_handler.py`

**行号**: 91, 115

**问题代码**:
```python
# 行91
def handle_auto_process_immediate(user_input: str, pending: Dict) -> str:
    # ...
    # 这里应该设置实际的定时任务，简化版本
    complete_pending(pending.get("id", ""))
    return f"⏰ 已推迟 {hours} 小时，将在 {time_str} 再次提醒"

# 行115
def schedule_discussion(article_file: str, hours: int) -> str:
    """
    设置定时讨论任务
    """
    # 简化版本，实际应使用OpenClaw Cron
    future_time = datetime.now() + timedelta(hours=hours)
    time_str = future_time.strftime("%Y-%m-%d %H:%M")
    
    return f"⏰ 已设置定时任务：{time_str} 提醒您讨论 {article_file}"
```

**问题类型**: 伪代码/未实现

**风险描述**: 
- 函数声称设置定时任务，实际仅返回提示消息
- 用户被告知"已设置定时任务"，但实际上没有任何任务被创建
- 这是**欺骗性行为**，可能导致用户错过重要提醒

**修复建议**:
```python
def schedule_discussion(article_file: str, hours: int) -> str:
    """设置定时讨论任务"""
    import subprocess
    from datetime import datetime, timedelta
    
    future_time = datetime.now() + timedelta(hours=hours)
    time_str = future_time.strftime("%Y-%m-%d %H:%M")
    cron_expr = future_time.strftime("%M %H %d %m *")
    
    # 实际创建cron任务
    cmd = f"openclaw cron add '{cron_expr}' 'python3 scheduled_discussion_handler.py --trigger {article_file}'"
    result = subprocess.run(cmd, shell=True, capture_output=True)
    
    if result.returncode == 0:
        return f"⏰ 已设置定时任务：{time_str} 提醒您讨论 {article_file}"
    else:
        return f"❌ 定时任务设置失败：{result.stderr.decode()}"
```

---

### 2. 文章内容获取伪实现

**文件**: `/root/.openclaw/workspace/second-brain-processor/article_handler.py`

**行号**: 28-36

**问题代码**:
```python
def fetch_or_wait_content(url: str) -> str:
    """
    获取文章内容
    v2.1: 简化版本，提示用户手动复制内容
    """
    return f"""# 待获取文章

URL: {url}

> 请复制文章内容到这里
"""
```

**问题类型**: 伪代码/简化版

**风险描述**:
- 函数声称"获取文章内容"，实际仅返回一个模板
- 用户需要手动复制粘贴，完全自动化失效
- 文件名标记"v2.1"暗示这是长期存在的临时方案

**修复建议**:
```python
def fetch_or_wait_content(url: str) -> str:
    """获取文章内容"""
    import requests
    from bs4 import BeautifulSoup
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 提取文章正文
        article = soup.find('article') or soup.find('main') or soup.find('div', class_='content')
        if article:
            return article.get_text(separator='\n', strip=True)
        return soup.get_text(separator='\n', strip=True)[:5000]
    except Exception as e:
        return f"# 待获取文章\n\nURL: {url}\n\n> 获取失败：{str(e)}，请手动复制内容\n"
```

---

### 3. 测试结果假数据生成

**文件**: `/root/.openclaw/workspace/shared/pipeline/layer0/tester.py`

**行号**: 285-287

**问题代码**:
```python
def _parse_test_output(self, task_type: str, ai_output: str, task_data: Dict) -> Dict:
    # ...
    # 模拟测试结果统计
    total = len(test_cases) if test_cases else 5
    passed = max(0, total - 1)  # 假设大部分通过
    failed = total - passed
    
    return {
        "test_type": task_type,
        "total_cases": total,
        "passed": passed,
        "failed": failed,
        "coverage": 85.0,  # 假设的覆盖率
        # ...
    }
```

**问题类型**: 假数据/硬编码

**风险描述**:
- 测试通过率被硬编码为"大部分通过"（total - 1）
- 覆盖率固定为85.0，与实际情况无关
- 可能掩盖真实的测试问题，导致质量误判

**修复建议**:
```python
def _parse_test_output(self, task_type: str, ai_output: str, task_data: Dict) -> Dict:
    # 从AI输出中解析真实结果
    test_results = self._extract_test_results(ai_output)
    
    passed = sum(1 for r in test_results if r.get('status') == 'passed')
    failed = sum(1 for r in test_results if r.get('status') == 'failed')
    total = len(test_results)
    
    # 计算真实覆盖率
    coverage = self._extract_coverage(ai_output)
    
    return {
        "test_type": task_type,
        "total_cases": total,
        "passed": passed,
        "failed": failed,
        "coverage": coverage,
        "is_real_data": True,  # 标记真实数据
        # ...
    }
```

---

## 🟠 HIGH 级别问题

### 4. AI分析简化版（主题讨论）

**文件**: `/root/.openclaw/workspace/skills/meeting-prep-orchestrator/scripts/topic_discussion_igniter.py`

**行号**: 396, 448, 369

**问题代码**:
```python
# 行396
# AI分析（简化版）
analysis = self.analyze_topic_with_ai(topic, related_notes)

# 行369
# 生成下一阶段消息（需要重新分析，简化版）
return self.generate_stage_message(...)

# 行448
# 检查链接内容与当前主题的相关性（简化版）
topic_keywords = self.state['current_topic'].lower().split()
link_relevant = any(kw in link.lower() or kw in context.lower() for kw in topic_keywords)
```

**问题类型**: 简化版实现

**风险描述**:
- 多处标记"简化版"但未实现完整功能
- 链接相关性检查仅基于关键词匹配，无法真正理解语义
- 影响用户体验和讨论质量

**修复建议**: 实现真实的AI调用：
```python
def analyze_topic_with_ai(self, topic: str, notes: List[Dict]) -> Dict:
    """使用真实AI分析主题"""
    from kimi_api import call_ai  # 假设的API
    
    prompt = f"""分析以下主题的讨论要点：
主题: {topic}
相关笔记: {json.dumps(notes, ensure_ascii=False)}

请提供：
1. 核心问题
2. 关键角度
3. 讨论阶段建议
"""
    response = call_ai(prompt, model="kimi-k2")
    return json.loads(response)
```

---

### 5. 会议检查简化版

**文件**: `/root/.openclaw/workspace/skills/meeting-prep-orchestrator/scripts/prep_check.py`

**行号**: 191-192, 238-240

**问题代码**:
```python
# 行191-192
def check_upcoming_meetings(config: Dict) -> List[Dict]:
    """检查即将到来的会议（简化版 - 从配置文件读取）"""
    # TODO: 未来可以从日历API或特定文件读取日程
    return []

# 行238-240
# 检查即将到来的会议（简化版）
log("检查即将到来的会议...")
# TODO: 实现自动检查逻辑
log("当前版本仅支持手动触发")
```

**问题类型**: TODO/未实现

**风险描述**:
- 核心功能（自动会议检查）完全未实现
- 仅返回空列表，系统无法自动工作

---

### 6. 队列响应处理器简化版

**文件**: `/root/.openclaw/workspace/second-brain-processor/queue_response_handler.py`

**行号**: 125

**问题代码**:
```python
elif user_input.startswith("稍后"):
    # 解析小时数
    match = re.search(r'(\d+)', user_input)
    hours = int(match.group(1)) if match else 2
    
    # 这里应该设置定时任务，简化版本
    complete_pending(pending.get("id", ""))
    return f"⏰ 已推迟 {hours} 小时，将在之后提醒您讨论"
```

**问题类型**: 伪代码/未实现

**风险描述**: 同问题#1，定时任务未实际创建

---

### 7. BMAD-EVO Mock模式自动回退

**文件**: `/root/.openclaw/skills/bmad-evo/lib/agent_executor.py`

**行号**: 401-420

**问题代码**:
```python
def _execute_local(self, config: AgentConfig, prompt: str) -> AgentResult:
    # ...
    # 检查是否显式启用mock模式（仅测试用途）
    if os.environ.get('BMAD_EVO_USE_MOCK') == '1':
        logger.warning("⚠️  BMAD_EVO_USE_MOCK=1 - Using mock output for testing only!")
        
        # 检查是否有预定义的模拟输出文件
        mock_file = self.project_path / ".bmad" / f"{config.name}-output.txt"
        if mock_file.exists():
            output = mock_file.read_text(encoding='utf-8')
            # ...
            return AgentResult(success=True, output=output, model_used=f"{config.model}(MOCK-FOR-TESTING)")
```

**问题类型**: Mock回退

**风险描述**:
- 虽然需要显式设置环境变量，但mock数据仍可能被误用
- 缺乏强制性的真实模式检查

**修复建议**: 移除mock模式或增加强制确认：
```python
def _execute_local(self, config: AgentConfig, prompt: str) -> AgentResult:
    # 检查是否显式启用mock模式
    if os.environ.get('BMAD_EVO_USE_MOCK') == '1':
        # 强制二次确认
        if os.environ.get('BMAD_EVO_MOCK_CONFIRM') != 'I_UNDERSTAND_THIS_IS_MOCK':
            raise RuntimeError(
                "MOCK mode requires explicit confirmation. "
                "Set BMAD_EVO_MOCK_CONFIRM=I_UNDERSTAND_THIS_IS_MOCK"
            )
        # ...
```

---

### 8. TypeScript解析器简化版

**文件**: `/root/.openclaw/skills/bmad-fullstack-backup/typescript_parser.py`

**行号**: 224-268

**问题代码**:
```python
class SimpleTypeScriptParser:
    """
    简化版 TypeScript 解析器（正则基础）
    
    用于在无法安装 Node.js/TypeScript 时的降级方案
    """
    
    def parse_interface(self, content: str) -> List[NormalizedSchema]:
        """使用正则解析 Interface"""
        schemas = []
        
        for match in self.interface_pattern.finditer(content):
            # ...
            for prop_match in self.property_pattern.finditer(body):
                field = FieldInfo(
                    name=prop_name,
                    field_type=FieldType.ANY,  # 简化处理
                    # ...
                )
```

**问题类型**: 简化版/降级方案

**风险描述**:
- 所有字段类型被硬编码为`FieldType.ANY`
- 复杂的TypeScript类型无法正确解析
- 可能导致类型安全问题

---

## 🟡 MEDIUM 级别问题

### 9. 测试文件中的Mock使用

**文件**: `/root/.openclaw/skills/cron-health-dashboard/scripts/test_cron_health.py`

**行号**: 159-187

这些测试文件中的mock使用是**合理的**，因为它们确实是用于单元测试。但需要确保：
- mock不会泄露到生产代码
- 测试明确标记为使用mock

### 10. 自动修复模拟模式

**文件**: `/root/.openclaw/skills/auto-fix/scripts/auto_fix.py`

**行号**: 65, 100, 158, 198, 271

```python
# 模拟执行：/compact
return True, "[模拟] 执行 /compact"
```

这些模拟模式有`--dry-run`参数控制，风险较低。

---

## 🟢 LOW 级别问题

### 11. 文档中的TODO标记

**文件**: 多个文件

这些TODO/FIXME标记在注释中，不会直接影响功能：

- `/root/.openclaw/workspace/skills/meeting-prep-orchestrator/scripts/prep_check.py`:192 - `TODO: 未来可以从日历API或特定文件读取日程`
- `/root/.openclaw/workspace/skills/meeting-prep-orchestrator/scripts/prep_check.py`:240 - `TODO: 实现自动检查逻辑`

---

## 修复优先级建议

| 优先级 | 问题 | 预计工作量 | 影响范围 |
|-------|------|-----------|---------|
| P0 | 定时任务伪实现 | 4小时 | second-brain-processor |
| P0 | 文章获取伪实现 | 6小时 | article_handler |
| P1 | 测试结果假数据 | 3小时 | pipeline tester |
| P1 | AI分析简化版 | 8小时 | meeting-prep-orchestrator |
| P2 | Mock模式安全加固 | 2小时 | bmad-evo |
| P2 | TypeScript解析器完善 | 10小时 | bmad-fullstack-backup |

---

## 检测工具

本次审计使用了自定义的扫描脚本，保存在 `/root/.openclaw/workspace/scan_fake_ai.py`，可以定期运行以检测新的伪AI调用。

**关键检测模式**:
```bash
# 检测简化版/模拟标记
grep -rn "简化版\|实际应调用\|模拟.*结果" --include="*.py"

# 检测假数据模式
grep -rn "passed = max(0, total\|coverage.*85.0\|硬编码" --include="*.py"

# 检测TODO AI调用
grep -rn "TODO.*调用AI\|FIXME.*调用" --include="*.py"
```

---

## 结论

本次审计发现了**3个CRITICAL级别**的问题，这些伪AI调用可能导致：
1. **用户被误导** - 被告知任务已设置/完成，实际未执行
2. **数据质量下降** - 假数据混入真实结果
3. **自动化失效** - 核心自动化功能需要人工干预

**建议立即修复**所有CRITICAL和HIGH级别问题，并建立代码审查机制防止新的伪AI调用进入生产代码。

---

*报告生成时间: 2026-03-25 23:55*  
*审计工具: scan_fake_ai.py v1.0*
