"""
测试日志工具
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum


class LogLevel(Enum):
    """日志级别"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class TestLogger:
    """测试日志器"""
    
    def __init__(self, name: str = "comprehensive_test", 
                 level: LogLevel = LogLevel.INFO,
                 log_file: Optional[str] = None,
                 console_output: bool = True):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level.value)
        
        # 清除现有处理器
        self.logger.handlers.clear()
        
        # 设置格式器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 控制台输出
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # 文件输出
        if log_file:
            # 确保日志目录存在
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def debug(self, message: str, **kwargs):
        """调试日志"""
        self._log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """信息日志"""
        self._log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """警告日志"""
        self._log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """错误日志"""
        self._log(LogLevel.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """严重错误日志"""
        self._log(LogLevel.CRITICAL, message, **kwargs)
    
    def _log(self, level: LogLevel, message: str, **kwargs):
        """内部日志方法"""
        if kwargs:
            extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
            message = f"{message} | {extra_info}"
        
        self.logger.log(level.value, message)
    
    def test_start(self, test_name: str, **context):
        """测试开始日志"""
        self.info(f"🧪 开始测试: {test_name}", **context)
    
    def test_end(self, test_name: str, success: bool, duration: float, **context):
        """测试结束日志"""
        status = "✅ 成功" if success else "❌ 失败"
        self.info(f"{status} 测试完成: {test_name} (耗时: {duration:.2f}s)", **context)
    
    def test_step(self, step_name: str, **context):
        """测试步骤日志"""
        self.info(f"  🔍 执行步骤: {step_name}", **context)
    
    def test_result(self, test_name: str, result: Dict[str, Any]):
        """测试结果日志"""
        self.info(f"📊 测试结果: {test_name}", **result)
    
    def performance_metric(self, metric_name: str, value: float, unit: str = "", **context):
        """性能指标日志"""
        self.info(f"📈 性能指标: {metric_name} = {value}{unit}", **context)
    
    def error_detail(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """详细错误日志"""
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error)
        }
        if context:
            error_info.update(context)
        
        self.error(f"💥 错误详情: {error}", **error_info)


# 全局日志器实例
_global_logger: Optional[TestLogger] = None


def get_logger(name: Optional[str] = None) -> TestLogger:
    """获取全局日志器"""
    global _global_logger
    
    if _global_logger is None:
        # 创建日志目录
        log_dir = Path("tests/comprehensive/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成日志文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"test_run_{timestamp}.log"
        
        _global_logger = TestLogger(
            name=name or "comprehensive_test",
            level=LogLevel.INFO,
            log_file=str(log_file),
            console_output=True
        )
    
    return _global_logger


def setup_logging(level: LogLevel = LogLevel.INFO, 
                 log_file: Optional[str] = None,
                 console_output: bool = True) -> TestLogger:
    """设置日志配置"""
    global _global_logger
    
    _global_logger = TestLogger(
        name="comprehensive_test",
        level=level,
        log_file=log_file,
        console_output=console_output
    )
    
    return _global_logger


def log_test_summary(total_tests: int, passed: int, failed: int, 
                    skipped: int, total_duration: float):
    """记录测试摘要"""
    logger = get_logger()
    
    success_rate = (passed / total_tests * 100) if total_tests > 0 else 0
    
    logger.info("=" * 60)
    logger.info("📊 测试执行摘要")
    logger.info("=" * 60)
    logger.info(f"总测试数: {total_tests}")
    logger.info(f"成功: {passed} ✅")
    logger.info(f"失败: {failed} ❌")
    logger.info(f"跳过: {skipped} ⏭️")
    logger.info(f"成功率: {success_rate:.1f}%")
    logger.info(f"总耗时: {total_duration:.2f}s")
    logger.info("=" * 60)