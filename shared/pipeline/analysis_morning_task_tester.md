# 凌晨5:00任务全方位验证方案

**文档版本**: v1.0  
**创建时间**: 2026-03-17  
**适用任务**: 凌晨5:00聊天记录整理 (Job ID: efccc41b-7887-4af7-b619-54f91679cdaa)

---

## 一、测试目标

确保定时任务执行后，可以验证以下三个关键点：

| 验证维度 | 检查内容 | 历史教训 |
|---------|---------|---------|
| 1. 任务执行 | 任务是否真的触发了 | 不能只检查"cron状态显示ok"（systemEvent模式的问题） |
| 2. AI分析 | AI是否真的完成了分析 | 不能只检查"任务触发"（agentTurn模式的问题） |
| 3. 输出文件 | 输出文件是否正确生成了 | 必须验证"输出文件的时间戳更新" |

---

## 二、测试方案概览

```
┌─────────────────────────────────────────────────────────────────┐
│                    凌晨5:00任务验证流程                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │  执行前测试  │ →  │  执行中监控  │ →  │  执行后验证  │         │
│  │  (T-30min)  │    │  (T+0~3min) │    │  (T+30min)  │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│         │                  │                  │                │
│         ▼                  ▼                  ▼                │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │ 前置条件检查 │    │ 实时日志捕获 │    │ 时间戳验证   │         │
│  │ API Key检查 │    │ 进度跟踪    │    │ 内容完整性   │         │
│  │ 目录权限检查 │    │ 异常检测    │    │ AI质量检查   │         │
│  │ Git状态检查 │    │ 超时告警    │    │ Git推送验证  │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    长期监控层                            │   │
│  │  • 每日自动验证脚本  • 告警机制  • 趋势分析(成功率统计)   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、执行前测试（Pre-Execution Checks）

### 3.1 检查清单

| 检查项 | 检查命令 | 预期结果 | 失败处理 |
|--------|---------|---------|---------|
| API Key有效性 | `echo $KIMI_API_KEY \| head -c 10` | 返回非空值 | 告警并停止 |
| 工作空间存在 | `test -d /root/.openclaw/workspace` | 目录存在 | 告警并停止 |
| Session目录可访问 | `ls /root/.openclaw/agents/main/sessions \| wc -l` | 返回数字 | 告警并停止 |
| 输出目录可写 | `touch /tmp/test_write && rm /tmp/test_write` | 成功 | 告警并停止 |
| Obsidian仓库存在 | `test -d /root/.openclaw/workspace/obsidian-vault/02-Conversations` | 目录存在 | 创建目录 |
| Git配置正确 | `git -C /root/.openclaw/workspace status` | 返回状态0 | 告警并停止 |
| 网络连接 | `curl -s https://api.moonshot.cn -o /dev/null -w '%{http_code}'` | 返回200 | 告警并停止 |
| 磁盘空间 | `df -h / \| awk 'NR==2 {print $5}' \| tr -d '%'` | < 90% | 清理空间 |
| 内存可用 | `free -m \| awk 'NR==2{print $7}'` | > 500MB | 告警 |
| 无其他实例运行 | `pgrep -f 'run_morning_process' \| wc -l` | 返回0或1 | 等待或终止 |

### 3.2 自动化脚本

