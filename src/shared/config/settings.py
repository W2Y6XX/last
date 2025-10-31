"""
统一配置管理器

重构说明：整合分散的配置文件到统一配置管理系统
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """数据库配置"""
    type: str = "sqlite"
    sqlite_path: str = "data/app.db"
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    echo: bool = False

@dataclass
class RedisConfig:
    """Redis配置"""
    url: str = "redis://localhost:6379/0"
    max_connections: int = 10
    retry_on_timeout: bool = True

@dataclass
class APIConfig:
    """API配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    enable_auth: bool = False
    enable_docs: bool = True
    cors_origins: list = field(default_factory=lambda: ["*"])

@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5

@dataclass
class LLMConfig:
    """LLM配置"""
    provider: str = "siliconflow"
    api_key: str = "sk-wmxxamqdqsmscgrrmweqsqcieowsmqpxqwvenlelrxtkvmms"
    base_url: str = "https://api.siliconflow.cn/v1"
    model: str = "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B"
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: int = 60
    max_retries: int = 3

@dataclass
class SystemConfig:
    """系统配置"""
    environment: str = "development"
    debug: bool = False
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    api: APIConfig = field(default_factory=APIConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)

class Settings:
    """统一设置管理器"""

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or os.getenv("CONFIG_FILE", "config.yaml")
        self._config: Optional[SystemConfig] = None

    @property
    def config(self) -> SystemConfig:
        """获取配置（懒加载）"""
        if self._config is None:
            self._config = self._load_config()
        return self._config

    def _load_config(self) -> SystemConfig:
        """加载配置"""
        try:
            # 创建基础配置
            config = SystemConfig()

            # 从环境变量覆盖
            self._load_from_environment(config)

            # 从配置文件加载（如果存在）
            if os.path.exists(self.config_file):
                self._load_from_file(config)

            return config

        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return SystemConfig()

    def _load_from_environment(self, config: SystemConfig):
        """从环境变量加载配置"""
        # 系统配置
        config.environment = os.getenv("ENVIRONMENT", config.environment)
        config.debug = os.getenv("DEBUG", "false").lower() == "true"

        # 数据库配置
        if os.getenv("DATABASE_TYPE"):
            config.database.type = os.getenv("DATABASE_TYPE")
        if os.getenv("SQLITE_DATABASE_PATH"):
            config.database.sqlite_path = os.getenv("SQLITE_DATABASE_PATH")
        if os.getenv("DATABASE_POOL_SIZE"):
            config.database.pool_size = int(os.getenv("DATABASE_POOL_SIZE"))

        # Redis配置
        if os.getenv("REDIS_URL"):
            config.redis.url = os.getenv("REDIS_URL")
        if os.getenv("REDIS_MAX_CONNECTIONS"):
            config.redis.max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS"))

        # API配置
        if os.getenv("API_HOST"):
            config.api.host = os.getenv("API_HOST")
        if os.getenv("API_PORT"):
            config.api.port = int(os.getenv("API_PORT"))
        if os.getenv("API_WORKERS"):
            config.api.workers = int(os.getenv("API_WORKERS"))

        # 日志配置
        if os.getenv("LOG_LEVEL"):
            config.logging.level = os.getenv("LOG_LEVEL")
        if os.getenv("LOG_FILE"):
            config.logging.file_path = os.getenv("LOG_FILE")

        # LLM配置
        if os.getenv("LLM_PROVIDER"):
            config.llm.provider = os.getenv("LLM_PROVIDER")
        if os.getenv("LLM_API_KEY"):
            config.llm.api_key = os.getenv("LLM_API_KEY")
        if os.getenv("LLM_BASE_URL"):
            config.llm.base_url = os.getenv("LLM_BASE_URL")
        if os.getenv("LLM_MODEL"):
            config.llm.model = os.getenv("LLM_MODEL")

    def _load_from_file(self, config: SystemConfig):
        """从文件加载配置"""
        try:
            import yaml
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not data:
                return

            # 更新配置
            if "database" in data:
                self._update_dataclass(config.database, data["database"])
            if "redis" in data:
                self._update_dataclass(config.redis, data["redis"])
            if "api" in data:
                self._update_dataclass(config.api, data["api"])
            if "logging" in data:
                self._update_dataclass(config.logging, data["logging"])
            if "llm" in data:
                self._update_dataclass(config.llm, data["llm"])

        except Exception as e:
            logger.error(f"从文件加载配置失败: {e}")

    def _update_dataclass(self, obj: Any, data: Dict[str, Any]):
        """更新数据类对象"""
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)

    def get_database_url(self) -> str:
        """获取数据库连接URL"""
        db = self.config.database
        if db.type == "sqlite":
            return f"sqlite:///{db.sqlite_path}"
        else:
            logger.warning(f"不支持的数据库类型: {db.type}，使用SQLite")
            return f"sqlite:///{db.sqlite_path}"

    def get_redis_url(self) -> str:
        """获取Redis连接URL"""
        return self.config.redis.url

    def create_directories(self):
        """创建必要的目录"""
        directories = [
            os.path.dirname(self.config.database.sqlite_path),
            os.path.dirname(self.config.logging.file_path) if self.config.logging.file_path else None,
            "data",
            "logs",
            "temp"
        ]

        for directory in directories:
            if directory:
                Path(directory).mkdir(parents=True, exist_ok=True)
                logger.debug(f"确保目录存在: {directory}")

    def validate_config(self) -> bool:
        """验证配置"""
        try:
            # 验证基本配置
            assert 1 <= self.config.api.port <= 65535, f"无效的API端口: {self.config.api.port}"
            assert self.config.logging.level.upper() in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], \
                f"无效的日志级别: {self.config.logging.level}"
            assert self.config.database.type in ["sqlite"], f"不支持的数据库类型: {self.config.database.type}"

            logger.info("配置验证通过")
            return True

        except AssertionError as e:
            logger.error(f"配置验证失败: {e}")
            return False
        except Exception as e:
            logger.error(f"配置验证出错: {e}")
            return False

# 全局设置实例
settings = Settings()