"""
测试配置管理模块
"""

import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class TestEnvironment(Enum):
    """测试环境枚举"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class ServiceConfig:
    """服务配置"""
    name: str
    url: str
    timeout: int = 30
    health_endpoint: str = "/health"
    enabled: bool = True


@dataclass
class TestConfiguration:
    """测试配置类"""
    # 基础配置
    environment: TestEnvironment = TestEnvironment.DEVELOPMENT
    base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    timeout: int = 30
    max_retries: int = 3
    parallel_execution: bool = True
    
    # 性能测试配置
    performance_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "max_response_time": 5.0,
        "min_success_rate": 90.0,
        "max_memory_usage": 1024,  # MB
        "max_cpu_usage": 80.0,     # %
        "max_concurrent_users": 100
    })
    
    # 测试数据配置
    test_data: Dict[str, Any] = field(default_factory=lambda: {
        "sample_task": {
            "title": "测试任务",
            "description": "这是一个用于测试的示例任务",
            "task_type": "test",
            "priority": 1,
            "requirements": ["测试需求1", "测试需求2"],
            "constraints": ["5分钟内完成", "使用测试数据"]
        },
        "sample_user": {
            "username": "test_user",
            "email": "test@example.com",
            "role": "tester"
        }
    })
    
    # 服务配置
    services: List[ServiceConfig] = field(default_factory=lambda: [
        ServiceConfig("backend", "http://localhost:8000"),
        ServiceConfig("frontend", "http://localhost:3000", health_endpoint="/"),
        ServiceConfig("database", "sqlite:///test.db", enabled=False)
    ])
    
    # 测试套件配置
    test_suites: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "health_check": {
            "enabled": True,
            "priority": 1,
            "timeout": 10,
            "critical": True
        },
        "frontend_tests": {
            "enabled": True,
            "priority": 2,
            "timeout": 60,
            "browser": "chrome",
            "headless": True
        },
        "api_tests": {
            "enabled": True,
            "priority": 3,
            "timeout": 30,
            "concurrent_requests": 10
        },
        "agent_tests": {
            "enabled": True,
            "priority": 4,
            "timeout": 120,
            "mock_llm": True
        },
        "workflow_tests": {
            "enabled": True,
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
            "load_levels": [5, 10, 20, 50]
        },
        "data_tests": {
            "enabled": True,
            "priority": 8,
            "timeout": 60
        },
        "error_recovery_tests": {
            "enabled": True,
            "priority": 9,
            "timeout": 120
        }
    })


def get_config(environment: Optional[str] = None) -> TestConfiguration:
    """获取测试配置"""
    env = environment or os.getenv("TEST_ENV", "development")
    
    config = TestConfiguration()
    config.environment = TestEnvironment(env)
    
    # 根据环境调整配置
    if config.environment == TestEnvironment.STAGING:
        config.base_url = "http://staging.example.com:8000"
        config.frontend_url = "http://staging.example.com:3000"
        config.timeout = 60
    elif config.environment == TestEnvironment.PRODUCTION:
        config.base_url = "https://api.example.com"
        config.frontend_url = "https://app.example.com"
        config.timeout = 120
        config.parallel_execution = False  # 生产环境谨慎并行
    
    return config


def get_service_config(service_name: str, config: Optional[TestConfiguration] = None) -> Optional[ServiceConfig]:
    """获取特定服务配置"""
    if config is None:
        config = get_config()
    
    for service in config.services:
        if service.name == service_name:
            return service
    return None


def is_suite_enabled(suite_name: str, config: Optional[TestConfiguration] = None) -> bool:
    """检查测试套件是否启用"""
    if config is None:
        config = get_config()
    
    suite_config = config.test_suites.get(suite_name, {})
    return suite_config.get("enabled", False)


def get_suite_config(suite_name: str, config: Optional[TestConfiguration] = None) -> Dict[str, Any]:
    """获取测试套件配置"""
    if config is None:
        config = get_config()
    
    return config.test_suites.get(suite_name, {})