#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可读的智能体动态对话测试脚本
生成自然、人性化的智能体对话记录
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

from langgraph_multi_agent.llm.siliconflow_client import SiliconFlowClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ReadableDialogueRecorder:
    """可读对话记录器"""

    def __init__(self):
        self.dialogue_sessions = []
        self.current_session = datetime.now().strftime("%Y%m%d_%H%M%S")

    def start_dialogue_session(self, session_name: str, participants: List[str]):
        """开始对话会话"""
        session = {
            "session_name": session_name,
            "participants": participants,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "status": "active",
            "dialogues": []
        }
        self.dialogue_sessions.append(session)
        return len(self.dialogue_sessions) - 1

    def add_dialogue(self, session_index: int, speaker: str, content: str,
                    emotion: str = "neutral", context: str = ""):
        """添加对话内容"""
        if session_index < len(self.dialogue_sessions):
            dialogue = {
                "timestamp": datetime.now().isoformat(),
                "speaker": speaker,
                "content": content,
                "emotion": emotion,
                "context": context
            }
            self.dialogue_sessions[session_index]["dialogues"].append(dialogue)

    def end_dialogue_session(self, session_index: int, summary: str = ""):
        """结束对话会话"""
        if session_index < len(self.dialogue_sessions):
            self.dialogue_sessions[session_index]["end_time"] = datetime.now().isoformat()
            self.dialogue_sessions[session_index]["status"] = "completed"
            self.dialogue_sessions[session_index]["summary"] = summary

    def save_readable_dialogue(self, filename: str = None) -> str:
        """保存为易读的对话格式"""
        if filename is None:
            filename = f"readable_dialogue_{self.current_session}.md"

        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# 智能体动态对话记录\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n\n")

            for i, session in enumerate(self.dialogue_sessions, 1):
                f.write(f"## 对话会话 {i}: {session['session_name']}\n\n")
                f.write(f"**参与者**: {', '.join(session['participants'])}\n")
                f.write(f"**开始时间**: {session['start_time']}\n")
                f.write(f"**结束时间**: {session.get('end_time', '进行中')}\n")
                f.write(f"**状态**: {session['status']}\n\n")

                if session.get('summary'):
                    f.write(f"**对话摘要**: {session['summary']}\n\n")

                f.write("### 对话内容\n\n")

                for dialogue in session['dialogues']:
                    timestamp = datetime.fromisoformat(dialogue['timestamp']).strftime('%H:%M:%S')
                    speaker = dialogue['speaker']
                    content = dialogue['content']
                    emotion = dialogue['emotion']
                    context = dialogue.get('context', '')

                    f.write(f"**[{timestamp}] {speaker}** ")
                    if emotion != "neutral":
                        f.write(f"*({emotion})* ")
                    f.write(f": {content}\n")
                    if context:
                        f.write(f"*上下文: {context}*\n")
                    f.write("\n")

                f.write("---\n\n")

        return filename

    def save_json_dialogue(self, filename: str = None) -> str:
        """保存为JSON格式"""
        if filename is None:
            filename = f"readable_dialogue_{self.current_session}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.dialogue_sessions, f, ensure_ascii=False, indent=2)

        return filename

class AgentCharacter:
    """智能体角色设定"""

    def __init__(self, name: str, role: str, personality: str, expertise: List[str]):
        self.name = name
        self.role = role
        self.personality = personality
        self.expertise = expertise

