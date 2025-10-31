"""智能体管理API路由"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Path

from ..models import AgentInfo, ApiResponse, AgentQueryParams
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

router = APIRouter()

# 扩展的智能体数据模型
class AgentConfigUpdate(BaseModel):
    """智能体配置更新请求"""
    llm_config: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    constraints: Optional[List[str]] = None

class AgentDetailResponse(BaseModel):
    """智能体详细信息响应"""
    agent_id: str
    agent_type: str
    name: str
    description: str
    capabilities: List[str]
    status: str
    current_task: Optional[str]
    configuration: Dict[str, Any]
    execution_stats: Dict[str, Any]
    health_status: Dict[str, Any]
    history: List[Dict[str, Any]]
    logs: List[Dict[str, Any]]

# 扩展的智能体数据
agents_data = {
    "meta_agent": {
        "agent_id": "meta_agent",
        "agent_type": "meta_agent",
        "name": "MetaAgent",
        "description": "任务分析和规划智能体",
        "capabilities": ["task_analysis", "complexity_assessment", "agent_recommendation"],
        "status": "active",
        "current_task": None,
        "configuration": {
            "llm_config": "config_1",
            "parameters": {
                "temperature": 0.7,
                "max_tokens": 2000,
                "timeout": 30
            },
            "constraints": ["no_external_api", "safe_mode"]
        },
        "execution_stats": {
            "total_executions": 15,
            "successful_executions": 14,
            "failed_executions": 1,
            "average_execution_time": 2.5,
            "last_execution_time": "2024-01-15T10:30:00Z"
        },
        "health_status": {
            "is_healthy": True,
            "last_health_check": "2024-01-15T10:35:00Z",
            "issues": []
        },
        "history": [
            {
                "task_id": "task_001",
                "action": "analyze_task",
                "timestamp": "2024-01-15T10:30:00Z",
                "result": "success",
                "duration": 2.1
            }
        ],
        "logs": [
            {
                "level": "INFO",
                "message": "任务分析完成",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        ]
    },
    "task_decomposer": {
        "agent_id": "task_decomposer",
        "agent_type": "task_decomposer",
        "name": "TaskDecomposer",
        "description": "任务分解智能体",
        "capabilities": ["task_decomposition", "dependency_analysis", "execution_planning"],
        "status": "active",
        "current_task": "task_002",
        "configuration": {
            "llm_config": "config_1",
            "parameters": {
                "temperature": 0.3,
                "max_tokens": 1500,
                "timeout": 45
            },
            "constraints": ["max_subtasks_10", "dependency_check"]
        },
        "execution_stats": {
            "total_executions": 8,
            "successful_executions": 7,
            "failed_executions": 1,
            "average_execution_time": 4.2,
            "last_execution_time": "2024-01-15T10:25:00Z"
        },
        "health_status": {
            "is_healthy": True,
            "last_health_check": "2024-01-15T10:35:00Z",
            "issues": []
        },
        "history": [
            {
                "task_id": "task_002",
                "action": "decompose_task",
                "timestamp": "2024-01-15T10:25:00Z",
                "result": "in_progress",
                "duration": None
            }
        ],
        "logs": [
            {
                "level": "INFO",
                "message": "开始任务分解",
                "timestamp": "2024-01-15T10:25:00Z"
            }
        ]
    },
    "coordinator": {
        "agent_id": "coordinator",
        "agent_type": "coordinator",
        "name": "Coordinator",
        "description": "智能体协调器",
        "capabilities": ["agent_coordination", "conflict_resolution", "resource_allocation"],
        "status": "active",
        "current_task": None,
        "configuration": {
            "llm_config": "config_2",
            "parameters": {
                "temperature": 0.5,
                "max_tokens": 1000,
                "timeout": 20
            },
            "constraints": ["resource_limit", "priority_based"]
        },
        "execution_stats": {
            "total_executions": 22,
            "successful_executions": 21,
            "failed_executions": 1,
            "average_execution_time": 1.8,
            "last_execution_time": "2024-01-15T10:32:00Z"
        },
        "health_status": {
            "is_healthy": True,
            "last_health_check": "2024-01-15T10:35:00Z",
            "issues": []
        },
        "history": [
            {
                "task_id": "task_003",
                "action": "coordinate_agents",
                "timestamp": "2024-01-15T10:32:00Z",
                "result": "success",
                "duration": 1.5
            }
        ],
        "logs": [
            {
                "level": "INFO",
                "message": "智能体协调完成",
                "timestamp": "2024-01-15T10:32:00Z"
            }
        ]
    }
}


@router.get("/", response_model=List[AgentInfo])
async def list_agents(
    agent_type: Optional[str] = Query(None, description="智能体类型过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    capability: Optional[str] = Query(None, description="能力过滤")
):
    """获取智能体列表"""
    try:
        filtered_agents = []
        
        for agent_data in agents_data.values():
            # 应用过滤条件
            if agent_type and agent_data["agent_type"] != agent_type:
                continue
            if status and agent_data["status"] != status:
                continue
            if capability and capability not in agent_data["capabilities"]:
                continue
            
            filtered_agents.append(AgentInfo(**agent_data))
        
        return filtered_agents
        
    except Exception as e:
        logger.error(f"获取智能体列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取智能体列表失败: {str(e)}")


@router.get("/{agent_id}", response_model=AgentInfo)
async def get_agent(agent_id: str = Path(..., description="智能体ID")):
    """获取智能体详情"""
    try:
        if agent_id not in agents_data:
            raise HTTPException(status_code=404, detail=f"智能体 {agent_id} 不存在")
        
        return AgentInfo(**agents_data[agent_id])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取智能体详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取智能体详情失败: {str(e)}")


@router.get("/{agent_id}/status", response_model=ApiResponse)
async def get_agent_status(agent_id: str = Path(..., description="智能体ID")):
    """获取智能体状态"""
    try:
        if agent_id not in agents_data:
            raise HTTPException(status_code=404, detail=f"智能体 {agent_id} 不存在")
        
        agent_data = agents_data[agent_id]
        
        return ApiResponse(
            success=True,
            message="获取智能体状态成功",
            data={
                "agent_id": agent_id,
                "status": agent_data["status"],
                "current_task": agent_data["current_task"],
                "execution_stats": agent_data["execution_stats"]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取智能体状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取智能体状态失败: {str(e)}")


@router.get("/enhanced", response_model=ApiResponse)
async def list_agents_enhanced(
    agent_type: Optional[str] = Query(None, description="智能体类型过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    capability: Optional[str] = Query(None, description="能力过滤")
):
    """获取增强的智能体列表（包含详细信息）"""
    try:
        filtered_agents = []
        
        for agent_data in agents_data.values():
            # 应用过滤条件
            if agent_type and agent_data["agent_type"] != agent_type:
                continue
            if status and agent_data["status"] != status:
                continue
            if capability and capability not in agent_data["capabilities"]:
                continue
            
            # 计算成功率
            stats = agent_data["execution_stats"]
            success_rate = 0.0
            if stats["total_executions"] > 0:
                success_rate = stats["successful_executions"] / stats["total_executions"]
            
            enhanced_agent = {
                **agent_data,
                "success_rate": success_rate,
                "is_busy": agent_data["current_task"] is not None
            }
            
            filtered_agents.append(enhanced_agent)
        
        return ApiResponse(
            success=True,
            message="获取增强智能体列表成功",
            data={
                "agents": filtered_agents,
                "total_count": len(filtered_agents)
            }
        )
        
    except Exception as e:
        logger.error(f"获取增强智能体列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取增强智能体列表失败: {str(e)}")

@router.get("/{agent_id}/detailed", response_model=ApiResponse)
async def get_agent_detailed(agent_id: str = Path(..., description="智能体ID")):
    """获取智能体详细信息"""
    try:
        if agent_id not in agents_data:
            raise HTTPException(status_code=404, detail=f"智能体 {agent_id} 不存在")
        
        agent_data = agents_data[agent_id]
        
        # 计算额外的统计信息
        stats = agent_data["execution_stats"]
        success_rate = 0.0
        if stats["total_executions"] > 0:
            success_rate = stats["successful_executions"] / stats["total_executions"]
        
        detailed_info = {
            **agent_data,
            "success_rate": success_rate,
            "is_busy": agent_data["current_task"] is not None,
            "uptime": "2 days 5 hours",  # 模拟运行时间
            "memory_usage": "45.2 MB",   # 模拟内存使用
            "cpu_usage": "12.5%"         # 模拟CPU使用
        }
        
        return ApiResponse(
            success=True,
            message="获取智能体详细信息成功",
            data=detailed_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取智能体详细信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取智能体详细信息失败: {str(e)}")

@router.put("/{agent_id}/config", response_model=ApiResponse)
async def update_agent_config(
    agent_id: str = Path(..., description="智能体ID"),
    config_update: AgentConfigUpdate = ...
):
    """更新智能体配置"""
    try:
        if agent_id not in agents_data:
            raise HTTPException(status_code=404, detail=f"智能体 {agent_id} 不存在")
        
        agent_data = agents_data[agent_id]
        config = agent_data["configuration"]
        
        # 更新配置
        if config_update.llm_config is not None:
            config["llm_config"] = config_update.llm_config
        if config_update.parameters is not None:
            config["parameters"].update(config_update.parameters)
        if config_update.constraints is not None:
            config["constraints"] = config_update.constraints
        
        return ApiResponse(
            success=True,
            message="更新智能体配置成功",
            data={
                "agent_id": agent_id,
                "updated_config": config
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新智能体配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新智能体配置失败: {str(e)}")

@router.get("/{agent_id}/history", response_model=ApiResponse)
async def get_agent_history(
    agent_id: str = Path(..., description="智能体ID"),
    limit: int = Query(default=50, ge=1, le=200, description="返回记录数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量")
):
    """获取智能体历史记录"""
    try:
        if agent_id not in agents_data:
            raise HTTPException(status_code=404, detail=f"智能体 {agent_id} 不存在")
        
        agent_data = agents_data[agent_id]
        history = agent_data.get("history", [])
        
        # 分页处理
        total = len(history)
        paginated_history = history[offset:offset + limit]
        
        return ApiResponse(
            success=True,
            message="获取智能体历史记录成功",
            data={
                "agent_id": agent_id,
                "history": paginated_history,
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取智能体历史记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取智能体历史记录失败: {str(e)}")

@router.get("/{agent_id}/logs", response_model=ApiResponse)
async def get_agent_logs(
    agent_id: str = Path(..., description="智能体ID"),
    level: Optional[str] = Query(None, description="日志级别过滤: DEBUG, INFO, WARN, ERROR"),
    limit: int = Query(default=100, ge=1, le=500, description="返回记录数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量")
):
    """获取智能体日志"""
    try:
        if agent_id not in agents_data:
            raise HTTPException(status_code=404, detail=f"智能体 {agent_id} 不存在")
        
        agent_data = agents_data[agent_id]
        logs = agent_data.get("logs", [])
        
        # 按级别过滤
        if level:
            logs = [log for log in logs if log.get("level") == level.upper()]
        
        # 分页处理
        total = len(logs)
        paginated_logs = logs[offset:offset + limit]
        
        return ApiResponse(
            success=True,
            message="获取智能体日志成功",
            data={
                "agent_id": agent_id,
                "logs": paginated_logs,
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total,
                "level_filter": level
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取智能体日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取智能体日志失败: {str(e)}")

@router.get("/{agent_id}/health", response_model=ApiResponse)
async def check_agent_health(agent_id: str = Path(..., description="智能体ID")):
    """检查智能体健康状态"""
    try:
        if agent_id not in agents_data:
            raise HTTPException(status_code=404, detail=f"智能体 {agent_id} 不存在")
        
        agent_data = agents_data[agent_id]
        
        # 执行健康检查
        health_status = {
            "agent_id": agent_id,
            "is_healthy": True,
            "last_health_check": datetime.now().isoformat(),
            "checks": {
                "connectivity": {"status": "ok", "response_time": 0.1},
                "memory": {"status": "ok", "usage": "45.2 MB"},
                "cpu": {"status": "ok", "usage": "12.5%"},
                "llm_connection": {"status": "ok", "response_time": 0.3}
            },
            "issues": [],
            "recommendations": []
        }
        
        # 模拟一些健康检查逻辑
        stats = agent_data["execution_stats"]
        if stats["failed_executions"] > stats["successful_executions"] * 0.1:
            health_status["issues"].append("错误率较高")
            health_status["recommendations"].append("检查配置参数")
        
        if agent_data["current_task"] and "timeout" in str(agent_data["current_task"]):
            health_status["issues"].append("任务执行超时")
            health_status["recommendations"].append("增加超时时间或检查任务复杂度")
        
        # 更新智能体的健康状态
        agent_data["health_status"] = health_status
        
        return ApiResponse(
            success=True,
            message="智能体健康检查完成",
            data=health_status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"智能体健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=f"智能体健康检查失败: {str(e)}")