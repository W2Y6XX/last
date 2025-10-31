#!/usr/bin/env python3
"""
演示服务器

这个服务器提供了一个简单的Web界面来演示LangGraph多智能体系统的功能。
包括：
- REST API演示
- WebSocket实时通信
- 系统状态监控
- 性能指标展示
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

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

# 全局变量
app = FastAPI(
    title="LangGraph多智能体系统演示",
    description="演示LangGraph多智能体系统的各种功能",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局系统集成器
integrator: SystemIntegrator = None
websocket_connections: List[WebSocket] = []


async def initialize_system():
    """初始化系统"""
    global integrator
    
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
    success = await integrator.initialize_system()
    
    if success:
        logger.info("演示系统初始化成功")
    else:
        logger.error("演示系统初始化失败")
        raise RuntimeError("系统初始化失败")


@app.on_event("startup")
async def startup_event():
    """启动事件"""
    await initialize_system()


@app.on_event("shutdown")
async def shutdown_event():
    """关闭事件"""
    if integrator:
        await integrator.shutdown_system()


# 静态文件服务
demo_static_dir = Path(__file__).parent / "static"
if demo_static_dir.exists():
    app.mount("/static", StaticFiles(directory=demo_static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
async def demo_home():
    """演示主页"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>LangGraph多智能体系统演示</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #333; text-align: center; margin-bottom: 30px; }
            .section { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
            .button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
            .button:hover { background: #0056b3; }
            .result { background: #f8f9fa; padding: 15px; border-radius: 5px; margin-top: 10px; white-space: pre-wrap; }
            .status { padding: 10px; border-radius: 5px; margin: 10px 0; }
            .status.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .status.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            .status.info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
            .metric { background: #e9ecef; padding: 15px; border-radius: 5px; text-align: center; }
            .metric-value { font-size: 24px; font-weight: bold; color: #007bff; }
            .metric-label { font-size: 14px; color: #666; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 LangGraph多智能体系统演示</h1>
            
            <div class="section">
                <h2>📊 系统状态</h2>
                <button class="button" onclick="checkSystemStatus()">检查系统状态</button>
                <button class="button" onclick="healthCheck()">健康检查</button>
                <div id="systemStatus" class="result"></div>
            </div>
            
            <div class="section">
                <h2>🚀 快速演示</h2>
                <button class="button" onclick="runBasicWorkflow()">运行基础工作流</button>
                <button class="button" onclick="runDataAnalysis()">数据分析演示</button>
                <button class="button" onclick="runParallelProcessing()">并行处理演示</button>
                <div id="workflowResult" class="result"></div>
            </div>
            
            <div class="section">
                <h2>⚡ 性能监控</h2>
                <button class="button" onclick="getPerformanceMetrics()">获取性能指标</button>
                <button class="button" onclick="optimizeSystem()">优化系统</button>
                <div class="grid" id="performanceMetrics"></div>
            </div>
            
            <div class="section">
                <h2>🔧 系统管理</h2>
                <button class="button" onclick="getAgentRegistry()">查看智能体</button>
                <button class="button" onclick="getWorkflowTemplates()">工作流模板</button>
                <button class="button" onclick="getOptimizationRecommendations()">优化建议</button>
                <div id="managementResult" class="result"></div>
            </div>
            
            <div class="section">
                <h2>📡 实时监控 (WebSocket)</h2>
                <button class="button" onclick="connectWebSocket()">连接实时监控</button>
                <button class="button" onclick="disconnectWebSocket()">断开连接</button>
                <div id="websocketStatus" class="status info">未连接</div>
                <div id="realtimeData" class="result"></div>
            </div>
        </div>

        <script>
            let websocket = null;
            
            async function apiCall(endpoint, method = 'GET', data = null) {
                try {
                    const options = {
                        method: method,
                        headers: { 'Content-Type': 'application/json' }
                    };
                    if (data) options.body = JSON.stringify(data);
                    
                    const response = await fetch(endpoint, options);
                    return await response.json();
                } catch (error) {
                    return { error: error.message };
                }
            }
            
            function displayResult(elementId, data) {
                document.getElementById(elementId).textContent = JSON.stringify(data, null, 2);
            }
            
            async function checkSystemStatus() {
                const result = await apiCall('/api/system/status');
                displayResult('systemStatus', result);
            }
            
            async function healthCheck() {
                const result = await apiCall('/api/system/health');
                displayResult('systemStatus', result);
            }
            
            async function runBasicWorkflow() {
                document.getElementById('workflowResult').textContent = '正在执行基础工作流...';
                const result = await apiCall('/api/demo/basic-workflow', 'POST');
                displayResult('workflowResult', result);
            }
            
            async function runDataAnalysis() {
                document.getElementById('workflowResult').textContent = '正在执行数据分析...';
                const result = await apiCall('/api/demo/data-analysis', 'POST');
                displayResult('workflowResult', result);
            }
            
            async function runParallelProcessing() {
                document.getElementById('workflowResult').textContent = '正在执行并行处理...';
                const result = await apiCall('/api/demo/parallel-processing', 'POST');
                displayResult('workflowResult', result);
            }
            
            async function getPerformanceMetrics() {
                const result = await apiCall('/api/system/performance');
                
                if (result.error) {
                    displayResult('performanceMetrics', result);
                    return;
                }
                
                const metricsHtml = `
                    <div class="metric">
                        <div class="metric-value">${result.cache?.global_stats?.hit_rate || 0}%</div>
                        <div class="metric-label">缓存命中率</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${result.concurrent_executor?.current_load || 0}%</div>
                        <div class="metric-label">系统负载</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${result.concurrent_executor?.stats?.completed || 0}</div>
                        <div class="metric-label">完成任务</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${result.resource_pools?.summary?.total_resources || 0}</div>
                        <div class="metric-label">资源总数</div>
                    </div>
                `;
                document.getElementById('performanceMetrics').innerHTML = metricsHtml;
            }
            
            async function optimizeSystem() {
                const result = await apiCall('/api/system/optimize', 'POST');
                displayResult('performanceMetrics', result);
            }
            
            async function getAgentRegistry() {
                const result = await apiCall('/api/system/agents');
                displayResult('managementResult', result);
            }
            
            async function getWorkflowTemplates() {
                const result = await apiCall('/api/system/templates');
                displayResult('managementResult', result);
            }
            
            async function getOptimizationRecommendations() {
                const result = await apiCall('/api/system/recommendations');
                displayResult('managementResult', result);
            }
            
            function connectWebSocket() {
                if (websocket) return;
                
                websocket = new WebSocket(`ws://${window.location.host}/ws/monitor`);
                
                websocket.onopen = function() {
                    document.getElementById('websocketStatus').textContent = '✅ 已连接到实时监控';
                    document.getElementById('websocketStatus').className = 'status success';
                };
                
                websocket.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    document.getElementById('realtimeData').textContent = JSON.stringify(data, null, 2);
                };
                
                websocket.onclose = function() {
                    document.getElementById('websocketStatus').textContent = '❌ 连接已断开';
                    document.getElementById('websocketStatus').className = 'status error';
                    websocket = null;
                };
                
                websocket.onerror = function(error) {
                    document.getElementById('websocketStatus').textContent = '❌ 连接错误';
                    document.getElementById('websocketStatus').className = 'status error';
                };
            }
            
            function disconnectWebSocket() {
                if (websocket) {
                    websocket.close();
                    websocket = null;
                }
            }
            
            // 页面加载时自动检查系统状态
            window.onload = function() {
                checkSystemStatus();
            };
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# API路由
@app.get("/api/system/status")
async def get_system_status():
    """获取系统状态"""
    try:
        if not integrator:
            raise HTTPException(status_code=503, detail="系统未初始化")
        
        status = await integrator.get_system_status()
        return JSONResponse(content=status)
    
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/system/health")
async def system_health_check():
    """系统健康检查"""
    try:
        if not integrator:
            raise HTTPException(status_code=503, detail="系统未初始化")
        
        health = await integrator.system_health_check()
        return JSONResponse(content=health)
    
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/system/performance")
async def get_performance_metrics():
    """获取性能指标"""
    try:
        if not integrator:
            raise HTTPException(status_code=503, detail="系统未初始化")
        
        status = await integrator.get_system_status()
        performance = status.get("system_performance", {})
        return JSONResponse(content=performance)
    
    except Exception as e:
        logger.error(f"获取性能指标失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/system/optimize")
async def optimize_system():
    """优化系统"""
    try:
        if not integrator:
            raise HTTPException(status_code=503, detail="系统未初始化")
        
        result = await integrator.optimize_system_performance()
        return JSONResponse(content=result)
    
    except Exception as e:
        logger.error(f"系统优化失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/system/agents")
async def get_agent_registry():
    """获取智能体注册表"""
    try:
        if not integrator:
            raise HTTPException(status_code=503, detail="系统未初始化")
        
        agents = integrator.get_agent_registry()
        return JSONResponse(content=agents)
    
    except Exception as e:
        logger.error(f"获取智能体注册表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/system/templates")
async def get_workflow_templates():
    """获取工作流模板"""
    try:
        if not integrator:
            raise HTTPException(status_code=503, detail="系统未初始化")
        
        templates = integrator.get_workflow_templates()
        return JSONResponse(content=templates)
    
    except Exception as e:
        logger.error(f"获取工作流模板失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/system/recommendations")
async def get_optimization_recommendations():
    """获取优化建议"""
    try:
        if not integrator:
            raise HTTPException(status_code=503, detail="系统未初始化")
        
        recommendations = integrator.get_performance_recommendations()
        return JSONResponse(content=recommendations)
    
    except Exception as e:
        logger.error(f"获取优化建议失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 演示API
@app.post("/api/demo/basic-workflow")
async def demo_basic_workflow():
    """基础工作流演示"""
    try:
        if not integrator:
            raise HTTPException(status_code=503, detail="系统未初始化")
        
        # 创建演示工作流
        workflow_id = f"demo_basic_{int(datetime.now().timestamp())}"
        workflow = await integrator.create_workflow(workflow_id, "simple")
        
        # 执行演示任务
        task_input = {
            "task_id": f"demo_task_{int(datetime.now().timestamp())}",
            "title": "演示基础任务",
            "description": "这是一个演示用的基础任务",
            "requirements": ["处理输入", "生成输出"],
            "priority": 2
        }
        
        result = await integrator.execute_workflow(workflow_id, task_input)
        
        return JSONResponse(content={
            "status": "success",
            "workflow_id": workflow_id,
            "result": result,
            "message": "基础工作流演示完成"
        })
    
    except Exception as e:
        logger.error(f"基础工作流演示失败: {e}")
        return JSONResponse(content={
            "status": "error",
            "error": str(e)
        })


@app.post("/api/demo/data-analysis")
async def demo_data_analysis():
    """数据分析演示"""
    try:
        if not integrator:
            raise HTTPException(status_code=503, detail="系统未初始化")
        
        # 模拟数据分析任务
        workflow_id = f"demo_analysis_{int(datetime.now().timestamp())}"
        workflow = await integrator.create_workflow(workflow_id, "analysis")
        
        task_input = {
            "task_id": f"analysis_demo_{int(datetime.now().timestamp())}",
            "title": "演示数据分析",
            "description": "演示数据分析工作流",
            "task_type": "data_analysis",
            "data": {"sample": "demo_data"},
            "analysis_requirements": ["统计分析", "趋势分析", "报告生成"]
        }
        
        result = await integrator.execute_workflow(workflow_id, task_input)
        
        return JSONResponse(content={
            "status": "success",
            "workflow_id": workflow_id,
            "result": result,
            "message": "数据分析演示完成"
        })
    
    except Exception as e:
        logger.error(f"数据分析演示失败: {e}")
        return JSONResponse(content={
            "status": "error",
            "error": str(e)
        })


@app.post("/api/demo/parallel-processing")
async def demo_parallel_processing():
    """并行处理演示"""
    try:
        if not integrator:
            raise HTTPException(status_code=503, detail="系统未初始化")
        
        # 模拟并行处理任务
        workflow_id = f"demo_parallel_{int(datetime.now().timestamp())}"
        workflow = await integrator.create_workflow(workflow_id, "parallel")
        
        task_input = {
            "task_id": f"parallel_demo_{int(datetime.now().timestamp())}",
            "title": "演示并行处理",
            "description": "演示并行处理工作流",
            "task_type": "parallel_processing",
            "subtasks": [
                {"id": 1, "type": "process_a"},
                {"id": 2, "type": "process_b"},
                {"id": 3, "type": "process_c"}
            ]
        }
        
        result = await integrator.execute_workflow(workflow_id, task_input)
        
        return JSONResponse(content={
            "status": "success",
            "workflow_id": workflow_id,
            "result": result,
            "message": "并行处理演示完成"
        })
    
    except Exception as e:
        logger.error(f"并行处理演示失败: {e}")
        return JSONResponse(content={
            "status": "error",
            "error": str(e)
        })


# WebSocket监控
@app.websocket("/ws/monitor")
async def websocket_monitor(websocket: WebSocket):
    """WebSocket实时监控"""
    await websocket.accept()
    websocket_connections.append(websocket)
    
    try:
        while True:
            # 发送实时系统状态
            if integrator:
                status = await integrator.get_system_status()
                performance = status.get("system_performance", {})
                
                monitor_data = {
                    "timestamp": datetime.now().isoformat(),
                    "system_status": status.get("initialized", False),
                    "active_workflows": status.get("active_workflows", 0),
                    "performance": {
                        "cache_hit_rate": performance.get("cache", {}).get("global_stats", {}).get("hit_rate", 0),
                        "system_load": performance.get("concurrent_executor", {}).get("current_load", 0),
                        "completed_tasks": performance.get("concurrent_executor", {}).get("stats", {}).get("completed", 0)
                    }
                }
                
                await websocket.send_text(json.dumps(monitor_data))
            
            await asyncio.sleep(5)  # 每5秒发送一次更新
    
    except WebSocketDisconnect:
        websocket_connections.remove(websocket)
    except Exception as e:
        logger.error(f"WebSocket监控错误: {e}")
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)


def main():
    """主函数"""
    print("=" * 60)
    print("LangGraph多智能体系统演示服务器")
    print("=" * 60)
    print("启动服务器...")
    print("访问地址: http://localhost:8080")
    print("API文档: http://localhost:8080/docs")
    print("按 Ctrl+C 停止服务器")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    main()