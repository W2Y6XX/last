"""
LangGraph多智能体系统综合功能测试包

这个包提供了完整的测试框架，用于验证LangGraph多智能体系统的所有核心功能。

主要组件:
- TestController: 测试控制器，管理整个测试流程
- TestSuite: 测试套件基类
- 各种具体的测试套件实现
- 配置管理和环境支持
- 日志和报告生成

使用示例:
    from tests.comprehensive import run_comprehensive_tests
    
    # 运行所有测试
    python -m tests.comprehensive.run_comprehensive_tests
    
    # 或者编程方式
    import asyncio
    from tests.comprehensive.core.test_controller import TestController
    
    async def main():
        controller = TestController()
        report = await controller.run_comprehensive_test()
        print(f"测试完成，成功率: {report.get_overall_success_rate():.1f}%")
    
    asyncio.run(main())
"""

__version__ = "1.0.0"
__author__ = "LangGraph Multi-Agent System Team"

# 导出主要组件
from .core.test_controller import TestController, TestSuite
from .core.test_result import TestResult, TestSuiteResult, ComprehensiveTestReport
from .core.test_status import TestStatus, TestPriority
from .config.test_config import TestConfiguration
from .config.environments import ConfigurationManager

# 导出测试套件
from .suites.health_check_suite import HealthCheckSuite
from .suites.frontend_test_suite import FrontendTestSuite
from .suites.api_test_suite import APITestSuite
from .suites.agent_test_suite import AgentTestSuite

__all__ = [
    # 核心组件
    "TestController",
    "TestSuite", 
    "TestResult",
    "TestSuiteResult",
    "ComprehensiveTestReport",
    "TestStatus",
    "TestPriority",
    
    # 配置
    "TestConfiguration",
    "ConfigurationManager",
    
    # 测试套件
    "HealthCheckSuite",
    "FrontendTestSuite", 
    "APITestSuite",
    "AgentTestSuite"
]