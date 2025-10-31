#!/usr/bin/env python3
"""
LangGraph 多智能体系统启动脚本
"""

import asyncio
import argparse
import signal
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.interface import LangGraphAgentSystem
from src.core.config import ConfigManager
from src.utils.logging import setup_logging, get_logger


class SystemRunner:
    """系统运行器"""

    def __init__(self, config_path: str = None, environment: str = None):
        self.config_manager = ConfigManager()
        self.system = None
        self.running = False
        self.logger = None

        # 加载配置
        if config_path:
            # 从指定文件加载配置
            self.config = self._load_config_from_file(config_path)
        else:
            # 从环境或默认加载配置
            env = environment or os.getenv("ENVIRONMENT", "default")
            self.config = self.config_manager.load_config(env)

        # 设置日志
        self._setup_logging()

    def _load_config_from_file(self, config_path: str):
        """从文件加载配置"""
        try:
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                config_dict = yaml.safe_load(f)

            # 创建配置对象
            from src.core.config import SystemConfig
            return SystemConfig(**config_dict)

        except Exception as e:
            print(f"Failed to load config from {config_path}: {e}")
            print("Using default configuration")
            return self.config_manager.load_config("default")

    def _setup_logging(self):
        """设置日志"""
        log_config = self.config.logging
        log_level = log_config.get("level", "INFO")
        log_file = log_config.get("file")
        format_string = log_config.get("format")

        setup_logging(log_level, log_file, format_string)
        self.logger = get_logger("system_runner")

    async def start(self):
        """启动系统"""
        try:
            self.logger.info("Starting LangGraph Agent System...")
            self.logger.info(f"Environment: {self.config.system.get('name', 'Unknown')}")
            self.logger.info(f"Version: {self.config.system.get('version', '0.1.0')}")

            # 创建系统实例
            self.system = LangGraphAgentSystem()

            # 启动系统
            success = await self.system.start()
            if not success:
                self.logger.error("Failed to start system")
                return False

            self.running = True
            self.logger.info("System started successfully!")

            # 显示系统信息
            await self._show_system_info()

            return True

        except Exception as e:
            self.logger.error(f"Error starting system: {e}")
            return False

    async def stop(self):
        """停止系统"""
        try:
            if not self.running:
                return

            self.logger.info("Stopping LangGraph Agent System...")

            if self.system:
                await self.system.stop()

            self.running = False
            self.logger.info("System stopped successfully!")

        except Exception as e:
            self.logger.error(f"Error stopping system: {e}")

    async def run_interactive(self):
        """运行交互式模式"""
        if not await self.start():
            return

        try:
            self.logger.info("System is running. Type 'help' for commands, 'quit' to exit.")

            while self.running:
                try:
                    command = input("\n> ").strip().lower()

                    if command in ["quit", "exit", "q"]:
                        break
                    elif command == "help":
                        self._show_help()
                    elif command == "status":
                        await self._show_status()
                    elif command == "agents":
                        await self._show_agents()
                    elif command == "tasks":
                        await self._show_tasks()
                    elif command.startswith("submit"):
                        await self._submit_task_interactive(command)
                    elif command.startswith("metrics"):
                        await self._show_metrics()
                    else:
                        print("Unknown command. Type 'help' for available commands.")

                except EOFError:
                    break
                except KeyboardInterrupt:
                    break

        except Exception as e:
            self.logger.error(f"Interactive mode error: {e}")

        finally:
            await self.stop()

    async def run_daemon(self):
        """运行守护进程模式"""
        if not await self.start():
            return

        try:
            self.logger.info("System running in daemon mode. Press Ctrl+C to stop.")

            # 等待中断信号
            while self.running:
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        finally:
            await self.stop()

    async def _show_system_info(self):
        """显示系统信息"""
        try:
            status = await self.system.get_system_status()
            agents = await self.system.get_agents()

            print("\n" + "="*50)
            print("SYSTEM INFORMATION")
            print("="*50)
            print(f"Total Agents: {status.total_agents}")
            print(f"Active Agents: {status.active_agents}")
            print(f"Total Tasks: {status.total_tasks}")
            print(f"Running Tasks: {status.running_tasks}")
            print(f"Completed Tasks: {status.completed_tasks}")
            print(f"Failed Tasks: {status.failed_tasks}")
            print(f"System Load: {status.system_load:.1f}%")
            print(f"System Health: {'Healthy' if status.is_healthy else 'Unhealthy'}")
            print(f"Uptime: {status.uptime_seconds} seconds")
            print("="*50)

        except Exception as e:
            self.logger.error(f"Error showing system info: {e}")

    async def _show_status(self):
        """显示状态"""
        try:
            status = await self.system.get_system_status()
            print(f"\nSystem Status: {'Healthy' if status.is_healthy else 'Unhealthy'}")
            print(f"Load: {status.system_load:.1f}%")
            print(f"Tasks: {status.running_tasks} running, {status.completed_tasks} completed")
            print(f"Agents: {status.active_agents}/{status.total_agents} active")

        except Exception as e:
            self.logger.error(f"Error showing status: {e}")

    async def _show_agents(self):
        """显示智能体信息"""
        try:
            agents = await self.system.get_agents()
            if not agents:
                print("\nNo agents found.")
                return

            print(f"\n{len(agents)} Active Agents:")
            print("-" * 60)
            for agent in agents:
                print(f"ID: {agent.agent_id}")
                print(f"Name: {agent.name}")
                print(f"Type: {agent.agent_type}")
                print(f"Status: {agent.status}")
                print(f"Load: {agent.load_percentage:.1f}%")
                print(f"Tasks: {agent.current_tasks}")
                print("-" * 60)

        except Exception as e:
            self.logger.error(f"Error showing agents: {e}")

    async def _show_tasks(self):
        """显示任务信息"""
        try:
            tasks = await self.system.list_tasks(limit=10)
            if not tasks:
                print("\nNo tasks found.")
                return

            print(f"\nRecent Tasks (showing {len(tasks)}):")
            print("-" * 80)
            for task in tasks:
                print(f"ID: {task['task_id']}")
                print(f"Title: {task['title']}")
                print(f"Status: {task['status']}")
                print(f"Priority: {task['priority']}")
                print(f"Agent: {task.get('assigned_agent', 'Unassigned')}")
                print("-" * 80)

        except Exception as e:
            self.logger.error(f"Error showing tasks: {e}")

    async def _submit_task_interactive(self, command):
        """交互式提交任务"""
        try:
            print("\nSubmit New Task:")
            title = input("Title: ").strip()
            if not title:
                print("Title is required.")
                return

            description = input("Description: ").strip()
            if not description:
                print("Description is required.")
                return

            priority = input("Priority (low/medium/high/critical) [medium]: ").strip().lower()
            if not priority:
                priority = "medium"
            elif priority not in ["low", "medium", "high", "critical"]:
                print("Invalid priority. Using medium.")
                priority = "medium"

            from src.core.interface import TaskRequest
            request = TaskRequest(
                title=title,
                description=description,
                priority=priority
            )

            response = await self.system.submit_task(request)
            if response.success:
                print(f"✓ Task submitted successfully! Task ID: {response.task_id}")
            else:
                print(f"✗ Task submission failed: {response.message}")

        except Exception as e:
            self.logger.error(f"Error submitting task: {e}")

    async def _show_metrics(self):
        """显示指标"""
        try:
            metrics = await self.system.get_system_metrics()
            print("\nSystem Metrics:")
            print("-" * 40)
            print(f"Timestamp: {metrics.get('timestamp')}")

            if 'system' in metrics:
                sys_metrics = metrics['system']
                print(f"System Load: {sys_metrics.get('system_load', 0):.1f}%")
                print(f"Total Tasks: {sys_metrics.get('total_tasks', 0)}")
                print(f"Running Tasks: {sys_metrics.get('running_tasks', 0)}")

            if 'messages' in metrics:
                msg_metrics = metrics['messages']
                print(f"Messages Sent: {msg_metrics.get('messages_sent', 0)}")
                print(f"Messages Delivered: {msg_metrics.get('messages_delivered', 0)}")

            print("-" * 40)

        except Exception as e:
            self.logger.error(f"Error showing metrics: {e}")

    def _show_help(self):
        """显示帮助信息"""
        print("\nAvailable Commands:")
        print("  help     - Show this help message")
        print("  status   - Show system status")
        print("  agents   - List active agents")
        print("  tasks    - Show recent tasks")
        print("  submit   - Submit a new task")
        print("  metrics  - Show system metrics")
        print("  quit     - Exit the system")


def signal_handler(signum, frame):
    """信号处理器"""
    print(f"\nReceived signal {signum}. Shutting down...")
    sys.exit(0)


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="LangGraph Agent System")
    parser.add_argument("--config", "-c", help="Configuration file path")
    parser.add_argument("--env", "-e", help="Environment (default/development/production)")
    parser.add_argument("--mode", "-m", choices=["interactive", "daemon"], default="interactive",
                       help="Running mode (default: interactive)")
    parser.add_argument("--port", "-p", type=int, help="Override server port")

    args = parser.parse_args()

    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 创建系统运行器
    runner = SystemRunner(args.config, args.env)

    # 覆盖端口配置
    if args.port:
        runner.config.server["port"] = args.port

    # 运行系统
    try:
        if args.mode == "interactive":
            await runner.run_interactive()
        else:
            await runner.run_daemon()
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())