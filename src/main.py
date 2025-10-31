"""
LangGraph多智能体系统 - 主入口文件

重构说明：整合多个入口点，创建统一的应用启动接口
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from langgraph_multi_agent.main import main as langgraph_main
from src.agents.meta.meta_agent import MetaAgent
from src.agents.coordinator.coordinator_agent import CoordinatorAgent
from src.agents.task_decomposer.task_decomposer_agent import TaskDecomposerAgent
from src.agents.base.base_agent import MessageBus, MessageType

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class UnifiedMultiAgentSystem:
    """统一的多智能体系统"""

    def __init__(self):
        self.message_bus = MessageBus()
        self.agents = {}
        self.is_running = False

    async def initialize_agents(self):
        """初始化所有智能体"""
        try:
            logger.info("初始化多智能体系统...")

            # 初始化核心智能体
            meta_agent = MetaAgent("meta_agent", message_bus=self.message_bus)
            coordinator = CoordinatorAgent("coordinator", message_bus=self.message_bus)
            task_decomposer = TaskDecomposerAgent("task_decomposer", message_bus=self.message_bus)

            # 初始化智能体
            agents = [meta_agent, coordinator, task_decomposer]

            for agent in agents:
                if await agent.initialize():
                    self.agents[agent.agent_id] = agent
                    logger.info(f"智能体 {agent.agent_id} 初始化成功")
                else:
                    logger.error(f"智能体 {agent.agent_id} 初始化失败")
                    return False

            logger.info(f"智能体系统初始化完成，共 {len(self.agents)} 个智能体")
            return True

        except Exception as e:
            logger.error(f"智能体系统初始化失败: {e}")
            return False

    async def start_system(self):
        """启动系统"""
        try:
            if not self.agents:
                await self.initialize_agents()

            logger.info("启动多智能体系统...")

            # 启动所有智能体
            for agent_id, agent in self.agents.items():
                if await agent.start():
                    logger.info(f"智能体 {agent_id} 启动成功")
                else:
                    logger.error(f"智能体 {agent_id} 启动失败")
                    return False

            self.is_running = True
            logger.info("多智能体系统启动完成")
            return True

        except Exception as e:
            logger.error(f"系统启动失败: {e}")
            return False

    async def stop_system(self):
        """停止系统"""
        try:
            logger.info("停止多智能体系统...")

            # 停止所有智能体
            for agent_id, agent in self.agents.items():
                await agent.stop()
                logger.info(f"智能体 {agent_id} 已停止")

            self.is_running = False
            logger.info("多智能体系统已停止")

        except Exception as e:
            logger.error(f"系统停止失败: {e}")

    def get_system_status(self) -> dict:
        """获取系统状态"""
        status = {
            "system_running": self.is_running,
            "agents_count": len(self.agents),
            "agents": {}
        }

        for agent_id, agent in self.agents.items():
            status["agents"][agent_id] = agent.get_status()

        return status

async def run_unified_system():
    """运行统一的多智能体系统"""
    system = UnifiedMultiAgentSystem()

    try:
        # 初始化并启动系统
        if await system.start_system():
            print("多智能体系统正在运行...")
            print("按 Ctrl+C 停止系统")

            # 保持运行
            while system.is_running:
                await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("收到停止信号")
    finally:
        await system.stop_system()

def main():
    """主入口函数"""
    import argparse

    parser = argparse.ArgumentParser(description="LangGraph多智能体系统")
    parser.add_argument("--mode", choices=["unified", "langgraph"], default="unified",
                       help="运行模式：unified（统一多智能体）或langgraph（LangGraph系统）")
    parser.add_argument("--host", default="0.0.0.0", help="API服务器主机")
    parser.add_argument("--port", type=int, default=8000, help="API服务器端口")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.mode == "unified":
        # 运行统一的多智能体系统
        print("启动统一多智能体系统...")
        asyncio.run(run_unified_system())
    else:
        # 运行LangGraph系统
        print("启动LangGraph系统...")
        # 传递命令行参数给LangGraph系统
        sys.argv = [sys.argv[0], "--host", args.host, "--port", str(args.port)]
        if args.debug:
            sys.argv.append("--log-level")
            sys.argv.append("DEBUG")
        langgraph_main()

if __name__ == "__main__":
    main()