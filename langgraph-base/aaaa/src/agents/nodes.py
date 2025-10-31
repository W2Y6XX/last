"""
MetaAgent 工作流节点实现
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from ..core.state import MetaAgentState
from ..core.types import TaskInfo, TaskStatus, Priority, TaskDependency
from ..core.exceptions import TaskError
from ..utils.logging import get_logger

logger = get_logger(__name__)


async def task_analysis_node(state: MetaAgentState) -> MetaAgentState:
    """
    任务分析节点 - 分析用户输入的任务描述
    """
    logger.info("Starting task analysis")

    try:
        # 获取最新的用户消息
        messages = state.get("messages", [])
        if not messages:
            raise TaskError("No messages found for analysis")

        latest_message = messages[-1]
        task_description = latest_message.content if hasattr(latest_message, 'content') else str(latest_message)

        # 分析任务内容
        analysis_result = await _analyze_task_content(task_description)

        # 更新状态
        state["workflow_stage"] = "analysis"
        state["current_analysis"] = analysis_result

        # 生成分析结果消息
        analysis_summary = _create_analysis_summary(analysis_result)
        state["messages"].append(AIMessage(content=analysis_summary))

        logger.info(f"Task analysis completed: {analysis_result['task_type']}")

        return state

    except Exception as e:
        logger.error(f"Task analysis failed: {e}")
        state["messages"].append(AIMessage(content=f"任务分析失败: {str(e)}"))
        return state


async def requirement_clarification_node(state: MetaAgentState) -> MetaAgentState:
    """
    需求澄清节点 - 识别和澄清模糊的需求
    """
    logger.info("Starting requirement clarification")

    try:
        analysis_result = state.get("current_analysis", {})

        # 检查是否需要澄清
        clarification_questions = await _generate_clarification_questions(analysis_result)

        if clarification_questions:
            state["workflow_stage"] = "clarification"
            state["clarification_needed"] = clarification_questions
            state["pending_clarifications"] = True

            # 生成澄清问题
            questions_text = "\n".join([f"- {q}" for q in clarification_questions])
            clarification_message = f"为了更好地理解您的需求，我需要澄清以下几点：\n{questions_text}"

            state["messages"].append(AIMessage(content=clarification_message))
            logger.info(f"Generated {len(clarification_questions)} clarification questions")

        else:
            state["pending_clarifications"] = False
            state["messages"].append(AIMessage(content="需求已明确，准备进行任务分解。"))
            logger.info("No clarification needed")

        return state

    except Exception as e:
        logger.error(f"Requirement clarification failed: {e}")
        state["messages"].append(AIMessage(content=f"需求澄清失败: {str(e)}"))
        return state


async def task_decomposition_node(state: MetaAgentState) -> MetaAgentState:
    """
    任务分解节点 - 将复杂任务分解为子任务
    """
    logger.info("Starting task decomposition")

    try:
        analysis_result = state.get("current_analysis", {})
        clarification_responses = state.get("clarification_responses", {})

        # 执行任务分解
        decomposition_result = await _decompose_task(analysis_result, clarification_responses)

        # 更新状态
        state["workflow_stage"] = "decomposition"
        state["task_decomposition"] = decomposition_result
        state["analyzed_tasks"] = [task["task_id"] for task in decomposition_result["subtasks"]]

        # 生成分解结果摘要
        decomposition_summary = _create_decomposition_summary(decomposition_result)
        state["messages"].append(AIMessage(content=decomposition_summary))

        logger.info(f"Task decomposition completed: {len(decomposition_result['subtasks'])} subtasks")

        return state

    except Exception as e:
        logger.error(f"Task decomposition failed: {e}")
        state["messages"].append(AIMessage(content=f"任务分解失败: {str(e)}"))
        return state


async def agent_assignment_node(state: MetaAgentState) -> MetaAgentState:
    """
    智能体分配节点 - 为子任务分配合适的智能体
    """
    logger.info("Starting agent assignment")

    try:
        decomposition_result = state.get("task_decomposition", {})
        available_agents = state.get("available_agents", [])

        # 执行智能体分配
        assignment_result = await _assign_agents_to_tasks(decomposition_result, available_agents)

        # 更新状态
        state["workflow_stage"] = "assignment"
        state["agent_assignments"] = assignment_result["assignments"]
        state["pending_tasks"] = assignment_result["pending_tasks"]

        # 生成分配结果摘要
        assignment_summary = _create_assignment_summary(assignment_result)
        state["messages"].append(AIMessage(content=assignment_summary))

        logger.info(f"Agent assignment completed: {len(assignment_result['assignments'])} assignments")

        return state

    except Exception as e:
        logger.error(f"Agent assignment failed: {e}")
        state["messages"].append(AIMessage(content=f"智能体分配失败: {str(e)}"))
        return state


# 辅助函数
async def _analyze_task_content(task_description: str) -> Dict[str, Any]:
    """分析任务内容"""
    # 简单的任务分析逻辑
    task_lower = task_description.lower()

    # 识别任务类型
    task_type = "general"
    if any(word in task_lower for word in ["开发", "实现", "编程", "代码"]):
        task_type = "development"
    elif any(word in task_lower for word in ["分析", "研究", "调查"]):
        task_type = "analysis"
    elif any(word in task_lower for word in ["设计", "规划", "架构"]):
        task_type = "design"
    elif any(word in task_lower for word in ["测试", "验证", "质量"]):
        task_type = "testing"

    # 识别关键词
    keywords = re.findall(r'\b\w+\b', task_description)
    keywords = [kw for kw in keywords if len(kw) > 3]  # 过滤短词

    # 评估复杂度
    complexity = "medium"
    complexity_indicators = ["复杂", "困难", "挑战", "系统", "架构", "集成"]
    if any(indicator in task_lower for indicator in complexity_indicators):
        complexity = "high"

    return {
        "task_type": task_type,
        "keywords": keywords,
        "complexity": complexity,
        "estimated_duration": _estimate_duration(task_type, complexity),
        "requires_clarification": _check_clarification_needed(task_description)
    }


def _estimate_duration(task_type: str, complexity: str) -> str:
    """估算任务持续时间"""
    base_durations = {
        "development": "2-4 hours",
        "analysis": "1-2 hours",
        "design": "1-3 hours",
        "testing": "1-2 hours",
        "general": "1-3 hours"
    }

    base = base_durations.get(task_type, "1-3 hours")

    if complexity == "high":
        # 高复杂度任务时间增加50%
        return f"{base} (可能更长)"

    return base


def _check_clarification_needed(task_description: str) -> bool:
    """检查是否需要澄清"""
    clarification_indicators = [
        "?", "？", "等等", "或者", "可能", "也许",
        "大概", "左右", "具体", "详细", "进一步"
    ]

    task_lower = task_description.lower()
    return any(indicator in task_lower for indicator in clarification_indicators)


async def _generate_clarification_questions(analysis_result: Dict[str, Any]) -> List[str]:
    """生成澄清问题"""
    if not analysis_result.get("requires_clarification", False):
        return []

    questions = []
    task_type = analysis_result.get("task_type", "general")
    complexity = analysis_result.get("complexity", "medium")

    # 基于任务类型生成问题
    if task_type == "development":
        questions.extend([
            "您希望使用什么编程语言或技术栈？",
            "是否有特定的性能要求或约束？",
            "需要支持哪些平台或环境？"
        ])
    elif task_type == "analysis":
        questions.extend([
            "分析的重点是什么？（例如：性能、安全性、可用性）",
            "分析结果需要什么格式的输出？",
            "是否有特定的分析标准或方法论？"
        ])
    elif task_type == "design":
        questions.extend([
            "设计的规模和范围是什么？",
            "是否需要遵循特定的设计原则或规范？",
            "预期的用户群体或使用场景是什么？"
        ])

    # 基于复杂度生成问题
    if complexity == "high":
        questions.append("这个任务是否可以分阶段完成？")
        questions.append("是否有时间限制或截止日期？")

    return questions[:5]  # 限制问题数量


def _create_analysis_summary(analysis_result: Dict[str, Any]) -> str:
    """创建分析结果摘要"""
    task_type = analysis_result.get("task_type", "general")
    complexity = analysis_result.get("complexity", "medium")
    duration = analysis_result.get("estimated_duration", "unknown")
    keywords = analysis_result.get("keywords", [])

    summary = f"**任务分析结果：**\n"
    summary += f"- 任务类型: {task_type}\n"
    summary += f"- 复杂度: {complexity}\n"
    summary += f"- 预估时间: {duration}\n"

    if keywords:
        summary += f"- 关键词: {', '.join(keywords[:5])}\n"

    return summary


async def _decompose_task(
    analysis_result: Dict[str, Any],
    clarification_responses: Dict[str, Any]
) -> Dict[str, Any]:
    """分解任务"""
    task_type = analysis_result.get("task_type", "general")
    complexity = analysis_result.get("complexity", "medium")

    # 根据任务类型生成子任务
    subtasks = []

    if task_type == "development":
        subtasks = [
            {
                "task_id": "dev-requirements",
                "title": "需求分析和确认",
                "description": "详细分析功能需求和技术要求",
                "estimated_time": "30-60 minutes",
                "dependencies": []
            },
            {
                "task_id": "dev-design",
                "title": "技术设计和架构",
                "description": "设计系统架构和技术实现方案",
                "estimated_time": "1-2 hours",
                "dependencies": ["dev-requirements"]
            },
            {
                "task_id": "dev-implementation",
                "title": "代码实现",
                "description": "根据设计文档实现核心功能",
                "estimated_time": "2-4 hours",
                "dependencies": ["dev-design"]
            },
            {
                "task_id": "dev-testing",
                "title": "测试和验证",
                "description": "编写测试用例并验证功能",
                "estimated_time": "1-2 hours",
                "dependencies": ["dev-implementation"]
            }
        ]
    elif task_type == "analysis":
        subtasks = [
            {
                "task_id": "analysis-planning",
                "title": "分析计划制定",
                "description": "制定详细的分析计划和范围",
                "estimated_time": "15-30 minutes",
                "dependencies": []
            },
            {
                "task_id": "data-collection",
                "title": "数据收集和准备",
                "description": "收集和分析所需的数据和信息",
                "estimated_time": "30-60 minutes",
                "dependencies": ["analysis-planning"]
            },
            {
                "task_id": "analysis-execution",
                "title": "执行分析",
                "description": "进行详细的数据分析和评估",
                "estimated_time": "1-2 hours",
                "dependencies": ["data-collection"]
            }
        ]
    else:
        # 通用任务分解
        subtasks = [
            {
                "task_id": "task-planning",
                "title": "任务规划",
                "description": "制定详细的执行计划和步骤",
                "estimated_time": "15-30 minutes",
                "dependencies": []
            },
            {
                "task_id": "task-execution",
                "title": "任务执行",
                "description": "按照计划执行主要任务",
                "estimated_time": "1-3 hours",
                "dependencies": ["task-planning"]
            },
            {
                "task_id": "task-review",
                "title": "结果检查和优化",
                "description": "检查执行结果并进行必要优化",
                "estimated_time": "30-60 minutes",
                "dependencies": ["task-execution"]
            }
        ]

    return {
        "subtasks": subtasks,
        "total_estimated_time": sum([
            int(time.split("-")[1].split()[0]) if "-" in time else 2
            for task in subtasks
            for time in [task.get("estimated_time", "2 hours")]
        ])
    }


def _create_decomposition_summary(decomposition_result: Dict[str, Any]) -> str:
    """创建分解结果摘要"""
    subtasks = decomposition_result.get("subtasks", [])
    total_time = decomposition_result.get("total_estimated_time", 0)

    summary = f"**任务分解结果：**\n"
    summary += f"- 子任务数量: {len(subtasks)}\n"
    summary += f"- 预估总时间: {total_time} 小时\n\n"

    summary += "**子任务列表：**\n"
    for i, task in enumerate(subtasks, 1):
        summary += f"{i}. **{task['title']}** ({task['estimated_time']})\n"
        summary += f"   {task['description']}\n"
        if task['dependencies']:
            summary += f"   依赖: {', '.join(task['dependencies'])}\n"
        summary += "\n"

    return summary


async def _assign_agents_to_tasks(
    decomposition_result: Dict[str, Any],
    available_agents: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """为任务分配智能体"""
    subtasks = decomposition_result.get("subtasks", [])
    assignments = {}

    # 模拟智能体分配逻辑
    for task in subtasks:
        task_id = task["task_id"]
        task_title = task["title"].lower()

        # 基于任务类型选择合适的智能体
        if "需求" in task_title or "分析" in task_title:
            assigned_agent = "meta-agent"
        elif "设计" in task_title or "架构" in task_title:
            assigned_agent = "coordinator"
        elif "执行" in task_title or "实现" in task_title:
            assigned_agent = "task-decomposer"
        else:
            assigned_agent = "meta-agent"  # 默认分配

        assignments[task_id] = {
            "agent_id": assigned_agent,
            "task": task,
            "assigned_at": datetime.now().isoformat(),
            "status": "assigned"
        }

    return {
        "assignments": assignments,
        "pending_tasks": list(assignments.keys())
    }


def _create_assignment_summary(assignment_result: Dict[str, Any]) -> str:
    """创建分配结果摘要"""
    assignments = assignment_result.get("assignments", {})

    summary = f"**智能体分配结果：**\n"
    summary += f"- 已分配任务: {len(assignments)}\n\n"

    summary += "**分配详情：**\n"
    for task_id, assignment in assignments.items():
        agent_id = assignment["agent_id"]
        task_title = assignment["task"]["title"]
        summary += f"- {task_title} → {agent_id}\n"

    summary += "\n任务已分配给相应的智能体，开始执行..."

    return summary