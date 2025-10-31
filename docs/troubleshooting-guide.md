# LangGraph多智能体系统故障排查指南

## 概述

本指南提供LangGraph多智能体系统常见问题的诊断和解决方案，帮助运维人员快速定位和修复系统故障。

## 目录

1. [故障分类和优先级](#故障分类和优先级)
2. [诊断工具和方法](#诊断工具和方法)
3. [应用层故障](#应用层故障)
4. [数据层故障](#数据层故障)
5. [网络和连接故障](#网络和连接故障)
6. [性能问题](#性能问题)
7. [安全相关问题](#安全相关问题)
8. [MVP2前端集成问题](#mvp2前端集成问题)
9. [监控和告警问题](#监控和告警问题)
10. [预防措施](#预防措施)

## 故障分类和优先级

### 故障等级定义

| 等级 | 描述 | 响应时间 | 示例 |
|------|------|----------|------|
| P0 | 系统完全不可用 | 立即 | 所有服务宕机、数据丢失 |
| P1 | 核心功能严重受影响 | 15分钟 | API不响应、数据库连接失败 |
| P2 | 部分功能受影响 | 2小时 | 某个智能体失效、缓存问题 |
| P3 | 性能问题或非关键功能 | 24小时 | 响应慢、日志错误 |
| P4 | 改进建议或文档问题 | 1周 | 优化建议、文档更新 |

### 故障影响范围

```
┌─────────────────────────────────────────────────────────────┐
│                    故障影响分析矩阵                          │
├─────────────────┬───────────────┬───────────────────────────┤
│ 影响范围        │ 用户数量      │ 业务影响                  │
├─────────────────┼───────────────┼───────────────────────────┤
│ 全系统          │ 所有用户      │ 完全无法使用              │
│ 核心功能        │ 大部分用户    │ 主要功能不可用            │
│ 特定功能        │ 部分用户      │ 某些功能受限              │
│ 单个组件        │ 少数用户      │ 特定组件功能异常          │
└─────────────────┴───────────────┴───────────────────────────┘

## 诊断工具和方法

### 1. 系统诊断工具

#### 快速诊断脚本
```bash
#!/bin/bash
# quick-diagnosis.sh - 快速系统诊断

NAMESPACE="langgraph-multi-agent"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    local status=$1
    local message=$2
    
    case $status in
        "OK")
            echo -e "${GREEN}✅ $message${NC}"
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠️  $message${NC}"
            ;;
        "ERROR")
            echo -e "${RED}❌ $message${NC}"
            ;;
    esac
}

check_kubernetes_cluster() {
    echo "=== Kubernetes集群检查 ==="
    
    if kubectl cluster-info > /dev/null 2>&1; then
        print_status "OK" "Kubernetes集群连接正常"
    else
        print_status "ERROR" "无法连接到Kubernetes集群"
        return 1
    fi
    
    # 检查节点状态
    local not_ready_nodes=$(kubectl get nodes --no-headers | grep -v Ready | wc -l)
    if [ $not_ready_nodes -eq 0 ]; then
        print_status "OK" "所有节点状态正常"
    else
        print_status "WARNING" "$not_ready_nodes 个节点状态异常"
    fi
}

check_namespace() {
    echo "=== 命名空间检查 ==="
    
    if kubectl get namespace $NAMESPACE > /dev/null 2>&1; then
        print_status "OK" "命名空间 $NAMESPACE 存在"
    else
        print_status "ERROR" "命名空间 $NAMESPACE 不存在"
        return 1
    fi
}

check_pods() {
    echo "=== Pod状态检查 ==="
    
    local total_pods=$(kubectl get pods -n $NAMESPACE --no-headers | wc -l)
    local running_pods=$(kubectl get pods -n $NAMESPACE --no-headers | grep Running | wc -l)
    local failed_pods=$(kubectl get pods -n $NAMESPACE --no-headers | grep -E "(Error|CrashLoopBackOff|ImagePullBackOff)" | wc -l)
    
    print_status "OK" "总Pod数: $total_pods, 运行中: $running_pods"
    
    if [ $failed_pods -gt 0 ]; then
        print_status "ERROR" "失败Pod数: $failed_pods"
        echo "失败的Pod:"
        kubectl get pods -n $NAMESPACE --no-headers | grep -E "(Error|CrashLoopBackOff|ImagePullBackOff)"
    else
        print_status "OK" "没有失败的Pod"
    fi
}

check_services() {
    echo "=== 服务检查 ==="
    
    local services=("langgraph-multi-agent-service" "postgres-service" "redis-service")
    
    for service in "${services[@]}"; do
        if kubectl get service $service -n $NAMESPACE > /dev/null 2>&1; then
            print_status "OK" "服务 $service 存在"
        else
            print_status "ERROR" "服务 $service 不存在"
        fi
    done
}

check_api_health() {
    echo "=== API健康检查 ==="
    
    # 获取服务端点
    local api_url=$(kubectl get ingress -n $NAMESPACE -o jsonpath='{.items[0].spec.rules[0].host}' 2>/dev/null)
    
    if [ -z "$api_url" ]; then
        api_url="localhost:8000"
        print_status "WARNING" "未找到Ingress配置，使用默认地址"
    fi
    
    # 检查主API
    if curl -f -s "http://$api_url/health" > /dev/null; then
        print_status "OK" "主API健康检查通过"
    else
        print_status "ERROR" "主API健康检查失败"
    fi
    
    # 检查MVP2适配器
    if curl -f -s "http://$api_url/api/v1/mvp2/health" > /dev/null; then
        print_status "OK" "MVP2适配器健康检查通过"
    else
        print_status "ERROR" "MVP2适配器健康检查失败"
    fi
}

check_database() {
    echo "=== 数据库检查 ==="
    
    if kubectl exec deployment/postgres -n $NAMESPACE -- psql -U langgraph_user -d langgraph_db -c "SELECT 1;" > /dev/null 2>&1; then
        print_status "OK" "PostgreSQL数据库连接正常"
    else
        print_status "ERROR" "PostgreSQL数据库连接失败"
    fi
}

check_redis() {
    echo "=== Redis检查 ==="
    
    if kubectl exec deployment/redis -n $NAMESPACE -- redis-cli ping > /dev/null 2>&1; then
        print_status "OK" "Redis连接正常"
    else
        print_status "ERROR" "Redis连接失败"
    fi
}

check_resources() {
    echo "=== 资源使用检查 ==="
    
    # 检查CPU和内存使用
    if command -v kubectl top > /dev/null; then
        kubectl top pods -n $NAMESPACE --no-headers | while read line; do
            local pod_name=$(echo $line | awk '{print $1}')
            local cpu_usage=$(echo $line | awk '{print $2}' | sed 's/m//')
            local memory_usage=$(echo $line | awk '{print $3}' | sed 's/Mi//')
            
            if [ ${cpu_usage:-0} -gt 1000 ]; then
                print_status "WARNING" "$pod_name CPU使用率过高: ${cpu_usage}m"
            fi
            
            if [ ${memory_usage:-0} -gt 2048 ]; then
                print_status "WARNING" "$pod_name 内存使用率过高: ${memory_usage}Mi"
            fi
        done
    else
        print_status "WARNING" "Metrics Server未安装，无法检查资源使用情况"
    fi
}

main() {
    echo "=== LangGraph多智能体系统快速诊断 ==="
    echo "时间: $(date)"
    echo ""
    
    check_kubernetes_cluster
    echo ""
    check_namespace
    echo ""
    check_pods
    echo ""
    check_services
    echo ""
    check_api_health
    echo ""
    check_database
    echo ""
    check_redis
    echo ""
    check_resources
    
    echo ""
    echo "=== 诊断完成 ==="
}

main "$@"
```

#### 详细诊断脚本
```bash
#!/bin/bash
# detailed-diagnosis.sh - 详细系统诊断

NAMESPACE="langgraph-multi-agent"
OUTPUT_DIR="/tmp/langgraph-diagnosis-$(date +%Y%m%d-%H%M%S)"

mkdir -p $OUTPUT_DIR

collect_pod_info() {
    echo "收集Pod信息..."
    
    kubectl get pods -n $NAMESPACE -o wide > $OUTPUT_DIR/pods.txt
    kubectl describe pods -n $NAMESPACE > $OUTPUT_DIR/pods-describe.txt
    
    # 收集每个Pod的日志
    kubectl get pods -n $NAMESPACE --no-headers | awk '{print $1}' | while read pod; do
        kubectl logs $pod -n $NAMESPACE --tail=1000 > $OUTPUT_DIR/logs-$pod.txt 2>/dev/null
        kubectl logs $pod -n $NAMESPACE --previous --tail=1000 > $OUTPUT_DIR/logs-$pod-previous.txt 2>/dev/null
    done
}

collect_service_info() {
    echo "收集服务信息..."
    
    kubectl get services -n $NAMESPACE -o wide > $OUTPUT_DIR/services.txt
    kubectl describe services -n $NAMESPACE > $OUTPUT_DIR/services-describe.txt
    kubectl get endpoints -n $NAMESPACE > $OUTPUT_DIR/endpoints.txt
}

collect_config_info() {
    echo "收集配置信息..."
    
    kubectl get configmaps -n $NAMESPACE -o yaml > $OUTPUT_DIR/configmaps.yaml
    kubectl get secrets -n $NAMESPACE -o yaml > $OUTPUT_DIR/secrets.yaml
    kubectl get ingress -n $NAMESPACE -o yaml > $OUTPUT_DIR/ingress.yaml
}

collect_events() {
    echo "收集事件信息..."
    
    kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' > $OUTPUT_DIR/events.txt
}

collect_resource_usage() {
    echo "收集资源使用信息..."
    
    kubectl top nodes > $OUTPUT_DIR/nodes-usage.txt 2>/dev/null
    kubectl top pods -n $NAMESPACE > $OUTPUT_DIR/pods-usage.txt 2>/dev/null
}

collect_network_info() {
    echo "收集网络信息..."
    
    kubectl get networkpolicies -n $NAMESPACE -o yaml > $OUTPUT_DIR/networkpolicies.yaml
    
    # 测试网络连接
    kubectl run network-test --image=busybox --rm -it --restart=Never -n $NAMESPACE -- /bin/sh -c "
        nslookup kubernetes.default.svc.cluster.local > /tmp/dns-test.txt 2>&1
        wget -qO- --timeout=5 http://langgraph-multi-agent-service:8000/health > /tmp/service-test.txt 2>&1
        cat /tmp/dns-test.txt /tmp/service-test.txt
    " > $OUTPUT_DIR/network-test.txt 2>/dev/null
}

generate_summary() {
    echo "生成诊断摘要..."
    
    cat > $OUTPUT_DIR/summary.txt << EOF
LangGraph多智能体系统诊断报告
生成时间: $(date)
命名空间: $NAMESPACE

=== 系统概览 ===
Pod总数: $(kubectl get pods -n $NAMESPACE --no-headers | wc -l)
运行中Pod: $(kubectl get pods -n $NAMESPACE --no-headers | grep Running | wc -l)
失败Pod: $(kubectl get pods -n $NAMESPACE --no-headers | grep -E "(Error|CrashLoopBackOff|ImagePullBackOff)" | wc -l)

服务总数: $(kubectl get services -n $NAMESPACE --no-headers | wc -l)

=== 最近事件 ===
$(kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' | tail -10)

=== 资源使用 ===
$(kubectl top pods -n $NAMESPACE 2>/dev/null || echo "Metrics Server不可用")

=== 诊断文件 ===
$(ls -la $OUTPUT_DIR/)
EOF
}

main() {
    echo "=== 开始详细诊断 ==="
    echo "输出目录: $OUTPUT_DIR"
    
    collect_pod_info
    collect_service_info
    collect_config_info
    collect_events
    collect_resource_usage
    collect_network_info
    generate_summary
    
    echo "=== 诊断完成 ==="
    echo "诊断文件保存在: $OUTPUT_DIR"
    echo "摘要文件: $OUTPUT_DIR/summary.txt"
    
    # 创建压缩包
    tar -czf $OUTPUT_DIR.tar.gz -C $(dirname $OUTPUT_DIR) $(basename $OUTPUT_DIR)
    echo "压缩包: $OUTPUT_DIR.tar.gz"
}

main "$@"
```

### 2. 监控工具

#### Prometheus查询示例
```bash
# 常用Prometheus查询
PROMETHEUS_URL="http://prometheus:9090"

# 检查服务可用性
curl -G "$PROMETHEUS_URL/api/v1/query" --data-urlencode 'query=up{job="langgraph-multi-agent"}'

# 检查错误率
curl -G "$PROMETHEUS_URL/api/v1/query" --data-urlencode 'query=rate(http_requests_total{status=~"5.."}[5m])'

# 检查响应时间
curl -G "$PROMETHEUS_URL/api/v1/query" --data-urlencode 'query=histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))'

# 检查内存使用
curl -G "$PROMETHEUS_URL/api/v1/query" --data-urlencode 'query=container_memory_usage_bytes{pod=~"langgraph-multi-agent.*"}'
```

#### 日志分析工具
```bash
#!/bin/bash
# log-analyzer.sh - 日志分析工具

NAMESPACE="langgraph-multi-agent"
TIME_RANGE="1h"

analyze_error_logs() {
    echo "=== 错误日志分析 ==="
    
    kubectl logs -n $NAMESPACE --since=$TIME_RANGE -l app=langgraph-multi-agent | \
    grep -i error | \
    sort | uniq -c | sort -nr | head -20
}

analyze_performance_logs() {
    echo "=== 性能日志分析 ==="
    
    kubectl logs -n $NAMESPACE --since=$TIME_RANGE -l app=langgraph-multi-agent | \
    grep -E "(slow|timeout|duration)" | \
    tail -20
}

analyze_api_logs() {
    echo "=== API访问日志分析 ==="
    
    kubectl logs -n $NAMESPACE --since=$TIME_RANGE -l app=langgraph-multi-agent | \
    grep -E "(GET|POST|PUT|DELETE)" | \
    awk '{print $1, $7, $9}' | \
    sort | uniq -c | sort -nr | head -20
}

main() {
    echo "=== 日志分析报告 (最近 $TIME_RANGE) ==="
    echo "时间: $(date)"
    echo ""
    
    analyze_error_logs
    echo ""
    analyze_performance_logs
    echo ""
    analyze_api_logs
    
    echo ""
    echo "=== 分析完成 ==="
}

main "$@"
```

## 应用层故障

### 1. 服务启动失败

#### 症状识别
- Pod处于CrashLoopBackOff状态
- 容器重启次数不断增加
- 健康检查失败

#### 诊断步骤
```bash
# 1. 检查Pod状态
kubectl get pods -n langgraph-multi-agent

# 2. 查看Pod详细信息
kubectl describe pod <pod-name> -n langgraph-multi-agent

# 3. 查看容器日志
kubectl logs <pod-name> -n langgraph-multi-agent
kubectl logs <pod-name> -n langgraph-multi-agent --previous

# 4. 检查资源限制
kubectl get pod <pod-name> -n langgraph-multi-agent -o yaml | grep -A 10 resources

# 5. 检查环境变量
kubectl get pod <pod-name> -n langgraph-multi-agent -o yaml | grep -A 20 env
```

#### 常见原因和解决方案

**原因1: 配置错误**
```bash
# 检查ConfigMap
kubectl get configmap langgraph-config -n langgraph-multi-agent -o yaml

# 检查Secret
kubectl get secret langgraph-secrets -n langgraph-multi-agent -o yaml

# 解决方案: 修正配置
kubectl edit configmap langgraph-config -n langgraph-multi-agent
kubectl rollout restart deployment/langgraph-multi-agent -n langgraph-multi-agent
```

**原因2: 依赖服务不可用**
```bash
# 检查数据库连接
kubectl exec deployment/postgres -n langgraph-multi-agent -- pg_isready

# 检查Redis连接
kubectl exec deployment/redis -n langgraph-multi-agent -- redis-cli ping

# 解决方案: 重启依赖服务
kubectl rollout restart deployment/postgres -n langgraph-multi-agent
kubectl rollout restart deployment/redis -n langgraph-multi-agent
```

**原因3: 资源不足**
```bash
# 检查节点资源
kubectl describe nodes | grep -A 5 "Allocated resources"

# 检查Pod资源请求
kubectl top pods -n langgraph-multi-agent

# 解决方案: 调整资源配置
kubectl patch deployment langgraph-multi-agent -n langgraph-multi-agent -p '
{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "langgraph-multi-agent",
          "resources": {
            "requests": {
              "memory": "512Mi",
              "cpu": "250m"
            },
            "limits": {
              "memory": "2Gi",
              "cpu": "1000m"
            }
          }
        }]
      }
    }
  }
}'
```

### 2. API响应异常

#### 症状识别
- HTTP 5xx错误增加
- 响应时间过长
- 部分API端点不可用

#### 诊断步骤
```bash
# 1. 检查API健康状态
curl -v http://your-domain.com/health
curl -v http://your-domain.com/api/v1/mvp2/health

# 2. 检查负载均衡器状态
kubectl get ingress -n langgraph-multi-agent
kubectl describe ingress langgraph-ingress -n langgraph-multi-agent

# 3. 检查服务端点
kubectl get endpoints -n langgraph-multi-agent

# 4. 测试内部服务连接
kubectl run debug-pod --image=busybox --rm -it --restart=Never -n langgraph-multi-agent -- /bin/sh
# 在Pod内执行
wget -qO- http://langgraph-multi-agent-service:8000/health
```

#### 解决方案

**解决方案1: 重启应用服务**
```bash
kubectl rollout restart deployment/langgraph-multi-agent -n langgraph-multi-agent
kubectl rollout status deployment/langgraph-multi-agent -n langgraph-multi-agent
```

**解决方案2: 检查和修复负载均衡配置**
```bash
# 检查Ingress配置
kubectl get ingress langgraph-ingress -n langgraph-multi-agent -o yaml

# 重新应用Ingress配置
kubectl apply -f k8s/ingress.yaml
```

**解决方案3: 扩容服务**
```bash
# 临时扩容
kubectl scale deployment langgraph-multi-agent --replicas=5 -n langgraph-multi-agent

# 检查扩容状态
kubectl get pods -n langgraph-multi-agent -w
```

### 3. 智能体协作异常

#### 症状识别
- 任务执行卡住
- 智能体状态异常
- 工作流执行失败

#### 诊断步骤
```bash
# 1. 检查智能体状态
curl http://your-domain.com/api/v1/system/agents/status

# 2. 查看工作流日志
kubectl logs -n langgraph-multi-agent -l app=langgraph-multi-agent | grep -i workflow

# 3. 检查任务队列状态
kubectl exec deployment/redis -n langgraph-multi-agent -- redis-cli llen task_queue

# 4. 查看数据库中的任务状态
kubectl exec deployment/postgres -n langgraph-multi-agent -- \
  psql -U langgraph_user -d langgraph_db -c "SELECT id, status, created_at FROM tasks WHERE status IN ('pending', 'in_progress') ORDER BY created_at DESC LIMIT 10;"
```

#### 解决方案

**解决方案1: 重置智能体状态**
```bash
# 通过API重置智能体
curl -X POST http://your-domain.com/api/v1/system/agents/reset

# 或者重启相关服务
kubectl rollout restart deployment/langgraph-multi-agent -n langgraph-multi-agent
```

**解决方案2: 清理卡住的任务**
```bash
# 查找长时间运行的任务
kubectl exec deployment/postgres -n langgraph-multi-agent -- \
  psql -U langgraph_user -d langgraph_db -c "
    UPDATE tasks 
    SET status = 'failed', 
        error_message = 'Task timeout - reset by admin' 
    WHERE status = 'in_progress' 
    AND created_at < NOW() - INTERVAL '1 hour';"

# 清理Redis队列
kubectl exec deployment/redis -n langgraph-multi-agent -- redis-cli flushdb
```

## 数据层故障

### 1. PostgreSQL数据库问题

#### 连接失败
```bash
# 诊断步骤
kubectl get pods -l app=postgres -n langgraph-multi-agent
kubectl logs deployment/postgres -n langgraph-multi-agent

# 测试连接
kubectl exec deployment/postgres -n langgraph-multi-agent -- \
  psql -U langgraph_user -d langgraph_db -c "SELECT version();"

# 解决方案
# 1. 重启数据库
kubectl rollout restart deployment/postgres -n langgraph-multi-agent

# 2. 检查存储
kubectl get pvc -n langgraph-multi-agent
kubectl describe pvc postgres-pvc -n langgraph-multi-agent

# 3. 检查密码配置
kubectl get secret langgraph-secrets -n langgraph-multi-agent -o yaml
```

#### 性能问题
```bash
# 诊断慢查询
kubectl exec deployment/postgres -n langgraph-multi-agent -- \
  psql -U langgraph_user -d langgraph_db -c "
    SELECT query, mean_time, calls, total_time 
    FROM pg_stat_statements 
    ORDER BY mean_time DESC 
    LIMIT 10;"

# 检查数据库大小
kubectl exec deployment/postgres -n langgraph-multi-agent -- \
  psql -U langgraph_user -d langgraph_db -c "
    SELECT 
      schemaname,
      tablename,
      pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
    FROM pg_tables 
    WHERE schemaname = 'public' 
    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"

# 优化解决方案
# 1. 重建索引
kubectl exec deployment/postgres -n langgraph-multi-agent -- \
  psql -U langgraph_user -d langgraph_db -c "REINDEX DATABASE langgraph_db;"

# 2. 更新统计信息
kubectl exec deployment/postgres -n langgraph-multi-agent -- \
  psql -U langgraph_user -d langgraph_db -c "ANALYZE;"

# 3. 清理过期数据
kubectl exec deployment/postgres -n langgraph-multi-agent -- \
  psql -U langgraph_user -d langgraph_db -c "
    DELETE FROM agent_messages WHERE created_at < NOW() - INTERVAL '30 days';
    DELETE FROM workflow_executions WHERE created_at < NOW() - INTERVAL '90 days' AND status = 'completed';"
```

### 2. Redis缓存问题

#### 内存不足
```bash
# 检查Redis内存使用
kubectl exec deployment/redis -n langgraph-multi-agent -- \
  redis-cli info memory

# 检查键数量
kubectl exec deployment/redis -n langgraph-multi-agent -- \
  redis-cli info keyspace

# 解决方案
# 1. 清理过期键
kubectl exec deployment/redis -n langgraph-multi-agent -- \
  redis-cli --scan --pattern "*" | head -1000 | xargs kubectl exec deployment/redis -n langgraph-multi-agent -- redis-cli del

# 2. 调整内存策略
kubectl exec deployment/redis -n langgraph-multi-agent -- \
  redis-cli config set maxmemory-policy allkeys-lru

# 3. 增加内存限制
kubectl patch deployment redis -n langgraph-multi-agent -p '
{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "redis",
          "resources": {
            "limits": {
              "memory": "2Gi"
            }
          }
        }]
      }
    }
  }
}'
```

## 网络和连接故障

### 1. 服务间通信问题

#### DNS解析失败
```bash
# 测试DNS解析
kubectl run dns-test --image=busybox --rm -it --restart=Never -n langgraph-multi-agent -- nslookup kubernetes.default.svc.cluster.local

