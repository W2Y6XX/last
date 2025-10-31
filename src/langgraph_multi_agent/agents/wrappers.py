"""智能体包装器 - LangGraph节点包装器基类"""

import asyncio
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import traceback

from ..utils.logging import LoggerMixin
from ..utils.config import config
from ..core.state import (
    LangGraphTaskState, 
    WorkflowPhase, 
    update_workflow_phase,
    add_agent_message,
    handle_error,
    add_performance_metric,
    create_error_state
)


class AgentExecutionResult:
    """智能体执行结果"""
    
    def __init__(
        self,
        success: bool,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None,
        execution_time: Optional[float] = None,
        retry_count: int = 0
    ):
        self.success = success
        self.result = result or {}
        self.error = error
        self.execution_time = execution_time
        self.retry_count = retry_count
        self.timestamp = datetime.now()


class AgentNodeWrapper(LoggerMixin, ABC):
    """智能体节点包装器基类
    
    将现有智能体包装为LangGraph节点，提供统一的执行接口、
    错误处理、重试机制和状态管理功能。
    """
    
    def __init__(
        self, 
        agent_instance: Any, 
        agent_type: str,
        max_retries: Optional[int] = None,
        timeout_seconds: Optional[int] = None,
        enable_monitoring: bool = True
    ):
        super().__init__()
        self.agent = agent_instance
        self.agent_type = agent_type
        self.max_retries = max_retries or config.agent.max_retries
        self.timeout_seconds = timeout_seconds or config.agent.timeout_seconds
        self.enable_monitoring = enable_monitoring
        
        # 执行统计
        self.execution_count = 0
        self.success_count = 0
        self.error_count = 0
        self.total_execution_time = 0.0
        self.last_execution_time: Optional[datetime] = None
        
        # 回调函数
        self.pre_execution_callbacks: List[Callable] = []
        self.post_execution_callbacks: List[Callable] = []
        self.error_callbacks: List[Callable] = []
    
    async def __call__(self, state: LangGraphTaskState) -> LangGraphTaskState:
        """LangGraph节点调用入口点"""
        start_time = datetime.now()
        self.execution_count += 1
        self.last_execution_time = start_time
        
        try:
            self.logger.info(
                "开始执行智能体",
                agent_type=self.agent_type,
                task_id=state["task_state"]["task_id"],
                current_node=state["current_node"]
            )
            
            # 执行前回调
            await self._execute_callbacks(self.pre_execution_callbacks, state)
            
            # 提取任务数据
            task_data = self._extract_task_data(state)
            
            # 执行智能体（带重试机制）
            execution_result = await self._execute_with_retry(task_data)
            
            # 更新状态
            updated_state = await self._update_state(state, execution_result)
            
            # 记录性能指标
            execution_time = (datetime.now() - start_time).total_seconds()
            self.total_execution_time += execution_time
            
            if execution_result.success:
                self.success_count += 1
                updated_state = add_performance_metric(
                    updated_state,
                    f"{self.agent_type}_execution_time",
                    execution_time
                )
            else:
                self.error_count += 1
            
            # 执行后回调
            await self._execute_callbacks(self.post_execution_callbacks, updated_state)
            
            self.logger.info(
                "智能体执行完成",
                agent_type=self.agent_type,
                success=execution_result.success,
                execution_time=execution_time,
                retry_count=execution_result.retry_count
            )
            
            return updated_state
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(
                "智能体执行失败",
                agent_type=self.agent_type,
                error=str(e),
                traceback=traceback.format_exc()
            )
            
            # 错误回调
            await self._execute_callbacks(self.error_callbacks, state, error=e)
            
            # 处理错误状态
            error_state = handle_error(state, e, self.agent_type, self.agent_type)
            return error_state
    
    @abstractmethod
    def _extract_task_data(self, state: LangGraphTaskState) -> Dict[str, Any]:
        """从LangGraph状态提取任务数据
        
        子类必须实现此方法，定义如何从LangGraph状态中提取
        适合该智能体的任务数据。
        """
        pass
    
    @abstractmethod
    async def _update_state(
        self, 
        state: LangGraphTaskState, 
        execution_result: AgentExecutionResult
    ) -> LangGraphTaskState:
        """更新LangGraph状态
        
        子类必须实现此方法，定义如何将智能体执行结果
        更新到LangGraph状态中。
        """
        pass
    
    async def _execute_with_retry(self, task_data: Dict[str, Any]) -> AgentExecutionResult:
        """带重试机制的智能体执行"""
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                self.logger.debug(
                    "执行智能体尝试",
                    agent_type=self.agent_type,
                    attempt=attempt + 1,
                    max_retries=self.max_retries + 1
                )
                
                # 执行智能体
                result = await self._execute_agent(task_data)
                
                return AgentExecutionResult(
                    success=True,
                    result=result,
                    retry_count=attempt
                )
                
            except Exception as e:
                last_error = e
                self.logger.warning(
                    "智能体执行尝试失败",
                    agent_type=self.agent_type,
                    attempt=attempt + 1,
                    error=str(e)
                )
                
                # 如果不是最后一次尝试，等待后重试
                if attempt < self.max_retries:
                    wait_time = min(2 ** attempt, 30)  # 指数退避，最大30秒
                    await asyncio.sleep(wait_time)
        
        # 所有重试都失败了
        return AgentExecutionResult(
            success=False,
            error=last_error,
            retry_count=self.max_retries
        )
    
    async def _execute_agent(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行智能体的核心逻辑"""
        start_time = datetime.now()
        
        try:
            # 检查智能体是否有process_task方法
            if not hasattr(self.agent, 'process_task'):
                raise AttributeError(f"智能体 {self.agent_type} 没有 process_task 方法")
            
            # 执行智能体（带超时控制）
            if asyncio.iscoroutinefunction(self.agent.process_task):
                result = await asyncio.wait_for(
                    self.agent.process_task(task_data),
                    timeout=self.timeout_seconds
                )
            else:
                # 对于同步方法，在线程池中执行
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.agent.process_task(task_data)
                )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 验证结果格式
            if not isinstance(result, dict):
                raise ValueError(f"智能体返回结果必须是字典类型，实际类型: {type(result)}")
            
            # 添加执行元数据
            result["_execution_metadata"] = {
                "agent_type": self.agent_type,
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat()
            }
            
            return result
            
        except asyncio.TimeoutError:
            raise TimeoutError(f"智能体 {self.agent_type} 执行超时 ({self.timeout_seconds}秒)")
        except Exception as e:
            # 重新抛出异常，保持原始错误信息
            raise
    
    def register_pre_execution_callback(self, callback: Callable):
        """注册执行前回调"""
        self.pre_execution_callbacks.append(callback)
        self.logger.debug("执行前回调已注册", agent_type=self.agent_type)
    
    def register_post_execution_callback(self, callback: Callable):
        """注册执行后回调"""
        self.post_execution_callbacks.append(callback)
        self.logger.debug("执行后回调已注册", agent_type=self.agent_type)
    
    def register_error_callback(self, callback: Callable):
        """注册错误回调"""
        self.error_callbacks.append(callback)
        self.logger.debug("错误回调已注册", agent_type=self.agent_type)
    
    async def _execute_callbacks(
        self, 
        callbacks: List[Callable], 
        state: LangGraphTaskState,
        **kwargs
    ):
        """执行回调函数"""
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(self.agent_type, state, **kwargs)
                else:
                    callback(self.agent_type, state, **kwargs)
            except Exception as e:
                self.logger.error(
                    "回调执行失败",
                    agent_type=self.agent_type,
                    callback=str(callback),
                    error=str(e)
                )
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        success_rate = (self.success_count / self.execution_count) if self.execution_count > 0 else 0
        avg_execution_time = (self.total_execution_time / self.execution_count) if self.execution_count > 0 else 0
        
        return {
            "agent_type": self.agent_type,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": success_rate,
            "total_execution_time": self.total_execution_time,
            "average_execution_time": avg_execution_time,
            "last_execution_time": self.last_execution_time.isoformat() if self.last_execution_time else None,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds
        }
    
    def reset_statistics(self):
        """重置执行统计"""
        self.execution_count = 0
        self.success_count = 0
        self.error_count = 0
        self.total_execution_time = 0.0
        self.last_execution_time = None
        self.logger.info("执行统计已重置", agent_type=self.agent_type)
    
    def validate_agent_interface(self) -> bool:
        """验证智能体接口是否符合要求"""
        if not hasattr(self.agent, 'process_task'):
            self.logger.error("智能体缺少process_task方法", agent_type=self.agent_type)
            return False
        
        # 可以添加更多接口验证逻辑
        return True
    
    def __str__(self) -> str:
        return f"AgentNodeWrapper({self.agent_type})"
    
    def __repr__(self) -> str:
        return f"AgentNodeWrapper(agent_type='{self.agent_type}', agent={self.agent})"