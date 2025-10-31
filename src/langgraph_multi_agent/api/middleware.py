"""API中间件"""

import time
import logging
import json
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
import asyncio

from fastapi import Request, Response, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import jwt

from .models import ErrorResponse

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """日志中间件"""
    
    async def dispatch(self, request: Request, call_next):
        """处理请求日志"""
        start_time = time.time()
        
        # 记录请求信息
        logger.info(
            f"请求开始 - {request.method} {request.url.path} "
            f"来源: {request.client.host if request.client else 'unknown'}"
        )
        
        try:
            response = await call_next(request)
            
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 记录响应信息
            logger.info(
                f"请求完成 - {request.method} {request.url.path} "
                f"状态: {response.status_code} "
                f"耗时: {process_time:.3f}s"
            )
            
            # 添加处理时间到响应头
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"请求异常 - {request.method} {request.url.path} "
                f"错误: {str(e)} "
                f"耗时: {process_time:.3f}s"
            )
            raise


class MetricsMiddleware(BaseHTTPMiddleware):
    """指标收集中间件"""
    
    def __init__(self, app, app_state):
        super().__init__(app)
        self.app_state = app_state
        self.request_times = []
        self.max_request_times = 1000  # 保留最近1000个请求的时间
    
    async def dispatch(self, request: Request, call_next):
        """收集请求指标"""
        start_time = time.time()
        
        # 增加请求计数
        self.app_state.increment_request_count()
        
        try:
            response = await call_next(request)
            
            # 记录响应时间
            process_time = time.time() - start_time
            self.request_times.append(process_time)
            
            # 保持列表大小
            if len(self.request_times) > self.max_request_times:
                self.request_times = self.request_times[-self.max_request_times:]
            
            # 添加指标到响应头
            response.headers["X-Request-ID"] = str(self.app_state.request_count)
            response.headers["X-Process-Time"] = f"{process_time:.3f}"
            
            return response
            
        except Exception as e:
            # 记录错误
            self.app_state.increment_error_count()
            raise
    
    def get_average_response_time(self) -> float:
        """获取平均响应时间"""
        if not self.request_times:
            return 0.0
        return sum(self.request_times) / len(self.request_times)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """认证中间件"""
    
    def __init__(self, app, secret_key: str, algorithm: str = "HS256"):
        super().__init__(app)
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.security = HTTPBearer()
        
        # 不需要认证的路径
        self.public_paths = {
            "/", "/health", "/version", "/docs", "/redoc", "/openapi.json"
        }
    
    async def dispatch(self, request: Request, call_next):
        """处理认证"""
        # 检查是否为公开路径
        if request.url.path in self.public_paths:
            return await call_next(request)
        
        # 检查是否为静态文件
        if request.url.path.startswith("/static/"):
            return await call_next(request)
        
        try:
            # 获取Authorization头
            authorization = request.headers.get("Authorization")
            if not authorization:
                return self._unauthorized_response("缺少Authorization头")
            
            # 验证Bearer token
            if not authorization.startswith("Bearer "):
                return self._unauthorized_response("无效的Authorization格式")
            
            token = authorization.split(" ")[1]
            
            # 验证JWT token
            try:
                payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
                
                # 检查token是否过期
                if "exp" in payload:
                    if datetime.utcnow().timestamp() > payload["exp"]:
                        return self._unauthorized_response("Token已过期")
                
                # 将用户信息添加到请求中
                request.state.user = payload
                
            except jwt.InvalidTokenError as e:
                return self._unauthorized_response(f"无效的token: {str(e)}")
            
            return await call_next(request)
            
        except Exception as e:
            logger.error(f"认证中间件错误: {e}")
            return self._unauthorized_response("认证失败")
    
    def _unauthorized_response(self, message: str) -> JSONResponse:
        """返回未授权响应"""
        return JSONResponse(
            status_code=401,
            content=ErrorResponse(
                error_code="UNAUTHORIZED",
                error_message=message
            ).dict()
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """限流中间件"""
    
    def __init__(self, app, requests_per_minute: int = 100, window_size: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_size = window_size
        self.client_requests: Dict[str, list] = {}
        
        # 清理任务
        asyncio.create_task(self._cleanup_old_requests())
    
    async def dispatch(self, request: Request, call_next):
        """处理限流"""
        # 获取客户端IP
        client_ip = self._get_client_ip(request)
        
        # 检查限流
        if not self._is_request_allowed(client_ip):
            return self._rate_limit_response()
        
        # 记录请求
        self._record_request(client_ip)
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP"""
        # 检查X-Forwarded-For头（代理情况）
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # 检查X-Real-IP头
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # 使用直接连接的IP
        return request.client.host if request.client else "unknown"
    
    def _is_request_allowed(self, client_ip: str) -> bool:
        """检查是否允许请求"""
        current_time = time.time()
        
        if client_ip not in self.client_requests:
            return True
        
        # 过滤时间窗口内的请求
        window_start = current_time - self.window_size
        recent_requests = [
            req_time for req_time in self.client_requests[client_ip]
            if req_time > window_start
        ]
        
        return len(recent_requests) < self.requests_per_minute
    
    def _record_request(self, client_ip: str):
        """记录请求"""
        current_time = time.time()
        
        if client_ip not in self.client_requests:
            self.client_requests[client_ip] = []
        
        self.client_requests[client_ip].append(current_time)
    
    def _rate_limit_response(self) -> JSONResponse:
        """返回限流响应"""
        return JSONResponse(
            status_code=429,
            content=ErrorResponse(
                error_code="RATE_LIMIT_EXCEEDED",
                error_message=f"请求频率超限，每分钟最多{self.requests_per_minute}次请求"
            ).dict(),
            headers={
                "Retry-After": str(self.window_size),
                "X-RateLimit-Limit": str(self.requests_per_minute),
                "X-RateLimit-Window": str(self.window_size)
            }
        )
    
    async def _cleanup_old_requests(self):
        """清理旧请求记录"""
        while True:
            try:
                await asyncio.sleep(300)  # 每5分钟清理一次
                
                current_time = time.time()
                cutoff_time = current_time - self.window_size * 2  # 保留2个窗口的数据
                
                for client_ip in list(self.client_requests.keys()):
                    # 过滤掉过期的请求
                    self.client_requests[client_ip] = [
                        req_time for req_time in self.client_requests[client_ip]
                        if req_time > cutoff_time
                    ]
                    
                    # 如果没有请求记录，删除客户端
                    if not self.client_requests[client_ip]:
                        del self.client_requests[client_ip]
                
                logger.debug(f"清理限流记录，当前客户端数: {len(self.client_requests)}")
                
            except Exception as e:
                logger.error(f"清理限流记录失败: {e}")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全头中间件"""
    
    async def dispatch(self, request: Request, call_next):
        """添加安全头"""
        response = await call_next(request)
        
        # 添加安全头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response


class CompressionMiddleware(BaseHTTPMiddleware):
    """压缩中间件"""
    
    def __init__(self, app, minimum_size: int = 1024):
        super().__init__(app)
        self.minimum_size = minimum_size
    
    async def dispatch(self, request: Request, call_next):
        """处理响应压缩"""
        response = await call_next(request)
        
        # 检查是否支持gzip压缩
        accept_encoding = request.headers.get("Accept-Encoding", "")
        if "gzip" not in accept_encoding:
            return response
        
        # 检查响应大小
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) < self.minimum_size:
            return response
        
        # 检查内容类型
        content_type = response.headers.get("Content-Type", "")
        compressible_types = [
            "application/json",
            "application/javascript",
            "text/html",
            "text/css",
            "text/plain",
            "text/xml"
        ]
        
        if not any(ct in content_type for ct in compressible_types):
            return response
        
        # 添加压缩头（实际压缩由ASGI服务器处理）
        response.headers["Content-Encoding"] = "gzip"
        response.headers["Vary"] = "Accept-Encoding"
        
        return response


def create_jwt_token(payload: Dict[str, Any], secret_key: str, expires_in: int = 3600) -> str:
    """创建JWT token"""
    # 添加过期时间
    payload["exp"] = datetime.utcnow().timestamp() + expires_in
    payload["iat"] = datetime.utcnow().timestamp()
    
    return jwt.encode(payload, secret_key, algorithm="HS256")


def verify_jwt_token(token: str, secret_key: str) -> Optional[Dict[str, Any]]:
    """验证JWT token"""
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        return payload
    except jwt.InvalidTokenError:
        return None