```python
#!/usr/bin/env python3
"""
执行前检查脚本 - morning_task_pre_check.py
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE = Path("/root/.openclaw/workspace")
SESSION_DIR = Path("/root/.openclaw/agents/main/sessions")
OUTPUT_DIR = WORKSPACE / "obsidian-vault" / "02-Conversations"

def check_api_key() -> tuple:
    """检查API Key"""
    api_key = os.environ.get('KIMI_API_KEY')
    if not api_key:
        return False, "KIMI_API_KEY 未设置"
    if len(api_key) < 10:
        return False, "KIMI_API_KEY 格式异常"
    return True, f"API Key有效 (前8位: {api_key[:8]}...)"

def check_directories() -> tuple:
    """检查目录"""
    checks = [
        (WORKSPACE, "工作空间"),
        (SESSION_DIR, "Session目录"),
        (OUTPUT_DIR, "输出目录"),
    ]
    
    for path, name in checks:
        if not path.exists():
            return False, f"{name}不存在: {path}"
        if not os.access(path, os.R_OK):
            return False, f"{name}不可读: {path}"
        if name == "输出目录" and not os.access(path, os.W_OK):
            return False, f"{name}不可写: {path}"
    
    return True, "所有目录检查通过"

def check_git_status() -> tuple:
    """检查Git状态"""
    try:
        result = subprocess.run(
            ['git', '-C', str(WORKSPACE), 'status', '--porcelain'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return False, f"Git状态检查失败: {result.stderr}"
        
        # 检查是否有未提交的更改（警告级别）
        if result.stdout.strip():
            return True, f"Git检查通过（有未提交更改: {len(result.stdout.strip().split(chr(10)))} 个文件）"
        return True, "Git检查通过（工作区干净）"
    except Exception as e:
        return False, f"Git检查异常: {e}"

def check_disk_space() -> tuple:
    """检查磁盘空间"""
    try:
        result = subprocess.run(
            ['df', '-h', '/'],
            capture_output=True, text=True, timeout=5
        )
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 2:
            usage = lines[1].split()[4].rstrip('%')
            if int(usage) > 90:
                return False, f"磁盘使用率过高: {usage}%"
            return True, f"磁盘空间充足: {usage}%"
    except Exception as e:
        return False, f"磁盘检查异常: {e}"

def check_network() -> tuple:
    """检查网络连接"""
    try:
        result = subprocess.run(
            ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}',
             'https://api.moonshot.cn'],
            capture_output=True, text=True, timeout=10
        )
        if result.stdout.strip() == '200':
            return True, "API服务器可访问"
        return False, f"API服务器返回: {result.stdout.strip()}"
    except Exception as e:
        return False, f"网络检查异常: {e}"

def check_running_instances() -> tuple:
    """检查是否有其他实例在运行"""
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'run_morning_process'],
            capture_output=True, text=True, timeout=5
        )
        pids = [p for p in result.stdout.strip().split('\n') if p]
        # 排除自己
        current_pid = str(os.getpid())
        other_pids = [p for p in pids if p != current_pid]
        
        if other_pids:
            return False, f"发现其他运行实例: {other_pids}"
        return True, "无其他运行实例"
    except Exception as e:
        return False, f"进程检查异常: {e}"

def run_all_checks() -> dict:
    """运行所有检查"""
    checks = [
        ("API Key", check_api_key),
        ("目录权限", check_directories),
        ("Git状态", check_git_status),
        ("磁盘空间", check_disk_space),
        ("网络连接", check_network),
        ("实例冲突", check_running_instances),
    ]
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "passed": [],
        "failed": [],
        "warnings": []
    }
    
    print("=" * 50)
    print("凌晨5:00任务 - 执行前检查")
    print("=" * 50)
    
    for name, check_func in checks:
        success, message = check_func()
        status = "✅" if success else "❌"
        print(f"{status} {name}: {message}")
        
        if success:
            results["passed"].append({"name": name, "message": message})
        else:
            results["failed"].append({"name": name, "message": message})
    
    print("=" * 50)
    print(f"检查完成: {len(results['passed'])} 通过, {len(results['failed'])} 失败")
    
    return results

if __name__ == "__main__":
    results = run_all_checks()
    sys.exit(0 if len(results['failed']) == 0 else 1)
```

---

## 四、执行中监控（Execution Monitoring）

### 4.1 实时日志捕获