# 检查CoreDNS状态
kubectl get pods -n kube-system -l k8s-app=kube-dns

# 解决方案
kubectl rollout restart deployment/coredns -n kube-system
```

#### 网络策略问题
```bash
# 检查网络策略
kubectl get networkpolicy -n langgraph-multi-agent

# 测试网络连接
kubectl run network-debug --image=nicolaka/netshoot --rm -it --restart=Never -n langgraph-multi-agent -- /bin/bash

# 在debug容器中测试
curl -v http://langgraph-multi-agent-service:8000/health
telnet postgres-service 5432
```

### 2. 外部访问问题

#### Ingress配置问题
```bash
# 检查Ingress状态
kubectl get ingress -n langgraph-multi-agent
kubectl describe ingress langgraph-ingress -n langgraph-multi-agent

# 检查Ingress控制器
kubectl get pods -n nginx-ingress
kubectl logs -n nginx-ingress deployment/nginx-ingress-controller

# 解决方案
# 1. 重新应用Ingress配置
kubectl apply -f k8s/ingress.yaml

# 2. 重启Ingress控制器
kubectl rollout restart deployment/nginx-ingress-controller -n nginx-ingress
```

## 性能问题

### 1. 响应时间过长

#### 诊断步骤
```bash
# 1. 检查API响应时间
time curl http://your-domain.com/api/v1/mvp2/tasks

