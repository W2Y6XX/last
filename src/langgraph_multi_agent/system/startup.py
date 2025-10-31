"""系统启动管理器"""

import logging
import asyncio
import signal
import sys
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from .integration import SystemIntegrator
from .config_manager import ConfigManager
from ..llm import SiliconFlowClient, set_llm_client
from ..utils.logging import setup_logging
from ..api.app import create_app

logger = logging.getLogger(__name__)


class SystemStartup:
    """系统启动管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.get_config()
        self.integrator: Optional[SystemIntegrator] = None
        self.app = None
        self.startup_time: Optional[datetime] = None
        self.shutdown_requested = False
        
        # 设置日志
        setup_logging(
            level=self.config.logging.level,
            format_str=self.config.logging.format,
            file_path=self.config.logging.file_path,
            max_file_size=self.config.logging.max_file_size,
            backup_count=self.config.logging.backup_count,
            enable_console=self.config.logging.enable_console
        )
        
        logger.info("系统启动管理器初始化完成")
    
    async def startup(self) -> bool:
        """启动系统"""
        try:
            logger.info("=" * 60)
            logger.info("LangGraph多智能体系统启动")
            logger.info("=" * 60)
            
            self.startup_time = datetime.now()
            
            # 1. 显示配置信息
            self._display_config_info()
            
            # 2. 创建必要的目录
            self._create_directories()
            
            # 3. 初始化LLM客户端
            logger.info("初始化LLM客户端...")
            await self._initialize_llm_client()
            
            # 4. 初始化系统集成器
            logger.info("初始化系统集成器...")
            self.integrator = SystemIntegrator(self.config_manager.get_config().__dict__)
            
            # 5. 初始化系统组件
            logger.info("初始化系统组件...")
            success = await self.integrator.initialize_system()
            if not success:
                logger.error("系统组件初始化失败")
                return False
            
            # 6. 创建FastAPI应用
            logger.info("创建API应用...")
            self.app = create_app(self._get_api_config())
            
            # 7. 设置信号处理
            self._setup_signal_handlers()
            
            # 8. 显示启动信息
            self._display_startup_info()
            
            logger.info("系统启动完成")
            return True
            
        except Exception as e:
            logger.error(f"系统启动失败: {e}")
            return False
    
    async def _initialize_llm_client(self):
        """初始化LLM客户端"""
        try:
            config = self.config_manager.get_config()
            llm_config = config.llm
            
            # 创建硅基流动客户端
            client = SiliconFlowClient(
                api_key=llm_config.api_key,
                base_url=llm_config.base_url,
                model=llm_config.model,
                temperature=llm_config.temperature,
                max_tokens=llm_config.max_tokens,
                timeout=llm_config.timeout,
                max_retries=llm_config.max_retries
            )
            
            # 设置为全局客户端
            set_llm_client(client)
            
            logger.info(f"LLM客户端初始化完成: {llm_config.model}")
            
        except Exception as e:
            logger.error(f"LLM客户端初始化失败: {e}")
            raise
    
    def _display_config_info(self):
        """显示配置信息"""
        try:
            config_summary = self.config_manager.get_config_summary()
            
            logger.info("配置信息:")
            logger.info(f"  环境: {config_summary['environment']}")
            logger.info(f"  版本: {config_summary['version']}")
            logger.info(f"  调试模式: {config_summary['debug']}")
            logger.info(f"  API地址: {config_summary['api_host']}:{config_summary['api_port']}")
            logger.info(f"  数据库类型: {config_summary['database_type']}")
            logger.info(f"  检查点存储: {config_summary['checkpoint_storage']}")
            logger.info(f"  监控启用: {config_summary['monitoring_enabled']}")
            logger.info(f"  认证启用: {config_summary['auth_enabled']}")
            
            if config_summary['config_file']:
                logger.info(f"  配置文件: {config_summary['config_file']}")
            
        except Exception as e:
            logger.warning(f"显示配置信息失败: {e}")
    
    def _create_directories(self):
        """创建必要的目录"""
        try:
            directories = [
                "data",
                "logs",
                "checkpoints",
                "temp"
            ]
            
            for dir_name in directories:
                Path(dir_name).mkdir(parents=True, exist_ok=True)
            
            # 创建数据库目录
            if self.config.database.type == "sqlite":
                db_path = Path(self.config.database.sqlite_path)
                db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 创建检查点目录
            if self.config.checkpoint.storage_type == "sqlite":
                cp_path = Path(self.config.checkpoint.sqlite_db_path)
                cp_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.debug("必要目录创建完成")
            
        except Exception as e:
            logger.warning(f"创建目录失败: {e}")
    
    def _get_api_config(self) -> Dict[str, Any]:
        """获取API配置"""
        return {
            "cors_origins": self.config.api.cors_origins,
            "trusted_hosts": self.config.api.trusted_hosts,
            "enable_auth": self.config.api.enable_auth,
            "auth_secret_key": self.config.api.auth_secret_key,
            "enable_rate_limit": self.config.api.enable_rate_limit,
            "rate_limit_rpm": self.config.api.rate_limit_rpm
        }
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        try:
            def signal_handler(signum, frame):
                logger.info(f"收到信号 {signum}，开始优雅关闭...")
                self.shutdown_requested = True
                asyncio.create_task(self.shutdown())
            
            # 设置信号处理器
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            if hasattr(signal, 'SIGHUP'):
                signal.signal(signal.SIGHUP, signal_handler)
            
            logger.debug("信号处理器设置完成")
            
        except Exception as e:
            logger.warning(f"设置信号处理器失败: {e}")
    
    def _display_startup_info(self):
        """显示启动信息"""
        try:
            if self.integrator:
                status = asyncio.run(self.integrator.get_system_status())
                
                logger.info("系统状态:")
                logger.info(f"  注册智能体: {status['registered_agents']} 个")
                logger.info(f"  工作流模板: {status['workflow_templates']} 个")
                logger.info(f"  活跃工作流: {status['active_workflows']} 个")
                
                components = status['components']
                logger.info("系统组件:")
                for component, enabled in components.items():
                    status_text = "✓" if enabled else "✗"
                    logger.info(f"  {component}: {status_text}")
            
            # 显示访问信息
            api_config = self.config.api
            logger.info("访问信息:")
            logger.info(f"  API文档: http://{api_config.host}:{api_config.port}/docs")
            logger.info(f"  健康检查: http://{api_config.host}:{api_config.port}/health")
            logger.info(f"  WebSocket: ws://{api_config.host}:{api_config.port}/api/v1/ws/connect")
            
            startup_duration = (datetime.now() - self.startup_time).total_seconds()
            logger.info(f"启动耗时: {startup_duration:.2f} 秒")
            
        except Exception as e:
            logger.warning(f"显示启动信息失败: {e}")
    
    async def run_api_server(self):
        """运行API服务器"""
        try:
            if not self.app:
                logger.error("API应用未创建")
                return
            
            import uvicorn
            
            config = uvicorn.Config(
                app=self.app,
                host=self.config.api.host,
                port=self.config.api.port,
                reload=self.config.api.reload,
                workers=1,  # 使用1个worker以支持后台任务
                log_level=self.config.logging.level.lower(),
                access_log=True
            )
            
            server = uvicorn.Server(config)
            
            logger.info(f"API服务器启动: {self.config.api.host}:{self.config.api.port}")
            await server.serve()
            
        except Exception as e:
            logger.error(f"API服务器运行失败: {e}")
            raise
    
    async def shutdown(self):
        """关闭系统"""
        try:
            if self.shutdown_requested:
                return
            
            self.shutdown_requested = True
            
            logger.info("开始系统关闭...")
            
            # 关闭系统集成器
            if self.integrator:
                await self.integrator.shutdown_system()
            
            # 计算运行时间
            if self.startup_time:
                runtime = (datetime.now() - self.startup_time).total_seconds()
                logger.info(f"系统运行时间: {runtime:.2f} 秒")
            
            logger.info("系统关闭完成")
            
        except Exception as e:
            logger.error(f"系统关闭失败: {e}")
    
    def run(self):
        """运行系统（同步入口）"""
        try:
            # 启动系统
            success = asyncio.run(self.startup())
            if not success:
                logger.error("系统启动失败")
                sys.exit(1)
            
            # 运行API服务器
            asyncio.run(self.run_api_server())
            
        except KeyboardInterrupt:
            logger.info("收到中断信号")
        except Exception as e:
            logger.error(f"系统运行失败: {e}")
            sys.exit(1)
        finally:
            # 确保系统关闭
            if not self.shutdown_requested:
                asyncio.run(self.shutdown())
    
    async def run_async(self):
        """运行系统（异步入口）"""
        try:
            # 启动系统
            success = await self.startup()
            if not success:
                logger.error("系统启动失败")
                return False
            
            # 运行API服务器
            await self.run_api_server()
            
            return True
            
        except Exception as e:
            logger.error(f"系统运行失败: {e}")
            return False
        finally:
            # 确保系统关闭
            if not self.shutdown_requested:
                await self.shutdown()
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        try:
            info = {
                "startup_time": self.startup_time.isoformat() if self.startup_time else None,
                "config_summary": self.config_manager.get_config_summary(),
                "shutdown_requested": self.shutdown_requested
            }
            
            if self.integrator:
                system_status = asyncio.run(self.integrator.get_system_status())
                info["system_status"] = system_status
            
            return info
            
        except Exception as e:
            logger.error(f"获取系统信息失败: {e}")
            return {"error": str(e)}
    
    def create_sample_config(self, file_path: str = "config.yml") -> bool:
        """创建示例配置文件"""
        try:
            # 创建示例配置
            sample_config = {
                "environment": "development",
                "debug": True,
                "version": "1.0.0",
                "database": {
                    "type": "sqlite",
                    "sqlite_path": "data/database.db"
                },
                "checkpoint": {
                    "storage_type": "sqlite",
                    "sqlite_db_path": "data/checkpoints.db",
                    "auto_checkpoint_interval": 300
                },
                "api": {
                    "host": "0.0.0.0",
                    "port": 8000,
                    "enable_auth": False,
                    "enable_rate_limit": True,
                    "rate_limit_rpm": 100
                },
                "logging": {
                    "level": "INFO",
                    "file_path": "logs/system.log",
                    "enable_console": True
                },
                "monitoring": {
                    "enable_metrics": True,
                    "enable_tracing": True,
                    "metrics_interval": 60
                },
                "error_handling": {
                    "max_retries": 3,
                    "enable_circuit_breaker": True,
                    "webhook_url": None
                },
                "workflow": {
                    "default_execution_mode": "adaptive",
                    "max_iterations": 100,
                    "default_timeout_seconds": 3600
                },
                "custom": {
                    "example_setting": "example_value"
                }
            }
            
            # 保存示例配置
            import yaml
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(sample_config, f, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"示例配置文件已创建: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"创建示例配置文件失败: {e}")
            return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="LangGraph多智能体系统")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--create-config", help="创建示例配置文件")
    parser.add_argument("--host", help="API服务器主机")
    parser.add_argument("--port", type=int, help="API服务器端口")
    parser.add_argument("--reload", action="store_true", help="开发模式重载")
    parser.add_argument("--log-level", help="日志级别")
    
    args = parser.parse_args()
    
    # 创建示例配置文件
    if args.create_config:
        startup = SystemStartup()
        success = startup.create_sample_config(args.create_config)
        sys.exit(0 if success else 1)
    
    # 创建启动管理器
    startup = SystemStartup(args.config)
    
    # 覆盖配置参数
    if args.host:
        startup.config.api.host = args.host
    if args.port:
        startup.config.api.port = args.port
    if args.reload:
        startup.config.api.reload = args.reload
    if args.log_level:
        startup.config.logging.level = args.log_level
    
    # 运行系统
    startup.run()


if __name__ == "__main__":
    main()