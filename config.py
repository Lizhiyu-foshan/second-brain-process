# 系统路径配置和统一配置加载
# 此文件用于集中管理所有配置，避免硬编码和代码重复

import os
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
# 基础路径配置
# ═══════════════════════════════════════════════════════════════

WORKSPACE = Path(os.environ.get('KIMI_WORKSPACE', '/root/.openclaw/workspace'))
PROCESSOR_DIR = WORKSPACE / "second-brain-processor"
LEARNINGS_DIR = WORKSPACE / ".learnings"
MEMORY_DIR = WORKSPACE / "memory"

# 状态文件
MODEL_STATE_FILE = LEARNINGS_DIR / "model_session_state.json"
AI_PENDING_FILE = LEARNINGS_DIR / "AI_PENDING.json"
AI_RESULTS_FILE = LEARNINGS_DIR / "AI_RESULTS.json"
ERRORS_FILE = LEARNINGS_DIR / "ERRORS.md"
EVOLUTION_LOG = LEARNINGS_DIR / "EVOLUTION_LOG.md"
FAKE_IMPL_FILE = LEARNINGS_DIR / "FAKE_IMPLEMENTATIONS.md"

# 环境变量文件
ENV_FILE = WORKSPACE / ".env"

# ═══════════════════════════════════════════════════════════════
# 统一环境变量加载
# ═══════════════════════════════════════════════════════════════

def load_env_file():
    """统一加载 .env 文件到环境变量"""
    if ENV_FILE.exists():
        try:
            with open(ENV_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value
        except (IOError, UnicodeDecodeError) as e:
            print(f"⚠️ 加载 .env 文件失败: {e}")

# 自动加载（首次导入时）
load_env_file()

# ═══════════════════════════════════════════════════════════════
# 模型配置
# ═══════════════════════════════════════════════════════════════

# 阿里云API配置
ALICLOUD_API_KEY = os.environ.get('ALICLOUD_API_KEY', '')
ALICLOUD_BASE_URL = os.environ.get('ALICLOUD_BASE_URL', 'https://coding.dashscope.aliyuncs.com/v1')

# 模型ID配置
ALICLOUD_MODEL_FAST = os.environ.get('ALICLOUD_MODEL_FAST', 'MiniMax-M2.5')
ALICLOUD_MODEL_COMPLEX = os.environ.get('ALICLOUD_MODEL_COMPLEX', 'glm-5')
ALICLOUD_MODEL_CHAT_FAST = os.environ.get('ALICLOUD_MODEL_CHAT_FAST', 'qwen3.5-plus')
ALICLOUD_MODEL_CHAT_COMPLEX = os.environ.get('ALICLOUD_MODEL_CHAT_COMPLEX', 'kimi-2.5')

# 默认模型
DEFAULT_MODEL = "kimi-coding/k2p5"

# 模型映射（统一名称 -> 完整ID）
MODEL_MAPPING = {
    "minimax": "alicloud/MiniMax-M2.5",
    "MiniMax": "alicloud/MiniMax-M2.5",
    "glm": "alicloud/glm-5",
    "GLM": "alicloud/glm-5",
    "glm-5": "alicloud/glm-5",
    "qwen": "alicloud/qwen3.5-plus",
    "Qwen": "alicloud/qwen3.5-plus",
    "qwen3.5-plus": "alicloud/qwen3.5-plus",
    "通义": "alicloud/qwen3.5-plus",
    "kimi": "kimi-coding/k2p5",
    "Kimi": "kimi-coding/k2p5",
    "kimi-2.5": "kimi-coding/k2p5",
    "default": DEFAULT_MODEL,
    "默认": DEFAULT_MODEL,
}

# ═══════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════

def ensure_directories():
    """确保所有需要的目录都存在"""
    LEARNINGS_DIR.mkdir(parents=True, exist_ok=True)
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def validate_api_key() -> str:
    """验证API Key是否存在"""
    key = ALICLOUD_API_KEY.strip()
    if not key:
        raise ValueError("❌ ALICLOUD_API_KEY 未配置，请在 .env 文件中设置")
    return key


def get_model_display_name(model_id: str) -> str:
    """获取模型的显示名称"""
    names = {
        "alicloud/MiniMax-M2.5": "MiniMax M2.5",
        "alicloud/glm-5": "GLM-5",
        "alicloud/qwen3.5-plus": "Qwen 3.5 Plus",
        "kimi-coding/k2p5": "Kimi 2.5"
    }
    return names.get(model_id, model_id)
