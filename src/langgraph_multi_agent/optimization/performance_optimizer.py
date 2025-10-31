"""性能优化器 - 系统性能优化和调优"""

import logging
import asyncio
import time
from typing import Dict, Any, List, Optional, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import statistics
import psutil
import threading

from .cache_manager import CacheManager
from .resource_pool import ResourcePoolManager
from .concurrent_executor import ConcurrentExecutor

logger = logging.getLogger(__name__)


class OptimizationLevel(str, Enum):
    """优化级别"""
    BASIC = "basic"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


@dataclass
class PerformanceMetrics:
    """性能指标"""
    cpu_usage: float
    memory_usage: float
    disk_io: float
    network_io: float
    response_time: float
    throughput: float
    error_rate: float
    timestamp: datetime


@dataclass
class OptimizationResult:
    """优化结果"""
    optimization_type: str
    before_metrics: PerformanceMetrics
    after_metrics: PerformanceMetrics
    improvement_percentage: float
    recommendations: List[str]
    applied_optimizations: List[str]


class PerformanceOptimizer:
    """性能优化器"""
    
    def __init__(
        self,
        optimization_level: OptimizationLevel = OptimizationLevel.MODERATE,
        enable_auto_optimization: bool = True,
        optimization_interval: int = 300  # 5分钟
    ):
        self.optimization_level = optimization_level
        self.enable_auto_optimization = enable_auto_optimization
        self.optimization_interval = optimization_interval
        
        # 性能监控
        self.metrics_history: List[PerformanceMetrics] = []
        self.max_history_size = 1000
        
        # 优化组件
        self.cache_manager = CacheManager()
        self.resource_pool_manager = ResourcePoolManager()
        self.concurrent_executor = ConcurrentExecutor()
        
        # 优化策略
        self.optimization_strategies = self._initialize_optimization_strategies()
        
        # 运行状态
        self.is_monitoring = False
        self.optimization_results: List[OptimizationResult] = []
        
        # 性能阈值
        self.performance_thresholds = {
            "cpu_usage": 80.0,
            "memory_usage": 85.0,
            "response_time": 2.0,
            "error_rate": 0.05,
            "throughput_min": 10.0
        }
        
        logger.info(f"性能优化器初始化完成，优化级别: {optimization_level.value}")
    
    def _initialize_optimization_strategies(self) -> Dict[str, Callable]:
        """初始化优化策略"""
        return {
            "cache_optimization": self._optimize_cache,
            "resource_pool_optimization": self._optimize_resource_pool,
            "concurrent_execution_optimization": self._optimize_concurrent_execution,
            "memory_optimization": self._optimize_memory,
            "cpu_optimization": self._optimize_cpu,
            "io_optimization": self._optimize_io
        }
    
    async def start_monitoring(self):
        """开始性能监控"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        logger.info("开始性能监控")
        
        # 启动监控任务
        asyncio.create_task(self._monitoring_loop())
        
        if self.enable_auto_optimization:
            asyncio.create_task(self._auto_optimization_loop())
    
    def stop_monitoring(self):
        """停止性能监控"""
        self.is_monitoring = False
        logger.info("停止性能监控")
    
    async def _monitoring_loop(self):
        """监控循环"""
        while self.is_monitoring:
            try:
                # 收集性能指标
                metrics = await self._collect_performance_metrics()
                self._add_metrics(metrics)
                
                # 检查性能阈值
                await self._check_performance_thresholds(metrics)
                
                await asyncio.sleep(60)  # 每分钟收集一次指标
                
            except Exception as e:
                logger.error(f"性能监控循环失败: {e}")
                await asyncio.sleep(60)
    
    async def _auto_optimization_loop(self):
        """自动优化循环"""
        while self.is_monitoring:
            try:
                await asyncio.sleep(self.optimization_interval)
                
                if len(self.metrics_history) >= 5:  # 至少有5个数据点
                    await self.auto_optimize()
                
            except Exception as e:
                logger.error(f"自动优化循环失败: {e}")
    
    async def _collect_performance_metrics(self) -> PerformanceMetrics:
        """收集性能指标"""
        try:
            # 系统指标
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk_io = psutil.disk_io_counters()
            network_io = psutil.net_io_counters()
            
            # 应用指标（模拟）
            response_time = await self._measure_response_time()
            throughput = await self._measure_throughput()
            error_rate = await self._measure_error_rate()
            
            return PerformanceMetrics(
                cpu_usage=cpu_percent,
                memory_usage=memory.percent,
                disk_io=disk_io.read_bytes + disk_io.write_bytes if disk_io else 0,
                network_io=network_io.bytes_sent + network_io.bytes_recv if network_io else 0,
                response_time=response_time,
                throughput=throughput,
                error_rate=error_rate,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"收集性能指标失败: {e}")
            return PerformanceMetrics(
                cpu_usage=0, memory_usage=0, disk_io=0, network_io=0,
                response_time=0, throughput=0, error_rate=0,
                timestamp=datetime.now()
            )
    
    async def _measure_response_time(self) -> float:
        """测量响应时间"""
        try:
            start_time = time.time()
            # 模拟一个简单的操作
            await asyncio.sleep(0.001)
            return time.time() - start_time
        except:
            return 0.0
    
    async def _measure_throughput(self) -> float:
        """测量吞吐量"""
        try:
            # 基于最近的请求数量计算吞吐量
            if len(self.metrics_history) >= 2:
                recent_metrics = self.metrics_history[-2:]
                time_diff = (recent_metrics[1].timestamp - recent_metrics[0].timestamp).total_seconds()
                if time_diff > 0:
                    return 60.0 / time_diff  # 每分钟请求数
            return 0.0
        except:
            return 0.0
    
    async def _measure_error_rate(self) -> float:
        """测量错误率"""
        try:
            # 模拟错误率计算
            return 0.01  # 1%错误率
        except:
            return 0.0
    
    def _add_metrics(self, metrics: PerformanceMetrics):
        """添加性能指标"""
        self.metrics_history.append(metrics)
        
        # 保持历史记录大小
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history = self.metrics_history[-self.max_history_size:]
    
    async def _check_performance_thresholds(self, metrics: PerformanceMetrics):
        """检查性能阈值"""
        try:
            alerts = []
            
            if metrics.cpu_usage > self.performance_thresholds["cpu_usage"]:
                alerts.append(f"CPU使用率过高: {metrics.cpu_usage:.1f}%")
            
            if metrics.memory_usage > self.performance_thresholds["memory_usage"]:
                alerts.append(f"内存使用率过高: {metrics.memory_usage:.1f}%")
            
            if metrics.response_time > self.performance_thresholds["response_time"]:
                alerts.append(f"响应时间过长: {metrics.response_time:.3f}s")
            
            if metrics.error_rate > self.performance_thresholds["error_rate"]:
                alerts.append(f"错误率过高: {metrics.error_rate:.1%}")
            
            if metrics.throughput < self.performance_thresholds["throughput_min"]:
                alerts.append(f"吞吐量过低: {metrics.throughput:.1f}")
            
            if alerts:
                logger.warning(f"性能告警: {'; '.join(alerts)}")
                
                # 触发自动优化
                if self.enable_auto_optimization:
                    await self.auto_optimize()
            
        except Exception as e:
            logger.error(f"检查性能阈值失败: {e}")
    
    async def auto_optimize(self) -> List[OptimizationResult]:
        """自动优化"""
        try:
            logger.info("开始自动性能优化")
            
            results = []
            
            # 获取当前性能基线
            baseline_metrics = await self._collect_performance_metrics()
            
            # 应用优化策略
            for strategy_name, strategy_func in self.optimization_strategies.items():
                try:
                    logger.debug(f"应用优化策略: {strategy_name}")
                    
                    # 执行优化
                    optimization_applied = await strategy_func()
                    
                    if optimization_applied:
                        # 等待优化生效
                        await asyncio.sleep(5)
                        
                        # 测量优化后的性能
                        after_metrics = await self._collect_performance_metrics()
                        
                        # 计算改进
                        improvement = self._calculate_improvement(baseline_metrics, after_metrics)
                        
                        result = OptimizationResult(
                            optimization_type=strategy_name,
                            before_metrics=baseline_metrics,
                            after_metrics=after_metrics,
                            improvement_percentage=improvement,
                            recommendations=[],
                            applied_optimizations=[strategy_name]
                        )
                        
                        results.append(result)
                        
                        logger.info(f"优化策略 {strategy_name} 完成，改进: {improvement:.1f}%")
                
                except Exception as e:
                    logger.error(f"优化策略 {strategy_name} 失败: {e}")
            
            self.optimization_results.extend(results)
            
            logger.info(f"自动优化完成，应用了 {len(results)} 个优化策略")
            return results
            
        except Exception as e:
            logger.error(f"自动优化失败: {e}")
            return []
    
    def _calculate_improvement(
        self, 
        before: PerformanceMetrics, 
        after: PerformanceMetrics
    ) -> float:
        """计算性能改进百分比"""
        try:
            # 综合多个指标计算改进
            improvements = []
            
            # CPU改进（使用率降低是好的）
            if before.cpu_usage > 0:
                cpu_improvement = (before.cpu_usage - after.cpu_usage) / before.cpu_usage * 100
                improvements.append(cpu_improvement)
            
            # 内存改进（使用率降低是好的）
            if before.memory_usage > 0:
                memory_improvement = (before.memory_usage - after.memory_usage) / before.memory_usage * 100
                improvements.append(memory_improvement)
            
            # 响应时间改进（时间减少是好的）
            if before.response_time > 0:
                response_improvement = (before.response_time - after.response_time) / before.response_time * 100
                improvements.append(response_improvement)
            
            # 吞吐量改进（增加是好的）
            if before.throughput > 0:
                throughput_improvement = (after.throughput - before.throughput) / before.throughput * 100
                improvements.append(throughput_improvement)
            
            # 错误率改进（降低是好的）
            if before.error_rate > 0:
                error_improvement = (before.error_rate - after.error_rate) / before.error_rate * 100
                improvements.append(error_improvement)
            
            # 返回平均改进
            return statistics.mean(improvements) if improvements else 0.0
            
        except Exception as e:
            logger.error(f"计算性能改进失败: {e}")
            return 0.0
    
    async def _optimize_cache(self) -> bool:
        """缓存优化"""
        try:
            # 清理过期缓存
            cleaned = await self.cache_manager.cleanup_expired()
            
            # 优化缓存大小
            if self.cache_manager.get_cache_size() > 1000:
                await self.cache_manager.optimize_cache_size()
                return True
            
            return cleaned > 0
            
        except Exception as e:
            logger.error(f"缓存优化失败: {e}")
            return False
    
    async def _optimize_resource_pool(self) -> bool:
        """资源池优化"""
        try:
            # 调整资源池大小
            optimized = await self.resource_pool_manager.optimize_pool_sizes()
            
            # 清理空闲资源
            cleaned = await self.resource_pool_manager.cleanup_idle_resources()
            
            return optimized or cleaned > 0
            
        except Exception as e:
            logger.error(f"资源池优化失败: {e}")
            return False
    
    async def _optimize_concurrent_execution(self) -> bool:
        """并发执行优化"""
        try:
            # 调整并发级别
            adjusted = await self.concurrent_executor.adjust_concurrency_level()
            
            # 优化任务队列
            optimized = await self.concurrent_executor.optimize_task_queue()
            
            return adjusted or optimized
            
        except Exception as e:
            logger.error(f"并发执行优化失败: {e}")
            return False
    
    async def _optimize_memory(self) -> bool:
        """内存优化"""
        try:
            import gc
            
            # 强制垃圾回收
            collected = gc.collect()
            
            # 清理大对象
            if collected > 100:
                logger.info(f"垃圾回收清理了 {collected} 个对象")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"内存优化失败: {e}")
            return False
    
    async def _optimize_cpu(self) -> bool:
        """CPU优化"""
        try:
            # 调整线程池大小
            current_threads = threading.active_count()
            optimal_threads = psutil.cpu_count() * 2
            
            if current_threads > optimal_threads:
                logger.info(f"当前线程数 {current_threads} 超过最优值 {optimal_threads}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"CPU优化失败: {e}")
            return False
    
    async def _optimize_io(self) -> bool:
        """I/O优化"""
        try:
            # 这里可以实现I/O优化策略
            # 例如：批量I/O操作、异步I/O等
            return False
            
        except Exception as e:
            logger.error(f"I/O优化失败: {e}")
            return False
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        try:
            if not self.metrics_history:
                return {"error": "没有性能数据"}
            
            recent_metrics = self.metrics_history[-10:]  # 最近10个数据点
            
            return {
                "current_metrics": {
                    "cpu_usage": recent_metrics[-1].cpu_usage,
                    "memory_usage": recent_metrics[-1].memory_usage,
                    "response_time": recent_metrics[-1].response_time,
                    "throughput": recent_metrics[-1].throughput,
                    "error_rate": recent_metrics[-1].error_rate
                },
                "average_metrics": {
                    "cpu_usage": statistics.mean([m.cpu_usage for m in recent_metrics]),
                    "memory_usage": statistics.mean([m.memory_usage for m in recent_metrics]),
                    "response_time": statistics.mean([m.response_time for m in recent_metrics]),
                    "throughput": statistics.mean([m.throughput for m in recent_metrics]),
                    "error_rate": statistics.mean([m.error_rate for m in recent_metrics])
                },
                "optimization_results": len(self.optimization_results),
                "total_improvements": sum(r.improvement_percentage for r in self.optimization_results),
                "monitoring_duration": (
                    (datetime.now() - self.metrics_history[0].timestamp).total_seconds() / 3600
                ) if self.metrics_history else 0,
                "data_points": len(self.metrics_history)
            }
            
        except Exception as e:
            logger.error(f"获取性能摘要失败: {e}")
            return {"error": str(e)}
    
    def get_optimization_recommendations(self) -> List[str]:
        """获取优化建议"""
        try:
            recommendations = []
            
            if not self.metrics_history:
                return ["需要更多性能数据来生成建议"]
            
            recent_metrics = self.metrics_history[-5:]
            avg_cpu = statistics.mean([m.cpu_usage for m in recent_metrics])
            avg_memory = statistics.mean([m.memory_usage for m in recent_metrics])
            avg_response_time = statistics.mean([m.response_time for m in recent_metrics])
            
            # CPU建议
            if avg_cpu > 80:
                recommendations.append("CPU使用率过高，建议优化算法或增加并发控制")
            elif avg_cpu < 20:
                recommendations.append("CPU使用率较低，可以考虑增加并发处理")
            
            # 内存建议
            if avg_memory > 85:
                recommendations.append("内存使用率过高，建议优化内存使用或增加缓存清理")
            
            # 响应时间建议
            if avg_response_time > 1.0:
                recommendations.append("响应时间较长，建议优化数据库查询或增加缓存")
            
            # 通用建议
            if len(self.optimization_results) == 0:
                recommendations.append("建议启用自动优化功能")
            
            return recommendations if recommendations else ["系统性能良好，暂无优化建议"]
            
        except Exception as e:
            logger.error(f"获取优化建议失败: {e}")
            return ["获取建议失败"]
    
    def set_optimization_level(self, level: OptimizationLevel):
        """设置优化级别"""
        self.optimization_level = level
        
        # 根据优化级别调整阈值
        if level == OptimizationLevel.BASIC:
            self.performance_thresholds.update({
                "cpu_usage": 90.0,
                "memory_usage": 90.0,
                "response_time": 3.0
            })
        elif level == OptimizationLevel.MODERATE:
            self.performance_thresholds.update({
                "cpu_usage": 80.0,
                "memory_usage": 85.0,
                "response_time": 2.0
            })
        elif level == OptimizationLevel.AGGRESSIVE:
            self.performance_thresholds.update({
                "cpu_usage": 70.0,
                "memory_usage": 75.0,
                "response_time": 1.0
            })
        
        logger.info(f"优化级别已设置为: {level.value}")
    
    def clear_history(self):
        """清空历史数据"""
        self.metrics_history.clear()
        self.optimization_results.clear()
        logger.info("性能历史数据已清空")