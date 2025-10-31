"""WebSocket管理器 - 临时占位符"""

from typing import List
from fastapi import WebSocket


class WebSocketManager:
    """WebSocket连接管理器 - 临时实现"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """连接WebSocket"""
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        """断开WebSocket"""
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: str):
        """广播消息"""
        for connection in self.active_connections:
            await connection.send_text(message)