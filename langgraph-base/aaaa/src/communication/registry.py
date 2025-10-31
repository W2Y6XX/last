"""
智能体注册表和能力管理
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
import json

from ..core.types import (
    AgentId, AgentType, AgentInfo, AgentCapability,
    TaskInfo, Priority
)
from ..core.exceptions import AgentNotFoundError, ValidationError
from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AgentRegistration:
    """智能体注册信息"""
    agent_info: AgentInfo
    registered_at: datetime
    last_heartbeat: datetime
    status: str = "active"
    load_percentage: float = 0.0
    current_tasks: List[str] = None

    def __post_init__(self):
        if self.current_tasks is None:
            self.current_tasks = []


class AgentRegistry:
    """智能体注册表 - 管理智能体的注册、能力和状态"""

    def __init__(self, heartbeat_timeout: int = 300):  # 5分钟
        self.heartbeat_timeout = heartbeat_timeout

        # 智能体存储
        self._agents: Dict[AgentId, AgentRegistration] = {}

        # 能力索引
        self._capability_index: Dict[str, Set[AgentId]] = {}

        # 类型索引
        self._type_index: Dict[AgentType, Set[AgentId]] = {}

        # 统计信息
        self._stats = {
            "total_registrations": 0,
            "active_agents": 0,
            "failed_heartbeats": 0,
            "last_cleanup": datetime.now()
        }

        # 后台任务
        self._cleanup_task: Optional[asyncio.Task] = None
        self._is_running = False

    async def start(self) -> None:
        """启动注册表服务"""
        if self._is_running:
            return

        self._is_running = True
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        logger.info("AgentRegistry started")

    async def stop(self) -> None:
        """停止注册表服务"""
        self._is_running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("AgentRegistry stopped")

    async def register_agent(
        self,
        agent_info: AgentInfo,
        load_percentage: float = 0.0
    ) -> bool:
        """注册智能体"""
        try:
            # 验证智能体信息
            self._validate_agent_info(agent_info)

            agent_id = agent_info.agent_id

            # 如果智能体已存在，更新信息
            if agent_id in self._agents:
                logger.info(f"Updating existing agent: {agent_id}")
                await self.unregister_agent(agent_id)

            # 创建注册记录
            registration = AgentRegistration(
                agent_info=agent_info,
                registered_at=datetime.now(),
                last_heartbeat=datetime.now(),
                load_percentage=load_percentage
            )

            # 添加到存储
            self._agents[agent_id] = registration

            # 更新索引
            self._update_indexes(agent_id, agent_info)

            # 更新统计
            self._stats["total_registrations"] += 1
            self._stats["active_agents"] = len(self._agents)

            logger.info(f"Agent registered: {agent_id} ({agent_info.agent_type})")
            return True

        except Exception as e:
            logger.error(f"Failed to register agent {agent_info.agent_id}: {e}")
            return False

    async def unregister_agent(self, agent_id: AgentId) -> bool:
        """注销智能体"""
        try:
            if agent_id not in self._agents:
                logger.warning(f"Agent not found for unregistration: {agent_id}")
                return False

            registration = self._agents.pop(agent_id)
            agent_info = registration.agent_info

            # 更新索引
            self._remove_from_indexes(agent_id, agent_info)

            # 更新统计
            self._stats["active_agents"] = len(self._agents)

            logger.info(f"Agent unregistered: {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to unregister agent {agent_id}: {e}")
            return False

    async def update_heartbeat(
        self,
        agent_id: AgentId,
        load_percentage: float = None,
        current_tasks: List[str] = None
    ) -> bool:
        """更新智能体心跳"""
        try:
            if agent_id not in self._agents:
                logger.warning(f"Agent not found for heartbeat update: {agent_id}")
                return False

            registration = self._agents[agent_id]
            registration.last_heartbeat = datetime.now()

            if load_percentage is not None:
                registration.load_percentage = load_percentage

            if current_tasks is not None:
                registration.current_tasks = current_tasks

            logger.debug(f"Heartbeat updated for agent: {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update heartbeat for {agent_id}: {e}")
            return False

    def get_agent_info(self, agent_id: AgentId) -> Optional[AgentInfo]:
        """获取智能体信息"""
        registration = self._agents.get(agent_id)
        return registration.agent_info if registration else None

    def get_active_agents(
        self,
        agent_type: AgentType = None,
        capability: str = None,
        max_load: float = None
    ) -> List[AgentInfo]:
        """获取活跃智能体列表"""
        agents = []

        for registration in self._agents.values():
            # 检查状态
            if registration.status != "active":
                continue

            # 检查心跳超时
            if self._is_heartbeat_expired(registration):
                continue

            # 检查类型过滤
            if agent_type and registration.agent_info.agent_type != agent_type:
                continue

            # 检查能力过滤
            if capability:
                capabilities = [cap.name for cap in registration.agent_info.capabilities]
                if capability not in capabilities:
                    continue

            # 检查负载过滤
            if max_load is not None and registration.load_percentage > max_load:
                continue

            agents.append(registration.agent_info)

        return agents

    def find_agents_by_capability(self, capability: str) -> List[AgentInfo]:
        """根据能力查找智能体"""
        agent_ids = self._capability_index.get(capability, set())
        return [self.get_agent_info(agent_id) for agent_id in agent_ids if self.get_agent_info(agent_id)]

    def find_best_agent(
        self,
        required_capabilities: List[str],
        agent_type: AgentType = None,
        prefer_low_load: bool = True
    ) -> Optional[AgentInfo]:
        """找到最适合的智能体"""
        candidates = []

        for registration in self._agents.values():
            if registration.status != "active":
                continue

            if self._is_heartbeat_expired(registration):
                continue

            # 检查类型要求
            if agent_type and registration.agent_info.agent_type != agent_type:
                continue

            # 检查能力要求
            agent_capabilities = [cap.name for cap in registration.agent_info.capabilities]
            if not all(cap in agent_capabilities for cap in required_capabilities):
                continue

            candidates.append(registration)

        if not candidates:
            return None

        # 根据负载选择最佳智能体
        if prefer_low_load:
            candidates.sort(key=lambda r: r.load_percentage)

        return candidates[0].agent_info

    def get_agent_load(self, agent_id: AgentId) -> float:
        """获取智能体负载"""
        registration = self._agents.get(agent_id)
        return registration.load_percentage if registration else 0.0

    def get_system_load(self) -> Dict[str, Any]:
        """获取系统负载统计"""
        if not self._agents:
            return {"average_load": 0.0, "total_agents": 0}

        total_load = sum(reg.load_percentage for reg in self._agents.values())
        average_load = total_load / len(self._agents)

        return {
            "average_load": average_load,
            "total_agents": len(self._agents),
            "load_distribution": {
                agent_id: reg.load_percentage
                for agent_id, reg in self._agents.items()
            }
        }

    def get_registry_stats(self) -> Dict[str, Any]:
        """获取注册表统计信息"""
        type_counts = {}
        capability_counts = {}

        for registration in self._agents.values():
            # 统计类型
            agent_type = registration.agent_info.agent_type.value
            type_counts[agent_type] = type_counts.get(agent_type, 0) + 1

            # 统计能力
            for capability in registration.agent_info.capabilities:
                cap_name = capability.name
                capability_counts[cap_name] = capability_counts.get(cap_name, 0) + 1

        return {
            **self._stats,
            "active_agents": len(self._agents),
            "agent_types": type_counts,
            "capabilities": capability_counts,
            "system_load": self.get_system_load()
        }

    async def export_registry(self, file_path: str) -> bool:
        """导出注册表到文件"""
        try:
            export_data = {
                "timestamp": datetime.now().isoformat(),
                "agents": [
                    {
                        "registration": asdict(registration),
                        "agent_info": asdict(registration.agent_info)
                    }
                    for registration in self._agents.values()
                ],
                "stats": self.get_registry_stats()
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)

            logger.info(f"Registry exported to: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export registry: {e}")
            return False

    async def _periodic_cleanup(self) -> None:
        """定期清理过期智能体"""
        while self._is_running:
            try:
                await asyncio.sleep(60)  # 每分钟清理一次
                await self._cleanup_expired_agents()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")

    async def _cleanup_expired_agents(self) -> None:
        """清理心跳过期的智能体"""
        expired_agents = []

        for agent_id, registration in self._agents.items():
            if self._is_heartbeat_expired(registration):
                expired_agents.append(agent_id)

        for agent_id in expired_agents:
            logger.warning(f"Agent heartbeat expired, removing: {agent_id}")
            await self.unregister_agent(agent_id)
            self._stats["failed_heartbeats"] += 1

        if expired_agents:
            self._stats["last_cleanup"] = datetime.now()
            logger.info(f"Cleaned up {len(expired_agents)} expired agents")

    def _validate_agent_info(self, agent_info: AgentInfo) -> None:
        """验证智能体信息"""
        if not agent_info.agent_id:
            raise ValidationError("Agent ID is required")

        if not agent_info.name:
            raise ValidationError("Agent name is required")

        if not isinstance(agent_info.agent_type, AgentType):
            raise ValidationError("Invalid agent type")

        if not agent_info.capabilities:
            raise ValidationError("Agent must have at least one capability")

    def _update_indexes(self, agent_id: AgentId, agent_info: AgentInfo) -> None:
        """更新索引"""
        # 更新类型索引
        agent_type = agent_info.agent_type
        if agent_type not in self._type_index:
            self._type_index[agent_type] = set()
        self._type_index[agent_type].add(agent_id)

        # 更新能力索引
        for capability in agent_info.capabilities:
            cap_name = capability.name
            if cap_name not in self._capability_index:
                self._capability_index[cap_name] = set()
            self._capability_index[cap_name].add(agent_id)

    def _remove_from_indexes(self, agent_id: AgentId, agent_info: AgentInfo) -> None:
        """从索引中移除"""
        # 从类型索引移除
        agent_type = agent_info.agent_type
        if agent_type in self._type_index:
            self._type_index[agent_type].discard(agent_id)

        # 从能力索引移除
        for capability in agent_info.capabilities:
            cap_name = capability.name
            if cap_name in self._capability_index:
                self._capability_index[cap_name].discard(agent_id)

    def _is_heartbeat_expired(self, registration: AgentRegistration) -> bool:
        """检查心跳是否过期"""
        time_since_heartbeat = datetime.now() - registration.last_heartbeat
        return time_since_heartbeat.total_seconds() > self.heartbeat_timeout