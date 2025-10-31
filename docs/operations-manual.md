# LangGraph多智能体系统运维手册

## 概述

本手册提供LangGraph多智能体系统的完整运维指南，包括日常运维、监控告警、故障排查、性能优化和安全管理等方面的详细说明。

## 目录

1. [系统架构概览](#系统架构概览)
2. [日常运维操作](#日常运维操作)
3. [监控和告警](#监控和告警)
4. [故障排查指南](#故障排查指南)
5. [性能优化](#性能优化)
6. [安全管理](#安全管理)
7. [备份和恢复](#备份和恢复)
8. [升级和维护](#升级和维护)
9. [应急响应](#应急响应)
10. [运维工具和脚本](#运维工具和脚本)

## 系统架构概览

### 核心组件

```
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph多智能体系统                      │
├─────────────────────────────────────────────────────────────┤
│  前端层                                                      │
│  ├── MVP2前端 (Nginx:80/443)                               │
│  └── 管理界面 (Grafana:3000)                               │
├─────────────────────────────────────────────────────────────┤
│  API层                                                      │
│  ├── FastAPI应用 (8000)                                    │
│  ├── WebSocket服务 (8000/ws)                               │
│  └── 健康检查端点 (8000/health)                             │
├─────────────────────────────────────────────────────────────┤
│  业务层                                                      │
│  ├── LangGraph工作流引擎                                    │
│  ├── 多智能体协调器                                          │
│  ├── 任务分解器                                             │
│  └── 错误恢复处理器                                          │
├─────────────────────────────────────────────────────────────┤
│  数据层                                                      │
│  ├── PostgreSQL (5432) - 主数据存储                        │
│  ├── Redis (6379) - 缓存和会话                             │
│  └── SQLite - 检查点存储                                    │
├─────────────────────────────────────────────────────────────┤
│  监控层                                                      │
│  ├── Prometheus (9090) - 指标收集                          │
│  ├── Grafana (3000) - 可视化监控                           │
│  ├── Elasticsearch (9200) - 日志存储                       │
│  ├── Kibana (5601) - 日志分析                              │
│  └── Logstash - 日志处理                                   │
└─────────────────────────────────────────────────────────────┘
```

### 部署架构

#### 生产环境 (Kubernetes)
- **命名空间**: `langgraph-multi-agent`
- **副本数**: 3个应用实例 (支持HPA自动扩缩容)
- **负载均衡**: Kubernetes Service + Ingress
- **存储**: PVC持久化存储
- **配置管理**: ConfigMap + Secret

#### 开发/测试环境 (Docker Compose)
- **容器编排**: Docker Compose
- **网络**: 自定义桥接网络
- **存储**: 本地卷挂载
- **配置**: 环境变量 + 配置文件

## 日常运维操作

### 1. 服务状态检查

#### 快速健康检查
```bash
# 检查所有服务状态
kubectl get pods -n langgraph-multi-agent

# 检查服务健康状态
curl -f http://your-domain.com/health
curl -f http://your-domain.com/api/v1/system/health

# 检查MVP2适配器状态
curl -f http://your-domain.com/api/v1/mvp2/health
```

#### 详细状态检查
```bash
# 查看Pod详细信息
kubectl describe pod <pod-name> -n langgraph-multi-agent

# 查看服务日志
kubectl logs -f deployment/langgraph-multi-agent -n langgraph-multi-agent

# 查看资源使用情况
kubectl top pods -n langgraph-multi-agent
kubectl top nodes
```

### 2. 日志管理

#### 日志查看
```bash
# 实时查看应用日志
kubectl logs -f deployment/langgraph-multi-agent -n langgraph-multi-agent

# 查看特定时间段的日志
kubectl logs --since=1h deployment/langgraph-multi-agent -n langgraph-multi-agent

# 查看错误日志
kubectl logs deployment/langgraph-multi-agent -n langgraph-multi-agent | grep ERROR

# 在Kibana中查看日志
# 访问 http://kibana-url:5601
# 创建索引模式: langgraph-multi-agent-*
# 使用KQL查询: level:ERROR AND @timestamp:[now-1h TO now]
```

#### 日志轮转和清理
```bash
# 设置日志保留策略 (在Kubernetes中)
kubectl patch deployment langgraph-multi-agent -n langgraph-multi-agent -p '
{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "langgraph-multi-agent",
          "env": [{
            "name": "LOG_RETENTION_DAYS",
            "value": "30"
          }]
        }]
      }
    }
  }
}'

# 手动清理旧日志
find /var/log/langgraph-multi-agent -name "*.log" -mtime +30 -delete
```

### 3. 配置管理

#### 更新配置
```bash
# 更新ConfigMap
kubectl edit configmap langgraph-config -n langgraph-multi-agent

# 重启服务以应用新配置
kubectl rollout restart deployment/langgraph-multi-agent -n langgraph-multi-agent

# 验证配置更新
kubectl rollout status deployment/langgraph-multi-agent -n langgraph-multi-agent
```

#### 密钥管理
```bash
# 更新密钥
kubectl create secret generic langgraph-secrets \
  --from-literal=LANGSMITH_API_KEY=new_api_key \
  --dry-run=client -o yaml | kubectl apply -f -

# 重启服务以应用新密钥
kubectl rollout restart deployment/langgraph-multi-agent -n langgraph-multi-agent
```

### 4. 扩缩容操作

#### 手动扩缩容
```bash
# 扩容到5个实例
kubectl scale deployment langgraph-multi-agent --replicas=5 -n langgraph-multi-agent

# 缩容到2个实例
kubectl scale deployment langgraph-multi-agent --replicas=2 -n langgraph-multi-agent

# 查看扩缩容状态
kubectl get pods -n langgraph-multi-agent -w
```

#### 自动扩缩容配置
```bash
# 查看HPA状态
kubectl get hpa -n langgraph-multi-agent

# 修改HPA配置
kubectl edit hpa langgraph-multi-agent-hpa -n langgraph-multi-agent

# 查看HPA详细信息
kubectl describe hpa langgraph-multi-agent-hpa -n langgraph-multi-agent
```

## 监控和告警

### 1. 关键指标监控

#### 应用层指标
- **请求指标**
  - `http_requests_total` - 总请求数
  - `http_request_duration_seconds` - 请求响应时间
  - `http_requests_per_second` - 每秒请求数

- **业务指标**
  - `langgraph_tasks_total` - 任务总数
  - `langgraph_tasks_active` - 活跃任务数
  - `langgraph_agents_active` - 活跃智能体数
  - `langgraph_workflow_duration_seconds` - 工作流执行时间

- **错误指标**
  - `langgraph_errors_total` - 错误总数
  - `langgraph_recovery_attempts_total` - 恢复尝试次数
  - `langgraph_failed_tasks_total` - 失败任务数

#### 系统层指标
- **资源使用**
  - `container_memory_usage_bytes` - 内存使用量
  - `container_cpu_usage_seconds_total` - CPU使用量
  - `container_fs_usage_bytes` - 磁盘使用量

- **数据库指标**
  - `postgresql_connections_active` - 活跃连接数
  - `postgresql_queries_per_second` - 每秒查询数
  - `redis_connected_clients` - Redis连接数

### 2. 告警规则配置

#### Prometheus告警规则
```yaml
# monitoring/alert_rules.yml
groups:
- name: langgraph-multi-agent
  rules:
  # 高错误率告警
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "高错误率检测到"
      description: "错误率超过10%，当前值: {{ $value }}"

  # 响应时间过长告警
  - alert: HighResponseTime
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "响应时间过长"
      description: "95%分位响应时间超过2秒，当前值: {{ $value }}s"

  # 内存使用率过高告警
  - alert: HighMemoryUsage
    expr: container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.8
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "内存使用率过高"
      description: "内存使用率超过80%，当前值: {{ $value | humanizePercentage }}"

  # 服务不可用告警
  - alert: ServiceDown
    expr: up{job="langgraph-multi-agent"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "服务不可用"
      description: "LangGraph多智能体服务已停止响应"

  # 数据库连接数过高告警
  - alert: HighDatabaseConnections
    expr: postgresql_connections_active > 80
    for: 3m
    labels:
      severity: warning
    annotations:
      summary: "数据库连接数过高"
      description: "PostgreSQL活跃连接数超过80，当前值: {{ $value }}"
```

### 3. Grafana仪表板

#### 主要仪表板面板
1. **系统概览**
   - 服务状态指示器
   - 总请求数和错误率
   - 响应时间趋势
   - 活跃用户数

2. **性能监控**
   - CPU和内存使用率
   - 网络I/O
   - 磁盘I/O
   - 数据库性能

3. **业务监控**
   - 任务执行统计
   - 智能体活动状态
   - 工作流执行时间分布
   - MVP2前端集成状态

4. **错误分析**
   - 错误类型分布
   - 错误趋势图
   - 恢复成功率
   - 故障影响范围

## 故障排查指南

### 1. 常见故障场景

#### 服务启动失败
**症状**: Pod处于CrashLoopBackOff状态
```bash
# 排查步骤
1. 查看Pod状态
kubectl get pods -n langgraph-multi-agent

2. 查看Pod事件
kubectl describe pod <pod-name> -n langgraph-multi-agent

3. 查看容器日志
kubectl logs <pod-name> -n langgraph-multi-agent

4. 检查配置
kubectl get configmap langgraph-config -n langgraph-multi-agent -o yaml
kubectl get secret langgraph-secrets -n langgraph-multi-agent -o yaml

# 常见原因和解决方案
- 配置错误: 检查环境变量和配置文件
- 依赖服务不可用: 检查数据库和Redis连接
- 资源不足: 检查CPU和内存限制
- 镜像问题: 验证镜像版本和可用性
```

#### 数据库连接失败
**症状**: 应用日志显示数据库连接错误
```bash
# 排查步骤
1. 检查PostgreSQL服务状态
kubectl get pods -l app=postgres -n langgraph-multi-agent

2. 测试数据库连接
kubectl exec -it <postgres-pod> -n langgraph-multi-agent -- \
  psql -U langgraph_user -d langgraph_db -c "SELECT 1;"

3. 检查网络连接
kubectl exec -it <app-pod> -n langgraph-multi-agent -- \
  nc -zv postgres 5432

4. 验证认证信息
kubectl get secret langgraph-secrets -n langgraph-multi-agent -o yaml

# 解决方案
- 重启PostgreSQL服务
- 检查密码和用户权限
- 验证网络策略配置
- 检查连接池配置
```

#### Redis缓存问题
**症状**: 缓存相关功能异常
```bash
# 排查步骤
1. 检查Redis服务状态
kubectl get pods -l app=redis -n langgraph-multi-agent

2. 测试Redis连接
kubectl exec -it <redis-pod> -n langgraph-multi-agent -- redis-cli ping

3. 检查Redis内存使用
kubectl exec -it <redis-pod> -n langgraph-multi-agent -- \
  redis-cli info memory

4. 查看Redis日志
kubectl logs <redis-pod> -n langgraph-multi-agent

# 解决方案
- 重启Redis服务
- 清理过期键值
- 调整内存策略
- 检查网络连接
```

#### 高负载问题
**症状**: 响应时间长，CPU/内存使用率高
```bash
# 排查步骤
1. 查看资源使用情况
kubectl top pods -n langgraph-multi-agent
kubectl top nodes

2. 分析慢查询
# 在PostgreSQL中执行
SELECT query, mean_time, calls FROM pg_stat_statements 
ORDER BY mean_time DESC LIMIT 10;

3. 检查并发任务数
curl http://your-domain.com/api/v1/system/metrics | grep langgraph_tasks_active

4. 分析请求模式
# 在Grafana中查看请求量和响应时间趋势

# 解决方案
- 增加副本数进行水平扩容
- 优化数据库查询
- 调整资源限制
- 启用缓存策略
```

### 2. 故障排查工具

#### 诊断脚本
```bash
#!/bin/bash
# diagnose.sh - 系统诊断脚本

echo "=== LangGraph多智能体系统诊断 ==="
echo "时间: $(date)"
echo

# 检查Pod状态
echo "1. Pod状态检查:"
kubectl get pods -n langgraph-multi-agent
echo

# 检查服务状态
echo "2. 服务状态检查:"
kubectl get svc -n langgraph-multi-agent
echo

# 检查资源使用
echo "3. 资源使用情况:"
kubectl top pods -n langgraph-multi-agent 2>/dev/null || echo "Metrics server不可用"
echo

# 检查健康状态
echo "4. 健康检查:"
for pod in $(kubectl get pods -n langgraph-multi-agent -o name | grep langgraph-multi-agent); do
    pod_name=$(echo $pod | cut -d'/' -f2)
    echo "检查 $pod_name:"
    kubectl exec $pod_name -n langgraph-multi-agent -- curl -s http://localhost:8000/health || echo "健康检查失败"
done
echo

# 检查最近的事件
echo "5. 最近事件:"
kubectl get events -n langgraph-multi-agent --sort-by='.lastTimestamp' | tail -10
echo

# 检查日志错误
echo "6. 最近错误日志:"
kubectl logs deployment/langgraph-multi-agent -n langgraph-multi-agent --tail=50 | grep -i error || echo "无错误日志"

echo "=== 诊断完成 ==="
```

#### 性能分析脚本
```bash
#!/bin/bash
# performance-analysis.sh - 性能分析脚本

echo "=== 性能分析报告 ==="
echo "时间: $(date)"
echo

# API响应时间测试
echo "1. API响应时间测试:"
for endpoint in "/health" "/api/v1/system/health" "/api/v1/mvp2/health"; do
    echo "测试 $endpoint:"
    curl -w "响应时间: %{time_total}s, 状态码: %{http_code}\n" \
         -s -o /dev/null http://your-domain.com$endpoint
done
echo

# 数据库性能检查
echo "2. 数据库性能检查:"
kubectl exec deployment/postgres -n langgraph-multi-agent -- \
  psql -U langgraph_user -d langgraph_db -c "
    SELECT 
      schemaname,
      tablename,
      attname,
      n_distinct,
      correlation
    FROM pg_stats 
    WHERE schemaname = 'public' 
    ORDER BY n_distinct DESC 
    LIMIT 10;"
echo

# Redis性能检查
echo "3. Redis性能检查:"
kubectl exec deployment/redis -n langgraph-multi-agent -- \
  redis-cli info stats | grep -E "(total_commands_processed|instantaneous_ops_per_sec|used_memory_human)"
echo

echo "=== 性能分析完成 ==="
```

## 性能优化

### 1. 应用层优化

#### 数据库优化
```sql
-- 创建必要的索引
CREATE INDEX CONCURRENTLY idx_tasks_status_created 
ON tasks(status, created_at) WHERE status IN ('pending', 'in_progress');

CREATE INDEX CONCURRENTLY idx_workflow_executions_task_id 
ON workflow_executions(task_id);

CREATE INDEX CONCURRENTLY idx_agent_messages_timestamp 
ON agent_messages(created_at) WHERE created_at > NOW() - INTERVAL '7 days';

-- 分析表统计信息
ANALYZE tasks;
ANALYZE workflow_executions;
ANALYZE agent_messages;

-- 清理过期数据
DELETE FROM agent_messages WHERE created_at < NOW() - INTERVAL '30 days';
DELETE FROM workflow_executions WHERE created_at < NOW() - INTERVAL '90 days' AND status = 'completed';
```

#### Redis优化
```bash
# 配置Redis内存策略
kubectl exec deployment/redis -n langgraph-multi-agent -- \
  redis-cli CONFIG SET maxmemory-policy allkeys-lru

# 设置键过期时间
kubectl exec deployment/redis -n langgraph-multi-agent -- \
  redis-cli CONFIG SET timeout 300

# 启用压缩
kubectl exec deployment/redis -n langgraph-multi-agent -- \
  redis-cli CONFIG SET rdbcompression yes
```

#### 应用配置优化
```yaml
# 在ConfigMap中添加性能优化配置
apiVersion: v1
kind: ConfigMap
metadata:
  name: langgraph-config
data:
  # 数据库连接池配置
  DATABASE_POOL_SIZE: "20"
  DATABASE_MAX_OVERFLOW: "30"
  DATABASE_POOL_TIMEOUT: "30"
  
  # 异步处理配置
  ASYNC_WORKERS: "4"
  TASK_QUEUE_SIZE: "1000"
  
  # 缓存配置
  CACHE_TTL: "3600"
  CACHE_MAX_SIZE: "10000"
  
  # 工作流优化
  MAX_CONCURRENT_WORKFLOWS: "50"
  WORKFLOW_TIMEOUT: "3600"
```

### 2. 基础设施优化

#### Kubernetes资源优化
```yaml
# 优化资源请求和限制
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "4Gi"
    cpu: "2000m"

# 配置节点亲和性
affinity:
  nodeAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      preference:
        matchExpressions:
        - key: node-type
          operator: In
          values:
          - compute-optimized

# 配置Pod反亲和性
podAntiAffinity:
  preferredDuringSchedulingIgnoredDuringExecution:
  - weight: 100
    podAffinityTerm:
      labelSelector:
        matchExpressions:
        - key: app
          operator: In
          values:
          - langgraph-multi-agent
      topologyKey: kubernetes.io/hostname
```

#### HPA优化配置
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: langgraph-multi-agent-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: langgraph-multi-agent
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
```

## 安全管理

### 1. 网络安全

#### 网络策略配置
```yaml
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
    - podSelector:
        matchLabels:
          app: nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
  - to: []
    ports:
    - protocol: TCP
      port: 443
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
```

### 2. 访问控制

#### RBAC配置
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: langgraph-service-account
  namespace: langgraph-multi-agent

---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: langgraph-role
  namespace: langgraph-multi-agent
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps", "secrets"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch"]

---
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

### 3. 安全扫描和审计

#### 定期安全检查脚本
```bash
#!/bin/bash
# security-audit.sh - 安全审计脚本

echo "=== 安全审计报告 ==="
echo "时间: $(date)"
echo

# 检查Pod安全上下文
echo "1. Pod安全上下文检查:"
kubectl get pods -n langgraph-multi-agent -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.securityContext}{"\n"}{end}'
echo

# 检查镜像漏洞 (需要安装trivy)
echo "2. 镜像安全扫描:"
if command -v trivy &> /dev/null; then
    trivy image langgraph-multi-agent:latest
else
    echo "Trivy未安装，跳过镜像扫描"
fi
echo

# 检查网络策略
echo "3. 网络策略检查:"
kubectl get networkpolicy -n langgraph-multi-agent
echo

# 检查RBAC配置
echo "4. RBAC配置检查:"
kubectl auth can-i --list --as=system:serviceaccount:langgraph-multi-agent:langgraph-service-account -n langgraph-multi-agent
echo

# 检查密钥安全
echo "5. 密钥安全检查:"
kubectl get secrets -n langgraph-multi-agent -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.type}{"\n"}{end}'
echo

echo "=== 安全审计完成 ==="
```

## 备份和恢复

### 1. 数据备份策略

#### 数据库备份
```bash
#!/bin/bash
# backup-database.sh - 数据库备份脚本

BACKUP_DIR="/backup/postgresql"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="langgraph_db_backup_$DATE.sql"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 执行数据库备份
kubectl exec deployment/postgres -n langgraph-multi-agent -- \
  pg_dump -U langgraph_user -d langgraph_db > $BACKUP_DIR/$BACKUP_FILE

# 压缩备份文件
gzip $BACKUP_DIR/$BACKUP_FILE

# 清理7天前的备份
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "数据库备份完成: $BACKUP_DIR/$BACKUP_FILE.gz"
```

#### 配置备份
```bash
#!/bin/bash
# backup-config.sh - 配置备份脚本

BACKUP_DIR="/backup/kubernetes"
DATE=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份所有Kubernetes资源
kubectl get all,configmap,secret,pvc,ingress -n langgraph-multi-agent -o yaml > \
  $BACKUP_DIR/langgraph-resources-$DATE.yaml

# 备份命名空间定义
kubectl get namespace langgraph-multi-agent -o yaml > \
  $BACKUP_DIR/langgraph-namespace-$DATE.yaml

# 压缩备份文件
tar -czf $BACKUP_DIR/langgraph-config-backup-$DATE.tar.gz \
  $BACKUP_DIR/langgraph-resources-$DATE.yaml \
  $BACKUP_DIR/langgraph-namespace-$DATE.yaml

# 清理原始文件
rm $BACKUP_DIR/langgraph-resources-$DATE.yaml
rm $BACKUP_DIR/langgraph-namespace-$DATE.yaml

echo "配置备份完成: $BACKUP_DIR/langgraph-config-backup-$DATE.tar.gz"
```

### 2. 恢复程序

#### 数据库恢复
```bash
#!/bin/bash
# restore-database.sh - 数据库恢复脚本

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "用法: $0 <backup_file.sql.gz>"
    exit 1
fi

# 解压备份文件
gunzip -c $BACKUP_FILE > /tmp/restore.sql

# 停止应用服务
kubectl scale deployment langgraph-multi-agent --replicas=0 -n langgraph-multi-agent

# 恢复数据库
kubectl exec -i deployment/postgres -n langgraph-multi-agent -- \
  psql -U langgraph_user -d langgraph_db < /tmp/restore.sql

# 重启应用服务
kubectl scale deployment langgraph-multi-agent --replicas=3 -n langgraph-multi-agent

# 清理临时文件
rm /tmp/restore.sql

echo "数据库恢复完成"
```

## 升级和维护

### 1. 滚动升级

#### 应用升级脚本
```bash
#!/bin/bash
# rolling-upgrade.sh - 滚动升级脚本

NEW_VERSION=$1

if [ -z "$NEW_VERSION" ]; then
    echo "用法: $0 <new_version>"
    exit 1
fi

echo "开始滚动升级到版本: $NEW_VERSION"

# 更新镜像版本
kubectl set image deployment/langgraph-multi-agent \
  langgraph-multi-agent=langgraph-multi-agent:$NEW_VERSION \
  -n langgraph-multi-agent

# 等待升级完成
kubectl rollout status deployment/langgraph-multi-agent -n langgraph-multi-agent

# 验证升级结果
echo "验证升级结果..."
kubectl get pods -n langgraph-multi-agent
curl -f http://your-domain.com/health

echo "滚动升级完成"
```

#### 回滚脚本
```bash
#!/bin/bash
# rollback.sh - 回滚脚本

echo "开始回滚部署..."

# 查看部署历史
kubectl rollout history deployment/langgraph-multi-agent -n langgraph-multi-agent

# 回滚到上一个版本
kubectl rollout undo deployment/langgraph-multi-agent -n langgraph-multi-agent

# 等待回滚完成
kubectl rollout status deployment/langgraph-multi-agent -n langgraph-multi-agent

# 验证回滚结果
echo "验证回滚结果..."
kubectl get pods -n langgraph-multi-agent
curl -f http://your-domain.com/health

echo "回滚完成"
```

### 2. 维护窗口操作

#### 维护模式脚本
```bash
#!/bin/bash
# maintenance-mode.sh - 维护模式脚本

ACTION=$1

case $ACTION in
    "enable")
        echo "启用维护模式..."
        # 缩容到0个实例
        kubectl scale deployment langgraph-multi-agent --replicas=0 -n langgraph-multi-agent
        # 部署维护页面
        kubectl apply -f k8s/maintenance-page.yaml
        echo "维护模式已启用"
        ;;
    "disable")
        echo "禁用维护模式..."
        # 删除维护页面
        kubectl delete -f k8s/maintenance-page.yaml
        # 恢复正常副本数
        kubectl scale deployment langgraph-multi-agent --replicas=3 -n langgraph-multi-agent
        # 等待服务恢复
        kubectl rollout status deployment/langgraph-multi-agent -n langgraph-multi-agent
        echo "维护模式已禁用"
        ;;
    *)
        echo "用法: $0 {enable|disable}"
        exit 1
        ;;
esac
```

## 应急响应

### 1. 应急响应流程

#### 严重故障响应
1. **立即响应** (0-5分钟)
   - 确认故障范围和影响
   - 启动应急响应团队
   - 通知相关干系人

2. **故障隔离** (5-15分钟)
   - 隔离故障组件
   - 启用备用系统
   - 实施临时解决方案

3. **问题修复** (15分钟-2小时)
   - 分析根本原因
   - 实施永久修复
   - 验证修复效果

4. **恢复验证** (2-4小时)
   - 全面系统测试
   - 性能验证
   - 用户验收测试

5. **事后分析** (24-48小时)
   - 编写故障报告
   - 改进预防措施
   - 更新应急预案

### 2. 应急脚本

#### 快速故障恢复
```bash
#!/bin/bash
# emergency-recovery.sh - 应急恢复脚本

echo "=== 应急恢复程序 ==="
echo "时间: $(date)"

# 1. 快速健康检查
echo "1. 执行快速健康检查..."
./diagnose.sh

# 2. 重启故障服务
echo "2. 重启可能的故障服务..."
kubectl rollout restart deployment/langgraph-multi-agent -n langgraph-multi-agent
kubectl rollout restart deployment/redis -n langgraph-multi-agent
kubectl rollout restart deployment/postgres -n langgraph-multi-agent

# 3. 等待服务恢复
echo "3. 等待服务恢复..."
kubectl rollout status deployment/langgraph-multi-agent -n langgraph-multi-agent
kubectl rollout status deployment/redis -n langgraph-multi-agent
kubectl rollout status deployment/postgres -n langgraph-multi-agent

# 4. 验证服务状态
echo "4. 验证服务状态..."
sleep 30
curl -f http://your-domain.com/health || echo "主服务健康检查失败"
curl -f http://your-domain.com/api/v1/mvp2/health || echo "MVP2适配器健康检查失败"

# 5. 检查关键指标
echo "5. 检查关键指标..."
kubectl top pods -n langgraph-multi-agent

echo "=== 应急恢复完成 ==="
```

## 运维工具和脚本

### 1. 监控脚本集合

#### 系统监控脚本
```bash
#!/bin/bash
# system-monitor.sh - 系统监控脚本

while true; do
    clear
    echo "=== LangGraph多智能体系统监控 ==="
    echo "时间: $(date)"
    echo
    
    # Pod状态
    echo "Pod状态:"
    kubectl get pods -n langgraph-multi-agent
    echo
    
    # 资源使用
    echo "资源使用:"
    kubectl top pods -n langgraph-multi-agent 2>/dev/null || echo "Metrics server不可用"
    echo
    
    # 服务状态
    echo "服务状态:"
    kubectl get svc -n langgraph-multi-agent
    echo
    
    # 最近事件
    echo "最近事件:"
    kubectl get events -n langgraph-multi-agent --sort-by='.lastTimestamp' | tail -5
    echo
    
    sleep 10
done
```

### 2. 自动化运维脚本

#### 定时任务脚本
```bash
#!/bin/bash
# cron-tasks.sh - 定时任务脚本

# 每日备份 (添加到crontab: 0 2 * * * /path/to/cron-tasks.sh daily)
# 每周清理 (添加到crontab: 0 3 * * 0 /path/to/cron-tasks.sh weekly)
# 每月报告 (添加到crontab: 0 4 1 * * /path/to/cron-tasks.sh monthly)

TASK=$1

case $TASK in
    "daily")
        echo "执行每日任务..."
        # 数据库备份
        ./backup-database.sh
        # 日志清理
        kubectl exec deployment/langgraph-multi-agent -n langgraph-multi-agent -- \
          find /app/logs -name "*.log" -mtime +7 -delete
        # 健康检查
        ./diagnose.sh > /var/log/daily-health-check.log
        ;;
    "weekly")
        echo "执行每周任务..."
        # 配置备份
        ./backup-config.sh
        # 性能分析
        ./performance-analysis.sh > /var/log/weekly-performance-report.log
        # 安全审计
        ./security-audit.sh > /var/log/weekly-security-audit.log
        ;;
    "monthly")
        echo "执行每月任务..."
        # 生成月度报告
        ./generate-monthly-report.sh
        # 清理旧备份
        find /backup -name "*.gz" -mtime +30 -delete
        # 系统优化建议
        ./optimization-recommendations.sh > /var/log/monthly-optimization.log
        ;;
    *)
        echo "用法: $0 {daily|weekly|monthly}"
        exit 1
        ;;
esac
```

## 联系信息和支持

### 运维团队联系方式
- **运维负责人**: [姓名] - [邮箱] - [电话]
- **开发团队**: [邮箱] - [Slack频道]
- **安全团队**: [邮箱] - [紧急联系方式]

### 支持资源
- **文档库**: [内部文档地址]
- **监控面板**: [Grafana地址]
- **日志系统**: [Kibana地址]
- **问题跟踪**: [JIRA/GitHub地址]

### 紧急联系流程
1. **P0故障** (系统完全不可用): 立即电话联系运维负责人
2. **P1故障** (核心功能受影响): 30分钟内通过Slack通知
3. **P2故障** (非核心功能问题): 工作时间内邮件通知
4. **P3故障** (性能问题): 每日报告中包含

---

## 运维自动化

### 1. 自动化脚本库

#### 系统健康检查自动化
```bash
#!/bin/bash
# automated-health-check.sh - 自动化健康检查脚本

NAMESPACE="langgraph-multi-agent"
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"

# 检查函数
check_pods() {
    echo "检查Pod状态..."
    FAILED_PODS=$(kubectl get pods -n $NAMESPACE --field-selector=status.phase!=Running --no-headers 2>/dev/null | wc -l)
    if [ $FAILED_PODS -gt 0 ]; then
        return 1
    fi
    return 0
}

check_services() {
    echo "检查服务健康状态..."
    
    # 检查主API
    if ! curl -f -s http://your-domain.com/health > /dev/null; then
        return 1
    fi
    
    # 检查MVP2适配器
    if ! curl -f -s http://your-domain.com/api/v1/mvp2/health > /dev/null; then
        return 2
    fi
    
    return 0
}

check_database() {
    echo "检查数据库连接..."
    kubectl exec deployment/postgres -n $NAMESPACE -- \
        psql -U langgraph_user -d langgraph_db -c "SELECT 1;" > /dev/null 2>&1
    return $?
}

check_redis() {
    echo "检查Redis连接..."
    kubectl exec deployment/redis -n $NAMESPACE -- \
        redis-cli ping > /dev/null 2>&1
    return $?
}

send_alert() {
    local message=$1
    local level=$2
    
    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"🚨 [$level] LangGraph系统告警: $message\"}" \
        $SLACK_WEBHOOK_URL
}

# 主检查流程
main() {
    echo "=== 自动化健康检查开始 $(date) ==="
    
    ISSUES=()
    
    if ! check_pods; then
        ISSUES+=("Pod状态异常")
    fi
    
    if ! check_services; then
        case $? in
            1) ISSUES+=("主API服务不可用") ;;
            2) ISSUES+=("MVP2适配器不可用") ;;
        esac
    fi
    
    if ! check_database; then
        ISSUES+=("数据库连接失败")
    fi
    
    if ! check_redis; then
        ISSUES+=("Redis连接失败")
    fi
    
    # 报告结果
    if [ ${#ISSUES[@]} -eq 0 ]; then
        echo "✅ 所有检查通过"
    else
        echo "❌ 发现问题:"
        for issue in "${ISSUES[@]}"; do
            echo "  - $issue"
            send_alert "$issue" "CRITICAL"
        done
    fi
    
    echo "=== 自动化健康检查结束 ==="
}

main "$@"
```

#### 自动扩缩容脚本
```bash
#!/bin/bash
# auto-scaling.sh - 智能扩缩容脚本

NAMESPACE="langgraph-multi-agent"
DEPLOYMENT="langgraph-multi-agent"
MIN_REPLICAS=3
MAX_REPLICAS=20
CPU_THRESHOLD=70
MEMORY_THRESHOLD=80

get_current_replicas() {
    kubectl get deployment $DEPLOYMENT -n $NAMESPACE -o jsonpath='{.spec.replicas}'
}

get_resource_usage() {
    # 获取平均CPU使用率
    CPU_USAGE=$(kubectl top pods -n $NAMESPACE --no-headers | \
        grep $DEPLOYMENT | \
        awk '{sum+=$2} END {print sum/NR}' | \
        sed 's/m//')
    
    # 获取平均内存使用率
    MEMORY_USAGE=$(kubectl top pods -n $NAMESPACE --no-headers | \
        grep $DEPLOYMENT | \
        awk '{sum+=$3} END {print sum/NR}' | \
        sed 's/Mi//')
    
    echo "CPU: ${CPU_USAGE:-0}, Memory: ${MEMORY_USAGE:-0}"
}

scale_up() {
    local current_replicas=$1
    local new_replicas=$((current_replicas + 2))
    
    if [ $new_replicas -le $MAX_REPLICAS ]; then
        echo "扩容到 $new_replicas 个副本"
        kubectl scale deployment $DEPLOYMENT --replicas=$new_replicas -n $NAMESPACE
        return 0
    else
        echo "已达到最大副本数限制 ($MAX_REPLICAS)"
        return 1
    fi
}

scale_down() {
    local current_replicas=$1
    local new_replicas=$((current_replicas - 1))
    
    if [ $new_replicas -ge $MIN_REPLICAS ]; then
        echo "缩容到 $new_replicas 个副本"
        kubectl scale deployment $DEPLOYMENT --replicas=$new_replicas -n $NAMESPACE
        return 0
    else
        echo "已达到最小副本数限制 ($MIN_REPLICAS)"
        return 1
    fi
}

main() {
    echo "=== 自动扩缩容检查 $(date) ==="
    
    current_replicas=$(get_current_replicas)
    echo "当前副本数: $current_replicas"
    
    resource_usage=$(get_resource_usage)
    echo "资源使用情况: $resource_usage"
    
    cpu_usage=$(echo $resource_usage | cut -d',' -f1 | cut -d':' -f2 | tr -d ' ')
    memory_usage=$(echo $resource_usage | cut -d',' -f2 | cut -d':' -f2 | tr -d ' ')
    
    # 扩容条件
    if [ ${cpu_usage:-0} -gt $CPU_THRESHOLD ] || [ ${memory_usage:-0} -gt $MEMORY_THRESHOLD ]; then
        echo "资源使用率过高，执行扩容"
        scale_up $current_replicas
    # 缩容条件
    elif [ ${cpu_usage:-100} -lt 30 ] && [ ${memory_usage:-100} -lt 40 ] && [ $current_replicas -gt $MIN_REPLICAS ]; then
        echo "资源使用率较低，执行缩容"
        scale_down $current_replicas
    else
        echo "资源使用率正常，无需调整"
    fi
    
    echo "=== 自动扩缩容检查结束 ==="
}

main "$@"
```

### 2. 定时任务配置

```bash
# 添加到crontab
# crontab -e

# 每5分钟执行健康检查
*/5 * * * * /opt/scripts/automated-health-check.sh >> /var/log/health-check.log 2>&1

# 每10分钟执行扩缩容检查
*/10 * * * * /opt/scripts/auto-scaling.sh >> /var/log/auto-scaling.log 2>&1

# 每小时执行性能分析
0 * * * * /opt/scripts/performance-analysis.sh >> /var/log/performance.log 2>&1

# 每天凌晨2点执行数据备份
0 2 * * * /opt/scripts/backup-database.sh >> /var/log/backup.log 2>&1

# 每天凌晨3点清理日志
0 3 * * * /opt/scripts/cleanup-logs.sh >> /var/log/cleanup.log 2>&1

# 每周日凌晨4点执行安全扫描
0 4 * * 0 /opt/scripts/security-scan.sh >> /var/log/security.log 2>&1

# 每月1号生成月度报告
0 5 1 * * /opt/scripts/monthly-report.sh >> /var/log/reports.log 2>&1
```

## 容量规划

### 1. 资源需求预测

```python
#!/usr/bin/env python3
# capacity-planning.py - 容量规划工具

import json
import requests
from datetime import datetime, timedelta
import numpy as np
from sklearn.linear_model import LinearRegression

class CapacityPlanner:
    def __init__(self, prometheus_url):
        self.prometheus_url = prometheus_url
        
    def get_metric_data(self, query, days=30):
        """从Prometheus获取指标数据"""
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        params = {
            'query': query,
            'start': start_time.timestamp(),
            'end': end_time.timestamp(),
            'step': '1h'
        }
        
        response = requests.get(f"{self.prometheus_url}/api/v1/query_range", params=params)
        return response.json()
    
    def predict_resource_usage(self, metric_name, days_ahead=30):
        """预测资源使用趋势"""
        data = self.get_metric_data(metric_name)
        
        if not data['data']['result']:
            return None
            
        values = data['data']['result'][0]['values']
        timestamps = [float(v[0]) for v in values]
        metrics = [float(v[1]) for v in values]
        
        # 准备训练数据
        X = np.array(timestamps).reshape(-1, 1)
        y = np.array(metrics)
        
        # 训练线性回归模型
        model = LinearRegression()
        model.fit(X, y)
        
        # 预测未来使用量
        future_time = datetime.now().timestamp() + (days_ahead * 24 * 3600)
        predicted_usage = model.predict([[future_time]])[0]
        
        return {
            'current_usage': metrics[-1],
            'predicted_usage': predicted_usage,
            'trend': 'increasing' if predicted_usage > metrics[-1] else 'decreasing',
            'change_rate': (predicted_usage - metrics[-1]) / metrics[-1] * 100
        }
    
    def generate_capacity_report(self):
        """生成容量规划报告"""
        metrics = {
            'cpu_usage': 'avg(rate(container_cpu_usage_seconds_total[5m])) * 100',
            'memory_usage': 'avg(container_memory_usage_bytes / container_spec_memory_limit_bytes) * 100',
            'disk_usage': 'avg(container_fs_usage_bytes / container_fs_limit_bytes) * 100',
            'request_rate': 'rate(http_requests_total[5m])'
        }
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'predictions': {}
        }
        
        for metric_name, query in metrics.items():
            prediction = self.predict_resource_usage(query)
            if prediction:
                report['predictions'][metric_name] = prediction
        
        return report
    
    def get_scaling_recommendations(self):
        """获取扩缩容建议"""
        report = self.generate_capacity_report()
        recommendations = []
        
        for metric, data in report['predictions'].items():
            if metric == 'cpu_usage' and data['predicted_usage'] > 80:
                recommendations.append({
                    'type': 'scale_up',
                    'reason': f'CPU使用率预计将达到 {data["predicted_usage"]:.1f}%',
                    'action': '建议增加2个副本'
                })
            elif metric == 'memory_usage' and data['predicted_usage'] > 85:
                recommendations.append({
                    'type': 'scale_up',
                    'reason': f'内存使用率预计将达到 {data["predicted_usage"]:.1f}%',
                    'action': '建议增加内存限制或副本数'
                })
            elif metric == 'request_rate' and data['change_rate'] > 50:
                recommendations.append({
                    'type': 'scale_up',
                    'reason': f'请求量预计增长 {data["change_rate"]:.1f}%',
                    'action': '建议提前扩容以应对流量增长'
                })
        
        return recommendations

