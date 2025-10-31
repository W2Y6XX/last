"""
环境配置管理
"""

import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from .test_config import TestConfiguration, TestEnvironment, ServiceConfig


@dataclass
class DevelopmentConfig(TestConfiguration):
    """开发环境配置"""
    environment: TestEnvironment = TestEnvironment.DEVELOPMENT
    base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    timeout: int = 30
    max_retries: int = 3
    parallel_execution: bool = True
    
    # 开发环境特定配置
    debug_mode: bool = True
    verbose_logging: bool = True
    mock_external_services: bool = True
    
    # 性能阈值相对宽松
    performance_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "max_response_time": 10.0,  # 开发环境允许更长响应时间
        "min_success_rate": 80.0,   # 开发环境允许更低成功率
        "max_memory_usage": 2048,   # 2GB
        "max_cpu_usage": 90.0,
        "max_concurrent_users": 50
    })
    
    # 开发环境服务配置
    services: list = field(default_factory=lambda: [
        ServiceConfig("backend", "http://localhost:8000", timeout=30),
        ServiceConfig("frontend", "http://localhost:3000", timeout=10, health_endpoint="/"),
        ServiceConfig("database", "sqlite:///test_dev.db", enabled=True)
    ])


@dataclass
class StagingConfig(TestConfiguration):
    """预发布环境配置"""
    environment: TestEnvironment = TestEnvironment.STAGING
    base_url: str = "http://staging-api.example.com:8000"
    frontend_url: str = "http://staging.example.com:3000"
    timeout: int = 60
    max_retries: int = 5
    parallel_execution: bool = True
    
    # 预发布环境特定配置
    debug_mode: bool = False
    verbose_logging: bool = True
    mock_external_services: bool = False
    
    # 性能阈值适中
    performance_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "max_response_time": 5.0,
        "min_success_rate": 90.0,
        "max_memory_usage": 1024,
        "max_cpu_usage": 80.0,
        "max_concurrent_users": 100
    })
    
    # 预发布环境服务配置
    services: list = field(default_factory=lambda: [
        ServiceConfig("backend", "http://staging-api.example.com:8000", timeout=60),
        ServiceConfig("frontend", "http://staging.example.com:3000", timeout=30, health_endpoint="/"),
        ServiceConfig("database", "postgresql://staging_db", enabled=True),
        ServiceConfig("redis", "redis://staging-redis:6379", enabled=True)
    ])


@dataclass
class ProductionConfig(TestConfiguration):
    """生产环境配置"""
    environment: TestEnvironment = TestEnvironment.PRODUCTION
    base_url: str = "https://api.example.com"
    frontend_url: str = "https://app.example.com"
    timeout: int = 120
    max_retries: int = 3
    parallel_execution: bool = False  # 生产环境谨慎并行
    
    # 生产环境特定配置
    debug_mode: bool = False
    verbose_logging: bool = False
    mock_external_services: bool = False
    
    # 性能阈值严格
    performance_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "max_response_time": 2.0,   # 生产环境要求更快响应
        "min_success_rate": 95.0,   # 生产环境要求更高成功率
        "max_memory_usage": 512,    # 512MB
        "max_cpu_usage": 70.0,
        "max_concurrent_users": 200
    })
    
    # 生产环境服务配置
    services: list = field(default_factory=lambda: [
        ServiceConfig("backend", "https://api.example.com", timeout=120),
        ServiceConfig("frontend", "https://app.example.com", timeout=60, health_endpoint="/"),
        ServiceConfig("database", "postgresql://prod_db", enabled=True),
        ServiceConfig("redis", "redis://prod-redis:6379", enabled=True),
        ServiceConfig("monitoring", "https://monitoring.example.com", enabled=True)
    ])
    
    # 生产环境测试套件配置 - 更保守
    test_suites: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "health_check": {
            "enabled": True,
            "priority": 1,
            "timeout": 30,
            "critical": True
        },
        "frontend_tests": {
            "enabled": False,  # 生产环境可能不运行前端测试
            "priority": 2,
            "timeout": 60
        },
        "api_tests": {
            "enabled": True,
            "priority": 3,
            "timeout": 60,
            "concurrent_requests": 5  # 减少并发请求
        },
        "agent_tests": {
            "enabled": False,  # 生产环境可能不运行智能体测试
            "priority": 4,
            "timeout": 120
        },
        "workflow_tests": {
            "enabled": False,
            "priority": 5,
            "timeout": 180
        },
        "integration_tests": {
            "enabled": True,
            "priority": 6,
            "timeout": 300
        },
        "performance_tests": {
            "enabled": True,
            "priority": 7,
            "timeout": 600,
            "load_levels": [5, 10]  # 减少负载测试级别
        },
        "data_tests": {
            "enabled": True,
            "priority": 8,
            "timeout": 60
        },
        "error_recovery_tests": {
            "enabled": False,  # 生产环境可能不运行错误恢复测试
            "priority": 9,
            "timeout": 120
        }
    })


