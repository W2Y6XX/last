"""现有系统桥接器 - 统一的集成接口"""

import asyncio
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

from ..utils.logging import LoggerMixin
from ..core.state import LangGraphTaskState
from ..legacy.task_state import TaskState as LegacyTaskState
from .state_adapter import StateAdapter
from .message_adapter import MessageBusAdapter


class LegacySystemBridge(LoggerMixin):
    """现有系统桥接器 - 提供LangGraph与现有智能体系统的统一集成接口"""
    
    def __init__(self):
        super().__init__()
        self.state_adapter = StateAdapter()
        self.message_adapter = MessageBusAdapter()
        self.legacy_agents: Dict[str, Any] = {}
        self.integration_callbacks: Dict[str, List[Callable]] = {}
        self.bridge_enabled = True
        self.sync_interval = 30  # 秒
        self._sync_task: Optional[asyncio.Task] = None
    
    def register_legacy_agent(self, agent_id: str, agent_instance: Any):
        """注册现有智能体实例"""
        self.legacy_agents[agent_id] = agent_instance
        self.logger.info("现有智能体已注册", agent_id=agent_id, agent_type=type(agent_instance).__name__)
    
    def register_legacy_message_bus(self, message_bus: Any):
        """注册现有消息总线"""
        self.message_adapter.set_legacy_message_bus(message_bus)
        self.logger.info("现有消息总线已注册")
    
    def register_integration_callback(
        self, 
        event_type: str, 
        callback: Callable[[str, Dict[str, Any]], Any]
    ):
        """注册集成事件回调"""
        if event_type not in self.integration_callbacks:
            self.integration_callbacks[event_type] = []
        
        self.integration_callbacks[event_type].append(callback)
        self.logger.info("集成回调已注册", event_type=event_type)
    
    async def initialize_bridge(self) -> bool:
        """初始化桥接器"""
        try:
            # 注册状态同步回调
            self.state_adapter.register_sync_callback(self._on_state_sync)
            
            # 注册消息处理器
            self.message_adapter.register_message_handler("task_update", self._handle_task_update)
            self.message_adapter.register_message_handler("agent_status", self._handle_agent_status)
            self.message_adapter.register_message_handler("coordination_request", self._handle_coordination_request)
            
            # 启动定期同步任务
            if self.sync_interval > 0:
                self._sync_task = asyncio.create_task(self._periodic_sync())
            
            self.logger.info("桥接器已初始化")
            return True
            
        except Exception as e:
            self.logger.error("桥接器初始化失败", error=str(e))
            return False
    
    async def shutdown_bridge(self):
        """关闭桥接器"""
        try:
            self.bridge_enabled = False
            
            # 停止同步任务
            if self._sync_task and not self._sync_task.done():
                self._sync_task.cancel()
                try:
                    await self._sync_task
                except asyncio.CancelledError:
                    pass
            
            self.logger.info("桥接器已关闭")
            
        except Exception as e:
            self.logger.error("桥接器关闭失败", error=str(e))
    
    async def sync_state_to_legacy(
        self, 
        langgraph_state: LangGraphTaskState,
        force_sync: bool = False
    ) -> bool:
        """同步LangGraph状态到现有系统"""
        if not self.bridge_enabled:
            return False
        
        try:
            # 状态同步
            state_sync_success = await self.state_adapter.sync_to_legacy_system(
                langgraph_state, force_sync
            )
            
            # 消息同步
            message_sync_success = await self.message_adapter.sync_agent_messages(
                langgraph_state, "to_legacy"
            )
            
            # 触发集成回调
            await self._trigger_callbacks("state_synced", {
                "task_id": langgraph_state["task_state"]["task_id"],
                "state_sync_success": state_sync_success,
                "message_sync_success": message_sync_success
            })
            
            return state_sync_success and message_sync_success
            
        except Exception as e:
            self.logger.error("同步状态到现有系统失败", error=str(e))
            return False
    
    async def sync_state_from_legacy(
        self, 
        legacy_state: LegacyTaskState,
        existing_langgraph_state: Optional[LangGraphTaskState] = None
    ) -> Optional[LangGraphTaskState]:
        """从现有系统同步状态到LangGraph"""
        if not self.bridge_enabled:
            return existing_langgraph_state
        
        try:
            # 状态同步
            langgraph_state = await self.state_adapter.sync_from_legacy_system(
                legacy_state, existing_langgraph_state
            )
            
            # 触发集成回调
            await self._trigger_callbacks("state_received", {
                "task_id": legacy_state["task_id"],
                "legacy_state": legacy_state
            })
            
            return langgraph_state
            
        except Exception as e:
            self.logger.error("从现有系统同步状态失败", error=str(e))
            return existing_langgraph_state
    
    async def execute_legacy_agent(
        self, 
        agent_id: str, 
        task_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """执行现有智能体"""
        if not self.bridge_enabled or agent_id not in self.legacy_agents:
            return None
        
        try:
            agent = self.legacy_agents[agent_id]
            
            # 调用智能体的process_task方法
            if hasattr(agent, 'process_task'):
                if asyncio.iscoroutinefunction(agent.process_task):
                    result = await agent.process_task(task_data)
                else:
                    result = agent.process_task(task_data)
                
                # 触发集成回调
                await self._trigger_callbacks("agent_executed", {
                    "agent_id": agent_id,
                    "task_data": task_data,
                    "result": result
                })
                
                return result
            else:
                self.logger.warning("智能体没有process_task方法", agent_id=agent_id)
                return None
                
        except Exception as e:
            self.logger.error("执行现有智能体失败", agent_id=agent_id, error=str(e))
            return None
    
    async def validate_integration_consistency(
        self, 
        langgraph_state: LangGraphTaskState
    ) -> Dict[str, Any]:
        """验证集成一致性"""
        try:
            # 转换为现有系统状态进行比较
            legacy_state = self.state_adapter.langgraph_to_legacy(langgraph_state)
            
            # 验证状态一致性
            consistency_result = self.state_adapter.validate_state_consistency(
                langgraph_state, legacy_state
            )
            
            # 获取消息统计
            message_stats = self.message_adapter.get_message_statistics()
            
            # 获取同步统计
            sync_stats = self.state_adapter.get_sync_statistics()
            
            return {
                "state_consistency": consistency_result,
                "message_statistics": message_stats,
                "sync_statistics": sync_stats,
                "bridge_status": {
                    "enabled": self.bridge_enabled,
                    "registered_agents": len(self.legacy_agents),
                    "registered_callbacks": sum(len(callbacks) for callbacks in self.integration_callbacks.values())
                },
                "validation_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error("验证集成一致性失败", error=str(e))
            return {
                "error": str(e),
                "validation_time": datetime.now().isoformat()
            }
    
    async def _periodic_sync(self):
        """定期同步任务"""
        while self.bridge_enabled:
            try:
                await asyncio.sleep(self.sync_interval)
                
                if not self.bridge_enabled:
                    break
                
                # 执行定期同步逻辑
                await self._trigger_callbacks("periodic_sync", {
                    "sync_time": datetime.now().isoformat()
                })
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("定期同步任务出错", error=str(e))
    
    async def _on_state_sync(self, task_id: str, legacy_state: Dict[str, Any]):
        """状态同步回调"""
        self.logger.debug("状态同步回调触发", task_id=task_id)
        
        # 这里可以添加额外的同步逻辑
        # 例如通知现有系统的其他组件
        
        await self._trigger_callbacks("legacy_state_updated", {
            "task_id": task_id,
            "legacy_state": legacy_state
        })
    
    async def _handle_task_update(self, message: Dict[str, Any]):
        """处理任务更新消息"""
        self.logger.info("收到任务更新消息", message_id=message.get("message_id"))
        
        await self._trigger_callbacks("task_update_received", {
            "message": message
        })
    
    async def _handle_agent_status(self, message: Dict[str, Any]):
        """处理智能体状态消息"""
        self.logger.info("收到智能体状态消息", sender=message.get("sender_agent"))
        
        await self._trigger_callbacks("agent_status_received", {
            "message": message
        })
    
    async def _handle_coordination_request(self, message: Dict[str, Any]):
        """处理协调请求消息"""
        self.logger.info("收到协调请求消息", sender=message.get("sender_agent"))
        
        await self._trigger_callbacks("coordination_request_received", {
            "message": message
        })
    
    async def _trigger_callbacks(self, event_type: str, data: Dict[str, Any]):
        """触发集成回调"""
        if event_type in self.integration_callbacks:
            for callback in self.integration_callbacks[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event_type, data)
                    else:
                        callback(event_type, data)
                except Exception as e:
                    self.logger.error(
                        "集成回调执行失败",
                        event_type=event_type,
                        callback=str(callback),
                        error=str(e)
                    )
    
    def get_bridge_status(self) -> Dict[str, Any]:
        """获取桥接器状态"""
        return {
            "bridge_enabled": self.bridge_enabled,
            "registered_agents": list(self.legacy_agents.keys()),
            "sync_interval": self.sync_interval,
            "sync_task_running": self._sync_task is not None and not self._sync_task.done(),
            "state_adapter_stats": self.state_adapter.get_sync_statistics(),
            "message_adapter_stats": self.message_adapter.get_message_statistics(),
            "integration_callbacks": {
                event_type: len(callbacks)
                for event_type, callbacks in self.integration_callbacks.items()
            }
        }