# 使用示例
if __name__ == "__main__":
    planner = CapacityPlanner("http://prometheus:9090")
    
    # 生成容量报告
    report = planner.generate_capacity_report()
    print(json.dumps(report, indent=2))
    
    # 获取扩缩容建议
    recommendations = planner.get_scaling_recommendations()
    for rec in recommendations:
        print(f"建议: {rec['action']} - {rec['reason']}")
```

### 2. 成本优化

```bash
#!/bin/bash
# cost-optimization.sh - 成本优化分析

NAMESPACE="langgraph-multi-agent"

analyze_resource_utilization() {
    echo "=== 资源利用率分析 ==="
    
    # 获取Pod资源请求和使用情况
    kubectl top pods -n $NAMESPACE --containers | while read line; do
        if [[ $line == *"langgraph"* ]]; then
            echo "$line"
        fi
    done
    
    echo ""
    echo "=== 资源请求 vs 限制分析 ==="
    kubectl get pods -n $NAMESPACE -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[0].resources.requests.cpu}{"\t"}{.spec.containers[0].resources.limits.cpu}{"\t"}{.spec.containers[0].resources.requests.memory}{"\t"}{.spec.containers[0].resources.limits.memory}{"\n"}{end}' | \
    column -t -s $'\t' -N "Pod,CPU请求,CPU限制,内存请求,内存限制"
}

