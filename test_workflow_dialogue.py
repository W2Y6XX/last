#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统工作流动态对话测试脚本
对整个多智能体工作流系统进行动态对话测试，并输出详细的对话记录
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

# 导入必要的模块
from langgraph_multi_agent.workflow.multi_agent_workflow import (
    MultiAgentWorkflow,
    WorkflowExecutionMode,
    WorkflowStatus
)
from agents.meta.meta_agent import MetaAgent
from agents.coordinator.coordinator_agent import CoordinatorAgent
from agents.task_decomposer.task_decomposer_agent import TaskDecomposerAgent

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WorkflowDialogueRecorder:
    """工作流对话记录器"""

    def __init__(self):
        self.workflow_sessions = []
        self.current_session = datetime.now().strftime("%Y%m%d_%H%M%S")

    def start_workflow_session(self, workflow_id: str, session_name: str):
        """开始工作流会话"""
        session = {
            "workflow_id": workflow_id,
            "session_name": session_name,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "status": "running",
            "dialogues": [],
            "workflow_states": [],
            "agent_interactions": []
        }
        self.workflow_sessions.append(session)
        return len(self.workflow_sessions) - 1

    def record_workflow_state(self, session_index: int, state: Dict[str, Any]):
        """记录工作流状态"""
        if session_index < len(self.workflow_sessions):
            self.workflow_sessions[session_index]["workflow_states"].append({
                "timestamp": datetime.now().isoformat(),
                "state": state
            })

    def record_agent_interaction(self, session_index: int, agent_name: str,
                               interaction_type: str, content: str):
        """记录智能体交互"""
        if session_index < len(self.workflow_sessions):
            interaction = {
                "timestamp": datetime.now().isoformat(),
                "agent_name": agent_name,
                "interaction_type": interaction_type,  # "task_assigned", "task_completed", "coordination", etc.
                "content": content
            }
            self.workflow_sessions[session_index]["agent_interactions"].append(interaction)

    def record_dialogue(self, session_index: int, role: str, content: str):
        """记录对话"""
        if session_index < len(self.workflow_sessions):
            dialogue = {
                "timestamp": datetime.now().isoformat(),
                "role": role,  # "user" or "system" or "workflow"
                "content": content
            }
            self.workflow_sessions[session_index]["dialogues"].append(dialogue)

    def end_workflow_session(self, session_index: int, final_status: str):
        """结束工作流会话"""
        if session_index < len(self.workflow_sessions):
            self.workflow_sessions[session_index]["end_time"] = datetime.now().isoformat()
            self.workflow_sessions[session_index]["status"] = final_status

    def save_workflow_dialogue(self, filename: str = None):
        """保存工作流对话记录"""
        if filename is None:
            filename = f"workflow_dialogue_{self.current_session}.json"

        # 创建可序列化的副本
        serializable_sessions = []
        for session in self.workflow_sessions:
            serializable_session = session.copy()
            # 确保所有字段都可以序列化
            if "workflow_states" in serializable_session:
                for state in serializable_session["workflow_states"]:
                    if "state" in state and isinstance(state["state"], dict):
                        # 清理不可序列化的对象
                        state["state"] = self._make_json_serializable(state["state"])
            serializable_sessions.append(serializable_session)

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(serializable_sessions, f, ensure_ascii=False, indent=2)

        return filename

    def _make_json_serializable(self, obj):
        """将对象转换为JSON可序列化格式"""
        if isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif hasattr(obj, 'isoformat'):  # datetime对象
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return str(obj)  # 转换为字符串
        else:
            return obj

    def get_workflow_summary(self) -> Dict[str, Any]:
        """获取工作流摘要"""
        total_sessions = len(self.workflow_sessions)
        completed_sessions = sum(1 for s in self.workflow_sessions if s["status"] == "completed")
        failed_sessions = sum(1 for s in self.workflow_sessions if s["status"] == "failed")

        total_dialogues = sum(len(s["dialogues"]) for s in self.workflow_sessions)
        total_interactions = sum(len(s["agent_interactions"]) for s in self.workflow_sessions)

        return {
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "failed_sessions": failed_sessions,
            "success_rate": completed_sessions / total_sessions if total_sessions > 0 else 0,
            "total_dialogues": total_dialogues,
            "total_agent_interactions": total_interactions,
            "session_time": self.current_session
        }

