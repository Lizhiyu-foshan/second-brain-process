#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一配置加载器

提供集中化的配置管理，支持：
- YAML 配置文件加载
- 环境变量替换
- 路径自动解析
- 配置缓存
- 配置验证

使用示例：
    from config_loader import Config
    
    config = Config()
    
    # 获取路径
    workspace = config.get_path('workspace')
    vault_dir = config.get_path('directories.obsidian_vault')
    
    # 获取设置
    debug = config.get('app.debug')
    timeout = config.get('timeouts.ai_request')
    
    # 获取模型
    model_id = config.get_model('qwen')
    api_key = config.get_api_key('alicloud')
"""

import os
import re
from pathlib import Path
from typing import Any, Optional, Dict, Union
import json

# 尝试导入 yaml，如果不存在则使用简单解析
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class Config:
    """统一配置加载器"""
    
    _instance = None
    _cache = {}
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化配置加载器"""
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.config_dir = Path(__file__).parent
        self.workspace = None
        self.paths = {}
        self.settings = {}
        self.models = {}
        
        self._load_all()
    
    def _load_all(self):
        """加载所有配置文件"""
        # 首先加载 paths.yaml 获取 workspace
        self.paths = self._load_yaml('paths.yaml')
        
        # 解析 workspace 环境变量
        workspace_str = self.paths.get('workspace', '/root/.openclaw/workspace')
        self.workspace = Path(self._resolve_env(workspace_str))
        
        # 加载其他配置
        self.settings = self._load_yaml('settings.yaml')
        self.models = self._load_yaml('models.yaml')
        
        # 解析所有路径
        self._resolve_all_paths()
    
    def _load_yaml(self, filename: str) -> Dict:
        """加载 YAML 文件"""
        file_path = self.config_dir / filename
        
        if not file_path.exists():
            print(f"⚠️ 配置文件不存在：{file_path}")
            return {}
        
        if HAS_YAML:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # 先解析环境变量
                content = self._resolve_env_in_content(content)
                return yaml.safe_load(content) or {}
        else:
            # 简单 YAML 解析（支持基本的键值对和嵌套）
            return self._simple_yaml_parse(file_path)
    
    def _simple_yaml_parse(self, file_path: Path) -> Dict:
        """简单的 YAML 解析器（当 PyYAML 不可用时）"""
        result = {}
        current_dict = result
        indent_stack = [(0, result)]
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                # 跳过注释和空行
                line_stripped = line.strip()
                if not line_stripped or line_stripped.startswith('#'):
                    continue
                
                # 计算缩进
                indent = len(line) - len(line.lstrip())
                
                # 处理键值对
                if ':' in line_stripped:
                    key, _, value = line_stripped.partition(':')
                    key = key.strip()
                    value = value.strip()
                    
                    # 调整当前层级
                    while indent_stack and indent <= indent_stack[-1][0] and len(indent_stack) > 1:
                        indent_stack.pop()
                    
                    current_dict = indent_stack[-1][1]
                    
                    if value:
                        # 有值的情况
                        if value.startswith('${') and value.endswith('}'):
                            # 环境变量
                            value = self._resolve_env(value)
                        elif value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        elif value.lower() in ('true', 'false'):
                            value = value.lower() == 'true'
                        elif value.isdigit():
                            value = int(value)
                        
                        current_dict[key] = value
                    else:
                        # 嵌套字典
                        new_dict = {}
                        current_dict[key] = new_dict
                        indent_stack.append((indent + 2, new_dict))
        
        return result
    
    def _resolve_env(self, value: str) -> str:
        """解析环境变量"""
        if not isinstance(value, str):
            return value
        
        # 匹配 ${VAR:-default} 或 ${VAR}
        pattern = r'\$\{([^}:]+)(?::-([^}]*))?\}'
        
        def replace(match):
            var_name = match.group(1)
            default = match.group(2) if match.group(2) is not None else ''
            return os.environ.get(var_name, default)
        
        return re.sub(pattern, replace, value)
    
    def _resolve_env_in_content(self, content: str) -> str:
        """解析内容中的环境变量"""
        return self._resolve_env(content)
    
    def _resolve_all_paths(self):
        """解析所有路径"""
        def resolve_dict(d: Dict, workspace: Path) -> Dict:
            for key, value in d.items():
                if isinstance(value, str):
                    # 替换 {workspace} 占位符
                    value = value.replace('{workspace}', str(workspace))
                    # 替换其他已解析的路径
                    for path_key, path_value in self.paths.items():
                        if path_key != 'workspace' and isinstance(path_value, str):
                            value = value.replace('{' + path_key + '}', path_value)
                    d[key] = value
                elif isinstance(value, dict):
                    d[key] = resolve_dict(value, workspace)
            return d
        
        self.paths = resolve_dict(self.paths, self.workspace)
    
    def get_path(self, key: str) -> Path:
        """获取路径"""
        keys = key.split('.')
        value = self.paths
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                raise KeyError(f"路径配置不存在：{key}")
        
        if value is None:
            raise KeyError(f"路径配置不存在：{key}")
        
        return Path(value)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        keys = key.split('.')
        
        # 根据第一个键决定从哪个配置中查找
        first_key = keys[0]
        if first_key in ['app', 'timeouts', 'retry', 'batch', 'logging', 'queue']:
            value = self.settings
        elif first_key in ['api', 'mapping', 'default_model', 'scenarios', 'display_names']:
            value = self.models
        else:
            value = self.paths
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        
        return value if value is not None else default
    
    def get_model(self, name: str) -> str:
        """获取模型 ID"""
        mapping = self.models.get('mapping', {})
        model_id = mapping.get(name, self.models.get('default_model', 'kimi-coding/k2p5'))
        return model_id
    
    def get_api_key(self, provider: str) -> str:
        """获取 API Key"""
        api_config = self.models.get('api', {})
        provider_config = api_config.get(provider, {})
        return provider_config.get('api_key', '')
    
    def get_base_url(self, provider: str) -> str:
        """获取 API 基础 URL"""
        api_config = self.models.get('api', {})
        provider_config = api_config.get(provider, {})
        return provider_config.get('base_url', '')
    
    def get_scenario_config(self, scenario: str) -> Dict:
        """获取场景化配置"""
        scenarios = self.models.get('scenarios', {})
        return scenarios.get(scenario, {})
    
    def validate(self) -> bool:
        """验证配置是否完整"""
        required_paths = [
            'workspace',
            'directories.second_brain_processor',
            'directories.learnings',
            'directories.memory',
        ]
        
        for path in required_paths:
            try:
                self.get_path(path)
            except KeyError:
                print(f"❌ 缺少必需的路径配置：{path}")
                return False
        
        # 验证 API Key
        api_key = self.get_api_key('alicloud')
        if not api_key:
            print("⚠️ 警告：ALICLOUD_API_KEY 未配置")
        
        return True
    
    def to_dict(self) -> Dict:
        """导出所有配置为字典"""
        return {
            'paths': self.paths,
            'settings': self.settings,
            'models': self.models,
        }
    
    def __repr__(self) -> str:
        return f"Config(workspace={self.workspace})"


# 便捷函数
def get_config() -> Config:
    """获取配置实例"""
    return Config()


def get_path(key: str) -> Path:
    """便捷获取路径"""
    return Config().get_path(key)


def get_setting(key: str, default: Any = None) -> Any:
    """便捷获取设置"""
    return Config().get(key, default)


# 测试
if __name__ == '__main__':
    config = Config()
    
    print("=== 配置加载测试 ===")
    print(f"Workspace: {config.workspace}")
    print(f"Vault Dir: {config.get_path('directories.obsidian_vault')}")
    print(f"Learnings Dir: {config.get_path('directories.learnings')}")
    print(f"Debug Mode: {config.get('app.debug')}")
    print(f"AI Timeout: {config.get('timeouts.ai_request')}秒")
    print(f"Qwen Model: {config.get_model('qwen')}")
    print(f"Kimi Model: {config.get_model('kimi')}")
    print(f"API Key: {'已配置' if config.get_api_key('alicloud') else '未配置'}")
    
    print("\n=== 验证配置 ===")
    if config.validate():
        print("✅ 配置验证通过")
    else:
        print("❌ 配置验证失败")