```python
#!/usr/bin/env python3
"""
实时监控脚本 - morning_task_monitor.py
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

LOG_FILE = Path("/tmp/morning_process_execution.log")
MONITOR_LOG = Path("/tmp/morning_task_monitor.log")
ALERT_TIMEOUT = 180  # 3分钟超时告警

class ExecutionMonitor:
    def __init__(self):
        self.start_time = datetime.now()
        self.last_activity = datetime.now()
        self.status = "MONITORING"
        self.progress = 0
        
    def log(self, message: str, level: str = "INFO"):
        """记录监控日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] [{level}] {message}"
        print(entry)
        
        with open(MONITOR_LOG, 'a') as f:
            f.write(entry + '\n')
    
    def check_log_activity(self) -> bool:
        """检查日志是否有更新"""
        if not LOG_FILE.exists():
            return False
        
        mtime = datetime.fromtimestamp(LOG_FILE.stat().st_mtime)
        age = (datetime.now() - mtime).total_seconds()
        
        return age < 30  # 30秒内有更新视为活跃
    
    def parse_progress(self) -> int:
        """解析当前进度"""
        if not LOG_FILE.exists():
            return 0
        
        try:
            content = LOG_FILE.read_text()
            # 查找进度标记
            if "步骤 3/3" in content:
                return 90
            elif "步骤 2/3" in content:
                return 60
            elif "步骤 1/3" in content:
                return 30
            elif "状态：SUCCESS" in content:
                return 100
            elif "状态：FAILED" in content:
                return -1
            return 10
        except:
            return 0
    
    def monitor(self, timeout: int = 300):
        """监控执行过程"""
        self.log(f"开始监控，超时时间: {timeout}秒")
        
        while True:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            
            # 检查是否超时
            if elapsed > timeout:
                self.log("执行超时！", "ERROR")
                self.send_alert(f"任务执行超过 {timeout} 秒")
                return False
            
            # 检查日志文件
            if LOG_FILE.exists():
                progress = self.parse_progress()
                
                if progress == 100:
                    self.log("任务执行成功完成")
                    return True
                elif progress == -1:
                    self.log("任务执行失败", "ERROR")
                    return False
                elif progress > self.progress:
                    self.progress = progress
                    self.last_activity = datetime.now()
                    self.log(f"进度更新: {progress}%")
            
            # 检查是否卡住（60秒无进度更新）
            inactive_time = (datetime.now() - self.last_activity).total_seconds()
            if inactive_time > 60 and self.progress < 100:
                self.log(f"警告: {inactive_time:.0f}秒无进度更新", "WARNING")
            
            # 检查是否完全无响应（超过ALERT_TIMEOUT）
            if elapsed > ALERT_TIMEOUT and self.progress < 50:
                self.log(f"严重警告: 超过{ALERT_TIMEOUT}秒进度仍低于50%", "ERROR")
                self.send_alert(f"任务执行异常缓慢，当前进度: {self.progress}%")
            
            time.sleep(5)  # 每5秒检查一次
    
    def send_alert(self, message: str):
        """发送告警"""
        try:
            # 发送飞书通知
            alert_msg = f"⚠️ 凌晨5:00任务监控告警\n\n{message}\n时间: {datetime.now().strftime('%H:%M:%S')}"
            subprocess.run(
                ["openclaw", "message", "send",
                 "--target", "ou_363105a68ee112f714ed44e12c802051",
                 "--content", alert_msg],
                capture_output=True, timeout=10
            )
        except Exception as e:
            self.log(f"告警发送失败: {e}", "ERROR")

if __name__ == "__main__":
    monitor = ExecutionMonitor()
    success = monitor.monitor()
    sys.exit(0 if success else 1)
```

### 4.2 异常检测规则

| 异常类型 | 检测条件 | 告警级别 | 自动处理 |
|---------|---------|---------|---------|
| 启动超时 | 30秒内无日志输出 | 严重 | 发送告警 |
| 进度停滞 | 60秒无进度更新 | 警告 | 记录日志 |
| 执行超时 | 超过5分钟未完成 | 严重 | 发送告警 |
| 内存不足 | 可用内存 < 100MB | 警告 | 记录日志 |
| 磁盘不足 | 剩余空间 < 1GB | 严重 | 发送告警 |
| 网络中断 | API调用失败 | 错误 | 重试3次 |
| 进程崩溃 | Python异常退出 | 严重 | 发送告警 |

---

## 五、执行后验证（Post-Execution Verification）

### 5.1 验证清单

#### 5.1.1 文件时间戳检查

| 检查项 | 检查方法 | 预期结果 |
|--------|---------|---------|
| 执行日志时间戳 | `stat /tmp/morning_process_execution.log` | 修改时间在今天05:00-06:00之间 |
| 输出文件时间戳 | `ls -lt obsidian-vault/02-Conversations/ \| head -5` | 最新文件修改时间在05:00之后 |
| Git提交时间戳 | `git log -1 --format=%ci` | 提交时间在05:00之后 |

#### 5.1.2 内容完整性检查

| 检查项 | 检查方法 | 预期结果 |
|--------|---------|---------|
| 执行日志存在 | `test -f /tmp/morning_process_execution.log` | 文件存在 |
| 成功状态标记 | `grep "状态：SUCCESS" /tmp/morning_process_execution.log` | 找到成功标记 |
| 无错误标记 | `grep -i "error\|exception\|failed" /tmp/morning_process_execution.log` | 无错误或已处理 |
| 输出文件非空 | `find obsidian-vault/02-Conversations/ -name "$(date +%Y-%m-%d)*" -size +100c` | 文件大小>100字节 |
| 文件数量合理 | 检查当天生成的文件数 | 0-15个（根据对话量） |

#### 5.1.3 AI分析质量检查

| 检查项 | 检查方法 | 预期结果 |
|--------|---------|---------|
| YAML frontmatter完整 | 检查输出文件的frontmatter | 包含date, type, tags |
| 内容结构完整 | 检查文件内容 | 有标题、正文、总结 |
| 无乱码 | 检查文件编码 | UTF-8编码，无乱码 |
| 链接可访问 | 检查文件中的URL | 格式正确（可选：实际访问） |