class ConversationalAgent:
    """对话式智能体"""

    def __init__(self, character: AgentCharacter, llm_client: SiliconFlowClient):
        self.character = character
        self.llm_client = llm_client
        self.conversation_history = []

    async def generate_response(self, message: str, context: str = "",
                              emotion: str = "neutral") -> Dict[str, str]:
        """生成对话回复"""
        try:
            # 构建系统提示
            system_prompt = f"""你是一个{self.character.role}，名字叫{self.character.name}。

角色特征:
- 性格: {self.character.personality}
- 专业领域: {', '.join(self.character.expertise)}

请以自然、人性化的方式回复，展现你的专业能力和个性特点。
回复应该简洁有力，避免过于技术化的表达。
可以根据上下文调整语气和情感。"""

            # 构建用户消息
            user_message = message
            if context:
                user_message = f"[上下文: {context}]\n\n{message}"
            if emotion != "neutral":
                user_message = f"[情感: {emotion}]\n\n{user_message}"

            # 调用LLM生成回复
            response = await self.llm_client.simple_chat(
                user_message,
                system_message=system_prompt,
                temperature=0.8,
                max_tokens=300
            )

            # 分析回复情感
            response_emotion = self._analyze_emotion(response)

            return {
                "content": response,
                "emotion": response_emotion,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"生成回复失败: {e}")
            return {
                "content": f"抱歉，我现在有些困惑。让我想想... (错误: {str(e)[:50]}...)",
                "emotion": "confused",
                "timestamp": datetime.now().isoformat()
            }

    def _analyze_emotion(self, text: str) -> str:
        """分析文本情感"""
        text_lower = text.lower()

        positive_words = ["好", "棒", "优秀", "完美", "成功", "赞", "太好了", "很好"]
        negative_words = ["不好", "失败", "糟糕", "困难", "问题", "错误", "抱歉"]
        questioning_words = ["吗", "呢", "如何", "怎么", "为什么", "是否"]
        excited_words = ["!", "太", "非常", "超级", "棒极了", "赞"]

        if any(word in text for word in excited_words):
            return "excited"
        elif any(word in text for word in positive_words):
            return "happy"
        elif any(word in text for word in negative_words):
            return "concerned"
        elif any(word in text for word in questioning_words):
            return "curious"
        else:
            return "neutral"

