"""系统性能集成 - 将性能优化集成到主系统中"""

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from ..optimization import (
    PerformanceOptimizer, 
    OptimizationLevel,
    CacheManager,
    ResourcePoolManager,
    ConcurrentExecutor,
    ExecutionMode
)
from .config_manager import ConfigManager

logger = logging.getLogger(__name__)


class SystemPerformanceManager:
    """系统性能管理器"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        
        # 获取性能配置
        perf_config = config_manager.get_config("performance", {})
        
        # 初始化性能组件
        self.performance_optimizer = PerformanceOptimizer(
            optimization_level=OptimizationLevel(perf_config.get("optimization_level", "moderate")),
            enable_auto_optimization=perf_config.get("enable_auto_optimization", True),
            optimization_interval=perf_config.get("optimization_interval", 300)
        )
        
        self.cache_manager = CacheManager(
            max_cache_size=perf_config.get("max_cache_size", 10000),
            default_ttl=perf_config.get("default_ttl", 3600),
            cleanup_interval=perf_config.get("cleanup_interval", 300)
        )
        
        self.resource_pool_manager = ResourcePoolManager()
        
        self.concurrent_executor = ConcurrentExecutor(
            max_workers=perf_config.get("max_workers"),
            execution_mode=ExecutionMode(perf_config.get("execution_mode", "adaptive")),
            enable_auto_scaling=perf_config.get("enable_auto_scaling", True)
        )
        
        # 运行状态
        self.is_running = False
        
        logger.info("系统性能管理器初始化完成")
    
    async def start(self):
        """启动性能管理器"""
        if self.is_running:
            return
        
        try:
            # 启动各个组件
            await self.performance_optimizer.start_monitoring()
            await self.cache_manager.start()
            await self.resource_pool_manager.start_all_cleanup()
            await self.concurrent_executor.start()
            
            # 创建默认资源池
            await self._create_default_resource_pools()
            
            self.is_running = True
            logger.info("系统性能管理器已启动")
            
        except Exception as e:
            logger.error(f"启动系统性能管理器失败: {e}")
            raise
    
    async def stop(self):
        """停止性能管理器"""
        if not self.is_running:
            return
        
        try:
            # 停止各个组件
            self.performance_optimizer.stop_monitoring()
            await self.cache_manager.stop()
            await self.resource_pool_manager.stop_all_cleanup()
            await self.concurrent_executor.stop()
            
            self.is_running = False
            logger.info("系统性能管理器已停止")
            
        except Exception as e:
            logger.error(f"停止系统性能管理器失败: {e}")
    
    async def _create_default_resource_pools(self):
        """创建默认资源池"""
        try:
            # 创建数据库连接池
            def create_db_connection():
                # 这里应该返回实际的数据库连接
                return {"type": "db_connection", "created_at": datetime.now()}
            
            self.resource_pool_manager.create_pool(
                pool_name="database",
                resource_type="db_connection",
                factory=create_db_connection,
                min_size=2,
                max_size=10
            )
            
            # 创建HTTP客户端池
            def create_http_client():
                # 这里应该返回实际的HTTP客户端
                return {"type": "http_client", "created_at": datetime.now()}
            
            self.resource_pool_manager.create_pool(
                pool_name="http_client",
                resource_type="http_client", 
                factory=create_http_client,
                min_size=1,
                max_size=5
            )
            
            logger.info("默认资源池创建完成")
            
        except Exception as e:
            logger.error(f"创建默认资源池失败: {e}")
    
    def get_cache_manager(self) -> CacheManager:
        """获取缓存管理器"""
        return self.cache_manager
    
    def get_resource_pool_manager(self) -> ResourcePoolManager:
        """获取资源池管理器"""
        return self.resource_pool_manager
    
    def get_concurrent_executor(self) -> ConcurrentExecutor:
        """获取并发执行器"""
        return self.concurrent_executor
    
    def get_performance_optimizer(self) -> PerformanceOptimizer:
        """获取性能优化器"""
        return self.performance_optimizer
    
    async def optimize_system(self) -> Dict[str, Any]:
        """执行系统优化"""
        try:
            logger.info("开始系统性能优化")
            
            # 执行自动优化
            optimization_results = await self.performance_optimizer.auto_optimize()
            
            # 获取优化后的统计信息
            stats = self.get_system_stats()
            
            result = {
                "optimization_results": len(optimization_results),
                "total_improvement": sum(r.improvement_percentage for r in optimization_results),
                "system_stats": stats,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"系统优化完成，应用了 {len(optimization_results)} 个优化策略")
            return result
            
        except Exception as e:
            logger.error(f"系统优化失败: {e}")
            return {"error": str(e)}
    
    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        try:
            return {
                "performance": self.performance_optimizer.get_performance_summary(),
                "cache": self.cache_manager.get_cache_stats(),
                "resource_pools": self.resource_pool_manager.get_all_stats(),
                "concurrent_executor": self.concurrent_executor.get_stats(),
                "is_running": self.is_running
            }
            
        except Exception as e:
            logger.error(f"获取系统统计失败: {e}")
            return {"error": str(e)}
    
    def get_optimization_recommendations(self) -> Dict[str, Any]:
        """获取优化建议"""
        try:
            recommendations = {
                "performance": self.performance_optimizer.get_optimization_recommendations(),
                "cache": self._get_cache_recommendations(),
                "resource_pools": self._get_resource_pool_recommendations(),
                "concurrent_execution": self._get_concurrent_execution_recommendations()
            }
            
            return recommendations
            
        except Exception as e:
            logger.error(f"获取优化建议失败: {e}")
            return {"error": str(e)}
    
    def _get_cache_recommendations(self) -> list:
        """获取缓存优化建议"""
        try:
            cache_stats = self.cache_manager.get_cache_stats()
            recommendations = []
            
            global_stats = cache_stats.get("global_stats", {})
            hit_rate = global_stats.get("hit_rate", 0)
            
            if hit_rate < 0.5:
                recommendations.append("缓存命中率较低，建议增加缓存TTL或优化缓存策略")
            
            if global_stats.get("total_size", 0) > 8000:
                recommendations.append("缓存大小较大，建议增加清理频率")
            
            return recommendations if recommendations else ["缓存性能良好"]
            
        except Exception as e:
            logger.error(f"获取缓存建议失败: {e}")
            return ["获取缓存建议失败"]
    
    def _get_resource_pool_recommendations(self) -> list:
        """获取资源池优化建议"""
        try:
            pool_stats = self.resource_pool_manager.get_all_stats()
            recommendations = []
            
            summary = pool_stats.get("summary", {})
            avg_utilization = summary.get("average_utilization", 0)
            
            if avg_utilization > 0.9:
                recommendations.append("资源池利用率过高，建议增加资源池大小")
            elif avg_utilization < 0.3:
                recommendations.append("资源池利用率较低，可以考虑减少资源池大小")
            
            return recommendations if recommendations else ["资源池配置合理"]
            
        except Exception as e:
            logger.error(f"获取资源池建议失败: {e}")
            return ["获取资源池建议失败"]
    
    def _get_concurrent_execution_recommendations(self) -> list:
        """获取并发执行优化建议"""
        try:
            exec_stats = self.concurrent_executor.get_stats()
            recommendations = []
            
            current_load = exec_stats.get("current_load", 0)
            queue_size = exec_stats.get("queue_size", 0)
            
            if current_load > 0.9:
                recommendations.append("并发负载过高，建议增加工作线程数")
            
            if queue_size > 100:
                recommendations.append("任务队列积压严重，建议优化任务处理速度")
            
            return recommendations if recommendations else ["并发执行性能良好"]
            
        except Exception as e:
            logger.error(f"获取并发执行建议失败: {e}")
            return ["获取并发执行建议失败"]
    
    async def health_check(self) -> Dict[str, Any]:
        """系统健康检查"""
        try:
            health_status = {
                "overall": "healthy",
                "components": {},
                "issues": [],
                "timestamp": datetime.now().isoformat()
            }
            
            # 检查各个组件
            components = {
                "performance_optimizer": self.performance_optimizer.is_monitoring,
                "cache_manager": self.cache_manager.is_running,
                "resource_pool_manager": True,  # 简化检查
                "concurrent_executor": self.concurrent_executor.is_running
            }
            
            for component, status in components.items():
                health_status["components"][component] = "healthy" if status else "unhealthy"
                if not status:
                    health_status["issues"].append(f"{component} 未运行")
            
            # 检查性能指标
            stats = self.get_system_stats()
            
            # 检查缓存命中率
            cache_stats = stats.get("cache", {}).get("global_stats", {})
            hit_rate = cache_stats.get("hit_rate", 0)
            if hit_rate < 0.3:
                health_status["issues"].append("缓存命中率过低")
            
            # 检查并发负载
            exec_stats = stats.get("concurrent_executor", {})
            current_load = exec_stats.get("current_load", 0)
            if current_load > 0.95:
                health_status["issues"].append("并发负载过高")
            
            # 确定整体状态
            if health_status["issues"]:
                health_status["overall"] = "degraded" if len(health_status["issues"]) <= 2 else "unhealthy"
            
            return health_status
            
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return {
                "overall": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def update_configuration(self, config_updates: Dict[str, Any]):
        """更新性能配置"""
        try:
            # 更新优化级别
            if "optimization_level" in config_updates:
                level = OptimizationLevel(config_updates["optimization_level"])
                self.performance_optimizer.set_optimization_level(level)
            
            # 更新并发配置
            if "max_workers" in config_updates:
                # 这里需要重启并发执行器来应用新配置
                logger.info("并发配置更新需要重启服务生效")
            
            logger.info("性能配置已更新")
            
        except Exception as e:
            logger.error(f"更新性能配置失败: {e}")
            raise