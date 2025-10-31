"""WebSocket实时通信路由"""

import logging
import json
import asyncio
from typing import Dict, Set, Any, Optional, List
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.websockets import WebSocketState

from ..models import (
    WebSocketMessage, TaskStatusUpdate, AgentStatusUpdate
)

logger = logging.getLogger(__name__)

router = APIRouter()


class MessageType(str, Enum):
    """WebSocket消息类型"""
    # 连接管理
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    PING = "ping"
    PONG = "pong"
    
    # 任务相关
    TASK_STATUS_UPDATE = "task_status_update"
    TASK_PROGRESS_UPDATE = "task_progress_update"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    
    # 智能体相关
    AGENT_STATUS_UPDATE = "agent_status_update"
    AGENT_RESULT = "agent_result"
    AGENT_ERROR = "agent_error"
    
    # 工作流相关
    WORKFLOW_PHASE_CHANGE = "workflow_phase_change"
    WORKFLOW_STATUS_UPDATE = "workflow_status_update"
    
    # 系统相关
    SYSTEM_ALERT = "system_alert"
    SYSTEM_HEALTH_UPDATE = "system_health_update"
    
    # 日志相关
    LOG_MESSAGE = "log_message"
    ERROR_MESSAGE = "error_message"


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 活跃连接
        self.active_connections: Dict[str, WebSocket] = {}
        
        # 订阅管理
        self.task_subscribers: Dict[str, Set[str]] = {}  # task_id -> {client_id}
        self.agent_subscribers: Dict[str, Set[str]] = {}  # agent_id -> {client_id}
        self.system_subscribers: Set[str] = set()  # 系统消息订阅者
        
        # 连接元数据
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        
        # 消息队列（用于离线消息）
        self.message_queues: Dict[str, List[Dict[str, Any]]] = {}
        
        logger.info("WebSocket连接管理器初始化完成")
    
    async def connect(self, websocket: WebSocket, client_id: str, metadata: Optional[Dict[str, Any]] = None):
        """接受WebSocket连接"""
        await websocket.accept()
        
        self.active_connections[client_id] = websocket
        self.connection_metadata[client_id] = {
            "connected_at": datetime.now(),
            "last_ping": datetime.now(),
            "metadata": metadata or {}
        }
        
        # 发送连接确认消息
        await self.send_personal_message(client_id, {
            "type": MessageType.CONNECT,
            "data": {
                "client_id": client_id,
                "connected_at": datetime.now().isoformat(),
                "message": "WebSocket连接建立成功"
            }
        })
        
        # 发送离线消息
        await self._send_queued_messages(client_id)
        
        logger.info(f"WebSocket连接建立: {client_id}")
    
    def disconnect(self, client_id: str):
        """断开WebSocket连接"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        
        if client_id in self.connection_metadata:
            del self.connection_metadata[client_id]
        
        # 清理订阅
        self._cleanup_subscriptions(client_id)
        
        logger.info(f"WebSocket连接断开: {client_id}")
    
    def _cleanup_subscriptions(self, client_id: str):
        """清理客户端订阅"""
        # 清理任务订阅
        for task_id, subscribers in self.task_subscribers.items():
            subscribers.discard(client_id)
        
        # 清理智能体订阅
        for agent_id, subscribers in self.agent_subscribers.items():
            subscribers.discard(client_id)
        
        # 清理系统订阅
        self.system_subscribers.discard(client_id)
        
        # 清理空的订阅集合
        self.task_subscribers = {k: v for k, v in self.task_subscribers.items() if v}
        self.agent_subscribers = {k: v for k, v in self.agent_subscribers.items() if v}
    
    async def send_personal_message(self, client_id: str, message: Dict[str, Any]):
        """发送个人消息"""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(json.dumps(message, default=str))
                else:
                    # 连接已断开，加入消息队列
                    self._queue_message(client_id, message)
            except Exception as e:
                logger.error(f"发送个人消息失败 {client_id}: {e}")
                # 连接可能已断开，移除连接
                self.disconnect(client_id)
        else:
            # 客户端不在线，加入消息队列
            self._queue_message(client_id, message)
    
    async def broadcast_message(self, message: Dict[str, Any], exclude_clients: Optional[Set[str]] = None):
        """广播消息给所有连接"""
        exclude_clients = exclude_clients or set()
        
        disconnected_clients = []
        for client_id, websocket in self.active_connections.items():
            if client_id in exclude_clients:
                continue
            
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(json.dumps(message, default=str))
                else:
                    disconnected_clients.append(client_id)
            except Exception as e:
                logger.error(f"广播消息失败 {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # 清理断开的连接
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    async def send_to_task_subscribers(self, task_id: str, message: Dict[str, Any]):
        """发送消息给任务订阅者"""
        if task_id in self.task_subscribers:
            subscribers = self.task_subscribers[task_id].copy()
            for client_id in subscribers:
                await self.send_personal_message(client_id, message)
    
    async def send_to_agent_subscribers(self, agent_id: str, message: Dict[str, Any]):
        """发送消息给智能体订阅者"""
        if agent_id in self.agent_subscribers:
            subscribers = self.agent_subscribers[agent_id].copy()
            for client_id in subscribers:
                await self.send_personal_message(client_id, message)
    
    async def send_to_system_subscribers(self, message: Dict[str, Any]):
        """发送消息给系统订阅者"""
        subscribers = self.system_subscribers.copy()
        for client_id in subscribers:
            await self.send_personal_message(client_id, message)
    
    def subscribe_to_task(self, client_id: str, task_id: str):
        """订阅任务更新"""
        if task_id not in self.task_subscribers:
            self.task_subscribers[task_id] = set()
        self.task_subscribers[task_id].add(client_id)
        logger.debug(f"客户端 {client_id} 订阅任务 {task_id}")
    
    def unsubscribe_from_task(self, client_id: str, task_id: str):
        """取消订阅任务更新"""
        if task_id in self.task_subscribers:
            self.task_subscribers[task_id].discard(client_id)
            if not self.task_subscribers[task_id]:
                del self.task_subscribers[task_id]
        logger.debug(f"客户端 {client_id} 取消订阅任务 {task_id}")
    
    def subscribe_to_agent(self, client_id: str, agent_id: str):
        """订阅智能体更新"""
        if agent_id not in self.agent_subscribers:
            self.agent_subscribers[agent_id] = set()
        self.agent_subscribers[agent_id].add(client_id)
        logger.debug(f"客户端 {client_id} 订阅智能体 {agent_id}")
    
    def unsubscribe_from_agent(self, client_id: str, agent_id: str):
        """取消订阅智能体更新"""
        if agent_id in self.agent_subscribers:
            self.agent_subscribers[agent_id].discard(client_id)
            if not self.agent_subscribers[agent_id]:
                del self.agent_subscribers[agent_id]
        logger.debug(f"客户端 {client_id} 取消订阅智能体 {agent_id}")
    
    def subscribe_to_system(self, client_id: str):
        """订阅系统消息"""
        self.system_subscribers.add(client_id)
        logger.debug(f"客户端 {client_id} 订阅系统消息")
    
    def unsubscribe_from_system(self, client_id: str):
        """取消订阅系统消息"""
        self.system_subscribers.discard(client_id)
        logger.debug(f"客户端 {client_id} 取消订阅系统消息")
    
    def _queue_message(self, client_id: str, message: Dict[str, Any]):
        """将消息加入队列"""
        if client_id not in self.message_queues:
            self.message_queues[client_id] = []
        
        self.message_queues[client_id].append(message)
        
        # 限制队列大小
        max_queue_size = 100
        if len(self.message_queues[client_id]) > max_queue_size:
            self.message_queues[client_id] = self.message_queues[client_id][-max_queue_size:]
    
    async def _send_queued_messages(self, client_id: str):
        """发送队列中的消息"""
        if client_id in self.message_queues:
            messages = self.message_queues[client_id]
            del self.message_queues[client_id]
            
            for message in messages:
                await self.send_personal_message(client_id, message)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计"""
        return {
            "active_connections": len(self.active_connections),
            "task_subscriptions": len(self.task_subscribers),
            "agent_subscriptions": len(self.agent_subscribers),
            "system_subscribers": len(self.system_subscribers),
            "queued_messages": sum(len(queue) for queue in self.message_queues.values())
        }
    
    async def ping_all_connections(self):
        """向所有连接发送ping"""
        ping_message = {
            "type": MessageType.PING,
            "data": {"timestamp": datetime.now().isoformat()}
        }
        
        await self.broadcast_message(ping_message)
    
    async def cleanup_stale_connections(self):
        """清理过期连接"""
        current_time = datetime.now()
        stale_clients = []
        
        for client_id, metadata in self.connection_metadata.items():
            last_ping = metadata.get("last_ping", metadata["connected_at"])
            if (current_time - last_ping).total_seconds() > 300:  # 5分钟无响应
                stale_clients.append(client_id)
        
        for client_id in stale_clients:
            logger.info(f"清理过期连接: {client_id}")
            self.disconnect(client_id)


