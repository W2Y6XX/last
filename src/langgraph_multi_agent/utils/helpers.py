"""辅助函数模块"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import json


def create_task_id() -> str:
    """创建唯一的任务ID"""
    return str(uuid.uuid4())


def generate_task_id() -> str:
    """生成唯一的任务ID（别名函数）"""
    return create_task_id()


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """格式化时间戳为ISO格式"""
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.isoformat()


def safe_json_serialize(obj: Any) -> str:
    """安全的JSON序列化"""
    def json_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)
    
    try:
        return json.dumps(obj, default=json_serializer, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"JSON序列化失败: {str(e)}"


def extract_error_info(error: Exception) -> Dict[str, Any]:
    """提取错误信息"""
    return {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "error_module": getattr(error, '__module__', 'unknown'),
        "timestamp": format_timestamp()
    }


def merge_dicts(*dicts: Dict[str, Any]) -> Dict[str, Any]:
    """合并多个字典"""
    result = {}
    for d in dicts:
        if d:
            result.update(d)
    return result


def validate_task_data(task_data: Dict[str, Any]) -> bool:
    """验证任务数据的基本结构"""
    required_fields = ["task_id", "title", "description"]
    return all(field in task_data for field in required_fields)


def calculate_complexity_score(task_data: Dict[str, Any]) -> float:
    """计算任务复杂度分数"""
    score = 0.0
    
    # 基于描述长度
    description = task_data.get("description", "")
    if len(description) > 500:
        score += 0.3
    elif len(description) > 200:
        score += 0.2
    else:
        score += 0.1
    
    # 基于需求数量
    requirements = task_data.get("requirements", [])
    if len(requirements) > 5:
        score += 0.3
    elif len(requirements) > 2:
        score += 0.2
    else:
        score += 0.1
    
    # 基于输入数据复杂度
    input_data = task_data.get("input_data", {})
    if len(input_data) > 10:
        score += 0.2
    elif len(input_data) > 5:
        score += 0.1
    
    # 基于优先级
    priority = task_data.get("priority", 1)
    if priority > 3:
        score += 0.2
    
    return min(score, 1.0)  # 确保分数不超过1.0