identify_oversized_pods() {
    echo "=== 识别过度配置的Pod ==="
    
    # 获取CPU使用率低于30%的Pod
    kubectl top pods -n $NAMESPACE --no-headers | awk '$2 < 100 {print $1 " CPU使用率过低: " $2}'
    
    # 获取内存使用率低于40%的Pod
    kubectl top pods -n $NAMESPACE --no-headers | awk '$3 < 400 {print $1 " 内存使用率过低: " $3}'
}

suggest_optimizations() {
    echo "=== 优化建议 ==="
    
    current_replicas=$(kubectl get deployment langgraph-multi-agent -n $NAMESPACE -o jsonpath='{.spec.replicas}')
    echo "当前副本数: $current_replicas"
    
    # 基于历史数据建议最优副本数
    avg_cpu=$(kubectl top pods -n $NAMESPACE --no-headers | grep langgraph | awk '{sum+=$2; count++} END {print sum/count}')
    if (( $(echo "$avg_cpu < 200" | bc -l) )); then
        echo "建议: CPU使用率较低，可以考虑减少副本数或降低资源请求"
    fi
    
    # 存储优化建议
    echo "存储优化建议:"
    kubectl get pvc -n $NAMESPACE -o custom-columns=NAME:.metadata.name,SIZE:.spec.resources.requests.storage,USED:.status.capacity.storage
}

