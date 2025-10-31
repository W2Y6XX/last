"""统一配置管理器"""

import os
import json
import yaml
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """数据库配置"""
    type: str = "sqlite"
    host: str = "localhost"
    port: int = 5432
    database: str = "langgraph_multi_agent"
    username: str = ""
    password: str = ""
    sqlite_path: str = "data/database.db"
    # SQLite优化配置
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False
    connect_args: dict = None

    def __post_init__(self):
        if self.connect_args is None:
            self.connect_args = {
                "check_same_thread": False,
                "timeout": 20,
                "isolation_level": None
            }


@dataclass
class CheckpointConfig:
    """检查点配置"""
    storage_type: str = "memory"  # memory, sqlite
    sqlite_db_path: str = "data/checkpoints.db"
    auto_checkpoint_interval: int = 300  # 5分钟
    max_checkpoints_per_thread: int = 50
    cleanup_interval_hours: int = 24


@dataclass
class ErrorHandlingConfig:
    """错误处理配置"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    enable_circuit_breaker: bool = True
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60
    webhook_url: Optional[str] = None


@dataclass
class MonitoringConfig:
    """监控配置"""
    enable_metrics: bool = True
    enable_tracing: bool = True
    metrics_interval: int = 60
    enable_langsmith: bool = False
    langsmith_api_key: Optional[str] = None
    langsmith_project: Optional[str] = None


@dataclass
class APIConfig:
    """API配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    workers: int = 1
    enable_auth: bool = False
    auth_secret_key: str = "default-secret-key"
    enable_rate_limit: bool = True
    rate_limit_rpm: int = 100
    cors_origins: list = None
    trusted_hosts: list = None
    
    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["*"]
        if self.trusted_hosts is None:
            self.trusted_hosts = []


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    enable_console: bool = True


@dataclass
class AgentConfig:
    """智能体配置"""
    timeout_seconds: int = 60
    max_retries: int = 3
    enable_caching: bool = True
    cache_ttl: int = 3600
    default_capabilities: list = None
    
    def __post_init__(self):
        if self.default_capabilities is None:
            self.default_capabilities = []


@dataclass
class LLMConfig:
    """LLM配置"""
    default_provider: str = "siliconflow"
    api_key: str = "sk-wmxxamqdqsmscgrrmweqsqcieowsmqpxqwvenlelrxtkvmms"
    base_url: str = "https://api.siliconflow.cn/v1"
    model: str = "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B"
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: int = 60
    max_retries: int = 3
    max_concurrent_requests: int = 5


@dataclass
class WorkflowConfig:
    """工作流配置"""
    default_execution_mode: str = "adaptive"
    max_iterations: int = 100
    default_timeout_seconds: int = 3600
    enable_parallel_execution: bool = True
    max_parallel_agents: int = 10
    enable_checkpointing: bool = True


@dataclass
class SystemConfig:
    """系统总配置"""
    environment: str = "development"
    debug: bool = False
    version: str = "1.0.0"
    
    # 子配置
    database: DatabaseConfig = None
    checkpoint: CheckpointConfig = None
    error_handling: ErrorHandlingConfig = None
    monitoring: MonitoringConfig = None
    api: APIConfig = None
    logging: LoggingConfig = None
    agent: AgentConfig = None
    workflow: WorkflowConfig = None
    llm: LLMConfig = None
    
    # 自定义配置
    custom: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.database is None:
            self.database = DatabaseConfig()
        if self.checkpoint is None:
            self.checkpoint = CheckpointConfig()
        if self.error_handling is None:
            self.error_handling = ErrorHandlingConfig()
        if self.monitoring is None:
            self.monitoring = MonitoringConfig()
        if self.api is None:
            self.api = APIConfig()
        if self.logging is None:
            self.logging = LoggingConfig()
        if self.agent is None:
            self.agent = AgentConfig()
        if self.workflow is None:
            self.workflow = WorkflowConfig()
        if self.llm is None:
            self.llm = LLMConfig()
        if self.custom is None:
            self.custom = {}
        if self.agent is None:
            self.agent = AgentConfig()
        if self.workflow is None:
            self.workflow = WorkflowConfig()
        if self.custom is None:
            self.custom = {}


