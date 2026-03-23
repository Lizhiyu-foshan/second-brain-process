#!/usr/bin/env python3
"""
AGENTS.md 自进化触发器
主动检测问题，自动推动规则固化

核心机制：
1. 异常模式检测（被动触发）
2. 定期巡检（主动发现）
3. 根因分析自动化
4. 规则更新提案
5. 用户确认闭环

运行方式：
- 异常发生时立即触发
- 每日23:00定期巡检
- 手动触发：python3 agents_self_evolution_trigger.py
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional


class SelfEvolutionTrigger:
    """自进化触发器"""
    
    def __init__(self):
        self.workspace = Path("/root/.openclaw/workspace")
        self.registry_path = self.workspace / "RULES_REGISTRY.json"
        self.learnings_path = self.workspace / ".learnings"
        self.proposals_path = self.workspace / ".learnings" / "RULE_PROPOSALS.md"
        
        # 确保目录存在
        self.learnings_path.mkdir(exist_ok=True)
        
        # 加载数据
        self.registry = self._load_registry()
    
    def _load_registry(self) -> Dict:
        """加载规则注册表"""
        try:
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  无法加载注册表: {e}")
            return {"rules": []}
    
    def detect_anomalies(self) -> List[Dict]:
        """
        异常模式检测
        检测需要触发根因分析的问题模式
        """
        anomalies = []
        
        # 1. 检查重复错误模式
        repeat_errors = self._check_repeat_errors()
        if repeat_errors:
            anomalies.append({
                "type": "repeat_errors",
                "severity": "high",
                "description": f"发现{len(repeat_errors)}个重复错误模式",
                "details": repeat_errors,
                "suggested_action": "根因分析 → 规则固化"
            })
        
        # 2. 检查未记录的修复
        unrecorded_fixes = self._check_unrecorded_fixes()
        if unrecorded_fixes:
            anomalies.append({
                "type": "unrecorded_fixes",
                "severity": "medium",
                "description": f"发现{len(unrecorded_fixes)}次修复未记录到规则",
                "details": unrecorded_fixes,
                "suggested_action": "补充规则溯源"
            })
        
        # 3. 检查规则覆盖缺口
        coverage_gaps = self._check_coverage_gaps()
        if coverage_gaps:
            anomalies.append({
                "type": "coverage_gaps",
                "severity": "medium",
                "description": f"发现{len(coverage_gaps)}个场景无规则覆盖",
                "details": coverage_gaps,
                "suggested_action": "新增规则提案"
            })
        
        # 4. 检查健康度下降趋势
        health_decline = self._check_health_decline()
        if health_decline:
            anomalies.append({
                "type": "health_decline",
                "severity": "high",
                "description": f"发现{len(health_decline)}条规则健康度下降",
                "details": health_decline,
                "suggested_action": "规则优化审查"
            })
        
        return anomalies
    
    def _check_repeat_errors(self) -> List[Dict]:
        """检查重复错误模式（同一类型错误7天内发生≥2次）"""
        repeat_errors = []
        
        # 读取错误日志
        error_log_path = self.learnings_path / "ERROR_LOG.md"
        if not error_log_path.exists():
            return repeat_errors
        
        content = error_log_path.read_text(encoding='utf-8')
        
        # 解析错误记录
        error_pattern = r'## 错误记录.*?\n\*\*时间\*\*:\s*(\d{4}-\d{2}-\d{2})'
        errors = re.findall(error_pattern, content, re.DOTALL)
        
        # 统计7天内的错误类型
        cutoff_date = datetime.now() - timedelta(days=7)
        recent_errors = {}
        
        for error in errors:
            try:
                error_date = datetime.strptime(error, "%Y-%m-%d")
                if error_date >= cutoff_date:
                    error_type = self._extract_error_type(error)
                    recent_errors[error_type] = recent_errors.get(error_type, 0) + 1
            except:
                continue
        
        # 找出重复的错误（≥2次）
        for error_type, count in recent_errors.items():
            if count >= 2:
                repeat_errors.append({
                    "error_type": error_type,
                    "count": count,
                    "time_window": "7天"
                })
        
        return repeat_errors
    
    def _extract_error_type(self, error_text: str) -> str:
        """从错误文本提取错误类型"""
        # 简单实现：提取关键词
        keywords = ["部署", "删除", "修改", "超时", "连接", "权限", "配置"]
        for kw in keywords:
            if kw in error_text:
                return kw
        return "其他"
    
    def _check_unrecorded_fixes(self) -> List[Dict]:
        """检查修复操作是否已记录到规则"""
        unrecorded = []
        
        # 检查最近的修复记录
        fixes_path = self.learnings_path / "DEPLOY_FAILURES.md"
        if not fixes_path.exists():
            return unrecorded
        
        content = fixes_path.read_text(encoding='utf-8')
        
        # 查找最近7天的修复记录
        fix_pattern = r'## 修复记录.*?\n\*\*时间\*\*:\s*(\d{4}-\d{2}-\d{2})'
        fixes = re.findall(fix_pattern, content, re.DOTALL)
        
        cutoff_date = datetime.now() - timedelta(days=7)
        
        for fix_date in fixes:
            try:
                fix_dt = datetime.strptime(fix_date, "%Y-%m-%d")
                if fix_dt >= cutoff_date:
                    # 检查是否已溯源到规则
                    if not self._is_fix_recorded_in_rules(fix_date):
                        unrecorded.append({
                            "date": fix_date,
                            "issue": "修复未记录到规则溯源"
                        })
            except:
                continue
        
        return unrecorded
    
    def _is_fix_recorded_in_rules(self, fix_date: str) -> bool:
        """检查修复是否已记录到规则溯源"""
        # 检查RULES_REGISTRY.json中的incidents
        for rule in self.registry.get("rules", []):
            for incident in rule.get("incidents", []):
                if incident.get("date") == fix_date:
                    return True
        return False
    
    def _check_coverage_gaps(self) -> List[str]:
        """检查规则覆盖缺口"""
        gaps = []
        
        # 定义需要覆盖的关键场景
        critical_scenarios = [
            ("文件操作安全", ["文件删除", "文件修改", "路径检查"]),
            ("网络请求超时", ["API超时", "请求重试", "连接失败"]),
            ("配置变更影响", ["配置修改", "环境变量", "依赖变更"]),
            ("并发冲突处理", ["并发", "锁", "竞态条件"]),
        ]
        
        # 收集所有规则的关键词
        all_keywords = set()
        for rule in self.registry.get("rules", []):
            keywords = rule.get("triggers", {}).get("keywords", [])
            all_keywords.update(keywords)
        
        # 检查关键场景是否被覆盖
        for scenario, keywords in critical_scenarios:
            if not any(kw in all_keywords for kw in keywords):
                gaps.append(scenario)
        
        return gaps
    
    def _check_health_decline(self) -> List[Dict]:
        """检查规则健康度是否下降"""
        declining = []
        
        for rule in self.registry.get("rules", []):
            health = rule.get("health_metrics", {})
            score = health.get("health_score", 100)
            false_positives = health.get("false_positive_30d", 0)
            
            # 健康度低于70或误报超过3次
            if score < 70 or false_positives >= 3:
                declining.append({
                    "rule_id": rule["id"],
                    "rule_name": rule["name"],
                    "health_score": score,
                    "false_positives": false_positives
                })
        
        return declining
    
    def generate_proposal(self, anomaly: Dict) -> str:
        """生成规则更新提案"""
        proposal = f"""
