#!/usr/bin/env python3
"""
综合系统功能测试主执行脚本
"""

import asyncio
import argparse
import sys
import os
from pathlib import Path
from typing import List, Optional

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.comprehensive.core.test_controller import TestController
from tests.comprehensive.config.environments import ConfigurationManager
from tests.comprehensive.suites.health_check_suite import HealthCheckSuite
from tests.comprehensive.suites.frontend_test_suite import FrontendTestSuite
from tests.comprehensive.suites.api_test_suite import APITestSuite
from tests.comprehensive.suites.agent_test_suite import AgentTestSuite
from tests.comprehensive.utils.logging_utils import setup_logging, LogLevel


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="LangGraph多智能体系统综合功能测试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python run_comprehensive_tests.py                    # 运行所有测试
  python run_comprehensive_tests.py --env staging     # 在预发布环境运行
  python run_comprehensive_tests.py --suites health_check api_tests  # 只运行指定套件
  python run_comprehensive_tests.py --exclude frontend_tests         # 排除前端测试
  python run_comprehensive_tests.py --config custom.json             # 使用自定义配置
        """
    )
    
    parser.add_argument(
        "--env", "--environment",
        choices=["development", "staging", "production"],
        default="development",
        help="测试环境 (默认: development)"
    )
    
    parser.add_argument(
        "--suites",
        nargs="+",
        choices=["health_check", "frontend_tests", "api_tests", "agent_tests"],
        help="指定要运行的测试套件"
    )
    
    parser.add_argument(
        "--exclude",
        nargs="+",
        choices=["health_check", "frontend_tests", "api_tests", "agent_tests"],
        help="排除的测试套件"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="自定义配置文件路径"
    )
    
    parser.add_argument(
        "--base-url",
        type=str,
        help="后端服务基础URL (覆盖配置文件)"
    )
    
    parser.add_argument(
        "--frontend-url",
        type=str,
        help="前端服务URL (覆盖配置文件)"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        help="测试超时时间(秒) (覆盖配置文件)"
    )
    
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="启用并行执行"
    )
    
    parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="禁用并行执行"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细输出"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="静默模式"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="测试报告输出文件路径"
    )
    
    parser.add_argument(
        "--format",
        choices=["json", "html", "text"],
        default="json",
        help="报告格式 (默认: json)"
    )
    
    return parser.parse_args()


def setup_environment():
    """设置测试环境"""
    # 设置环境变量
    os.environ.setdefault("PYTHONPATH", str(project_root))
    
    # 创建必要的目录
    logs_dir = Path("tests/comprehensive/logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    reports_dir = Path("tests/comprehensive/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)


def validate_environment(config):
    """验证测试环境"""
    print("🔍 验证测试环境...")
    
    # 验证配置
    errors = ConfigurationManager.validate_config(config)
    if errors:
        print("❌ 配置验证失败:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    print("✅ 配置验证通过")
    
    # 检查网络连接
    try:
        import requests
        response = requests.get(config.base_url, timeout=10)
        if response.status_code < 500:
            print(f"✅ 后端服务可访问: {config.base_url}")
        else:
            print(f"⚠️ 后端服务响应异常: {response.status_code}")
    except Exception as e:
        print(f"⚠️ 后端服务连接失败: {e}")
    
    try:
        response = requests.get(config.frontend_url, timeout=10)
        if response.status_code < 500:
            print(f"✅ 前端服务可访问: {config.frontend_url}")
        else:
            print(f"⚠️ 前端服务响应异常: {response.status_code}")
    except Exception as e:
        print(f"⚠️ 前端服务连接失败: {e}")
    
    return True


async def run_tests(args):
    """运行测试"""
    # 设置环境
    setup_environment()
    
    # 设置日志
    log_level = LogLevel.DEBUG if args.verbose else LogLevel.WARNING if args.quiet else LogLevel.INFO
    logger = setup_logging(level=log_level)
    
    # 加载配置
    if args.config:
        from tests.comprehensive.config.environments import load_config_from_file
        config = load_config_from_file(args.config)
    else:
        config = ConfigurationManager.get_config(args.env)
    
    # 应用命令行参数覆盖
    if args.base_url:
        config.base_url = args.base_url
    if args.frontend_url:
        config.frontend_url = args.frontend_url
    if args.timeout:
        config.timeout = args.timeout
    if args.parallel:
        config.parallel_execution = True
    if args.no_parallel:
        config.parallel_execution = False
    
    # 验证环境
    if not validate_environment(config):
        print("❌ 环境验证失败，退出测试")
        return 1
    
    # 创建测试控制器
    controller = TestController(config)
    
    # 注册测试套件
    available_suites = {
        "health_check": HealthCheckSuite,
        "frontend_tests": FrontendTestSuite,
        "api_tests": APITestSuite,
        "agent_tests": AgentTestSuite
    }
    
    # 确定要运行的测试套件
    if args.suites:
        suites_to_run = args.suites
    else:
        suites_to_run = list(available_suites.keys())
    
    if args.exclude:
        suites_to_run = [s for s in suites_to_run if s not in args.exclude]
    
    # 注册选定的测试套件
    for suite_name in suites_to_run:
        if suite_name in available_suites:
            controller.register_test_suite(available_suites[suite_name], suite_name)
        else:
            print(f"⚠️ 未知的测试套件: {suite_name}")
    
    if not controller.get_available_suites():
        print("❌ 没有可用的测试套件")
        return 1
    
    print(f"🚀 开始运行测试套件: {', '.join(controller.get_available_suites())}")
    
    # 执行测试
    try:
        report = await controller.run_comprehensive_test()
        
        # 保存报告
        if args.output:
            report_path = controller.save_report(args.output)
        else:
            report_path = controller.save_report()
        
        print(f"\n📄 测试报告已保存: {report_path}")
        
        # 返回退出码
        if report.total_failed > 0:
            return 1  # 有失败测试
        else:
            return 0  # 所有测试通过
    
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
        return 130
    except Exception as e:
        print(f"\n❌ 测试执行失败: {e}")
        return 1


def main():
    """主函数"""
    args = parse_arguments()
    
    print("🧪 LangGraph多智能体系统 - 综合功能测试")
    print("=" * 60)
    
    try:
        exit_code = asyncio.run(run_tests(args))
        sys.exit(exit_code)
    except Exception as e:
        print(f"❌ 程序执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()