### 5.2 自动化验证脚本

```python
#!/usr/bin/env python3
"""
执行后验证脚本 - morning_task_post_verify.py
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path("/root/.openclaw/workspace")
OUTPUT_DIR = WORKSPACE / "obsidian-vault" / "02-Conversations"
LOG_FILE = Path("/tmp/morning_process_execution.log")
EXECUTION_RECORD = Path("/tmp/morning_task_execution_record.json")

def check_execution_log() -> tuple:
    """检查执行日志"""
    if not LOG_FILE.exists():
        return False, "执行日志不存在", {}
    
    content = LOG_FILE.read_text()
    
    # 检查成功状态
    if "状态：SUCCESS" not in content:
        return False, "日志中未找到成功标记", {"log_snippet": content[-500:]}
    
    # 提取执行时间
    start_time = None
    end_time = None
    for line in content.split('\n'):
        if '启动时间：' in line:
            start_time = line.split('：')[1].strip()
        if '完成时间：' in line:
            end_time = line.split('：')[1].strip()
    
    return True, "执行日志验证通过", {
        "start_time": start_time,
        "end_time": end_time,
        "log_size": len(content)
    }

def check_output_files() -> tuple:
    """检查输出文件"""
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # 查找今天和昨天生成的文件
    files = []
    for date_prefix in [today, yesterday]:
        pattern = f"{date_prefix}*.md"
        files.extend(OUTPUT_DIR.glob(pattern))
    
    if not files:
        return True, "今日无输出文件（可能没有新对话）", {"files_count": 0}
    
    # 验证文件内容
    valid_files = 0
    invalid_files = []
    
    for f in files:
        try:
            content = f.read_text(encoding='utf-8')
            
            # 检查YAML frontmatter
            has_frontmatter = content.startswith('---') and 'date:' in content
            
            # 检查内容非空
            has_content = len(content) > 100
            
            # 检查无乱码（简单检查）
            has_no_garbage = '\\x00' not in content
            
            if has_frontmatter and has_content and has_no_garbage:
                valid_files += 1
            else:
                invalid_files.append({
                    "file": f.name,
                    "has_frontmatter": has_frontmatter,
                    "has_content": has_content
                })
        except Exception as e:
            invalid_files.append({"file": f.name, "error": str(e)})
    
    if invalid_files:
        return False, f"发现 {len(invalid_files)} 个无效文件", {
            "total_files": len(files),
            "valid_files": valid_files,
            "invalid_files": invalid_files
        }
    
    return True, f"所有 {len(files)} 个文件验证通过", {
        "total_files": len(files),
        "valid_files": valid_files
    }

def check_git_push() -> tuple:
    """检查Git推送"""
    try:
        # 检查是否有未推送的提交
        result = subprocess.run(
            ['git', '-C', str(WORKSPACE), 'log', '@{u}..HEAD', '--oneline'],
            capture_output=True, text=True, timeout=10
        )
        
        if result.stdout.strip():
            unpushed = len(result.stdout.strip().split('\n'))
            return False, f"有 {unpushed} 个提交未推送", {
                "unpushed_commits": unpushed
            }
        
        # 检查最后一次提交时间
        result = subprocess.run(
            ['git', '-C', str(WORKSPACE), 'log', '-1', '--format=%ci'],
            capture_output=True, text=True, timeout=10
        )
        
        last_commit_time = datetime.fromisoformat(result.stdout.strip().replace(' ', 'T').replace(' +', '+'))
        hours_since_commit = (datetime.now() - last_commit_time.replace(tzinfo=None)).total_seconds() / 3600
        
        if hours_since_commit > 25:
            return False, f"最后一次提交是 {hours_since_commit:.1f} 小时前", {
                "last_commit_time": last_commit_time.isoformat()
            }
        
        return True, f"Git推送正常，最后一次提交 {hours_since_commit:.1f} 小时前", {
            "last_commit_time": last_commit_time.isoformat()
        }
        
    except Exception as e:
        return False, f"Git检查异常: {e}", {}

def check_timestamps() -> tuple:
    """检查时间戳连续性"""
    today_5am = datetime.now().replace(hour=5, minute=0, second=0, microsecond=0)
    
    # 检查执行日志时间戳
    if LOG_FILE.exists():
        mtime = datetime.fromtimestamp(LOG_FILE.stat().st_mtime)
        if mtime < today_5am:
            return False, f"执行日志时间戳异常: {mtime}", {"log_mtime": mtime.isoformat()}
    
    # 检查输出文件时间戳
    files = list(OUTPUT_DIR.glob(f"{datetime.now().strftime('%Y-%m-%d')}*.md"))
    if files:
        latest = max(files, key=lambda p: p.stat().st_mtime)
        latest_mtime = datetime.fromtimestamp(latest.stat().st_mtime)
        
        if latest_mtime < today_5am:
            return False, f"输出文件时间戳异常: {latest_mtime}", {
                "latest_file": latest.name,
                "latest_mtime": latest_mtime.isoformat()
            }
        
        return True, f"时间戳验证通过，最新文件: {latest.name}", {
            "latest_file": latest.name,
            "latest_mtime": latest_mtime.isoformat()
        }
    
    return True, "今日无输出文件，跳过时间戳检查", {}

def run_all_verifications() -> dict:
    """运行所有验证"""
    verifications = [
        ("执行日志检查", check_execution_log),
        ("时间戳检查", check_timestamps),
        ("输出文件检查", check_output_files),
        ("Git推送检查", check_git_push),
    ]
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "verifications": {},
        "all_passed": True
    }
    
    print("=" * 60)
    print("凌晨5:00任务 - 执行后验证")
    print("=" * 60)
    
    for name, verify_func in verifications:
        success, message, details = verify_func()
        status = "✅" if success else "❌"
        print(f"{status} {name}: {message}")
        
        results["verifications"][name] = {
            "passed": success,
            "message": message,
            "details": details
        }
        
        if not success:
            results["all_passed"] = False
    
    print("=" * 60)
    
    # 保存验证记录
    with open(EXECUTION_RECORD, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"验证记录已保存: {EXECUTION_RECORD}")
    
    return results

if __name__ == "__main__":
    results = run_all_verifications()
    sys.exit(0 if results['all_passed'] else 1)
```

