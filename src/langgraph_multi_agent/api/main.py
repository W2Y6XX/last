"""API主模块 - 临时占位符"""

from fastapi import FastAPI


def create_app() -> FastAPI:
    """创建FastAPI应用 - 临时实现"""
    app = FastAPI(title="LangGraph Multi-Agent System")
    
    @app.get("/")
    async def root():
        return {"message": "LangGraph Multi-Agent System API"}
    
    return app