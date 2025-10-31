"""
MVP2前端WebSocket实时通信处理器
提供任务状态实时更新和智能体协作状态广播
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Any, Optional
import json
import asyncio
import logging
from datetime import datetime
from enum import Enum

from ..integration.mvp2_adapter import mvp2_adapter

logger = logging.getLogger(__name__)


class MVP2MessageType(Enum):
    """MVP2 WebSocket消息类型"""
    TASK_UPDATE = "task_update"
    TASK_CREATED = "task_created"
    TASK_COMPLETED = "task_completed"
    TASK_DELETED = "task_deleted"
    CHAT_MESSAGE = "chat_message"
    AGENT_STATUS = "agent_status"
    SYSTEM_NOTIFICATION = "system_notification"
    HEARTBEAT = "heartbeat"
    ERROR = "error"


class MVP2ConnectionManager:
    """MVP2 WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}
        self.heartbeat_interval = 30  # 秒
        self.heartbeat_task = None
    
    async def connect(self, websocket: WebSocket, client_info: Dict[str, Any] = None):
        """建立WebSocket连接"""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # 存储连接信息
        self.connection_info[websocket] = {
            "connected_at": datetime.now().isoformat(),
            "client_info": client_info or {},
            "last_heartbeat": datetime.now().isoformat(),
            "message_count": 0
        }
        
        logger.info(f"MVP2 WebSocket连接建立: {len(self.active_connections)}个活跃连接")
        
        # 发送欢迎消息
        await self.send_personal_message(websocket, {
            "type": MVP2MessageType.SYSTEM_NOTIFICATION.value,
            "message": "连接成功，实时通信已启用",
            "timestamp": datetime.now().isoformat()
        })
        
        # 启动心跳检测
        if not self.heartbeat_task:
            self.heartbeat_task = asyncio.create_task(self.heartbeat_loop())
    
    def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            
        if websocket in self.connection_info:
            connection_duration = datetime.now() - datetime.fromisoformat(
                self.connection_info[websocket]["connected_at"]
            )
            logger.info(f"MVP2 WebSocket连接断开，持续时间: {connection_duration}")
            del self.connection_info[websocket]
        
        logger.info(f"剩余活跃连接: {len(self.active_connections)}")
        
        # 如果没有活跃连接，停止心跳检测
        if not self.active_connections and self.heartbeat_task:
            self.heartbeat_task.cancel()
            self.heartbeat_task = None
    
    async def send_personal_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """发送个人消息"""
        try:
            await websocket.send_text(json.dumps(message, ensure_ascii=False))
            
            # 更新消息计数
            if websocket in self.connection_info:
                self.connection_info[websocket]["message_count"] += 1
                
        except Exception as e:
            logger.error(f"发送个人消息失败: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any], exclude: Optional[WebSocket] = None):
        """广播消息给所有连接"""
        if not self.active_connections:
            return
        
        message["broadcast"] = True
        message["timestamp"] = datetime.now().isoformat()
        
        disconnected = []
        for connection in self.active_connections:
            if connection == exclude:
                continue
                
            try:
                await connection.send_text(json.dumps(message, ensure_ascii=False))
                
                # 更新消息计数
                if connection in self.connection_info:
                    self.connection_info[connection]["message_count"] += 1
                    
            except Exception as e:
                logger.error(f"广播消息失败: {e}")
                disconnected.append(connection)
        
        # 清理断开的连接
        for connection in disconnected:
            self.disconnect(connection)
        
        logger.info(f"广播消息给 {len(self.active_connections)} 个连接")
    
    async def heartbeat_loop(self):
        """心跳检测循环"""
        while self.active_connections:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                heartbeat_message = {
                    "type": MVP2MessageType.HEARTBEAT.value,
                    "timestamp": datetime.now().isoformat(),
                    "active_connections": len(self.active_connections)
                }
                
                await self.broadcast(heartbeat_message)
                
            except asyncio.CancelledError:
                logger.info("心跳检测任务已取消")
                break
            except Exception as e:
                logger.error(f"心跳检测失败: {e}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计信息"""
        total_messages = sum(
            info.get("message_count", 0) 
            for info in self.connection_info.values()
        )
        
        return {
            "active_connections": len(self.active_connections),
            "total_messages_sent": total_messages,
            "heartbeat_interval": self.heartbeat_interval,
            "connections_info": [
                {
                    "connected_at": info["connected_at"],
                    "last_heartbeat": info["last_heartbeat"],
                    "message_count": info["message_count"],
                    "client_info": info["client_info"]
                }
                for info in self.connection_info.values()
            ]
        }


class MVP2WebSocketHandler:
    """MVP2 WebSocket消息处理器"""
    
    def __init__(self, connection_manager: MVP2ConnectionManager):
        self.connection_manager = connection_manager
        self.message_handlers = {
            "ping": self.handle_ping,
            "task_subscribe": self.handle_task_subscribe,
            "chat_subscribe": self.handle_chat_subscribe,
            "agent_subscribe": self.handle_agent_subscribe,
            "get_status": self.handle_get_status
        }
    
    async def handle_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """处理接收到的WebSocket消息"""
        try:
            message_type = message.get("type")
            
            if message_type in self.message_handlers:
                await self.message_handlers[message_type](websocket, message)
            else:
                await self.send_error(websocket, f"未知消息类型: {message_type}")
                
        except Exception as e:
            logger.error(f"处理WebSocket消息失败: {e}")
            await self.send_error(websocket, f"消息处理错误: {str(e)}")
    
    async def handle_ping(self, websocket: WebSocket, message: Dict[str, Any]):
        """处理ping消息"""
        await self.connection_manager.send_personal_message(websocket, {
            "type": "pong",
            "timestamp": datetime.now().isoformat(),
            "original_message": message
        })
        
        # 更新心跳时间
        if websocket in self.connection_manager.connection_info:
            self.connection_manager.connection_info[websocket]["last_heartbeat"] = datetime.now().isoformat()
    
    async def handle_task_subscribe(self, websocket: WebSocket, message: Dict[str, Any]):
        """处理任务订阅"""
        task_id = message.get("task_id")
        
        response = {
            "type": "task_subscription_confirmed",
            "task_id": task_id,
            "message": f"已订阅任务 {task_id} 的状态更新",
            "timestamp": datetime.now().isoformat()
        }
        
        await self.connection_manager.send_personal_message(websocket, response)
    
    async def handle_chat_subscribe(self, websocket: WebSocket, message: Dict[str, Any]):
        """处理聊天订阅"""
        response = {
            "type": "chat_subscription_confirmed",
            "message": "已订阅聊天消息推送",
            "timestamp": datetime.now().isoformat()
        }
        
        await self.connection_manager.send_personal_message(websocket, response)
    
    async def handle_agent_subscribe(self, websocket: WebSocket, message: Dict[str, Any]):
        """处理智能体状态订阅"""
        response = {
            "type": "agent_subscription_confirmed",
            "message": "已订阅智能体状态更新",
            "timestamp": datetime.now().isoformat()
        }
        
        await self.connection_manager.send_personal_message(websocket, response)
    
    async def handle_get_status(self, websocket: WebSocket, message: Dict[str, Any]):
        """处理状态查询"""
        status = {
            "type": "status_response",
            "system_status": "healthy",
            "connection_stats": self.connection_manager.get_connection_stats(),
            "adapter_status": mvp2_adapter.get_adapter_status(),
            "timestamp": datetime.now().isoformat()
        }
        
        await self.connection_manager.send_personal_message(websocket, status)
    
    async def send_error(self, websocket: WebSocket, error_message: str):
        """发送错误消息"""
        error_response = {
            "type": MVP2MessageType.ERROR.value,
            "error": True,
            "message": error_message,
            "timestamp": datetime.now().isoformat()
        }
        
        await self.connection_manager.send_personal_message(websocket, error_response)


class MVP2EventBroadcaster:
    """MVP2事件广播器"""
    
    def __init__(self, connection_manager: MVP2ConnectionManager):
        self.connection_manager = connection_manager
    
    async def broadcast_task_update(self, task_data: Dict[str, Any]):
        """广播任务更新事件"""
        message = {
            "type": MVP2MessageType.TASK_UPDATE.value,
            "data": task_data,
            "message": f"任务 {task_data.get('name', 'Unknown')} 已更新"
        }
        
        await self.connection_manager.broadcast(message)
    
    async def broadcast_task_created(self, task_data: Dict[str, Any]):
        """广播任务创建事件"""
        message = {
            "type": MVP2MessageType.TASK_CREATED.value,
            "data": task_data,
            "message": f"新任务 {task_data.get('name', 'Unknown')} 已创建"
        }
        
        await self.connection_manager.broadcast(message)
    
    async def broadcast_task_completed(self, task_data: Dict[str, Any]):
        """广播任务完成事件"""
        message = {
            "type": MVP2MessageType.TASK_COMPLETED.value,
            "data": task_data,
            "message": f"任务 {task_data.get('name', 'Unknown')} 已完成"
        }
        
        await self.connection_manager.broadcast(message)
    
    async def broadcast_chat_message(self, chat_data: Dict[str, Any]):
        """广播聊天消息"""
        message = {
            "type": MVP2MessageType.CHAT_MESSAGE.value,
            "data": chat_data,
            "message": "新的聊天消息"
        }
        
        await self.connection_manager.broadcast(message)
    
    async def broadcast_agent_status(self, agent_data: Dict[str, Any]):
        """广播智能体状态"""
        message = {
            "type": MVP2MessageType.AGENT_STATUS.value,
            "data": agent_data,
            "message": f"智能体 {agent_data.get('agent_type', 'Unknown')} 状态更新"
        }
        
        await self.connection_manager.broadcast(message)
    
    async def broadcast_system_notification(self, notification: str, level: str = "info"):
        """广播系统通知"""
        message = {
            "type": MVP2MessageType.SYSTEM_NOTIFICATION.value,
            "level": level,
            "message": notification,
            "timestamp": datetime.now().isoformat()
        }
        
        await self.connection_manager.broadcast(message)


# 全局实例
mvp2_connection_manager = MVP2ConnectionManager()
mvp2_websocket_handler = MVP2WebSocketHandler(mvp2_connection_manager)
mvp2_event_broadcaster = MVP2EventBroadcaster(mvp2_connection_manager)


async def handle_mvp2_websocket(websocket: WebSocket):
    """处理MVP2 WebSocket连接"""
    client_info = {
        "user_agent": websocket.headers.get("user-agent", ""),
        "origin": websocket.headers.get("origin", ""),
        "client_ip": websocket.client.host if websocket.client else "unknown"
    }
    
    await mvp2_connection_manager.connect(websocket, client_info)
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await mvp2_websocket_handler.handle_message(websocket, message)
            except json.JSONDecodeError:
                await mvp2_websocket_handler.send_error(websocket, "无效的JSON格式")
            except Exception as e:
                await mvp2_websocket_handler.send_error(websocket, f"消息处理错误: {str(e)}")
                
    except WebSocketDisconnect:
        logger.info("MVP2 WebSocket客户端断开连接")
    except Exception as e:
        logger.error(f"MVP2 WebSocket连接错误: {e}")
    finally:
        mvp2_connection_manager.disconnect(websocket)


# 状态同步回调函数
async def sync_state_to_mvp2_frontend(data: Dict[str, Any]):
    """同步状态到MVP2前端"""
    try:
        event_type = data.get("event_type")
        
        if event_type == "task_update":
            await mvp2_event_broadcaster.broadcast_task_update(data.get("task_data", {}))
        elif event_type == "task_created":
            await mvp2_event_broadcaster.broadcast_task_created(data.get("task_data", {}))
        elif event_type == "task_completed":
            await mvp2_event_broadcaster.broadcast_task_completed(data.get("task_data", {}))
        elif event_type == "chat_message":
            await mvp2_event_broadcaster.broadcast_chat_message(data.get("chat_data", {}))
        elif event_type == "agent_status":
            await mvp2_event_broadcaster.broadcast_agent_status(data.get("agent_data", {}))
        elif event_type == "system_notification":
            await mvp2_event_broadcaster.broadcast_system_notification(
                data.get("message", ""), 
                data.get("level", "info")
            )
        
    except Exception as e:
        logger.error(f"同步状态到MVP2前端失败: {e}")


# 注册状态同步回调
mvp2_adapter.state_sync.register_sync_callback(sync_state_to_mvp2_frontend)