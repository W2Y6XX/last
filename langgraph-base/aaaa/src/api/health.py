"""
健康检查和监控API端点
"""

from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
import asyncio

from ..core.interface import LangGraphAgentSystem
from ..core.monitoring import PerformanceMonitor

router = APIRouter(prefix="/health", tags=["health"])

# 全局系统实例
_system_instance: Optional[LangGraphAgentSystem] = None
_monitor_instance: Optional[PerformanceMonitor] = None


def get_system() -> LangGraphAgentSystem:
    """获取系统实例"""
    global _system_instance
    if _system_instance is None:
        raise HTTPException(status_code=503, detail="System not initialized")
    return _system_instance


def get_monitor() -> Optional[PerformanceMonitor]:
    """获取监控实例"""
    global _monitor_instance
    return _monitor_instance


def set_system_instance(system: LangGraphAgentSystem, monitor: PerformanceMonitor = None):
    """设置系统实例"""
    global _system_instance, _monitor_instance
    _system_instance = system
    _monitor_instance = monitor


@router.get("/")
async def health_check(
    detailed: bool = False,
    system: LangGraphAgentSystem = Depends(get_system)
):
    """基本健康检查"""
    try:
        # 执行健康检查
        health = await system.coordinator.perform_health_check()

        if health["overall"] == "healthy":
            status_code = 200
        elif health["overall"] == "degraded":
            status_code = 200  # 系统可用但有问题
        else:
            status_code = 503  # 系统不可用

        response_data = {
            "status": health["overall"],
            "timestamp": datetime.now().isoformat(),
            "version": "0.1.0"
        }

        if detailed:
            response_data.update({
                "components": health["components"],
                "agents": {
                    "total": len(health["agents"]),
                    "healthy": sum(1 for a in health["agents"].values() if a["status"] == "healthy"),
                    "unhealthy": sum(1 for a in health["agents"].values() if a["status"] != "healthy")
                }
            })

        return JSONResponse(content=response_data, status_code=status_code)

    except Exception as e:
        return JSONResponse(
            content={
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            },
            status_code=503
        )


@router.get("/ready")
async def readiness_check(system: LangGraphAgentSystem = Depends(get_system)):
    """就绪检查 - 系统是否准备好接收请求"""
    try:
        # 检查系统是否运行
        system_status = await system.get_system_status()

        if not system_status.is_healthy:
            raise HTTPException(status_code=503, detail="System is not healthy")

        # 检查是否有活跃的智能体
        if system_status.active_agents == 0:
            raise HTTPException(status_code=503, detail="No active agents")

        # 检查消息总线
        message_stats = system.coordinator.message_bus.get_statistics()
        if not message_stats.get("is_running", False):
            raise HTTPException(status_code=503, detail="Message bus not running")

        return JSONResponse(content={
            "status": "ready",
            "timestamp": datetime.now().isoformat(),
            "agents": system_status.active_agents,
            "message_bus": "running"
        })

    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            content={
                "status": "not_ready",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            },
            status_code=503
        )


@router.get("/live")
async def liveness_check(system: LangGraphAgentSystem = Depends(get_system)):
    """存活检查 - 系统是否正在运行"""
    try:
        # 基本检查：系统是否正在运行
        return JSONResponse(content={
            "status": "alive",
            "timestamp": datetime.now().isoformat(),
            "uptime": datetime.now().isoformat()  # 简化实现
        })

    except Exception as e:
        return JSONResponse(
            content={
                "status": "dead",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            },
            status_code=503
        )