class WorkflowTester:
    """工作流测试器"""

    def __init__(self):
        self.recorder = WorkflowDialogueRecorder()
        self.workflows = {}
        self.agents = {}
        self.test_results = {}

    async def setup_workflow_system(self):
        """设置工作流系统"""
        try:
            print("正在设置工作流系统...")

            # 1. 创建智能体实例
            meta_agent = MetaAgent("meta_agent_workflow")
            coordinator = CoordinatorAgent("coordinator_workflow")
            task_decomposer = TaskDecomposerAgent("task_decomposer_workflow")

            self.agents = {
                "meta_agent": meta_agent,
                "coordinator": coordinator,
                "task_decomposer": task_decomposer
            }

            # 2. 初始化智能体
            print("正在初始化智能体...")
            for agent_name, agent in self.agents.items():
                await agent.initialize()
                print(f"  [OK] {agent_name} 初始化成功")

            # 3. 创建工作流实例
            print("正在创建工作流引擎...")
            workflow = MultiAgentWorkflow(
                workflow_id="test_workflow_001",
                execution_mode=WorkflowExecutionMode.ADAPTIVE,
                max_iterations=50,
                timeout_seconds=1800  # 30分钟
            )

            # 4. 注册智能体到工作流
            print("正在注册智能体到工作流...")
            workflow.register_agent("meta_agent", meta_agent, "meta_agent")
            workflow.register_agent("coordinator", coordinator, "coordinator")
            workflow.register_agent("task_decomposer", task_decomposer, "task_decomposer")

            # 5. 编译工作流
            print("正在编译工作流...")
            workflow.compile_workflow()

            self.workflows["main"] = workflow

            print("[SUCCESS] 工作流系统设置完成")
            return True

        except Exception as e:
            print(f"[ERROR] 工作流系统设置失败: {e}")
            logger.exception("工作流设置异常")
            return False

    async def test_workflow_scenarios(self):
        """测试工作流场景"""
        print("\n" + "="*60)
        print("开始工作流场景测试")
        print("="*60)

        workflow_scenarios = [
            {
                "name": "项目管理协调场景",
                "description": "测试项目管理任务的智能体协调",
                "input": {
                    "title": "新产品发布项目管理",
                    "description": "协调多个智能体完成新产品发布的全流程管理",
                    "task_type": "multi_step_process",
                    "priority": 1,
                    "input_data": {
                        "project": "智能家居产品发布",
                        "phases": [
                            "市场调研",
                            "产品设计",
                            "开发实施",
                            "测试验证",
                            "市场推广"
                        ],
                        "requirements": [
                            "确保各阶段协调一致",
                            "优化资源配置",
                            "控制时间进度",
                            "保证产品质量"
                        ],
                        "constraints": {
                            "budget": "500万",
                            "timeline": "6个月",
                            "team_size": "15人"
                        }
                    },
                    "requester_id": "project_manager"
                }
            },
            {
                "name": "复杂问题分解场景",
                "description": "测试复杂问题的任务分解和协调执行",
                "input": {
                    "title": "电商平台性能优化",
                    "description": "通过多智能体协作完成电商平台全面性能优化",
                    "task_type": "problem_solving",
                    "priority": 2,
                    "input_data": {
                        "problem_domain": "电商平台",
                        "performance_issues": [
                            "响应时间过长",
                            "数据库查询缓慢",
                            "缓存命中率低",
                            "并发处理能力不足"
                        ],
                        "optimization_targets": [
                            "响应时间减少50%",
                            "数据库查询效率提升3倍",
                            "缓存命中率提升到95%",
                            "支持10000并发用户"
                        ],
                        "technical_stack": {
                            "frontend": "React",
                            "backend": "Spring Boot",
                            "database": "MySQL",
                            "cache": "Redis",
                            "message_queue": "RabbitMQ"
                        }
                    },
                    "requester_id": "system_architect"
                }
            },
            {
                "name": "数据分析工作流场景",
                "description": "测试复杂数据分析任务的智能体协作",
                "input": {
                    "title": "用户行为分析项目",
                    "description": "协调多个智能体完成大规模用户行为数据分析",
                    "task_type": "data_analysis",
                    "priority": 2,
                    "input_data": {
                        "dataset": {
                            "source": "电商平台用户行为日志",
                            "size": "10TB",
                            "time_range": "2024年全年",
                            "user_count": "100万+",
                            "event_types": [
                                "页面访问",
                                "商品浏览",
                                "加购物车",
                                "下单支付",
                                "用户评价"
                            ]
                        },
                        "analysis_goals": [
                            "用户画像构建",
                            "购买路径分析",
                            "用户留存分析",
                            "个性化推荐优化",
                            "流失用户预测"
                        ],
                        "deliverables": [
                            "用户画像报告",
                            "行为分析仪表板",
                            "推荐系统优化方案",
                            "流失预警模型"
                        ]
                    },
                    "requester_id": "data_analytics_team"
                }
            }
        ]

        all_success = True

        for i, scenario in enumerate(workflow_scenarios, 1):
            print(f"\n--- 场景 {i}: {scenario['name']} ---")
            print(f"描述: {scenario['description']}")

            session_index = self.recorder.start_workflow_session(
                f"scenario_{i}",
                scenario['name']
            )

            # 记录用户输入
            self.recorder.record_dialogue(
                session_index, "user",
                f"场景{i}: {scenario['description']}"
            )

            success = await self._execute_workflow_scenario(
                scenario, session_index, i
            )

            if success:
                print(f"   [SUCCESS] 场景 {i} 执行成功")
                self.recorder.end_workflow_session(session_index, "completed")
            else:
                print(f"   [FAIL] 场景 {i} 执行失败")
                self.recorder.end_workflow_session(session_index, "failed")
                all_success = False

            # 记录场景结果
            self.recorder.record_dialogue(
                session_index, "system",
                f"场景{i}执行状态: {'成功' if success else '失败'}"
            )

        return all_success

    async def _execute_workflow_scenario(self, scenario: Dict[str, Any],
                                       session_index: int, scenario_num: int):
        """执行工作流场景"""
        try:
            workflow = self.workflows["main"]

            print(f"   正在执行工作流场景 {scenario_num}...")
            start_time = datetime.now()

            # 执行工作流
            final_state = await workflow.execute(scenario["input"])

            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            print(f"   执行时间: {execution_time:.2f}秒")

            # 记录工作流状态
            self.recorder.record_workflow_state(session_index, {
                "execution_time": execution_time,
                "final_state": final_state,
                "workflow_info": workflow.get_workflow_info()
            })

            # 分析并记录智能体交互
            await self._analyze_agent_interactions(
                final_state, session_index, scenario_num
            )

            # 保存测试结果
            self.test_results[f"scenario_{scenario_num}"] = {
                "success": True,
                "execution_time": execution_time,
                "workflow_id": workflow.workflow_id,
                "final_status": workflow.status.value
            }

            return True

        except Exception as e:
            print(f"   [ERROR] 工作流执行异常: {e}")
            logger.exception(f"场景{scenario_num}执行异常")

            # 记录异常
            self.recorder.record_dialogue(
                session_index, "system",
                f"执行异常: {str(e)}"
            )

            self.test_results[f"scenario_{scenario_num}"] = {
                "success": False,
                "error": str(e),
                "execution_time": 0
            }

            return False

    async def _analyze_agent_interactions(self, final_state: Dict[str, Any],
                                        session_index: int, scenario_num: int):
        """分析智能体交互"""
        try:
            # 从最终状态中提取智能体交互信息
            workflow_context = final_state.get("workflow_context", {})
            agent_messages = final_state.get("agent_messages", [])
            task_results = final_state.get("task_results", {})

            # 记录工作流阶段转换
            current_phase = workflow_context.get("current_phase")
            self.recorder.record_agent_interaction(
                session_index, "workflow_system", "phase_transition",
                f"当前工作流阶段: {current_phase}"
            )

            # 记录各智能体的任务结果
            for agent_id, result in task_results.items():
                self.recorder.record_agent_interaction(
                    session_index, agent_id, "task_completion",
                    f"任务完成: {json.dumps(result, ensure_ascii=False)[:200]}..."
                )

            # 记录智能体消息
            for message in agent_messages:
                agent_name = message.get("agent_name", "unknown")
                content = message.get("content", "")
                self.recorder.record_agent_interaction(
                    session_index, agent_name, "communication",
                    content
                )

        except Exception as e:
            logger.error(f"分析智能体交互失败: {e}")

    async def cleanup(self):
        """清理资源"""
        print("\n正在清理工作流系统资源...")

        try:
            # 停止所有智能体
            for agent_name, agent in self.agents.items():
                await agent.stop()
                print(f"  [OK] 智能体 {agent_name} 已停止")

            # 清理工作流
            for workflow_name, workflow in self.workflows.items():
                print(f"  [OK] 工作流 {workflow_name} 已清理")

            print("资源清理完成")

        except Exception as e:
            print(f"  [ERROR] 资源清理失败: {e}")

