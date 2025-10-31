# LangGraph多智能体系统 - 综合功能测试

这是一个全面的测试系统，用于验证LangGraph多智能体系统的所有核心功能。

## 🎯 测试覆盖范围

### 测试套件

1. **健康检查测试套件** (`health_check`)
   - 后端服务健康状态
   - 前端页面访问
   - API端点可用性
   - 数据库连接状态
   - WebSocket连接测试

2. **前端测试套件** (`frontend_tests`)
   - 页面加载测试
   - 用户界面交互
   - 智能体管理界面
   - 任务创建功能
   - LLM配置界面

3. **API测试套件** (`api_tests`)
   - 系统管理API
   - 智能体管理API
   - 任务管理API
   - WebSocket API
   - 错误处理测试

4. **智能体系统测试套件** (`agent_tests`)
   - MetaAgent功能测试
   - TaskDecomposer测试
   - Coordinator测试
   - LLM集成测试

## 🚀 快速开始

### 安装依赖

```bash
pip install -r tests/comprehensive/requirements.txt
```

### 运行所有测试

```bash
python tests/comprehensive/run_comprehensive_tests.py
```

### 运行特定测试套件

```bash
# 只运行健康检查和API测试
python tests/comprehensive/run_comprehensive_tests.py --suites health_check api_tests

# 排除前端测试
python tests/comprehensive/run_comprehensive_tests.py --exclude frontend_tests
```

### 指定环境

```bash
# 开发环境（默认）
python tests/comprehensive/run_comprehensive_tests.py --env development

# 预发布环境
python tests/comprehensive/run_comprehensive_tests.py --env staging

# 生产环境
python tests/comprehensive/run_comprehensive_tests.py --env production
```

## ⚙️ 配置

### 环境配置

测试系统支持多环境配置：

- `development` - 开发环境（默认）
- `staging` - 预发布环境
- `production` - 生产环境

配置文件位于 `tests/comprehensive/config/` 目录。

### 自定义配置

```bash
# 使用自定义配置文件
python tests/comprehensive/run_comprehensive_tests.py --config my_config.json

# 覆盖特定配置
python tests/comprehensive/run_comprehensive_tests.py \
  --base-url http://localhost:8080 \
  --frontend-url http://localhost:3001 \
  --timeout 60
```

## 📊 测试报告

测试完成后会生成详细的测试报告，包括：

- 测试执行摘要
- 各测试套件结果
- 性能指标
- 失败详情
- 系统状态评估

报告保存在 `tests/comprehensive/reports/` 目录。

## 🔧 高级用法

### 并行执行

```bash
# 启用并行执行（提高速度）
python tests/comprehensive/run_comprehensive_tests.py --parallel

# 禁用并行执行（更稳定）
python tests/comprehensive/run_comprehensive_tests.py --no-parallel
```

### 日志控制

```bash
# 详细输出
python tests/comprehensive/run_comprehensive_tests.py --verbose

# 静默模式
python tests/comprehensive/run_comprehensive_tests.py --quiet
```

### 自定义报告

```bash
# 指定报告输出路径
python tests/comprehensive/run_comprehensive_tests.py --output my_report.json

# 不同报告格式
python tests/comprehensive/run_comprehensive_tests.py --format html
```

## 🏗️ 架构说明

### 目录结构

```
tests/comprehensive/
├── config/                 # 配置文件
│   ├── test_config.py     # 配置模型
│   ├── environments.py    # 环境配置
│   ├── development.json   # 开发环境配置
│   ├── staging.json       # 预发布环境配置
│   └── production.json    # 生产环境配置
├── core/                   # 核心框架
│   ├── test_controller.py # 测试控制器
│   ├── test_result.py     # 测试结果模型
│   └── test_status.py     # 测试状态管理
├── suites/                 # 测试套件
│   ├── health_check_suite.py
│   ├── frontend_test_suite.py
│   ├── api_test_suite.py
│   └── agent_test_suite.py
├── utils/                  # 工具模块
│   ├── helpers.py         # 辅助函数
│   ├── logging_utils.py   # 日志工具
│   └── data_utils.py      # 数据工具
├── logs/                   # 日志文件
├── reports/                # 测试报告
└── run_comprehensive_tests.py  # 主执行脚本
```

### 扩展测试套件

要添加新的测试套件：

1. 继承 `TestSuite` 基类
2. 实现 `run_all_tests()` 方法
3. 在主脚本中注册测试套件

```python
from tests.comprehensive.core.test_controller import TestSuite

class MyTestSuite(TestSuite):
    async def run_all_tests(self) -> TestSuiteResult:
        # 实现测试逻辑
        pass
```

## 🐛 故障排除

### 常见问题

1. **Chrome WebDriver不可用**
   ```bash
   # 安装Chrome和ChromeDriver
   # Ubuntu/Debian:
   sudo apt-get install google-chrome-stable
   
   # 或使用无头模式
   python run_comprehensive_tests.py --exclude frontend_tests
   ```

2. **网络连接问题**
   ```bash
   # 检查服务是否运行
   curl http://localhost:8000/health
   curl http://localhost:3000
   
   # 调整超时时间
   python run_comprehensive_tests.py --timeout 120
   ```

3. **权限问题**
   ```bash
   # 确保有写入权限
   chmod +w tests/comprehensive/logs/
   chmod +w tests/comprehensive/reports/
   ```

### 调试模式

```bash
# 启用详细日志
python run_comprehensive_tests.py --verbose

# 只运行健康检查
python run_comprehensive_tests.py --suites health_check
```

## 📈 性能优化

- 使用 `--parallel` 启用并行执行
- 排除不必要的测试套件
- 调整超时时间以适应网络环境
- 在CI/CD中使用无头模式

## 🤝 贡献指南

1. 添加新测试时，确保包含适当的错误处理
2. 使用模拟数据避免依赖外部服务
3. 添加详细的日志记录
4. 更新文档和配置示例

## 📄 许可证

本测试系统遵循与主项目相同的许可证。