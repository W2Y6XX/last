"""任务管理API路由"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

from fastapi import APIRouter, HTTPException, Depends, Query, Path, BackgroundTasks
from fastapi.responses import StreamingResponse

from ..models import (
    TaskCreateRequest, TaskUpdateRequest, TaskActionRequest,
    TaskInfo, TaskDetail, TaskListResponse, ApiResponse,
    TaskQueryParams, BatchTaskAction, BatchOperationResult,
    TaskStatistics
)
from ...workflow.multi_agent_workflow import MultiAgentWorkflow, WorkflowExecutionMode
from ...workflow.checkpoint_manager import CheckpointManager
from ...core.state import create_initial_state
from ...legacy.task_state import TaskStatus
from ...utils.helpers import generate_task_id

logger = logging.getLogger(__name__)

router = APIRouter()

# 全局任务存储（实际应用中应使用数据库）
tasks_storage: Dict[str, Dict[str, Any]] = {}
workflows_storage: Dict[str, MultiAgentWorkflow] = {}


def get_checkpoint_manager():
    """获取检查点管理器依赖"""
    return CheckpointManager()


def get_task_by_id(task_id: str) -> Dict[str, Any]:
    """根据ID获取任务"""
    if task_id not in tasks_storage:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    return tasks_storage[task_id]


def convert_to_task_info(task_data: Dict[str, Any]) -> TaskInfo:
    """转换为TaskInfo模型"""
    return TaskInfo(
        task_id=task_data["task_id"],
        title=task_data["title"],
        description=task_data["description"],
        task_type=task_data["task_type"],
        priority=task_data["priority"],
        status=task_data["status"],
        created_at=task_data["created_at"],
        updated_at=task_data["updated_at"],
        started_at=task_data.get("started_at"),
        completed_at=task_data.get("completed_at"),
        requester_id=task_data.get("requester_id")
    )


def convert_to_task_detail(task_data: Dict[str, Any]) -> TaskDetail:
    """转换为TaskDetail模型"""
    return TaskDetail(
        task_id=task_data["task_id"],
        title=task_data["title"],
        description=task_data["description"],
        task_type=task_data["task_type"],
        priority=task_data["priority"],
        status=task_data["status"],
        created_at=task_data["created_at"],
        updated_at=task_data["updated_at"],
        started_at=task_data.get("started_at"),
        completed_at=task_data.get("completed_at"),
        requester_id=task_data.get("requester_id"),
        requirements=task_data.get("requirements", []),
        constraints=task_data.get("constraints", []),
        input_data=task_data.get("input_data", {}),
        output_data=task_data.get("output_data"),
        subtasks=task_data.get("subtasks", []),
        execution_metadata=task_data.get("execution_metadata", {}),
        error_info=task_data.get("error_info")
    )


@router.post("/", response_model=ApiResponse)
async def create_task(
    request: TaskCreateRequest,
    background_tasks: BackgroundTasks,
    checkpoint_manager: CheckpointManager = Depends(get_checkpoint_manager)
):
    """创建新任务"""
    try:
        # 生成任务ID
        task_id = generate_task_id()
        
        # 创建任务数据
        task_data = {
            "task_id": task_id,
            "title": request.title,
            "description": request.description,
            "task_type": request.task_type.value,
            "priority": request.priority.value,
            "status": TaskStatus.PENDING.value,
            "requirements": request.requirements,
            "constraints": request.constraints,
            "input_data": request.input_data,
            "execution_mode": request.execution_mode.value,
            "timeout_seconds": request.timeout_seconds,
            "requester_id": request.requester_id,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "started_at": None,
            "completed_at": None,
            "output_data": None,
            "subtasks": [],
            "execution_metadata": {},
            "error_info": None
        }
        
        # 存储任务
        tasks_storage[task_id] = task_data
        
        # 创建工作流
        workflow = MultiAgentWorkflow(
            workflow_id=f"workflow_{task_id}",
            execution_mode=WorkflowExecutionMode(request.execution_mode.value)
        )
        
        # 注册智能体（这里应该根据任务类型动态注册）
        # 暂时使用模拟的智能体注册
        workflows_storage[task_id] = workflow
        
        logger.info(f"创建任务成功: {task_id}")
        
        return ApiResponse(
            success=True,
            message="任务创建成功",
            data={
                "task_id": task_id,
                "status": TaskStatus.PENDING.value,
                "created_at": task_data["created_at"].isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"创建任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[str] = Query(None, description="状态过滤"),
    task_type: Optional[str] = Query(None, description="类型过滤"),
    priority: Optional[int] = Query(None, ge=1, le=4, description="优先级过滤"),
    requester_id: Optional[str] = Query(None, description="请求者过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="页大小"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="排序顺序")
):
    """获取任务列表"""
    try:
        # 过滤任务
        filtered_tasks = []
        for task_data in tasks_storage.values():
            # 应用过滤条件
            if status and task_data["status"] != status:
                continue
            if task_type and task_data["task_type"] != task_type:
                continue
            if priority and task_data["priority"] != priority:
                continue
            if requester_id and task_data.get("requester_id") != requester_id:
                continue
            
            filtered_tasks.append(task_data)
        
        # 排序
        reverse = sort_order == "desc"
        if sort_by == "created_at":
            filtered_tasks.sort(key=lambda x: x["created_at"], reverse=reverse)
        elif sort_by == "updated_at":
            filtered_tasks.sort(key=lambda x: x["updated_at"], reverse=reverse)
        elif sort_by == "priority":
            filtered_tasks.sort(key=lambda x: x["priority"], reverse=reverse)
        
        # 分页
        total = len(filtered_tasks)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_tasks = filtered_tasks[start_idx:end_idx]
        
        # 转换为响应模型
        task_infos = [convert_to_task_info(task) for task in page_tasks]
        
        return TaskListResponse(
            tasks=task_infos,
            total=total,
            page=page,
            page_size=page_size,
            has_next=end_idx < total
        )
        
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")


@router.get("/{task_id}", response_model=TaskDetail)
async def get_task(task_id: str = Path(..., description="任务ID")):
    """获取任务详情"""
    try:
        task_data = get_task_by_id(task_id)
        return convert_to_task_detail(task_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务详情失败: {str(e)}")


@router.put("/{task_id}", response_model=ApiResponse)
async def update_task(
    task_id: str = Path(..., description="任务ID"),
    request: TaskUpdateRequest = None
):
    """更新任务"""
    try:
        task_data = get_task_by_id(task_id)
        
        # 检查任务状态是否允许更新
        if task_data["status"] in [TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value]:
            raise HTTPException(status_code=400, detail="已完成或已取消的任务不能更新")
        
        # 更新字段
        if request.title is not None:
            task_data["title"] = request.title
        if request.description is not None:
            task_data["description"] = request.description
        if request.priority is not None:
            task_data["priority"] = request.priority.value
        if request.requirements is not None:
            task_data["requirements"] = request.requirements
        if request.constraints is not None:
            task_data["constraints"] = request.constraints
        if request.input_data is not None:
            task_data["input_data"] = request.input_data
        
        task_data["updated_at"] = datetime.now()
        
        logger.info(f"更新任务成功: {task_id}")
        
        return ApiResponse(
            success=True,
            message="任务更新成功",
            data={
                "task_id": task_id,
                "updated_at": task_data["updated_at"].isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新任务失败: {str(e)}")


@router.delete("/{task_id}", response_model=ApiResponse)
async def delete_task(task_id: str = Path(..., description="任务ID")):
    """删除任务"""
    try:
        task_data = get_task_by_id(task_id)
        
        # 检查任务状态
        if task_data["status"] == TaskStatus.IN_PROGRESS.value:
            raise HTTPException(status_code=400, detail="正在执行的任务不能删除，请先暂停或取消")
        
        # 删除任务
        del tasks_storage[task_id]
        
        # 删除相关工作流
        if task_id in workflows_storage:
            del workflows_storage[task_id]
        
        logger.info(f"删除任务成功: {task_id}")
        
        return ApiResponse(
            success=True,
            message="任务删除成功",
            data={"task_id": task_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除任务失败: {str(e)}")


@router.post("/{task_id}/actions", response_model=ApiResponse)
async def execute_task_action(
    task_id: str = Path(..., description="任务ID"),
    request: TaskActionRequest = None,
    background_tasks: BackgroundTasks = None,
    checkpoint_manager: CheckpointManager = Depends(get_checkpoint_manager)
):
    """执行任务操作"""
    try:
        task_data = get_task_by_id(task_id)
        action = request.action.lower()
        
        if action == "start":
            return await _start_task(task_id, task_data, background_tasks)
        elif action == "pause":
            return await _pause_task(task_id, task_data, checkpoint_manager, request.reason)
        elif action == "resume":
            return await _resume_task(task_id, task_data, background_tasks, checkpoint_manager)
        elif action == "cancel":
            return await _cancel_task(task_id, task_data, request.reason)
        elif action == "retry":
            return await _retry_task(task_id, task_data, background_tasks)
        else:
            raise HTTPException(status_code=400, detail=f"不支持的操作: {action}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"执行任务操作失败: {e}")
        raise HTTPException(status_code=500, detail=f"执行任务操作失败: {str(e)}")


async def _start_task(task_id: str, task_data: Dict[str, Any], background_tasks: BackgroundTasks) -> ApiResponse:
    """启动任务"""
    if task_data["status"] != TaskStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="只有待处理的任务可以启动")
    
    # 更新任务状态
    task_data["status"] = TaskStatus.IN_PROGRESS.value
    task_data["started_at"] = datetime.now()
    task_data["updated_at"] = datetime.now()
    
    # 在后台执行任务
    background_tasks.add_task(_execute_task_workflow, task_id)
    
    return ApiResponse(
        success=True,
        message="任务启动成功",
        data={
            "task_id": task_id,
            "status": TaskStatus.IN_PROGRESS.value,
            "started_at": task_data["started_at"].isoformat()
        }
    )


async def _pause_task(
    task_id: str, 
    task_data: Dict[str, Any], 
    checkpoint_manager: CheckpointManager,
    reason: Optional[str]
) -> ApiResponse:
    """暂停任务"""
    if task_data["status"] != TaskStatus.IN_PROGRESS.value:
        raise HTTPException(status_code=400, detail="只有正在执行的任务可以暂停")
    
    # 创建检查点
    if task_id in workflows_storage:
        workflow = workflows_storage[task_id]
        # 这里应该获取当前工作流状态并创建检查点
        # 暂时简化处理
        pass
    
    # 更新任务状态
    task_data["status"] = TaskStatus.PAUSED.value
    task_data["updated_at"] = datetime.now()
    task_data["execution_metadata"]["pause_reason"] = reason
    task_data["execution_metadata"]["paused_at"] = datetime.now().isoformat()
    
    return ApiResponse(
        success=True,
        message="任务暂停成功",
        data={
            "task_id": task_id,
            "status": TaskStatus.PAUSED.value,
            "paused_at": task_data["execution_metadata"]["paused_at"]
        }
    )


async def _resume_task(
    task_id: str, 
    task_data: Dict[str, Any], 
    background_tasks: BackgroundTasks,
    checkpoint_manager: CheckpointManager
) -> ApiResponse:
    """恢复任务"""
    if task_data["status"] != TaskStatus.PAUSED.value:
        raise HTTPException(status_code=400, detail="只有暂停的任务可以恢复")
    
    # 更新任务状态
    task_data["status"] = TaskStatus.IN_PROGRESS.value
    task_data["updated_at"] = datetime.now()
    task_data["execution_metadata"]["resumed_at"] = datetime.now().isoformat()
    
    # 在后台恢复执行
    background_tasks.add_task(_resume_task_workflow, task_id)
    
    return ApiResponse(
        success=True,
        message="任务恢复成功",
        data={
            "task_id": task_id,
            "status": TaskStatus.IN_PROGRESS.value,
            "resumed_at": task_data["execution_metadata"]["resumed_at"]
        }
    )


async def _cancel_task(task_id: str, task_data: Dict[str, Any], reason: Optional[str]) -> ApiResponse:
    """取消任务"""
    if task_data["status"] in [TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value]:
        raise HTTPException(status_code=400, detail="已完成或已取消的任务不能再次取消")
    
    # 更新任务状态
    task_data["status"] = TaskStatus.CANCELLED.value
    task_data["completed_at"] = datetime.now()
    task_data["updated_at"] = datetime.now()
    task_data["execution_metadata"]["cancel_reason"] = reason
    task_data["execution_metadata"]["cancelled_at"] = datetime.now().isoformat()
    
    return ApiResponse(
        success=True,
        message="任务取消成功",
        data={
            "task_id": task_id,
            "status": TaskStatus.CANCELLED.value,
            "cancelled_at": task_data["execution_metadata"]["cancelled_at"]
        }
    )


async def _retry_task(task_id: str, task_data: Dict[str, Any], background_tasks: BackgroundTasks) -> ApiResponse:
    """重试任务"""
    if task_data["status"] != TaskStatus.FAILED.value:
        raise HTTPException(status_code=400, detail="只有失败的任务可以重试")
    
    # 重置任务状态
    task_data["status"] = TaskStatus.IN_PROGRESS.value
    task_data["started_at"] = datetime.now()
    task_data["updated_at"] = datetime.now()
    task_data["completed_at"] = None
    task_data["error_info"] = None
    
    # 增加重试计数
    retry_count = task_data["execution_metadata"].get("retry_count", 0) + 1
    task_data["execution_metadata"]["retry_count"] = retry_count
    task_data["execution_metadata"]["retried_at"] = datetime.now().isoformat()
    
    # 在后台重新执行
    background_tasks.add_task(_execute_task_workflow, task_id)
    
    return ApiResponse(
        success=True,
        message="任务重试成功",
        data={
            "task_id": task_id,
            "status": TaskStatus.IN_PROGRESS.value,
            "retry_count": retry_count,
            "retried_at": task_data["execution_metadata"]["retried_at"]
        }
    )


async def _execute_task_workflow(task_id: str):
    """执行任务工作流（后台任务）"""
    try:
        task_data = tasks_storage.get(task_id)
        if not task_data:
            logger.error(f"任务不存在: {task_id}")
            return
        
        workflow = workflows_storage.get(task_id)
        if not workflow:
            logger.error(f"工作流不存在: {task_id}")
            return
        
        # 创建初始状态
        initial_input = {
            "title": task_data["title"],
            "description": task_data["description"],
            "task_type": task_data["task_type"],
            "priority": task_data["priority"],
            "requirements": task_data["requirements"],
            "constraints": task_data["constraints"],
            "input_data": task_data["input_data"]
        }
        
        # 执行工作流
        result = await workflow.execute(initial_input)
        
        # 更新任务结果
        if result:
            task_data["status"] = TaskStatus.COMPLETED.value
            task_data["completed_at"] = datetime.now()
            task_data["output_data"] = result.get("task_state", {}).get("output_data")
            task_data["execution_metadata"].update(result.get("workflow_context", {}).get("execution_metadata", {}))
        else:
            task_data["status"] = TaskStatus.FAILED.value
            task_data["completed_at"] = datetime.now()
            task_data["error_info"] = {"message": "工作流执行失败"}
        
        task_data["updated_at"] = datetime.now()
        
        logger.info(f"任务执行完成: {task_id}, 状态: {task_data['status']}")
        
    except Exception as e:
        logger.error(f"任务执行失败: {task_id}, 错误: {e}")
        
        # 更新任务为失败状态
        if task_id in tasks_storage:
            task_data = tasks_storage[task_id]
            task_data["status"] = TaskStatus.FAILED.value
            task_data["completed_at"] = datetime.now()
            task_data["updated_at"] = datetime.now()
            task_data["error_info"] = {
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }


async def _resume_task_workflow(task_id: str):
    """恢复任务工作流（后台任务）"""
    try:
        # 这里应该从检查点恢复工作流执行
        # 暂时简化为重新执行
        await _execute_task_workflow(task_id)
        
    except Exception as e:
        logger.error(f"任务恢复失败: {task_id}, 错误: {e}")


@router.post("/batch", response_model=BatchOperationResult)
async def batch_task_operation(request: BatchTaskAction):
    """批量任务操作"""
    try:
        results = []
        errors = []
        successful = 0
        failed = 0
        
        for task_id in request.task_ids:
            try:
                if task_id not in tasks_storage:
                    errors.append({
                        "task_id": task_id,
                        "error": "任务不存在"
                    })
                    failed += 1
                    continue
                
                task_data = tasks_storage[task_id]
                
                # 执行操作
                if request.action == "cancel":
                    if task_data["status"] not in [TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value]:
                        task_data["status"] = TaskStatus.CANCELLED.value
                        task_data["completed_at"] = datetime.now()
                        task_data["updated_at"] = datetime.now()
                        task_data["execution_metadata"]["cancel_reason"] = request.reason
                        
                        results.append({
                            "task_id": task_id,
                            "status": "success",
                            "message": "任务已取消"
                        })
                        successful += 1
                    else:
                        errors.append({
                            "task_id": task_id,
                            "error": "任务状态不允许取消"
                        })
                        failed += 1
                else:
                    errors.append({
                        "task_id": task_id,
                        "error": f"不支持的批量操作: {request.action}"
                    })
                    failed += 1
                    
            except Exception as e:
                errors.append({
                    "task_id": task_id,
                    "error": str(e)
                })
                failed += 1
        
        return BatchOperationResult(
            total=len(request.task_ids),
            successful=successful,
            failed=failed,
            results=results,
            errors=errors
        )
        
    except Exception as e:
        logger.error(f"批量操作失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量操作失败: {str(e)}")


@router.get("/statistics", response_model=TaskStatistics)
async def get_task_statistics():
    """获取任务统计信息"""
    try:
        total_tasks = len(tasks_storage)
        completed_tasks = sum(1 for task in tasks_storage.values() if task["status"] == TaskStatus.COMPLETED.value)
        failed_tasks = sum(1 for task in tasks_storage.values() if task["status"] == TaskStatus.FAILED.value)
        running_tasks = sum(1 for task in tasks_storage.values() if task["status"] == TaskStatus.IN_PROGRESS.value)
        pending_tasks = sum(1 for task in tasks_storage.values() if task["status"] == TaskStatus.PENDING.value)
        
        # 计算平均执行时间
        execution_times = []
        for task in tasks_storage.values():
            if task.get("started_at") and task.get("completed_at"):
                duration = (task["completed_at"] - task["started_at"]).total_seconds()
                execution_times.append(duration)
        
        average_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        success_rate = completed_tasks / total_tasks if total_tasks > 0 else 0
        
        # 按类型统计
        tasks_by_type = {}
        for task in tasks_storage.values():
            task_type = task["task_type"]
            tasks_by_type[task_type] = tasks_by_type.get(task_type, 0) + 1
        
        # 按优先级统计
        tasks_by_priority = {}
        for task in tasks_storage.values():
            priority = str(task["priority"])
            tasks_by_priority[priority] = tasks_by_priority.get(priority, 0) + 1
        
        return TaskStatistics(
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            running_tasks=running_tasks,
            pending_tasks=pending_tasks,
            average_execution_time=average_execution_time,
            success_rate=success_rate,
            tasks_by_type=tasks_by_type,
            tasks_by_priority=tasks_by_priority
        )
        
    except Exception as e:
        logger.error(f"获取任务统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务统计失败: {str(e)}")


@router.get("/{task_id}/logs")
async def get_task_logs(
    task_id: str = Path(..., description="任务ID"),
    lines: int = Query(100, ge=1, le=1000, description="日志行数")
):
    """获取任务日志"""
    try:
        task_data = get_task_by_id(task_id)
        
        # 这里应该从日志系统获取任务相关日志
        # 暂时返回模拟数据
        logs = [
            f"[{datetime.now().isoformat()}] INFO: 任务 {task_id} 开始执行",
            f"[{datetime.now().isoformat()}] INFO: 工作流阶段: 分析",
            f"[{datetime.now().isoformat()}] INFO: 智能体执行中...",
            f"[{datetime.now().isoformat()}] INFO: 任务状态: {task_data['status']}"
        ]
        
        return ApiResponse(
            success=True,
            message="获取日志成功",
            data={
                "task_id": task_id,
                "logs": logs[-lines:],
                "total_lines": len(logs)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务日志失败: {str(e)}")


@router.get("/{task_id}/stream")
async def stream_task_logs(task_id: str = Path(..., description="任务ID")):
    """流式获取任务日志"""
    try:
        task_data = get_task_by_id(task_id)
        
        async def log_generator():
            """日志生成器"""
            # 这里应该实现真实的日志流
            # 暂时返回模拟数据
            for i in range(10):
                yield f"data: [{datetime.now().isoformat()}] 任务 {task_id} 执行进度: {i*10}%\n\n"
                await asyncio.sleep(1)
            
            yield f"data: [{datetime.now().isoformat()}] 任务 {task_id} 执行完成\n\n"
        
        return StreamingResponse(
            log_generator(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"流式日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"流式日志失败: {str(e)}")