async def main():
    """主测试函数"""
    print("系统工作流动态对话测试开始")
    print("="*60)

    tester = WorkflowTester()

    try:
        # 1. 设置工作流系统
        if not await tester.setup_workflow_system():
            print("[ERROR] 工作流系统设置失败，测试终止")
            return 1

        # 2. 执行工作流场景测试
        workflow_test_success = await tester.test_workflow_scenarios()

        # 3. 保存工作流对话记录
        dialogue_file = tester.recorder.save_workflow_dialogue()
        print(f"\n[INFO] 工作流对话记录已保存到: {dialogue_file}")

        # 4. 生成测试报告
        summary = tester.recorder.get_workflow_summary()
        print(f"\n[SUMMARY] 工作流测试统计:")
        print(f"  总场景数: {summary['total_sessions']}")
        print(f"  成功场景数: {summary['completed_sessions']}")
        print(f"  失败场景数: {summary['failed_sessions']}")
        print(f"  成功率: {summary['success_rate']:.2%}")
        print(f"  总对话数: {summary['total_dialogues']}")
        print(f"  总智能体交互数: {summary['total_agent_interactions']}")

        # 5. 输出详细测试结果
        print(f"\n[SUMMARY] 详细测试结果:")
        for scenario_name, result in tester.test_results.items():
            status = "成功" if result["success"] else "失败"
            exec_time = result.get("execution_time", 0)
            print(f"  {scenario_name}: {status}, 执行时间: {exec_time:.2f}s")

        # 6. 保存详细测试结果
        results_file = f"workflow_test_results_{tester.recorder.current_session}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                "workflow_summary": summary,
                "test_results": tester.test_results,
                "workflow_sessions": tester.recorder.workflow_sessions
            }, f, ensure_ascii=False, indent=2)
        print(f"[INFO] 详细工作流测试结果已保存到: {results_file}")

        # 7. 最终结果判定
        if workflow_test_success:
            print("\n[SUCCESS] 所有工作流场景测试通过！")
            return 0
        else:
            print("\n[WARNING] 部分工作流场景测试失败，请检查日志和结果文件")
            return 1

    except Exception as e:
        print(f"\n[ERROR] 工作流测试过程中发生异常: {e}")
        logger.exception("工作流测试异常")
        return 1

    finally:
        # 清理资源
        await tester.cleanup()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)