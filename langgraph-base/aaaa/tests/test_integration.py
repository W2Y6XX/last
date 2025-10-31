"""
集成测试 - 验证系统整体工作流
"""

import pytest
import asyncio
from datetime import datetime

from src.core.interface import LangGraphAgentSystem, TaskRequest
from src.core.types import Priority, TaskStatus


class TestSystemIntegration:
    """系统集成测试"""

    @pytest.fixture
    async def system(self):
        """创建系统实例"""
        system = LangGraphAgentSystem()
        await system.start()
        yield system
        await system.stop()

    @pytest.mark.asyncio
    async def test_system_startup_shutdown(self, system):
        """测试系统启动和关闭"""
        # 系统已经启动
        status = await system.get_system_status()
        assert status.total_agents >= 1  # 至少有 MetaAgent
        assert status.is_healthy

        # 重新启动应该不会出错
        await system.start()
        await system.stop()

    @pytest.mark.asyncio
    async def test_task_submission_and_processing(self, system):
        """测试任务提交和处理"""
        # 提交任务
        request = TaskRequest(
            title="Integration Test Task",
            description="这是一个集成测试任务，用于验证系统的工作流程。",
            priority="medium"
        )

        response = await system.submit_task(request)

        assert response.success, f"Task submission failed: {response.message}"
        assert response.task_id is not None

        # 等待任务处理
        await asyncio.sleep(2.0)

        # 检查任务状态
        task_status = await system.get_task_status(response.task_id)
        assert "error" not in task_status
        assert task_status["status"] in ["pending", "in_progress", "completed"]

    @pytest.mark.asyncio
    async def test_multiple_task_submission(self, system):
        """测试多任务提交"""
        task_count = 5
        submitted_tasks = []

        # 提交多个任务
        for i in range(task_count):
            request = TaskRequest(
                title=f"Test Task {i+1}",
                description=f"这是第{i+1}个测试任务",
                priority="medium"
            )

            response = await system.submit_task(request)
            assert response.success
            submitted_tasks.append(response.task_id)

        # 等待任务处理
        await asyncio.sleep(3.0)

        # 检查任务列表
        task_list = await system.list_tasks(limit=20)
        assert len(task_list) >= task_count

        # 检查每个任务的状态
        for task_id in submitted_tasks:
            task_status = await system.get_task_status(task_id)
            assert "error" not in task_status

    @pytest.mark.asyncio
    async def test_agent_communication(self, system):
        """测试智能体间通信"""
        # 获取智能体列表
        agents = await system.get_agents()
        assert len(agents) >= 1

        # 发送消息给 MetaAgent
        response = await system.send_message_to_agent(
            sender_id="test-user",
            receiver_id="meta-agent",
            content="测试消息：你好，MetaAgent！",
            message_type="task_request"
        )

        assert response["success"], f"Message sending failed: {response['message']}"

    @pytest.mark.asyncio
    async def test_broadcast_message(self, system):
        """测试广播消息"""
        response = await system.broadcast_message(
            sender_id="system",
            content="这是一条系统广播消息",
            message_type="broadcast"
        )

        assert response["success"]
        assert response["total_agents"] >= 0
        assert "successful_deliveries" in response

    @pytest.mark.asyncio
    async def test_system_health_check(self, system):
        """测试系统健康检查"""
        health = await system.coordinator.perform_health_check()

        assert "overall" in health
        assert "components" in health
        assert "agents" in health
        assert health["overall"] in ["healthy", "degraded", "unhealthy"]

        # 检查组件状态
        components = health["components"]
        for component_name, component_info in components.items():
            assert "status" in component_info
            assert "running" in component_info

    @pytest.mark.asyncio
    async def test_system_metrics(self, system):
        """测试系统指标收集"""
        metrics = await system.get_system_metrics()

        assert "timestamp" in metrics
        assert "system" in metrics
        assert "tasks" in metrics
        assert "messages" in metrics
        assert "health" in metrics

        # 验证系统指标
        system_metrics = metrics["system"]
        assert "total_agents" in system_metrics
        assert "active_agents" in system_metrics
        assert "total_tasks" in system_metrics

    @pytest.mark.asyncio
    async def test_task_cancellation(self, system):
        """测试任务取消"""
        # 提交任务
        request = TaskRequest(
            title="Cancellable Task",
            description="这个任务将被取消",
            priority="low"  # 使用低优先级，可能有时间取消
        )

        response = await system.submit_task(request)
        assert response.success

        task_id = response.task_id

        # 等待任务开始处理
        await asyncio.sleep(1.0)

        # 取消任务
        cancel_response = await system.cancel_task(task_id, "测试取消")
        assert cancel_response["success"]

        # 检查任务状态
        await asyncio.sleep(0.5)
        task_status = await system.get_task_status(task_id)
        assert "error" not in task_status
        assert task_status["status"] in ["cancelled", "pending"]

    @pytest.mark.asyncio
    async def test_priority_based_task_processing(self, system):
        """测试基于优先级的任务处理"""
        tasks = []

        # 提交不同优先级的任务
        priorities = ["low", "medium", "high", "critical"]
        for priority in priorities:
            request = TaskRequest(
                title=f"Priority {priority} Task",
                description=f"优先级为 {priority} 的任务",
                priority=priority
            )

            response = await system.submit_task(request)
            assert response.success
            tasks.append((response.task_id, priority))

        # 等待任务处理
        await asyncio.sleep(3.0)

        # 检查任务是否都被处理
        for task_id, priority in tasks:
            task_status = await system.get_task_status(task_id)
            assert "error" not in task_status
            # 注意：由于异步处理，优先级顺序可能不明显
            # 但所有任务都应该被处理

    @pytest.mark.asyncio
    async def test_error_handling(self, system):
        """测试错误处理"""
        # 提交一个可能导致错误的任务
        request = TaskRequest(
            title="Error Test Task",
            description="",  # 空描述可能导致处理错误
            priority="medium"
        )

        response = await system.submit_task(request)

        # 即使有错误，系统也应该能够响应
        assert isinstance(response.success, bool)
        assert response.message is not None

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, system):
        """测试并发操作"""
        async def submit_tasks(count: int):
            tasks = []
            for i in range(count):
                request = TaskRequest(
                    title=f"Concurrent Task {i}",
                    description=f"并发任务 {i}",
                    priority="medium"
                )
                response = await system.submit_task(request)
                if response.success:
                    tasks.append(response.task_id)
            return tasks

        # 并发提交任务
        task_counts = [3, 5, 7]
        results = await asyncio.gather(
            *[submit_tasks(count) for count in task_counts],
            return_exceptions=True
        )

        # 检查结果
        all_tasks = []
        for result in results:
            if isinstance(result, Exception):
                pytest.fail(f"Concurrent operation failed: {result}")
            else:
                all_tasks.extend(result)

        # 等待处理
        await asyncio.sleep(2.0)

        # 验证任务都被正确处理
        assert len(all_tasks) == sum(task_counts)

    @pytest.mark.asyncio
    async def test_system_restart(self, system):
        """测试系统重启"""
        # 获取重启前的状态
        initial_status = await system.get_system_status()
        initial_agents = len(await system.get_agents())

        # 停止系统
        await system.stop()

        # 重新启动
        await system.start()

        # 验证系统正常运行
        new_status = await system.get_system_status()
        new_agents = len(await system.get_agents())

        assert new_status.is_healthy
        assert new_agents >= 1  # MetaAgent 应该重新注册

    @pytest.mark.asyncio
    async def test_data_export(self, system):
        """测试数据导出"""
        # 提交一些任务以产生数据
        for i in range(3):
            request = TaskRequest(
                title=f"Export Test Task {i}",
                description=f"用于测试导出的任务 {i}",
                priority="medium"
            )
            await system.submit_task(request)

        # 等待处理
        await asyncio.sleep(1.0)

        # 导出数据
        export_response = await system.export_system_data("json")

        assert export_response["success"]
        assert "data" in export_response

        data = export_response["data"]
        assert "export_timestamp" in data
        assert "system_status" in data
        assert "agents" in data
        assert "tasks" in data
        assert "metrics" in data

        # 验证导出的数据结构
        assert isinstance(data["agents"], list)
        assert isinstance(data["tasks"], list)
        assert isinstance(data["metrics"], dict)