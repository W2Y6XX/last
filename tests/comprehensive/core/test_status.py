"""
测试状态管理
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List


class TestStatus(Enum):
    """测试状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    ERROR = "error"


class TestPriority(Enum):
    """测试优先级"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class TestExecution:
    """测试执行信息"""
    test_id: str
    test_name: str
    status: TestStatus
    priority: TestPriority
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def start(self):
        """开始执行"""
        self.status = TestStatus.RUNNING
        self.start_time = datetime.now()
    
    def complete(self, success: bool):
        """完成执行"""
        self.end_time = datetime.now()
        if self.start_time:
            self.duration = (self.end_time - self.start_time).total_seconds()
        
        self.status = TestStatus.PASSED if success else TestStatus.FAILED
    
    def fail(self, error_message: str = ""):
        """标记失败"""
        self.status = TestStatus.FAILED
        self.end_time = datetime.now()
        if self.start_time:
            self.duration = (self.end_time - self.start_time).total_seconds()
    
    def skip(self, reason: str = ""):
        """跳过测试"""
        self.status = TestStatus.SKIPPED
        self.end_time = datetime.now()
    
    def timeout(self):
        """超时"""
        self.status = TestStatus.TIMEOUT
        self.end_time = datetime.now()
        if self.start_time:
            self.duration = (self.end_time - self.start_time).total_seconds()
    
    def can_retry(self) -> bool:
        """是否可以重试"""
        return self.retry_count < self.max_retries and self.status in [TestStatus.FAILED, TestStatus.TIMEOUT, TestStatus.ERROR]
    
    def retry(self):
        """重试"""
        if self.can_retry():
            self.retry_count += 1
            self.status = TestStatus.PENDING
            self.start_time = None
            self.end_time = None
            self.duration = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "status": self.status.value,
            "priority": self.priority.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries
        }


class TestProgress:
    """测试进度跟踪"""
    
    def __init__(self):
        self.executions: Dict[str, TestExecution] = {}
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
    
    def add_test(self, test_id: str, test_name: str, priority: TestPriority = TestPriority.MEDIUM):
        """添加测试"""
        execution = TestExecution(
            test_id=test_id,
            test_name=test_name,
            status=TestStatus.PENDING,
            priority=priority
        )
        self.executions[test_id] = execution
    
    def start_test(self, test_id: str):
        """开始测试"""
        if test_id in self.executions:
            self.executions[test_id].start()
            
            # 如果是第一个测试，记录总开始时间
            if self.start_time is None:
                self.start_time = datetime.now()
    
    def complete_test(self, test_id: str, success: bool):
        """完成测试"""
        if test_id in self.executions:
            self.executions[test_id].complete(success)
    
    def fail_test(self, test_id: str, error_message: str = ""):
        """测试失败"""
        if test_id in self.executions:
            self.executions[test_id].fail(error_message)
    
    def skip_test(self, test_id: str, reason: str = ""):
        """跳过测试"""
        if test_id in self.executions:
            self.executions[test_id].skip(reason)
    
    def timeout_test(self, test_id: str):
        """测试超时"""
        if test_id in self.executions:
            self.executions[test_id].timeout()
    
    def retry_test(self, test_id: str) -> bool:
        """重试测试"""
        if test_id in self.executions:
            execution = self.executions[test_id]
            if execution.can_retry():
                execution.retry()
                return True
        return False
    
    def get_summary(self) -> Dict[str, Any]:
        """获取进度摘要"""
        total = len(self.executions)
        
        status_counts = {}
        for status in TestStatus:
            status_counts[status.value] = sum(
                1 for exec in self.executions.values() 
                if exec.status == status
            )
        
        completed = status_counts[TestStatus.PASSED.value] + status_counts[TestStatus.FAILED.value] + status_counts[TestStatus.SKIPPED.value]
        progress_percentage = (completed / total * 100) if total > 0 else 0
        
        # 计算总耗时
        total_duration = 0
        if self.start_time:
            end_time = self.end_time or datetime.now()
            total_duration = (end_time - self.start_time).total_seconds()
        
        return {
            "total_tests": total,
            "completed_tests": completed,
            "progress_percentage": progress_percentage,
            "status_counts": status_counts,
            "total_duration": total_duration,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None
        }
    
    def get_failed_tests(self) -> List[TestExecution]:
        """获取失败的测试"""
        return [
            exec for exec in self.executions.values()
            if exec.status == TestStatus.FAILED
        ]
    
    def get_pending_tests(self) -> List[TestExecution]:
        """获取待执行的测试"""
        return [
            exec for exec in self.executions.values()
            if exec.status == TestStatus.PENDING
        ]
    
    def is_complete(self) -> bool:
        """是否全部完成"""
        return all(
            exec.status in [TestStatus.PASSED, TestStatus.FAILED, TestStatus.SKIPPED]
            for exec in self.executions.values()
        )
    
    def finalize(self):
        """结束进度跟踪"""
        self.end_time = datetime.now()