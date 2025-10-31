"""
端到端测试 - 验证完整的工作流程
"""

import pytest
import asyncio
from datetime import datetime, timedelta

from src.core.interface import LangGraphAgentSystem, TaskRequest


class TestEndToEndWorkflow:
    """端到端工作流测试"""

    @pytest.fixture
    async def system(self):
        """创建系统实例"""
        system = LangGraphAgentSystem()
        await system.start()
        yield system
        await system.stop()

    @pytest.mark.asyncio
    async def test_complete_task_workflow(self, system):
        """测试完整的任务工作流：提交 -> 分析 -> 分解 -> 分配 -> 执行"""
        print("\n=== 开始完整任务工作流测试 ===")

        # 1. 提交复杂任务
        print("1. 提交复杂开发任务...")
        request = TaskRequest(
            title="开发用户管理系统",
            description="需要开发一个完整的用户管理系统，包括用户注册、登录、权限管理、用户信息管理等功能。系统需要支持Web界面，使用React前端和Node.js后端，数据库使用PostgreSQL。需要包含用户认证、权限控制、数据验证等功能。",
            priority="high",
            requester_id="product-manager"
        )

        response = await system.submit_task(request)
        assert response.success, f"任务提交失败: {response.message}"
        task_id = response.task_id
        print(f"✓ 任务提交成功，任务ID: {task_id}")

        # 2. 等待任务分析和分解
        print("2. 等待任务分析和分解...")
        await asyncio.sleep(3.0)

        # 3. 检查任务状态
        print("3. 检查任务状态...")
        task_status = await system.get_task_status(task_id)
        assert "error" not in task_status, f"获取任务状态失败: {task_status}"
        print(f"✓ 任务状态: {task_status['status']}")
        print(f"✓ 任务标题: {task_status['title']}")

        # 4. 检查子任务创建
        print("4. 检查子任务创建...")
        task_list = await system.list_tasks(limit=20)
        related_tasks = [
            task for task in task_list
            if "用户管理" in task["title"] or "开发" in task["title"] or task_id == task["task_id"]
        ]
        print(f"✓ 找到相关任务: {len(related_tasks)} 个")

        # 5. 检查智能体分配
        print("5. 检查智能体分配...")
        agents = await system.get_agents()
        print(f"✓ 活跃智能体数量: {len(agents)}")
        for agent in agents[:3]:  # 显示前3个智能体
            print(f"  - {agent.name} ({agent.agent_type}): {agent.current_tasks} 个任务, 负载 {agent.load_percentage:.1f}%")

        # 6. 检查系统状态
        print("6. 检查系统状态...")
        system_status = await system.get_system_status()
        print(f"✓ 系统状态: 健康={system_status.is_healthy}")
        print(f"✓ 总任务数: {system_status.total_tasks}")
        print(f"✓ 运行中任务: {system_status.running_tasks}")

        print("\n=== 完整任务工作流测试完成 ===")

    @pytest.mark.asyncio
    async def test_multi_agent_collaboration(self, system):
        """测试多智能体协作场景"""
        print("\n=== 开始多智能体协作测试 ===")

        # 创建一系列相关任务
        tasks = []

        # 1. 需求分析任务
        print("1. 创建需求分析任务...")
        req_task = TaskRequest(
            title="电商系统需求分析",
            description="分析电商系统的功能需求，包括商品管理、订单处理、支付集成、用户管理、库存管理等模块的详细需求。",
            priority="high"
        )
        req_response = await system.submit_task(req_task)
        if req_response.success:
            tasks.append(req_response.task_id)
            print(f"✓ 需求分析任务创建: {req_response.task_id}")

        # 2. 系统设计任务
        print("2. 创建系统设计任务...")
        design_task = TaskRequest(
            title="电商系统架构设计",
            description="基于需求分析结果，设计电商系统的整体架构，包括微服务划分、数据库设计、API设计等。",
            priority="high"
        )
        design_response = await system.submit_task(design_task)
        if design_response.success:
            tasks.append(design_response.task_id)
            print(f"✓ 系统设计任务创建: {design_response.task_id}")

        # 3. 开发实现任务
        print("3. 创建开发实现任务...")
        dev_task = TaskRequest(
            title="电商系统核心功能开发",
            description="实现电商系统的核心功能，包括用户注册登录、商品展示、购物车、订单处理等。",
            priority="medium"
        )
        dev_response = await system.submit_task(dev_task)
        if dev_response.success:
            tasks.append(dev_response.task_id)
            print(f"✓ 开发实现任务创建: {dev_response.task_id}")

        # 等待任务处理
        print("4. 等待任务处理...")
        await asyncio.sleep(5.0)

        # 检查任务协作情况
        print("5. 检查任务协作情况...")
        agent_assignments = {}
        for task_id in tasks:
            task_status = await system.get_task_status(task_id)
            if "error" not in task_status:
                assigned_agent = task_status.get("assigned_agent")
                if assigned_agent:
                    agent_assignments[task_id] = assigned_agent
                    print(f"✓ 任务 {task_id[:8]}... 分配给 {assigned_agent}")

        # 检查智能体负载分布
        print("6. 检查智能体负载分布...")
        agents = await system.get_agents()
        load_distribution = {}
        for agent in agents:
            load_distribution[agent.agent_id] = agent.load_percentage
            print(f"  - {agent.name}: {agent.load_percentage:.1f}% 负载")

        print("\n=== 多智能体协作测试完成 ===")

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, system):
        """测试错误恢复工作流"""
        print("\n=== 开始错误恢复测试 ===")

        # 1. 提交正常任务
        print("1. 提交正常任务...")
        normal_task = TaskRequest(
            title="数据处理任务",
            description="处理用户数据，进行数据清洗和转换。",
            priority="medium"
        )
        normal_response = await system.submit_task(normal_task)
        assert normal_response.success
        normal_task_id = normal_response.task_id
        print(f"✓ 正常任务提交: {normal_task_id}")

        # 2. 提交可能导致问题的任务
        print("2. 提交有挑战性的任务...")
        challenging_task = TaskRequest(
            title="复杂算法实现",
            description="实现一个复杂的机器学习算法，需要大量计算资源和复杂的数学运算。",
            priority="high"
        )
        challenging_response = await system.submit_task(challenging_task)
        challenging_task_id = challenging_response.task_id
        print(f"✓ 复杂任务提交: {challenging_task_id}")

        # 等待处理
        await asyncio.sleep(3.0)

        # 3. 检查任务状态
        print("3. 检查任务状态...")
        for task_id, task_name in [(normal_task_id, "正常任务"), (challenging_task_id, "复杂任务")]:
            status = await system.get_task_status(task_id)
            if "error" not in status:
                print(f"✓ {task_name}: {status['status']}")
                if status.get("error"):
                    print(f"  错误信息: {status['error']}")

        # 4. 测试任务取消和恢复
        print("4. 测试任务取消...")
        if challenging_response.success:
            cancel_result = await system.cancel_task(challenging_task_id, "测试取消恢复")
            print(f"✓ 任务取消结果: {cancel_result['success']}")

        # 5. 检查系统健康状态
        print("5. 检查系统健康状态...")
        health = await system.coordinator.perform_health_check()
        print(f"✓ 系统健康状态: {health['overall']}")
        if health['overall'] != 'healthy':
            print("  问题组件:")
            for component, info in health['components'].items():
                if info['status'] != 'healthy':
                    print(f"    - {component}: {info['status']}")

        print("\n=== 错误恢复测试完成 ===")

    @pytest.mark.asyncio
    async def test_performance_monitoring(self, system):
        """测试性能监控功能"""
        print("\n=== 开始性能监控测试 ===")

        # 1. 记录初始性能指标
        print("1. 记录初始性能指标...")
        initial_metrics = await system.get_system_metrics()
        initial_time = datetime.now()

        # 2. 提交批量任务
        print("2. 提交批量任务...")
        task_count = 10
        submitted_tasks = []

        start_time = datetime.now()
        for i in range(task_count):
            task = TaskRequest(
                title=f"性能测试任务 {i+1}",
                description=f"第{i+1}个性能测试任务，用于测试系统处理能力。",
                priority="medium"
            )
            response = await system.submit_task(task)
            if response.success:
                submitted_tasks.append(response.task_id)

        submission_time = (datetime.now() - start_time).total_seconds()
        print(f"✓ {len(submitted_tasks)} 个任务提交完成，耗时 {submission_time:.2f} 秒")

        # 3. 等待任务处理
        print("3. 等待任务处理...")
        await asyncio.sleep(8.0)

        # 4. 收集性能数据
        print("4. 收集性能数据...")
        final_metrics = await system.get_system_metrics()

        # 5. 分析性能指标
        print("5. 分析性能指标...")
        if 'tasks' in final_metrics and 'total_tasks' in final_metrics['tasks']:
            final_task_count = final_metrics['tasks']['total_tasks']
            print(f"✓ 总任务数: {final_task_count}")
            print(f"✓ 完成任务数: {final_metrics['tasks'].get('completed_tasks', 0)}")
            print(f"✓ 失败任务数: {final_metrics['tasks'].get('failed_tasks', 0)}")

        if 'messages' in final_metrics:
            message_stats = final_metrics['messages']
            print(f"✓ 消息统计: {message_stats}")

        # 6. 检查系统资源使用
        print("6. 检查系统资源使用...")
        system_status = await system.get_system_status()
        print(f"✓ 系统负载: {system_status.system_load:.1f}%")
        print(f"✓ 活跃智能体: {system_status.active_agents}")

        # 7. 测试指标导出
        print("7. 测试指标导出...")
        export_response = await system.export_system_data("json")
        assert export_response['success']
        print(f"✓ 数据导出成功，数据大小: {len(str(export_response['data']))} 字符")

        print("\n=== 性能监控测试完成 ===")

    @pytest.mark.asyncio
    async def test_system_scalability(self, system):
        """测试系统可扩展性"""
        print("\n=== 开始系统可扩展性测试 ===")

        # 1. 渐进式负载测试
        print("1. 渐进式负载测试...")
        load_levels = [5, 10, 15, 20]  # 不同负载级别
        performance_data = []

        for load_level in load_levels:
            print(f"  测试负载级别: {load_level} 个任务")

            start_time = datetime.now()

            # 提交任务
            tasks = []
            for i in range(load_level):
                task = TaskRequest(
                    title=f"负载测试任务 {load_level}-{i+1}",
                    description=f"负载级别 {load_level} 的第 {i+1} 个任务",
                    priority="medium"
                )
                response = await system.submit_task(task)
                if response.success:
                    tasks.append(response.task_id)

            submission_time = (datetime.now() - start_time).total_seconds()

            # 等待处理
            await asyncio.sleep(3.0)

            # 收集指标
            system_status = await system.get_system_status()
            metrics = await system.get_system_metrics()

            performance_data.append({
                'load_level': load_level,
                'submission_time': submission_time,
                'submitted_tasks': len(tasks),
                'system_load': system_status.system_load,
                'active_agents': system_status.active_agents
            })

            print(f"    ✓ 提交时间: {submission_time:.2f}s")
            print(f"    ✓ 系统负载: {system_status.system_load:.1f}%")

        # 2. 分析可扩展性结果
        print("2. 分析可扩展性结果...")
        print("  负载级别 | 提交时间 | 系统负载 | 活跃智能体")
        print("  --------|----------|----------|----------")
        for data in performance_data:
            print(f"  {data['load_level']:8d} | {data['submission_time']:8.2f}s | {data['system_load']:8.1f}% | {data['active_agents']:10d}")

        # 3. 验证系统稳定性
        print("3. 验证系统稳定性...")
        final_health = await system.coordinator.perform_health_check()
        assert final_health['overall'] in ['healthy', 'degraded'], f"系统状态异常: {final_health['overall']}"
        print(f"✓ 系统最终状态: {final_health['overall']}")

        print("\n=== 系统可扩展性测试完成 ===")

    @pytest.mark.asyncio
    async def test_long_running_workflow(self, system):
        """测试长时间运行工作流"""
        print("\n=== 开始长时间运行测试 ===")

        # 1. 创建长期任务序列
        print("1. 创建长期任务序列...")
        task_sequence = []

        # 分阶段创建任务
        phases = ["规划", "设计", "开发", "测试", "部署"]
        for phase in phases:
            task = TaskRequest(
                title=f"{phase}阶段任务",
                description=f"项目{phase}阶段的详细工作内容，需要仔细执行和验证。",
                priority="medium"
            )
            response = await system.submit_task(task)
            if response.success:
                task_sequence.append((response.task_id, phase))
                print(f"✓ {phase}阶段任务创建: {response.task_id}")

        # 2. 监控任务执行进度
        print("2. 监控任务执行进度...")
        monitoring_duration = 15  # 监控15秒
        start_time = datetime.now()

        while (datetime.now() - start_time).total_seconds() < monitoring_duration:
            await asyncio.sleep(3.0)

            completed_count = 0
            for task_id, phase in task_sequence:
                status = await system.get_task_status(task_id)
                if "error" not in status and status['status'] == 'completed':
                    completed_count += 1

            progress = (completed_count / len(task_sequence)) * 100
            print(f"  进度: {progress:.1f}% ({completed_count}/{len(task_sequence)})")

        # 3. 最终状态检查
        print("3. 最终状态检查...")
        final_status = await system.get_system_status()
        print(f"✓ 最终系统状态: 健康={final_status.is_healthy}")
        print(f"✓ 总任务数: {final_status.total_tasks}")
        print(f"✓ 完成任务数: {final_status.completed_tasks}")

        print("\n=== 长时间运行测试完成 ===")