# 全局连接管理器
connection_manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """获取连接管理器依赖"""
    return connection_manager


@router.websocket("/connect")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str = Query(..., description="客户端ID"),
    user_id: Optional[str] = Query(None, description="用户ID"),
    session_id: Optional[str] = Query(None, description="会话ID")
):
    """WebSocket连接端点"""
    manager = get_connection_manager()
    
    # 连接元数据
    metadata = {
        "user_id": user_id,
        "session_id": session_id,
        "user_agent": websocket.headers.get("user-agent", ""),
        "origin": websocket.headers.get("origin", "")
    }
    
    await manager.connect(websocket, client_id, metadata)
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await handle_client_message(client_id, message, manager)
                
            except json.JSONDecodeError:
                await manager.send_personal_message(client_id, {
                    "type": "error",
                    "data": {"message": "无效的JSON格式"}
                })
            except Exception as e:
                logger.error(f"处理客户端消息失败 {client_id}: {e}")
                await manager.send_personal_message(client_id, {
                    "type": "error",
                    "data": {"message": f"消息处理失败: {str(e)}"}
                })
    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket连接异常 {client_id}: {e}")
        manager.disconnect(client_id)


async def handle_client_message(client_id: str, message: Dict[str, Any], manager: ConnectionManager):
    """处理客户端消息"""
    message_type = message.get("type")
    data = message.get("data", {})
    
    if message_type == MessageType.PING:
        # 响应ping
        await manager.send_personal_message(client_id, {
            "type": MessageType.PONG,
            "data": {"timestamp": datetime.now().isoformat()}
        })
        
        # 更新最后ping时间
        if client_id in manager.connection_metadata:
            manager.connection_metadata[client_id]["last_ping"] = datetime.now()
    
    elif message_type == "subscribe":
        # 处理订阅请求
        subscription_type = data.get("subscription_type")
        target_id = data.get("target_id")
        
        if subscription_type == "task" and target_id:
            manager.subscribe_to_task(client_id, target_id)
            await manager.send_personal_message(client_id, {
                "type": "subscription_confirmed",
                "data": {
                    "subscription_type": "task",
                    "target_id": target_id,
                    "message": f"已订阅任务 {target_id} 的更新"
                }
            })
        
        elif subscription_type == "agent" and target_id:
            manager.subscribe_to_agent(client_id, target_id)
            await manager.send_personal_message(client_id, {
                "type": "subscription_confirmed",
                "data": {
                    "subscription_type": "agent",
                    "target_id": target_id,
                    "message": f"已订阅智能体 {target_id} 的更新"
                }
            })
        
        elif subscription_type == "system":
            manager.subscribe_to_system(client_id)
            await manager.send_personal_message(client_id, {
                "type": "subscription_confirmed",
                "data": {
                    "subscription_type": "system",
                    "message": "已订阅系统消息"
                }
            })
    
    elif message_type == "unsubscribe":
        # 处理取消订阅请求
        subscription_type = data.get("subscription_type")
        target_id = data.get("target_id")
        
        if subscription_type == "task" and target_id:
            manager.unsubscribe_from_task(client_id, target_id)
        elif subscription_type == "agent" and target_id:
            manager.unsubscribe_from_agent(client_id, target_id)
        elif subscription_type == "system":
            manager.unsubscribe_from_system(client_id)
        
        await manager.send_personal_message(client_id, {
            "type": "unsubscription_confirmed",
            "data": {
                "subscription_type": subscription_type,
                "target_id": target_id,
                "message": "取消订阅成功"
            }
        })
    
    elif message_type == "get_status":
        # 获取连接状态
        stats = manager.get_connection_stats()
        await manager.send_personal_message(client_id, {
            "type": "status_response",
            "data": {
                "client_id": client_id,
                "connection_stats": stats,
                "timestamp": datetime.now().isoformat()
            }
        })
    
    else:
        await manager.send_personal_message(client_id, {
            "type": "error",
            "data": {"message": f"未知消息类型: {message_type}"}
        })


