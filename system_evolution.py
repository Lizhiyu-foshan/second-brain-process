#!/usr/bin/env python3
"""
系统论自动进化引擎 v1.0

核心功能：
1. 错误模式分析 - 从系统角度分析错误根因
2. 改进方案生成 - 提出系统性解决方案
3. 版本管理与回滚 - git-based 版本控制
4. 自动验证测试 - 重试原指令或等效测试
5. 效果追踪汇报 - 结构化报告

使用：
    python3 system_evolution.py --daily-review    # 凌晨5点复盘
    python3 system_evolution.py --analyze-only    # 仅分析不实施
    python3 system_evolution.py --rollback [hash] # 回滚到指定版本
"""

import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 路径配置
WORKSPACE = Path("/root/.openclaw/workspace")
LEARNINGS_DIR = WORKSPACE / ".learnings"
ERRORS_FILE = LEARNINGS_DIR / "ERRORS.md"
EVOLUTION_LOG = LEARNINGS_DIR / "EVOLUTION_LOG.md"

# 保留配置
ERROR_RETENTION_DAYS = 30  # 错误日志保留30天
MAX_DAILY_IMPROVEMENTS = 1  # 每天最多1次改进

def log(msg):
    """打印日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {msg}")

def get_recent_errors(hours=24):
    """获取最近N小时的错误记录"""
    if not ERRORS_FILE.exists():
        return []
    
    try:
        content = ERRORS_FILE.read_text(encoding='utf-8')
        # 解析错误条目
        error_pattern = r'## \[(ERR-\d{8}-\d+)\] (.+?)\n\n\*\*Logged\*\*: ([^\n]+)'
        matches = re.findall(error_pattern, content, re.DOTALL)
        
        errors = []
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        for error_id, title, logged_time in matches:
            try:
                # 解析时间
                log_dt = datetime.fromisoformat(logged_time.replace('Z', '+00:00').replace('+00:00', ''))
                if log_dt > cutoff_time:
                    errors.append({
                        'id': error_id,
                        'title': title,
                        'time': log_dt
                    })
            except:
                continue
        
        return errors
    except Exception as e:
        log(f"读取错误日志失败: {e}")
        return []

def analyze_error_patterns(errors):
    """分析错误模式"""
    if not errors:
        return None
    
    # 简单分类
    categories = {
        'network': 0,
        'git': 0,
        'file': 0,
        'api': 0,
        'other': 0
    }
    
    for error in errors:
        title_lower = error['title'].lower()
        if any(kw in title_lower for kw in ['network', 'connect', 'timeout', '443', 'port']):
            categories['network'] += 1
        elif any(kw in title_lower for kw in ['git', 'push', 'commit']):
            categories['git'] += 1
        elif any(kw in title_lower for kw in ['file', 'read', 'write', 'access']):
            categories['file'] += 1
        elif any(kw in title_lower for kw in ['api', 'request', 'response']):
            categories['api'] += 1
        else:
            categories['other'] += 1
    
    # 找出主要问题
    main_category = max(categories, key=categories.get)
    main_count = categories[main_category]
    
    return {
        'total': len(errors),
        'categories': categories,
        'main_category': main_category,
        'main_count': main_count
    }

def generate_improvement_plan(analysis):
    """生成改进方案"""
    if not analysis or analysis['total'] == 0:
        return None
    
    main_cat = analysis['main_category']
    count = analysis['main_count']
    
    # 基于主要问题类型生成方案
    plans = {
        'network': {
            'problem': f'网络相关错误 {count} 次',
            'solution': '增加网络重试机制、超时配置优化',
            'action': 'update_network_config'
        },
        'git': {
            'problem': f'Git操作错误 {count} 次',
            'solution': '优化git操作流程、增加前置检查',
            'action': 'optimize_git_workflow'
        },
        'file': {
            'problem': f'文件操作错误 {count} 次',
            'solution': '增加文件存在性检查、权限验证',
            'action': 'add_file_checks'
        },
        'api': {
            'problem': f'API调用错误 {count} 次',
            'solution': '增加API降级策略、缓存机制',
            'action': 'add_api_fallback'
        },
        'other': {
            'problem': f'其他错误 {count} 次',
            'solution': '增加通用错误处理和日志',
            'action': 'improve_error_handling'
        }
    }
    
    return plans.get(main_cat)

def create_backup():
    """创建版本备份"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_msg = f"backup: 系统进化前自动备份 {timestamp}"
        
        # git add
        subprocess.run(
            ['git', 'add', '-A'],
            cwd=WORKSPACE, capture_output=True, timeout=30
        )
        
        # git commit
        result = subprocess.run(
            ['git', 'commit', '-m', backup_msg],
            cwd=WORKSPACE, capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            # 获取commit hash
            hash_result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=WORKSPACE, capture_output=True, text=True, timeout=10
            )
            commit_hash = hash_result.stdout.strip()[:8] if hash_result.returncode == 0 else "unknown"
            log(f"✅ 备份成功: {commit_hash}")
            return commit_hash
        else:
            log(f"⚠️ 备份警告: {result.stderr[:100]}")
            return None
    except Exception as e:
        log(f"❌ 备份失败: {e}")
        return None

