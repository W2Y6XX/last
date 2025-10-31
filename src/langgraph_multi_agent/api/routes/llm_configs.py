"""大模型配置管理API路由"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import asyncio

from fastapi import APIRouter, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field

from ..models import ApiResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# 大模型配置数据模型
class LLMConfigCreate(BaseModel):
    """创建大模型配置请求"""
    name: str = Field(..., min_length=1, max_length=100, description="配置名称")
    provider: str = Field(..., description="提供商：siliconflow, openai, anthropic, local")
    settings: Dict[str, Any] = Field(..., description="配置参数")

class LLMConfigUpdate(BaseModel):
    """更新大模型配置请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="配置名称")
    settings: Optional[Dict[str, Any]] = Field(None, description="配置参数")

class LLMConfigResponse(BaseModel):
    """大模型配置响应"""
    id: str = Field(..., description="配置ID")
    name: str = Field(..., description="配置名称")
    provider: str = Field(..., description="提供商")
    settings: Dict[str, Any] = Field(..., description="配置参数")
    is_active: bool = Field(..., description="是否激活")
    test_result: Optional[Dict[str, Any]] = Field(None, description="测试结果")
    usage: Dict[str, Any] = Field(..., description="使用统计")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

# 模拟配置存储
llm_configs_storage = {}
active_config_id = None

@router.get("/", response_model=ApiResponse)
async def list_llm_configs():
    """获取大模型配置列表"""
    try:
        configs = list(llm_configs_storage.values())
        return ApiResponse(
            success=True,
            message="获取配置列表成功",
            data={
                "configs": configs,
                "active_config_id": active_config_id,
                "total": len(configs)
            }
        )
    except Exception as e:
        logger.error(f"获取配置列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置列表失败: {str(e)}")


