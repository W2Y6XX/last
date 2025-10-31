#!/usr/bin/env python3
"""
基础工作流示例

这个示例展示了如何使用LangGraph多智能体系统创建和执行一个基本的工作流。
包括：
- 系统初始化
- 创建简单工作流
- 执行任务
- 获取结果
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入系统组件
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph_multi_agent.system.integration import SystemIntegrator


async def basic_workflow_example():
    """基础工作流示例"""
    
    print("=" * 60)
    print("LangGraph多智能体系统 - 基础工作流示例")
    print("=" * 60)
    
    # 1. 初始化系统
    print("\n1. 初始化系统...")
    
    config = {
        "checkpoint_storage": "memory",
        "enable_metrics": True,
        "enable_tracing": True,
        "optimization_level": "moderate"
    }
    
    integrator = SystemIntegrator(config)
    
    try:
        # 初始化系统
        success = await integrator.initialize_system()
        if not success:
            print("❌ 系统初始化失败")
            return
        
        print("✅ 系统初始化成功")
        
        # 2. 查看系统状态
        print("\n2. 系统状态检查...")
        status = await integrator.get_system_status()
        
        print(f"✅ 已注册智能体: {status['registered_agents']} 个")
        print(f"✅ 工作流模板: {status['workflow_templates']} 个")
        print(f"✅ 活跃工作流: {status['active_workflows']} 个")
        
        # 3. 创建工作流
        print("\n3. 创建工作流...")
        
        workflow_id = f"basic_demo_{int(datetime.now().timestamp())}"
        workflow = await integrator.create_workflow(
            workflow_id=workflow_id,
            template_name="simple",
            custom_config={
                "timeout_seconds": 300,
                "max_iterations": 50
            }
        )
        
        print(f"✅ 工作流创建成功: {workflow_id}")
        
        # 4. 准备任务输入
        print("\n4. 准备任务...")
        
        task_input = {
            "task_id": f"task_{int(datetime.now().timestamp())}",
            "title": "基础示例任务",
            "description": "这是一个基础的示例任务，用于演示系统功能",
            "requirements": [
                "分析任务内容",
                "生成处理方案",
                "执行处理逻辑",
                "返回结果"
            ],
            "priority": 2,
            "timeout": 300
        }
        
        print(f"✅ 任务准备完成: {task_input['title']}")
        
        # 5. 执行工作流
        print("\n5. 执行工作流...")
        print("⏳ 正在处理任务，请稍候...")
        
        start_time = datetime.now()
        
        try:
            result = await integrator.execute_workflow(
                workflow_id=workflow_id,
                task_input=task_input,
                config={
                    "recursion_limit": 100,
                    "timeout": 300
                }
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            print(f"✅ 工作流执行完成，耗时: {execution_time:.2f}秒")
            
            # 6. 显示结果
            print("\n6. 执行结果:")
            print("-" * 40)
            
            if isinstance(result, dict):
                for key, value in result.items():
                    if key == "messages" and isinstance(value, list):
                        print(f"{key}: {len(value)} 条消息")
                        for i, msg in enumerate(value[-3:], 1):  # 显示最后3条消息
                            print(f"  消息{i}: {str(msg)[:100]}...")
                    else:
                        print(f"{key}: {str(value)[:200]}...")
            else:
                print(f"结果: {str(result)[:500]}...")
            
        except Exception as e:
            print(f"❌ 工作流执行失败: {e}")
            logger.error(f"工作流执行错误: {e}")
        
        # 7. 系统性能统计
        print("\n7. 性能统计:")
        print("-" * 40)
        
        final_status = await integrator.get_system_status()
        
        if "system_performance" in final_status:
            perf = final_status["system_performance"]
            
            # 缓存统计
            if "cache" in perf:
                cache_stats = perf["cache"]["global_stats"]
                print(f"缓存命中率: {cache_stats.get('hit_rate', 0):.2%}")
                print(f"缓存大小: {cache_stats.get('total_size', 0)} 项")
            
            # 并发执行统计
            if "concurrent_executor" in perf:
                exec_stats = perf["concurrent_executor"]
                print(f"当前负载: {exec_stats.get('current_load', 0):.2%}")
                print(f"运行任务: {exec_stats.get('running_tasks', 0)} 个")
        
        # 8. 健康检查
        print("\n8. 系统健康检查:")
        print("-" * 40)
        
        health = await integrator.system_health_check()
        print(f"整体状态: {health['overall']}")
        
        if health.get("issues"):
            print("发现问题:")
            for issue in health["issues"]:
                print(f"  ⚠️  {issue}")
        else:
            print("✅ 系统运行正常")
        
        # 9. 优化建议
        print("\n9. 优化建议:")
        print("-" * 40)
        
        recommendations = integrator.get_performance_recommendations()
        
        if isinstance(recommendations, dict) and "error" not in recommendations:
            for category, suggestions in recommendations.items():
                if suggestions and isinstance(suggestions, list):
                    print(f"{category}:")
                    for suggestion in suggestions:
                        print(f"  💡 {suggestion}")
        else:
            print("暂无优化建议")
        
    except Exception as e:
        print(f"❌ 示例执行失败: {e}")
        logger.error(f"示例执行错误: {e}")
    
    finally:
        # 10. 清理资源
        print("\n10. 清理资源...")
        
        try:
            await integrator.shutdown_system()
            print("✅ 系统关闭完成")
        except Exception as e:
            print(f"⚠️  系统关闭时出现警告: {e}")
    
    print("\n" + "=" * 60)
    print("基础工作流示例完成")
    print("=" * 60)


def main():
    """主函数"""
    try:
        asyncio.run(basic_workflow_example())
    except KeyboardInterrupt:
        print("\n用户中断执行")
    except Exception as e:
        print(f"程序执行失败: {e}")
        logger.error(f"主程序错误: {e}")


if __name__ == "__main__":
    main()