# 2. 分析慢查询
kubectl exec deployment/postgres -n langgraph-multi-agent -- \
  psql -U langgraph_user -d langgraph_db -c "
    SELECT query, mean_time, calls 
    FROM pg_stat_statements 
    WHERE mean_time > 1000 
    ORDER BY mean_time DESC;"

# 3. 检查资源使用
kubectl top pods -n langgraph-multi-agent
kubectl top nodes
```

#### 优化方案
```bash
# 1. 数据库优化
kubectl exec deployment/postgres -n langgraph-multi-agent -- \
  psql -U langgraph_user -d langgraph_db -c "
    CREATE INDEX CONCURRENTLY idx_tasks_status_created ON tasks(status, created_at);
    CREATE INDEX CONCURRENTLY idx_workflow_executions_task_id ON workflow_executions(task_id);"

# 2. 应用层缓存
kubectl patch deployment langgraph-multi-agent -n langgraph-multi-agent -p '
{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "langgraph-multi-agent",
          "env": [{
            "name": "CACHE_TTL",
            "value": "3600"
          }, {
            "name": "CACHE_MAX_SIZE",
            "value": "10000"
          }]
        }]
      }
    }
  }
}'

# 3. 水平扩容
kubectl scale deployment langgraph-multi-agent --replicas=5 -n langgraph-multi-agent
```

### 2. 内存泄漏

#### 诊断步骤
```bash
# 监控内存使用趋势
kubectl top pods -n langgraph-multi-agent --sort-by=memory

