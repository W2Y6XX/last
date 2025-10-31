"""
测试数据工具
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import random
import string


class TestDataGenerator:
    """测试数据生成器"""
    
    @staticmethod
    def generate_task_data(task_type: str = "test", 
                          complexity: str = "simple") -> Dict[str, Any]:
        """生成任务测试数据"""
        task_id = str(uuid.uuid4())
        
        base_data = {
            "task_id": task_id,
            "title": f"测试任务_{task_id[:8]}",
            "description": f"这是一个{complexity}的{task_type}类型测试任务",
            "task_type": task_type,
            "priority": random.randint(1, 5),
            "created_at": datetime.now().isoformat(),
            "status": "pending"
        }
        
        if complexity == "simple":
            base_data.update({
                "requirements": ["基本功能测试"],
                "constraints": ["5分钟内完成"],
                "estimated_duration": 300
            })
        elif complexity == "medium":
            base_data.update({
                "requirements": ["功能测试", "性能测试"],
                "constraints": ["15分钟内完成", "内存使用不超过500MB"],
                "estimated_duration": 900,
                "subtasks": [
                    {"name": "子任务1", "status": "pending"},
                    {"name": "子任务2", "status": "pending"}
                ]
            })
        elif complexity == "complex":
            base_data.update({
                "requirements": ["功能测试", "性能测试", "集成测试", "安全测试"],
                "constraints": ["30分钟内完成", "内存使用不超过1GB", "CPU使用不超过80%"],
                "estimated_duration": 1800,
                "subtasks": [
                    {"name": "子任务1", "status": "pending"},
                    {"name": "子任务2", "status": "pending"},
                    {"name": "子任务3", "status": "pending"},
                    {"name": "子任务4", "status": "pending"}
                ],
                "dependencies": ["external_service", "database"]
            })
        
        return base_data
    
    @staticmethod
    def generate_user_data() -> Dict[str, Any]:
        """生成用户测试数据"""
        user_id = str(uuid.uuid4())
        
        return {
            "user_id": user_id,
            "username": f"test_user_{user_id[:8]}",
            "email": f"test_{user_id[:8]}@example.com",
            "role": random.choice(["user", "admin", "tester"]),
            "created_at": datetime.now().isoformat(),
            "active": True,
            "preferences": {
                "language": "zh-CN",
                "theme": "light",
                "notifications": True
            }
        }
    
    @staticmethod
    def generate_agent_data(agent_type: str = "meta_agent") -> Dict[str, Any]:
        """生成智能体测试数据"""
        agent_id = str(uuid.uuid4())
        
        return {
            "agent_id": agent_id,
            "name": f"{agent_type}_{agent_id[:8]}",
            "type": agent_type,
            "status": "active",
            "capabilities": [
                "task_analysis",
                "requirement_processing",
                "response_generation"
            ],
            "configuration": {
                "model": "test_model",
                "temperature": 0.7,
                "max_tokens": 1000
            },
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat()
        }
    
    @staticmethod
    def generate_performance_data(metric_name: str, 
                                count: int = 100) -> List[Dict[str, Any]]:
        """生成性能测试数据"""
        data = []
        base_time = datetime.now()
        
        for i in range(count):
            timestamp = base_time + timedelta(seconds=i)
            
            if metric_name == "response_time":
                value = random.uniform(0.1, 2.0)  # 100ms to 2s
            elif metric_name == "memory_usage":
                value = random.uniform(100, 800)  # 100MB to 800MB
            elif metric_name == "cpu_usage":
                value = random.uniform(10, 90)    # 10% to 90%
            elif metric_name == "throughput":
                value = random.uniform(50, 200)   # 50 to 200 requests/sec
            else:
                value = random.uniform(0, 100)
            
            data.append({
                "timestamp": timestamp.isoformat(),
                "metric": metric_name,
                "value": value,
                "unit": TestDataGenerator._get_metric_unit(metric_name)
            })
        
        return data
    
    @staticmethod
    def _get_metric_unit(metric_name: str) -> str:
        """获取指标单位"""
        units = {
            "response_time": "ms",
            "memory_usage": "MB",
            "cpu_usage": "%",
            "throughput": "req/s",
            "error_rate": "%",
            "success_rate": "%"
        }
        return units.get(metric_name, "")
    
    @staticmethod
    def generate_random_string(length: int = 10) -> str:
        """生成随机字符串"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    @staticmethod
    def generate_test_dataset(size: int = 100) -> List[Dict[str, Any]]:
        """生成测试数据集"""
        dataset = []
        
        for i in range(size):
            data_type = random.choice(["task", "user", "agent"])
            
            if data_type == "task":
                complexity = random.choice(["simple", "medium", "complex"])
                data = TestDataGenerator.generate_task_data(complexity=complexity)
            elif data_type == "user":
                data = TestDataGenerator.generate_user_data()
            else:
                agent_type = random.choice(["meta_agent", "coordinator", "task_decomposer"])
                data = TestDataGenerator.generate_agent_data(agent_type)
            
            data["dataset_index"] = i
            dataset.append(data)
        
        return dataset


class TestDataManager:
    """测试数据管理器"""
    
    def __init__(self, data_dir: str = "tests/comprehensive/data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.generator = TestDataGenerator()
    
    def save_test_data(self, data: Union[Dict, List], filename: str) -> str:
        """保存测试数据到文件"""
        file_path = self.data_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        return str(file_path)
    
    def load_test_data(self, filename: str) -> Union[Dict, List]:
        """从文件加载测试数据"""
        file_path = self.data_dir / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"Test data file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def create_sample_dataset(self, name: str, size: int = 50) -> str:
        """创建示例数据集"""
        dataset = self.generator.generate_test_dataset(size)
        filename = f"{name}_dataset.json"
        return self.save_test_data(dataset, filename)
    
    def cleanup_test_data(self, pattern: str = "test_*"):
        """清理测试数据"""
        for file_path in self.data_dir.glob(pattern):
            if file_path.is_file():
                file_path.unlink()
    
    def get_data_summary(self) -> Dict[str, Any]:
        """获取数据摘要"""
        files = list(self.data_dir.glob("*.json"))
        
        summary = {
            "total_files": len(files),
            "files": [],
            "total_size": 0
        }
        
        for file_path in files:
            file_size = file_path.stat().st_size
            summary["total_size"] += file_size
            
            summary["files"].append({
                "name": file_path.name,
                "size": file_size,
                "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            })
        
        return summary


def create_mock_response(status_code: int = 200, 
                        data: Optional[Dict[str, Any]] = None,
                        headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """创建模拟HTTP响应"""
    response = {
        "status_code": status_code,
        "headers": headers or {"Content-Type": "application/json"},
        "timestamp": datetime.now().isoformat()
    }
    
    if data is not None:
        response["data"] = data
    elif status_code == 200:
        response["data"] = {"message": "Success", "status": "ok"}
    elif status_code >= 400:
        response["data"] = {"error": "Test error", "status": "error"}
    
    return response


def validate_test_data(data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """验证测试数据格式"""
    errors = []
    
    # 检查必需字段
    required_fields = schema.get("required", [])
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")
    
    # 检查字段类型
    field_types = schema.get("types", {})
    for field, expected_type in field_types.items():
        if field in data:
            actual_type = type(data[field]).__name__
            if actual_type != expected_type:
                errors.append(f"Field {field} should be {expected_type}, got {actual_type}")
    
    return errors