"""
简单测试脚本 - 验证系统核心功能
"""

import sys
import asyncio
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """测试基本导入"""
    print("Testing imports...")
    try:
        from src.core.types import AgentType, TaskStatus, Priority
        from src.core.config import ConfigManager
        from src.utils.logging import setup_logging, get_logger
        print("All imports successful")
        return True
    except Exception as e:
        print(f"Import failed: {e}")
        return False

def test_config():
    """测试配置管理"""
    print("Testing configuration...")
    try:
        from src.core.config import ConfigManager
        config_manager = ConfigManager()
        config = config_manager.load_config("default")
        print("SUCCESS: Configuration loaded successfully")
        return True
    except Exception as e:
        print(f"FAILED: Configuration test failed: {e}")
        return False

def test_types():
    """测试类型系统"""
    print("Testing type system...")
    try:
        from src.core.types import AgentType, TaskStatus, Priority
        assert AgentType.META.value == "meta"
        assert TaskStatus.PENDING.value == "pending"
        assert Priority.MEDIUM.value == "medium"
        print("SUCCESS: Type system working correctly")
        return True
    except Exception as e:
        print(f"FAILED: Type system test failed: {e}")
        return False

async def test_message_bus():
    """测试消息总线"""
    print("Testing message bus...")
    try:
        from src.communication.message_bus import MessageBus
        from src.core.types import MessageType, Priority

        bus = MessageBus(max_queue_size=10)
        await bus.start()

        await bus.register_agent("test-agent")

        # 使用 MessageContent 而不是协议消息
        from src.core.types import MessageContent
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

        await bus.send_message(message)

        stats = bus.get_statistics()
        assert stats["messages_sent"] >= 1

        await bus.stop()
        print("SUCCESS: Message bus working correctly")
        return True
    except Exception as e:
        print(f"FAILED: Message bus test failed: {e}")
        return False

async def test_task_manager():
    """测试任务管理器"""
    print("Testing task manager...")
    try:
        from src.task_management.task_manager import TaskManager

        task_manager = TaskManager()
        await task_manager.start()

        task_id = await task_manager.create_task(
            title="Test Task",
            description="A test task"
        )

        assert task_id is not None

        task_info = await task_manager.get_task_info(task_id)
        assert task_info.title == "Test Task"

        await task_manager.stop()
        print("SUCCESS: Task manager working correctly")
        return True
    except Exception as e:
        print(f"FAILED: Task manager test failed: {e}")
        return False

async def run_tests():
    """运行所有测试"""
    print("Starting system tests...")
    print("=" * 40)

    # 同步测试
    sync_tests = [test_imports, test_config, test_types]
    sync_passed = 0

    for test in sync_tests:
        if test():
            sync_passed += 1

    print(f"Sync tests: {sync_passed}/{len(sync_tests)} passed")

    # 异步测试
    async_tests = [test_message_bus, test_task_manager]
    async_passed = 0

    for test in async_tests:
        if await test():
            async_passed += 1

    print(f"Async tests: {async_passed}/{len(async_tests)} passed")

    # 总体结果
    total_passed = sync_passed + async_passed
    total_tests = len(sync_tests) + len(async_tests)

    print(f"\nOverall results: {total_passed}/{total_tests} tests passed")
    print(f"Success rate: {total_passed/total_tests*100:.1f}%")

    if total_passed == total_tests:
        print("All tests passed! System is working correctly.")
        return True
    else:
        print("Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)