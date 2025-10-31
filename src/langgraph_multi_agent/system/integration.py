"""系统集成器 - 连接所有组件"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Type
from datetime import datetime

from ..workflow.multi_agent_workflow import MultiAgentWorkflow, WorkflowExecutionMode
from ..workflow.checkpoint_manager import CheckpointManager, MemoryCheckpointStorage, SQLiteCheckpointStorage
from ..workflow.error_recovery import ErrorRecoveryHandler
from ..integration.error_integration import IntegratedErrorHandler
from ..workflow.monitoring import WorkflowMonitor
from ..agents.meta_agent_wrapper import MetaAgentWrapper
from ..agents.task_decomposer_wrapper import TaskDecomposerWrapper
from ..agents.coordinator_wrapper import CoordinatorWrapper
from ..agents.generic_wrapper import GenericAgentWrapper
from ..agents.llm_agents import LLMMetaAgent, LLMTaskDecomposer, LLMCoordinator, LLMGenericAgent
from ..core.state import create_initial_state
from ..utils.config import get_config
from .performance_integration import SystemPerformanceManager
from .config_manager import ConfigManager

logger = logging.getLogger(__name__)


class SystemIntegrator:
    """系统集成器 - 负责集成所有组件"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or get_config()
        
        # 配置管理器
        self.config_manager = ConfigManager(self.config)
        
        # 核心组件
        self.checkpoint_manager: Optional[CheckpointManager] = None
        self.error_recovery_handler: Optional[ErrorRecoveryHandler] = None
        self.integrated_error_handler: Optional[IntegratedErrorHandler] = None
        self.workflow_monitor: Optional[WorkflowMonitor] = None
        self.performance_manager: Optional[SystemPerformanceManager] = None
        
        # 智能体注册表
        self.agent_registry: Dict[str, Any] = {}
        self.agent_wrappers: Dict[str, Any] = {}
        
        # 工作流管理
        self.workflow_templates: Dict[str, Dict[str, Any]] = {}
        self.active_workflows: Dict[str, MultiAgentWorkflow] = {}
        
        # 系统状态
        self.is_initialized = False
        self.initialization_time: Optional[datetime] = None
        
        logger.info("系统集成器初始化")
    
    async def initialize_system(self) -> bool:
        """初始化整个系统"""
        try:
            logger.info("开始系统初始化...")
            
            # 1. 初始化存储和检查点管理
            await self._initialize_storage()
            
            # 2. 初始化错误处理
            await self._initialize_error_handling()
            
            # 3. 初始化监控系统
            await self._initialize_monitoring()
            
            # 4. 注册默认智能体
            await self._register_default_agents()
            
            # 5. 初始化性能管理器
            await self._initialize_performance_manager()
            
            # 6. 创建工作流模板
            await self._create_workflow_templates()
            
            # 7. 启动后台服务
            await self._start_background_services()
            
            self.is_initialized = True
            self.initialization_time = datetime.now()
            
            logger.info("系统初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"系统初始化失败: {e}")
            return False
    
    async def _initialize_storage(self):
        """初始化存储系统"""
        try:
            storage_type = self.config.get("checkpoint_storage", "memory")
            
            if storage_type == "sqlite":
                db_path = self.config.get("sqlite_db_path", "checkpoints.db")
                storage = SQLiteCheckpointStorage(db_path)
            else:
                storage = MemoryCheckpointStorage()
            
            self.checkpoint_manager = CheckpointManager(
                storage=storage,
                auto_checkpoint_interval=self.config.get("checkpoint_interval", 300),
                max_checkpoints_per_thread=self.config.get("max_checkpoints", 50)
            )
            
            logger.info(f"存储系统初始化完成: {storage_type}")
            
        except Exception as e:
            logger.error(f"存储系统初始化失败: {e}")
            raise
    
    async def _initialize_error_handling(self):
        """初始化错误处理系统"""
        try:
            # 创建错误恢复处理器
            self.error_recovery_handler = ErrorRecoveryHandler(
                checkpoint_manager=self.checkpoint_manager
            )
            
            # 创建集成错误处理器
            self.integrated_error_handler = IntegratedErrorHandler(
                error_recovery_handler=self.error_recovery_handler,
                workflow_monitor=self.workflow_monitor
            )
            
            # 配置Webhook报告器（如果配置了）
            webhook_url = self.config.get("error_webhook_url")
            if webhook_url:
                self.integrated_error_handler.add_webhook_reporter(webhook_url)
            
            logger.info("错误处理系统初始化完成")
            
        except Exception as e:
            logger.error(f"错误处理系统初始化失败: {e}")
            raise
    
    async def _initialize_monitoring(self):
        """初始化监控系统"""
        try:
            self.workflow_monitor = WorkflowMonitor(
                enable_metrics=self.config.get("enable_metrics", True),
                enable_tracing=self.config.get("enable_tracing", True),
                metrics_interval=self.config.get("metrics_interval", 60)
            )
            
            # 启动监控
            await self.workflow_monitor.start_monitoring()
            
            logger.info("监控系统初始化完成")
            
        except Exception as e:
            logger.error(f"监控系统初始化失败: {e}")
            raise
    
    async def _initialize_performance_manager(self):
        """初始化性能管理器"""
        try:
            self.performance_manager = SystemPerformanceManager(self.config_manager)
            await self.performance_manager.start()
            
            logger.info("性能管理器初始化完成")
            
        except Exception as e:
            logger.error(f"性能管理器初始化失败: {e}")
            raise
    
    async def _register_default_agents(self):
        """注册默认智能体"""
        try:
            # 这里应该根据配置注册实际的智能体实例
            # 暂时使用模拟的智能体
            
            # 注册MetaAgent
            meta_agent = self._create_llm_agent("meta_agent", "meta_agent")
            self.register_agent("meta_agent", meta_agent, "meta_agent")
            
            # 注册TaskDecomposer
            task_decomposer = self._create_llm_agent("task_decomposer", "task_decomposer")
            self.register_agent("task_decomposer", task_decomposer, "task_decomposer")
            
            # 注册Coordinator
            coordinator = self._create_llm_agent("coordinator", "coordinator")
            self.register_agent("coordinator", coordinator, "coordinator")
            
            # 注册通用智能体
            for skill in ["data_processing", "analysis", "reporting", "visualization"]:
                agent = self._create_llm_agent(f"{skill}_agent", "generic")
                self.register_agent(f"{skill}_agent", agent, "generic", capabilities=[skill])
            
            logger.info(f"注册了 {len(self.agent_registry)} 个默认智能体")
            
        except Exception as e:
            logger.error(f"注册默认智能体失败: {e}")
            raise
    
    def _create_llm_agent(self, agent_id: str, agent_type: str):
        """创建基于LLM的智能体实例"""
        if agent_type == "meta_agent":
            return LLMMetaAgent()
        elif agent_type == "task_decomposer":
            return LLMTaskDecomposer()
        elif agent_type == "coordinator":
            return LLMCoordinator()
        else:
            # 根据agent_id确定能力
            capabilities = []
            if "data_processing" in agent_id:
                capabilities = ["data_processing", "data_analysis"]
            elif "analysis" in agent_id:
                capabilities = ["analysis", "research", "reporting"]
            elif "reporting" in agent_id:
                capabilities = ["reporting", "documentation", "visualization"]
            elif "visualization" in agent_id:
                capabilities = ["visualization", "charting", "presentation"]
            else:
                capabilities = ["general_processing"]
            
            return LLMGenericAgent(agent_type="generic", capabilities=capabilities)
    
    def register_agent(
        self, 
        agent_id: str, 
        agent_instance: Any, 
        agent_type: str,
        capabilities: Optional[List[str]] = None,
        **wrapper_kwargs
    ):
        """注册智能体"""
        try:
            # 存储原始智能体实例
            self.agent_registry[agent_id] = {
                "instance": agent_instance,
                "type": agent_type,
                "capabilities": capabilities or [],
                "registered_at": datetime.now(),
                "metadata": wrapper_kwargs
            }
            
            # 创建包装器
            if agent_type == "meta_agent":
                wrapper = MetaAgentWrapper(agent_instance, **wrapper_kwargs)
            elif agent_type == "task_decomposer":
                wrapper = TaskDecomposerWrapper(agent_instance, **wrapper_kwargs)
            elif agent_type == "coordinator":
                wrapper = CoordinatorWrapper(agent_instance, **wrapper_kwargs)
            else:
                wrapper = GenericAgentWrapper(
                    agent_instance, 
                    agent_type, 
                    capabilities=capabilities,
                    **wrapper_kwargs
                )
            
            self.agent_wrappers[agent_id] = wrapper
            
            logger.info(f"智能体注册成功: {agent_id} ({agent_type})")
            
        except Exception as e:
            logger.error(f"智能体注册失败 {agent_id}: {e}")
            raise
    
    async def _create_workflow_templates(self):
        """创建工作流模板"""
        try:
            # 简单任务模板
            self.workflow_templates["simple"] = {
                "name": "简单任务工作流",
                "description": "适用于简单、单步骤任务",
                "execution_mode": WorkflowExecutionMode.SEQUENTIAL,
                "required_agents": ["generic_agent"],
                "optional_agents": [],
                "max_execution_time": 300
            }
            
            # 分析任务模板
            self.workflow_templates["analysis"] = {
                "name": "分析任务工作流",
                "description": "适用于数据分析和研究任务",
                "execution_mode": WorkflowExecutionMode.SEQUENTIAL,
                "required_agents": ["meta_agent", "analysis_agent"],
                "optional_agents": ["data_processing_agent", "visualization_agent"],
                "max_execution_time": 1800
            }
            
            # 复杂任务模板
            self.workflow_templates["complex"] = {
                "name": "复杂任务工作流",
                "description": "适用于需要分解和协调的复杂任务",
                "execution_mode": WorkflowExecutionMode.ADAPTIVE,
                "required_agents": ["meta_agent", "task_decomposer", "coordinator"],
                "optional_agents": ["data_processing_agent", "analysis_agent", "reporting_agent"],
                "max_execution_time": 3600
            }
            
            # 并行任务模板
            self.workflow_templates["parallel"] = {
                "name": "并行任务工作流",
                "description": "适用于可以并行执行的任务",
                "execution_mode": WorkflowExecutionMode.PARALLEL,
                "required_agents": ["coordinator"],
                "optional_agents": ["data_processing_agent", "analysis_agent"],
                "max_execution_time": 1200
            }
            
            logger.info(f"创建了 {len(self.workflow_templates)} 个工作流模板")
            
        except Exception as e:
            logger.error(f"创建工作流模板失败: {e}")
            raise
    
    async def _start_background_services(self):
        """启动后台服务"""
        try:
            # 启动健康监控
            if self.integrated_error_handler:
                await self.integrated_error_handler.start_health_monitoring()
            
            # 启动定期清理任务
            asyncio.create_task(self._periodic_cleanup())
            
            # 启动性能监控
            if self.workflow_monitor:
                asyncio.create_task(self.workflow_monitor.start_performance_monitoring())
            
            logger.info("后台服务启动完成")
            
        except Exception as e:
            logger.error(f"后台服务启动失败: {e}")
            raise
    
    async def create_workflow(
        self, 
        workflow_id: str, 
        template_name: str = "simple",
        custom_config: Optional[Dict[str, Any]] = None
    ) -> MultiAgentWorkflow:
        """创建工作流实例"""
        try:
            if template_name not in self.workflow_templates:
                raise ValueError(f"未知的工作流模板: {template_name}")
            
            template = self.workflow_templates[template_name]
            config = custom_config or {}
            
            # 创建工作流
            workflow = MultiAgentWorkflow(
                workflow_id=workflow_id,
                checkpointer=self.checkpoint_manager.checkpointer if self.checkpoint_manager else None,
                execution_mode=config.get("execution_mode", template["execution_mode"]),
                max_iterations=config.get("max_iterations", 100),
                timeout_seconds=config.get("timeout_seconds", template["max_execution_time"])
            )
            
            # 注册必需的智能体
            for agent_id in template["required_agents"]:
                if agent_id in self.agent_wrappers:
                    workflow.register_agent(
                        agent_id,
                        self.agent_registry[agent_id]["instance"],
                        self.agent_registry[agent_id]["type"]
                    )
            
            # 注册可选的智能体（如果可用）
            for agent_id in template.get("optional_agents", []):
                if agent_id in self.agent_wrappers:
                    workflow.register_agent(
                        agent_id,
                        self.agent_registry[agent_id]["instance"],
                        self.agent_registry[agent_id]["type"]
                    )
            
            # 编译工作流
            workflow.compile_workflow()
            
            # 存储活跃工作流
            self.active_workflows[workflow_id] = workflow
            
            logger.info(f"工作流创建成功: {workflow_id} (模板: {template_name})")
            return workflow
            
        except Exception as e:
            logger.error(f"工作流创建失败: {e}")
            raise
    
    async def execute_workflow(
        self,
        workflow_id: str,
        task_input: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """执行工作流"""
        try:
            if workflow_id not in self.active_workflows:
                raise ValueError(f"工作流不存在: {workflow_id}")
            
            workflow = self.active_workflows[workflow_id]
            
            # 配置执行参数
            execution_config = config or {}
            execution_config.update({
                "configurable": {
                    "thread_id": f"{workflow_id}_{datetime.now().timestamp()}",
                    "checkpoint_manager": self.checkpoint_manager,
                    "error_handler": self.integrated_error_handler
                }
            })
            
            # 执行工作流
            result = await workflow.execute(task_input, execution_config)
            
            logger.info(f"工作流执行完成: {workflow_id}")
            return result
            
        except Exception as e:
            logger.error(f"工作流执行失败: {e}")
            
            # 使用集成错误处理器处理错误
            if self.integrated_error_handler:
                await self.integrated_error_handler.handle_integrated_error(
                    e, "system", workflow_id, {}, 0
                )
            
            raise
    
    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            status = {
                "initialized": self.is_initialized,
                "initialization_time": self.initialization_time.isoformat() if self.initialization_time else None,
                "registered_agents": len(self.agent_registry),
                "active_workflows": len(self.active_workflows),
                "workflow_templates": len(self.workflow_templates),
                "components": {
                    "checkpoint_manager": self.checkpoint_manager is not None,
                    "error_recovery_handler": self.error_recovery_handler is not None,
                    "integrated_error_handler": self.integrated_error_handler is not None,
                    "workflow_monitor": self.workflow_monitor is not None,
                    "performance_manager": self.performance_manager is not None
                }
            }
            
            # 添加健康状态
            if self.integrated_error_handler:
                health_status = self.integrated_error_handler.get_system_health()
                status["health"] = health_status
            
            # 添加性能指标
            if self.workflow_monitor:
                metrics = await self.workflow_monitor.get_performance_metrics()
                status["performance"] = metrics
            
            # 添加系统性能统计
            if self.performance_manager:
                perf_stats = self.performance_manager.get_system_stats()
                status["system_performance"] = perf_stats
            
            return status
            
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {"error": str(e)}
    
    async def shutdown_system(self):
        """关闭系统"""
        try:
            logger.info("开始系统关闭...")
            
            # 停止后台服务
            if self.integrated_error_handler:
                self.integrated_error_handler.stop_health_monitoring()
            
            if self.workflow_monitor:
                await self.workflow_monitor.stop_monitoring()
            
            # 停止性能管理器
            if self.performance_manager:
                await self.performance_manager.stop()
            
            # 清理活跃工作流
            for workflow_id, workflow in self.active_workflows.items():
                logger.info(f"清理工作流: {workflow_id}")
            
            self.active_workflows.clear()
            
            # 清理检查点管理器
            if self.checkpoint_manager:
                await self.checkpoint_manager.cleanup_old_checkpoints(days_old=0)
            
            self.is_initialized = False
            
            logger.info("系统关闭完成")
            
        except Exception as e:
            logger.error(f"系统关闭失败: {e}")
    
    async def _periodic_cleanup(self):
        """定期清理任务"""
        while self.is_initialized:
            try:
                await asyncio.sleep(3600)  # 每小时执行一次
                
                # 清理旧检查点
                if self.checkpoint_manager:
                    cleaned = await self.checkpoint_manager.cleanup_old_checkpoints(days_old=7)
                    if cleaned > 0:
                        logger.info(f"清理了 {cleaned} 个旧检查点")
                
                # 清理完成的工作流
                completed_workflows = []
                for workflow_id, workflow in self.active_workflows.items():
                    if workflow.status.value in ["completed", "failed", "cancelled"]:
                        completed_workflows.append(workflow_id)
                
                for workflow_id in completed_workflows:
                    del self.active_workflows[workflow_id]
                    logger.info(f"清理完成的工作流: {workflow_id}")
                
            except Exception as e:
                logger.error(f"定期清理任务失败: {e}")
    
    def get_agent_registry(self) -> Dict[str, Dict[str, Any]]:
        """获取智能体注册表"""
        return {
            agent_id: {
                "type": info["type"],
                "capabilities": info["capabilities"],
                "registered_at": info["registered_at"].isoformat(),
                "metadata": info["metadata"]
            }
            for agent_id, info in self.agent_registry.items()
        }
    
    def get_workflow_templates(self) -> Dict[str, Dict[str, Any]]:
        """获取工作流模板"""
        return self.workflow_templates.copy()
    
    def get_active_workflows(self) -> List[str]:
        """获取活跃工作流列表"""
        return list(self.active_workflows.keys())
    
    async def optimize_system_performance(self) -> Dict[str, Any]:
        """优化系统性能"""
        try:
            if not self.performance_manager:
                return {"error": "性能管理器未初始化"}
            
            result = await self.performance_manager.optimize_system()
            logger.info("系统性能优化完成")
            return result
            
        except Exception as e:
            logger.error(f"系统性能优化失败: {e}")
            return {"error": str(e)}
    
    def get_performance_recommendations(self) -> Dict[str, Any]:
        """获取性能优化建议"""
        try:
            if not self.performance_manager:
                return {"error": "性能管理器未初始化"}
            
            return self.performance_manager.get_optimization_recommendations()
            
        except Exception as e:
            logger.error(f"获取性能建议失败: {e}")
            return {"error": str(e)}
    
    async def system_health_check(self) -> Dict[str, Any]:
        """系统健康检查"""
        try:
            health_status = {
                "overall": "healthy",
                "components": {},
                "issues": [],
                "timestamp": datetime.now().isoformat()
            }
            
            # 检查核心组件
            components = {
                "system_integrator": self.is_initialized,
                "checkpoint_manager": self.checkpoint_manager is not None,
                "error_recovery": self.error_recovery_handler is not None,
                "workflow_monitor": self.workflow_monitor is not None,
                "performance_manager": self.performance_manager is not None
            }
            
            for component, status in components.items():
                health_status["components"][component] = "healthy" if status else "unhealthy"
                if not status:
                    health_status["issues"].append(f"{component} 未初始化或不可用")
            
            # 检查性能管理器健康状态
            if self.performance_manager:
                perf_health = await self.performance_manager.health_check()
                health_status["performance"] = perf_health
                
                if perf_health.get("overall") != "healthy":
                    health_status["issues"].extend(perf_health.get("issues", []))
            
            # 确定整体状态
            if health_status["issues"]:
                health_status["overall"] = "degraded" if len(health_status["issues"]) <= 3 else "unhealthy"
            
            return health_status
            
        except Exception as e:
            logger.error(f"系统健康检查失败: {e}")
            return {
                "overall": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_cache_manager(self):
        """获取缓存管理器"""
        if self.performance_manager:
            return self.performance_manager.get_cache_manager()
        return None
    
    def get_resource_pool_manager(self):
        """获取资源池管理器"""
        if self.performance_manager:
            return self.performance_manager.get_resource_pool_manager()
        return None
    
    def get_concurrent_executor(self):
        """获取并发执行器"""
        if self.performance_manager:
            return self.performance_manager.get_concurrent_executor()
        return None