---

## 六、长期监控（Long-term Monitoring）

### 6.1 每日自动验证脚本

```python
#!/usr/bin/env python3
"""
每日自动验证脚本 - daily_verification.py
每日 07:30 执行，验证凌晨5:00任务是否正常完成
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path("/root/.openclaw/workspace")
HISTORY_FILE = WORKSPACE / ".learnings" / "morning_task_history.json"
ALERT_THRESHOLD = 2  # 连续失败2次告警

def load_history() -> list:
    """加载历史记录"""
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return []

def save_history(history: list):
    """保存历史记录"""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history[-30:], f, indent=2)  # 保留最近30天

def calculate_success_rate(history: list, days: int = 7) -> float:
    """计算成功率"""
    recent = [h for h in history if h['date'] >= (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')]
    if not recent:
        return 0.0
    passed = sum(1 for h in recent if h['passed'])
    return passed / len(recent) * 100

def send_daily_report(history: list, today_result: dict):
    """发送每日报告"""
    success_rate_7d = calculate_success_rate(history, 7)
    success_rate_30d = calculate_success_rate(history, 30)
    
    # 统计连续失败
    consecutive_failures = 0
    for h in reversed(history):
        if not h['passed']:
            consecutive_failures += 1
        else:
            break
    
    report = f"""📊 凌晨5:00任务 - 每日验证报告

📅 检查日期: {datetime.now().strftime('%Y-%m-%d')}
✅ 今日状态: {'通过' if today_result['passed'] else '失败'}

📈 成功率统计:
   • 近7天: {success_rate_7d:.1f}%
   • 近30天: {success_rate_30d:.1f}%

🔔 连续失败: {consecutive_failures} 天

{"⚠️ 告警: 连续失败超过阈值！" if consecutive_failures >= ALERT_THRESHOLD else ""}
"""
    
    try:
        subprocess.run(
            ["openclaw", "message", "send",
             "--target", "ou_363105a68ee112f714ed44e12c802051",
             "--content", report],
            capture_output=True, timeout=10
        )
    except Exception as e:
        print(f"报告发送失败: {e}")

def main():
    """主函数"""
    print("=" * 50)
    print("每日自动验证 - 凌晨5:00任务")
    print("=" * 50)
    
    # 加载历史
    history = load_history()
    
    # 运行验证
    result = subprocess.run(
        [sys.executable, str(WORKSPACE / "scripts" / "morning_task_post_verify.py")],
        capture_output=True, text=True
    )
    
    today_result = {
        "date": datetime.now().strftime('%Y-%m-%d'),
        "passed": result.returncode == 0,
        "timestamp": datetime.now().isoformat()
    }
    
    # 更新历史
    history.append(today_result)
    save_history(history)
    
    # 发送报告
    send_daily_report(history, today_result)
    
    print(f"今日验证: {'通过' if today_result['passed'] else '失败'}")
    print(f"历史记录已更新: {HISTORY_FILE}")

if __name__ == "__main__":
    main()
```