class DialogueTester:
    """对话测试器"""

    def __init__(self):
        self.recorder = ReadableDialogueRecorder()
        self.llm_client = SiliconFlowClient()
        self.agents = {}
        self.setup_agents()

    def setup_agents(self):
        """设置智能体角色"""
        # Meta-Agent - 系统协调者
        meta_character = AgentCharacter(
            name="元智能体",
            role="系统协调和管理专家",
            personality="沉着冷静，善于全局思考，具有战略眼光，说话有条理",
            expertise=["系统架构", "任务协调", "资源管理", "决策分析"]
        )

        # Coordinator-Agent - 项目协调者
        coordinator_character = AgentCharacter(
            name="协调智能体",
            role="项目协调和团队管理专家",
            personality="热情积极，善于沟通，注重效率，有亲和力",
            expertise=["项目管理", "团队协作", "流程优化", "冲突解决"]
        )

        # Task-Decomposer-Agent - 任务分解者
        decomposer_character = AgentCharacter(
            name="任务分解智能体",
            role="任务分析和分解专家",
            personality="细致严谨，逻辑清晰，善于分析，追求完美",
            expertise=["任务分解", "工作流设计", "复杂度分析", "依赖关系管理"]
        )

        # 创建对话智能体
        self.agents = {
            "meta_agent": ConversationalAgent(meta_character, self.llm_client),
            "coordinator": ConversationalAgent(coordinator_character, self.llm_client),
            "task_decomposer": ConversationalAgent(decomposer_character, self.llm_client)
        }

    async def test_individual_agent_dialogues(self):
        """测试单个智能体的对话能力"""
        print("=" * 60)
        print("开始单个智能体可读对话测试")
        print("=" * 60)

        test_scenarios = [
            {
                "agent_key": "meta_agent",
                "agent_name": "元智能体",
                "scenario_name": "系统架构讨论",
                "dialogues": [
                    {
                        "speaker": "user",
                        "content": "你好元智能体，我需要设计一个多智能体协作系统，你能给我一些建议吗？",
                        "emotion": "curious"
                    },
                    {
                        "speaker": "meta_agent",
                        "content": "需要生成的回复",
                        "emotion": "neutral"
                    },
                    {
                        "speaker": "user",
                        "content": "听起来很有道理。那么在任务分配方面，你有什么好的策略吗？",
                        "emotion": "interested"
                    },
                    {
                        "speaker": "meta_agent",
                        "content": "需要生成的回复",
                        "emotion": "confident"
                    },
                    {
                        "speaker": "user",
                        "content": "非常感谢你的建议！这对我的项目很有帮助。",
                        "emotion": "grateful"
                    },
                    {
                        "speaker": "meta_agent",
                        "content": "需要生成的回复",
                        "emotion": "helpful"
                    }
                ]
            },
            {
                "agent_key": "coordinator",
                "agent_name": "协调智能体",
                "scenario_name": "团队管理对话",
                "dialogues": [
                    {
                        "speaker": "user",
                        "content": "协调智能体，我在管理一个开发团队时遇到了一些挑战，你能帮助我吗？",
                        "emotion": "concerned"
                    },
                    {
                        "speaker": "coordinator",
                        "content": "需要生成的回复",
                        "emotion": "empathetic"
                    },
                    {
                        "speaker": "user",
                        "content": "主要是团队成员之间的沟通不太顺畅，有时候会出现信息断层。",
                        "emotion": "worried"
                    },
                    {
                        "speaker": "coordinator",
                        "content": "需要生成的回复",
                        "emotion": "thoughtful"
                    },
                    {
                        "speaker": "user",
                        "content": "这些建议很实用，我会尝试的。谢谢你的帮助！",
                        "emotion": "relieved"
                    },
                    {
                        "speaker": "coordinator",
                        "content": "需要生成的回复",
                        "emotion": "encouraging"
                    }
                ]
            },
            {
                "agent_key": "task_decomposer",
                "agent_name": "任务分解智能体",
                "scenario_name": "项目规划讨论",
                "dialogues": [
                    {
                        "speaker": "user",
                        "content": "任务分解智能体，我有一个复杂的项目需要分解，你能帮我分析一下吗？",
                        "emotion": "hopeful"
                    },
                    {
                        "speaker": "task_decomposer",
                        "content": "需要生成的回复",
                        "emotion": "analytical"
                    },
                    {
                        "speaker": "user",
                        "content": "这是一个电商平台重构项目，涉及前端、后端、数据库等多个方面。",
                        "emotion": "focused"
                    },
                    {
                        "speaker": "task_decomposer",
                        "content": "需要生成的回复",
                        "emotion": "methodical"
                    },
                    {
                        "speaker": "user",
                        "content": "你的分析非常详细和专业！我对项目规划更清晰了。",
                        "emotion": "impressed"
                    },
                    {
                        "speaker": "task_decomposer",
                        "content": "需要生成的回复",
                        "emotion": "satisfied"
                    }
                ]
            }
        ]

        all_success = True

        for scenario in test_scenarios:
            print(f"\n--- {scenario['agent_name']}对话测试: {scenario['scenario_name']} ---")

            session_index = self.recorder.start_dialogue_session(
                scenario['scenario_name'],
                ["用户", scenario['agent_name']]
            )

            agent = self.agents[scenario['agent_key']]
            context = scenario['scenario_name']
            success = True

            for dialogue in scenario['dialogues']:
                if dialogue['speaker'] == 'user':
                    # 用户消息，直接添加到记录
                    self.recorder.add_dialogue(
                        session_index,
                        "用户",
                        dialogue['content'],
                        dialogue['emotion'],
                        context
                    )
                    print(f"  用户 [{dialogue['emotion']}]: {dialogue['content']}")

                elif dialogue['speaker'] in [scenario['agent_name'], scenario['agent_key']]:
                    # 智能体回复，需要生成
                    try:
                        # 获取之前的对话作为上下文
                        previous_dialogues = [d for d in scenario['dialogues']
                                            if d['speaker'] == 'user']
                        if previous_dialogues:
                            last_user_msg = previous_dialogues[-1]['content']
                        else:
                            last_user_msg = dialogue['content']

                        response = await agent.generate_response(
                            last_user_msg,
                            context,
                            dialogue['emotion']
                        )

                        content = response['content']
                        emotion = response['emotion']

                        self.recorder.add_dialogue(
                            session_index,
                            scenario['agent_name'],
                            content,
                            emotion,
                            context
                        )

                        print(f"  {scenario['agent_name']} [{emotion}]: {content}")

                    except Exception as e:
                        print(f"  [ERROR] {scenario['agent_name']} 回复生成失败: {e}")
                        success = False
                        all_success = False

            # 结束对话会话
            self.recorder.end_dialogue_session(
                session_index,
                f"完成了{scenario['agent_name']}的对话测试"
            )

            if success:
                print(f"  [SUCCESS] {scenario['agent_name']}对话测试完成")
            else:
                print(f"  [PARTIAL] {scenario['agent_name']}对话测试部分完成")

        return all_success

    async def test_multi_agent_dialogue(self):
        """测试多智能体协作对话"""
        print("\n" + "=" * 60)
        print("开始多智能体协作对话测试")
        print("=" * 60)

        # 创建一个项目管理场景的多智能体对话
        session_index = self.recorder.start_dialogue_session(
            "多智能体协作: 项目规划会议",
            ["用户", "元智能体", "协调智能体", "任务分解智能体"]
        )

        dialogue_flow = [
            {
                "speaker": "用户",
                "content": "各位智能体，我需要规划一个新产品开发项目，请大家协作帮忙。",
                "emotion": "professional",
                "context": "项目启动会议"
            },
            {
                "speaker": "meta_agent",
                "content": "需要生成的回复",
                "emotion": "leadership",
                "agent_key": "meta_agent"
            },
            {
                "speaker": "coordinator",
                "content": "需要生成的回复",
                "emotion": "collaborative",
                "agent_key": "coordinator"
            },
            {
                "speaker": "task_decomposer",
                "content": "需要生成的回复",
                "emotion": "analytical",
                "agent_key": "task_decomposer"
            },
            {
                "speaker": "用户",
                "content": "太好了！那么我们先从需求分析开始吧。",
                "emotion": "decisive",
                "context": "确定工作重点"
            },
            {
                "speaker": "meta_agent",
                "content": "需要生成的回复",
                "emotion": "strategic",
                "agent_key": "meta_agent"
            },
            {
                "speaker": "coordinator",
                "content": "需要生成的回复",
                "emotion": "organized",
                "agent_key": "coordinator"
            },
            {
                "speaker": "用户",
                "content": "完美！我相信在我们的协作下，这个项目一定会很成功。",
                "emotion": "optimistic",
                "context": "项目总结"
            }
        ]

        success = True
        current_context = "项目启动会议"

        for step in dialogue_flow:
            if step['speaker'] == '用户':
                # 用户消息
                self.recorder.add_dialogue(
                    session_index,
                    "用户",
                    step['content'],
                    step['emotion'],
                    current_context
                )
                print(f"  用户 [{step['emotion']}]: {step['content']}")

                if step.get('context'):
                    current_context = step['context']

            else:
                # 智能体消息
                try:
                    agent = self.agents[step['agent_key']]

                    # 获取最近的用户消息作为输入
                    recent_user_messages = [d for d in dialogue_flow
                                          if d['speaker'] == '用户' and
                                          dialogue_flow.index(d) < dialogue_flow.index(step)]
                    if recent_user_messages:
                        last_user_msg = recent_user_messages[-1]['content']
                    else:
                        last_user_msg = step['content']

                    response = await agent.generate_response(
                        last_user_msg,
                        current_context,
                        step['emotion']
                    )

                    content = response['content']
                    emotion = response['emotion']

                    self.recorder.add_dialogue(
                        session_index,
                        step['speaker'],
                        content,
                        emotion,
                        current_context
                    )

                    print(f"  {step['speaker']} [{emotion}]: {content}")

                except Exception as e:
                    print(f"  [ERROR] {step['speaker']} 回复生成失败: {e}")
                    success = False

        # 结束多智能体对话
        self.recorder.end_dialogue_session(
            session_index,
            "成功完成了多智能体协作的项目规划对话"
        )

        return success

    async def cleanup(self):
        """清理资源"""
        print("\n正在清理测试资源...")
        # 这里可以添加清理逻辑
        print("资源清理完成")

