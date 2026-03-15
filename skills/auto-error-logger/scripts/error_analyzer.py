#!/usr/bin/env python3
"""
错误模式分析器

定期分析 ERRORS.md，识别重复出现的错误模式，生成修复建议。

使用方式：
    python3 error_analyzer.py [--days 7] [--output report.json]
"""

import os
import sys
import json
import re
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter
from typing import Dict, List, Any, Tuple

# 配置
WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE", "/root/.openclaw/workspace"))
ERRORS_FILE = WORKSPACE / ".learnings" / "ERRORS.md"
OUTPUT_DIR = WORKSPACE / "shared" / "pipeline"


def parse_errors(content: str) -> List[Dict[str, Any]]:
    """
    解析 ERRORS.md 中的错误记录
    
    Returns:
        错误记录列表
    """
    errors = []
    
    # 按错误块分割
    error_pattern = r"## (ERR-[\d-]+)\n(.*?)(?=\n## |$)"
    
    for match in re.finditer(error_pattern, content, re.DOTALL):
        error_id = match.group(1)
        error_body = match.group(2)
        
        # 提取各个字段
        error = {
            "id": error_id,
            "time": extract_field(error_body, "时间"),
            "context": extract_field(error_body, "操作"),
            "type": extract_field(error_body, "错误类型"),
            "message": extract_field(error_body, "错误信息"),
            "status": extract_field(error_body, "状态"),
            "retry_count": extract_field(error_body, "重试次数"),
        }
        
        errors.append(error)
    
    return errors


def extract_field(text: str, field_name: str) -> str:
    """提取指定字段的值"""
    pattern = rf"\*\*{field_name}\*\*:\s*(.+?)(?:\n|$)"
    match = re.search(pattern, text)
    if match:
        return match.group(1).strip()
    return ""


def analyze_error_types(errors: List[Dict[str, Any]]) -> Dict[str, int]:
    """分析错误类型分布"""
    types = Counter(e.get("type", "Unknown") for e in errors)
    return dict(types.most_common())


def analyze_error_contexts(errors: List[Dict[str, Any]]) -> Dict[str, int]:
    """分析错误上下文分布"""
    contexts = Counter(e.get("context", "unknown") for e in errors)
    return dict(contexts.most_common())


def analyze_error_trends(errors: List[Dict[str, Any]], days: int = 7) -> Dict[str, Any]:
    """分析错误趋势"""
    # 按日期分组
    daily_counts = Counter()
    
    for error in errors:
        time_str = error.get("time", "")
        if time_str:
            try:
                # 解析日期
                date = datetime.strptime(time_str.split()[0], "%Y-%m-%d")
                daily_counts[date.date()] += 1
            except:
                pass
    
    # 计算趋势
    recent_count = sum(count for date, count in daily_counts.items() 
                      if datetime.now().date() - date <= timedelta(days=days))
    
    previous_count = sum(count for date, count in daily_counts.items()
                        if timedelta(days=days) < datetime.now().date() - date <= timedelta(days=days*2))
    
    trend = "stable"
    if recent_count > previous_count * 1.2:
        trend = "increasing"
    elif recent_count < previous_count * 0.8:
        trend = "decreasing"
    
    return {
        "daily_counts": {str(k): v for k, v in sorted(daily_counts.items())},
        "recent_count": recent_count,
        "previous_count": previous_count,
        "trend": trend
    }


def generate_recommendations(
    error_types: Dict[str, int],
    error_contexts: Dict[str, int],
    trends: Dict[str, Any]
) -> List[Dict[str, str]]:
    """生成修复建议"""
    recommendations = []
    
    # 基于错误类型
    for error_type, count in list(error_types.items())[:3]:
        if count >= 3:
            recommendations.append({
                "priority": "high",
                "type": "error_pattern",
                "description": f"错误类型 '{error_type}' 出现 {count} 次，需要优先处理",
                "action": f"检查所有 {error_type} 错误的共同原因，考虑添加全局异常处理"
            })
    
    # 基于上下文
    for context, count in list(error_contexts.items())[:3]:
        if count >= 3:
            recommendations.append({
                "priority": "medium",
                "type": "context_pattern",
                "description": f"操作 '{context}' 失败 {count} 次",
                "action": f"检查 {context} 的实现，考虑添加重试机制或错误恢复"
            })
    
    # 基于趋势
    if trends.get("trend") == "increasing":
        recommendations.append({
            "priority": "high",
            "type": "trend",
            "description": "错误数量呈上升趋势",
            "action": "进行系统健康检查，识别最近的变化"
        })
    
    return recommendations


def main():
    parser = argparse.ArgumentParser(description="错误模式分析器")
    parser.add_argument("--days", type=int, default=7, help="分析最近几天的错误")
    parser.add_argument("--output", type=str, help="输出文件路径")
    args = parser.parse_args()
    
    print(f"=== 错误模式分析 ({datetime.now().isoformat()}) ===\n")
    
    if not ERRORS_FILE.exists():
        print("没有错误记录文件")
        result = {
            "status": "no_errors",
            "message": "没有错误记录",
            "timestamp": datetime.now().isoformat()
        }
    else:
        content = ERRORS_FILE.read_text(encoding="utf-8")
        errors = parse_errors(content)
        
        print(f"解析到 {len(errors)} 条错误记录\n")
        
        # 分析
        error_types = analyze_error_types(errors)
        error_contexts = analyze_error_contexts(errors)
        trends = analyze_error_trends(errors, args.days)
        recommendations = generate_recommendations(error_types, error_contexts, trends)
        
        # 输出结果
        print("错误类型分布:")
        for t, c in list(error_types.items())[:5]:
            print(f"  - {t}: {c} 次")
        
        print("\n错误上下文分布:")
        for ctx, c in list(error_contexts.items())[:5]:
            print(f"  - {ctx}: {c} 次")
        
        print(f"\n趋势: {trends.get('trend', 'unknown')}")
        print(f"最近 {args.days} 天错误数: {trends.get('recent_count', 0)}")
        
        print("\n修复建议:")
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. [{rec['priority']}] {rec['description']}")
            print(f"   行动: {rec['action']}\n")
        
        result = {
            "status": "analyzed",
            "timestamp": datetime.now().isoformat(),
            "total_errors": len(errors),
            "analysis_period_days": args.days,
            "error_types": error_types,
            "error_contexts": error_contexts,
            "trends": trends,
            "recommendations": recommendations
        }
    
    # 保存报告
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"报告已保存到: {output_path}")
    else:
        # 默认保存位置
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = OUTPUT_DIR / f"error_analysis_{datetime.now().strftime('%Y%m%d')}.json"
        output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"报告已保存到: {output_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())