# LangGraph多智能体系统部署指南

## 概述

本文档提供LangGraph多智能体系统的完整部署指南，包括本地开发环境、测试环境和生产环境的部署方法。系统基于LangGraph框架构建，集成了多个智能体组件，支持MVP2前端集成，提供完整的任务管理和智能体协作功能。

## 版本信息

- **系统版本**: v1.0.0
- **LangGraph版本**: 1.0.1+
- **Python版本**: 3.9+
- **文档更新日期**: 2024年10月26日

## 系统要求

### 最低硬件要求

- **CPU**: 4核心
- **内存**: 8GB RAM
- **存储**: 50GB可用空间
- **网络**: 稳定的互联网连接

### 推荐硬件配置

- **CPU**: 8核心或更多
- **内存**: 16GB RAM或更多
- **存储**: 100GB SSD
- **网络**: 高速网络连接

### 软件依赖

- **操作系统**: Linux (Ubuntu 20.04+), macOS, Windows 10+
- **Python**: 3.9+
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Kubernetes**: 1.24+ (生产环境)
- **kubectl**: 1.24+

## 部署方式

### 1. 本地开发环境部署

#### 使用Docker Compose

```bash
# 克隆项目
git clone <repository-url>
cd langgraph-multi-agent

# 复制环境变量文件
cp .env.example .env

# 编辑环境变量
nano .env

# 启动服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

#### 直接运行

```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export PYTHONPATH=$PWD
export DATABASE_URL="sqlite:///./data/app.db"
export REDIS_URL="redis://localhost:6379/0"

# 启动Redis (如果需要)
redis-server

# 启动应用
python -m uvicorn langgraph_multi_agent.api.app:create_app --factory --reload
```

### 2. 生产环境部署

#### 使用部署脚本

```bash
# 赋予执行权限
chmod +x scripts/deploy.sh

# 部署到生产环境
./scripts/deploy.sh prod -v v1.0.0

# 查看部署状态
kubectl get pods -n langgraph-multi-agent
```

#### 手动Kubernetes部署

```bash
# 创建命名空间
kubectl apply -f k8s/namespace.yaml

# 应用配置
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml

# 创建存储
kubectl apply -f k8s/pvc.yaml

# 部署应用
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

# 配置自动扩缩容
kubectl apply -f k8s/hpa.yaml

# 等待部署完成
kubectl rollout status deployment/langgraph-multi-agent -n langgraph-multi-agent
```

## 环境配置

### 环境变量配置

创建 `.env` 文件并配置以下变量：

```bash
# 应用配置
ENVIRONMENT=production
LOG_LEVEL=info
API_HOST=0.0.0.0
API_PORT=8000

# 数据库配置
DATABASE_URL=postgresql://user:password@localhost:5432/langgraph_db
REDIS_URL=redis://localhost:6379/0

# LangSmith配置
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=langgraph-multi-agent

# 安全配置
JWT_SECRET_KEY=your_jwt_secret_key
AUTH_SECRET_KEY=your_auth_secret_key

# CORS配置
CORS_ORIGINS=["http://localhost:3000", "https://yourdomain.com"]

# 监控配置
ENABLE_METRICS=true
ENABLE_TRACING=true

# MVP2前端配置
MVP2_FRONTEND_URL=http://localhost:80/mvp2
```

### Kubernetes Secret配置

```bash
# 创建数据库密码Secret
kubectl create secret generic langgraph-secrets \
  --from-literal=POSTGRES_PASSWORD=your_postgres_password \
  --from-literal=LANGSMITH_API_KEY=your_langsmith_api_key \
  --from-literal=JWT_SECRET_KEY=your_jwt_secret_key \
  -n langgraph-multi-agent

# 创建TLS证书Secret (如果使用HTTPS)
kubectl create secret tls langgraph-tls \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key \
  -n langgraph-multi-agent
```

## 数据库初始化

### PostgreSQL初始化

```sql
-- 创建数据库
CREATE DATABASE langgraph_db;

-- 创建用户
CREATE USER langgraph_user WITH PASSWORD 'langgraph_password';