class ConfigurationManager:
    """配置管理器"""
    
    _configs = {
        "development": DevelopmentConfig,
        "staging": StagingConfig,
        "production": ProductionConfig
    }
    
    @classmethod
    def get_config(cls, environment: Optional[str] = None) -> TestConfiguration:
        """获取指定环境的配置"""
        env = environment or os.getenv("TEST_ENV", "development")
        
        if env not in cls._configs:
            raise ValueError(f"Unknown environment: {env}. Available: {list(cls._configs.keys())}")
        
        config_class = cls._configs[env]
        config = config_class()
        
        # 从环境变量覆盖配置
        cls._override_from_env(config)
        
        return config
    
    @classmethod
    def _override_from_env(cls, config: TestConfiguration):
        """从环境变量覆盖配置"""
        # 基础URL覆盖
        if os.getenv("TEST_BASE_URL"):
            config.base_url = os.getenv("TEST_BASE_URL")
        
        if os.getenv("TEST_FRONTEND_URL"):
            config.frontend_url = os.getenv("TEST_FRONTEND_URL")
        
        # 超时配置覆盖
        if os.getenv("TEST_TIMEOUT"):
            try:
                config.timeout = int(os.getenv("TEST_TIMEOUT"))
            except ValueError:
                pass
        
        # 并行执行覆盖
        if os.getenv("TEST_PARALLEL"):
            config.parallel_execution = os.getenv("TEST_PARALLEL").lower() in ["true", "1", "yes"]
        
        # 调试模式覆盖
        if os.getenv("TEST_DEBUG"):
            if hasattr(config, 'debug_mode'):
                config.debug_mode = os.getenv("TEST_DEBUG").lower() in ["true", "1", "yes"]
    
    @classmethod
    def validate_config(cls, config: TestConfiguration) -> List[str]:
        """验证配置"""
        errors = []
        
        # 验证URL格式
        from ..utils.helpers import validate_url
        
        if not validate_url(config.base_url):
            errors.append(f"Invalid base_url: {config.base_url}")
        
        if not validate_url(config.frontend_url):
            errors.append(f"Invalid frontend_url: {config.frontend_url}")
        
        # 验证超时配置
        if config.timeout <= 0:
            errors.append("Timeout must be positive")
        
        if config.max_retries < 0:
            errors.append("Max retries cannot be negative")
        
        # 验证性能阈值
        thresholds = config.performance_thresholds
        
        if thresholds.get("max_response_time", 0) <= 0:
            errors.append("max_response_time must be positive")
        
        if not (0 <= thresholds.get("min_success_rate", 0) <= 100):
            errors.append("min_success_rate must be between 0 and 100")
        
        if thresholds.get("max_memory_usage", 0) <= 0:
            errors.append("max_memory_usage must be positive")
        
        # 验证服务配置
        for service in config.services:
            if not service.name:
                errors.append("Service name cannot be empty")
            
            # 跳过数据库URL验证（可能是sqlite://等格式）
            if service.enabled and service.name not in ["database"] and not validate_url(service.url):
                errors.append(f"Invalid service URL for {service.name}: {service.url}")
            
            if service.timeout <= 0:
                errors.append(f"Service timeout must be positive for {service.name}")
        
        return errors
    
    @classmethod
    def get_available_environments(cls) -> List[str]:
        """获取可用环境列表"""
        return list(cls._configs.keys())
    
    @classmethod
    def register_config(cls, environment: str, config_class: type):
        """注册新的环境配置"""
        cls._configs[environment] = config_class


def load_config_from_file(file_path: str) -> TestConfiguration:
    """从文件加载配置"""
    import json
    from pathlib import Path
    
    config_file = Path(file_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
    
    # 创建基础配置
    env = config_data.get("environment", "development")
    config = ConfigurationManager.get_config(env)
    
    # 更新配置
    for key, value in config_data.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    return config


def save_config_to_file(config: TestConfiguration, file_path: str):
    """保存配置到文件"""
    import json
    from pathlib import Path
    
    config_file = Path(file_path)
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 转换配置为字典
    config_dict = {
        "environment": config.environment.value,
        "base_url": config.base_url,
        "frontend_url": config.frontend_url,
        "timeout": config.timeout,
        "max_retries": config.max_retries,
        "parallel_execution": config.parallel_execution,
        "performance_thresholds": config.performance_thresholds,
        "test_suites": config.test_suites
    }
    
    # 添加环境特定配置
    if hasattr(config, 'debug_mode'):
        config_dict["debug_mode"] = config.debug_mode
    if hasattr(config, 'verbose_logging'):
        config_dict["verbose_logging"] = config.verbose_logging
    if hasattr(config, 'mock_external_services'):
        config_dict["mock_external_services"] = config.mock_external_services
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config_dict, f, indent=2, ensure_ascii=False)