### 6.2 告警规则设计

| 告警级别 | 触发条件 | 通知方式 | 响应时间 |
|---------|---------|---------|---------|
| P0-紧急 | 任务完全未执行（无日志） | 飞书消息 + 飞书电话 | 立即 |
| P1-严重 | 任务执行失败（有错误日志） | 飞书消息 | 5分钟内 |
| P2-警告 | 输出文件缺失或异常 | 飞书消息 | 30分钟内 |
| P3-提示 | 连续2天成功率<100% | 飞书消息 | 每日报告 |

### 6.3 趋势分析

```python
# 成功率统计示例
def analyze_trends(history: list) -> dict:
    """分析执行趋势"""
    
    # 按周统计
    weekly_stats = {}
    for record in history:
        week = datetime.fromisoformat(record['timestamp']).strftime('%Y-W%W')
        if week not in weekly_stats:
            weekly_stats[week] = {"total": 0, "passed": 0}
        weekly_stats[week]["total"] += 1
        if record['passed']:
            weekly_stats[week]["passed"] += 1
    
    # 计算每周成功率
    for week in weekly_stats:
        stats = weekly_stats[week]
        stats['rate'] = stats['passed'] / stats['total'] * 100
    
    # 趋势判断
    recent_weeks = sorted(weekly_stats.keys())[-4:]  # 最近4周
    trend = "stable"
    if len(recent_weeks) >= 2:
        rates = [weekly_stats[w]['rate'] for w in recent_weeks]
        if rates[-1] < rates[0] - 10:
            trend = "declining"
        elif rates[-1] > rates[0] + 10:
            trend = "improving"
    
    return {
        "weekly_stats": weekly_stats,
        "trend": trend,
        "recommendation": "需要优化" if trend == "declining" else "保持稳定"
    }
```

---

## 七、失败诊断流程

### 7.1 诊断决策树

```
任务失败?
│
├─► 无执行日志?
│   │
│   ├─► 检查Cron任务状态 → openclaw cron list
│   │   ├─► 任务不存在? → 重新创建任务
│   │   ├─► 任务被禁用? → 启用任务
│   │   └─► 调度异常? → 检查Cron表达式
│   │
│   └─► 检查系统时间 → date
│       └─► 时间不对? → 同步NTP时间
│
├─► 日志显示失败?
│   │
│   ├─► 查看错误详情 → tail -50 /tmp/morning_process_execution.log
│   │   ├─► API错误? → 检查API Key
│   │   ├─► 权限错误? → 检查目录权限
│   │   ├─► 网络错误? → 检查网络连接
│   │   └─► 内存不足? → 释放内存
│   │
│   └─► 检查错误日志 → cat /tmp/morning_process_execution.error
│
├─► 日志成功但无输出?
│   │
│   ├─► 检查输出目录 → ls obsidian-vault/02-Conversations/
│   │   └─► 目录不存在? → 创建目录
│   │
│   ├─► 检查Session文件 → ls /root/.openclaw/agents/main/sessions/
│   │   └─► 无新Session? → 前一天无对话
│   │
│   └─► 检查Git状态 → git status
│       └─► 未推送? → 手动推送
│
└─► 输出文件异常?
    │
    ├─► 文件为空? → 检查AI分析是否完成
    ├─► 文件乱码? → 检查编码设置
    └─► 内容不完整? → 检查处理逻辑
```

### 7.2 常用诊断命令

```bash
# 1. 快速状态检查
echo "=== 凌晨5:00任务快速诊断 ==="
echo "1. Cron任务状态:"
openclaw cron list | grep "凌晨5:00"

echo "2. 最后执行时间:"
stat /tmp/morning_process_execution.log 2>/dev/null | grep Modify || echo "无执行日志"

echo "3. 最新输出文件:"
ls -lt /root/.openclaw/workspace/obsidian-vault/02-Conversations/ | head -3

echo "4. Git状态:"
git -C /root/.openclaw/workspace log -1 --oneline

echo "5. 磁盘空间:"
df -h / | tail -1

echo "6. 内存使用:"
free -h | grep Mem

# 2. 详细日志检查
echo "=== 执行日志最后50行 ==="
tail -50 /tmp/morning_process_execution.log

# 3. 错误日志检查
echo "=== 错误日志 ==="
cat /tmp/morning_process_execution.error 2>/dev/null || echo "无错误日志"

# 4. 手动补执行
bash /root/.openclaw/workspace/second-brain-processor/run_morning_wrapper.sh
```