@router.get("/metrics")
async def get_metrics(
    system: LangGraphAgentSystem = Depends(get_system),
    monitor: PerformanceMonitor = Depends(get_monitor)
):
    """获取系统指标"""
    try:
        # 获取系统指标
        system_metrics = await system.get_system_metrics()

        # 获取性能监控指标
        monitor_metrics = {}
        if monitor:
            # 获取最近的指标
            recent_metrics = monitor.get_metrics(limit=100)

            # 聚合指标
            for metric_name in ["system.load_percentage", "tasks.total_tasks", "messages.messages_sent"]:
                aggregated = monitor.get_aggregated_metrics(metric_name)
                if aggregated:
                    monitor_metrics[metric_name] = aggregated

        return JSONResponse(content={
            "timestamp": datetime.now().isoformat(),
            "system_metrics": system_metrics,
            "performance_metrics": monitor_metrics
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.get("/metrics/{metric_name}")
async def get_metric_details(
    metric_name: str,
    hours: int = 1,
    monitor: PerformanceMonitor = Depends(get_monitor)
):
    """获取特定指标的详细信息"""
    try:
        if not monitor:
            raise HTTPException(status_code=503, detail="Performance monitor not available")

        from datetime import timedelta
        start_time = datetime.now() - timedelta(hours=hours)

        metrics = monitor.get_metrics(
            name_pattern=metric_name,
            start_time=start_time
        )

        # 聚合数据
        aggregated = monitor.get_aggregated_metrics(metric_name, timedelta(hours=hours))

        return JSONResponse(content={
            "metric_name": metric_name,
            "time_window_hours": hours,
            "data_points": len(metrics),
            "aggregated": aggregated,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metric details: {str(e)}")


@router.get("/alerts")
async def get_alerts(
    level: Optional[str] = None,
    resolved: Optional[bool] = None,
    limit: int = 50,
    monitor: PerformanceMonitor = Depends(get_monitor)
):
    """获取告警信息"""
    try:
        if not monitor:
            raise HTTPException(status_code=503, detail="Performance monitor not available")

        # 转换参数
        alert_level = None
        if level:
            from ..core.monitoring import AlertLevel
            try:
                alert_level = AlertLevel(level.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid alert level: {level}")

        alerts = monitor.get_alerts(level=alert_level, resolved=resolved, limit=limit)

        return JSONResponse(content={
            "alerts": [
                {
                    "alert_id": alert.alert_id,
                    "level": alert.level.value,
                    "message": alert.message,
                    "source": alert.source,
                    "timestamp": alert.timestamp.isoformat(),
                    "resolved": alert.resolved,
                    "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                    "metadata": alert.metadata
                }
                for alert in alerts
            ],
            "total_count": len(alerts),
            "timestamp": datetime.now().isoformat()
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alerts: {str(e)}")


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    monitor: PerformanceMonitor = Depends(get_monitor)
):
    """解决告警"""
    try:
        if not monitor:
            raise HTTPException(status_code=503, detail="Performance monitor not available")

        success = monitor.resolve_alert(alert_id)

        if success:
            return JSONResponse(content={
                "message": f"Alert {alert_id} resolved successfully",
                "timestamp": datetime.now().isoformat()
            })
        else:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resolve alert: {str(e)}")


@router.get("/system")
async def get_system_details(system: LangGraphAgentSystem = Depends(get_system)):
    """获取详细系统信息"""
    try:
        # 获取系统状态
        status = await system.get_system_status()

        # 获取智能体信息
        agents = await system.get_agents()

        # 获取任务统计
        task_stats = await system.coordinator.task_manager.get_statistics()

        # 获取消息统计
        message_stats = system.coordinator.message_bus.get_statistics()

        # 获取资源统计
        resource_stats = await system.coordinator.resource_manager.get_system_load()

        return JSONResponse(content={
            "timestamp": datetime.now().isoformat(),
            "system_status": status.dict(),
            "agents": {
                "total": len(agents),
                "active": len([a for a in agents if a.status == "active"]),
                "details": [
                    {
                        "agent_id": a.agent_id,
                        "name": a.name,
                        "type": a.agent_type,
                        "status": a.status,
                        "load_percentage": a.load_percentage,
                        "current_tasks": a.current_tasks,
                        "capabilities": a.capabilities
                    }
                    for a in agents
                ]
            },
            "tasks": task_stats,
            "messages": message_stats,
            "resources": resource_stats
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system details: {str(e)}")


@router.get("/components")
async def get_component_status(system: LangGraphAgentSystem = Depends(get_system)):
    """获取组件状态"""
    try:
        health = await system.coordinator.perform_health_check()

        components = {}
        for name, info in health["components"].items():
            components[name] = {
                "status": info["status"],
                "running": info["running"],
                "last_check": datetime.now().isoformat()
            }

        return JSONResponse(content={
            "components": components,
            "overall_health": health["overall"],
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get component status: {str(e)}")