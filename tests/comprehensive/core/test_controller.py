"""
测试控制器 - 协调和管理整个测试流程
"""

import asyncio
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Type
from pathlib import Path

from ..config.test_config import TestConfiguration, get_config
from ..utils.logging_utils import get_logger, TestLogger
from ..utils.helpers import generate_test_id, format_duration
from .test_status import TestStatus, TestPriority, TestProgress
from .test_result import TestResult, TestSuiteResult, ComprehensiveTestReport, ResultType


class TestSuite:
    """测试套件基类"""
    
    def __init__(self, name: str, config: TestConfiguration):
        self.name = name
        self.config = config
        self.logger = get_logger(f"suite_{name}")
        self.results: List[TestResult] = []
    
    async def run_all_tests(self) -> TestSuiteResult:
        """运行所有测试 - 子类需要实现"""
        raise NotImplementedError("Subclasses must implement run_all_tests")
    
    def create_test_result(self, test_name: str, test_id: Optional[str] = None) -> TestResult:
        """创建测试结果对象"""
        return TestResult(
            test_id=test_id or generate_test_id(),
            test_name=test_name,
            test_suite=self.name,
            status=TestStatus.PENDING,
            result_type=ResultType.FUNCTIONAL,
            environment=self.config.environment.value
        )


class TestController:
    """测试控制器 - 管理整个测试流程"""
    
    def __init__(self, config: Optional[TestConfiguration] = None):
        self.config = config or get_config()
        self.logger = get_logger("test_controller")
        self.progress = TestProgress()
        self.test_suites: Dict[str, TestSuite] = {}
        self.session_id = str(uuid.uuid4())
        
        # 测试报告
        self.report = ComprehensiveTestReport(
            report_id=generate_test_id(),
            test_session_id=self.session_id,
            environment=self.config.environment.value,
            start_time=datetime.now()
        )
    
    def register_test_suite(self, suite_class: Type[TestSuite], name: Optional[str] = None):
        """注册测试套件"""
        suite_name = name or suite_class.__name__.lower().replace("testsuite", "")
        
        if not self.is_suite_enabled(suite_name):
            self.logger.info(f"测试套件 {suite_name} 已禁用，跳过注册")
            return
        
        try:
            suite_instance = suite_class(suite_name, self.config)
            self.test_suites[suite_name] = suite_instance
            self.logger.info(f"已注册测试套件: {suite_name}")
        except Exception as e:
            self.logger.error(f"注册测试套件 {suite_name} 失败: {e}")
    
    def is_suite_enabled(self, suite_name: str) -> bool:
        """检查测试套件是否启用"""
        suite_config = self.config.test_suites.get(suite_name, {})
        return suite_config.get("enabled", False)
    
    def get_suite_priority(self, suite_name: str) -> int:
        """获取测试套件优先级"""
        suite_config = self.config.test_suites.get(suite_name, {})
        return suite_config.get("priority", 999)
    
    def is_suite_critical(self, suite_name: str) -> bool:
        """检查测试套件是否关键"""
        suite_config = self.config.test_suites.get(suite_name, {})
        return suite_config.get("critical", False)
    
    async def run_comprehensive_test(self) -> ComprehensiveTestReport:
        """执行综合测试"""
        self.logger.info("🧪 开始综合系统功能测试")
        self.logger.info(f"测试会话ID: {self.session_id}")
        self.logger.info(f"测试环境: {self.config.environment.value}")
        
        start_time = time.time()
        
        try:
            # 按优先级排序测试套件
            sorted_suites = sorted(
                self.test_suites.items(),
                key=lambda x: self.get_suite_priority(x[0])
            )
            
            # 执行测试套件
            for suite_name, suite_instance in sorted_suites:
                await self._run_test_suite(suite_name, suite_instance)
                
                # 检查关键测试失败
                if self._should_stop_on_critical_failure(suite_name):
                    self.logger.warning("检测到关键测试失败，停止后续测试")
                    break
            
            # 完成测试报告
            self.report.finalize()
            
            # 记录测试摘要
            self._log_test_summary()
            
            return self.report
            
        except Exception as e:
            self.logger.error(f"测试执行过程中发生错误: {e}")
            self.report.finalize()
            raise
        finally:
            total_duration = time.time() - start_time
            self.logger.info(f"测试总耗时: {format_duration(total_duration)}")
    
    async def _run_test_suite(self, suite_name: str, suite_instance: TestSuite):
        """运行单个测试套件"""
        self.logger.info(f"🔍 执行测试套件: {suite_name}")
        
        suite_start_time = time.time()
        suite_result = TestSuiteResult(
            suite_name=suite_name,
            start_time=datetime.now()
        )
        
        try:
            # 获取套件配置
            suite_config = self.config.test_suites.get(suite_name, {})
            timeout = suite_config.get("timeout", self.config.timeout)
            
            # 执行测试套件
            if timeout > 0:
                suite_result = await asyncio.wait_for(
                    suite_instance.run_all_tests(),
                    timeout=timeout
                )
            else:
                suite_result = await suite_instance.run_all_tests()
            
            suite_result.end_time = datetime.now()
            suite_result.calculate_duration()
            
            # 记录结果
            self.report.add_suite_result(suite_result)
            
            # 日志记录
            success_rate = suite_result.get_success_rate()
            status_emoji = "✅" if success_rate >= 90 else "⚠️" if success_rate >= 70 else "❌"
            
            self.logger.info(
                f"{status_emoji} 套件 {suite_name} 完成: "
                f"{suite_result.passed_tests}/{suite_result.total_tests} 通过 "
                f"({success_rate:.1f}%) "
                f"耗时: {format_duration(suite_result.duration)}"
            )
            
        except asyncio.TimeoutError:
            self.logger.error(f"测试套件 {suite_name} 执行超时")
            suite_result.end_time = datetime.now()
            suite_result.calculate_duration()
            self.report.add_suite_result(suite_result)
            
        except Exception as e:
            self.logger.error(f"测试套件 {suite_name} 执行失败: {e}")
            suite_result.end_time = datetime.now()
            suite_result.calculate_duration()
            self.report.add_suite_result(suite_result)
    
    def _should_stop_on_critical_failure(self, suite_name: str) -> bool:
        """是否应该因关键失败而停止"""
        if not self.is_suite_critical(suite_name):
            return False
        
        # 检查当前套件的失败率
        suite_result = None
        for result in self.report.suite_results:
            if result.suite_name == suite_name:
                suite_result = result
                break
        
        if suite_result and suite_result.total_tests > 0:
            failure_rate = (suite_result.failed_tests / suite_result.total_tests) * 100
            return failure_rate > 50  # 失败率超过50%则停止
        
        return False
    
    def _log_test_summary(self):
        """记录测试摘要"""
        self.logger.info("=" * 70)
        self.logger.info("📊 综合测试执行摘要")
        self.logger.info("=" * 70)
        
        # 总体统计
        self.logger.info(f"测试会话: {self.session_id}")
        self.logger.info(f"测试环境: {self.report.environment}")
        self.logger.info(f"执行时间: {self.report.start_time.strftime('%Y-%m-%d %H:%M:%S')} - {self.report.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.report.end_time else 'N/A'}")
        self.logger.info(f"总耗时: {format_duration(self.report.total_duration)}")
        
        self.logger.info("")
        self.logger.info(f"总测试数: {self.report.total_tests}")
        self.logger.info(f"成功: {self.report.total_passed} ✅")
        self.logger.info(f"失败: {self.report.total_failed} ❌")
        self.logger.info(f"跳过: {self.report.total_skipped} ⏭️")
        self.logger.info(f"成功率: {self.report.get_overall_success_rate():.1f}%")
        
        # 套件详情
        self.logger.info("")
        self.logger.info("📋 测试套件详情:")
        for suite_result in self.report.suite_results:
            success_rate = suite_result.get_success_rate()
            status_emoji = "✅" if success_rate >= 90 else "⚠️" if success_rate >= 70 else "❌"
            
            self.logger.info(
                f"  {status_emoji} {suite_result.suite_name}: "
                f"{suite_result.passed_tests}/{suite_result.total_tests} "
                f"({success_rate:.1f}%) "
                f"{format_duration(suite_result.duration)}"
            )
        
        # 关键失败
        critical_failures = self.report.get_critical_failures()
        if critical_failures:
            self.logger.info("")
            self.logger.info("🚨 关键失败:")
            for failure in critical_failures:
                self.logger.info(f"  ❌ {failure.test_name}: {failure.error_message}")
        
        # 性能摘要
        performance_summary = self.report.get_performance_summary()
        if performance_summary:
            self.logger.info("")
            self.logger.info("📈 性能摘要:")
            for metric_name, metric_data in performance_summary.items():
                if "avg" in metric_data:
                    self.logger.info(
                        f"  📊 {metric_name}: "
                        f"平均 {metric_data['avg']:.2f}{metric_data['unit']}, "
                        f"范围 {metric_data['min']:.2f}-{metric_data['max']:.2f}{metric_data['unit']}"
                    )
        
        # 系统状态评估
        overall_status = self._get_system_status()
        self.logger.info("")
        self.logger.info(f"🎯 系统整体状态: {overall_status}")
        self.logger.info("=" * 70)
    
    def _get_system_status(self) -> str:
        """获取系统整体状态"""
        success_rate = self.report.get_overall_success_rate()
        critical_failures = self.report.get_critical_failures()
        
        if critical_failures:
            return "🔴 严重问题 - 存在关键功能失败"
        elif success_rate >= 95:
            return "🟢 优秀 - 系统运行良好"
        elif success_rate >= 85:
            return "🟡 良好 - 系统基本正常"
        elif success_rate >= 70:
            return "🟠 一般 - 存在一些问题"
        else:
            return "🔴 较差 - 系统存在较多问题"
    
    async def run_single_suite(self, suite_name: str) -> Optional[TestSuiteResult]:
        """运行单个测试套件"""
        if suite_name not in self.test_suites:
            self.logger.error(f"测试套件 {suite_name} 未注册")
            return None
        
        suite_instance = self.test_suites[suite_name]
        await self._run_test_suite(suite_name, suite_instance)
        
        # 返回最新的套件结果
        for result in self.report.suite_results:
            if result.suite_name == suite_name:
                return result
        
        return None
    
    def get_available_suites(self) -> List[str]:
        """获取可用的测试套件列表"""
        return list(self.test_suites.keys())
    
    def get_test_progress(self) -> Dict[str, Any]:
        """获取测试进度"""
        return self.progress.get_summary()
    
    def save_report(self, file_path: Optional[str] = None) -> str:
        """保存测试报告"""
        if file_path is None:
            reports_dir = Path("tests/comprehensive/reports")
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = reports_dir / f"test_report_{timestamp}.json"
        
        report_data = self.report.to_dict()
        
        with open(file_path, 'w', encoding='utf-8') as f:
            import json
            json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
        
        self.logger.info(f"测试报告已保存: {file_path}")
        return str(file_path)