"""LangGraph多智能体系统主启动文件"""

import logging
import asyncio
from typing import Dict, Any, Optional

from .api.app import create_app, run_app
from .workflow.multi_agent_workflow import MultiAgentWorkflow
from .workflow.error_recovery import ErrorRecoveryHandler
from .integration.error_integration import IntegratedErrorHandler
from .utils.config import get_config
from .utils.logging import setup_logging

logger = logging.getLogger(__name__)


class MultiAgentSystem:
    """多智能体系统主类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or get_config()
        self.workflows: Dict[str, MultiAgentWorkflow] = {}
        self.error_handler: Optional[IntegratedErrorHandler] = None
        self.app = None
        
        # 设置日志
        setup_logging(self.config.get("log_level", "INFO"))
        
        logger.info("多智能体系统初始化")
    
    def initialize_error_handling(self):
        """初始化错误处理"""
        try:
            error_recovery_handler = ErrorRecoveryHandler()
            self.error_handler = IntegratedErrorHandler(error_recovery_handler)
            logger.info("错误处理系统初始化完成")
        except Exception as e:
            logger.error(f"错误处理系统初始化失败: {e}")
            raise
    
    def create_workflow(
        self, 
        workflow_id: str, 
        execution_mode: str = "adaptive"
    ) -> MultiAgentWorkflow:
        """创建工作流"""
        try:
            from .workflow.multi_agent_workflow import WorkflowExecutionMode
            
            workflow = MultiAgentWorkflow(
                workflow_id=workflow_id,
                execution_mode=WorkflowExecutionMode(execution_mode)
            )
            
            self.workflows[workflow_id] = workflow
            logger.info(f"工作流创建成功: {workflow_id}")
            
            return workflow
            
        except Exception as e:
            logger.error(f"工作流创建失败: {e}")
            raise
    
    def start_api_server(
        self, 
        host: str = "0.0.0.0", 
        port: int = 8000, 
        reload: bool = False
    ):
        """启动API服务器"""
        try:
            logger.info(f"启动API服务器: {host}:{port}")
            run_app(host=host, port=port, reload=reload)
        except Exception as e:
            logger.error(f"API服务器启动失败: {e}")
            raise
    
    async def start_system(self):
        """启动系统"""
        try:
            # 初始化错误处理
            self.initialize_error_handling()
            
            # 启动健康监控
            if self.error_handler:
                await self.error_handler.start_health_monitoring()
            
            logger.info("多智能体系统启动完成")
            
        except Exception as e:
            logger.error(f"系统启动失败: {e}")
            raise
    
    async def stop_system(self):
        """停止系统"""
        try:
            # 停止健康监控
            if self.error_handler:
                self.error_handler.stop_health_monitoring()
            
            # 清理工作流
            for workflow_id, workflow in self.workflows.items():
                logger.info(f"清理工作流: {workflow_id}")
            
            logger.info("多智能体系统停止完成")
            
        except Exception as e:
            logger.error(f"系统停止失败: {e}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="LangGraph多智能体系统")
    parser.add_argument("--host", default="0.0.0.0", help="API服务器主机")
    parser.add_argument("--port", type=int, default=8000, help="API服务器端口")
    parser.add_argument("--reload", action="store_true", help="开发模式重载")
    parser.add_argument("--log-level", default="INFO", help="日志级别")
    
    args = parser.parse_args()
    
    # 创建系统实例
    config = {
        "log_level": args.log_level,
        "api_host": args.host,
        "api_port": args.port
    }
    
    system = MultiAgentSystem(config)
    
    try:
        # 启动系统
        asyncio.run(system.start_system())
        
        # 启动API服务器
        system.start_api_server(
            host=args.host,
            port=args.port,
            reload=args.reload
        )
        
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭系统...")
        asyncio.run(system.stop_system())
    except Exception as e:
        logger.error(f"系统运行失败: {e}")
        raise


if __name__ == "__main__":
    main()