"""消息总线适配器 - 集成现有的消息总线系统"""

import asyncio
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import json
import uuid

from ..utils.logging import LoggerMixin
from ..core.state import LangGraphTaskState, AgentMessage


class MessageBusAdapter(LoggerMixin):
    """消息总线适配器 - 处理LangGraph与现有消息系统的集成"""
    
    def __init__(self):
        super().__init__()
        self.message_handlers: Dict[str, List[Callable]] = {}
        self.message_queue: List[Dict[str, Any]] = []
        self.legacy_message_bus = None
        self.message_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000
    
    def set_legacy_message_bus(self, message_bus):
        """设置现有的消息总线实例"""
        self.legacy_message_bus = message_bus
        self.logger.info("现有消息总线已设置")
    
    def register_message_handler(
        self, 
        message_type: str, 
        handler: Callable[[Dict[str, Any]], Any]
    ):
        """注册消息处理器"""
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        
        self.message_handlers[message_type].append(handler)
        self.logger.info("消息处理器已注册", message_type=message_type)
    
    async def send_to_legacy_system(
        self,
        message_type: str,
        content: Dict[str, Any],
        sender_id: str,
        recipient_id: Optional[str] = None
    ) -> bool:
        """发送消息到现有系统"""
        try:
            # 构造现有系统格式的消息
            legacy_message = {
                "message_id": str(uuid.uuid4()),
                "message_type": message_type,
                "sender_id": sender_id,
                "recipient_id": recipient_id,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "source": "langgraph_system"
            }
            
            # 记录消息历史
            self._record_message(legacy_message, "outgoing")
            
            # 如果有现有消息总线，使用它发送
            if self.legacy_message_bus:
                if hasattr(self.legacy_message_bus, 'send_message'):
                    if asyncio.iscoroutinefunction(self.legacy_message_bus.send_message):
                        await self.legacy_message_bus.send_message(legacy_message)
                    else:
                        self.legacy_message_bus.send_message(legacy_message)
                elif hasattr(self.legacy_message_bus, 'publish'):
                    if asyncio.iscoroutinefunction(self.legacy_message_bus.publish):
                        await self.legacy_message_bus.publish(message_type, legacy_message)
                    else:
                        self.legacy_message_bus.publish(message_type, legacy_message)
                else:
                    self.logger.warning("现有消息总线没有可用的发送方法")
                    return False
            else:
                # 如果没有现有消息总线，添加到队列
                self.message_queue.append(legacy_message)
                self.logger.info("消息已添加到队列", message_id=legacy_message["message_id"])
            
            self.logger.info(
                "消息已发送到现有系统",
                message_type=message_type,
                sender_id=sender_id,
                recipient_id=recipient_id
            )
            
            return True
            
        except Exception as e:
            self.logger.error("发送消息到现有系统失败", error=str(e))
            return False
    
    async def receive_from_legacy_system(self, legacy_message: Dict[str, Any]) -> bool:
        """接收来自现有系统的消息"""
        try:
            # 记录消息历史
            self._record_message(legacy_message, "incoming")
            
            # 转换为LangGraph格式
            langgraph_message = self._convert_to_langgraph_message(legacy_message)
            
            # 调用注册的处理器
            message_type = legacy_message.get("message_type", "unknown")
            if message_type in self.message_handlers:
                for handler in self.message_handlers[message_type]:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(langgraph_message)
                        else:
                            handler(langgraph_message)
                    except Exception as e:
                        self.logger.error(
                            "消息处理器执行失败",
                            handler=str(handler),
                            error=str(e)
                        )
            
            self.logger.info(
                "已接收现有系统消息",
                message_type=message_type,
                sender_id=legacy_message.get("sender_id")
            )
            
            return True
            
        except Exception as e:
            self.logger.error("接收现有系统消息失败", error=str(e))
            return False
    
    def convert_langgraph_message_to_legacy(self, agent_message: AgentMessage) -> Dict[str, Any]:
        """将LangGraph智能体消息转换为现有系统格式"""
        return {
            "message_id": agent_message["message_id"],
            "message_type": agent_message["message_type"],
            "sender_id": agent_message["sender_agent"],
            "recipient_id": agent_message["receiver_agent"],
            "content": agent_message["content"],
            "timestamp": agent_message["timestamp"].isoformat(),
            "priority": agent_message["priority"],
            "requires_response": agent_message["requires_response"],
            "source": "langgraph_agent"
        }
    
    def _convert_to_langgraph_message(self, legacy_message: Dict[str, Any]) -> AgentMessage:
        """将现有系统消息转换为LangGraph格式"""
        timestamp = legacy_message.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        elif timestamp is None:
            timestamp = datetime.now()
        
        return AgentMessage(
            message_id=legacy_message.get("message_id", str(uuid.uuid4())),
            sender_agent=legacy_message.get("sender_id", "unknown"),
            receiver_agent=legacy_message.get("recipient_id"),
            message_type=legacy_message.get("message_type", "unknown"),
            content=legacy_message.get("content", {}),
            timestamp=timestamp,
            priority=legacy_message.get("priority", 1),
            requires_response=legacy_message.get("requires_response", False)
        )
    
    async def sync_agent_messages(
        self,
        langgraph_state: LangGraphTaskState,
        direction: str = "both"  # "to_legacy", "from_legacy", "both"
    ) -> bool:
        """同步智能体消息"""
        try:
            success = True
            
            if direction in ["to_legacy", "both"]:
                # 同步LangGraph消息到现有系统
                for agent_message in langgraph_state["agent_messages"]:
                    legacy_message = self.convert_langgraph_message_to_legacy(agent_message)
                    
                    # 检查是否已经同步过
                    if not self._is_message_synced(legacy_message["message_id"]):
                        sync_success = await self.send_to_legacy_system(
                            legacy_message["message_type"],
                            legacy_message["content"],
                            legacy_message["sender_id"],
                            legacy_message["recipient_id"]
                        )
                        
                        if not sync_success:
                            success = False
                        else:
                            self._mark_message_synced(legacy_message["message_id"])
            
            if direction in ["from_legacy", "both"]:
                # 从现有系统同步消息（这通常通过消息处理器被动接收）
                # 这里可以实现主动拉取逻辑，如果现有系统支持的话
                pass
            
            return success
            
        except Exception as e:
            self.logger.error("同步智能体消息失败", error=str(e))
            return False
    
    def _record_message(self, message: Dict[str, Any], direction: str):
        """记录消息历史"""
        history_entry = {
            "message": message,
            "direction": direction,
            "recorded_at": datetime.now().isoformat()
        }
        
        self.message_history.append(history_entry)
        
        # 限制历史记录大小
        if len(self.message_history) > self.max_history_size:
            self.message_history = self.message_history[-self.max_history_size:]
    
    def _is_message_synced(self, message_id: str) -> bool:
        """检查消息是否已同步"""
        for entry in self.message_history:
            if (entry["message"]["message_id"] == message_id and 
                entry["direction"] == "outgoing"):
                return True
        return False
    
    def _mark_message_synced(self, message_id: str):
        """标记消息已同步"""
        # 消息已经在_record_message中记录，这里可以添加额外的标记逻辑
        pass
    
    def get_message_statistics(self) -> Dict[str, Any]:
        """获取消息统计信息"""
        total_messages = len(self.message_history)
        outgoing_count = sum(1 for entry in self.message_history if entry["direction"] == "outgoing")
        incoming_count = sum(1 for entry in self.message_history if entry["direction"] == "incoming")
        
        # 按消息类型统计
        message_types = {}
        for entry in self.message_history:
            msg_type = entry["message"].get("message_type", "unknown")
            message_types[msg_type] = message_types.get(msg_type, 0) + 1
        
        return {
            "total_messages": total_messages,
            "outgoing_messages": outgoing_count,
            "incoming_messages": incoming_count,
            "message_types": message_types,
            "queued_messages": len(self.message_queue),
            "registered_handlers": {
                msg_type: len(handlers) 
                for msg_type, handlers in self.message_handlers.items()
            },
            "has_legacy_bus": self.legacy_message_bus is not None
        }
    
    def get_queued_messages(self) -> List[Dict[str, Any]]:
        """获取队列中的消息"""
        return self.message_queue.copy()
    
    def clear_message_queue(self):
        """清空消息队列"""
        cleared_count = len(self.message_queue)
        self.message_queue.clear()
        self.logger.info("消息队列已清空", cleared_count=cleared_count)
    
    def get_message_history(
        self, 
        limit: int = 100,
        message_type: Optional[str] = None,
        direction: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取消息历史"""
        history = self.message_history
        
        # 过滤条件
        if message_type:
            history = [
                entry for entry in history 
                if entry["message"].get("message_type") == message_type
            ]
        
        if direction:
            history = [
                entry for entry in history 
                if entry["direction"] == direction
            ]
        
        # 返回最新的记录
        return history[-limit:] if limit > 0 else history