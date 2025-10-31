#!/usr/bin/env python3
"""
并行处理示例

这个示例展示了如何使用多智能体系统进行并行任务处理。
包括：
- 任务分解
- 并行执行
- 结果聚合
- 性能对比
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, List
import random

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


def generate_parallel_tasks() -> List[Dict[str, Any]]:
    """生成并行处理任务"""
    
    task_types = [
        "文本处理",
        "数据计算", 
        "图像分析",
        "文档生成",
        "数据验证"
    ]
    
    tasks = []
    for i in range(10):  # 生成10个任务
        task = {
            "task_id": f"parallel_task_{i+1}",
            "task_type": random.choice(task_types),
            "title": f"并行任务 {i+1}",
            "description": f"这是第 {i+1} 个并行处理任务",
            "complexity": random.choice(["simple", "medium", "complex"]),
            "estimated_time": random.randint(5, 30),  # 预估处理时间（秒）
            "data_size": random.randint(100, 1000),   # 数据大小（KB）
            "priority": random.randint(1, 3),
            "dependencies": [],  # 简化示例，无依赖关系
            "processing_requirements": {
                "cpu_intensive": random.choice([True, False]),
                "memory_intensive": random.choice([True, False]),
                "io_intensive": random.choice([True, False])
            }
        }
        tasks.append(task)
    
    return tasks


async def simulate_task_processing(task: Dict[str, Any]) -> Dict[str, Any]:
    """模拟任务处理"""
    
    start_time = time.time()
    
    # 根据任务复杂度模拟处理时间
    complexity_time = {
        "simple": random.uniform(1, 3),
        "medium": random.uniform(3, 8),
        "complex": random.uniform(8, 15)
    }
    
    processing_time = complexity_time.get(task["complexity"], 5)
    await asyncio.sleep(processing_time)
    
    end_time = time.time()
    actual_time = end_time - start_time
    
    # 模拟处理结果
    result = {
        "task_id": task["task_id"],
        "status": "completed",
        "actual_processing_time": actual_time,
        "estimated_time": task["estimated_time"],
        "efficiency": task["estimated_time"] / actual_time if actual_time > 0 else 1.0,
        "output_data": {
            "processed_items": random.randint(50, 200),
            "success_rate": random.uniform(0.85, 0.99),
            "quality_score": random.uniform(0.8, 0.95)
        },
        "resource_usage": {
            "cpu_usage": random.uniform(0.2, 0.8),
            "memory_usage": random.uniform(0.1, 0.6),
            "io_operations": random.randint(10, 100)
        }
    }
    
    return result


async def parallel_processing_example():
    """并行处理示例"""
    
    print("=" * 70)
    print("LangGraph多智能体系统 - 并行处理示例")
    print("=" * 70)
    
    # 1. 生成并行任务
    print("\n1. 生成并行处理任务...")
    
    parallel_tasks = generate_parallel_tasks()
    print(f"✅ 生成 {len(parallel_tasks)} 个并行任务")
    
    # 显示任务概览
    task_summary = {}
    for task in parallel_tasks:
        task_type = task["task_type"]
        task_summary[task_type] = task_summary.get(task_type, 0) + 1
    
    print("任务类型分布:")
    for task_type, count in task_summary.items():
        print(f"  • {task_type}: {count} 个")
    
    # 2. 初始化系统
    print("\n2. 初始化并行处理系统...")
    
    config = {
        "checkpoint_storage": "memory",
        "enable_metrics": True,
        "enable_tracing": True,
        "optimization_level": "aggressive",  # 使用激进优化
        "performance": {
            "max_cache_size": 10000,
            "enable_auto_optimization": True,
            "max_workers": 8,  # 增加工作线程
            "execution_mode": "adaptive",
            "enable_auto_scaling": True
        }
    }
    
    integrator = SystemIntegrator(config)
    
    try:
        # 初始化系统
        success = await integrator.initialize_system()
        if not success:
            print("❌ 系统初始化失败")
            return
        
        print("✅ 并行处理系统初始化成功")
        
        # 3. 创建并行工作流
        print("\n3. 创建并行工作流...")
        
        workflow_id = f"parallel_workflow_{int(datetime.now().timestamp())}"
        workflow = await integrator.create_workflow(
            workflow_id=workflow_id,
            template_name="parallel",  # 使用并行模板
            custom_config={
                "timeout_seconds": 300,
                "max_iterations": 50,
                "execution_mode": "parallel",
                "max_concurrent_tasks": 5
            }
        )
        
        print(f"✅ 并行工作流创建成功: {workflow_id}")
        
        # 4. 顺序处理基准测试
        print("\n4. 顺序处理基准测试...")
        print("⏳ 执行顺序处理（用于性能对比）...")
        
        sequential_start = time.time()
        sequential_results = []
        
        for i, task in enumerate(parallel_tasks[:5], 1):  # 只处理前5个任务作为基准
            print(f"   处理任务 {i}/5: {task['title']}")
            result = await simulate_task_processing(task)
            sequential_results.append(result)
        
        sequential_time = time.time() - sequential_start
        
        print(f"✅ 顺序处理完成，耗时: {sequential_time:.2f}秒")
        
        # 5. 并行处理测试
        print("\n5. 并行处理测试...")
        print("⏳ 执行并行处理...")
        
        parallel_start = time.time()
        
        # 创建并行任务
        parallel_coroutines = []
        for task in parallel_tasks:
            parallel_coroutines.append(simulate_task_processing(task))
        
        # 并行执行所有任务
        parallel_results = await asyncio.gather(*parallel_coroutines, return_exceptions=True)
        
        parallel_time = time.time() - parallel_start
        
        # 过滤异常结果
        successful_results = [r for r in parallel_results if not isinstance(r, Exception)]
        failed_results = [r for r in parallel_results if isinstance(r, Exception)]
        
        print(f"✅ 并行处理完成，耗时: {parallel_time:.2f}秒")
        print(f"   成功任务: {len(successful_results)} 个")
        print(f"   失败任务: {len(failed_results)} 个")
        
        # 6. 性能对比分析
        print("\n6. 性能对比分析:")
        print("=" * 50)
        
        # 计算性能提升
        if sequential_time > 0:
            speedup = sequential_time / parallel_time
            efficiency = speedup / len(parallel_tasks)
            
            print(f"顺序处理时间: {sequential_time:.2f}秒 (5个任务)")
            print(f"并行处理时间: {parallel_time:.2f}秒 ({len(parallel_tasks)}个任务)")
            print(f"理论加速比: {speedup:.2f}x")
            print(f"并行效率: {efficiency:.2%}")
        
        # 7. 详细结果分析
        print("\n7. 详细结果分析:")
        print("-" * 50)
        
        if successful_results:
            # 统计分析
            total_processing_time = sum(r["actual_processing_time"] for r in successful_results)
            avg_processing_time = total_processing_time / len(successful_results)
            avg_efficiency = sum(r["efficiency"] for r in successful_results) / len(successful_results)
            avg_success_rate = sum(r["output_data"]["success_rate"] for r in successful_results) / len(successful_results)
            avg_quality_score = sum(r["output_data"]["quality_score"] for r in successful_results) / len(successful_results)
            
            print(f"平均处理时间: {avg_processing_time:.2f}秒")
            print(f"平均效率: {avg_efficiency:.2f}")
            print(f"平均成功率: {avg_success_rate:.2%}")
            print(f"平均质量分数: {avg_quality_score:.2%}")
            
            # 资源使用统计
            avg_cpu = sum(r["resource_usage"]["cpu_usage"] for r in successful_results) / len(successful_results)
            avg_memory = sum(r["resource_usage"]["memory_usage"] for r in successful_results) / len(successful_results)
            total_io = sum(r["resource_usage"]["io_operations"] for r in successful_results)
            
            print(f"\n资源使用情况:")
            print(f"  平均CPU使用率: {avg_cpu:.2%}")
            print(f"  平均内存使用率: {avg_memory:.2%}")
            print(f"  总I/O操作数: {total_io}")
        
        # 8. 系统性能监控
        print("\n8. 系统性能监控:")
        print("-" * 50)
        
        status = await integrator.get_system_status()
        
        if "system_performance" in status:
            perf = status["system_performance"]
            
            # 并发执行器统计
            if "concurrent_executor" in perf:
                exec_stats = perf["concurrent_executor"]
                stats = exec_stats.get("stats", {})
                
                print("并发执行器统计:")
                print(f"  提交任务: {stats.get('submitted', 0)} 个")
                print(f"  完成任务: {stats.get('completed', 0)} 个")
                print(f"  失败任务: {stats.get('failed', 0)} 个")
                print(f"  当前负载: {exec_stats.get('current_load', 0):.2%}")
                print(f"  工作线程: {exec_stats.get('worker_threads', 0)} 个")
            
            # 缓存性能
            if "cache" in perf:
                cache_stats = perf["cache"]["global_stats"]
                print(f"\n缓存性能:")
                print(f"  命中率: {cache_stats.get('hit_rate', 0):.2%}")
                print(f"  缓存大小: {cache_stats.get('total_size', 0)} 项")
        
        # 9. 并发执行器优化
        print("\n9. 并发执行器优化...")
        
        concurrent_executor = integrator.get_concurrent_executor()
        if concurrent_executor:
            # 获取性能摘要
            perf_summary = concurrent_executor.get_performance_summary()
            
            print("并发执行性能摘要:")
            print(f"  总任务数: {perf_summary.get('total_tasks', 0)}")
            print(f"  成功率: {perf_summary.get('success_rate', 0):.2%}")
            print(f"  平均执行时间: {perf_summary.get('avg_execution_time', 0):.3f}秒")
            print(f"  最小执行时间: {perf_summary.get('min_execution_time', 0):.3f}秒")
            print(f"  最大执行时间: {perf_summary.get('max_execution_time', 0):.3f}秒")
            print(f"  队列积压: {perf_summary.get('queue_backlog', 0)} 个")
            
            # 尝试优化
            optimized = await concurrent_executor.adjust_concurrency_level()
            if optimized:
                print("✅ 并发级别已优化")
            else:
                print("ℹ️  当前并发级别已是最优")
        
        # 10. 健康检查和建议
        print("\n10. 系统健康检查:")
        print("-" * 50)
        
        health = await integrator.system_health_check()
        print(f"整体健康状态: {health['overall']}")
        
        if health.get("issues"):
            print("发现的问题:")
            for issue in health["issues"]:
                print(f"  ⚠️  {issue}")
        
        # 优化建议
        recommendations = integrator.get_performance_recommendations()
        
        if isinstance(recommendations, dict) and "error" not in recommendations:
            print("\n优化建议:")
            for category, suggestions in recommendations.items():
                if suggestions and isinstance(suggestions, list):
                    print(f"{category}:")
                    for suggestion in suggestions:
                        print(f"  💡 {suggestion}")
        
    except Exception as e:
        print(f"❌ 示例执行失败: {e}")
        logger.error(f"并行处理示例错误: {e}")
    
    finally:
        # 11. 清理资源
        print("\n11. 清理资源...")
        
        try:
            await integrator.shutdown_system()
            print("✅ 系统关闭完成")
        except Exception as e:
            print(f"⚠️  系统关闭时出现警告: {e}")
    
    print("\n" + "=" * 70)
    print("并行处理示例完成")
    print("=" * 70)


def main():
    """主函数"""
    try:
        asyncio.run(parallel_processing_example())
    except KeyboardInterrupt:
        print("\n用户中断执行")
    except Exception as e:
        print(f"程序执行失败: {e}")
        logger.error(f"主程序错误: {e}")


if __name__ == "__main__":
    main()