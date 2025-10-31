#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM API连接测试脚本
测试后端对SiliconFlow API的调用是否成功
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# 设置控制台编码
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from langgraph_multi_agent.llm.siliconflow_client import SiliconFlowClient, get_llm_client

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_siliconflow_api():
    """测试SiliconFlow API连接"""

    print("=" * 60)
    print("LLM API连接测试开始")
    print("=" * 60)

    try:
        # 1. 测试客户端初始化
        print("\n1. 测试客户端初始化...")
        client = SiliconFlowClient()
        print(f"[SUCCESS] 客户端初始化成功")
        print(f"   - API Base URL: {client.base_url}")
        print(f"   - 模型: {client.model}")
        print(f"   - 超时时间: {client.timeout}秒")

        # 2. 测试简单聊天
        print("\n2. 测试简单聊天请求...")
        test_prompt = "请用一句话介绍你自己"
        response = await client.simple_chat(test_prompt)
        print(f"[SUCCESS] 聊天请求成功")
        print(f"   - 提问: {test_prompt}")
        print(f"   - 回答: {response[:100]}..." if len(response) > 100 else f"   - 回答: {response}")

        # 3. 测试聊天完成API
        print("\n3. 测试聊天完成API...")
        messages = [
            {"role": "system", "content": "你是一个有帮助的助手"},
            {"role": "user", "content": "计算 2 + 2 等于多少？"}
        ]
        completion_response = await client.chat_completion(messages)
        print(f"[SUCCESS] 聊天完成API请求成功")
        if "choices" in completion_response and len(completion_response["choices"]) > 0:
            content = completion_response["choices"][0]["message"]["content"]
            print(f"   - 回答: {content}")

        # 4. 测试统计信息
        print("\n4. 查看使用统计...")
        stats = client.get_stats()
        print(f"[SUCCESS] 统计信息获取成功")
        print(f"   - 总请求数: {stats['total_requests']}")
        print(f"   - 成功请求数: {stats['successful_requests']}")
        print(f"   - 失败请求数: {stats['failed_requests']}")
        print(f"   - 成功率: {stats['success_rate']:.2%}")
        print(f"   - 总Token数: {stats['total_tokens']}")

        # 5. 测试批量请求
        print("\n5. 测试批量请求...")
        batch_prompts = [
            "什么是人工智能？",
            "Python是什么语言？",
            "简单介绍一下机器学习"
        ]
        batch_responses = await client.batch_chat(batch_prompts, max_concurrent=2)
        print(f"[SUCCESS] 批量请求成功，处理了 {len(batch_responses)} 个请求")
        for i, resp in enumerate(batch_responses):
            print(f"   - 问题{i+1}回答: {resp[:50]}..." if len(resp) > 50 else f"   - 问题{i+1}回答: {resp}")

        print("\n" + "=" * 60)
        print("[SUCCESS] 所有测试通过！LLM API连接正常")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        print(f"错误类型: {type(e).__name__}")

        # 提供详细的错误信息和建议
        if "Connection" in str(e) or "network" in str(e).lower():
            print("\n[TIPS] 可能的解决方案:")
            print("   1. 检查网络连接")
            print("   2. 确认API地址是否正确")
            print("   3. 检查防火墙设置")
        elif "authorization" in str(e).lower() or "401" in str(e):
            print("\n[TIPS] 可能的解决方案:")
            print("   1. 检查API密钥是否正确")
            print("   2. 确认API密钥是否有效")
            print("   3. 检查账户余额")
        elif "timeout" in str(e).lower():
            print("\n[TIPS] 可能的解决方案:")
            print("   1. 增加超时时间")
            print("   2. 检查网络延迟")
            print("   3. 减少请求大小")

        return False

async def test_global_client():
    """测试全局客户端实例"""
    print("\n6. 测试全局客户端实例...")
    try:
        client = get_llm_client()
        response = await client.simple_chat("测试全局客户端", system_message="简短回答")
        print(f"[SUCCESS] 全局客户端测试成功")
        print(f"   - 回答: {response}")
        return True
    except Exception as e:
        print(f"[ERROR] 全局客户端测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    print("开始LLM API连接测试...")

    # 运行主要测试
    main_test_success = await test_siliconflow_api()

    # 运行全局客户端测试
    global_test_success = await test_global_client()

    # 总结
    print("\n" + "=" * 60)
    print("测试总结:")
    print(f"  主要功能测试: {'[PASS]' if main_test_success else '[FAIL]'}")
    print(f"  全局客户端测试: {'[PASS]' if global_test_success else '[FAIL]'}")

    if main_test_success and global_test_success:
        print("\n[SUCCESS] 所有LLM API测试通过！后端可以成功调用LLM API。")
        return 0
    else:
        print("\n[WARNING] 部分测试失败，请检查配置和网络连接。")
        return 1

if __name__ == "__main__":
    # 运行测试
    exit_code = asyncio.run(main())
    sys.exit(exit_code)