-- 授予权限
GRANT ALL PRIVILEGES ON DATABASE langgraph_db TO langgraph_user;

-- 创建扩展
\c langgraph_db
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
```

### 数据库迁移

```bash
# 运行数据库迁移
python -m alembic upgrade head

# 创建初始数据
python scripts/init_data.py
```

## 服务验证

### 健康检查

```bash
# API健康检查
curl -f http://localhost:8000/health

# MVP2适配器健康检查
curl -f http://localhost:8000/api/v1/mvp2/health

# 数据库连接检查
curl -f http://localhost:8000/api/v1/system/db-status

# Redis连接检查
curl -f http://localhost:8000/api/v1/system/redis-status
```

### 功能测试

```bash
# 创建测试任务
curl -X POST http://localhost:8000/api/v1/mvp2/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试任务",
    "description": "这是一个测试任务",
    "priority": "中",
    "deadline": "2024-12-31",
    "assignee": "测试用户"
  }'

# 获取任务列表
curl http://localhost:8000/api/v1/mvp2/tasks

# 测试WebSocket连接
wscat -c ws://localhost:8000/api/v1/mvp2/ws
```

## 监控配置

### Prometheus配置

```bash
# 访问Prometheus
http://localhost:9090

# 检查目标状态
http://localhost:9090/targets

# 查看指标
http://localhost:9090/graph
```

### Grafana配置

```bash
# 访问Grafana
http://localhost:3000

# 默认登录信息
用户名: admin
密码: admin (首次登录后需要修改)

