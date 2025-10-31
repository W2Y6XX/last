"""资源池管理器 - 智能资源分配和管理"""

import logging
import asyncio
import threading
from typing import Dict, Any, Optional, List, Callable, TypeVar, Generic
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import queue
import weakref
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ResourceState(str, Enum):
    """资源状态"""
    IDLE = "idle"
    BUSY = "busy"
    RESERVED = "reserved"
    MAINTENANCE = "maintenance"
    FAILED = "failed"


@dataclass
class ResourceInfo:
    """资源信息"""
    resource_id: str
    resource_type: str
    state: ResourceState
    created_at: datetime
    last_used: datetime
    usage_count: int
    max_usage: Optional[int] = None
    metadata: Dict[str, Any] = None
    
    def is_expired(self, max_idle_time: int = 3600) -> bool:
        """检查资源是否过期"""
        idle_time = (datetime.now() - self.last_used).total_seconds()
        return idle_time > max_idle_time
    
    def is_overused(self) -> bool:
        """检查资源是否过度使用"""
        if self.max_usage is None:
            return False
        return self.usage_count >= self.max_usage


class ResourcePool(Generic[T]):
    """通用资源池"""
    
    def __init__(
        self,
        resource_type: str,
        factory: Callable[[], T],
        min_size: int = 1,
        max_size: int = 10,
        max_idle_time: int = 3600,
        cleanup_interval: int = 300
    ):
        self.resource_type = resource_type
        self.factory = factory
        self.min_size = min_size
        self.max_size = max_size
        self.max_idle_time = max_idle_time
        self.cleanup_interval = cleanup_interval
        
        # 资源存储
        self.resources: Dict[str, T] = {}
        self.resource_info: Dict[str, ResourceInfo] = {}
        self.available_queue: queue.Queue = queue.Queue()
        
        # 同步控制
        self.lock = threading.RLock()
        self.condition = threading.Condition(self.lock)
        
        # 统计信息
        self.stats = {
            "created": 0,
            "destroyed": 0,
            "acquired": 0,
            "released": 0,
            "timeouts": 0,
            "failures": 0
        }
        
        # 运行状态
        self.is_running = False
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # 初始化最小资源
        self._initialize_pool()
        
        logger.info(f"资源池初始化完成: {resource_type}, 大小: {min_size}-{max_size}")
    
    def _initialize_pool(self):
        """初始化资源池"""
        with self.lock:
            for _ in range(self.min_size):
                self._create_resource()
    
    def _create_resource(self) -> Optional[str]:
        """创建新资源"""
        try:
            if len(self.resources) >= self.max_size:
                return None
            
            resource = self.factory()
            resource_id = f"{self.resource_type}_{len(self.resources)}_{int(datetime.now().timestamp())}"
            
            self.resources[resource_id] = resource
            self.resource_info[resource_id] = ResourceInfo(
                resource_id=resource_id,
                resource_type=self.resource_type,
                state=ResourceState.IDLE,
                created_at=datetime.now(),
                last_used=datetime.now(),
                usage_count=0,
                metadata={}
            )
            
            self.available_queue.put(resource_id)
            self.stats["created"] += 1
            
            logger.debug(f"创建资源: {resource_id}")
            return resource_id
            
        except Exception as e:
            logger.error(f"创建资源失败: {e}")
            self.stats["failures"] += 1
            return None
    
    def _destroy_resource(self, resource_id: str):
        """销毁资源"""
        try:
            if resource_id in self.resources:
                resource = self.resources[resource_id]
                
                # 如果资源有清理方法，调用它
                if hasattr(resource, 'close'):
                    resource.close()
                elif hasattr(resource, 'cleanup'):
                    resource.cleanup()
                
                del self.resources[resource_id]
                del self.resource_info[resource_id]
                
                self.stats["destroyed"] += 1
                logger.debug(f"销毁资源: {resource_id}")
            
        except Exception as e:
            logger.error(f"销毁资源失败: {e}")
    
    def acquire(self, timeout: float = 30.0) -> Optional[T]:
        """获取资源"""
        try:
            with self.condition:
                start_time = datetime.now()
                
                while True:
                    # 尝试从可用队列获取资源
                    try:
                        resource_id = self.available_queue.get_nowait()
                        
                        if resource_id in self.resources:
                            info = self.resource_info[resource_id]
                            
                            # 检查资源状态
                            if info.state == ResourceState.IDLE and not info.is_overused():
                                info.state = ResourceState.BUSY
                                info.last_used = datetime.now()
                                info.usage_count += 1
                                
                                self.stats["acquired"] += 1
                                logger.debug(f"获取资源: {resource_id}")
                                
                                return self.resources[resource_id]
                            else:
                                # 资源不可用，销毁它
                                self._destroy_resource(resource_id)
                        
                    except queue.Empty:
                        # 队列为空，尝试创建新资源
                        new_resource_id = self._create_resource()
                        if new_resource_id:
                            continue
                    
                    # 检查超时
                    elapsed = (datetime.now() - start_time).total_seconds()
                    if elapsed >= timeout:
                        self.stats["timeouts"] += 1
                        logger.warning(f"获取资源超时: {timeout}s")
                        return None
                    
                    # 等待资源释放
                    remaining_timeout = timeout - elapsed
                    self.condition.wait(remaining_timeout)
            
        except Exception as e:
            logger.error(f"获取资源失败: {e}")
            self.stats["failures"] += 1
            return None
    
    def release(self, resource: T):
        """释放资源"""
        try:
            with self.condition:
                # 查找资源ID
                resource_id = None
                for rid, res in self.resources.items():
                    if res is resource:
                        resource_id = rid
                        break
                
                if resource_id and resource_id in self.resource_info:
                    info = self.resource_info[resource_id]
                    
                    if info.state == ResourceState.BUSY:
                        info.state = ResourceState.IDLE
                        info.last_used = datetime.now()
                        
                        # 检查资源是否需要销毁
                        if info.is_overused() or info.is_expired(self.max_idle_time):
                            self._destroy_resource(resource_id)
                        else:
                            self.available_queue.put(resource_id)
                        
                        self.stats["released"] += 1
                        logger.debug(f"释放资源: {resource_id}")
                        
                        # 通知等待的线程
                        self.condition.notify()
            
        except Exception as e:
            logger.error(f"释放资源失败: {e}")
    
    @asynccontextmanager
    async def get_resource(self, timeout: float = 30.0):
        """异步上下文管理器获取资源"""
        resource = None
        try:
            # 在线程池中获取资源
            loop = asyncio.get_event_loop()
            resource = await loop.run_in_executor(None, self.acquire, timeout)
            
            if resource is None:
                raise TimeoutError("获取资源超时")
            
            yield resource
            
        finally:
            if resource is not None:
                # 在线程池中释放资源
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.release, resource)
    
    async def start_cleanup(self):
        """启动清理任务"""
        if self.is_running:
            return
        
        self.is_running = True
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info(f"资源池清理任务已启动: {self.resource_type}")
    
    async def stop_cleanup(self):
        """停止清理任务"""
        self.is_running = False
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"资源池清理任务已停止: {self.resource_type}")
    
    async def _cleanup_loop(self):
        """清理循环"""
        while self.is_running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_expired_resources()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"资源池清理失败: {e}")
    
    async def _cleanup_expired_resources(self):
        """清理过期资源"""
        try:
            expired_resources = []
            
            with self.lock:
                for resource_id, info in self.resource_info.items():
                    if (info.state == ResourceState.IDLE and 
                        (info.is_expired(self.max_idle_time) or info.is_overused())):
                        expired_resources.append(resource_id)
            
            # 销毁过期资源
            for resource_id in expired_resources:
                self._destroy_resource(resource_id)
            
            # 确保最小资源数量
            current_size = len(self.resources)
            if current_size < self.min_size:
                for _ in range(self.min_size - current_size):
                    self._create_resource()
            
            if expired_resources:
                logger.info(f"清理过期资源: {len(expired_resources)} 个")
            
        except Exception as e:
            logger.error(f"清理过期资源失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取资源池统计"""
        with self.lock:
            idle_count = sum(1 for info in self.resource_info.values() 
                           if info.state == ResourceState.IDLE)
            busy_count = sum(1 for info in self.resource_info.values() 
                           if info.state == ResourceState.BUSY)
            
            return {
                "resource_type": self.resource_type,
                "total_resources": len(self.resources),
                "idle_resources": idle_count,
                "busy_resources": busy_count,
                "available_in_queue": self.available_queue.qsize(),
                "min_size": self.min_size,
                "max_size": self.max_size,
                "stats": self.stats.copy(),
                "utilization": busy_count / len(self.resources) if self.resources else 0
            }
    
    def resize(self, new_min_size: int, new_max_size: int):
        """调整资源池大小"""
        with self.lock:
            self.min_size = new_min_size
            self.max_size = new_max_size
            
            current_size = len(self.resources)
            
            # 如果当前大小小于最小值，创建更多资源
            if current_size < new_min_size:
                for _ in range(new_min_size - current_size):
                    self._create_resource()
            
            # 如果当前大小大于最大值，标记多余资源为待销毁
            elif current_size > new_max_size:
                excess_count = current_size - new_max_size
                idle_resources = [rid for rid, info in self.resource_info.items() 
                                if info.state == ResourceState.IDLE]
                
                for i, resource_id in enumerate(idle_resources):
                    if i >= excess_count:
                        break
                    self._destroy_resource(resource_id)
            
            logger.info(f"资源池大小已调整: {new_min_size}-{new_max_size}")


class ResourcePoolManager:
    """资源池管理器"""
    
    def __init__(self):
        self.pools: Dict[str, ResourcePool] = {}
        self.lock = threading.RLock()
        
        logger.info("资源池管理器初始化完成")
    
    def create_pool(
        self,
        pool_name: str,
        resource_type: str,
        factory: Callable,
        min_size: int = 1,
        max_size: int = 10,
        **kwargs
    ) -> ResourcePool:
        """创建资源池"""
        with self.lock:
            if pool_name in self.pools:
                logger.warning(f"资源池已存在: {pool_name}")
                return self.pools[pool_name]
            
            pool = ResourcePool(
                resource_type=resource_type,
                factory=factory,
                min_size=min_size,
                max_size=max_size,
                **kwargs
            )
            
            self.pools[pool_name] = pool
            logger.info(f"创建资源池: {pool_name}")
            
            return pool
    
    def get_pool(self, pool_name: str) -> Optional[ResourcePool]:
        """获取资源池"""
        return self.pools.get(pool_name)
    
    def remove_pool(self, pool_name: str):
        """移除资源池"""
        with self.lock:
            if pool_name in self.pools:
                pool = self.pools[pool_name]
                
                # 停止清理任务
                if pool.cleanup_task:
                    pool.cleanup_task.cancel()
                
                # 销毁所有资源
                for resource_id in list(pool.resources.keys()):
                    pool._destroy_resource(resource_id)
                
                del self.pools[pool_name]
                logger.info(f"移除资源池: {pool_name}")
    
    async def start_all_cleanup(self):
        """启动所有资源池的清理任务"""
        for pool in self.pools.values():
            await pool.start_cleanup()
    
    async def stop_all_cleanup(self):
        """停止所有资源池的清理任务"""
        for pool in self.pools.values():
            await pool.stop_cleanup()
    
    async def optimize_pool_sizes(self) -> bool:
        """优化所有资源池大小"""
        try:
            optimized = False
            
            for pool_name, pool in self.pools.items():
                stats = pool.get_stats()
                utilization = stats["utilization"]
                
                # 根据利用率调整池大小
                if utilization > 0.8:  # 高利用率，增加资源
                    new_max = min(pool.max_size + 2, pool.max_size * 2)
                    if new_max > pool.max_size:
                        pool.resize(pool.min_size, new_max)
                        optimized = True
                        logger.info(f"增加资源池大小: {pool_name}, 新最大值: {new_max}")
                
                elif utilization < 0.3 and pool.max_size > pool.min_size:  # 低利用率，减少资源
                    new_max = max(pool.max_size - 1, pool.min_size)
                    if new_max < pool.max_size:
                        pool.resize(pool.min_size, new_max)
                        optimized = True
                        logger.info(f"减少资源池大小: {pool_name}, 新最大值: {new_max}")
            
            return optimized
            
        except Exception as e:
            logger.error(f"优化资源池大小失败: {e}")
            return False
    
    async def cleanup_idle_resources(self) -> int:
        """清理所有空闲资源"""
        try:
            total_cleaned = 0
            
            for pool in self.pools.values():
                await pool._cleanup_expired_resources()
                # 统计清理的资源数量（简化实现）
                total_cleaned += 1
            
            logger.info(f"清理空闲资源完成: {total_cleaned} 个池")
            return total_cleaned
            
        except Exception as e:
            logger.error(f"清理空闲资源失败: {e}")
            return 0
    
    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有资源池统计"""
        stats = {}
        total_resources = 0
        total_utilization = 0
        
        for pool_name, pool in self.pools.items():
            pool_stats = pool.get_stats()
            stats[pool_name] = pool_stats
            total_resources += pool_stats["total_resources"]
            total_utilization += pool_stats["utilization"]
        
        return {
            "pools": stats,
            "summary": {
                "total_pools": len(self.pools),
                "total_resources": total_resources,
                "average_utilization": total_utilization / len(self.pools) if self.pools else 0
            }
        }


# 全局资源池管理器实例
resource_pool_manager = ResourcePoolManager()


# 便捷函数
def create_connection_pool(pool_name: str, connection_factory: Callable, **kwargs):
    """创建连接池"""
    return resource_pool_manager.create_pool(
        pool_name=pool_name,
        resource_type="connection",
        factory=connection_factory,
        **kwargs
    )


def create_thread_pool(pool_name: str, min_threads: int = 2, max_threads: int = 10):
    """创建线程池"""
    import threading
    
    def thread_factory():
        return threading.Thread()
    
    return resource_pool_manager.create_pool(
        pool_name=pool_name,
        resource_type="thread",
        factory=thread_factory,
        min_size=min_threads,
        max_size=max_threads
    )