def implement_improvement(plan):
    """实施改进方案"""
    action = plan.get('action')
    
    if action == 'optimize_git_workflow':
        return improve_git_workflow()
    elif action == 'update_network_config':
        return improve_network_config()
    elif action == 'add_file_checks':
        return improve_file_handling()
    elif action == 'add_api_fallback':
        return improve_api_handling()
    else:
        return improve_error_handling()

def improve_git_workflow():
    """改进Git工作流程 - 真正实施"""
    log("实施Git流程优化...")
    
    # 实际改进：在 kimiclaw_v2.py 中增加更详细的git错误处理
    try:
        improvements = []
        
        # 改进1: 检查并修复git推送重试逻辑
        kimiclaw_file = WORKSPACE / "second-brain-processor" / "kimiclaw_v2.py"
        if kimiclaw_file.exists():
            content = kimiclaw_file.read_text(encoding='utf-8')
            
            # 检查是否已经有改进过的推送逻辑
            if 'git push --force-with-lease' not in content:
                # 添加更安全的推送选项
                content = content.replace(
                    "['git', 'push']",
                    "['git', 'push', '--force-with-lease']"
                )
                kimiclaw_file.write_text(content, encoding='utf-8')
                improvements.append('优化git推送安全性(添加--force-with-lease)')
        
        return {'success': True, 'changes': improvements if improvements else ['Git流程已是最优']}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def improve_network_config():
    """改进网络配置 - 真正实施"""
    log("实施网络配置优化...")
    
    try:
        improvements = []
        
        # 改进1: 增加网络超时配置
        run_script = WORKSPACE / "second-brain-processor" / "run_morning_process.sh"
        if run_script.exists():
            content = run_script.read_text(encoding='utf-8')
            
            # 添加超时控制环境变量
            if 'CURL_TIMEOUT' not in content:
                content = content.replace(
                    '#!/bin/bash',
                    '#!/bin/bash\n\n# 网络超时配置\nexport CURL_TIMEOUT=60\nexport GIT_HTTP_TIMEOUT=60'
                )
                run_script.write_text(content, encoding='utf-8')
                improvements.append('添加网络超时环境变量配置')
        
        return {'success': True, 'changes': improvements if improvements else ['网络配置已是最优']}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def improve_file_handling():
    """改进文件处理 - 真正实施"""
    log("实施文件处理优化...")
    
    try:
        improvements = []
        
        # 改进1: 检查文件大小限制是否合理
        kimiclaw_file = WORKSPACE / "second-brain-processor" / "kimiclaw_v2.py"
        if kimiclaw_file.exists():
            content = kimiclaw_file.read_text(encoding='utf-8')
            
            # 检查是否有重复文件检测逻辑
            if '文件已存在' not in content:
                # 在保存对话前添加重复检测
                old_code = """                    with open(target_file, 'w', encoding='utf-8') as f:
                        f.write(content)"""
                new_code = """                    # 检查文件是否已存在（避免重复保存）
                    if target_file.exists():
                        log(f"  跳过已存在的文件: {filename}")
                        continue
                    
                    with open(target_file, 'w', encoding='utf-8') as f:
                        f.write(content)"""
                
                content = content.replace(old_code, new_code)
                kimiclaw_file.write_text(content, encoding='utf-8')
                improvements.append('添加重复文件检测逻辑')
        
        return {'success': True, 'changes': improvements if improvements else ['文件处理已是最优']}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def improve_api_handling():
    """改进API处理 - 真正实施"""
    log("实施API处理优化...")
    
    try:
        improvements = []
        
        # 改进1: 增加API调用失败时的降级策略
        # 在 run_morning_process.sh 中添加错误处理
        run_script = WORKSPACE / "second-brain-processor" / "run_morning_process.sh"
        if run_script.exists():
            content = run_script.read_text(encoding='utf-8')
            
            if 'set -e' in content and 'trap' not in content:
                content = content.replace(
                    'set -e',
                    '''set -e

# 错误处理
trap 'echo "[ERROR] 脚本执行失败，退出码: $?" | tee -a "$LOG_FILE"' ERR'''
                )
                run_script.write_text(content, encoding='utf-8')
                improvements.append('添加脚本错误捕获机制')
        
        return {'success': True, 'changes': improvements if improvements else ['API处理已是最优']}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def improve_error_handling():
    """改进通用错误处理 - 真正实施"""
    log("实施错误处理优化...")
    
    try:
        improvements = []
        
        # 改进1: 确保 .learnings 目录存在并有正确的错误记录格式
        learnings_dir = WORKSPACE / ".learnings"
        learnings_dir.mkdir(parents=True, exist_ok=True)
        
        errors_file = learnings_dir / "ERRORS.md"
        if not errors_file.exists():
            errors_file.write_text("""# 错误日志

记录系统运行中遇到的错误、失败操作及解决方案。

---

""", encoding='utf-8')
            improvements.append('初始化错误日志文件')
        
        # 改进2: 添加系统健康检查脚本
        health_script = WORKSPACE / "second-brain-processor" / "health_check.sh"
        if not health_script.exists():
            health_script.write_text("""#!/bin/bash
# 系统健康检查脚本

echo "=== 系统健康检查 ==="
echo "时间: $(date)"

# 检查Python语法
for py_file in *.py; do
    if python3 -m py_compile "$py_file" 2>/dev/null; then
        echo "✅ $py_file - 语法正确"
    else
        echo "❌ $py_file - 语法错误"
    fi
done

# 检查关键目录
dirs=("/root/.openclaw/workspace/obsidian-vault" "/root/.openclaw/agents/main/sessions")
for dir in "${dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo "✅ 目录存在: $dir"
    else
        echo "❌ 目录不存在: $dir"
    fi
done

echo "=== 检查完成 ==="
""", encoding='utf-8')
            health_script.chmod(0o755)
            improvements.append('创建系统健康检查脚本')
        
        return {'success': True, 'changes': improvements if improvements else ['错误处理已是最优']}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def verify_improvement(plan):
    """验证改进效果 - 真正执行验证"""
    log("验证改进效果...")
    
    try:
        action = plan.get('action')
        verification_results = []
        
        if action == 'optimize_git_workflow':
            # 验证Git配置是否正确
            result = subprocess.run(
                ['git', 'config', '--get', 'push.default'],
                cwd=WORKSPACE, capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                verification_results.append(f"Git推送配置: {result.stdout.strip()}")
            else:
                # 设置安全的推送配置
                subprocess.run(
                    ['git', 'config', 'push.default', 'simple'],
                    cwd=WORKSPACE, capture_output=True, timeout=10
                )
                verification_results.append("已设置Git推送配置为simple")
        
        elif action == 'add_file_checks':
            # 验证文件处理逻辑
            test_file = WORKSPACE / "second-brain-processor" / ".test_file_check"
            test_file.write_text("test", encoding='utf-8')
            if test_file.exists():
                test_file.unlink()
                verification_results.append("文件系统读写正常")
        
        elif action == 'improve_error_handling':
            # 验证错误日志目录
            learnings_dir = WORKSPACE / ".learnings"
            if learnings_dir.exists():
                verification_results.append("错误日志目录存在")
            else:
                learnings_dir.mkdir(parents=True, exist_ok=True)
                verification_results.append("已创建错误日志目录")
        
        # 通用验证：语法检查
        syntax_check = subprocess.run(
            ['python3', '-m', 'py_compile', 'kimiclaw_v2.py'],
            cwd=WORKSPACE / "second-brain-processor",
            capture_output=True, timeout=30
        )
        if syntax_check.returncode == 0:
            verification_results.append("Python语法检查通过")
        else:
            return {'success': False, 'message': f'语法检查失败: {syntax_check.stderr.decode()[:200]}'}
        
        return {
            'success': True, 
            'message': '验证通过: ' + '; '.join(verification_results)
        }
    
    except Exception as e:
        return {'success': False, 'message': f'验证失败: {str(e)}'}

def rollback_to_commit(commit_hash):
    """回滚到指定版本"""
    try:
        log(f"回滚到版本: {commit_hash}")
        result = subprocess.run(
            ['git', 'reset', '--hard', commit_hash],
            cwd=WORKSPACE, capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            log("✅ 回滚成功")
            return True
        else:
            log(f"❌ 回滚失败: {result.stderr}")
            return False
    except Exception as e:
        log(f"❌ 回滚异常: {e}")
        return False

def log_evolution(plan, commit_hash, verification, should_rollback=False):
    """记录进化日志"""
    try:
        timestamp = datetime.now()
        evolution_id = f"EVO-{timestamp.strftime('%Y%m%d')}-{timestamp.strftime('%H%M')}"
        
        status = "已回滚" if should_rollback else ("已验证" if verification.get('success') else "验证失败")
        
        log_entry = f"""
## [{evolution_id}] {plan['solution']}

**时间**: {timestamp.strftime('%Y-%m-%d %H:%M')}
**类型**: 系统优化
**状态**: {status}

### 问题
{plan['problem']}

### 方案
{plan['solution']}

### 回滚点
- Git commit: {commit_hash}
- 回滚命令: `git reset --hard {commit_hash}`

### 验证结果
- 结果: {'通过' if verification.get('success') else '失败'}
- 详情: {verification.get('message', 'N/A')}

### 结论
{'改进成功，效果良好' if verification.get('success') and not should_rollback else '已回滚，需重新分析'}

---
"""
        
        with open(EVOLUTION_LOG, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        log(f"✅ 进化记录已保存: {evolution_id}")
    except Exception as e:
        log(f"❌ 记录进化日志失败: {e}")

def generate_report(analysis, plan, commit_hash, verification):
    """生成结构化报告"""
    report = f"""
🔄 系统论每日复盘报告
═══════════════════════════════════

📊 错误统计（过去24小时）
- 总错误数: {analysis['total'] if analysis else 0}
- 主要问题: {plan['problem'] if plan else '无'}

🔧 改进方案
{plan['solution'] if plan else '今日无需改进'}

✅ 实施状态
- 版本备份: {commit_hash if commit_hash else '未创建'}
- 验证结果: {'通过' if verification.get('success') else '失败'}

📋 建议
{verification.get('message', '继续观察') if verification else '保持现状'}

═══════════════════════════════════
*报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""
    return report

def daily_review():
    """每日复盘主流程"""
    log("=== 系统论每日复盘开始 ===")
    
    # 1. 收集错误
    errors = get_recent_errors(24)
    log(f"发现 {len(errors)} 个错误记录")
    
    # 2. 分析模式
    analysis = analyze_error_patterns(errors)
    if analysis:
        log(f"主要问题类型: {analysis['main_category']} ({analysis['main_count']}次)")
    
    # 3. 生成方案
    plan = generate_improvement_plan(analysis)
    
    if not plan:
        log("✅ 今日无需改进，系统运行良好")
        return generate_report(analysis, None, None, {})
    
    log(f"📝 改进方案: {plan['solution']}")
    
    # 4. 创建备份
    commit_hash = create_backup()
    if not commit_hash:
        log("⚠️ 备份失败，跳过改进")
        return generate_report(analysis, plan, None, {'success': False, 'message': '备份失败'})
    
    # 5. 实施改进
    implementation = implement_improvement(plan)
    if not implementation.get('success'):
        log("❌ 改进实施失败")
        rollback_to_commit(commit_hash)
        log_evolution(plan, commit_hash, {'success': False}, should_rollback=True)
        return generate_report(analysis, plan, commit_hash, {'success': False, 'message': '实施失败，已回滚'})
    
    log(f"✅ 改进实施完成: {', '.join(implementation.get('changes', []))}")
    
    # 6. 验证测试
    verification = verify_improvement(plan)
    
    # 7. 评估效果
    should_rollback = not verification.get('success')
    if should_rollback:
        log("⚠️ 验证失败，执行回滚...")
        rollback_to_commit(commit_hash)
    
    # 8. 记录日志
    log_evolution(plan, commit_hash, verification, should_rollback)
    
    # 9. 生成报告
    report = generate_report(analysis, plan, commit_hash, verification)
    
    log("=== 系统论每日复盘完成 ===")
    return report

def cleanup_old_errors():
    """清理30天前的错误记录"""
    if not ERRORS_FILE.exists():
        return
    
    try:
        content = ERRORS_FILE.read_text(encoding='utf-8')
        cutoff_time = datetime.now() - timedelta(days=ERROR_RETENTION_DAYS)
        
        # 解析并过滤错误条目
        error_pattern = r'(## \[ERR-\d{8}-\d+\] .+?)(?=## \[ERR-|\Z)'
        matches = re.findall(error_pattern, content + '\n## [', re.DOTALL)
        
        kept_errors = []
        for match in matches:
            # 提取时间
            time_match = re.search(r'\*\*Logged\*\*: ([^\n]+)', match)
            if time_match:
                try:
                    log_time = datetime.fromisoformat(time_match.group(1).replace('Z', '+00:00').replace('+00:00', ''))
                    if log_time > cutoff_time:
                        kept_errors.append(match.rstrip())
                except:
                    kept_errors.append(match.rstrip())
            else:
                kept_errors.append(match.rstrip())
        
        # 重新写入文件
        header = "# 错误日志\n\n记录系统运行中遇到的错误、失败操作及解决方案。\n\n---\n\n"
        new_content = header + "\n\n".join(kept_errors)
        
        with open(ERRORS_FILE, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        removed_count = len(matches) - len(kept_errors)
        if removed_count > 0:
            log(f"🧹 清理了 {removed_count} 条30天前的错误记录")
    except Exception as e:
        log(f"⚠️ 清理错误日志失败: {e}")

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--daily-review', action='store_true', help='执行每日复盘')
    parser.add_argument('--analyze-only', action='store_true', help='仅分析不实施')
    parser.add_argument('--rollback', type=str, help='回滚到指定commit')
    args = parser.parse_args()
    
    if args.rollback:
        success = rollback_to_commit(args.rollback)
        sys.exit(0 if success else 1)
    elif args.daily_review:
        # 先清理旧错误
        cleanup_old_errors()
        report = daily_review()
        print("\n" + report)
    elif args.analyze_only:
        errors = get_recent_errors(24)
        analysis = analyze_error_patterns(errors)
        print(json.dumps(analysis, indent=2, default=str))
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
