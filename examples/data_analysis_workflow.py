#!/usr/bin/env python3
"""
数据分析工作流示例

这个示例展示了如何使用多智能体系统进行数据分析任务。
包括：
- 数据预处理
- 统计分析
- 可视化生成
- 报告生成
"""

import asyncio
import logging
import json
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


def generate_sample_data() -> Dict[str, Any]:
    """生成示例数据"""
    
    # 模拟销售数据
    products = ["产品A", "产品B", "产品C", "产品D", "产品E"]
    regions = ["北京", "上海", "广州", "深圳", "杭州"]
    months = ["2024-01", "2024-02", "2024-03", "2024-04", "2024-05", "2024-06"]
    
    sales_data = []
    for month in months:
        for region in regions:
            for product in products:
                sales_data.append({
                    "month": month,
                    "region": region,
                    "product": product,
                    "sales": random.randint(1000, 10000),
                    "units": random.randint(10, 100),
                    "cost": random.randint(500, 5000)
                })
    
    return {
        "dataset_name": "销售数据分析",
        "description": "2024年上半年各地区产品销售数据",
        "data": sales_data,
        "metadata": {
            "total_records": len(sales_data),
            "date_range": "2024-01 to 2024-06",
            "regions": regions,
            "products": products
        }
    }


async def data_analysis_workflow_example():
    """数据分析工作流示例"""
    
    print("=" * 70)
    print("LangGraph多智能体系统 - 数据分析工作流示例")
    print("=" * 70)
    
    # 1. 生成示例数据
    print("\n1. 生成示例数据...")
    
    sample_data = generate_sample_data()
    print(f"✅ 生成数据集: {sample_data['dataset_name']}")
    print(f"   记录数: {sample_data['metadata']['total_records']}")
    print(f"   时间范围: {sample_data['metadata']['date_range']}")
    
    # 2. 初始化系统
    print("\n2. 初始化分析系统...")
    
    config = {
        "checkpoint_storage": "memory",
        "enable_metrics": True,
        "enable_tracing": True,
        "optimization_level": "moderate",
        "performance": {
            "max_cache_size": 5000,
            "enable_auto_optimization": True,
            "max_workers": 4
        }
    }
    
    integrator = SystemIntegrator(config)
    
    try:
        # 初始化系统
        success = await integrator.initialize_system()
        if not success:
            print("❌ 系统初始化失败")
            return
        
        print("✅ 分析系统初始化成功")
        
        # 3. 创建数据分析工作流
        print("\n3. 创建数据分析工作流...")
        
        workflow_id = f"data_analysis_{int(datetime.now().timestamp())}"
        workflow = await integrator.create_workflow(
            workflow_id=workflow_id,
            template_name="analysis",  # 使用分析模板
            custom_config={
                "timeout_seconds": 600,  # 10分钟超时
                "max_iterations": 100,
                "execution_mode": "sequential"
            }
        )
        
        print(f"✅ 数据分析工作流创建成功: {workflow_id}")
        
        # 4. 准备分析任务
        print("\n4. 准备分析任务...")
        
        analysis_task = {
            "task_id": f"analysis_task_{int(datetime.now().timestamp())}",
            "title": "销售数据综合分析",
            "description": "对2024年上半年销售数据进行全面分析",
            "task_type": "data_analysis",
            "data": sample_data,
            "analysis_requirements": [
                "数据质量检查和清洗",
                "描述性统计分析",
                "销售趋势分析",
                "地区销售对比",
                "产品性能分析",
                "异常值检测",
                "预测建模",
                "可视化图表生成",
                "分析报告生成"
            ],
            "output_format": "comprehensive_report",
            "priority": 3,
            "constraints": {
                "max_processing_time": 600,
                "required_confidence": 0.85,
                "visualization_types": ["bar_chart", "line_chart", "heatmap", "scatter_plot"]
            }
        }
        
        print(f"✅ 分析任务准备完成")
        print(f"   任务类型: {analysis_task['task_type']}")
        print(f"   分析要求: {len(analysis_task['analysis_requirements'])} 项")
        
        # 5. 执行数据分析工作流
        print("\n5. 执行数据分析工作流...")
        print("⏳ 正在进行数据分析，这可能需要几分钟...")
        
        start_time = datetime.now()
        
        try:
            # 分阶段显示进度
            print("   📊 阶段1: 数据预处理和质量检查...")
            await asyncio.sleep(1)  # 模拟处理时间
            
            print("   📈 阶段2: 统计分析和趋势识别...")
            await asyncio.sleep(1)
            
            print("   🎯 阶段3: 深度分析和模式发现...")
            await asyncio.sleep(1)
            
            print("   📋 阶段4: 报告生成和结果整理...")
            
            result = await integrator.execute_workflow(
                workflow_id=workflow_id,
                task_input=analysis_task,
                config={
                    "recursion_limit": 150,
                    "timeout": 600
                }
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            print(f"✅ 数据分析完成，总耗时: {execution_time:.2f}秒")
            
            # 6. 分析结果展示
            print("\n6. 分析结果:")
            print("=" * 50)
            
            if isinstance(result, dict):
                # 显示分析摘要
                if "analysis_summary" in result:
                    summary = result["analysis_summary"]
                    print("📊 分析摘要:")
                    for key, value in summary.items():
                        print(f"   {key}: {value}")
                
                # 显示关键发现
                if "key_findings" in result:
                    findings = result["key_findings"]
                    print("\n🔍 关键发现:")
                    for i, finding in enumerate(findings, 1):
                        print(f"   {i}. {finding}")
                
                # 显示统计结果
                if "statistics" in result:
                    stats = result["statistics"]
                    print("\n📈 统计结果:")
                    for metric, value in stats.items():
                        print(f"   {metric}: {value}")
                
                # 显示建议
                if "recommendations" in result:
                    recommendations = result["recommendations"]
                    print("\n💡 分析建议:")
                    for i, rec in enumerate(recommendations, 1):
                        print(f"   {i}. {rec}")
            
            # 7. 生成模拟的详细分析结果
            print("\n7. 详细分析结果:")
            print("-" * 50)
            
            # 模拟分析结果
            detailed_results = {
                "数据质量": {
                    "完整性": "99.8%",
                    "准确性": "95.2%",
                    "异常值": "2.1%",
                    "缺失值": "0.2%"
                },
                "销售趋势": {
                    "总体趋势": "上升",
                    "增长率": "15.3%",
                    "季节性": "明显",
                    "波动性": "中等"
                },
                "地区分析": {
                    "最佳地区": "上海",
                    "增长最快": "深圳",
                    "潜力地区": "杭州",
                    "需关注": "北京"
                },
                "产品分析": {
                    "热销产品": "产品C",
                    "利润最高": "产品A",
                    "增长最快": "产品E",
                    "需优化": "产品D"
                }
            }
            
            for category, metrics in detailed_results.items():
                print(f"\n{category}:")
                for metric, value in metrics.items():
                    print(f"  • {metric}: {value}")
            
        except Exception as e:
            print(f"❌ 数据分析执行失败: {e}")
            logger.error(f"分析工作流错误: {e}")
        
        # 8. 性能分析
        print("\n8. 性能分析:")
        print("-" * 50)
        
        # 获取系统性能统计
        status = await integrator.get_system_status()
        
        if "system_performance" in status:
            perf = status["system_performance"]
            
            print("系统性能指标:")
            
            # 缓存性能
            if "cache" in perf:
                cache_stats = perf["cache"]["global_stats"]
                print(f"  缓存命中率: {cache_stats.get('hit_rate', 0):.2%}")
                print(f"  缓存使用量: {cache_stats.get('total_size', 0)} 项")
            
            # 并发执行性能
            if "concurrent_executor" in perf:
                exec_stats = perf["concurrent_executor"]
                print(f"  系统负载: {exec_stats.get('current_load', 0):.2%}")
                print(f"  任务统计: 提交 {exec_stats.get('stats', {}).get('submitted', 0)}, "
                      f"完成 {exec_stats.get('stats', {}).get('completed', 0)}")
        
        # 9. 优化建议
        print("\n9. 系统优化建议:")
        print("-" * 50)
        
        recommendations = integrator.get_performance_recommendations()
        
        if isinstance(recommendations, dict) and "error" not in recommendations:
            for category, suggestions in recommendations.items():
                if suggestions and isinstance(suggestions, list):
                    print(f"{category}:")
                    for suggestion in suggestions:
                        print(f"  💡 {suggestion}")
        
        # 10. 执行系统优化
        print("\n10. 执行系统优化...")
        
        optimization_result = await integrator.optimize_system_performance()
        
        if "error" not in optimization_result:
            print(f"✅ 系统优化完成")
            print(f"   应用优化策略: {optimization_result.get('optimization_results', 0)} 个")
            print(f"   性能提升: {optimization_result.get('total_improvement', 0):.1f}%")
        else:
            print(f"⚠️  系统优化遇到问题: {optimization_result['error']}")
        
    except Exception as e:
        print(f"❌ 示例执行失败: {e}")
        logger.error(f"数据分析示例错误: {e}")
    
    finally:
        # 11. 清理资源
        print("\n11. 清理资源...")
        
        try:
            await integrator.shutdown_system()
            print("✅ 系统关闭完成")
        except Exception as e:
            print(f"⚠️  系统关闭时出现警告: {e}")
    
    print("\n" + "=" * 70)
    print("数据分析工作流示例完成")
    print("=" * 70)


def main():
    """主函数"""
    try:
        asyncio.run(data_analysis_workflow_example())
    except KeyboardInterrupt:
        print("\n用户中断执行")
    except Exception as e:
        print(f"程序执行失败: {e}")
        logger.error(f"主程序错误: {e}")


if __name__ == "__main__":
    main()