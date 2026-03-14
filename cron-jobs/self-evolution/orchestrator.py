#!/usr/bin/env python3
"""
自我进化流水线编排器
协调架构师、开发者、测试员三个Agent完成系统改进
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 配置
WORKSPACE = Path("/root/.openclaw/workspace")
SHARED_DIR = WORKSPACE / "shared"
PIPELINE_DIR = SHARED_DIR / "pipeline"
CONFIG_DIR = SHARED_DIR / "config"
AGENTS_DIR = Path("/root/.openclaw/agents")

def load_preferences():
    """加载用户偏好配置"""
    pref_file = CONFIG_DIR / "user-preferences.json"
    if pref_file.exists():
        return json.loads(pref_file.read_text())
    return {}

def call_agent(agent_name, task_message, model, thinking="medium"):
    """
    调用指定Agent执行任务
    使用 sessions_spawn 创建子Agent会话
    """
    print(f"\n{'='*60}")
    print(f"调用Agent: {agent_name}")
    print(f"模型: {model}")
    print(f"任务: {task_message[:100]}...")
    print(f"{'='*60}\n")
    
    try:
        # 构建完整的prompt（包含共享规则）
        full_prompt = f"""请先读取以下共享配置文件：
1. /root/.openclaw/workspace/shared/config/global-rules.md
2. /root/.openclaw/workspace/shared/config/user-preferences.json

然后执行以下任务：
{task_message}

注意：你是{agent_name}角色，请遵循你的AGENTS.md和SOUL.md定义的行为准则。
"""
        
        # 使用openclaw命令行调用（如果支持）
        # 或者通过sessions_spawn
        result = subprocess.run([
            sys.executable, "-c",
            f"""
import subprocess
import json

# 创建Agent会话并执行任务
msg = {repr(full_prompt)}
model = {repr(model)}
thinking = {repr(thinking)}

# 这里使用openclaw的agent运行机制
# 实际实现可能需要根据openclaw的API调整
result = subprocess.run([
    "openclaw", "agent", "run",
    "--agent", "{agent_name}",
    "--model", model,
    "--thinking", thinking,
    "--message", msg
], capture_output=True, text=True, timeout=1800)

print(result.stdout)
if result.returncode != 0:
    print("STDERR:", result.stderr, file=sys.stderr)
    sys.exit(1)
"""
        ], capture_output=True, text=True, timeout=1900)
        
        success = result.returncode == 0
        return success, result.stdout, result.stderr
        
    except subprocess.TimeoutExpired:
        return False, "", "Agent执行超时（30分钟）"
    except Exception as e:
        return False, "", str(e)

def check_stage_input(stage_name, input_file):
    """检查前置阶段输出是否存在"""
    if not input_file:
        return True, None
    
    file_path = PIPELINE_DIR / input_file.replace("YYYYMMDD", datetime.now().strftime("%Y%m%d"))
    
    if not file_path.exists():
        return False, f"前置文件不存在: {file_path}"
    
    try:
        data = json.loads(file_path.read_text())
        status = data.get("status", "unknown")
        if status == "failed":
            return False, f"前置阶段失败: {file_path}"
        return True, data
    except json.JSONDecodeError:
        return False, f"前置文件格式错误: {file_path}"

def update_stage_status(stage_name, status, data=None):
    """更新阶段状态文件"""
    status_file = PIPELINE_DIR / f"status_{datetime.now().strftime('%Y%m%d')}.json"
    
    all_status = {}
    if status_file.exists():
        all_status = json.loads(status_file.read_text())
    
    all_status[stage_name] = {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "data": data or {}
    }
    
    status_file.write_text(json.dumps(all_status, indent=2), encoding="utf-8")

def run_stage(stage_config, preferences):
    """运行单个阶段"""
    stage_name = stage_config["name"]
    agent_name = stage_config["agent"]
    timeout = stage_config.get("timeout_minutes", 30)
    input_file = stage_config.get("input")
    output_file = stage_config.get("output", "")
    
    print(f"\n{'#'*70}")
    print(f"# Stage: {stage_name}")
    print(f"{'#'*70}\n")
    
    # 检查前置条件
    if input_file:
        ok, data = check_stage_input(stage_name, input_file)
        if not ok:
            print(f"❌ 前置检查失败: {data}")
            update_stage_status(stage_name, "skipped", {"reason": data})
            return False
        print(f"✅ 前置检查通过")
    
    # 获取Agent配置
    agent_config = preferences.get("agents", {}).get(agent_name, {})
    model = agent_config.get("model", "kimi-coding/k2p5")
    thinking = agent_config.get("thinking", "medium")
    
    # 构建任务消息
    today = datetime.now().strftime("%Y%m%d")
    output_path = str(PIPELINE_DIR / output_file.replace("YYYYMMDD", today))
    
    task_message = f"""请执行{stage_name}阶段的任务。

当前日期: {today}
输出文件: {output_path}

请确保：
1. 读取必要的输入文件（如果有）
2. 按照你的工作流程执行任务
3. 将结果以JSON格式写入指定的输出文件
4. 在JSON中包含 'status' 字段（completed/failed）

开始工作。
"""
    
    # 调用Agent
    update_stage_status(stage_name, "processing")
    success, stdout, stderr = call_agent(agent_name, task_message, model, thinking)
    
    if success:
        # 检查输出文件
        if Path(output_path).exists():
            try:
                output_data = json.loads(Path(output_path).read_text())
                final_status = output_data.get("status", "unknown")
                update_stage_status(stage_name, final_status, output_data)
                print(f"✅ Stage {stage_name} 完成，状态: {final_status}")
                return final_status == "completed"
            except:
                update_stage_status(stage_name, "completed")
                return True
        else:
            print(f"⚠️ 输出文件未生成，但Agent执行成功")
            update_stage_status(stage_name, "completed")
            return True
    else:
        print(f"❌ Stage {stage_name} 失败")
        print(f"错误: {stderr}")
        update_stage_status(stage_name, "failed", {"error": stderr})
        return False

def pipeline():
    """主流水线"""
    print("="*70)
    print("自我进化流水线启动")
    print(f"时间: {datetime.now().isoformat()}")
    print("="*70)
    
    # 加载配置
    preferences = load_preferences()
    pipeline_config = preferences.get("pipeline", {})
    stages = pipeline_config.get("stages", [])
    
    if not stages:
        print("❌ 未找到pipeline配置")
        return False
    
    print(f"\n配置加载成功，共 {len(stages)} 个阶段")
    
    # 创建pipeline目录
    PIPELINE_DIR.mkdir(parents=True, exist_ok=True)
    
    # 执行各阶段
    all_success = True
    for stage in stages:
        success = run_stage(stage, preferences)
        if not success:
            all_success = False
            print(f"\n⛔ 流水线中断于阶段: {stage['name']}")
            break
    
    # 总结
    print("\n" + "="*70)
    print("流水线执行完成")
    print(f"最终结果: {'✅ 成功' if all_success else '❌ 失败'}")
    print("="*70)
    
    return all_success

if __name__ == "__main__":
    try:
        success = pipeline()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 流水线异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