# 查看内存使用历史
curl -G "http://prometheus:9090/api/v1/query_range" \
  --data-urlencode 'query=container_memory_usage_bytes{pod=~"langgraph-multi-agent.*"}' \
  --data-urlencode 'start='$(date -d '1 hour ago' +%s) \
  --data-urlencode 'end='$(date +%s) \
  --data-urlencode 'step=60'
```

#### 解决方案
```bash
# 1. 重启高内存使用的Pod
kubectl delete pod <high-memory-pod> -n langgraph-multi-agent

# 2. 调整内存限制
kubectl patch deployment langgraph-multi-agent -n langgraph-multi-agent -p '
{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "langgraph-multi-agent",
          "resources": {
            "limits": {
              "memory": "4Gi"
            }
          }
        }]
      }
    }
  }
}'

# 3. 启用内存监控
kubectl patch deployment langgraph-multi-agent -n langgraph-multi-agent -p '
{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "langgraph-multi-agent",
          "env": [{
            "name": "MEMORY_MONITORING",
            "value": "true"
          }]
        }]
      }
    }
  }
}'
```

## MVP2前端集成问题

### 1. 前端无法连接后端

#### 诊断步骤
```bash
# 1. 检查前端配置
curl http://mvp2.your-domain.com/config.js

# 2. 测试API连接
curl -v http://your-domain.com/api/v1/mvp2/health

