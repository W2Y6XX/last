#!/usr/bin/env python3
"""
任务提交示例
演示如何向多智能体系统提交任务
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any

# 假设已安装相关的通信模块
try:
    from communication.message_bus import get_message_bus
    from communication.protocol import MessageType, Message
except ImportError:
    print("需要安装相关的通信模块")
    exit(1)

class TaskSubmitter:
    """任务提交器"""

    def __init__(self):
        self.message_bus = get_message_bus()

    async def submit_simple_task(self) -> Dict[str, Any]:
        """提交简单任务"""

        task_data = {
            "task_id": f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "task_type": "data_analysis",
            "priority": 5,
            "input_data": {
                "data_source": "database",
                "query": "SELECT * FROM sales WHERE date >= '2024-01-01'",
                "analysis_type": "trend_analysis"
            },
            "requirements": [
                "data_processing",
                "statistical_analysis"
            ],
            "deadline": (datetime.now() + timedelta(hours=2)).isoformat(),
            "requester_id": "user_001",
            "metadata": {
                "project": "quarterly_report",
                "department": "analytics"
            }
        }

        print("提交简单任务...")
        print(f"任务ID: {task_data['task_id']}")
        print(f"任务类型: {task_data['task_type']}")
        print(f"优先级: {task_data['priority']}")

        # 发送任务到元智能体
        response = await self.message_bus.send_message(
            recipient_id="meta-agent-001",
            message_type=MessageType.TASK_REQUEST,
            content=task_data,
            requires_response=True,
            timeout_seconds=30
        )

        if response and response.content.get("success"):
            result = response.content
            print("✅ 任务提交成功!")
            print(f"分配的智能体: {result.get('assigned_agents', [])}")
            print(f"预计完成时间: {result.get('estimated_completion', '未知')}")
            print(f"任务状态: {result.get('status', '已分配')}")
            return result
        else:
            print("❌ 任务提交失败")
            if response:
                print(f"错误信息: {response.content.get('error', '未知错误')}")
            return {"success": False}

    async def submit_complex_task(self) -> Dict[str, Any]:
        """提交复杂任务，需要任务拆解"""

        task_data = {
            "task_id": f"complex_task_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "task_type": "complex_analysis",
            "priority": 8,
            "input_data": {
                "project_scope": "multi_market_analysis",
                "data_sources": [
                    "sales_database",
                    "customer_feedback",
                    "market_research",
                    "competitor_data"
                ],
                "analysis_requirements": [
                    "trend_identification",
                    "market_segmentation",
                    "competitive_analysis",
                    "recommendation_generation"
                ],
                "deliverables": [
                    "executive_summary",
                    "detailed_report",
                    "presentation_slides",
                    "actionable_insights"
                ]
            },
            "requirements": [
                "data_collection",
                "statistical_analysis",
                "market_research",
                "report_generation",
                "visualization"
            ],
            "deadline": (datetime.now() + timedelta(days=3)).isoformat(),
            "requester_id": "user_002",
            "decomposition_required": True,
            "decomposition_strategy": "hierarchical",
            "metadata": {
                "project": "strategic_planning_2024",
                "stakeholders": ["CEO", "CTO", "VP_Marketing"],
                "budget": 50000,
                "impact_level": "high"
            }
        }

        print("\n提交复杂任务...")
        print(f"任务ID: {task_data['task_id']}")
        print(f"任务类型: {task_data['task_type']}")
        print(f"优先级: {task_data['priority']}")
        print(f"需要分解: {task_data['decomposition_required']}")
        print(f"分解策略: {task_data['decomposition_strategy']}")

        # 发送复杂任务到任务拆解智能体
        response = await self.message_bus.send_message(
            recipient_id="task-decomposer-001",
            message_type=MessageType.TASK_REQUEST,
            content=task_data,
            requires_response=True,
            timeout_seconds=60
        )

        if response and response.content.get("success"):
            result = response.content
            decomposition = result.get("decomposition", {})
            print("✅ 复杂任务提交成功!")
            print(f"生成了 {decomposition.get('subtasks_count', 0)} 个子任务")
            print(f"预计总时长: {decomposition.get('estimated_duration', 0)} 分钟")

            # 显示子任务概览
            if "execution_plan" in result:
                plan = result["execution_plan"]
                print(f"执行顺序: {len(plan.get('execution_order', []))} 个步骤")
                print(f"监控点: {len(plan.get('monitoring_points', []))} 个")

            return result
        else:
            print("❌ 复杂任务提交失败")
            if response:
                print(f"错误信息: {response.content.get('error', '未知错误')}")
            return {"success": False}

    async def submit_collaborative_task(self) -> Dict[str, Any]:
        """提交需要多智能体协作的任务"""

        collaboration_data = {
            "coordination_type": "establish_collaboration",
            "participants": ["agent-001", "agent-002", "agent-003"],
            "collaboration_type": "data_processing_pipeline",
            "context": {
                "project": "customer_analytics",
                "deadline": (datetime.now() + timedelta(hours=6)).isoformat(),
                "shared_resources": [
                    "customer_database_connection",
                    "analytics_cache",
                    "report_template"
                ],
                "coordination_requirements": {
                    "synchronization_points": ["data_loaded", "analysis_complete", "report_ready"],
                    "communication_frequency": "real_time",
                    "conflict_resolution": "automatic"
                }
            },
            "workflow": {
                "steps": [
                    {
                        "name": "data_extraction",
                        "assigned_to": "agent-001",
                        "dependencies": [],
                        "estimated_duration": 1800
                    },
                    {
                        "name": "data_cleaning",
                        "assigned_to": "agent-002",
                        "dependencies": ["data_extraction"],
                        "estimated_duration": 2400
                    },
                    {
                        "name": "analysis_and_visualization",
                        "assigned_to": "agent-003",
                        "dependencies": ["data_cleaning"],
                        "estimated_duration": 3600
                    }
                ]
            }
        }

        print("\n提交协作任务...")
        print(f"协作类型: {collaboration_data['collaboration_type']}")
        print(f"参与者: {collaboration_data['participants']}")
        print(f"项目: {collaboration_data['context']['project']}")

        # 发送协作请求到协调智能体
        response = await self.message_bus.send_message(
            recipient_id="coordinator-001",
            message_type=MessageType.COORDINATION_REQUEST,
            content=collaboration_data,
            requires_response=True,
            timeout_seconds=45
        )

        if response and response.content.get("success"):
            result = response.content
            print("✅ 协作任务提交成功!")
            print(f"协作会话ID: {result.get('session_id', '未知')}")
            print(f"协作状态: {result.get('status', '未知')}")

            if "collaboration_protocol" in result:
                protocol = result["collaboration_protocol"]
                print(f"协调模式: {protocol.get('coordination_mode', '未知')}")
                print(f"角色分配: {protocol.get('roles', {})}")

            return result
        else:
            print("❌ 协作任务提交失败")
            if response:
                print(f"错误信息: {response.content.get('error', '未知错误')}")
            return {"success": False}

    async def monitor_task_status(self, task_id: str) -> Dict[str, Any]:
        """监控任务状态"""

        print(f"\n监控任务状态: {task_id}")

        status_request = {
            "task_id": task_id,
            "include_details": True,
            "include_subtasks": True
        }

        response = await self.message_bus.send_message(
            recipient_id="meta-agent-001",
            message_type=MessageType.STATUS_REQUEST,
            content=status_request,
            requires_response=True,
            timeout_seconds=15
        )

        if response:
            status = response.content
            print(f"任务状态: {status.get('status', '未知')}")
            print(f"进度: {status.get('progress', 0)}%")
            print(f"当前执行者: {status.get('current_executor', '未知')}")

            if "subtasks" in status:
                subtasks = status["subtasks"]
                print(f"子任务状态:")
                for subtask in subtasks:
                    print(f"  - {subtask['name']}: {subtask['status']}")

            return status
        else:
            print("无法获取任务状态")
            return {"error": "无法获取任务状态"}

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""

        print(f"\n取消任务: {task_id}")

        cancel_request = {
            "task_id": task_id,
            "reason": "用户取消",
            "force": False
        }

        response = await self.message_bus.send_message(
            recipient_id="meta-agent-001",
            message_type=MessageType.CANCELLATION_REQUEST,
            content=cancel_request,
            requires_response=True,
            timeout_seconds=20
        )

        if response and response.content.get("success"):
            print("✅ 任务已取消")
            return True
        else:
            print("❌ 任务取消失败")
            return False


async def main():
    """主函数 - 演示任务提交流程"""

    print("=== 多智能体系统任务提交示例 ===\n")

    submitter = TaskSubmitter()

    try:
        # 1. 提交简单任务
        simple_result = await submitter.submit_simple_task()
        if simple_result.get("success"):
            simple_task_id = simple_result.get("task_id")

            # 监控简单任务状态
            await asyncio.sleep(2)
            await submitter.monitor_task_status(simple_task_id)

        await asyncio.sleep(2)

        # 2. 提交复杂任务
        complex_result = await submitter.submit_complex_task()
        if complex_result.get("success"):
            complex_task_id = complex_result.get("task_id")

            # 监控复杂任务状态
            await asyncio.sleep(3)
            await submitter.monitor_task_status(complex_task_id)

        await asyncio.sleep(2)

        # 3. 提交协作任务
        collab_result = await submitter.submit_collaborative_task()
        if collab_result.get("success"):
            session_id = collab_result.get("result", {}).get("session_id")
            print(f"协作会话已建立: {session_id}")

        await asyncio.sleep(2)

        # 4. 演示任务取消
        if simple_result.get("success"):
            print("\n演示任务取消功能...")
            cancelled = await submitter.cancel_task(simple_task_id)
            if cancelled:
                print("任务取消演示完成")

        print("\n=== 任务提交示例完成 ===")

    except Exception as e:
        print(f"执行过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())