# 导入仪表板
1. 点击 "+" -> Import
2. 上传 monitoring/grafana/dashboards/langgraph-dashboard.json
3. 配置数据源为 Prometheus (http://prometheus:9090)
```

### 日志配置

```bash
# 访问Kibana
http://localhost:5601

# 创建索引模式
1. 进入 Management -> Index Patterns
2. 创建索引模式: langgraph-multi-agent-*
3. 选择时间字段: @timestamp
```

## 扩容配置

### 水平扩容

```bash
# 手动扩容
kubectl scale deployment langgraph-multi-agent --replicas=5 -n langgraph-multi-agent

# 查看扩容状态
kubectl get pods -n langgraph-multi-agent

# 配置HPA自动扩容
kubectl apply -f k8s/hpa.yaml
```

### 垂直扩容

```yaml
# 修改 k8s/deployment.yaml 中的资源限制
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

## 备份和恢复

### 数据库备份

```bash
# 创建备份
kubectl exec -it postgres-pod -n langgraph-multi-agent -- \
  pg_dump -U langgraph_user langgraph_db > backup.sql

# 恢复备份
kubectl exec -i postgres-pod -n langgraph-multi-agent -- \
  psql -U langgraph_user langgraph_db < backup.sql
```

### 配置备份

```bash
# 备份Kubernetes配置
kubectl get all -n langgraph-multi-agent -o yaml > k8s-backup.yaml

# 备份ConfigMap和Secret
kubectl get configmap,secret -n langgraph-multi-agent -o yaml > config-backup.yaml
```

## 安全配置

### 网络安全

```yaml
# 网络策略示例
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: langgraph-network-policy
  namespace: langgraph-multi-agent
spec:
  podSelector:
    matchLabels:
      app: langgraph-multi-agent
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: nginx-ingress
    ports:
    - protocol: TCP
      port: 8000
```

### RBAC配置

```yaml
# ServiceAccount
apiVersion: v1
kind: ServiceAccount
metadata:
  name: langgraph-service-account
  namespace: langgraph-multi-agent

---
# Role
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: langgraph-role
  namespace: langgraph-multi-agent
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps"]
  verbs: ["get", "list", "watch"]

---
# RoleBinding
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: langgraph-role-binding
  namespace: langgraph-multi-agent
subjects:
- kind: ServiceAccount
  name: langgraph-service-account
  namespace: langgraph-multi-agent
roleRef:
  kind: Role
  name: langgraph-role
  apiGroup: rbac.authorization.k8s.io
```

## 故障排查

### 常见问题

1. **应用启动失败**
   ```bash
   # 查看Pod日志
   kubectl logs -f deployment/langgraph-multi-agent -n langgraph-multi-agent
   
   # 查看Pod事件
   kubectl describe pod <pod-name> -n langgraph-multi-agent
   ```

2. **数据库连接失败**
   ```bash
   # 检查数据库服务
   kubectl get svc postgres -n langgraph-multi-agent
   
   # 测试数据库连接
   kubectl exec -it <app-pod> -n langgraph-multi-agent -- \
     psql -h postgres -U langgraph_user -d langgraph_db
   ```

3. **Redis连接失败**
   ```bash
   # 检查Redis服务
   kubectl get svc redis -n langgraph-multi-agent
   
   # 测试Redis连接
   kubectl exec -it <app-pod> -n langgraph-multi-agent -- \
     redis-cli -h redis ping
   ```

4. **Ingress访问失败**
   ```bash
   # 检查Ingress状态
   kubectl get ingress -n langgraph-multi-agent
   
   # 查看Ingress控制器日志
   kubectl logs -f -n nginx-ingress deployment/nginx-ingress-controller
   ```

### 性能调优

1. **数据库优化**
   ```sql
   -- 创建索引
   CREATE INDEX idx_tasks_status ON tasks(status);
   CREATE INDEX idx_tasks_created_at ON tasks(created_at);
   
   -- 分析查询性能
   EXPLAIN ANALYZE SELECT * FROM tasks WHERE status = 'pending';
   ```

2. **Redis优化**
   ```bash
   # 配置Redis内存策略
   redis-cli CONFIG SET maxmemory-policy allkeys-lru
   
   # 监控Redis性能
   redis-cli --latency-history
   ```

3. **应用优化**
   ```python
   # 启用连接池
   DATABASE_POOL_SIZE=20
   DATABASE_MAX_OVERFLOW=30
   
   # 配置异步处理
   ASYNC_WORKERS=4
   TASK_QUEUE_SIZE=1000
   ```

## 更新和升级

### 滚动更新

```bash
# 更新镜像
kubectl set image deployment/langgraph-multi-agent \
  langgraph-multi-agent=langgraph-multi-agent:v1.1.0 \
  -n langgraph-multi-agent

# 查看更新状态
kubectl rollout status deployment/langgraph-multi-agent -n langgraph-multi-agent

# 回滚更新
kubectl rollout undo deployment/langgraph-multi-agent -n langgraph-multi-agent
```

### 蓝绿部署

```bash
# 创建新版本部署
kubectl apply -f k8s/deployment-v2.yaml

# 切换流量
kubectl patch service langgraph-multi-agent-service \
  -p '{"spec":{"selector":{"version":"v2"}}}' \
  -n langgraph-multi-agent

# 清理旧版本
kubectl delete deployment langgraph-multi-agent-v1 -n langgraph-multi-agent
```

## 部署验证清单

### 部署前检查清单

- [ ] 确认硬件资源满足最低要求
- [ ] 验证所有依赖软件已正确安装
- [ ] 检查网络连接和防火墙配置
- [ ] 准备所有必需的配置文件和密钥
- [ ] 备份现有数据（如果是升级部署）

### 部署后验证清单

- [ ] 所有Pod/容器状态正常
- [ ] API健康检查通过
- [ ] 数据库连接正常
- [ ] Redis缓存服务可用
- [ ] WebSocket连接正常
- [ ] MVP2前端集成功能正常
- [ ] 监控和日志系统工作正常
- [ ] 告警规则配置正确
- [ ] 备份策略已启用

### 性能验证清单

- [ ] API响应时间在可接受范围内（< 2秒）
- [ ] 并发用户测试通过
- [ ] 内存使用率正常（< 80%）
- [ ] CPU使用率正常（< 70%）
- [ ] 数据库查询性能正常
- [ ] 缓存命中率达到预期

## 部署最佳实践

### 1. 环境隔离

```bash
# 使用不同的命名空间隔离环境
kubectl create namespace langgraph-dev
kubectl create namespace langgraph-staging  
kubectl create namespace langgraph-prod

# 为每个环境设置资源配额
kubectl apply -f - <<EOF
apiVersion: v1
kind: ResourceQuota
metadata:
  name: compute-quota
  namespace: langgraph-prod
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    persistentvolumeclaims: "10"
EOF
```

### 2. 配置管理

```bash
# 使用ConfigMap管理配置
kubectl create configmap langgraph-config \
  --from-file=config/ \
  --namespace=langgraph-prod

# 使用Secret管理敏感信息
kubectl create secret generic langgraph-secrets \
  --from-literal=DATABASE_PASSWORD=secure_password \
  --from-literal=LANGSMITH_API_KEY=your_api_key \
  --namespace=langgraph-prod
```

### 3. 安全配置

```yaml
# Pod安全策略
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: langgraph-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
```

### 4. 监控集成

```yaml
# ServiceMonitor for Prometheus
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: langgraph-metrics
  namespace: langgraph-prod
spec:
  selector:
    matchLabels:
      app: langgraph-multi-agent
  endpoints:
  - port: metrics
    interval: 30s
    path: /metrics
```

## 故障恢复程序

### 1. 数据库故障恢复

```bash
#!/bin/bash
# database-recovery.sh

echo "开始数据库故障恢复..."

# 1. 检查数据库状态
kubectl get pods -l app=postgres -n langgraph-prod

# 2. 如果Pod异常，重启数据库
kubectl delete pod -l app=postgres -n langgraph-prod

# 3. 等待Pod重新启动
kubectl wait --for=condition=ready pod -l app=postgres -n langgraph-prod --timeout=300s

# 4. 验证数据库连接
kubectl exec deployment/postgres -n langgraph-prod -- \
  psql -U langgraph_user -d langgraph_db -c "SELECT 1;"

# 5. 如果数据损坏，从备份恢复
if [ "$1" = "restore" ]; then
    echo "从备份恢复数据库..."
    kubectl exec -i deployment/postgres -n langgraph-prod -- \
      psql -U langgraph_user -d langgraph_db < /backup/latest.sql
fi

echo "数据库故障恢复完成"
```

### 2. 应用故障恢复

```bash
#!/bin/bash
# app-recovery.sh

echo "开始应用故障恢复..."

# 1. 重启应用
kubectl rollout restart deployment/langgraph-multi-agent -n langgraph-prod

# 2. 等待部署完成
kubectl rollout status deployment/langgraph-multi-agent -n langgraph-prod

# 3. 验证应用状态
kubectl get pods -l app=langgraph-multi-agent -n langgraph-prod

# 4. 健康检查
for i in {1..10}; do
    if curl -f http://your-domain.com/health; then
        echo "应用健康检查通过"
        break
    else
        echo "等待应用启动... ($i/10)"
        sleep 30
    fi
done

echo "应用故障恢复完成"
```

## 联系支持

### 技术支持团队

- **运维负责人**: 系统管理员 - ops@company.com - 24/7热线
- **开发团队**: 开发团队 - dev@company.com - 工作时间支持
- **安全团队**: 安全团队 - security@company.com - 安全事件专线

### 支持流程

1. **P0/P1故障**: 立即电话联系运维负责人
2. **P2故障**: 发送邮件至ops@company.com，2小时内响应
3. **P3/P4问题**: 通过工单系统提交，24小时内响应

### 文档和资源

- **运维手册**: [docs/operations-manual.md](./operations-manual.md)
- **故障排查指南**: [docs/troubleshooting-guide.md](./troubleshooting-guide.md)
- **MVP2集成指南**: [docs/mvp2-integration-guide.md](./mvp2-integration-guide.md)
- **监控面板**: http://grafana.company.com
- **日志系统**: http://kibana.company.com

### 紧急联系信息

```
运维热线: +86-xxx-xxxx-xxxx
安全事件: security-incident@company.com
升级通道: escalation@company.com
```

---

**重要提醒**: 
- 在生产环境部署前，请务必在测试环境中验证所有配置和功能
- 定期更新本文档以反映最新的部署配置和最佳实践
- 所有部署操作都应该有相应的回滚计划
- 建议定期进行灾难恢复演练以验证恢复程序的有效性