"""
测试辅助工具函数
"""

import time
import asyncio
import functools
from typing import Any, Callable, Dict, List, Optional, Tuple
from datetime import datetime, timedelta


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """重试装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = delay * (backoff ** attempt)
                        await asyncio.sleep(wait_time)
                    else:
                        raise last_exception
            
            raise last_exception
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = delay * (backoff ** attempt)
                        time.sleep(wait_time)
                    else:
                        raise last_exception
            
            raise last_exception
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def timeout_after(seconds: float):
    """超时装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                raise TimeoutError(f"Function {func.__name__} timed out after {seconds} seconds")
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            
            if elapsed > seconds:
                raise TimeoutError(f"Function {func.__name__} took {elapsed:.2f}s, exceeded {seconds}s timeout")
            
            return result
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def measure_time(func: Callable) -> Callable:
    """测量执行时间装饰器"""
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            return result, time.time() - start_time
        except Exception as e:
            raise e
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            return result, time.time() - start_time
        except Exception as e:
            raise e
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def safe_execute(func: Callable, default_value: Any = None, log_errors: bool = True) -> Tuple[bool, Any, Optional[str]]:
    """安全执行函数，返回(成功标志, 结果, 错误信息)"""
    try:
        if asyncio.iscoroutinefunction(func):
            # 对于异步函数，需要在事件循环中执行
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(func())
        else:
            result = func()
        return True, result, None
    except Exception as e:
        error_msg = str(e)
        if log_errors:
            print(f"Error in {func.__name__}: {error_msg}")
        return False, default_value, error_msg


def format_duration(seconds: float) -> str:
    """格式化持续时间"""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs:.1f}s"


def format_bytes(bytes_count: int) -> str:
    """格式化字节数"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.1f}{unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f}PB"


def generate_test_id() -> str:
    """生成测试ID"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"test_{timestamp}_{int(time.time() * 1000) % 10000}"


def validate_url(url: str) -> bool:
    """验证URL格式"""
    import re
    pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return pattern.match(url) is not None


def wait_for_condition(condition_func: Callable[[], bool], 
                      timeout: float = 30.0, 
                      check_interval: float = 1.0) -> bool:
    """等待条件满足"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            if condition_func():
                return True
        except Exception:
            pass
        
        time.sleep(check_interval)
    
    return False


async def async_wait_for_condition(condition_func: Callable[[], bool], 
                                 timeout: float = 30.0, 
                                 check_interval: float = 1.0) -> bool:
    """异步等待条件满足"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            if asyncio.iscoroutinefunction(condition_func):
                if await condition_func():
                    return True
            else:
                if condition_func():
                    return True
        except Exception:
            pass
        
        await asyncio.sleep(check_interval)
    
    return False


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """将列表分块"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def merge_dicts(*dicts: Dict[str, Any]) -> Dict[str, Any]:
    """合并多个字典"""
    result = {}
    for d in dicts:
        result.update(d)
    return result


def deep_merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """深度合并字典"""
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result