"""FastAPI应用程序主文件"""

import logging
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import uvicorn

from .models import ErrorResponse, ApiResponse
from .routes import tasks, agents, workflows, system, websocket, mvp2, llm_configs, meta_agent
from .websocket_mvp2 import handle_mvp2_websocket
from .middleware import (
    LoggingMiddleware,
    AuthenticationMiddleware,
    RateLimitMiddleware,
    MetricsMiddleware
)
from ..workflow.multi_agent_workflow import MultiAgentWorkflow
from ..workflow.error_recovery import ErrorRecoveryHandler
from ..integration.error_integration import IntegratedErrorHandler
from ..utils.config import get_config

logger = logging.getLogger(__name__)


class ApplicationState:
    """应用程序状态管理"""
    
    def __init__(self):
        self.workflows: Dict[str, MultiAgentWorkflow] = {}
        self.error_handler: Optional[IntegratedErrorHandler] = None
        self.startup_time = datetime.now()
        self.request_count = 0
        self.error_count = 0
        self.is_healthy = True
        self.shutdown_requested = False
    
    def increment_request_count(self):
        """增加请求计数"""
        self.request_count += 1
    
    def increment_error_count(self):
        """增加错误计数"""
        self.error_count += 1
    
    def get_uptime_seconds(self) -> int:
        """获取运行时间"""
        return int((datetime.now() - self.startup_time).total_seconds())
    
    def get_error_rate(self) -> float:
        """获取错误率"""
        if self.request_count == 0:
            return 0.0
        return self.error_count / self.request_count


# 全局应用状态
app_state = ApplicationState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用程序生命周期管理"""
    # 启动时的初始化
    logger.info("启动多智能体工作流API服务")
    
    try:
        # 初始化错误处理器
        error_recovery_handler = ErrorRecoveryHandler()
        app_state.error_handler = IntegratedErrorHandler(error_recovery_handler)
        
        # 启动健康监控
        await app_state.error_handler.start_health_monitoring()
        
        logger.info("API服务启动完成")
        
    except Exception as e:
        logger.error(f"API服务启动失败: {e}")
        app_state.is_healthy = False
        raise
    
    yield
    
    # 关闭时的清理
    logger.info("关闭多智能体工作流API服务")
    
    try:
        app_state.shutdown_requested = True
        
        # 停止健康监控
        if app_state.error_handler:
            app_state.error_handler.stop_health_monitoring()
        
        # 清理工作流
        for workflow in app_state.workflows.values():
            if workflow.status.value in ["running", "paused"]:
                logger.info(f"正在关闭工作流: {workflow.workflow_id}")
        
        logger.info("API服务关闭完成")
        
    except Exception as e:
        logger.error(f"API服务关闭失败: {e}")


def create_app(config: Optional[Dict[str, Any]] = None) -> FastAPI:
    """创建FastAPI应用程序"""
    
    # 获取配置
    app_config = config or get_config()
    
    # 创建FastAPI应用
    app = FastAPI(
        title="LangGraph多智能体工作流API",
        description="基于LangGraph的多智能体协作工作流系统API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )
    
    # 配置CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_config.get("cors_origins", ["*"]),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 配置可信主机
    if app_config.get("trusted_hosts"):
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=app_config["trusted_hosts"]
        )
    
    # 添加自定义中间件
    app.add_middleware(MetricsMiddleware, app_state=app_state)
    app.add_middleware(LoggingMiddleware)
    
    # 添加认证中间件（如果启用）
    if app_config.get("enable_auth", False):
        app.add_middleware(
            AuthenticationMiddleware,
            secret_key=app_config.get("auth_secret_key", "default-secret")
        )
    
    # 添加限流中间件（如果启用）
    if app_config.get("enable_rate_limit", False):
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=app_config.get("rate_limit_rpm", 100)
        )
    
    # 注册路由
    app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["任务管理"])
    app.include_router(agents.router, prefix="/api/v1/agents", tags=["智能体管理"])
    app.include_router(workflows.router, prefix="/api/v1/workflows", tags=["工作流管理"])
    app.include_router(system.router, prefix="/api/v1/system", tags=["系统管理"])
    app.include_router(websocket.router, prefix="/api/v1/ws", tags=["WebSocket"])
    app.include_router(mvp2.mvp2_router, tags=["MVP2前端"])
    app.include_router(llm_configs.router, prefix="/api/v1/llm/configs", tags=["大模型配置"])
    app.include_router(meta_agent.router, prefix="/api/v1/meta-agent", tags=["元智能体对话"])
    
    # MVP2 WebSocket端点
    @app.websocket("/api/v1/mvp2/ws")
    async def mvp2_websocket_endpoint(websocket):
        await handle_mvp2_websocket(websocket)
    
    # 全局异常处理器
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """HTTP异常处理"""
        app_state.increment_error_count()
        
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error_code=f"HTTP_{exc.status_code}",
                error_message=exc.detail,
                details={"path": str(request.url.path)}
            ).dict()
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """请求验证异常处理"""
        app_state.increment_error_count()
        
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error_code="VALIDATION_ERROR",
                error_message="请求参数验证失败",
                details={
                    "errors": exc.errors(),
                    "body": exc.body
                }
            ).dict()
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """通用异常处理"""
        app_state.increment_error_count()
        logger.error(f"未处理的异常: {exc}", exc_info=True)
        
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR",
                error_message="服务器内部错误",
                details={"path": str(request.url.path)}
            ).dict()
        )
    
    # 健康检查端点
    @app.get("/health", response_model=ApiResponse)
    async def health_check():
        """健康检查"""
        try:
            health_status = "healthy" if app_state.is_healthy else "unhealthy"
            
            return ApiResponse(
                success=app_state.is_healthy,
                message=f"服务状态: {health_status}",
                data={
                    "status": health_status,
                    "uptime_seconds": app_state.get_uptime_seconds(),
                    "request_count": app_state.request_count,
                    "error_count": app_state.error_count,
                    "error_rate": app_state.get_error_rate(),
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return ApiResponse(
                success=False,
                message="健康检查失败",
                error_code="HEALTH_CHECK_ERROR"
            )
    
    # 根路径
    @app.get("/", response_model=ApiResponse)
    async def root():
        """根路径"""
        return ApiResponse(
            success=True,
            message="LangGraph多智能体工作流API服务正在运行",
            data={
                "version": "1.0.0",
                "docs_url": "/docs",
                "health_url": "/health",
                "uptime_seconds": app_state.get_uptime_seconds()
            }
        )
    
    # 版本信息
    @app.get("/version", response_model=ApiResponse)
    async def version():
        """版本信息"""
        return ApiResponse(
            success=True,
            message="版本信息",
            data={
                "version": "1.0.0",
                "build_time": app_state.startup_time.isoformat(),
                "python_version": "3.8+",
                "fastapi_version": "0.104.0+",
                "features": [
                    "多智能体协作",
                    "LangGraph工作流",
                    "检查点恢复",
                    "错误处理",
                    "实时监控",
                    "WebSocket通信"
                ]
            }
        )
    
    return app


def run_app(
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool = False,
    log_level: str = "info",
    workers: int = 1
):
    """运行应用程序"""
    config = get_config()
    app = create_app(config)
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
        workers=workers,
        access_log=True
    )


if __name__ == "__main__":
    run_app()