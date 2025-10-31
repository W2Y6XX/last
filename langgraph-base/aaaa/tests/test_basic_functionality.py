"""
基本功能测试 - 验证系统核心功能
"""

import pytest
import asyncio
from datetime import datetime
from pathlib import Path
import sys

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 测试基本导入
def test_basic_imports():
    """测试基本模块导入"""
    try:
        from src.core.types import AgentType, TaskStatus, Priority
        from src.core.config import ConfigManager
        from src.utils.logging import setup_logging, get_logger
        print("✓ 基本模块导入成功")
        assert True
    except Exception as e:
        print(f"✗ 导入失败: {e}")
        assert False, f"Import failed: {e}"

# 测试配置管理
def test_config_manager():
    """测试配置管理器"""
    try:
        from src.core.config import ConfigManager

        config_manager = ConfigManager()
        config = config_manager.load_config("default")

        assert config is not None
        assert hasattr(config, 'system')
        assert hasattr(config, 'server')
        print("✓ 配置管理器测试通过")

    except Exception as e:
        print(f"✗ 配置管理器测试失败: {e}")
        assert False, f"Config manager test failed: {e}"

# 测试类型系统
def test_type_system():
    """测试类型系统"""
    try:
        from src.core.types import AgentType, TaskStatus, Priority, AgentInfo, TaskInfo

        # 测试枚举
        assert AgentType.META.value == "meta"
        assert TaskStatus.PENDING.value == "pending"
        assert Priority.MEDIUM.value == "medium"

        # 测试数据类
        agent_info = AgentInfo(
            agent_id="test-agent",
            agent_type=AgentType.META,
            name="Test Agent",
            description="A test agent",
            capabilities=[]
        )

        assert agent_info.agent_id == "test-agent"
        assert agent_info.agent_type == AgentType.META

        task_info = TaskInfo(
            task_id="test-task",
            title="Test Task",
            description="A test task"
        )

        assert task_info.task_id == "test-task"
        assert task_info.status == TaskStatus.PENDING

        print("✓ 类型系统测试通过")

    except Exception as e:
        print(f"✗ 类型系统测试失败: {e}")
        assert False, f"Type system test failed: {e}"

# 测试日志系统
def test_logging_system():
    """测试日志系统"""
    try:
        from src.utils.logging import setup_logging, get_logger

        # 设置日志
        setup_logging(level="INFO")

        # 获取日志器
        logger = get_logger("test")

        # 测试日志记录
        logger.info("Test log message")

        print("✓ 日志系统测试通过")

    except Exception as e:
        print(f"✗ 日志系统测试失败: {e}")
        assert False, f"Logging system test failed: {e}"

# 测试异常系统
def test_exception_system():
    """测试异常系统"""
    try:
        from src.core.exceptions import (
            AgentSystemError, AgentError, TaskError,
            CommunicationError, WorkflowError
        )

        # 测试异常创建
        error = AgentSystemError("Test error")
        assert str(error) == "Test error"

        agent_error = AgentError("Agent error")
        assert str(agent_error) == "Agent error"

        print("✓ 异常系统测试通过")

    except Exception as e:
        print(f"✗ 异常系统测试失败: {e}")
        assert False, f"Exception system test failed: {e}"

# 异步测试：简单的消息总线功能
@pytest.mark.asyncio
async def test_message_bus_basic():
    """测试消息总线基本功能"""
    try:
        from src.communication.message_bus import MessageBus
        from src.core.types import MessageType, Priority, MessageContent

        # 创建消息总线
        bus = MessageBus(max_queue_size=10)
        await bus.start()

        # 注册智能体
        await bus.register_agent("test-agent")

        # 创建消息
        message = MessageContent(
            message_type=MessageType.TASK_REQUEST,
            sender_id="sender",
            receiver_id="test-agent",
            content={
                "task_id": "test-task",
                "title": "Test Task",
                "description": "Test description"
            },
            priority=Priority.MEDIUM
        )

        # 发送消息
        await bus.send_message(message)

        # 检查统计
        stats = bus.get_statistics()
        assert stats["messages_sent"] >= 1

        # 停止消息总线
        await bus.stop()

        print("SUCCESS: Message bus basic test passed")

    except Exception as e:
        print(f"FAILED: Message bus test failed: {e}")
        assert False, f"Message bus test failed: {e}"

# 异步测试：简单的任务管理功能
@pytest.mark.asyncio
async def test_task_manager_basic():
    """测试任务管理器基本功能"""
    try:
        from src.task_management.task_manager import TaskManager

        # 创建任务管理器
        task_manager = TaskManager()
        await task_manager.start()

        # 创建任务
        task_id = await task_manager.create_task(
            title="Test Task",
            description="A test task"
        )

        assert task_id is not None

        # 获取任务信息
        task_info = await task_manager.get_task_info(task_id)
        assert task_info is not None
        assert task_info.title == "Test Task"

        # 更新任务状态
        success = await task_manager.update_task_status(task_id, "in_progress")
        assert success

        # 停止任务管理器
        await task_manager.stop()

        print("✓ 任务管理器基本测试通过")

    except Exception as e:
        print(f"✗ 任务管理器测试失败: {e}")
        assert False, f"Task manager test failed: {e}"

# 测试系统集成（简化版）
@pytest.mark.asyncio
async def test_system_integration():
    """测试系统集成"""
    try:
        from src.core.coordinator import SystemCoordinator

        # 创建系统协调器
        coordinator = SystemCoordinator()
        await coordinator.initialize()

        # 检查系统状态
        status = await coordinator.get_system_status()
        assert status is not None
        assert status.total_agents >= 1  # 至少有 MetaAgent

        # 停止系统
        await coordinator.stop()

        print("✓ 系统集成测试通过")

    except Exception as e:
        print(f"✗ 系统集成测试失败: {e}")
        assert False, f"System integration test failed: {e}"

# 运行所有测试
def run_all_tests():
    """运行所有测试"""
    print("开始运行基本功能测试...")
    print("=" * 50)

    tests = [
        test_basic_imports,
        test_config_manager,
        test_type_system,
        test_logging_system,
        test_exception_system,
    ]

    sync_passed = 0
    sync_total = len(tests)

    for test in tests:
        try:
            test()
            sync_passed += 1
        except Exception as e:
            print(f"✗ 测试失败: {test.__name__}: {e}")

    print(f"\n同步测试结果: {sync_passed}/{sync_total} 通过")

    # 运行异步测试
    async_tests = [
        test_message_bus_basic,
        test_task_manager_basic,
        test_system_integration,
    ]

    async def run_async_tests():
        async_passed = 0
        async_total = len(async_tests)

        for test in async_tests:
            try:
                await test()
                async_passed += 1
            except Exception as e:
                print(f"✗ 异步测试失败: {test.__name__}: {e}")

        print(f"异步测试结果: {async_passed}/{async_total} 通过")

        total_passed = sync_passed + async_passed
        total_tests = sync_total + async_total

        print(f"\n总体测试结果: {total_passed}/{total_tests} 通过")
        print(f"成功率: {total_passed/total_tests*100:.1f}%")

        if total_passed == total_tests:
            print("所有测试都通过了！")
        else:
            print("部分测试失败，请检查错误信息")

        return total_passed == total_tests

    return asyncio.run(run_async_tests())

if __name__ == "__main__":
    run_all_tests()