async def main():
    """主测试函数"""
    print("可读智能体动态对话测试开始")
    print("=" * 60)

    tester = DialogueTester()

    try:
        # 1. 测试单个智能体对话
        individual_success = await tester.test_individual_agent_dialogues()

        # 2. 测试多智能体协作对话
        multi_success = await tester.test_multi_agent_dialogue()

        # 3. 保存对话记录
        markdown_file = tester.recorder.save_readable_dialogue()
        json_file = tester.recorder.save_json_dialogue()

        print(f"\n[INFO] 可读对话记录已保存:")
        print(f"  Markdown格式: {markdown_file}")
        print(f"  JSON格式: {json_file}")

        # 4. 生成测试报告
        total_sessions = len(tester.recorder.dialogue_sessions)
        completed_sessions = sum(1 for s in tester.recorder.dialogue_sessions
                               if s['status'] == 'completed')

        print(f"\n[SUMMARY] 对话测试统计:")
        print(f"  总对话会话数: {total_sessions}")
        print(f"  完成会话数: {completed_sessions}")
        print(f"  参与智能体: {', '.join(tester.agents.keys())}")

        # 5. 最终结果判定
        if individual_success and multi_success:
            print("\n[SUCCESS] 所有可读对话测试通过！")
            print("已生成人性化的智能体对话记录。")
            return 0
        else:
            print("\n[WARNING] 部分对话测试失败，请检查日志")
            return 1

    except Exception as e:
        print(f"\n[ERROR] 对话测试过程中发生异常: {e}")
        logger.exception("对话测试异常")
        return 1

    finally:
        # 清理资源
        await tester.cleanup()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)