#!/usr/bin/env python3
"""
进化日志扫描器 - 自动统计系统进化数据

功能：
- 扫描 ERRORS.md 统计今日错误数
- 扫描 LEARNINGS.md 统计今日学习数
- 扫描 AGENTS.md 统计改进数
- 扫描 git 历史获取今日提交数
- 生成每日进化日志

使用方式：
    python3 evolution_scanner.py              # 生成今日日志
    python3 evolution_scanner.py --dry-run    # 预览但不写入
    python3 evolution_scanner.py --check      # 健康检查模式（带告警）
"""

import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# 配置
WORKSPACE = Path("/root/.openclaw/workspace")
LEARNINGS_DIR = WORKSPACE / ".learnings"
ERRORS_FILE = LEARNINGS_DIR / "ERRORS.md"
LEARNINGS_FILE = LEARNINGS_DIR / "LEARNINGS.md"
AGENTS_FILE = WORKSPACE / "AGENTS.md"
EVOLUTION_LOG = LEARNINGS_DIR / "evolution_log.md"
DAILY_LOG = LEARNINGS_DIR / "daily_evolution.md"
STATE_FILE = LEARNINGS_DIR / ".evolution_state.json"

# 告警阈值
ERROR_SPIKE_THRESHOLD = 5  # 错误数突增阈值
ERROR_RATE_THRESHOLD = 0.3  # 错误率阈值


