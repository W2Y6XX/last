"""缓存管理器 - 智能缓存优化"""

import logging
import asyncio
import time
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import hashlib
import pickle
import threading
from collections import OrderedDict

logger = logging.getLogger(__name__)


class CacheStrategy(str, Enum):
    """缓存策略"""
    LRU = "lru"  # 最近最少使用
    LFU = "lfu"  # 最少使用频率
    TTL = "ttl"  # 生存时间
    ADAPTIVE = "adaptive"  # 自适应


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int
    ttl: Optional[int] = None
    size: int = 0
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return (datetime.now() - self.created_at).total_seconds() > self.ttl
    
    def get_age(self) -> float:
        """获取缓存年龄（秒）"""
        return (datetime.now() - self.created_at).total_seconds()
    
    def get_idle_time(self) -> float:
        """获取空闲时间（秒）"""
        return (datetime.now() - self.last_accessed).total_seconds()


class LRUCache:
    """LRU缓存实现"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                if entry.is_expired():
                    del self.cache[key]
                    return None
                
                # 更新访问信息
                entry.last_accessed = datetime.now()
                entry.access_count += 1
                
                # 移到末尾（最近使用）
                self.cache.move_to_end(key)
                return entry.value
            
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        with self.lock:
            now = datetime.now()
            
            # 计算值的大小
            try:
                size = len(pickle.dumps(value))
            except:
                size = 0
            
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                last_accessed=now,
                access_count=1,
                ttl=ttl,
                size=size
            )
            
            if key in self.cache:
                # 更新现有条目
                self.cache[key] = entry
                self.cache.move_to_end(key)
            else:
                # 添加新条目
                self.cache[key] = entry
                
                # 检查大小限制
                while len(self.cache) > self.max_size:
                    # 移除最旧的条目
                    oldest_key = next(iter(self.cache))
                    del self.cache[oldest_key]
            
            return True
    
    def delete(self, key: str) -> bool:
        """删除缓存条目"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self.lock:
            total_size = sum(entry.size for entry in self.cache.values())
            total_accesses = sum(entry.access_count for entry in self.cache.values())
            
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "total_memory": total_size,
                "total_accesses": total_accesses,
                "hit_rate": 0.0  # 需要额外跟踪
            }


