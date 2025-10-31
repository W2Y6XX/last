"""状态适配器 - LangGraph状态与现有系统的双向同步"""

import asyncio
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import json

from ..utils.logging import LoggerMixin
from ..core.state import LangGraphTaskState, WorkflowPhase
from ..legacy.task_state import TaskState as LegacyTaskState, TaskStatus


class StateAdapter(LoggerMixin):
    """状态适配器 - 处理LangGraph状态与现有系统状态的转换和同步"""
    
    def __init__(self):
        super().__init__()
        self.sync_callbacks: List[Callable] = []
        self.state_cache: Dict[str, Dict[str, Any]] = {}
        self.sync_enabled = True
    
    def register_sync_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """注册状态同步回调函数"""
        self.sync_callbacks.append(callback)
        self.logger.info("状态同步回调已注册")
    
    def enable_sync(self):
        """启用状态同步"""
        self.sync_enabled = True
        self.logger.info("状态同步已启用")
    
    def disable_sync(self):
        """禁用状态同步"""
        self.sync_enabled = False
        self.logger.info("状态同步已禁用")
    
    def langgraph_to_legacy(self, langgraph_state: LangGraphTaskState) -> LegacyTaskState:
        """将LangGraph状态转换为现有系统状态"""
        try:
            # 直接使用LangGraph状态中的task_state部分
            legacy_state = langgraph_state["task_state"].copy()
            
            # 同步工作流阶段到任务状态
            workflow_phase = langgraph_state["workflow_context"]["current_phase"]
            phase_to_status = {
                WorkflowPhase.INITIALIZATION: TaskStatus.PENDING,
                WorkflowPhase.ANALYSIS: TaskStatus.ANALYZING,
                WorkflowPhase.DECOMPOSITION: TaskStatus.DECOMPOSED,
                WorkflowPhase.COORDINATION: TaskStatus.IN_PROGRESS,
                WorkflowPhase.EXECUTION: TaskStatus.IN_PROGRESS,
                WorkflowPhase.REVIEW: TaskStatus.REVIEWING,
                WorkflowPhase.COMPLETION: TaskStatus.COMPLETED,
                WorkflowPhase.ERROR_HANDLING: TaskStatus.FAILED
            }
            
            if workflow_phase in phase_to_status:
                legacy_state["status"] = phase_to_status[workflow_phase]
            
            # 添加LangGraph特有的元数据
            if "langgraph_metadata" not in legacy_state["metadata"]:
                legacy_state["metadata"]["langgraph_metadata"] = {}
            
            legacy_state["metadata"]["langgraph_metadata"].update({
                "workflow_phase": workflow_phase.value,
                "current_node": langgraph_state["current_node"],
                "retry_count": langgraph_state["retry_count"],
                "has_checkpoint": langgraph_state["checkpoint_data"] is not None,
                "active_agents": langgraph_state["coordination_state"]["active_agents"],
                "last_sync": datetime.now().isoformat()
            })
            
            # 同步智能体结果到执行计划
            agent_results = langgraph_state["workflow_context"]["agent_results"]
            if agent_results:
                legacy_state["execution_plan"]["agent_results"] = agent_results
            
            # 同步协调计划
            coordination_plan = langgraph_state["workflow_context"]["coordination_plan"]
            if coordination_plan:
                legacy_state["execution_plan"]["coordination_plan"] = coordination_plan
            
            self.logger.debug(
                "LangGraph状态已转换为现有系统状态",
                task_id=legacy_state["task_id"],
                workflow_phase=workflow_phase.value,
                task_status=legacy_state["status"]
            )
            
            return legacy_state
            
        except Exception as e:
            self.logger.error("状态转换失败", error=str(e))
            raise
    
    def legacy_to_langgraph(
        self, 
        legacy_state: LegacyTaskState,
        existing_langgraph_state: Optional[LangGraphTaskState] = None
    ) -> LangGraphTaskState:
        """将现有系统状态转换为LangGraph状态"""
        try:
            from ..core.state import create_initial_state, update_workflow_phase
            
            # 如果有现有的LangGraph状态，则更新它；否则创建新的
            if existing_langgraph_state:
                langgraph_state = existing_langgraph_state.copy()
                # 更新基础任务状态
                langgraph_state["task_state"] = legacy_state
            else:
                # 创建新的LangGraph状态
                langgraph_state = create_initial_state(
                    title=legacy_state["title"],
                    description=legacy_state["description"],
                    task_type=legacy_state["task_type"],
                    priority=legacy_state["priority"],
                    input_data=legacy_state["input_data"],
                    requester_id=legacy_state["requester_id"]
                )
                # 替换task_state
                langgraph_state["task_state"] = legacy_state
            
            # 从现有系统状态同步工作流阶段
            task_status = legacy_state["status"]
            status_to_phase = {
                TaskStatus.PENDING: WorkflowPhase.INITIALIZATION,
                TaskStatus.ANALYZING: WorkflowPhase.ANALYSIS,
                TaskStatus.DECOMPOSED: WorkflowPhase.DECOMPOSITION,
                TaskStatus.IN_PROGRESS: WorkflowPhase.EXECUTION,
                TaskStatus.REVIEWING: WorkflowPhase.REVIEW,
                TaskStatus.COMPLETED: WorkflowPhase.COMPLETION,
                TaskStatus.FAILED: WorkflowPhase.ERROR_HANDLING,
                TaskStatus.CANCELLED: WorkflowPhase.COMPLETION
            }
            
            if task_status in status_to_phase:
                target_phase = status_to_phase[task_status]
                if langgraph_state["workflow_context"]["current_phase"] != target_phase:
                    langgraph_state = update_workflow_phase(langgraph_state, target_phase)
            
            # 从元数据恢复LangGraph特有信息
            langgraph_metadata = legacy_state["metadata"].get("langgraph_metadata", {})
            if langgraph_metadata:
                if "current_node" in langgraph_metadata:
                    langgraph_state["current_node"] = langgraph_metadata["current_node"]
                if "retry_count" in langgraph_metadata:
                    langgraph_state["retry_count"] = langgraph_metadata["retry_count"]
                if "active_agents" in langgraph_metadata:
                    langgraph_state["coordination_state"]["active_agents"] = langgraph_metadata["active_agents"]
            
            # 恢复智能体结果
            if "agent_results" in legacy_state["execution_plan"]:
                langgraph_state["workflow_context"]["agent_results"] = legacy_state["execution_plan"]["agent_results"]
            
            # 恢复协调计划
            if "coordination_plan" in legacy_state["execution_plan"]:
                langgraph_state["workflow_context"]["coordination_plan"] = legacy_state["execution_plan"]["coordination_plan"]
            
            self.logger.debug(
                "现有系统状态已转换为LangGraph状态",
                task_id=legacy_state["task_id"],
                task_status=task_status,
                workflow_phase=langgraph_state["workflow_context"]["current_phase"].value
            )
            
            return langgraph_state
            
        except Exception as e:
            self.logger.error("状态转换失败", error=str(e))
            raise
    
    async def sync_to_legacy_system(
        self, 
        langgraph_state: LangGraphTaskState,
        force_sync: bool = False
    ) -> bool:
        """同步LangGraph状态到现有系统"""
        if not self.sync_enabled and not force_sync:
            return False
        
        try:
            task_id = langgraph_state["task_state"]["task_id"]
            
            # 检查是否需要同步（避免不必要的同步）
            if not force_sync and self._should_skip_sync(task_id, langgraph_state):
                return True
            
            # 转换状态
            legacy_state = self.langgraph_to_legacy(langgraph_state)
            
            # 更新缓存
            self.state_cache[task_id] = {
                "legacy_state": legacy_state,
                "langgraph_state_hash": self._calculate_state_hash(langgraph_state),
                "last_sync": datetime.now().isoformat()
            }
            
            # 调用同步回调
            for callback in self.sync_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(task_id, legacy_state)
                    else:
                        callback(task_id, legacy_state)
                except Exception as e:
                    self.logger.error("同步回调执行失败", callback=str(callback), error=str(e))
            
            self.logger.info(
                "状态已同步到现有系统",
                task_id=task_id,
                workflow_phase=langgraph_state["workflow_context"]["current_phase"].value
            )
            
            return True
            
        except Exception as e:
            self.logger.error("同步到现有系统失败", error=str(e))
            return False
    
    async def sync_from_legacy_system(
        self, 
        legacy_state: LegacyTaskState,
        existing_langgraph_state: Optional[LangGraphTaskState] = None
    ) -> LangGraphTaskState:
        """从现有系统同步状态到LangGraph"""
        try:
            # 转换状态
            langgraph_state = self.legacy_to_langgraph(legacy_state, existing_langgraph_state)
            
            # 更新缓存
            task_id = legacy_state["task_id"]
            self.state_cache[task_id] = {
                "legacy_state": legacy_state,
                "langgraph_state_hash": self._calculate_state_hash(langgraph_state),
                "last_sync": datetime.now().isoformat()
            }
            
            self.logger.info(
                "状态已从现有系统同步",
                task_id=task_id,
                task_status=legacy_state["status"]
            )
            
            return langgraph_state
            
        except Exception as e:
            self.logger.error("从现有系统同步失败", error=str(e))
            raise
    
    def validate_state_consistency(
        self, 
        langgraph_state: LangGraphTaskState,
        legacy_state: LegacyTaskState
    ) -> Dict[str, Any]:
        """验证状态一致性"""
        inconsistencies = []
        
        try:
            # 检查基本字段一致性
            if langgraph_state["task_state"]["task_id"] != legacy_state["task_id"]:
                inconsistencies.append("task_id不一致")
            
            if langgraph_state["task_state"]["title"] != legacy_state["title"]:
                inconsistencies.append("title不一致")
            
            if langgraph_state["task_state"]["status"] != legacy_state["status"]:
                inconsistencies.append(f"status不一致: LangGraph={langgraph_state['task_state']['status']}, Legacy={legacy_state['status']}")
            
            # 检查工作流阶段与任务状态的一致性
            workflow_phase = langgraph_state["workflow_context"]["current_phase"]
            task_status = legacy_state["status"]
            
            expected_phases = {
                TaskStatus.PENDING: [WorkflowPhase.INITIALIZATION],
                TaskStatus.ANALYZING: [WorkflowPhase.ANALYSIS],
                TaskStatus.DECOMPOSED: [WorkflowPhase.DECOMPOSITION],
                TaskStatus.IN_PROGRESS: [WorkflowPhase.COORDINATION, WorkflowPhase.EXECUTION],
                TaskStatus.REVIEWING: [WorkflowPhase.REVIEW],
                TaskStatus.COMPLETED: [WorkflowPhase.COMPLETION],
                TaskStatus.FAILED: [WorkflowPhase.ERROR_HANDLING],
                TaskStatus.CANCELLED: [WorkflowPhase.COMPLETION]
            }
            
            if task_status in expected_phases:
                if workflow_phase not in expected_phases[task_status]:
                    inconsistencies.append(f"工作流阶段与任务状态不匹配: phase={workflow_phase.value}, status={task_status}")
            
            return {
                "consistent": len(inconsistencies) == 0,
                "inconsistencies": inconsistencies,
                "validation_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error("状态一致性验证失败", error=str(e))
            return {
                "consistent": False,
                "inconsistencies": [f"验证过程出错: {str(e)}"],
                "validation_time": datetime.now().isoformat()
            }
    
    def _should_skip_sync(self, task_id: str, langgraph_state: LangGraphTaskState) -> bool:
        """判断是否应该跳过同步"""
        if task_id not in self.state_cache:
            return False
        
        cached_info = self.state_cache[task_id]
        current_hash = self._calculate_state_hash(langgraph_state)
        
        # 如果状态哈希相同，跳过同步
        return cached_info.get("langgraph_state_hash") == current_hash
    
    def _calculate_state_hash(self, langgraph_state: LangGraphTaskState) -> str:
        """计算状态哈希值"""
        import hashlib
        
        # 选择关键字段计算哈希
        key_data = {
            "task_id": langgraph_state["task_state"]["task_id"],
            "status": langgraph_state["task_state"]["status"],
            "workflow_phase": langgraph_state["workflow_context"]["current_phase"].value,
            "current_node": langgraph_state["current_node"],
            "retry_count": langgraph_state["retry_count"],
            "updated_at": langgraph_state["task_state"]["updated_at"].isoformat() if langgraph_state["task_state"]["updated_at"] else None
        }
        
        data_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def get_sync_statistics(self) -> Dict[str, Any]:
        """获取同步统计信息"""
        return {
            "total_cached_states": len(self.state_cache),
            "sync_enabled": self.sync_enabled,
            "registered_callbacks": len(self.sync_callbacks),
            "cache_keys": list(self.state_cache.keys())
        }
    
    def clear_cache(self, task_id: Optional[str] = None):
        """清理缓存"""
        if task_id:
            if task_id in self.state_cache:
                del self.state_cache[task_id]
                self.logger.info("已清理指定任务的缓存", task_id=task_id)
        else:
            self.state_cache.clear()
            self.logger.info("已清理所有缓存")