class EvolutionScanner:
    def __init__(self):
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        self.stats = {
            "date": self.today,
            "errors": 0,
            "learnings": 0,
            "improvements": 0,
            "commits": 0,
            "trends": {},
            "key_improvements": [],
            "warnings": []
        }
        self.prev_stats = self._load_previous_stats()

    def _load_previous_stats(self) -> dict:
        """加载前一日统计数据"""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"errors": 0, "learnings": 0, "improvements": 0, "commits": 0}

    def _save_stats(self):
        """保存今日统计数据"""
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(STATE_FILE, 'w') as f:
                json.dump({
                    "date": self.today,
                    "errors": self.stats["errors"],
                    "learnings": self.stats["learnings"],
                    "improvements": self.stats["improvements"],
                    "commits": self.stats["commits"]
                }, f, indent=2)
        except Exception as e:
            print(f"⚠️ 保存统计数据失败: {e}")

    def _safe_read(self, filepath: Path) -> str:
        """安全读取文件，不存在时返回空字符串"""
        try:
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    return f.read()
            return ""
        except Exception as e:
            print(f"⚠️ 读取文件失败 {filepath}: {e}")
            return ""

    def scan_errors(self):
        """扫描 ERRORS.md 统计今日错误"""
        content = self._safe_read(ERRORS_FILE)
        if not content:
            print("ℹ️ ERRORS.md 不存在或为空")
            return

        # 统计今日错误（匹配日期格式：2026-03-17 或 2026-03-17T14:30:00）
        today_patterns = [
            rf'\[?{re.escape(self.today)}[\sT]',  # [2026-03-17T... 或 2026-03-17 ...
            rf'Logged.*{re.escape(self.today)}',   # Logged: 2026-03-17
            rf'时间.*{re.escape(self.today)}',      # 时间: 2026-03-17
        ]
        
        count = 0
        error_patterns = []
        
        for pattern in today_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                count += 1
                # 提取错误模式（前后100字符）
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 100)
                context = content[start:end]
                
                # 尝试提取错误类型
                error_type_match = re.search(r'错误类型[：:]\s*(\w+)', context)
                if error_type_match:
                    error_patterns.append(error_type_match.group(1))
        
        self.stats["errors"] = count
        
        # 统计重复错误模式
        if error_patterns:
            from collections import Counter
            pattern_counts = Counter(error_patterns)
            self.stats["error_patterns"] = {
                k: v for k, v in pattern_counts.most_common(3) if v > 1
            }

    def scan_learnings(self):
        """扫描 LEARNINGS.md 统计今日学习"""
        content = self._safe_read(LEARNINGS_FILE)
        if not content:
            print("ℹ️ LEARNINGS.md 不存在或为空")
            return

        # 统计今日学习记录
        today_patterns = [
            rf'##?\s*\[?LEARN-{re.escape(self.today.replace("-", ""))}',  # ## [LEARN-20260317
            rf'##?\s*\[?{re.escape(self.today)}',                           # ## [2026-03-17
            rf'Logged.*{re.escape(self.today)}',                            # Logged: 2026-03-17
        ]
        
        count = 0
        for pattern in today_patterns:
            count += len(re.findall(pattern, content, re.IGNORECASE))
        
        # 如果没有匹配到今日格式，统计所有学习条目
        if count == 0:
            # 统计 ## 开头的条目
            count = len(re.findall(r'^##\s+\[', content, re.MULTILINE))
        
        self.stats["learnings"] = count

    def scan_improvements(self):
        """扫描 AGENTS.md 统计改进数"""
        content = self._safe_read(AGENTS_FILE)
        if not content:
            print("ℹ️ AGENTS.md 不存在或为空")
            return

        # 查找迭代记录格式：
        # - [2026-03-17] 改进内容
        # ## 迭代记录... 下方的条目
        improvement_patterns = [
            rf'^\s*-?\s*\[?{re.escape(self.today)}[\]\s]+([^\n]+)',  # - [2026-03-17] xxx
            rf'迭代.*{re.escape(self.today[:7])}.*\n.*?(?=\n##|\Z)', # 迭代章节内的内容
        ]
        
        count = 0
        key_improvements = []
        
        # 简单统计包含日期的行
        date_pattern = rf'{re.escape(self.today)}.*改进|优化|新增|修复'
        matches = re.finditer(date_pattern, content, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            count += 1
            # 提取改进描述
            line_start = content.rfind('\n', 0, match.start()) + 1
            line_end = content.find('\n', match.end())
            if line_end == -1:
                line_end = len(content)
            line = content[line_start:line_end].strip()
            if len(line) > 10 and len(key_improvements) < 3:
                key_improvements.append(line[:100])
        
        self.stats["improvements"] = count
        self.stats["key_improvements"] = key_improvements

    def scan_git_commits(self):
        """扫描 git 历史获取今日提交数"""
        try:
            result = subprocess.run(
                ['git', '-C', str(WORKSPACE), 'log', 
                 '--since=midnight', '--until=now',
                 '--oneline', '--all'],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                commits = result.stdout.strip().split('\n')
                commits = [c for c in commits if c.strip()]
                self.stats["commits"] = len(commits)
                
                # 提取提交信息作为改进
                for commit in commits[:3]:
                    # 去掉 commit hash，保留消息
                    msg = re.sub(r'^[a-f0-9]+\s+', '', commit)
                    if msg and len(self.stats["key_improvements"]) < 5:
                        self.stats["key_improvements"].append(f"[Git] {msg}")
            else:
                print(f"⚠️ Git 命令失败: {result.stderr}")
                self.stats["commits"] = 0
        except Exception as e:
            print(f"⚠️ 扫描 git 历史失败: {e}")
            self.stats["commits"] = 0

    def calculate_trends(self):
        """计算趋势（与昨日比较）"""
        trends = {}
        
        for key in ["errors", "learnings", "improvements", "commits"]:
            today_val = self.stats[key]
            prev_val = self.prev_stats.get(key, 0)
            diff = today_val - prev_val
            
            if diff > 0:
                trends[key] = f"↑{diff}"
            elif diff < 0:
                trends[key] = f"↓{abs(diff)}"
            else:
                trends[key] = "持平"
        
        self.stats["trends"] = trends

    def check_warnings(self) -> list:
        """检查异常情况"""
        warnings = []
        
        # 错误数突增
        if self.stats["errors"] > ERROR_SPIKE_THRESHOLD:
            if self.stats["errors"] > self.prev_stats.get("errors", 0) * 2:
                warnings.append(f"⚠️ 错误数突增: {self.stats['errors']} (昨日: {self.prev_stats.get('errors', 0)})")
        
        # 高错误率（错误 > 学习 + 改进）
        total_activity = self.stats["learnings"] + self.stats["improvements"] + self.stats["commits"]
        if total_activity > 0:
            error_rate = self.stats["errors"] / total_activity
            if error_rate > ERROR_RATE_THRESHOLD:
                warnings.append(f"⚠️ 错误率过高: {error_rate:.1%}")
        
        # 无改进无学习（停滞）
        if self.stats["learnings"] == 0 and self.stats["improvements"] == 0 and self.stats["commits"] == 0:
            warnings.append("⚠️ 今日无学习/改进记录，系统可能停滞")
        
        self.stats["warnings"] = warnings
        return warnings

    def generate_log(self) -> str:
        """生成进化日志"""
        lines = [
            f"## {self.today}",
            "",
            "### 📊 今日统计",
            f"- 错误数：{self.stats['errors']} ({self.stats['trends'].get('errors', '持平')})",
            f"- 学习数：{self.stats['learnings']} ({self.stats['trends'].get('learnings', '持平')})",
            f"- 改进数：{self.stats['improvements']} ({self.stats['trends'].get('improvements', '持平')})",
            f"- 提交数：{self.stats['commits']} ({self.stats['trends'].get('commits', '持平')})",
            "",
        ]
        
        # 关键改进
        if self.stats["key_improvements"]:
            lines.extend([
                "### 🔧 关键改进",
            ])
            for imp in self.stats["key_improvements"]:
                lines.append(f"- {imp}")
            lines.append("")
        
        # 待关注
        if self.stats.get("error_patterns"):
            lines.extend([
                "### ⚠️ 待关注",
                "重复错误模式：",
            ])
            for pattern, count in self.stats["error_patterns"].items():
                lines.append(f"- {pattern}: {count} 次")
            lines.append("")
        
        if self.stats["warnings"]:
            lines.extend([
                "### 🚨 告警",
            ])
            for warning in self.stats["warnings"]:
                lines.append(f"- {warning}")
            lines.append("")
        
        lines.append("---")
        lines.append("")
        
        return "\n".join(lines)

    def run(self, dry_run: bool = False, check_mode: bool = False) -> dict:
        """执行扫描并生成日志"""
        print(f"🔍 开始扫描 {self.today} 的进化数据...")
        
        # 执行扫描
        self.scan_errors()
        self.scan_learnings()
        self.scan_improvements()
        self.scan_git_commits()
        
        # 计算趋势和告警
        self.calculate_trends()
        self.check_warnings()
        
        # 生成日志
        log_content = self.generate_log()
        
        if dry_run:
            print("\n" + "="*50)
            print("📋 预览模式（不会写入文件）")
            print("="*50)
            print(log_content)
            return self.stats
        
        # 写入每日日志
        try:
            DAILY_LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(DAILY_LOG, 'w', encoding='utf-8') as f:
                f.write(log_content)
            print(f"✅ 每日日志已保存: {DAILY_LOG}")
        except Exception as e:
            print(f"❌ 写入每日日志失败: {e}")
        
        # 追加到进化日志
        try:
            EVOLUTION_LOG.parent.mkdir(parents=True, exist_ok=True)
            
            # 如果文件不存在或为空，添加标题
            if not EVOLUTION_LOG.exists() or EVOLUTION_LOG.stat().st_size == 0:
                with open(EVOLUTION_LOG, 'w', encoding='utf-8') as f:
                    f.write("# 🧬 进化日志\n\n")
                    f.write("记录系统的每日进化与成长。\n\n")
                    f.write("---\n\n")
            
            with open(EVOLUTION_LOG, 'a', encoding='utf-8') as f:
                f.write(log_content)
            print(f"✅ 已追加到进化日志: {EVOLUTION_LOG}")
        except Exception as e:
            print(f"❌ 追加进化日志失败: {e}")
        
        # 保存统计数据
        self._save_stats()
        
        # 健康检查模式返回告警
        if check_mode:
            return {
                "stats": self.stats,
                "warnings": self.stats["warnings"],
                "has_warnings": len(self.stats["warnings"]) > 0
            }
        
        return self.stats


def main():
    parser = argparse.ArgumentParser(description="进化日志扫描器")
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不写入文件')
    parser.add_argument('--check', action='store_true', help='健康检查模式（返回告警）')
    
    args = parser.parse_args()
    
    scanner = EvolutionScanner()
    result = scanner.run(dry_run=args.dry_run, check_mode=args.check)
    
    if args.check:
        # 健康检查模式输出 JSON
        print(json.dumps(result, indent=2, ensure_ascii=False))
        # 如果有告警，返回非零退出码
        if result.get("has_warnings"):
            exit(1)
    else:
        # 正常模式打印统计
        print("\n" + "="*50)
        print("📊 扫描完成")
        print("="*50)
        print(f"错误数: {result['errors']}")
        print(f"学习数: {result['learnings']}")
        print(f"改进数: {result['improvements']}")
        print(f"提交数: {result['commits']}")
        if result.get('warnings'):
            print(f"\n🚨 发现 {len(result['warnings'])} 个告警")


if __name__ == "__main__":
    main()
