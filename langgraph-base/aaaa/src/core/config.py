"""
配置管理器 - 处理系统配置的加载和管理
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field

from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SystemConfig:
    """系统配置数据类"""
    system: Dict[str, Any] = field(default_factory=dict)
    server: Dict[str, Any] = field(default_factory=dict)
    message_bus: Dict[str, Any] = field(default_factory=dict)
    agent_registry: Dict[str, Any] = field(default_factory=dict)
    task_manager: Dict[str, Any] = field(default_factory=dict)
    resource_manager: Dict[str, Any] = field(default_factory=dict)
    checkpoint: Dict[str, Any] = field(default_factory=dict)
    monitoring: Dict[str, Any] = field(default_factory=dict)
    database: Dict[str, Any] = field(default_factory=dict)
    redis: Dict[str, Any] = field(default_factory=dict)
    security: Dict[str, Any] = field(default_factory=dict)
    logging: Dict[str, Any] = field(default_factory=dict)
    api: Dict[str, Any] = field(default_factory=dict)
    health_check: Dict[str, Any] = field(default_factory=dict)
    extensions: Dict[str, Any] = field(default_factory=dict)


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self._config: Optional[SystemConfig] = None
        self._raw_config: Dict[str, Any] = {}

    def load_config(self, environment: str = "default") -> SystemConfig:
        """加载配置"""
        try:
            # 获取配置文件路径
            config_file = self.config_dir / f"{environment}.yaml"

            if not config_file.exists():
                logger.warning(f"Config file not found: {config_file}, using default")
                config_file = self.config_dir / "default.yaml"

            if not config_file.exists():
                logger.error("No config file found, using built-in defaults")
                return self._get_builtin_config()

            # 加载配置文件
            with open(config_file, 'r', encoding='utf-8') as f:
                self._raw_config = yaml.safe_load(f)

            # 处理配置继承
            if "extends" in self._raw_config:
                base_config = self._load_base_config(self._raw_config["extends"])
                self._raw_config = self._merge_configs(base_config, self._raw_config)

            # 替换环境变量
            self._raw_config = self._substitute_env_vars(self._raw_config)

            # 创建配置对象
            self._config = SystemConfig(**self._raw_config)

            logger.info(f"Configuration loaded from {config_file}")
            return self._config

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            logger.info("Using built-in default configuration")
            return self._get_builtin_config()

    def get_config(self) -> Optional[SystemConfig]:
        """获取当前配置"""
        return self._config

    def get_value(self, path: str, default: Any = None) -> Any:
        """获取配置值，支持点号路径"""
        if not self._raw_config:
            return default

        keys = path.split('.')
        value = self._raw_config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def _load_base_config(self, base_name: str) -> Dict[str, Any]:
        """加载基础配置"""
        base_file = self.config_dir / f"{base_name}.yaml"
        if not base_file.exists():
            logger.warning(f"Base config file not found: {base_file}")
            return {}

        with open(base_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """合并配置"""
        result = base.copy()

        for key, value in override.items():
            if key == "extends":
                continue  # 跳过继承标记

            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def _substitute_env_vars(self, config: Any) -> Any:
        """替换环境变量"""
        if isinstance(config, dict):
            return {key: self._substitute_env_vars(value) for key, value in config.items()}
        elif isinstance(config, list):
            return [self._substitute_env_vars(item) for item in config]
        elif isinstance(config, str) and config.startswith("${") and config.endswith("}"):
            env_var = config[2:-1]
            default_value = None
            if ":" in env_var:
                env_var, default_value = env_var.split(":", 1)
            return os.getenv(env_var, default_value)
        else:
            return config

    def _get_builtin_config(self) -> SystemConfig:
        """获取内置默认配置"""
        return SystemConfig(
            system={
                "name": "LangGraph Agent System",
                "version": "0.1.0",
                "debug": False,
                "log_level": "INFO"
            },
            server={
                "host": "127.0.0.1",
                "port": 8000,
                "workers": 1,
                "timeout": 300,
                "max_connections": 100
            },
            message_bus={
                "max_queue_size": 1000,
                "message_retention_hours": 24,
                "processing_interval_seconds": 0.01,
                "max_message_size_mb": 10
            },
            agent_registry={
                "heartbeat_timeout_seconds": 300,
                "cleanup_interval_seconds": 60,
                "max_agents": 100,
                "auto_cleanup": True
            },
            task_manager={
                "max_concurrent_tasks": 100,
                "default_timeout_seconds": 3600,
                "retry_attempts": 3,
                "cleanup_interval_hours": 1,
                "task_retention_days": 30
            },
            resource_manager={
                "monitoring_interval_seconds": 60,
                "rebalance_interval_seconds": 600,
                "default_agent_limits": {
                    "max_concurrent_tasks": 5,
                    "max_cpu_usage": 80.0,
                    "max_memory_usage": 80.0
                }
            },
            monitoring={
                "enabled": True,
                "monitoring_interval_seconds": 30,
                "performance_tracking": {
                    "enabled": True,
                    "detailed_logging": False
                }
            },
            logging={
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "console_output": True
            },
            health_check={
                "enabled": True,
                "interval_seconds": 30,
                "timeout_seconds": 10
            }
        )

    def save_config(self, config: SystemConfig, file_path: str) -> bool:
        """保存配置到文件"""
        try:
            config_dict = {
                "system": config.system,
                "server": config.server,
                "message_bus": config.message_bus,
                "agent_registry": config.agent_registry,
                "task_manager": config.task_manager,
                "resource_manager": config.resource_manager,
                "checkpoint": config.checkpoint,
                "monitoring": config.monitoring,
                "database": config.database,
                "redis": config.redis,
                "security": config.security,
                "logging": config.logging,
                "api": config.api,
                "health_check": config.health_check,
                "extensions": config.extensions
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)

            logger.info(f"Configuration saved to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False

    def validate_config(self) -> Dict[str, Any]:
        """验证配置"""
        errors = []
        warnings = []

        if not self._config:
            return {"valid": False, "errors": ["No configuration loaded"]}

        # 验证必需的配置项
        required_sections = ["system", "server", "message_bus"]
        for section in required_sections:
            if not hasattr(self._config, section) or not getattr(self._config, section):
                errors.append(f"Missing required configuration section: {section}")

        # 验证服务器配置
        if self._config.server:
            if not (1 <= self._config.server.get("port", 0) <= 65535):
                errors.append("Invalid server port number")

            if self._config.server.get("workers", 0) < 1:
                warnings.append("Server workers should be at least 1")

        # 验证消息总线配置
        if self._config.message_bus:
            if self._config.message_bus.get("max_queue_size", 0) <= 0:
                errors.append("Message bus max_queue_size must be positive")

        # 验证任务管理器配置
        if self._config.task_manager:
            if self._config.task_manager.get("max_concurrent_tasks", 0) <= 0:
                errors.append("Task manager max_concurrent_tasks must be positive")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }