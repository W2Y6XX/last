#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能体动态对话测试脚本
对所有智能体进行动态对话测试，并输出详细的对话记录
"""

import asyncio
import sys
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import json

# 设置控制台编码
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agents.base.base_agent import BaseAgent, MessageType, Message, Config, MessageBus
from agents.meta.meta_agent import MetaAgent
from agents.coordinator.coordinator_agent import CoordinatorAgent
from agents.task_decomposer.task_decomposer_agent import TaskDecomposerAgent

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DialogueRecorder:
    """对话记录器"""

    def __init__(self):
        self.dialogues = []
        self.current_session = datetime.now().strftime("%Y%m%d_%H%M%S")

    def record_dialogue(self, agent_name: str, role: str, content: str, timestamp: datetime = None):
        """记录对话"""
        if timestamp is None:
            timestamp = datetime.now()

        dialogue_entry = {
            "timestamp": timestamp.isoformat(),
            "agent_name": agent_name,
            "role": role,  # "user" or "assistant"
            "content": content
        }
        self.dialogues.append(dialogue_entry)

    def save_dialogue(self, filename: str = None):
        """保存对话记录"""
        if filename is None:
            filename = f"agent_dialogue_{self.current_session}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.dialogues, f, ensure_ascii=False, indent=2)

        return filename

    def get_dialogue_summary(self) -> Dict[str, Any]:
        """获取对话摘要"""
        agent_counts = {}
        for dialogue in self.dialogues:
            agent = dialogue["agent_name"]
            agent_counts[agent] = agent_counts.get(agent, 0) + 1

        return {
            "total_dialogues": len(self.dialogues),
            "agent_participation": agent_counts,
            "session_time": self.current_session,
            "duration_minutes": (datetime.now() - datetime.strptime(self.current_session, "%Y%m%d_%H%M%S")).total_seconds() / 60
        }

class SimpleMessageBus(MessageBus):
    """简单的消息总线实现"""

    def __init__(self):
        super().__init__()
        self.message_history = []
        self.handlers = {}

    async def send_message(self, recipient_id: str, message: Message):
        """发送消息"""
        self.message_history.append({
            "type": "send",
            "recipient_id": recipient_id,
            "message": message,
            "timestamp": datetime.now()
        })

        # 如果有对应的处理器，直接调用
        if recipient_id in self.handlers:
            handler = self.handlers[recipient_id]
            await handler(message)

    async def broadcast(self, message: Message):
        """广播消息"""
        self.message_history.append({
            "type": "broadcast",
            "message": message,
            "timestamp": datetime.now()
        })

        # 发送给所有注册的处理器
        for handler in self.handlers.values():
            await handler(message)

    async def register_handler(self, message_type: MessageType, handler: callable):
        """注册消息处理器"""
        if message_type not in self.handlers:
            self.handlers[message_type] = []
        self.handlers[message_type].append(handler)

class DialogueTester:
    """对话测试器"""

    def __init__(self):
        self.message_bus = SimpleMessageBus()
        self.agents = {}
        self.recorder = DialogueRecorder()
        self.test_results = {}

    async def setup_agents(self):
        """设置所有智能体"""
        try:
            # 创建消息总线
            self.message_bus = SimpleMessageBus()

            # 创建并初始化各智能体
            print("正在初始化智能体...")

            # Meta-Agent
            meta_agent = MetaAgent("meta_agent_1")
            await self._initialize_agent(meta_agent, "Meta-Agent")

            # Coordinator Agent
            coordinator_agent = CoordinatorAgent("coordinator_1")
            await self._initialize_agent(coordinator_agent, "Coordinator-Agent")

            # Task Decomposer Agent
            task_decomposer = TaskDecomposerAgent("task_decomposer_1")
            await self._initialize_agent(task_decomposer, "Task-Decomposer-Agent")

            self.agents = {
                "meta_agent": meta_agent,
                "coordinator": coordinator_agent,
                "task_decomposer": task_decomposer
            }

            # 设置智能体间的通信
            await self._setup_agent_communication()

            print("[SUCCESS] 所有智能体初始化完成")
            return True

        except Exception as e:
            print(f"[ERROR] 智能体初始化失败: {e}")
            return False

    async def _initialize_agent(self, agent: BaseAgent, display_name: str):
        """初始化单个智能体"""
        try:
            # 设置消息总线
            agent.message_bus = self.message_bus

            # 初始化智能体
            success = await agent.initialize()
            if success:
                print(f"  [OK] {display_name} 初始化成功")
            else:
                print(f"  [FAIL] {display_name} 初始化失败")

        except Exception as e:
            print(f"  [ERROR] {display_name} 初始化异常: {e}")
            raise

    async def _setup_agent_communication(self):
        """设置智能体间通信"""
        # 这里可以设置智能体间的消息路由
        # 简化起见，我们暂时让所有智能体都能接收到所有消息
        pass

    async def test_individual_agents(self):
        """测试各个智能体的对话能力"""
        print("\n" + "="*60)
        print("开始单个智能体对话测试")
        print("="*60)

        test_tasks = [
            {
                "agent_name": "meta_agent",
                "agent_type": "Meta-Agent",
                "tasks": [
                    {
                        "task_type": "analysis",
                        "description": "分析一个复杂的项目管理任务",
                        "input_data": {
                            "project": "开发一个多智能体协作系统",
                            "requirements": ["系统稳定性", "高效通信", "任务分配"],
                            "timeline": "3个月",
                            "team_size": 5
                        },
                        "question": "请分析这个项目的复杂性和实施策略"
                    },
                    {
                        "task_type": "coordination",
                        "description": "协调多个智能体的工作",
                        "input_data": {
                            "agents": ["数据分析智能体", "决策智能体", "执行智能体"],
                            "task": "协同完成市场分析报告"
                        },
                        "question": "如何设计协调机制以确保智能体间高效协作？"
                    }
                ]
            },
            {
                "agent_name": "coordinator",
                "agent_type": "Coordinator-Agent",
                "tasks": [
                    {
                        "task_type": "multi_step_process",
                        "description": "协调多步骤项目执行",
                        "input_data": {
                            "steps": [
                                {"description": "需求分析", "data": {"priority": "high"}},
                                {"description": "方案设计", "data": {"complexity": "medium"}},
                                {"description": "开发实施", "data": {"duration": "2weeks"}}
                            ]
                        },
                        "question": "请协调这个多步骤项目的执行流程"
                    },
                    {
                        "task_type": "conflict_resolution",
                        "description": "解决资源冲突",
                        "input_data": {
                            "conflicts": [
                                {"resource": "计算资源", "demanders": ["Task1", "Task2"]},
                                {"resource": "时间窗口", "demanders": ["Task2", "Task3"]}
                            ]
                        },
                        "question": "如何解决这些资源冲突问题？"
                    }
                ]
            },
            {
                "agent_name": "task_decomposer",
                "agent_type": "Task-Decomposer-Agent",
                "tasks": [
                    {
                        "task_type": "problem_solving",
                        "description": "分解复杂问题解决任务",
                        "input_data": {
                            "problem": "优化电商平台性能",
                            "aspects": ["数据库优化", "缓存策略", "负载均衡", "CDN优化"]
                        },
                        "question": "请将这个性能优化任务分解为可执行的子任务"
                    },
                    {
                        "task_type": "data_analysis",
                        "description": "分解数据分析工作",
                        "input_data": {
                            "dataset": "用户行为数据",
                            "analysis_goals": ["用户画像", "行为模式", "转化优化"],
                            "data_size": "100GB"
                        },
                        "question": "如何分解这个大型数据分析任务？"
                    }
                ]
            }
        ]

        all_success = True

        for agent_test in test_tasks:
            agent_name = agent_test["agent_name"]
            agent_type = agent_test["agent_type"]
            tasks = agent_test["tasks"]

            print(f"\n--- 测试 {agent_type} ---")

            if agent_name not in self.agents:
                print(f"[ERROR] 智能体 {agent_name} 未找到")
                all_success = False
                continue

            agent = self.agents[agent_name]
            agent_success = True

            for i, task in enumerate(tasks, 1):
                print(f"\n{i}. 测试任务: {task['description']}")
                print(f"   问题: {task['question']}")

                try:
                    # 记录用户问题
                    self.recorder.record_dialogue(
                        agent_type, "user",
                        f"任务{i}: {task['question']}"
                    )

                    # 构建任务数据
                    task_data = {
                        "task_id": f"test_{agent_name}_{i}",
                        "task_type": task["task_type"],
                        "description": task["description"],
                        "input_data": task["input_data"],
                        "requirements": [task["question"]],
                        "priority": 2
                    }

                    # 发送任务给智能体
                    start_time = datetime.now()
                    result = await agent.process_task(task_data)
                    end_time = datetime.now()

                    processing_time = (end_time - start_time).total_seconds()

                    if result.get("success", False):
                        print(f"   [SUCCESS] 任务处理成功")
                        print(f"   处理时间: {processing_time:.2f}秒")

                        # 提取并记录智能体回复
                        response_content = self._extract_response_content(result, task)
                        print(f"   回复: {response_content[:100]}..." if len(response_content) > 100 else f"   回复: {response_content}")

                        # 记录智能体回复
                        self.recorder.record_dialogue(
                            agent_type, "assistant",
                            response_content, end_time
                        )

                        # 保存测试结果
                        if agent_name not in self.test_results:
                            self.test_results[agent_name] = []
                        self.test_results[agent_name].append({
                            "task_index": i,
                            "success": True,
                            "processing_time": processing_time,
                            "response_length": len(response_content),
                            "task_type": task["task_type"]
                        })

                    else:
                        print(f"   [FAIL] 任务处理失败: {result.get('error', 'Unknown error')}")
                        agent_success = False

                        # 记录错误回复
                        error_response = f"处理失败: {result.get('error', 'Unknown error')}"
                        self.recorder.record_dialogue(
                            agent_type, "assistant",
                            error_response, end_time
                        )

                except Exception as e:
                    print(f"   [ERROR] 测试异常: {e}")
                    agent_success = False

                    # 记录异常
                    error_response = f"测试异常: {str(e)}"
                    self.recorder.record_dialogue(
                        agent_type, "assistant",
                        error_response, datetime.now()
                    )

            if agent_success:
                print(f"   [SUMMARY] {agent_type} 所有测试通过")
            else:
                print(f"   [SUMMARY] {agent_type} 部分测试失败")
                all_success = False

        return all_success

    def _extract_response_content(self, result: Dict[str, Any], task: Dict[str, Any]) -> str:
        """提取智能体回复内容"""
        try:
            # 尝试从不同字段提取回复内容
            content_fields = [
                "result", "response", "answer", "output",
                "analysis", "strategy", "plan", "recommendation"
            ]

            for field in content_fields:
                if field in result and result[field]:
                    if isinstance(result[field], str):
                        return result[field]
                    elif isinstance(result[field], dict):
                        # 尝试从字典中提取文本内容
                        text_content = json.dumps(result[field], ensure_ascii=False, indent=2)
                        return text_content
                    elif isinstance(result[field], list):
                        # 处理列表类型的回复
                        return "; ".join(str(item) for item in result[field])

            # 如果没有找到标准字段，尝试从子任务结果中提取
            if "subtasks" in result:
                subtask_summary = []
                for subtask in result["subtasks"]:
                    if isinstance(subtask, dict) and "description" in subtask:
                        subtask_summary.append(subtask["description"])
                if subtask_summary:
                    return "子任务: " + "; ".join(subtask_summary)

            # 如果还是没有找到，返回整个结果的字符串表示
            return json.dumps(result, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"提取回复内容失败: {e}")
            return f"无法提取回复内容: {str(e)}"

    async def cleanup(self):
        """清理资源"""
        print("\n正在清理资源...")

        for agent_name, agent in self.agents.items():
            try:
                await agent.stop()
                print(f"  [OK] {agent_name} 已停止")
            except Exception as e:
                print(f"  [ERROR] 停止 {agent_name} 失败: {e}")

        print("资源清理完成")

async def main():
    """主测试函数"""
    print("智能体动态对话测试开始")
    print("="*60)

    tester = DialogueTester()

    try:
        # 1. 设置智能体
        if not await tester.setup_agents():
            print("[ERROR] 智能体设置失败，测试终止")
            return 1

        # 2. 执行单个智能体测试
        individual_test_success = await tester.test_individual_agents()

        # 3. 保存对话记录
        dialogue_file = tester.recorder.save_dialogue()
        print(f"\n[INFO] 对话记录已保存到: {dialogue_file}")

        # 4. 生成测试报告
        summary = tester.recorder.get_dialogue_summary()
        print(f"\n[SUMMARY] 对话统计:")
        print(f"  总对话数: {summary['total_dialogues']}")
        print(f"  会话时长: {summary['duration_minutes']:.2f} 分钟")
        print(f"  智能体参与情况:")
        for agent, count in summary['agent_participation'].items():
            print(f"    {agent}: {count} 次对话")

        # 5. 输出测试结果摘要
        print(f"\n[SUMMARY] 测试结果:")
        for agent_name, results in tester.test_results.items():
            success_count = sum(1 for r in results if r["success"])
            total_count = len(results)
            avg_time = sum(r["processing_time"] for r in results) / total_count if total_count > 0 else 0
            print(f"  {agent_name}: {success_count}/{total_count} 成功, 平均处理时间: {avg_time:.2f}s")

        # 6. 保存详细测试结果
        results_file = f"agent_test_results_{tester.recorder.current_session}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                "dialogue_summary": summary,
                "test_results": tester.test_results,
                "dialogues": tester.recorder.dialogues
            }, f, ensure_ascii=False, indent=2)
        print(f"[INFO] 详细测试结果已保存到: {results_file}")

        # 7. 最终结果判定
        if individual_test_success:
            print("\n[SUCCESS] 所有单个智能体对话测试通过！")
            return 0
        else:
            print("\n[WARNING] 部分智能体测试失败，请检查日志和结果文件")
            return 1

    except Exception as e:
        print(f"\n[ERROR] 测试过程中发生异常: {e}")
        logger.exception("测试异常")
        return 1

    finally:
        # 清理资源
        await tester.cleanup()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)