# 3. 检查CORS配置
curl -H "Origin: http://mvp2.your-domain.com" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: X-Requested-With" \
     -X OPTIONS \
     http://your-domain.com/api/v1/mvp2/tasks
```

#### 解决方案
```bash
# 1. 更新CORS配置
kubectl patch deployment langgraph-multi-agent -n langgraph-multi-agent -p '
{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "langgraph-multi-agent",
          "env": [{
            "name": "CORS_ORIGINS",
            "value": "[\"http://mvp2.your-domain.com\", \"https://mvp2.your-domain.com\"]"
          }]
        }]
      }
    }
  }
}'

# 2. 重启服务
kubectl rollout restart deployment/langgraph-multi-agent -n langgraph-multi-agent
```

### 2. WebSocket连接问题

#### 诊断步骤
```bash
# 测试WebSocket连接
wscat -c ws://your-domain.com/api/v1/mvp2/ws

# 检查Nginx WebSocket配置
kubectl exec deployment/nginx -n langgraph-multi-agent -- nginx -T | grep -A 10 "location.*ws"
```

#### 解决方案
```bash
# 更新Nginx配置支持WebSocket
kubectl patch configmap nginx-config -n langgraph-multi-agent -p '
{
  "data": {
    "nginx.conf": "... WebSocket proxy configuration ..."
  }
}'

