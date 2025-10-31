"""工作流管理API路由"""

import logging
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Query, Path

from ..models import WorkflowStatus, ApiResponse, WorkflowConfigRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{workflow_id}/status", response_model=WorkflowStatus)
async def get_workflow_status(workflow_id: str = Path(..., description="工作流ID")):
    """获取工作流状态"""
    try:
        # 模拟工作流状态数据
        workflow_status = WorkflowStatus(
            workflow_id=workflow_id,
            task_id=f"task_{workflow_id}",
            current_phase="execution",
            status="running",
            progress=0.6,
            active_agents=["meta_agent", "coordinator"],
            completed_agents=["task_decomposer"],
            failed_agents=[],
            execution_time=120.5,
            estimated_remaining_time=80.0
        )
        
        return workflow_status
        
    except Exception as e:
        logger.error(f"获取工作流状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取工作流状态失败: {str(e)}")


@router.put("/{workflow_id}/config", response_model=ApiResponse)
async def update_workflow_config(
    workflow_id: str = Path(..., description="工作流ID"),
    config: WorkflowConfigRequest = None
):
    """更新工作流配置"""
    try:
        return ApiResponse(
            success=True,
            message="工作流配置更新成功",
            data={
                "workflow_id": workflow_id,
                "config": config.dict() if config else {}
            }
        )
        
    except Exception as e:
        logger.error(f"更新工作流配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新工作流配置失败: {str(e)}")