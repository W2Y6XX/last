"""LangSmith集成模块 - 追踪和监控"""

import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from .monitoring import WorkflowEvent, ExecutionTrace, get_workflow_monitor

logger = logging.getLogger(__name__)


class LangSmithTracker:
    """LangSmith追踪器"""
    
    def __init__(self, api_key: Optional[str] = None, project_name: str = "langgraph-multi-agent"):
        self.api_key = api_key or os.getenv("LANGCHAIN_API_KEY")
        self.project_name = project_name
        self.enabled = bool(self.api_key)
        
        if not self.enabled:
            logger.warning("LangSmith API密钥未配置，追踪功能已禁用")
        else:
            logger.info(f"LangSmith追踪已启用，项目: {project_name}")
    
    def track_workflow_start(
        self, 
        workflow_id: str, 
        thread_id: str,
        inputs: Dict[str, Any]
    ) -> Optional[str]:
        """追踪工作流开始"""
        if not self.enabled:
            return None
        
        try:
            # 这里可以集成实际的LangSmith SDK
            # 目前使用模拟实现
            run_id = f"run_{workflow_id}_{thread_id}"
            
            logger.debug(
                "LangSmith追踪工作流开始",
                run_id=run_id,
                workflow_id=workflow_id,
                thread_id=thread_id,
                project=self.project_name
            )
            
            return run_id
            
        except Exception as e:
            logger.error(f"LangSmith追踪开始失败: {e}")
            return None
    
    def track_workflow_end(
        self, 
        run_id: str, 
        outputs: Dict[str, Any],
        success: bool = True,
        error: Optional[str] = None
    ) -> None:
        """追踪工作流结束"""
        if not self.enabled or not run_id:
            return
        
        try:
            logger.debug(
                "LangSmith追踪工作流结束",
                run_id=run_id,
                success=success,
                error=error,
                project=self.project_name
            )
            
        except Exception as e:
            logger.error(f"LangSmith追踪结束失败: {e}")
    
    def track_agent_execution(
        self, 
        parent_run_id: str,
        agent_id: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        duration_ms: float,
        success: bool = True,
        error: Optional[str] = None
    ) -> Optional[str]:
        """追踪智能体执行"""
        if not self.enabled or not parent_run_id:
            return None
        
        try:
            agent_run_id = f"{parent_run_id}_{agent_id}"
            
            logger.debug(
                "LangSmith追踪智能体执行",
                run_id=agent_run_id,
                parent_run_id=parent_run_id,
                agent_id=agent_id,
                duration_ms=duration_ms,
                success=success,
                error=error
            )
            
            return agent_run_id
            
        except Exception as e:
            logger.error(f"LangSmith智能体追踪失败: {e}")
            return None
    
    def add_metadata(
        self, 
        run_id: str, 
        metadata: Dict[str, Any]
    ) -> None:
        """添加元数据"""
        if not self.enabled or not run_id:
            return
        
        try:
            logger.debug(
                "LangSmith添加元数据",
                run_id=run_id,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"LangSmith元数据添加失败: {e}")


class LangSmithIntegration:
    """LangSmith集成"""
    
    def __init__(self, api_key: Optional[str] = None, project_name: str = "langgraph-multi-agent"):
        self.tracker = LangSmithTracker(api_key, project_name)
        self.workflow_monitor = get_workflow_monitor()
        self.active_runs: Dict[str, str] = {}  # thread_id -> run_id
        
        # 注册事件处理器
        self.workflow_monitor.tracer.register_event_handler(self._handle_workflow_event)
    
    def _handle_workflow_event(self, event: WorkflowEvent) -> None:
        """处理工作流事件"""
        try:
            if event.event_type == "workflow_started":
                self._handle_workflow_start(event)
            elif event.event_type == "workflow_completed":
                self._handle_workflow_end(event)
            elif event.event_type == "agent_executed":
                self._handle_agent_execution(event)
            elif event.event_type == "phase_changed":
                self._handle_phase_change(event)
                
        except Exception as e:
            logger.error(f"LangSmith事件处理失败: {e}")
    
    def _handle_workflow_start(self, event: WorkflowEvent) -> None:
        """处理工作流开始事件"""
        inputs = {
            "workflow_id": event.workflow_id,
            "thread_id": event.thread_id,
            "phase": event.phase.value,
            "data": event.data or {}
        }
        
        run_id = self.tracker.track_workflow_start(
            event.workflow_id,
            event.thread_id,
            inputs
        )
        
        if run_id:
            self.active_runs[event.thread_id] = run_id
    
    def _handle_workflow_end(self, event: WorkflowEvent) -> None:
        """处理工作流结束事件"""
        run_id = self.active_runs.pop(event.thread_id, None)
        if not run_id:
            return
        
        outputs = {
            "workflow_id": event.workflow_id,
            "thread_id": event.thread_id,
            "final_phase": event.phase.value,
            "duration_ms": event.duration_ms,
            "data": event.data or {}
        }
        
        success = event.data.get("success", True) if event.data else True
        error = event.data.get("error") if event.data else None
        
        self.tracker.track_workflow_end(run_id, outputs, success, error)
    
    def _handle_agent_execution(self, event: WorkflowEvent) -> None:
        """处理智能体执行事件"""
        parent_run_id = self.active_runs.get(event.thread_id)
        if not parent_run_id or not event.agent_id:
            return
        
        inputs = {
            "agent_id": event.agent_id,
            "phase": event.phase.value,
            "timestamp": event.timestamp.isoformat()
        }
        
        outputs = event.data or {}
        success = event.data.get("success", True) if event.data else True
        error = event.data.get("error") if event.data else None
        duration_ms = event.duration_ms or 0
        
        self.tracker.track_agent_execution(
            parent_run_id,
            event.agent_id,
            inputs,
            outputs,
            duration_ms,
            success,
            error
        )
    
    def _handle_phase_change(self, event: WorkflowEvent) -> None:
        """处理阶段变化事件"""
        run_id = self.active_runs.get(event.thread_id)
        if not run_id:
            return
        
        metadata = {
            "phase_change": {
                "from_phase": event.data.get("from_phase") if event.data else None,
                "to_phase": event.phase.value,
                "timestamp": event.timestamp.isoformat()
            }
        }
        
        self.tracker.add_metadata(run_id, metadata)
    
    def get_active_runs(self) -> Dict[str, str]:
        """获取活跃的运行"""
        return self.active_runs.copy()
    
    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self.tracker.enabled


# 全局LangSmith集成实例
_langsmith_integration: Optional[LangSmithIntegration] = None


def get_langsmith_integration(
    api_key: Optional[str] = None, 
    project_name: str = "langgraph-multi-agent"
) -> LangSmithIntegration:
    """获取LangSmith集成实例"""
    global _langsmith_integration
    
    if _langsmith_integration is None:
        _langsmith_integration = LangSmithIntegration(api_key, project_name)
    
    return _langsmith_integration


def enable_langsmith_tracking(
    api_key: Optional[str] = None, 
    project_name: str = "langgraph-multi-agent"
) -> bool:
    """启用LangSmith追踪"""
    try:
        integration = get_langsmith_integration(api_key, project_name)
        if integration.is_enabled():
            logger.info("LangSmith追踪已启用")
            return True
        else:
            logger.warning("LangSmith追踪启用失败：API密钥未配置")
            return False
    except Exception as e:
        logger.error(f"启用LangSmith追踪失败: {e}")
        return False


def disable_langsmith_tracking() -> None:
    """禁用LangSmith追踪"""
    global _langsmith_integration
    _langsmith_integration = None
    logger.info("LangSmith追踪已禁用")