kubectl rollout restart deployment/nginx -n langgraph-multi-agent
```

## 预防措施

### 1. 监控告警配置

```yaml
# monitoring/alert-rules.yml
groups:
- name: langgraph-alerts
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "高错误率告警"
      description: "错误率超过10%"

  - alert: HighMemoryUsage
    expr: container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.8
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "内存使用率过高"
      description: "内存使用率超过80%"

  - alert: DatabaseConnectionFailure
    expr: up{job="postgres"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "数据库连接失败"
      description: "PostgreSQL数据库不可用"
```

### 2. 健康检查配置

```yaml
# 在deployment.yaml中添加健康检查
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3
```

### 3. 资源限制配置

```yaml
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

### 4. 定期维护脚本

```bash
#!/bin/bash
# maintenance.sh - 定期维护脚本

# 每日执行
if [ "$1" = "daily" ]; then
    # 清理过期日志
    kubectl exec deployment/postgres -n langgraph-multi-agent -- \
      psql -U langgraph_user -d langgraph_db -c "
        DELETE FROM agent_messages WHERE created_at < NOW() - INTERVAL '7 days';"
    
    # 清理Redis过期键
    kubectl exec deployment/redis -n langgraph-multi-agent -- redis-cli --scan --pattern "*:expired:*" | xargs kubectl exec deployment/redis -n langgraph-multi-agent -- redis-cli del
fi

# 每周执行
if [ "$1" = "weekly" ]; then
    # 数据库维护
    kubectl exec deployment/postgres -n langgraph-multi-agent -- \
      psql -U langgraph_user -d langgraph_db -c "VACUUM ANALYZE;"
    
    # 重启服务以释放内存
    kubectl rollout restart deployment/langgraph-multi-agent -n langgraph-multi-agent
fi
```

---

**重要提醒**: 
- 在执行任何故障排查操作前，请先备份重要数据
- 对于生产环境的问题，建议先在测试环境中验证解决方案
- 保持故障排查日志，便于后续分析和改进
- 定期更新本指南以包含新发现的问题和解决方案