class CacheManager:
    """缓存管理器"""
    
    def __init__(
        self,
        default_strategy: CacheStrategy = CacheStrategy.ADAPTIVE,
        max_cache_size: int = 10000,
        default_ttl: int = 3600,
        cleanup_interval: int = 300
    ):
        self.default_strategy = default_strategy
        self.max_cache_size = max_cache_size
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        
        # 多级缓存
        self.caches: Dict[str, LRUCache] = {
            "default": LRUCache(max_cache_size),
            "agents": LRUCache(1000),
            "workflows": LRUCache(500),
            "results": LRUCache(2000)
        }
        
        # 统计信息
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "cleanups": 0
        }
        
        # 运行状态
        self.is_running = False
        self.cleanup_task: Optional[asyncio.Task] = None
        
        logger.info(f"缓存管理器初始化完成，策略: {default_strategy.value}")
    
    async def start(self):
        """启动缓存管理器"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # 启动清理任务
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("缓存管理器已启动")
    
    async def stop(self):
        """停止缓存管理器"""
        self.is_running = False
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("缓存管理器已停止")
    
    def get(self, key: str, cache_name: str = "default") -> Optional[Any]:
        """获取缓存值"""
        try:
            cache = self.caches.get(cache_name, self.caches["default"])
            value = cache.get(key)
            
            if value is not None:
                self.stats["hits"] += 1
                logger.debug(f"缓存命中: {cache_name}/{key}")
            else:
                self.stats["misses"] += 1
                logger.debug(f"缓存未命中: {cache_name}/{key}")
            
            return value
            
        except Exception as e:
            logger.error(f"获取缓存失败: {e}")
            self.stats["misses"] += 1
            return None
    
    def set(
        self, 
        key: str, 
        value: Any, 
        cache_name: str = "default",
        ttl: Optional[int] = None
    ) -> bool:
        """设置缓存值"""
        try:
            cache = self.caches.get(cache_name, self.caches["default"])
            ttl = ttl or self.default_ttl
            
            success = cache.set(key, value, ttl)
            
            if success:
                self.stats["sets"] += 1
                logger.debug(f"缓存设置: {cache_name}/{key}")
            
            return success
            
        except Exception as e:
            logger.error(f"设置缓存失败: {e}")
            return False
    
    def delete(self, key: str, cache_name: str = "default") -> bool:
        """删除缓存条目"""
        try:
            cache = self.caches.get(cache_name, self.caches["default"])
            success = cache.delete(key)
            
            if success:
                self.stats["deletes"] += 1
                logger.debug(f"缓存删除: {cache_name}/{key}")
            
            return success
            
        except Exception as e:
            logger.error(f"删除缓存失败: {e}")
            return False
    
    def clear_cache(self, cache_name: Optional[str] = None):
        """清空缓存"""
        try:
            if cache_name:
                if cache_name in self.caches:
                    self.caches[cache_name].clear()
                    logger.info(f"清空缓存: {cache_name}")
            else:
                for cache in self.caches.values():
                    cache.clear()
                logger.info("清空所有缓存")
            
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")
    
    async def cleanup_expired(self) -> int:
        """清理过期缓存"""
        try:
            total_cleaned = 0
            
            for cache_name, cache in self.caches.items():
                cleaned = 0
                expired_keys = []
                
                with cache.lock:
                    for key, entry in cache.cache.items():
                        if entry.is_expired():
                            expired_keys.append(key)
                    
                    for key in expired_keys:
                        del cache.cache[key]
                        cleaned += 1
                
                total_cleaned += cleaned
                
                if cleaned > 0:
                    logger.debug(f"清理过期缓存 {cache_name}: {cleaned} 个")
            
            if total_cleaned > 0:
                self.stats["cleanups"] += 1
                logger.info(f"清理过期缓存完成: {total_cleaned} 个")
            
            return total_cleaned
            
        except Exception as e:
            logger.error(f"清理过期缓存失败: {e}")
            return 0
    
    async def optimize_cache_size(self) -> bool:
        """优化缓存大小"""
        try:
            optimized = False
            
            for cache_name, cache in self.caches.items():
                with cache.lock:
                    current_size = len(cache.cache)
                    
                    if current_size > cache.max_size * 0.9:  # 90%满
                        # 移除最少使用的条目
                        entries = list(cache.cache.items())
                        entries.sort(key=lambda x: (x[1].access_count, x[1].last_accessed))
                        
                        # 移除20%的条目
                        remove_count = int(current_size * 0.2)
                        for i in range(remove_count):
                            key, _ = entries[i]
                            del cache.cache[key]
                        
                        optimized = True
                        logger.info(f"优化缓存大小 {cache_name}: 移除 {remove_count} 个条目")
            
            return optimized
            
        except Exception as e:
            logger.error(f"优化缓存大小失败: {e}")
            return False
    
    async def _cleanup_loop(self):
        """清理循环"""
        while self.is_running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                # 清理过期缓存
                await self.cleanup_expired()
                
                # 优化缓存大小
                await self.optimize_cache_size()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"缓存清理循环失败: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        try:
            cache_stats = {}
            total_size = 0
            total_memory = 0
            
            for cache_name, cache in self.caches.items():
                stats = cache.get_stats()
                cache_stats[cache_name] = stats
                total_size += stats["size"]
                total_memory += stats["total_memory"]
            
            hit_rate = (
                self.stats["hits"] / (self.stats["hits"] + self.stats["misses"])
                if (self.stats["hits"] + self.stats["misses"]) > 0 else 0
            )
            
            return {
                "global_stats": {
                    **self.stats,
                    "hit_rate": hit_rate,
                    "total_size": total_size,
                    "total_memory": total_memory
                },
                "cache_stats": cache_stats,
                "is_running": self.is_running
            }
            
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {"error": str(e)}
    
    def get_cache_size(self) -> int:
        """获取总缓存大小"""
        return sum(len(cache.cache) for cache in self.caches.values())
    
    # 便捷方法
    def cache_agent_result(self, agent_id: str, input_hash: str, result: Any, ttl: int = 1800):
        """缓存智能体结果"""
        key = f"{agent_id}:{input_hash}"
        return self.set(key, result, "agents", ttl)
    
    def get_agent_result(self, agent_id: str, input_hash: str) -> Optional[Any]:
        """获取智能体结果缓存"""
        key = f"{agent_id}:{input_hash}"
        return self.get(key, "agents")
    
    def cache_workflow_result(self, workflow_id: str, result: Any, ttl: int = 3600):
        """缓存工作流结果"""
        return self.set(workflow_id, result, "workflows", ttl)
    
    def get_workflow_result(self, workflow_id: str) -> Optional[Any]:
        """获取工作流结果缓存"""
        return self.get(workflow_id, "workflows")
    
    def generate_cache_key(self, *args) -> str:
        """生成缓存键"""
        try:
            # 将参数序列化并生成哈希
            content = ":".join(str(arg) for arg in args)
            return hashlib.md5(content.encode()).hexdigest()
        except Exception as e:
            logger.error(f"生成缓存键失败: {e}")
            return str(hash(args))
    
    def warm_up_cache(self, cache_data: Dict[str, Any], cache_name: str = "default"):
        """预热缓存"""
        try:
            count = 0
            for key, value in cache_data.items():
                if self.set(key, value, cache_name):
                    count += 1
            
            logger.info(f"缓存预热完成: {cache_name}, {count} 个条目")
            
        except Exception as e:
            logger.error(f"缓存预热失败: {e}")
    
    def export_cache(self, cache_name: str = "default") -> Dict[str, Any]:
        """导出缓存数据"""
        try:
            cache = self.caches.get(cache_name)
            if not cache:
                return {}
            
            exported = {}
            with cache.lock:
                for key, entry in cache.cache.items():
                    if not entry.is_expired():
                        exported[key] = entry.value
            
            logger.info(f"导出缓存数据: {cache_name}, {len(exported)} 个条目")
            return exported
            
        except Exception as e:
            logger.error(f"导出缓存失败: {e}")
            return {}