generate_cost_report() {
    echo "=== 成本分析报告 ==="
    
    # 计算资源成本（假设价格）
    local cpu_cost_per_core_hour=0.05  # $0.05 per core per hour
    local memory_cost_per_gb_hour=0.01  # $0.01 per GB per hour
    
    total_cpu_requests=$(kubectl get pods -n $NAMESPACE -o jsonpath='{.items[*].spec.containers[*].resources.requests.cpu}' | tr ' ' '\n' | sed 's/m$//' | awk '{sum+=$1} END {print sum/1000}')
    total_memory_requests=$(kubectl get pods -n $NAMESPACE -o jsonpath='{.items[*].spec.containers[*].resources.requests.memory}' | tr ' ' '\n' | sed 's/Mi$//' | awk '{sum+=$1} END {print sum/1024}')
    
    daily_cpu_cost=$(echo "$total_cpu_requests * $cpu_cost_per_core_hour * 24" | bc -l)
    daily_memory_cost=$(echo "$total_memory_requests * $memory_cost_per_gb_hour * 24" | bc -l)
    daily_total_cost=$(echo "$daily_cpu_cost + $daily_memory_cost" | bc -l)
    
    echo "每日资源成本估算:"
    echo "  CPU成本: \$$(printf '%.2f' $daily_cpu_cost)"
    echo "  内存成本: \$$(printf '%.2f' $daily_memory_cost)"
    echo "  总成本: \$$(printf '%.2f' $daily_total_cost)"
    echo "  月度成本: \$$(echo "$daily_total_cost * 30" | bc -l | xargs printf '%.2f')"
}