### 7.3 自动诊断脚本

```python
#!/usr/bin/env python3
"""
自动诊断脚本 - morning_task_diagnose.py
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE = Path("/root/.openclaw/workspace")

def run_command(cmd: list, timeout: int = 10) -> str:
    """执行命令并返回输出"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except Exception as e:
        return f"[ERROR] {e}"

def diagnose():
    """执行诊断"""
    print("=" * 60)
    print("凌晨5:00任务 - 自动诊断报告")
    print("=" * 60)
    
    issues = []
    
    # 1. 检查Cron任务
    print("\n[1/6] 检查Cron任务...")
    cron_output = run_command(["openclaw", "cron", "list"])
    if "凌晨5:00" in cron_output:
        print("  ✅ Cron任务存在")
        if "ok" in cron_output.lower():
            print("  ✅ 任务状态正常")
        else:
            print("  ⚠️ 任务状态异常")
            issues.append("Cron任务状态异常")
    else:
        print("  ❌ Cron任务不存在")
        issues.append("Cron任务不存在")
    
    # 2. 检查执行日志
    print("\n[2/6] 检查执行日志...")
    log_file = Path("/tmp/morning_process_execution.log")
    if log_file.exists():
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
        age_hours = (datetime.now() - mtime).total_seconds() / 3600
        print(f"  ✅ 日志存在，最后修改: {age_hours:.1f}小时前")
        
        content = log_file.read_text()
        if "状态：SUCCESS" in content:
            print("  ✅ 日志显示成功")
        elif "状态：FAILED" in content:
            print("  ❌ 日志显示失败")
            issues.append("任务执行失败")
        else:
            print("  ⚠️ 日志状态不明确")
    else:
        print("  ❌ 执行日志不存在")
        issues.append("执行日志不存在")
    
    # 3. 检查输出文件
    print("\n[3/6] 检查输出文件...")
    output_dir = WORKSPACE / "obsidian-vault" / "02-Conversations"
    if output_dir.exists():
        files = list(output_dir.glob(f"{datetime.now().strftime('%Y-%m-%d')}*.md"))
        if files:
            print(f"  ✅ 今日有 {len(files)} 个输出文件")
        else:
            print("  ⚠️ 今日无输出文件")
    else:
        print("  ❌ 输出目录不存在")
        issues.append("输出目录不存在")
    
    # 4. 检查Git状态
    print("\n[4/6] 检查Git状态...")
    git_output = run_command(["git", "-C", str(WORKSPACE), "status", "--porcelain"])
    if git_output:
        print(f"  ⚠️ 有未提交/推送的更改: {len(git_output.split(chr(10)))} 个文件")
    else:
        print("  ✅ Git工作区干净")
    
    # 5. 检查系统资源
    print("\n[5/6] 检查系统资源...")
    df_output = run_command(["df", "-h", "/"])
    if df_output:
        usage = df_output.split('\n')[1].split()[4].rstrip('%')
        if int(usage) > 90:
            print(f"  ⚠️ 磁盘使用率过高: {usage}%")
            issues.append(f"磁盘使用率过高: {usage}%")
        else:
            print(f"  ✅ 磁盘空间充足: {usage}%")
    
    free_output = run_command(["free", "-m"])
    if free_output:
        available = int(free_output.split('\n')[1].split()[6])
        if available < 500:
            print(f"  ⚠️ 可用内存不足: {available}MB")
            issues.append(f"内存不足: {available}MB")
        else:
            print(f"  ✅ 内存充足: {available}MB")
    
    # 6. 检查网络
    print("\n[6/6] 检查网络连接...")
    curl_output = run_command([
        "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
        "https://api.moonshot.cn"
    ], timeout=10)
    if curl_output == "200":
        print("  ✅ API服务器可访问")
    else:
        print(f"  ❌ API服务器返回: {curl_output}")
        issues.append("网络/API连接异常")
    
    # 总结
    print("\n" + "=" * 60)
    if issues:
        print(f"❌ 诊断完成，发现 {len(issues)} 个问题:")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
        print("\n建议操作:")
        print("  1. 查看详细日志: tail -50 /tmp/morning_process_execution.log")
        print("  2. 手动执行: bash /root/.openclaw/workspace/second-brain-processor/run_morning_wrapper.sh")
        print("  3. 检查Cron配置: openclaw cron list")
    else:
        print("✅ 诊断完成，未发现问题")
    print("=" * 60)
    
    return len(issues) == 0

if __name__ == "__main__":
    success = diagnose()
    sys.exit(0 if success else 1)
```

