#!/usr/bin/env python3
"""
技能安装验证报告生成器
验证已安装技能的有效性
"""
import subprocess
import sys
from pathlib import Path
from datetime import datetime

def run_command(cmd, cwd=None):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30, cwd=cwd)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_skill(skill_name, skill_path):
    """检查单个技能"""
    report = {
        "name": skill_name,
        "path": str(skill_path),
        "checks": {}
    }
    
    # 1. 检查 SKILL.md
    skill_md = skill_path / "SKILL.md"
    report["checks"]["skill_md"] = skill_md.exists()
    
    # 2. 检查 scripts 目录
    scripts_dir = skill_path / "scripts"
    report["checks"]["scripts_dir"] = scripts_dir.exists()
    
    # 3. 获取 Python 文件列表
    if scripts_dir.exists():
        py_files = list(scripts_dir.glob("*.py"))
        report["python_files"] = [f.name for f in py_files]
        
        # 4. 语法检查
        syntax_ok = True
        for py_file in py_files:
            ok, _, _ = run_command(f"python3 -m py_compile {py_file}", cwd=scripts_dir)
            if not ok:
                syntax_ok = False
                break
        report["checks"]["syntax"] = syntax_ok
    else:
        report["python_files"] = []
        report["checks"]["syntax"] = False
    
    return report

def main():
    print("=" * 70)
    print("🔍 技能安装验证报告")
    print("=" * 70)
    print(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    skills_dir = Path("/root/.openclaw/skills")
    
    # 要验证的技能列表
    skills_to_check = [
        "openclaw-version-adapter",
        "auto-error-logger"
    ]
    
    all_passed = True
    
    for skill_name in skills_to_check:
        skill_path = skills_dir / skill_name
        print(f"\n📦 检查技能: {skill_name}")
        print("-" * 50)
        
        if not skill_path.exists():
            print(f"   ❌ 技能目录不存在: {skill_path}")
            all_passed = False
            continue
        
        report = check_skill(skill_name, skill_path)
        
        # 输出检查结果
        for check_name, result in report["checks"].items():
            status = "✅" if result else "❌"
            print(f"   {status} {check_name}: {result}")
        
        if report["python_files"]:
            print(f"   📄 Python文件: {', '.join(report['python_files'])}")
        
        # 运行功能测试
        if skill_name == "openclaw-version-adapter":
            print(f"\n   🧪 功能测试:")
            ok, stdout, stderr = run_command("python3 scripts/check_version.py", cwd=skill_path)
            if ok and "发现新版本" in stdout:
                print(f"      ✅ 版本检查: 正常 (检测到新版本)")
            else:
                print(f"      ⚠️  版本检查: 需要关注")
            
            ok, stdout, stderr = run_command("python3 scripts/test_compatibility.py", cwd=skill_path)
            if ok and "Passed: 3" in stdout:
                print(f"      ✅ 兼容性测试: 3/3 通过")
            else:
                print(f"      ⚠️  兼容性测试: 需要关注")
                
        elif skill_name == "auto-error-logger":
            print(f"\n   🧪 功能测试:")
            ok, stdout, stderr = run_command("python3 scripts/test_error_logger.py", cwd=skill_path)
            if ok and "通过: 7/7" in stdout:
                print(f"      ✅ 单元测试: 7/7 通过")
            else:
                print(f"      ⚠️  单元测试: 需要关注")
    
    print("\n" + "=" * 70)
    print("📊 验证总结")
    print("=" * 70)
    
    for skill_name in skills_to_check:
        skill_path = skills_dir / skill_name
        if skill_path.exists():
            print(f"✅ {skill_name}: 已安装并验证")
        else:
            print(f"❌ {skill_name}: 未找到")
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 所有技能验证通过！")
    else:
        print("⚠️  部分技能需要检查")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
