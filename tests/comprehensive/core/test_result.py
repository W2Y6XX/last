"""
测试结果数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum
import json

from .test_status import TestStatus


class ResultType(Enum):
    """结果类型"""
    FUNCTIONAL = "functional"
    PERFORMANCE = "performance"
    INTEGRATION = "integration"
    SECURITY = "security"
    USABILITY = "usability"


@dataclass
class TestMetric:
    """测试指标"""
    name: str
    value: Union[int, float, str]
    unit: str = ""
    threshold: Optional[Union[int, float]] = None
    passed: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "threshold": self.threshold,
            "passed": self.passed
        }


@dataclass
class TestStep:
    """测试步骤"""
    name: str
    status: TestStatus
    duration: float = 0.0
    details: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "duration": self.duration,
            "details": self.details,
            "error_message": self.error_message
        }


@dataclass
class TestResult:
    """测试结果"""
    test_id: str
    test_name: str
    test_suite: str
    status: TestStatus
    result_type: ResultType = ResultType.FUNCTIONAL
    
    # 时间信息
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: float = 0.0
    
    # 结果详情
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    
    # 测试步骤
    steps: List[TestStep] = field(default_factory=list)
    
    # 性能指标
    metrics: List[TestMetric] = field(default_factory=list)
    
    # 附加信息
    tags: List[str] = field(default_factory=list)
    environment: Optional[str] = None
    retry_count: int = 0
    
    def add_step(self, name: str, status: TestStatus, duration: float = 0.0, 
                details: Optional[Dict[str, Any]] = None, error_message: Optional[str] = None):
        """添加测试步骤"""
        step = TestStep(
            name=name,
            status=status,
            duration=duration,
            details=details,
            error_message=error_message
        )
        self.steps.append(step)
    
    def add_metric(self, name: str, value: Union[int, float, str], unit: str = "",
                  threshold: Optional[Union[int, float]] = None):
        """添加性能指标"""
        passed = True
        if threshold is not None and isinstance(value, (int, float)):
            passed = value <= threshold
        
        metric = TestMetric(
            name=name,
            value=value,
            unit=unit,
            threshold=threshold,
            passed=passed
        )
        self.metrics.append(metric)
    
    def set_error(self, error_message: str, error_traceback: Optional[str] = None):
        """设置错误信息"""
        self.status = TestStatus.FAILED
        self.error_message = error_message
        self.error_traceback = error_traceback
    
    def set_success(self, details: Optional[Dict[str, Any]] = None):
        """设置成功状态"""
        self.status = TestStatus.PASSED
        if details:
            self.details.update(details)
    
    def calculate_duration(self):
        """计算执行时间"""
        if self.start_time and self.end_time:
            self.duration = (self.end_time - self.start_time).total_seconds()
    
    def is_passed(self) -> bool:
        """是否通过"""
        return self.status == TestStatus.PASSED
    
    def is_failed(self) -> bool:
        """是否失败"""
        return self.status == TestStatus.FAILED
    
    def get_failed_metrics(self) -> List[TestMetric]:
        """获取失败的指标"""
        return [metric for metric in self.metrics if not metric.passed]
    
    def get_failed_steps(self) -> List[TestStep]:
        """获取失败的步骤"""
        return [step for step in self.steps if step.status == TestStatus.FAILED]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "test_suite": self.test_suite,
            "status": self.status.value,
            "result_type": self.result_type.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "details": self.details,
            "error_message": self.error_message,
            "error_traceback": self.error_traceback,
            "steps": [step.to_dict() for step in self.steps],
            "metrics": [metric.to_dict() for metric in self.metrics],
            "tags": self.tags,
            "environment": self.environment,
            "retry_count": self.retry_count
        }
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False, default=str)


@dataclass
class TestSuiteResult:
    """测试套件结果"""
    suite_name: str
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: float = 0.0
    
    results: List[TestResult] = field(default_factory=list)
    
    def add_result(self, result: TestResult):
        """添加测试结果"""
        self.results.append(result)
        self.total_tests += 1
        
        if result.status == TestStatus.PASSED:
            self.passed_tests += 1
        elif result.status == TestStatus.FAILED:
            self.failed_tests += 1
        elif result.status == TestStatus.SKIPPED:
            self.skipped_tests += 1
    
    def calculate_duration(self):
        """计算总执行时间"""
        if self.start_time and self.end_time:
            self.duration = (self.end_time - self.start_time).total_seconds()
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100
    
    def get_failed_results(self) -> List[TestResult]:
        """获取失败的测试结果"""
        return [result for result in self.results if result.is_failed()]
    
    def get_summary(self) -> Dict[str, Any]:
        """获取摘要"""
        return {
            "suite_name": self.suite_name,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "skipped_tests": self.skipped_tests,
            "success_rate": self.get_success_rate(),
            "duration": self.duration,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        summary = self.get_summary()
        summary["results"] = [result.to_dict() for result in self.results]
        return summary


@dataclass
class ComprehensiveTestReport:
    """综合测试报告"""
    report_id: str
    test_session_id: str
    environment: str
    
    start_time: datetime
    end_time: Optional[datetime] = None
    total_duration: float = 0.0
    
    suite_results: List[TestSuiteResult] = field(default_factory=list)
    
    # 总体统计
    total_tests: int = 0
    total_passed: int = 0
    total_failed: int = 0
    total_skipped: int = 0
    
    # 系统信息
    system_info: Dict[str, Any] = field(default_factory=dict)
    
    def add_suite_result(self, suite_result: TestSuiteResult):
        """添加套件结果"""
        self.suite_results.append(suite_result)
        
        # 更新总体统计
        self.total_tests += suite_result.total_tests
        self.total_passed += suite_result.passed_tests
        self.total_failed += suite_result.failed_tests
        self.total_skipped += suite_result.skipped_tests
    
    def finalize(self):
        """完成报告"""
        self.end_time = datetime.now()
        if self.start_time:
            self.total_duration = (self.end_time - self.start_time).total_seconds()
    
    def get_overall_success_rate(self) -> float:
        """获取总体成功率"""
        if self.total_tests == 0:
            return 0.0
        return (self.total_passed / self.total_tests) * 100
    
    def get_critical_failures(self) -> List[TestResult]:
        """获取关键失败"""
        critical_failures = []
        for suite_result in self.suite_results:
            for result in suite_result.get_failed_results():
                if "critical" in result.tags or suite_result.suite_name in ["health_check", "api_tests"]:
                    critical_failures.append(result)
        return critical_failures
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        all_metrics = []
        for suite_result in self.suite_results:
            for result in suite_result.results:
                all_metrics.extend(result.metrics)
        
        performance_metrics = {}
        for metric in all_metrics:
            if metric.name not in performance_metrics:
                performance_metrics[metric.name] = {
                    "values": [],
                    "unit": metric.unit,
                    "passed_count": 0,
                    "failed_count": 0
                }
            
            performance_metrics[metric.name]["values"].append(metric.value)
            if metric.passed:
                performance_metrics[metric.name]["passed_count"] += 1
            else:
                performance_metrics[metric.name]["failed_count"] += 1
        
        # 计算统计信息
        for metric_name, metric_data in performance_metrics.items():
            values = [v for v in metric_data["values"] if isinstance(v, (int, float))]
            if values:
                metric_data.update({
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "count": len(values)
                })
        
        return performance_metrics
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "report_id": self.report_id,
            "test_session_id": self.test_session_id,
            "environment": self.environment,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_duration": self.total_duration,
            "summary": {
                "total_tests": self.total_tests,
                "total_passed": self.total_passed,
                "total_failed": self.total_failed,
                "total_skipped": self.total_skipped,
                "success_rate": self.get_overall_success_rate()
            },
            "suite_results": [suite.to_dict() for suite in self.suite_results],
            "performance_summary": self.get_performance_summary(),
            "critical_failures": [failure.to_dict() for failure in self.get_critical_failures()],
            "system_info": self.system_info
        }