---

## 八、完整测试执行计划

### 8.1 测试执行时间表

| 时间 | 任务 | 执行方式 | 责任人 |
|-----|------|---------|--------|
| 04:30 | 执行前检查 | 自动 (Cron) | 系统 |
| 05:00 | 主要任务执行 | 自动 (Cron) | 系统 |
| 05:00-05:05 | 实时监控 | 自动（子进程） | 系统 |
| 07:30 | 执行后验证 | 自动 (Cron) | 系统 |
| 07:35 | 每日报告发送 | 自动 | 系统 |
| 08:30 | 人工复查（可选） | 手动 | 用户 |

### 8.2 Cron配置

```bash
# 1. 执行前检查 (04:30)
# Job ID: 3a0fc967-169f-489f-8b36-4fa053dfeefa (配置健康检查)
# 扩展：添加 pre-check 调用

# 2. 主要任务 (05:00)
# Job ID: efccc41b-7887-4af7-b619-54f91679cdaa
# 当前配置: agentTurn + isolated

# 3. 执行后验证 (07:30)
# 需要添加新的Cron任务
openclaw cron add --job '{
  "name": "凌晨任务执行验证",
  "schedule": {"kind": "cron", "expr": "30 7 * * *"},
  "payload": {"kind": "agentTurn", "message": "运行每日验证脚本：python3 /root/.openclaw/workspace/scripts/daily_verification.py"},
  "sessionTarget": "main",
  "enabled": true
}'

# 4. 实时监控 (嵌入到主任务中，无需单独Cron)
```

### 8.3 测试检查清单（可打印版）

```markdown
## 凌晨5:00任务测试检查清单

### 执行前 (T-30min)
- [ ] API Key有效
- [ ] 工作空间目录可访问
- [ ] Session目录可读
- [ ] 输出目录可写
- [ ] Git配置正确
- [ ] 网络连接正常
- [ ] 磁盘空间充足 (<90%)
- [ ] 内存充足 (>500MB)
- [ ] 无其他实例运行

### 执行中 (T+0~T+5min)
- [ ] 日志文件开始更新
- [ ] 进度正常推进
- [ ] 无异常错误
- [ ] 步骤1完成 (<60s)
- [ ] 步骤2完成 (<90s)
- [ ] 步骤3完成 (<120s)

### 执行后 (T+30min)
- [ ] 执行日志存在
- [ ] 日志显示"SUCCESS"
- [ ] 输出文件生成
- [ ] 文件时间戳正确 (>05:00)
- [ ] 文件内容完整
- [ ] Git提交成功
- [ ] Git推送成功

### 长期监控
- [ ] 每日报告发送成功
- [ ] 成功率 > 95% (7天)
- [ ] 无连续失败 > 2天
```

---

## 九、附录

### 9.1 文件路径汇总

| 文件类型 | 路径 |
|---------|------|
| 执行日志 | `/tmp/morning_process_execution.log` |
| 错误日志 | `/tmp/morning_process_execution.error` |
| 监控日志 | `/tmp/morning_task_monitor.log` |
| 验证记录 | `/tmp/morning_task_execution_record.json` |
| 历史记录 | `/root/.openclaw/workspace/.learnings/morning_task_history.json` |
| 输出文件 | `/root/.openclaw/workspace/obsidian-vault/02-Conversations/` |
| 主脚本 | `/root/.openclaw/workspace/second-brain-processor/run_morning_process_progress.py` |
| 包装脚本 | `/root/.openclaw/workspace/second-brain-processor/run_morning_wrapper.sh` |

### 9.2 快速参考命令

```bash
# 查看任务状态
openclaw cron list | grep "凌晨5:00"

# 查看执行日志
tail -100 /tmp/morning_process_execution.log

# 查看最新输出
ls -lt /root/.openclaw/workspace/obsidian-vault/02-Conversations/ | head

# 手动执行任务
bash /root/.openclaw/workspace/second-brain-processor/run_morning_wrapper.sh

# 运行验证
python3 /root/.openclaw/workspace/scripts/morning_task_post_verify.py

# 运行诊断
python3 /root/.openclaw/workspace/scripts/morning_task_diagnose.py
```

### 9.3 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|---------|
| v1.0 | 2026-03-17 | 初始版本，基于历史教训设计完整验证方案 |

---

**文档维护**: 测试员  
**审核状态**: 待架构师和开发员确认  
**下次评审**: 2026-03-24