main() {
    echo "=== LangGraph系统成本优化分析 $(date) ==="
    
    analyze_resource_utilization
    echo ""
    identify_oversized_pods
    echo ""
    suggest_optimizations
    echo ""
    generate_cost_report
    
    echo "=== 分析完成 ==="
}

main "$@"
```

## 运维知识库

### 1. 常见问题FAQ

**Q: 如何快速重启整个系统？**
```bash
# 重启所有组件
kubectl rollout restart deployment -n langgraph-multi-agent
kubectl rollout restart statefulset -n langgraph-multi-agent
```

**Q: 如何查看特定时间段的日志？**
```bash
# 查看最近1小时的日志
kubectl logs --since=1h deployment/langgraph-multi-agent -n langgraph-multi-agent

# 查看特定时间段的日志（需要日志聚合系统）
curl -X GET "http://elasticsearch:9200/langgraph-*/_search" -H 'Content-Type: application/json' -d'
{
  "query": {
    "range": {
      "@timestamp": {
        "gte": "2024-10-26T00:00:00",
        "lte": "2024-10-26T23:59:59"
      }
    }
  }
}'
```

**Q: 如何临时增加系统资源？**
```bash
# 临时扩容
kubectl scale deployment langgraph-multi-agent --replicas=10 -n langgraph-multi-agent

