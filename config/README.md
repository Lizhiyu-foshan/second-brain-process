# 统一配置管理系统

## 📁 目录结构

```
/root/.openclaw/workspace/config/
├── __init__.py           # Python 包标识
├── config_loader.py      # 配置加载库
├── paths.yaml           # 路径配置
├── settings.yaml        # 系统设置
└── models.yaml          # 模型配置
```

## 🚀 快速开始

### 新代码推荐使用方式

```python
# 方式 1：直接使用便捷函数
from config_loader import get_path, get_setting, get_model

vault_dir = get_path('directories.obsidian_vault')
timeout = get_setting('timeouts.ai_request')
model_id = get_model('qwen')

# 方式 2：使用 Config 类
from config_loader import Config

config = Config()
workspace = config.workspace
learnings_dir = config.get_path('directories.learnings')
api_key = config.get_api_key('alicloud')
```

### 在 second-brain-processor 目录中使用

```python
# 导入统一的 config.py（已集成新配置系统）
import sys
from pathlib import Path

# 添加 workspace 到路径
WORKSPACE = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE))

# 现在可以使用 config.py 中的所有配置
from config import WORKSPACE, LEARNINGS_DIR, DEFAULT_MODEL, ALICLOUD_API_KEY

# 或者使用新配置系统
from config import get_path, get_setting
vault_dir = get_path('directories.obsidian_vault')
```

## 📋 配置说明

### paths.yaml - 路径配置

```yaml
workspace: ${KIMI_WORKSPACE:-/root/.openclaw/workspace}

directories:
  second_brain_processor: "{workspace}/second-brain-processor"
  learnings: "{workspace}/.learnings"
  memory: "{workspace}/memory"
  obsidian_vault: "{workspace}/obsidian-vault"

files:
  model_state: "{learnings}/model_session_state.json"
  ai_pending: "{learnings}/AI_PENDING.json"
```

**支持的环境变量**：
- `KIMI_WORKSPACE` - 工作区根目录

**支持的占位符**：
- `{workspace}` - 工作区根目录
- `{learnings}` - Learnings 目录
- `{memory}` - Memory 目录
- 等等（自动解析）

### settings.yaml - 系统设置

```yaml
app:
  name: "Kimi Claw Second Brain"
  version: "2.0"
  environment: production  # development, staging, production

timeouts:
  ai_request: 300  # 5 分钟
  file_operation: 30
  network_request: 60

retry:
  max_attempts: 3
  delay_seconds: 5
```

### models.yaml - 模型配置

```yaml
api:
  alicloud:
    base_url: ${ALICLOUD_BASE_URL:-https://coding.dashscope.aliyuncs.com/v1}
    api_key: ${ALICLOUD_API_KEY}

mapping:
  qwen: "alicloud/qwen3.5-plus"
  kimi: "kimi-coding/k2p5"
  glm: "alicloud/glm-5"
  minimax: "alicloud/MiniMax-M2.5"

default_model: "kimi-coding/k2p5"
```

**支持的环境变量**：
- `ALICLOUD_API_KEY` - 阿里云 API 密钥
- `ALICLOUD_BASE_URL` - API 基础 URL

## 🔧 配置加载器 API

### Config 类

```python
from config_loader import Config

config = Config()

# 获取路径（返回 Path 对象）
config.get_path('workspace')
config.get_path('directories.obsidian_vault')

# 获取设置
config.get('app.debug', default=False)
config.get('timeouts.ai_request')

# 获取模型
config.get_model('qwen')  # 返回 "alicloud/qwen3.5-plus"
config.get_model('kimi')  # 返回 "kimi-coding/k2p5"

# 获取 API 配置
config.get_api_key('alicloud')
config.get_base_url('alicloud')

# 获取场景化配置
config.get_scenario_config('fast_chat')
# 返回：{'model': 'kimi-coding/k2p5', 'max_tokens': 2048, ...}

# 验证配置
if config.validate():
    print("✅ 配置验证通过")
```

### 便捷函数

```python
from config_loader import get_path, get_setting, get_model, get_config

# 获取路径
vault = get_path('directories.obsidian_vault')

# 获取设置
timeout = get_setting('timeouts.ai_request')

# 获取模型
model = get_model('qwen')

# 获取 Config 实例
config = get_config()
```

## 🎯 迁移指南

### 旧代码（硬编码路径）

```python
# ❌ 不推荐：硬编码路径
VAULT_DIR = Path("/root/.openclaw/workspace/obsidian-vault")
WORKSPACE = Path("/root/.openclaw/workspace")
```

### 新代码（使用配置）

```python
# ✅ 推荐：使用配置
from config_loader import get_path

VAULT_DIR = get_path('directories.obsidian_vault')
WORKSPACE = get_path('workspace')

# 或者使用 Config 类
from config_loader import Config
config = Config()
VAULT_DIR = config.get_path('directories.obsidian_vault')
```

### 向后兼容

现有的 `second-brain-processor/config.py` 已经集成了新配置系统，并保持向后兼容：

```python
# 现有脚本可以继续使用这些变量
from config import WORKSPACE, LEARNINGS_DIR, DEFAULT_MODEL

# 它们会自动使用新配置系统（如果可用）
```

## ✅ 验证配置

运行测试脚本：

```bash
cd /root/.openclaw/workspace/config
python3 config_loader.py
```

预期输出：
```
=== 配置加载测试 ===
Workspace: /root/.openclaw/workspace
Vault Dir: /root/.openclaw/workspace/obsidian-vault
Learnings Dir: /root/.openclaw/workspace/.learnings
Debug Mode: False
AI Timeout: 300 秒
Qwen Model: alicloud/qwen3.5-plus
Kimi Model: kimi-coding/k2p5
API Key: 已配置

=== 验证配置 ===
✅ 配置验证通过
```

## 📝 最佳实践

1. **新代码**：始终使用 `config_loader.py` 获取路径和配置
2. **旧代码**：逐步迁移到使用 `config_loader.py`
3. **不要硬编码**：避免在代码中直接写路径字符串
4. **环境变量优先**：敏感信息（API Key）通过环境变量配置
5. **集中管理**：所有配置集中在 `config/` 目录下

## 🐛 故障排查

### 问题：导入失败 "No module named 'config.config_loader'"

**原因**：文件名冲突（本地有 config.py）

**解决**：使用绝对导入或 importlib

```python
import importlib.util
spec = importlib.util.spec_from_file_location(
    "config_loader",
    "/root/.openclaw/workspace/config/config_loader.py"
)
config_loader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config_loader)
```

### 问题：环境变量未生效

**检查**：
1. 确认 `.env` 文件存在
2. 确认环境变量已导出
3. 重启 Python 进程

### 问题：路径解析错误

**检查**：
1. YAML 语法是否正确
2. 占位符格式：`{workspace}`（花括号）
3. 环境变量格式：`${VAR:-default}`

## 📚 相关文件

- 配置文件：`/root/.openclaw/workspace/config/*.yaml`
- 配置加载器：`/root/.openclaw/workspace/config/config_loader.py`
- 统一 config：`/root/.openclaw/workspace/second-brain-processor/config.py`
- 测试脚本：`/root/.openclaw/workspace/test_config_import.py`