# WebSocket事件发布函数
async def publish_task_status_update(task_id: str, status_update: TaskStatusUpdate):
    """发布任务状态更新"""
    message = {
        "type": MessageType.TASK_STATUS_UPDATE,
        "data": status_update.dict(),
        "timestamp": datetime.now().isoformat()
    }
    
    await connection_manager.send_to_task_subscribers(task_id, message)


async def publish_agent_status_update(agent_id: str, status_update: AgentStatusUpdate):
    """发布智能体状态更新"""
    message = {
        "type": MessageType.AGENT_STATUS_UPDATE,
        "data": status_update.dict(),
        "timestamp": datetime.now().isoformat()
    }
    
    await connection_manager.send_to_agent_subscribers(agent_id, message)


async def publish_workflow_phase_change(task_id: str, old_phase: str, new_phase: str):
    """发布工作流阶段变更"""
    message = {
        "type": MessageType.WORKFLOW_PHASE_CHANGE,
        "data": {
            "task_id": task_id,
            "old_phase": old_phase,
            "new_phase": new_phase,
            "timestamp": datetime.now().isoformat()
        }
    }
    
    await connection_manager.send_to_task_subscribers(task_id, message)


async def publish_system_alert(alert_type: str, message: str, severity: str = "info"):
    """发布系统告警"""
    alert_message = {
        "type": MessageType.SYSTEM_ALERT,
        "data": {
            "alert_type": alert_type,
            "message": message,
            "severity": severity,
            "timestamp": datetime.now().isoformat()
        }
    }
    
    await connection_manager.send_to_system_subscribers(alert_message)


async def publish_log_message(task_id: str, log_level: str, message: str, source: str = "system"):
    """发布日志消息"""
    log_message = {
        "type": MessageType.LOG_MESSAGE,
        "data": {
            "task_id": task_id,
            "log_level": log_level,
            "message": message,
            "source": source,
            "timestamp": datetime.now().isoformat()
        }
    }
    
    await connection_manager.send_to_task_subscribers(task_id, log_message)


# 后台任务：定期清理连接
async def connection_cleanup_task():
    """连接清理后台任务"""
    while True:
        try:
            await asyncio.sleep(60)  # 每分钟执行一次
            await connection_manager.cleanup_stale_connections()
            await connection_manager.ping_all_connections()
        except Exception as e:
            logger.error(f"连接清理任务失败: {e}")


# 后台任务将在应用启动时创建
# asyncio.create_task(connection_cleanup_task())