class ConfigManager:
    """统一配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.config: SystemConfig = SystemConfig()
        self._config_loaded = False
        self._config_file_path: Optional[Path] = None
        
        # 加载配置
        self.load_config()
    
    def load_config(self) -> SystemConfig:
        """加载配置"""
        try:
            # 1. 加载默认配置
            self.config = SystemConfig()
            
            # 2. 从配置文件加载
            if self.config_path:
                self._load_from_file(self.config_path)
            else:
                # 尝试从默认位置加载
                self._load_from_default_locations()
            
            # 3. 从环境变量覆盖
            self._load_from_environment()
            
            # 4. 验证配置
            self._validate_config()
            
            self._config_loaded = True
            logger.info("配置加载完成")
            
            return self.config
            
        except Exception as e:
            logger.error(f"配置加载失败: {e}")
            # 使用默认配置
            self.config = SystemConfig()
            return self.config
    
    def _load_from_file(self, file_path: str):
        """从文件加载配置"""
        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"配置文件不存在: {file_path}")
                return
            
            self._config_file_path = path
            
            with open(path, 'r', encoding='utf-8') as f:
                if path.suffix.lower() in ['.yml', '.yaml']:
                    data = yaml.safe_load(f)
                elif path.suffix.lower() == '.json':
                    data = json.load(f)
                else:
                    logger.warning(f"不支持的配置文件格式: {path.suffix}")
                    return
            
            # 更新配置
            self._update_config_from_dict(data)
            logger.info(f"从文件加载配置: {file_path}")
            
        except Exception as e:
            logger.error(f"从文件加载配置失败: {e}")
    
    def _load_from_default_locations(self):
        """从默认位置加载配置"""
        default_paths = [
            "config.yml",
            "config.yaml", 
            "config.json",
            "configs/config.yml",
            "configs/config.yaml",
            "configs/config.json",
            os.path.expanduser("~/.langgraph_multi_agent/config.yml"),
            "/etc/langgraph_multi_agent/config.yml"
        ]
        
        for path in default_paths:
            if os.path.exists(path):
                self._load_from_file(path)
                break
    
    def _load_from_environment(self):
        """从环境变量加载配置"""
        try:
            # 系统配置
            if os.getenv("ENVIRONMENT"):
                self.config.environment = os.getenv("ENVIRONMENT")
            if os.getenv("DEBUG"):
                self.config.debug = os.getenv("DEBUG").lower() == "true"
            
            # API配置
            if os.getenv("API_HOST"):
                self.config.api.host = os.getenv("API_HOST")
            if os.getenv("API_PORT"):
                self.config.api.port = int(os.getenv("API_PORT"))
            if os.getenv("API_WORKERS"):
                self.config.api.workers = int(os.getenv("API_WORKERS"))
            if os.getenv("AUTH_SECRET_KEY"):
                self.config.api.auth_secret_key = os.getenv("AUTH_SECRET_KEY")
            
            # 数据库配置
            if os.getenv("DB_TYPE"):
                self.config.database.type = os.getenv("DB_TYPE")
            if os.getenv("DB_HOST"):
                self.config.database.host = os.getenv("DB_HOST")
            if os.getenv("DB_PORT"):
                self.config.database.port = int(os.getenv("DB_PORT"))
            if os.getenv("DB_NAME"):
                self.config.database.database = os.getenv("DB_NAME")
            if os.getenv("DB_USER"):
                self.config.database.username = os.getenv("DB_USER")
            if os.getenv("DB_PASSWORD"):
                self.config.database.password = os.getenv("DB_PASSWORD")
            
            # 检查点配置
            if os.getenv("CHECKPOINT_STORAGE"):
                self.config.checkpoint.storage_type = os.getenv("CHECKPOINT_STORAGE")
            if os.getenv("CHECKPOINT_DB_PATH"):
                self.config.checkpoint.sqlite_db_path = os.getenv("CHECKPOINT_DB_PATH")
            
            # 监控配置
            if os.getenv("LANGSMITH_API_KEY"):
                self.config.monitoring.langsmith_api_key = os.getenv("LANGSMITH_API_KEY")
                self.config.monitoring.enable_langsmith = True
            if os.getenv("LANGSMITH_PROJECT"):
                self.config.monitoring.langsmith_project = os.getenv("LANGSMITH_PROJECT")
            
            # 错误处理配置
            if os.getenv("ERROR_WEBHOOK_URL"):
                self.config.error_handling.webhook_url = os.getenv("ERROR_WEBHOOK_URL")
            
            # 日志配置
            if os.getenv("LOG_LEVEL"):
                self.config.logging.level = os.getenv("LOG_LEVEL")
            if os.getenv("LOG_FILE"):
                self.config.logging.file_path = os.getenv("LOG_FILE")
            
            logger.debug("从环境变量加载配置完成")
            
        except Exception as e:
            logger.error(f"从环境变量加载配置失败: {e}")
    
    def _update_config_from_dict(self, data: Dict[str, Any]):
        """从字典更新配置"""
        try:
            # 系统配置
            if "environment" in data:
                self.config.environment = data["environment"]
            if "debug" in data:
                self.config.debug = data["debug"]
            if "version" in data:
                self.config.version = data["version"]
            
            # 数据库配置
            if "database" in data:
                db_data = data["database"]
                for key, value in db_data.items():
                    if hasattr(self.config.database, key):
                        setattr(self.config.database, key, value)
            
            # 检查点配置
            if "checkpoint" in data:
                cp_data = data["checkpoint"]
                for key, value in cp_data.items():
                    if hasattr(self.config.checkpoint, key):
                        setattr(self.config.checkpoint, key, value)
            
            # 错误处理配置
            if "error_handling" in data:
                eh_data = data["error_handling"]
                for key, value in eh_data.items():
                    if hasattr(self.config.error_handling, key):
                        setattr(self.config.error_handling, key, value)
            
            # 监控配置
            if "monitoring" in data:
                mon_data = data["monitoring"]
                for key, value in mon_data.items():
                    if hasattr(self.config.monitoring, key):
                        setattr(self.config.monitoring, key, value)
            
            # API配置
            if "api" in data:
                api_data = data["api"]
                for key, value in api_data.items():
                    if hasattr(self.config.api, key):
                        setattr(self.config.api, key, value)
            
            # 日志配置
            if "logging" in data:
                log_data = data["logging"]
                for key, value in log_data.items():
                    if hasattr(self.config.logging, key):
                        setattr(self.config.logging, key, value)
            
            # 智能体配置
            if "agent" in data:
                agent_data = data["agent"]
                for key, value in agent_data.items():
                    if hasattr(self.config.agent, key):
                        setattr(self.config.agent, key, value)
            
            # 工作流配置
            if "workflow" in data:
                wf_data = data["workflow"]
                for key, value in wf_data.items():
                    if hasattr(self.config.workflow, key):
                        setattr(self.config.workflow, key, value)
            
            # 自定义配置
            if "custom" in data:
                self.config.custom.update(data["custom"])
            
        except Exception as e:
            logger.error(f"从字典更新配置失败: {e}")
    
    def _validate_config(self):
        """验证配置"""
        try:
            # 验证API端口
            if not (1 <= self.config.api.port <= 65535):
                raise ValueError(f"无效的API端口: {self.config.api.port}")
            
            # 验证日志级别
            valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if self.config.logging.level.upper() not in valid_log_levels:
                raise ValueError(f"无效的日志级别: {self.config.logging.level}")
            
            # 验证存储类型
            valid_storage_types = ["memory", "sqlite"]
            if self.config.checkpoint.storage_type not in valid_storage_types:
                raise ValueError(f"无效的存储类型: {self.config.checkpoint.storage_type}")
            
            # 验证执行模式
            valid_execution_modes = ["sequential", "parallel", "adaptive"]
            if self.config.workflow.default_execution_mode not in valid_execution_modes:
                raise ValueError(f"无效的执行模式: {self.config.workflow.default_execution_mode}")
            
            logger.debug("配置验证通过")
            
        except Exception as e:
            logger.error(f"配置验证失败: {e}")
            raise
    
    def save_config(self, file_path: Optional[str] = None) -> bool:
        """保存配置到文件"""
        try:
            target_path = file_path or self._config_file_path or "config.yml"
            path = Path(target_path)
            
            # 确保目录存在
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # 转换为字典
            config_dict = asdict(self.config)
            
            # 保存文件
            with open(path, 'w', encoding='utf-8') as f:
                if path.suffix.lower() in ['.yml', '.yaml']:
                    yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
                elif path.suffix.lower() == '.json':
                    json.dump(config_dict, f, indent=2, ensure_ascii=False)
                else:
                    # 默认使用YAML格式
                    yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"配置已保存到: {path}")
            return True
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def get_config(self) -> SystemConfig:
        """获取配置"""
        if not self._config_loaded:
            self.load_config()
        return self.config
    
    def get_database_url(self) -> str:
        """获取数据库连接URL"""
        db = self.config.database
        if db.type == "sqlite":
            return f"sqlite:///{db.sqlite_path}"
        elif db.type == "postgresql":
            # PostgreSQL支持已移除，回退到SQLite
            logger.warning("PostgreSQL支持已移除，回退到SQLite")
            return f"sqlite:///{db.sqlite_path}"
        elif db.type == "mysql":
            # MySQL支持已移除，回退到SQLite
            logger.warning("MySQL支持已移除，回退到SQLite")
            return f"sqlite:///{db.sqlite_path}"
        else:
            logger.warning(f"不支持的数据库类型: {db.type}，使用SQLite")
            return f"sqlite:///{db.sqlite_path}"
    
    def update_config(self, updates: Dict[str, Any]) -> bool:
        """更新配置"""
        try:
            self._update_config_from_dict(updates)
            self._validate_config()
            logger.info("配置更新成功")
            return True
        except Exception as e:
            logger.error(f"配置更新失败: {e}")
            return False
    
    def reset_to_defaults(self):
        """重置为默认配置"""
        self.config = SystemConfig()
        self._config_loaded = True
        logger.info("配置已重置为默认值")
    
    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要"""
        return {
            "environment": self.config.environment,
            "debug": self.config.debug,
            "version": self.config.version,
            "api_host": self.config.api.host,
            "api_port": self.config.api.port,
            "database_type": self.config.database.type,
            "checkpoint_storage": self.config.checkpoint.storage_type,
            "monitoring_enabled": self.config.monitoring.enable_metrics,
            "auth_enabled": self.config.api.enable_auth,
            "config_file": str(self._config_file_path) if self._config_file_path else None,
            "loaded_at": datetime.now().isoformat()
        }