@router.post("/", response_model=ApiResponse)
async def create_llm_config(config: LLMConfigCreate):
    """创建大模型配置"""
    try:
        config_id = f"config_{len(llm_configs_storage) + 1}_{int(datetime.now().timestamp())}"
        
        new_config = {
            "id": config_id,
            "name": config.name,
            "provider": config.provider,
            "settings": config.settings,
            "is_active": False,
            "test_result": None,
            "usage": {
                "total_requests": 0,
                "successful_requests": 0,
                "total_tokens": 0,
                "total_cost": 0.0
            },
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        llm_configs_storage[config_id] = new_config
        
        return ApiResponse(
            success=True,
            message="创建配置成功",
            data={"config_id": config_id}
        )
    except Exception as e:
        logger.error(f"创建配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建配置失败: {str(e)}")

@router.get("/{config_id}", response_model=ApiResponse)
async def get_llm_config(config_id: str = Path(..., description="配置ID")):
    """获取指定配置详情"""
    try:
        if config_id not in llm_configs_storage:
            raise HTTPException(status_code=404, detail=f"配置 {config_id} 不存在")
        
        config = llm_configs_storage[config_id]
        return ApiResponse(
            success=True,
            message="获取配置成功",
            data=config
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")

@router.put("/{config_id}", response_model=ApiResponse)
async def update_llm_config(
    config_id: str = Path(..., description="配置ID"),
    config_update: LLMConfigUpdate = Body(...)
):
    """更新大模型配置"""
    try:
        if config_id not in llm_configs_storage:
            raise HTTPException(status_code=404, detail=f"配置 {config_id} 不存在")
        
        config = llm_configs_storage[config_id]
        
        if config_update.name is not None:
            config["name"] = config_update.name
        if config_update.settings is not None:
            config["settings"].update(config_update.settings)
        
        config["updated_at"] = datetime.now()
        
        return ApiResponse(
            success=True,
            message="更新配置成功",
            data=config
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


@router.delete("/{config_id}", response_model=ApiResponse)
async def delete_llm_config(config_id: str = Path(..., description="配置ID")):
    """删除大模型配置"""
    try:
        global active_config_id
        
        if config_id not in llm_configs_storage:
            raise HTTPException(status_code=404, detail=f"配置 {config_id} 不存在")
        
        # 如果删除的是激活配置，清除激活状态
        if active_config_id == config_id:
            active_config_id = None
        
        del llm_configs_storage[config_id]
        
        return ApiResponse(
            success=True,
            message="删除配置成功",
            data={"deleted_config_id": config_id}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除配置失败: {str(e)}")

@router.post("/{config_id}/test", response_model=ApiResponse)
async def test_llm_config(config_id: str = Path(..., description="配置ID")):
    """测试大模型配置连接"""
    try:
        if config_id not in llm_configs_storage:
            raise HTTPException(status_code=404, detail=f"配置 {config_id} 不存在")
        
        config = llm_configs_storage[config_id]
        
        # 模拟测试连接
        await asyncio.sleep(0.5)  # 模拟网络延迟
        
        # 根据提供商进行不同的测试逻辑
        provider = config["provider"]
        settings = config["settings"]
        
        test_result = {
            "is_valid": True,
            "response_time": 0.5,
            "error_message": None,
            "last_tested": datetime.now(),
            "test_details": {
                "provider": provider,
                "model": settings.get("model", "unknown"),
                "api_endpoint": settings.get("base_url", "default")
            }
        }
        
        # 简单的验证逻辑
        if not settings.get("api_key"):
            test_result["is_valid"] = False
            test_result["error_message"] = "API密钥未配置"
        elif provider not in ["siliconflow", "openai", "anthropic", "local"]:
            test_result["is_valid"] = False
            test_result["error_message"] = "不支持的提供商"
        
        # 更新配置的测试结果
        config["test_result"] = test_result
        config["updated_at"] = datetime.now()
        
        return ApiResponse(
            success=True,
            message="配置测试完成",
            data=test_result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"测试配置失败: {str(e)}")


@router.post("/{config_id}/activate", response_model=ApiResponse)
async def activate_llm_config(config_id: str = Path(..., description="配置ID")):
    """激活大模型配置"""
    try:
        global active_config_id
        
        if config_id not in llm_configs_storage:
            raise HTTPException(status_code=404, detail=f"配置 {config_id} 不存在")
        
        # 取消之前的激活配置
        if active_config_id and active_config_id in llm_configs_storage:
            llm_configs_storage[active_config_id]["is_active"] = False
        
        # 激活新配置
        llm_configs_storage[config_id]["is_active"] = True
        llm_configs_storage[config_id]["updated_at"] = datetime.now()
        active_config_id = config_id
        
        return ApiResponse(
            success=True,
            message="配置激活成功",
            data={
                "active_config_id": config_id,
                "config_name": llm_configs_storage[config_id]["name"]
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"激活配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"激活配置失败: {str(e)}")

@router.get("/{config_id}/usage", response_model=ApiResponse)
async def get_config_usage(config_id: str = Path(..., description="配置ID")):
    """获取配置使用统计"""
    try:
        if config_id not in llm_configs_storage:
            raise HTTPException(status_code=404, detail=f"配置 {config_id} 不存在")
        
        config = llm_configs_storage[config_id]
        usage_stats = config["usage"]
        
        # 计算成功率
        success_rate = 0.0
        if usage_stats["total_requests"] > 0:
            success_rate = usage_stats["successful_requests"] / usage_stats["total_requests"]
        
        detailed_usage = {
            **usage_stats,
            "success_rate": success_rate,
            "average_cost_per_request": (
                usage_stats["total_cost"] / usage_stats["total_requests"] 
                if usage_stats["total_requests"] > 0 else 0.0
            ),
            "config_name": config["name"],
            "provider": config["provider"]
        }
        
        return ApiResponse(
            success=True,
            message="获取使用统计成功",
            data=detailed_usage
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取使用统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取使用统计失败: {str(e)}")

@router.post("/{config_id}/usage/update", response_model=ApiResponse)
async def update_config_usage(
    config_id: str = Path(..., description="配置ID"),
    usage_data: Dict[str, Any] = Body(..., description="使用数据")
):
    """更新配置使用统计"""
    try:
        if config_id not in llm_configs_storage:
            raise HTTPException(status_code=404, detail=f"配置 {config_id} 不存在")
        
        config = llm_configs_storage[config_id]
        usage = config["usage"]
        
        # 更新统计数据
        if "requests" in usage_data:
            usage["total_requests"] += usage_data["requests"]
        if "successful_requests" in usage_data:
            usage["successful_requests"] += usage_data["successful_requests"]
        if "tokens" in usage_data:
            usage["total_tokens"] += usage_data["tokens"]
        if "cost" in usage_data:
            usage["total_cost"] += usage_data["cost"]
        
        config["updated_at"] = datetime.now()
        
        return ApiResponse(
            success=True,
            message="更新使用统计成功",
            data=usage
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新使用统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新使用统计失败: {str(e)}")