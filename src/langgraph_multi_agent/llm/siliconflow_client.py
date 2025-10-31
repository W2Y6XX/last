"""硅基流动LLM客户端"""

import logging
import asyncio
import aiohttp
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class SiliconFlowClient:
    """硅基流动API客户端"""
    
    def __init__(
        self,
        api_key: str = "sk-wmxxamqdqsmscgrrmweqsqcieowsmqpxqwvenlelrxtkvmms",
        base_url: str = "https://api.siliconflow.cn/v1",
        model: str = "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: int = 60,
        max_retries: int = 3
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.max_retries = max_retries
        
        # 统计信息
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0
        }
        
        logger.info(f"硅基流动客户端初始化完成，模型: {self.model}")
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "LangGraph-MultiAgent/1.0.0"
        }
    
    async def _make_request(
        self, 
        endpoint: str, 
        data: Dict[str, Any],
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """发送API请求"""
        url = f"{self.base_url}/{endpoint}"
        headers = self._get_headers()
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(url, headers=headers, json=data) as response:
                    response_data = await response.json()
                    
                    if response.status == 200:
                        self.stats["successful_requests"] += 1
                        return response_data
                    else:
                        error_msg = response_data.get("error", {}).get("message", "未知错误")
                        raise Exception(f"API请求失败 (状态码: {response.status}): {error_msg}")
        
        except Exception as e:
            self.stats["failed_requests"] += 1
            
            if retry_count < self.max_retries:
                wait_time = 2 ** retry_count  # 指数退避
                logger.warning(f"请求失败，{wait_time}秒后重试 (第{retry_count + 1}次): {e}")
                await asyncio.sleep(wait_time)
                return await self._make_request(endpoint, data, retry_count + 1)
            else:
                logger.error(f"请求最终失败: {e}")
                raise
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """聊天完成API调用"""
        
        self.stats["total_requests"] += 1
        
        # 准备请求数据
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
            "stream": stream,
            **kwargs
        }
        
        try:
            start_time = time.time()
            response = await self._make_request("chat/completions", data)
            end_time = time.time()
            
            # 更新统计信息
            if "usage" in response:
                usage = response["usage"]
                self.stats["total_tokens"] += usage.get("total_tokens", 0)
            
            # 添加响应时间
            response["_response_time"] = end_time - start_time
            
            logger.debug(f"聊天完成请求成功，耗时: {end_time - start_time:.3f}秒")
            
            return response
            
        except Exception as e:
            logger.error(f"聊天完成请求失败: {e}")
            raise
    
    async def simple_chat(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        **kwargs
    ) -> str:
        """简单聊天接口"""
        
        messages = []
        
        if system_message:
            messages.append({"role": "system", "content": system_message})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = await self.chat_completion(messages, **kwargs)
            
            if "choices" in response and len(response["choices"]) > 0:
                return response["choices"][0]["message"]["content"]
            else:
                raise Exception("响应格式错误：未找到choices")
                
        except Exception as e:
            logger.error(f"简单聊天请求失败: {e}")
            raise
    
    async def batch_chat(
        self,
        prompts: List[str],
        system_message: Optional[str] = None,
        max_concurrent: int = 5,
        **kwargs
    ) -> List[str]:
        """批量聊天请求"""
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single_prompt(prompt: str) -> str:
            async with semaphore:
                return await self.simple_chat(prompt, system_message, **kwargs)
        
        try:
            results = await asyncio.gather(
                *[process_single_prompt(prompt) for prompt in prompts],
                return_exceptions=True
            )
            
            # 处理异常结果
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"批量请求第{i}个失败: {result}")
                    processed_results.append(f"错误: {str(result)}")
                else:
                    processed_results.append(result)
            
            return processed_results
            
        except Exception as e:
            logger.error(f"批量聊天请求失败: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        success_rate = (
            self.stats["successful_requests"] / self.stats["total_requests"]
            if self.stats["total_requests"] > 0 else 0
        )
        
        return {
            **self.stats,
            "success_rate": success_rate,
            "model": self.model,
            "base_url": self.base_url
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0
        }
        logger.info("统计信息已重置")


# 全局客户端实例
_global_client: Optional[SiliconFlowClient] = None


def get_llm_client() -> SiliconFlowClient:
    """获取全局LLM客户端实例"""
    global _global_client
    
    if _global_client is None:
        _global_client = SiliconFlowClient()
    
    return _global_client


def set_llm_client(client: SiliconFlowClient):
    """设置全局LLM客户端实例"""
    global _global_client
    _global_client = client


# 便捷函数
async def chat(prompt: str, system_message: Optional[str] = None, **kwargs) -> str:
    """便捷的聊天函数"""
    client = get_llm_client()
    return await client.simple_chat(prompt, system_message, **kwargs)


async def batch_chat(
    prompts: List[str], 
    system_message: Optional[str] = None, 
    **kwargs
) -> List[str]:
    """便捷的批量聊天函数"""
    client = get_llm_client()
    return await client.batch_chat(prompts, system_message, **kwargs)


def get_llm_stats() -> Dict[str, Any]:
    """获取LLM使用统计"""
    client = get_llm_client()
    return client.get_stats()