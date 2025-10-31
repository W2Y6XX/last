import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 直接导入智能体类，避免循环导入
try:
    from src.agents.base.base_agent import BaseAgent, MessageType, Message, Config, MessageBus
    from src.agents.meta.meta_agent import MetaAgent
    from src.agents.coordinator.coordinator_agent import CoordinatorAgent
    from src.agents.task_decomposer.task_decomposer_agent import TaskDecomposerAgent
    
    logger.info("✅ 所有智能体类导入成功")
except ImportError as e:
    logger.error(f"❌ 导入智能体类失败: {e}")
    sys.exit(1)

class TestAgentSystem:
    """测试智能体系统"""
    
    def __init__(self):
        self.message_bus = MessageBus()
        self.agents = {}
        self.test_results = []
        
    async def setup_agents(self):
        """设置智能体"""
        logger.info("🚀 开始设置智能体...")
        
        # 创建智能体实例
        meta_agent = MetaAgent("meta_agent", message_bus=self.message_bus)
        coordinator = CoordinatorAgent("coordinator", message_bus=self.message_bus)
        task_decomposer = TaskDecomposerAgent("task_decomposer", message_bus=self.message_bus)
        
        # 初始化智能体
        agents = [meta_agent, coordinator, task_decomposer]
        
        for agent in agents:
            try:
                success = await agent.initialize()
                if success:
                    self.agents[agent.agent_id] = agent
                    logger.info(f"✅ 智能体 {agent.agent_id} 初始化成功")
                    self.test_results.append(f"{agent.agent_id}: 初始化成功")
                else:
                    logger.error(f"❌ 智能体 {agent.agent_id} 初始化失败")
                    self.test_results.append(f"{agent.agent_id}: 初始化失败")
            except Exception as e:
                logger.error(f"❌ 智能体 {agent.agent_id} 设置失败: {e}")
                self.test_results.append(f"{agent.agent_id}: 设置失败 - {str(e)}")

async def main():
    """主测试函数"""
    print("🚀 开始多智能体系统测试...")
    print("=" * 60)
    
    test_system = TestAgentSystem()
    
    try:
        # 1. 设置智能体
        await test_system.setup_agents()
        
        print(f"📊 系统状态: 共初始化了 {len(test_system.agents)} 个智能体")
        for result in test_system.test_results:
            print(f"• {result}")
        
    except Exception as e:
        logger.error(f"❌ 测试过程异常: {e}")
        test_system.test_results.append(f"main_test: 异常 - {str(e)}")
    
    finally:
        print("=" * 60)
        print("🎉 测试完成")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试执行失败: {e}")
        logger.error(f"主程序错误: {e}")
