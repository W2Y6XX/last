"""并发执行器 - 智能并发控制和任务调度"""

import logging
import asyncio
import threading
from typing import Dict, Any, Optional, List, Callable, Awaitable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import queue
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, Future
import psutil

logger = logging.getLogger(__name__)


class ExecutionMode(str, Enum):
    """执行模式"""
    THREAD = "thread"
    PROCESS = "process"
    ASYNC = "async"
    ADAPTIVE = "adaptive"


class TaskPriority(int, Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class TaskInfo:
    """任务信息"""
    task_id: str
    func: Callable
    args: tuple
    kwargs: dict
    priority: TaskPriority
    created_at: datetime
    timeout: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __lt__(self, other):
        """用于优先级队列排序"""
        return (self.priority.value, self.created_at) > (other.priority.value, other.created_at)


class ConcurrentExecutor:
    """并发执行器"""
    
    def __init__(
        self,
        max_workers: Optional[int] = None,
        execution_mode: ExecutionMode = ExecutionMode.ADAPTIVE,
        enable_auto_scaling: bool = True
    ):
        self.max_workers = max_workers or psutil.cpu_count()
        self.execution_mode = execution_mode
        self.enable_auto_scaling = enable_auto_scaling
        
        # 执行器
        self.thread_executor: Optional[ThreadPoolExecutor] = None
        self.process_executor: Optional[ProcessPoolExecutor] = None
        
        # 任务队列
        self.task_queue: queue.PriorityQueue = queue.PriorityQueue()
        self.running_tasks: Dict[str, Future] = {}
        
        # 统计信息
        self.stats = {
            "submitted": 0,
            "completed": 0,
            "failed": 0,
            "timeout": 0,
            "retried": 0
        }
        
        # 性能监控
        self.performance_history: List[Dict[str, Any]] = []
        self.current_load = 0.0
        
        # 运行状态
        self.is_running = False
        self.worker_threads: List[threading.Thread] = []
        
        self._initialize_executors()
        
        logger.info(f"并发执行器初始化完成，最大工作线程: {self.max_workers}")
    
    def _initialize_executors(self):
        """初始化执行器"""
        if self.execution_mode in [ExecutionMode.THREAD, ExecutionMode.ADAPTIVE]:
            self.thread_executor = ThreadPoolExecutor(
                max_workers=self.max_workers,
                thread_name_prefix="ConcurrentExecutor"
            )
        
        if self.execution_mode in [ExecutionMode.PROCESS, ExecutionMode.ADAPTIVE]:
            # 进程池使用较少的工作进程
            process_workers = min(self.max_workers, psutil.cpu_count())
            self.process_executor = ProcessPoolExecutor(max_workers=process_workers)
    
    async def start(self):
        """启动执行器"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # 启动工作线程
        for i in range(min(4, self.max_workers)):  # 启动4个工作线程
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"ConcurrentWorker-{i}",
                daemon=True
            )
            worker.start()
            self.worker_threads.append(worker)
        
        # 启动监控任务
        asyncio.create_task(self._monitoring_loop())
        
        logger.info("并发执行器已启动")
    
    async def stop(self):
        """停止执行器"""
        self.is_running = False
        
        # 等待所有任务完成
        await self._wait_for_completion()
        
        # 关闭执行器
        if self.thread_executor:
            self.thread_executor.shutdown(wait=True)
        
        if self.process_executor:
            self.process_executor.shutdown(wait=True)
        
        logger.info("并发执行器已停止")
    
    def submit_task(
        self,
        func: Callable,
        *args,
        task_id: Optional[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: Optional[float] = None,
        max_retries: int = 3,
        **kwargs
    ) -> str:
        """提交任务"""
        task_id = task_id or f"task_{int(time.time() * 1000000)}"
        
        task_info = TaskInfo(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            created_at=datetime.now(),
            timeout=timeout,
            max_retries=max_retries
        )
        
        self.task_queue.put(task_info)
        self.stats["submitted"] += 1
        
        logger.debug(f"提交任务: {task_id}, 优先级: {priority.name}")
        return task_id
    
    async def submit_async_task(
        self,
        coro: Awaitable,
        task_id: Optional[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: Optional[float] = None
    ) -> str:
        """提交异步任务"""
        task_id = task_id or f"async_task_{int(time.time() * 1000000)}"
        
        # 包装协程为可调用函数
        def async_wrapper():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()
        
        return self.submit_task(
            async_wrapper,
            task_id=task_id,
            priority=priority,
            timeout=timeout
        )
    
    def _worker_loop(self):
        """工作线程循环"""
        while self.is_running:
            try:
                # 获取任务
                try:
                    task_info = self.task_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # 执行任务
                self._execute_task(task_info)
                
            except Exception as e:
                logger.error(f"工作线程异常: {e}")
    
    def _execute_task(self, task_info: TaskInfo):
        """执行任务"""
        try:
            start_time = time.time()
            
            # 选择执行器
            executor = self._select_executor(task_info)
            
            # 提交到执行器
            future = executor.submit(task_info.func, *task_info.args, **task_info.kwargs)
            self.running_tasks[task_info.task_id] = future
            
            try:
                # 等待结果
                result = future.result(timeout=task_info.timeout)
                
                execution_time = time.time() - start_time
                self.stats["completed"] += 1
                
                logger.debug(f"任务完成: {task_info.task_id}, 耗时: {execution_time:.3f}s")
                
                # 记录性能数据
                self._record_performance(task_info, execution_time, True)
                
            except TimeoutError:
                future.cancel()
                self.stats["timeout"] += 1
                logger.warning(f"任务超时: {task_info.task_id}")
                
                # 重试任务
                if task_info.retry_count < task_info.max_retries:
                    self._retry_task(task_info)
                
            except Exception as e:
                self.stats["failed"] += 1
                logger.error(f"任务执行失败: {task_info.task_id}, 错误: {e}")
                
                # 重试任务
                if task_info.retry_count < task_info.max_retries:
                    self._retry_task(task_info)
            
            finally:
                # 清理运行任务记录
                if task_info.task_id in self.running_tasks:
                    del self.running_tasks[task_info.task_id]
        
        except Exception as e:
            logger.error(f"执行任务异常: {e}")
    
    def _select_executor(self, task_info: TaskInfo) -> Union[ThreadPoolExecutor, ProcessPoolExecutor]:
        """选择执行器"""
        if self.execution_mode == ExecutionMode.THREAD:
            return self.thread_executor
        elif self.execution_mode == ExecutionMode.PROCESS:
            return self.process_executor
        elif self.execution_mode == ExecutionMode.ADAPTIVE:
            # 自适应选择
            if self._should_use_process_executor(task_info):
                return self.process_executor
            else:
                return self.thread_executor
        else:
            return self.thread_executor
    
    def _should_use_process_executor(self, task_info: TaskInfo) -> bool:
        """判断是否应该使用进程执行器"""
        # 基于任务特征和当前负载决定
        
        # 高优先级任务使用线程执行器（更快启动）
        if task_info.priority == TaskPriority.CRITICAL:
            return False
        
        # CPU密集型任务使用进程执行器
        if hasattr(task_info.func, '__name__'):
            func_name = task_info.func.__name__
            cpu_intensive_keywords = ['compute', 'calculate', 'process', 'analyze']
            if any(keyword in func_name.lower() for keyword in cpu_intensive_keywords):
                return True
        
        # 当前负载高时使用进程执行器
        if self.current_load > 0.8:
            return True
        
        return False
    
    def _retry_task(self, task_info: TaskInfo):
        """重试任务"""
        task_info.retry_count += 1
        task_info.created_at = datetime.now()  # 更新创建时间
        
        self.task_queue.put(task_info)
        self.stats["retried"] += 1
        
        logger.info(f"重试任务: {task_info.task_id}, 第 {task_info.retry_count} 次")
    
    def _record_performance(self, task_info: TaskInfo, execution_time: float, success: bool):
        """记录性能数据"""
        performance_data = {
            "task_id": task_info.task_id,
            "execution_time": execution_time,
            "success": success,
            "priority": task_info.priority.value,
            "timestamp": datetime.now(),
            "retry_count": task_info.retry_count
        }
        
        self.performance_history.append(performance_data)
        
        # 保持历史记录大小
        if len(self.performance_history) > 1000:
            self.performance_history = self.performance_history[-1000:]
    
    async def _monitoring_loop(self):
        """监控循环"""
        while self.is_running:
            try:
                await asyncio.sleep(30)  # 每30秒监控一次
                
                # 更新当前负载
                self._update_current_load()
                
                # 自动调整并发级别
                if self.enable_auto_scaling:
                    await self._auto_scale()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"监控循环异常: {e}")
    
    def _update_current_load(self):
        """更新当前负载"""
        try:
            # 基于运行任务数和队列大小计算负载
            running_count = len(self.running_tasks)
            queue_size = self.task_queue.qsize()
            
            # 负载 = (运行任务数 + 队列大小) / 最大工作线程数
            self.current_load = (running_count + queue_size) / self.max_workers
            
            # 限制在0-1之间
            self.current_load = min(1.0, max(0.0, self.current_load))
            
        except Exception as e:
            logger.error(f"更新负载失败: {e}")
    
    async def _auto_scale(self):
        """自动扩缩容"""
        try:
            current_workers = len(self.worker_threads)
            
            # 高负载时增加工作线程
            if self.current_load > 0.8 and current_workers < self.max_workers:
                new_worker = threading.Thread(
                    target=self._worker_loop,
                    name=f"ConcurrentWorker-{current_workers}",
                    daemon=True
                )
                new_worker.start()
                self.worker_threads.append(new_worker)
                
                logger.info(f"增加工作线程，当前: {len(self.worker_threads)}")
            
            # 低负载时减少工作线程（简化实现，实际中需要更复杂的逻辑）
            elif self.current_load < 0.3 and current_workers > 2:
                # 这里只是标记，实际减少线程需要更复杂的实现
                logger.debug("负载较低，考虑减少工作线程")
            
        except Exception as e:
            logger.error(f"自动扩缩容失败: {e}")
    
    async def _wait_for_completion(self, timeout: float = 30.0):
        """等待所有任务完成"""
        start_time = time.time()
        
        while self.running_tasks and (time.time() - start_time) < timeout:
            await asyncio.sleep(0.1)
        
        # 取消剩余任务
        for future in self.running_tasks.values():
            future.cancel()
    
    def get_task_status(self, task_id: str) -> Optional[str]:
        """获取任务状态"""
        if task_id in self.running_tasks:
            future = self.running_tasks[task_id]
            if future.done():
                if future.cancelled():
                    return "cancelled"
                elif future.exception():
                    return "failed"
                else:
                    return "completed"
            else:
                return "running"
        
        return None
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self.running_tasks:
            future = self.running_tasks[task_id]
            return future.cancel()
        
        return False
    
    async def adjust_concurrency_level(self) -> bool:
        """调整并发级别"""
        try:
            # 基于性能历史调整
            if len(self.performance_history) < 10:
                return False
            
            recent_performance = self.performance_history[-10:]
            avg_execution_time = sum(p["execution_time"] for p in recent_performance) / len(recent_performance)
            success_rate = sum(1 for p in recent_performance if p["success"]) / len(recent_performance)
            
            # 如果性能不佳，调整并发级别
            if avg_execution_time > 5.0 or success_rate < 0.8:
                # 减少并发
                new_max_workers = max(2, int(self.max_workers * 0.8))
                if new_max_workers != self.max_workers:
                    self.max_workers = new_max_workers
                    logger.info(f"降低并发级别: {self.max_workers}")
                    return True
            
            elif avg_execution_time < 1.0 and success_rate > 0.95:
                # 增加并发
                new_max_workers = min(psutil.cpu_count() * 2, int(self.max_workers * 1.2))
                if new_max_workers != self.max_workers:
                    self.max_workers = new_max_workers
                    logger.info(f"提高并发级别: {self.max_workers}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"调整并发级别失败: {e}")
            return False
    
    async def optimize_task_queue(self) -> bool:
        """优化任务队列"""
        try:
            # 清理已完成的任务引用
            completed_tasks = [
                task_id for task_id, future in self.running_tasks.items()
                if future.done()
            ]
            
            for task_id in completed_tasks:
                del self.running_tasks[task_id]
            
            if completed_tasks:
                logger.debug(f"清理已完成任务: {len(completed_tasks)} 个")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"优化任务队列失败: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "stats": self.stats.copy(),
            "current_load": self.current_load,
            "running_tasks": len(self.running_tasks),
            "queue_size": self.task_queue.qsize(),
            "worker_threads": len(self.worker_threads),
            "max_workers": self.max_workers,
            "execution_mode": self.execution_mode.value,
            "performance_history_size": len(self.performance_history)
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        if not self.performance_history:
            return {"error": "没有性能数据"}
        
        recent_data = self.performance_history[-50:]  # 最近50个任务
        
        execution_times = [p["execution_time"] for p in recent_data]
        success_count = sum(1 for p in recent_data if p["success"])
        
        return {
            "total_tasks": len(recent_data),
            "success_rate": success_count / len(recent_data),
            "avg_execution_time": sum(execution_times) / len(execution_times),
            "min_execution_time": min(execution_times),
            "max_execution_time": max(execution_times),
            "current_load": self.current_load,
            "queue_backlog": self.task_queue.qsize()
        }