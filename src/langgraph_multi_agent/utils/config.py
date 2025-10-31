"""配置管理模块"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DatabaseConfig:
    """数据库配置"""
    redis_url: str = "redis://localhost:6379/0"
    sqlite_path: str = "checkpoints.db"
    connection_pool_size: int = 10


@dataclass
class LangGraphConfig:
    """LangGraph配置"""
    checkpoint_storage: str = "sqlite"  # "memory" or "sqlite"
    enable_tracing: bool = True
    langsmith_project: str = "langgraph-multi-agent"
    max_concurrent_tasks: int = 10


@dataclass
class APIConfig:
    """API配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list = field(default_factory=lambda: ["*"])
    enable_docs: bool = True
    api_prefix: str = "/api/v1"


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


@dataclass
class AgentConfig:
    """智能体配置"""
    max_retries: int = 3
    timeout_seconds: int = 300
    enable_monitoring: bool = True
    log_level: str = "INFO"


@dataclass
class Config:
    """主配置类"""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    langgraph: LangGraphConfig = field(default_factory=LangGraphConfig)
    api: APIConfig = field(default_factory=APIConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    
    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量创建配置"""
        config = cls()
        
        # 数据库配置
        config.database.redis_url = os.getenv("REDIS_URL", config.database.redis_url)
        config.database.sqlite_path = os.getenv("SQLITE_PATH", config.database.sqlite_path)
        
        # LangGraph配置
        config.langgraph.checkpoint_storage = os.getenv("CHECKPOINT_STORAGE", config.langgraph.checkpoint_storage)
        config.langgraph.enable_tracing = os.getenv("ENABLE_TRACING", "true").lower() == "true"
        config.langgraph.langsmith_project = os.getenv("LANGSMITH_PROJECT", config.langgraph.langsmith_project)
        
        # API配置
        config.api.host = os.getenv("API_HOST", config.api.host)
        config.api.port = int(os.getenv("API_PORT", str(config.api.port)))
        
        # 智能体配置
        config.agent.max_retries = int(os.getenv("AGENT_MAX_RETRIES", str(config.agent.max_retries)))
        config.agent.timeout_seconds = int(os.getenv("AGENT_TIMEOUT", str(config.agent.timeout_seconds)))
        config.agent.log_level = os.getenv("LOG_LEVEL", config.agent.log_level)
        
        # LLM配置
        config.llm.api_key = os.getenv("SILICONFLOW_API_KEY", config.llm.api_key)
        config.llm.base_url = os.getenv("SILICONFLOW_BASE_URL", config.llm.base_url)
        config.llm.model = os.getenv("SILICONFLOW_MODEL", config.llm.model)
        config.llm.temperature = float(os.getenv("SILICONFLOW_TEMPERATURE", str(config.llm.temperature)))
        config.llm.max_tokens = int(os.getenv("SILICONFLOW_MAX_TOKENS", str(config.llm.max_tokens)))
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "database": {
                "redis_url": self.database.redis_url,
                "sqlite_path": self.database.sqlite_path,
                "connection_pool_size": self.database.connection_pool_size
            },
            "langgraph": {
                "checkpoint_storage": self.langgraph.checkpoint_storage,
                "enable_tracing": self.langgraph.enable_tracing,
                "langsmith_project": self.langgraph.langsmith_project,
                "max_concurrent_tasks": self.langgraph.max_concurrent_tasks
            },
            "api": {
                "host": self.api.host,
                "port": self.api.port,
                "cors_origins": self.api.cors_origins,
                "enable_docs": self.api.enable_docs,
                "api_prefix": self.api.api_prefix
            },
            "agent": {
                "max_retries": self.agent.max_retries,
                "timeout_seconds": self.agent.timeout_seconds,
                "enable_monitoring": self.agent.enable_monitoring,
                "log_level": self.agent.log_level
            },
            "llm": {
                "default_provider": self.llm.default_provider,
                "api_key": self.llm.api_key,
                "base_url": self.llm.base_url,
                "model": self.llm.model,
                "temperature": self.llm.temperature,
                "max_tokens": self.llm.max_tokens,
                "timeout": self.llm.timeout,
                "max_retries": self.llm.max_retries
            }
        }


# 全局配置实例
config = Config.from_env()


def get_config() -> Dict[str, Any]:
    """获取配置字典"""
    return config.to_dict()


def get_llm_config() -> Dict[str, Any]:
    """获取LLM配置"""
    return config.to_dict()["llm"]