## 规则更新提案

**提案时间**：{datetime.now().strftime('%Y-%m-%d %H:%M')}
**触发原因**：{anomaly['description']}
**建议操作**：{anomaly['suggested_action']}

### 问题详情

```json
{json.dumps(anomaly['details'], indent=2, ensure_ascii=False)}
```

### 建议方案

1. **根因分析**
   - 收集相关日志和上下文
   - 分析问题发生的根本原因
   - 评估影响范围

2. **规则设计**
   - 确定规则触发条件
   - 设计规则执行流程
   - 制定验证标准

3. **规则实现**
   - 更新AGENTS_DETAILS.md
   - 更新RULES_REGISTRY.json
   - 添加溯源注释

4. **验证测试**
   - 模拟触发场景
   - 验证规则有效性
   - 更新健康度数据

### 用户确认

- [ ] 确认进行根因分析
- [ ] 确认规则设计方案
- [ ] 确认规则实现
- [ ] 确认验证通过

---

**下一步**：等待用户确认后开始执行
"""
        return proposal
    
    def save_proposal(self, anomaly: Dict):
        """保存提案到文件"""
        proposal = self.generate_proposal(anomaly)
        
        # 追加到提案文件
        with open(self.proposals_path, 'a', encoding='utf-8') as f:
            f.write("\n" + "="*60 + "\n")
            f.write(proposal)
            f.write("\n")
        
        return proposal
    
    def run(self):
        """运行完整检测流程"""
        print("="*60)
        print("AGENTS.md 自进化触发器")
        print("="*60)
        print(f"检测时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 检测异常
        anomalies = self.detect_anomalies()
        
        if not anomalies:
            print("✅ 未发现需要固化的异常模式")
            print("系统运行良好，无需更新规则")
            return []
        
        print(f"🔍 发现 {len(anomalies)} 个异常模式：")
        print()
        
        proposals = []
        for i, anomaly in enumerate(anomalies, 1):
            emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(anomaly["severity"], "⚪")
            print(f"{i}. {emoji} [{anomaly['severity'].upper()}] {anomaly['description']}")
            print(f"   建议：{anomaly['suggested_action']}")
            
            # 生成并保存提案
            proposal = self.save_proposal(anomaly)
            proposals.append({
                "anomaly": anomaly,
                "proposal": proposal
            })
        
        print()
        print(f"✅ 已生成 {len(proposals)} 个规则更新提案")
        print(f"📄 提案保存位置：{self.proposals_path}")
        print()
        print("="*60)
        print("⚠️  等待用户确认后开始根因分析和规则固化")
        print("="*60)
        
        return proposals


def main():
    trigger = SelfEvolutionTrigger()
    proposals = trigger.run()
    
    if proposals:
        print("\n💡 建议操作：")
        print("1. 查看提案文件：cat .learnings/RULE_PROPOSALS.md")
        print("2. 确认后开始根因分析")
        print("3. 按提案步骤执行规则固化")


if __name__ == "__main__":
    main()
