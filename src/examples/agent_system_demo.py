"""
智能体系统演示 - 个人AI助手任务

这个脚本演示了完整的智能体系统工作流程：
1. MetaAgent 分析任务复杂度
2. TaskDecomposer 分解任务为子任务
3. CoordinatorAgent 协调执行
4. 汇总结果并生成报告
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List
import uuid

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AgentSystemDemo:
    """智能体系统演示类"""

    def __init__(self):
        self.results_dir = Path("demo_results")
        self.results_dir.mkdir(exist_ok=True)
        self.execution_log = []
        self.start_time = datetime.now(timezone.utc)

    def log_execution(self, agent_type: str, action: str, data: Any = None):
        """记录执行日志"""
        timestamp = datetime.now(timezone.utc)
        log_entry = {
            "timestamp": timestamp.isoformat(),
            "agent_type": agent_type,
            "action": action,
            "data": data
        }
        self.execution_log.append(log_entry)
        logger.info(f"[{agent_type}] {action}")

    async def run_demo(self, task_file: str):
        """运行完整的智能体系统演示"""
        logger.info("开始执行个人AI助手任务...")

        # 加载任务
        task_data = self._load_task(task_file)
        self.log_execution("System", "TaskLoaded", {"task_id": task_data.get("task_id")})

        # 执行完整流程
        final_result = await self._execute_complete_workflow(task_data)

        # 保存结果
        await self._save_results(final_result)

        return final_result

    def _load_task(self, task_file: str) -> Dict[str, Any]:
        """加载任务数据"""
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                task_data = json.load(f)
            logger.info(f"任务加载成功: {task_data.get('title')}")
            return task_data
        except Exception as e:
            logger.error(f"❌ 任务加载失败: {e}")
            raise

    async def _execute_complete_workflow(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行完整的工作流程"""
        workflow_result = {
            "task_id": task_data["task_id"],
            "task_title": task_data["title"],
            "execution_id": str(uuid.uuid4()),
            "start_time": self.start_time.isoformat(),
            "phases": []
        }

        try:
            # 阶段1: MetaAgent 任务分析
            self.log_execution("System", "Phase1_Start", "MetaAgent任务分析")
            meta_result = await self._simulate_meta_agent_analysis(task_data)
            workflow_result["phases"].append({
                "phase": "meta_analysis",
                "status": "completed",
                "result": meta_result,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            # 阶段2: TaskDecomposer 任务分解
            self.log_execution("System", "Phase2_Start", "TaskDecomposer任务分解")
            decomposition_result = await self._simulate_task_decomposition(task_data, meta_result)
            workflow_result["phases"].append({
                "phase": "task_decomposition",
                "status": "completed",
                "result": decomposition_result,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            # 阶段3: CoordinatorAgent 任务协调
            self.log_execution("System", "Phase3_Start", "CoordinatorAgent任务协调")
            coordination_result = await self._simulate_coordination(decomposition_result)
            workflow_result["phases"].append({
                "phase": "coordination",
                "status": "completed",
                "result": coordination_result,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            # 阶段4: 任务执行模拟
            self.log_execution("System", "Phase4_Start", "任务执行模拟")
            execution_result = await self._simulate_task_execution(coordination_result)
            workflow_result["phases"].append({
                "phase": "execution",
                "status": "completed",
                "result": execution_result,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            # 阶段5: 结果汇总
            self.log_execution("System", "Phase5_Start", "结果汇总")
            summary_result = await self._generate_summary(workflow_result)
            workflow_result["phases"].append({
                "phase": "summary",
                "status": "completed",
                "result": summary_result,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            workflow_result["end_time"] = datetime.now(timezone.utc).isoformat()
            workflow_result["duration_seconds"] = (
                datetime.fromisoformat(workflow_result["end_time"]) -
                datetime.fromisoformat(workflow_result["start_time"])
            ).total_seconds()
            workflow_result["status"] = "success"
            workflow_result["success"] = True

            logger.info(f"工作流程执行完成，耗时: {workflow_result['duration_seconds']:.2f}秒")

        except Exception as e:
            logger.error(f"❌ 工作流程执行失败: {e}")
            workflow_result["status"] = "failed"
            workflow_result["success"] = False
            workflow_result["error"] = str(e)

        return workflow_result

    async def _simulate_meta_agent_analysis(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """模拟MetaAgent任务分析"""
        await asyncio.sleep(1)  # 模拟分析时间

        task_type = task_data.get("task_type", "general")
        requirements = task_data.get("input_data", {}).get("requirements", [])
        constraints = task_data.get("input_data", {}).get("constraints", [])

        # 模拟复杂度分析
        complexity_factors = {
            "requirements_count": len(requirements),
            "constraints_count": len(constraints),
            "technical_stack_complexity": self._analyze_technical_stack(task_data),
            "timeline_pressure": self._analyze_timeline_pressure(task_data)
        }

        complexity_score = sum(complexity_factors.values())

        if complexity_score < 15:
            complexity_level = "low"
        elif complexity_score < 30:
            complexity_level = "medium"
        else:
            complexity_level = "high"

        analysis_result = {
            "agent_id": "meta_agent_001",
            "analysis_id": str(uuid.uuid4()),
            "task_type": task_type,
            "complexity_level": complexity_level,
            "complexity_score": complexity_score,
            "factors": complexity_factors,
            "needs_decomposition": complexity_level in ["medium", "high"],
            "recommended_approach": self._determine_approach(complexity_level, task_data),
            "estimated_duration": self._estimate_duration(complexity_level),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        self.log_execution("MetaAgent", "AnalysisComplete", analysis_result)
        return analysis_result

    def _analyze_technical_stack(self, task_data: Dict[str, Any]) -> int:
        """分析技术栈复杂度"""
        stack = task_data.get("input_data", {}).get("technical_stack", {})
        complexity = 0

        if stack.get("backend"):
            if "Python" in stack["backend"]:
                complexity += 2
            if "FastAPI" in stack["backend"]:
                complexity += 2
            if "LangGraph" in stack["backend"]:
                complexity += 3

        if stack.get("frontend"):
            if "JavaScript" in stack["frontend"]:
                complexity += 2
            if "React" in stack["frontend"]:
                complexity += 3
            if "Vue" in stack["frontend"]:
                complexity += 2

        if stack.get("database"):
            if "SQLite" in stack["database"]:
                complexity += 1
            if "Redis" in stack["database"]:
                complexity += 1
            if "PostgreSQL" in stack["database"]:
                complexity += 3

        if stack.get("ai_models"):
            complexity += len(stack["ai_models"]) * 2

        return complexity

    def _analyze_timeline_pressure(self, task_data: Dict[str, Any]) -> int:
        """分析时间线压力"""
        deadline = task_data.get("deadline")
        if not deadline:
            return 0

        try:
            deadline_dt = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
            days_remaining = (deadline_dt - datetime.now(timezone.utc)).days

            if days_remaining < 7:
                return 5
            elif days_remaining < 30:
                return 3
            else:
                return 0
        except:
            return 0

    def _determine_approach(self, complexity_level: str, task_data: Dict[str, Any]) -> str:
        """确定实施方法"""
        if complexity_level == "high":
            return "coordinated_development"
        elif complexity_level == "medium":
            return "structured_development"
        else:
            return "iterative_development"

    def _estimate_duration(self, complexity_level: str) -> int:
        """估算持续时间（天）"""
        duration_map = {
            "low": 7,
            "medium": 21,
            "high": 42
        }
        return duration_map.get(complexity_level, 14)

    async def _simulate_task_decomposition(self, task_data: Dict[str, Any], meta_result: Dict[str, Any]) -> Dict[str, Any]:
        """模拟TaskDecomposer任务分解"""
        await asyncio.sleep(2)  # 模拟分解时间

        requirements = task_data.get("input_data", {}).get("requirements", [])

        # 创建子任务
        subtasks = []

        # 基于需求创建子任务
        requirement_mapping = {
            "自然语言对话交互": ["对话引擎开发", "自然语言处理", "对话历史管理"],
            "任务管理功能": ["任务创建模块", "任务状态跟踪", "任务优先级管理"],
            "日程安排管理": ["日历集成", "事件提醒", "时间规划"],
            "信息查询和搜索": ["搜索引擎", "数据检索", "信息聚合"],
            "个性化推荐": ["推荐算法", "用户偏好学习", "内容过滤"],
            "数据分析和可视化": ["数据收集", "分析引擎", "可视化组件"],
            "知识库管理": ["知识存储", "智能检索", "知识更新"],
            "多模态交互支持": ["图像处理", "语音识别", "多模态融合"]
        }

        subtask_id = 1
        for requirement in requirements:
            if requirement in requirement_mapping:
                for subtask_name in requirement_mapping[requirement]:
                    subtask = {
                        "subtask_id": f"subtask_{subtask_id:03d}",
                        "name": subtask_name,
                        "parent_requirement": requirement,
                        "description": f"实现{subtask_name}功能",
                        "priority": "high",
                        "estimated_days": 5,
                        "dependencies": [],
                        "required_skills": ["Python", "AI/ML", "Web开发"]
                    }
                    subtasks.append(subtask)
                    subtask_id += 1

        # 分析依赖关系
        dependency_graph = {}
        for i, subtask in enumerate(subtasks):
            deps = []
            # 模拟一些依赖关系
            if i > 0:
                deps.append(subtasks[i-1]["subtask_id"])
            dependency_graph[subtask["subtask_id"]] = deps

        # 创建工作流计划
        workflow_plan = {
            "parallel_groups": [
                [subtasks[0]["subtask_id"], subtasks[1]["subtask_id"]],  # 阶段1：基础框架
                [subtasks[2]["subtask_id"], subtasks[3]["subtask_id"]],  # 阶段2：核心功能
                [subtasks[4]["subtask_id"], subtasks[5]["subtask_id"]],  # 阶段3：智能功能
                [subtasks[6]["subtask_id"], subtasks[7]["subtask_id"]]   # 阶段4：高级功能
            ],
            "critical_path": [subtask["subtask_id"] for subtask in subtasks],
            "estimated_total_days": max([subtask.get("estimated_days", 0) for subtask in subtasks]) * len(subtasks),
            "parallel_execution": True
        }

        decomposition_result = {
            "agent_id": "task_decomposer_001",
            "decomposition_id": str(uuid.uuid4()),
            "original_task_id": task_data["task_id"],
            "subtasks_count": len(subtasks),
            "subtasks": subtasks,
            "dependency_graph": dependency_graph,
            "workflow_plan": workflow_plan,
            "complexity_score": meta_result.get("complexity_score", 0),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        self.log_execution("TaskDecomposer", "DecompositionComplete", {
            "subtasks_count": len(subtasks),
            "workflow_groups": len(workflow_plan["parallel_groups"])
        })
        return decomposition_result

    async def _simulate_coordination(self, decomposition_result: Dict[str, Any]) -> Dict[str, Any]:
        """模拟CoordinatorAgent协调"""
        await asyncio.sleep(1.5)  # 模拟协调时间

        subtasks = decomposition_result.get("subtasks", [])
        workflow_plan = decomposition_result.get("workflow_plan", {})
        parallel_groups = workflow_plan.get("parallel_groups", [])

        coordination_result = {
            "agent_id": "coordinator_001",
            "coordination_id": str(uuid.uuid4()),
            "assigned_agents": [],
            "execution_plan": {},
            "resource_allocation": {},
            "timeline": {}
        }

        # 为每个并行组分配资源
        total_duration = 0
        for i, group in enumerate(parallel_groups):
            group_duration = 0
            group_agents = []

            for j, subtask_id in enumerate(group):
                # 查找子任务
                subtask = next((s for s in subtasks if s["subtask_id"] == subtask_id), None)
                if subtask:
                    # 分配智能体
                    agent_id = f"agent_{i+1}_{j+1}"
                    group_agents.append(agent_id)

                    # 分配资源
                    resource_allocation = {
                        "cpu_cores": 2,
                        "memory_gb": 4,
                        "storage_gb": 10,
                        "estimated_duration": subtask.get("estimated_days", 5)
                    }

                    coordination_result["resource_allocation"][agent_id] = resource_allocation
                    group_duration = max(group_duration, resource_allocation["estimated_duration"])

            coordination_result["execution_plan"][f"group_{i+1}"] = {
                "subtasks": group,
                "agents": group_agents,
                "duration_days": group_duration,
                "start_day": total_duration + 1
            }

            coordination_result["assigned_agents"].extend(group_agents)
            total_duration += group_duration

        coordination_result["total_duration_days"] = total_duration
        coordination_result["estimated_completion_date"] = (
            datetime.now(timezone.utc) + timedelta(days=total_duration)
        ).isoformat()

        self.log_execution("Coordinator", "CoordinationComplete", {
            "groups_count": len(parallel_groups),
            "total_duration_days": total_duration,
            "agents_assigned": len(coordination_result["assigned_agents"])
        })
        return coordination_result

    async def _simulate_task_execution(self, coordination_result: Dict[str, Any]) -> Dict[str, Any]:
        """模拟任务执行"""
        await asyncio.sleep(1)  # 模拟执行时间

        execution_result = {
            "execution_id": str(uuid.uuid4()),
            "execution_status": "in_progress",
            "progress": {},
            "completed_subtasks": [],
            "failed_subtasks": [],
            "quality_metrics": {}
        }

        # 模拟每个组的执行进度
        execution_plan = coordination_result.get("execution_plan", {})

        for group_name, group_info in execution_plan.items():
            group_progress = {}
            subtasks = group_info.get("subtasks", [])

            for subtask_id in subtasks:
                # 模拟子任务执行
                await asyncio.sleep(0.2)
                progress = min(100, len(group_progress) * 20 + 20)
                group_progress[subtask_id] = progress

                if progress >= 100:
                    execution_result["completed_subtasks"].append(subtask_id)
                    quality_score = 85 + (hash(subtask_id) % 15)  # 模拟质量分数
                    execution_result["quality_metrics"][subtask_id] = quality_score
                else:
                    group_progress[subtask_id] = progress

            execution_result["progress"][group_name] = {
                "overall_progress": sum(group_progress.values()) / len(group_progress),
                "subtasks_progress": group_progress,
                "status": "completed" if all(p >= 100 for p in group_progress.values()) else "in_progress"
            }

        # 计算总体进度
        all_progress = []
        for group_info in execution_result["progress"].values():
            all_progress.append(group_info["overall_progress"])

        overall_progress = sum(all_progress) / len(all_progress) if all_progress else 0
        execution_result["overall_progress"] = overall_progress
        execution_result["execution_status"] = "completed" if overall_progress >= 100 else "in_progress"

        if overall_progress >= 100:
            execution_result["completion_time"] = datetime.now(timezone.utc).isoformat()
            execution_result["quality_score"] = sum(
                execution_result["quality_metrics"].get(subtask_id, 85)
                for subtask_id in execution_result["quality_metrics"]
            ) / len(execution_result["quality_metrics"]) if execution_result["quality_metrics"] else 85

        self.log_execution("Executor", "ExecutionComplete", {
            "overall_progress": overall_progress,
            "completed_subtasks": len(execution_result["completed_subtasks"]),
            "quality_score": execution_result.get("quality_score", 0)
        })
        return execution_result

    async def _generate_summary(self, workflow_result: Dict[str, Any]) -> Dict[str, Any]:
        """生成汇总报告"""
        summary = {
            "summary_id": str(uuid.uuid4()),
            "task_info": {
                "task_id": workflow_result["task_id"],
                "task_title": workflow_result["task_title"],
                "execution_id": workflow_result["execution_id"]
            },
            "execution_summary": {
                "status": workflow_result.get("status", "unknown"),
                "success": workflow_result.get("success", False),
                "duration_seconds": workflow_result.get("duration_seconds", 0),
                "phases_completed": len(workflow_result.get("phases", [])),
                "start_time": workflow_result.get("start_time"),
                "end_time": workflow_result.get("end_time")
            },
            "phase_results": {},
            "key_metrics": {},
            "recommendations": []
        }

        # 收集各阶段结果
        for phase in workflow_result.get("phases", []):
            phase_name = phase["phase"]
            phase_result = phase.get("result", {})

            summary["phase_results"][phase_name] = {
                "status": phase.get("status"),
                "duration": 0,  # 这里可以计算各阶段耗时
                "key_outputs": []
            }

            # 提取关键输出
            if phase_name == "meta_analysis":
                summary["phase_results"][phase_name]["key_outputs"] = [
                    f"复杂度级别: {phase_result.get('complexity_level', 'unknown')}",
                    f"分解需求: {phase_result.get('needs_decomposition', False)}"
                ]
            elif phase_name == "task_decomposition":
                summary["phase_results"][phase_name]["key_outputs"] = [
                    f"子任务数量: {phase_result.get('subtasks_count', 0)}",
                    f"并行组数: {len(phase_result.get('workflow_plan', {}).get('parallel_groups', []))}"
                ]
            elif phase_name == "coordination":
                summary["phase_results"][phase_name]["key_outputs"] = [
                    f"协调智能体: {phase_result.get('agent_id', 'unknown')}",
                    f"分配任务组: {len(phase_result.get('execution_plan', {}))}"
                ]
            elif phase_name == "execution":
                summary["phase_results"][phase_name]["key_outputs"] = [
                    f"完成进度: {phase_result.get('overall_progress', 0):.1f}%",
                    f"质量评分: {phase_result.get('quality_score', 0):.1f}"
                ]

        # 计算关键指标
        meta_phase = next((p for p in workflow_result.get("phases", []) if p["phase"] == "meta_analysis"), None)
        if meta_phase:
            meta_result = meta_phase.get("result", {})
            summary["key_metrics"]["complexity_level"] = meta_result.get("complexity_level")
            summary["key_metrics"]["complexity_score"] = meta_result.get("complexity_score")
            summary["key_metrics"]["estimated_duration"] = meta_result.get("estimated_duration")

        decomp_phase = next((p for p in workflow_result.get("phases", []) if p["phase"] == "task_decomposition"), None)
        if decomp_phase:
            decomp_result = decomp_phase.get("result", {})
            summary["key_metrics"]["subtasks_created"] = decomp_result.get("subtasks_count", 0)
            summary["key_metrics"]["workflow_groups"] = len(decomp_result.get("workflow_plan", {}).get("parallel_groups", []))

        exec_phase = next((p for p in workflow_result.get("phases", []) if p["phase"] == "execution"), None)
        if exec_phase:
            exec_result = exec_phase.get("result", {})
            summary["key_metrics"]["overall_progress"] = exec_result.get("overall_progress", 0)
            summary["key_metrics"]["quality_score"] = exec_result.get("quality_score", 0)

        # 生成建议
        recommendations = []

        if summary["key_metrics"].get("complexity_level") == "high":
            recommendations.append("建议分阶段实施，优先实现核心功能")

        if summary["key_metrics"].get("overall_progress", 0) < 100:
            recommendations.append("任务执行未完成，建议检查依赖关系")

        if summary["key_metrics"].get("quality_score", 0) < 80:
            recommendations.append("建议增加测试和质量保证环节")

        summary["recommendations"] = recommendations

        self.log_execution("System", "SummaryGenerated", {
            "recommendations_count": len(recommendations),
            "quality_score": summary["key_metrics"].get("quality_score", 0)
        })
        return summary

    async def _save_results(self, final_result: Dict[str, Any]):
        """保存所有结果"""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        # 保存完整结果
        results_file = self.results_dir / f"agent_system_results_{timestamp}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(final_result, f, ensure_ascii=False, indent=2)

        # 保存执行日志
        log_file = self.results_dir / f"execution_log_{timestamp}.json"
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(self.execution_log, f, ensure_ascii=False, indent=2)

        # 保存可读报告
        report_file = self.results_dir / f"execution_report_{timestamp}.md"
        await self._generate_readable_report(final_result, report_file)

        # 保存任务数据
        task_file = self.results_dir / f"task_data_{timestamp}.json"
        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(final_result.get("phase_results", {}), f, ensure_ascii=False, indent=2)

        # 返回文件路径
        return {
            "results_file": str(results_file),
            "log_file": str(log_file),
            "report_file": str(report_file),
            "task_data_file": str(task_file),
            "timestamp": timestamp
        }

    async def _generate_readable_report(self, results: Dict[str, Any], output_file: Path):
        """生成可读的报告"""
        report = []
        report.append("# 个人AI助手任务执行报告")
        report.append(f"执行时间: {results.get('end_time', 'Unknown')}")
        report.append(f"执行ID: {results.get('execution_id', 'Unknown')}")
        report.append(f"任务ID: {results.get('task_id', 'Unknown')}")
        report.append(f"任务标题: {results.get('task_title', 'Unknown')}")
        report.append("")

        # 执行概要
        report.append("## 执行概要")
        report.append(f"- **状态**: {'成功' if results.get('success') else '失败'}")
        report.append(f"- **耗时**: {results.get('duration_seconds', 0):.2f} 秒")
        report.append(f"- **阶段数**: {len(results.get('phases', []))}")
        report.append("")

        # 阶段详情
        report.append("## 🔄 执行阶段详情")
        for i, phase in enumerate(results.get("phases", []), 1):
            report.append(f"### 阶段 {i}: {phase['phase'].title()}")
            report.append(f"- **状态**: {phase.get('status', 'Unknown')}")
            report.append(f"- **时间**: {phase.get('timestamp', 'Unknown')}")

            result = phase.get("result", {})
            if "complexity_level" in result:
                report.append(f"- **复杂度**: {result['complexity_level']}")
            if "subtasks_count" in result:
                report.append(f"- **子任务数**: {result['subtasks_count']}")
            if "overall_progress" in result:
                report.append(f"- **完成度**: {result['overall_progress']:.1f}%")
            if "quality_score" in result:
                report.append(f"- **质量评分**: {result['quality_score']:.1f}/100")
            report.append("")

        # 关键指标
        report.append("## 关键指标")
        execution_summary = results.get("execution_summary", {})
        summary = results.get("key_metrics", {})

        for metric_name, metric_value in summary.items():
            report.append(f"- **{metric_name}**: {metric_value}")
        report.append("")

        # 建议
        report.append("## 改进建议")
        phase_summary = results.get("phase_results", {})
        summary_phase = phase_summary.get("summary", {})
        recommendations = summary_phase.get("recommendations", [])

        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                report.append(f"{i}. {rec}")
        else:
            report.append("- 无重大问题，执行良好")
        report.append("")

        # 保存报告
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))

async def main():
    """主函数"""
    demo = AgentSystemDemo()

    # 运行演示
    task_file = "examples/personal_ai_assistant_task.json"
    results = await demo.run_demo(task_file)

    # 输出结果信息
    print("\n" + "="*80)
    print("个人AI助手任务执行完成！")
    print("="*80)
    print(f"任务标题: {results['task_title']}")
    print(f"执行状态: {'成功' if results['success'] else '失败'}")
    print(f"执行耗时: {results['duration_seconds']:.2f} 秒")
    print(f"完成阶段: {len(results['phases'])}")
    print(f"质量评分: {results.get('key_metrics', {}).get('quality_score', 0):.1f}/100")
    print("\n结果文件保存位置:")

    file_paths = results.get("file_paths", {})
    if file_paths:
        for file_type, file_path in file_paths.items():
            print(f"  {file_type}: {file_path}")

    print("\n查看详细报告:")
    print(f"  {file_paths.get('report_file', '')}")

    return results

if __name__ == "__main__":
    asyncio.run(main())