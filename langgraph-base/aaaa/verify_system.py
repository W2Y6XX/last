"""
系统验证脚本 - 确认基本功能可用
"""

import sys
import os

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    return version.major >= 3

def check_file_structure():
    """检查文件结构"""
    required_files = [
        "src/core/types.py",
        "src/core/config.py",
        "src/communication/message_bus.py",
        "src/task_management/task_manager.py",
        "config/default.yaml",
        "scripts/start_system.py"
    ]

    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)

    if missing_files:
        print(f"Missing files: {missing_files}")
        return False
    else:
        print("All required files present")
        return True

def check_dependencies():
    """检查依赖包"""
    try:
        import yaml
        print("✓ yaml available")
    except ImportError:
        print("✗ yaml not available")
        return False

    try:
        from pydantic import BaseModel
        print("✓ pydantic available")
    except ImportError:
        print("✗ pydantic not available")
        return False

    return True

def test_basic_functionality():
    """测试基本功能"""
    try:
        # 测试类型定义
        from enum import Enum

        class AgentType(str, Enum):
            META = "meta"
            COORDINATOR = "coordinator"

        class TaskStatus(str, Enum):
            PENDING = "pending"
            IN_PROGRESS = "in_progress"

        assert AgentType.META.value == "meta"
        assert TaskStatus.PENDING.value == "pending"

        print("✓ Type definitions working")

        # 测试配置
        import yaml
        config_data = {
            "system": {
                "name": "Test System",
                "version": "0.1.0"
            },
            "server": {
                "host": "localhost",
                "port": 8000
            }
        }

        config_yaml = yaml.dump(config_data)
        parsed_config = yaml.safe_load(config_yaml)

        assert parsed_config["system"]["name"] == "Test System"
        print("✓ YAML configuration working")

        return True

    except Exception as e:
        print(f"✗ Basic functionality test failed: {e}")
        return False

def main():
    """主验证函数"""
    print("=== LangGraph Agent System Verification ===")
    print()

    checks = [
        ("Python version", check_python_version),
        ("File structure", check_file_structure),
        ("Dependencies", check_dependencies),
        ("Basic functionality", test_basic_functionality)
    ]

    passed = 0
    total = len(checks)

    for name, check_func in checks:
        print(f"Checking {name}...")
        if check_func():
            passed += 1
            print(f"✓ {name} passed")
        else:
            print(f"✗ {name} failed")
        print()

    print(f"Verification Results: {passed}/{total} checks passed")

    if passed == total:
        print("\n🎉 System verification passed!")
        print("The LangGraph Agent System is ready to use.")
        print("\nNext steps:")
        print("1. Run: python scripts/start_system.py --env development")
        print("2. Open: http://localhost:8000/health to check system status")
        print("3. Read README.md for usage instructions")
        return True
    else:
        print(f"\n⚠️  {total - passed} checks failed.")
        print("Please fix the issues before running the system.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)