# 增加资源限制
kubectl patch deployment langgraph-multi-agent -n langgraph-multi-agent -p '
{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "langgraph-multi-agent",
          "resources": {
            "limits": {
              "cpu": "4000m",
              "memory": "8Gi"
            }
          }
        }]
      }
    }
  }
}'
```

### 2. 运维检查清单

#### 日常检查清单（每日）
- [ ] 检查所有Pod状态
- [ ] 验证API健康检查
- [ ] 查看错误日志
- [ ] 检查资源使用率
- [ ] 验证备份任务执行
- [ ] 检查监控告警

#### 周度检查清单（每周）
- [ ] 分析性能趋势
- [ ] 检查安全更新
- [ ] 验证灾难恢复程序
- [ ] 清理旧日志和数据
- [ ] 更新文档
- [ ] 团队培训和知识分享

#### 月度检查清单（每月）
- [ ] 容量规划评估
- [ ] 成本分析和优化
- [ ] 安全审计
- [ ] 系统性能调优
- [ ] 备份策略评估
- [ ] 运维流程改进

### 3. 应急联系卡

```
┌─────────────────────────────────────────┐
│          LangGraph系统应急联系卡         │
├─────────────────────────────────────────┤
│ P0故障（系统完全不可用）                │
│ 📞 运维热线: +86-xxx-xxxx-xxxx          │
│ 📧 紧急邮箱: emergency@company.com      │
│                                         │
│ P1故障（核心功能受影响）                │
│ 📞 技术负责人: +86-xxx-xxxx-xxxx        │
│ 📧 技术团队: tech-team@company.com      │
│                                         │
│ 安全事件                                │
│ 📞 安全团队: +86-xxx-xxxx-xxxx          │
│ 📧 安全邮箱: security@company.com       │
│                                         │
│ 系统访问地址                            │
│ 🌐 监控面板: http://grafana.company.com │
│ 🌐 日志系统: http://kibana.company.com  │
│ 🌐 主系统: http://langgraph.company.com │
└─────────────────────────────────────────┘
```

---

**重要提醒**: 
- 本手册应定期更新，确保与系统实际配置保持一致
- 所有运维人员都应熟悉本手册内容，并定期进行应急演练
- 建议每季度进行一次完整的灾难恢复演练
- 所有运维操作都应该记录在案，便于后续分析和改进
- 定期评估和更新运维流程，确保其有效性和时效性