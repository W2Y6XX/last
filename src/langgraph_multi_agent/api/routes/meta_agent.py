"""元智能体对话API路由"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import asyncio

from fastapi import APIRouter, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field

from ..models import ApiResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# 元智能体对话数据模型
class ConversationCreate(BaseModel):
    """创建对话请求"""
    initial_prompt: str = Field(..., min_length=1, max_length=2000, description="初始提示")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="上下文信息")

class MessageSend(BaseModel):
    """发送消息请求"""
    message: str = Field(..., min_length=1, max_length=2000, description="消息内容")
    message_type: str = Field(default="user", description="消息类型：user, system")

class ConversationResponse(BaseModel):
    """对话响应"""
    conversation_id: str = Field(..., description="对话ID")
    messages: List[Dict[str, Any]] = Field(..., description="消息列表")
    task_context: Dict[str, Any] = Field(..., description="任务上下文")
    current_phase: str = Field(..., description="当前阶段")
    progress: float = Field(..., ge=0, le=1, description="进度")
    can_decompose: bool = Field(..., description="是否可以拆解")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

# 对话存储
conversations_storage = {}

# 预定义的对话流程
CONVERSATION_PHASES = [
    "task_understanding",    # 任务理解
    "requirement_gathering", # 需求收集
    "complexity_analysis",   # 复杂度分析
    "solution_planning",     # 解决方案规划
    "task_finalization"      # 任务确定
]

# 预定义的问题模板
QUESTION_TEMPLATES = {
    "task_understanding": [
        "请详细描述您想要完成的任务目标。",
        "这个任务的预期结果是什么？",
        "您希望通过这个任务解决什么问题？"
    ],
    "requirement_gathering": [
        "这个任务有哪些具体的功能要求？",
        "是否有特定的技术约束或限制？",
        "任务的优先级如何？是否有时间要求？",
        "需要哪些输入数据或资源？"
    ],
    "complexity_analysis": [
        "任务中最具挑战性的部分是什么？",
        "是否涉及多个系统或组件的集成？",
        "预计需要多长时间完成？"
    ],
    "solution_planning": [
        "您倾向于什么样的实现方案？",
        "是否有参考的类似项目或解决方案？",
        "需要考虑哪些风险因素？"
    ]
}

@router.post("/conversations", response_model=ApiResponse)
async def create_conversation(conversation_data: ConversationCreate):
    """创建新的对话会话"""
    try:
        conversation_id = str(uuid.uuid4())
        
        # 初始化对话
        conversation = {
            "conversation_id": conversation_id,
            "messages": [
                {
                    "id": str(uuid.uuid4()),
                    "type": "system",
                    "content": "您好！我是元智能体，将帮助您分析和规划任务。让我们开始吧！",
                    "timestamp": datetime.now().isoformat()
                },
                {
                    "id": str(uuid.uuid4()),
                    "type": "user",
                    "content": conversation_data.initial_prompt,
                    "timestamp": datetime.now().isoformat()
                }
            ],
            "task_context": {
                "title": "",
                "description": conversation_data.initial_prompt,
                "requirements": [],
                "constraints": [],
                "complexity": 0.0,
                "estimated_duration": 0,
                **conversation_data.context
            },
            "current_phase": "task_understanding",
            "progress": 0.1,
            "can_decompose": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        # 生成第一个问题
        first_question = QUESTION_TEMPLATES["task_understanding"][0]
        conversation["messages"].append({
            "id": str(uuid.uuid4()),
            "type": "assistant",
            "content": first_question,
            "timestamp": datetime.now().isoformat()
        })
        
        conversations_storage[conversation_id] = conversation
        
        return ApiResponse(
            success=True,
            message="对话创建成功",
            data={
                "conversation_id": conversation_id,
                "first_question": first_question,
                "current_phase": conversation["current_phase"],
                "progress": conversation["progress"]
            }
        )
        
    except Exception as e:
        logger.error(f"创建对话失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建对话失败: {str(e)}")

@router.get("/conversations/{conversation_id}", response_model=ApiResponse)
async def get_conversation(conversation_id: str = Path(..., description="对话ID")):
    """获取对话详情"""
    try:
        if conversation_id not in conversations_storage:
            raise HTTPException(status_code=404, detail=f"对话 {conversation_id} 不存在")
        
        conversation = conversations_storage[conversation_id]
        
        return ApiResponse(
            success=True,
            message="获取对话成功",
            data=conversation
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取对话失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取对话失败: {str(e)}")


@router.post("/conversations/{conversation_id}/messages", response_model=ApiResponse)
async def send_message(
    conversation_id: str = Path(..., description="对话ID"),
    message_data: MessageSend = Body(...)
):
    """发送消息到对话"""
    try:
        if conversation_id not in conversations_storage:
            raise HTTPException(status_code=404, detail=f"对话 {conversation_id} 不存在")
        
        conversation = conversations_storage[conversation_id]
        
        # 添加用户消息
        user_message = {
            "id": str(uuid.uuid4()),
            "type": message_data.message_type,
            "content": message_data.message,
            "timestamp": datetime.now().isoformat()
        }
        conversation["messages"].append(user_message)
        
        # 更新任务上下文
        await _update_task_context(conversation, message_data.message)
        
        # 生成智能体回复
        response_message = await _generate_agent_response(conversation)
        conversation["messages"].append(response_message)
        
        # 更新进度和阶段
        await _update_conversation_progress(conversation)
        
        conversation["updated_at"] = datetime.now()
        
        return ApiResponse(
            success=True,
            message="消息发送成功",
            data={
                "response": response_message["content"],
                "progress": conversation["progress"],
                "can_decompose": conversation["can_decompose"],
                "current_phase": conversation["current_phase"],
                "next_question": response_message.get("next_question")
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发送消息失败: {e}")
        raise HTTPException(status_code=500, detail=f"发送消息失败: {str(e)}")

@router.post("/conversations/{conversation_id}/analyze-complexity", response_model=ApiResponse)
async def analyze_task_complexity(conversation_id: str = Path(..., description="对话ID")):
    """分析任务复杂度"""
    try:
        if conversation_id not in conversations_storage:
            raise HTTPException(status_code=404, detail=f"对话 {conversation_id} 不存在")
        
        conversation = conversations_storage[conversation_id]
        task_context = conversation["task_context"]
        
        # 模拟复杂度分析
        complexity_factors = {
            "requirements_count": len(task_context.get("requirements", [])),
            "constraints_count": len(task_context.get("constraints", [])),
            "description_length": len(task_context.get("description", "")),
            "technical_keywords": _count_technical_keywords(task_context.get("description", ""))
        }
        
        # 计算复杂度评分 (0-1)
        complexity_score = min(1.0, (
            complexity_factors["requirements_count"] * 0.1 +
            complexity_factors["constraints_count"] * 0.15 +
            min(complexity_factors["description_length"] / 1000, 1.0) * 0.3 +
            complexity_factors["technical_keywords"] * 0.05
        ))
        
        task_context["complexity"] = complexity_score
        conversation["can_decompose"] = complexity_score >= 0.6
        conversation["updated_at"] = datetime.now()
        
        return ApiResponse(
            success=True,
            message="复杂度分析完成",
            data={
                "complexity_score": complexity_score,
                "can_decompose": conversation["can_decompose"],
                "complexity_factors": complexity_factors,
                "analysis": {
                    "level": "high" if complexity_score >= 0.7 else "medium" if complexity_score >= 0.4 else "low",
                    "recommendation": "建议进行任务拆解" if complexity_score >= 0.6 else "可以直接执行"
                }
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"复杂度分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"复杂度分析失败: {str(e)}")

@router.post("/conversations/{conversation_id}/decompose", response_model=ApiResponse)
async def decompose_task(conversation_id: str = Path(..., description="对话ID")):
    """执行任务拆解"""
    try:
        if conversation_id not in conversations_storage:
            raise HTTPException(status_code=404, detail=f"对话 {conversation_id} 不存在")
        
        conversation = conversations_storage[conversation_id]
        task_context = conversation["task_context"]
        
        if not conversation["can_decompose"]:
            raise HTTPException(status_code=400, detail="当前任务复杂度不足，无需拆解")
        
        # 模拟任务拆解
        main_task = {
            "id": str(uuid.uuid4()),
            "title": task_context.get("title", "主任务"),
            "description": task_context.get("description", ""),
            "priority": "high",
            "estimated_duration": task_context.get("estimated_duration", 60)
        }
        
        # 生成子任务
        subtasks = []
        requirements = task_context.get("requirements", [])
        
        for i, req in enumerate(requirements[:5]):  # 最多5个子任务
            subtask = {
                "id": str(uuid.uuid4()),
                "title": f"子任务 {i+1}: {req[:50]}...",
                "description": req,
                "priority": "medium" if i < 2 else "low",
                "estimated_duration": max(15, task_context.get("estimated_duration", 60) // len(requirements)),
                "dependencies": [subtasks[-1]["id"]] if subtasks else []
            }
            subtasks.append(subtask)
        
        # 如果没有明确需求，生成默认子任务
        if not subtasks:
            default_subtasks = [
                "需求分析和设计",
                "核心功能实现",
                "测试和验证",
                "文档和部署"
            ]
            
            for i, task_name in enumerate(default_subtasks):
                subtask = {
                    "id": str(uuid.uuid4()),
                    "title": task_name,
                    "description": f"完成{task_name}相关工作",
                    "priority": "high" if i < 2 else "medium",
                    "estimated_duration": task_context.get("estimated_duration", 60) // len(default_subtasks),
                    "dependencies": [subtasks[-1]["id"]] if subtasks else []
                }
                subtasks.append(subtask)
        
        # 计算依赖关系
        dependencies = []
        for i, subtask in enumerate(subtasks[1:], 1):
            dependencies.append({
                "from": subtasks[i-1]["id"],
                "to": subtask["id"],
                "type": "sequential"
            })
        
        decomposition_result = {
            "main_task": main_task,
            "subtasks": subtasks,
            "dependencies": dependencies,
            "complexity": task_context["complexity"],
            "estimated_total_time": sum(st["estimated_duration"] for st in subtasks),
            "decomposition_strategy": "sequential" if len(subtasks) <= 3 else "mixed"
        }
        
        # 保存拆解结果
        conversation["decomposition_result"] = decomposition_result
        conversation["updated_at"] = datetime.now()
        
        return ApiResponse(
            success=True,
            message="任务拆解完成",
            data=decomposition_result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"任务拆解失败: {e}")
        raise HTTPException(status_code=500, detail=f"任务拆解失败: {str(e)}")

@router.delete("/conversations/{conversation_id}", response_model=ApiResponse)
async def delete_conversation(conversation_id: str = Path(..., description="对话ID")):
    """删除对话"""
    try:
        if conversation_id not in conversations_storage:
            raise HTTPException(status_code=404, detail=f"对话 {conversation_id} 不存在")
        
        del conversations_storage[conversation_id]
        
        return ApiResponse(
            success=True,
            message="对话删除成功",
            data={"deleted_conversation_id": conversation_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除对话失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除对话失败: {str(e)}")

# 辅助函数
async def _update_task_context(conversation: Dict[str, Any], message: str):
    """更新任务上下文"""
    task_context = conversation["task_context"]
    
    # 简单的关键词提取和分类
    if "需求" in message or "要求" in message:
        # 提取需求
        requirements = task_context.get("requirements", [])
        if message not in requirements:
            requirements.append(message)
            task_context["requirements"] = requirements
    
    if "约束" in message or "限制" in message:
        # 提取约束
        constraints = task_context.get("constraints", [])
        if message not in constraints:
            constraints.append(message)
            task_context["constraints"] = constraints
    
    # 更新标题（如果还没有）
    if not task_context.get("title") and len(message) < 100:
        task_context["title"] = message[:50]

async def _generate_agent_response(conversation: Dict[str, Any]) -> Dict[str, Any]:
    """生成智能体回复"""
    current_phase = conversation["current_phase"]
    messages_count = len([m for m in conversation["messages"] if m["type"] == "user"])
    
    # 根据阶段和消息数量选择回复
    if current_phase == "task_understanding" and messages_count < 3:
        questions = QUESTION_TEMPLATES["task_understanding"]
        response = questions[min(messages_count - 1, len(questions) - 1)]
    elif current_phase == "requirement_gathering" and messages_count < 6:
        questions = QUESTION_TEMPLATES["requirement_gathering"]
        response = questions[min(messages_count - 3, len(questions) - 1)]
    elif current_phase == "complexity_analysis":
        response = "让我分析一下任务的复杂度。根据您提供的信息，我将评估是否需要进行任务拆解。"
    else:
        response = "感谢您的信息。让我整理一下任务详情，准备为您创建任务。"
    
    return {
        "id": str(uuid.uuid4()),
        "type": "assistant",
        "content": response,
        "timestamp": datetime.now().isoformat()
    }

async def _update_conversation_progress(conversation: Dict[str, Any]):
    """更新对话进度"""
    messages_count = len([m for m in conversation["messages"] if m["type"] == "user"])
    
    # 根据消息数量更新阶段和进度
    if messages_count <= 2:
        conversation["current_phase"] = "task_understanding"
        conversation["progress"] = 0.2
    elif messages_count <= 5:
        conversation["current_phase"] = "requirement_gathering"
        conversation["progress"] = 0.5
    elif messages_count <= 7:
        conversation["current_phase"] = "complexity_analysis"
        conversation["progress"] = 0.8
    else:
        conversation["current_phase"] = "task_finalization"
        conversation["progress"] = 1.0

def _count_technical_keywords(text: str) -> int:
    """计算技术关键词数量"""
    technical_keywords = [
        "API", "数据库", "算法", "架构", "框架", "接口", "服务", "系统",
        "前端", "后端", "全栈", "微服务", "容器", "部署", "测试", "集成"
    ]
    
    count = 0
    text_upper = text.upper()
    for keyword in technical_keywords:
        if keyword.upper() in text_upper:
            count += 1
    
    return count