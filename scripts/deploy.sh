#!/bin/bash

# LangGraph多智能体系统部署脚本
set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助信息
show_help() {
    cat << EOF
LangGraph多智能体系统部署脚本

用法: $0 [选项] <环境>

环境:
    dev         部署到开发环境
    staging     部署到测试环境
    prod        部署到生产环境
    local       本地Docker部署

选项:
    -h, --help              显示帮助信息
    -v, --version VERSION   指定部署版本 (默认: latest)
    -n, --namespace NS      指定Kubernetes命名空间 (默认: langgraph-multi-agent)
    -c, --config FILE       指定配置文件路径
    --dry-run              只显示将要执行的命令，不实际执行
    --skip-build           跳过镜像构建
    --skip-tests           跳过测试
    --force                强制部署，忽略健康检查

示例:
    $0 dev                          # 部署到开发环境
    $0 prod -v v1.2.3              # 部署指定版本到生产环境
    $0 local --skip-tests          # 本地部署，跳过测试
    $0 staging --dry-run           # 测试环境试运行

EOF
}

# 默认参数
ENVIRONMENT=""
VERSION="latest"
NAMESPACE="langgraph-multi-agent"
CONFIG_FILE=""
DRY_RUN=false
SKIP_BUILD=false
SKIP_TESTS=false
FORCE=false

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        dev|staging|prod|local)
            ENVIRONMENT="$1"
            shift
            ;;
        *)
            log_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

# 验证环境参数
if [[ -z "$ENVIRONMENT" ]]; then
    log_error "必须指定部署环境"
    show_help
    exit 1
fi

# 执行命令函数
execute_command() {
    local cmd="$1"
    local description="$2"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] $description"
        echo "  命令: $cmd"
        return 0
    fi
    
    log_info "$description"
    if eval "$cmd"; then
        log_success "$description 完成"
    else
        log_error "$description 失败"
        exit 1
    fi
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    local deps=("docker" "kubectl")
    if [[ "$ENVIRONMENT" == "local" ]]; then
        deps+=("docker-compose")
    fi
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            log_error "缺少依赖: $dep"
            exit 1
        fi
    done
    
    log_success "依赖检查通过"
}

# 运行测试
run_tests() {
    if [[ "$SKIP_TESTS" == "true" ]]; then
        log_warning "跳过测试"
        return 0
    fi
    
    log_info "运行测试..."
    execute_command "python -m pytest tests/ -v" "运行单元测试"
    execute_command "python -m pytest tests/integration/ -v" "运行集成测试"
}

# 构建镜像
build_image() {
    if [[ "$SKIP_BUILD" == "true" ]]; then
        log_warning "跳过镜像构建"
        return 0
    fi
    
    log_info "构建Docker镜像..."
    local image_tag="langgraph-multi-agent:$VERSION"
    
    execute_command "docker build -t $image_tag ." "构建Docker镜像"
    
    if [[ "$ENVIRONMENT" != "local" ]]; then
        execute_command "docker tag $image_tag ghcr.io/your-org/$image_tag" "标记镜像"
        execute_command "docker push ghcr.io/your-org/$image_tag" "推送镜像"
    fi
}

# 本地部署
deploy_local() {
    log_info "开始本地部署..."
    
    # 停止现有服务
    execute_command "docker-compose down" "停止现有服务"
    
    # 启动服务
    execute_command "docker-compose up -d" "启动服务"
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 30
    
    # 健康检查
    execute_command "curl -f http://localhost:8000/health" "健康检查"
    
    log_success "本地部署完成"
    log_info "访问地址:"
    log_info "  API: http://localhost:8000"
    log_info "  MVP2前端: http://localhost:80/mvp2/"
    log_info "  Grafana: http://localhost:3000"
    log_info "  Prometheus: http://localhost:9090"
}

# Kubernetes部署
deploy_kubernetes() {
    log_info "开始Kubernetes部署到 $ENVIRONMENT 环境..."
    
    # 设置配置文件
    local config_suffix=""
    case "$ENVIRONMENT" in
        dev)
            config_suffix="-dev"
            ;;
        staging)
            config_suffix="-staging"
            ;;
        prod)
            config_suffix="-prod"
            ;;
    esac
    
    # 应用配置
    execute_command "kubectl apply -f k8s/namespace.yaml" "创建命名空间"
    execute_command "kubectl apply -f k8s/configmap${config_suffix}.yaml" "应用配置"
    execute_command "kubectl apply -f k8s/secret${config_suffix}.yaml" "应用密钥"
    execute_command "kubectl apply -f k8s/pvc.yaml" "创建存储卷"
    
    # 更新镜像版本
    if [[ "$VERSION" != "latest" ]]; then
        execute_command "sed -i 's|langgraph-multi-agent:latest|langgraph-multi-agent:$VERSION|g' k8s/deployment.yaml" "更新镜像版本"
    fi
    
    # 部署应用
    execute_command "kubectl apply -f k8s/deployment.yaml" "部署应用"
    execute_command "kubectl apply -f k8s/service.yaml" "创建服务"
    execute_command "kubectl apply -f k8s/ingress.yaml" "配置Ingress"
    execute_command "kubectl apply -f k8s/hpa.yaml" "配置自动扩缩容"
    
    # 等待部署完成
    log_info "等待部署完成..."
    execute_command "kubectl rollout status deployment/langgraph-multi-agent -n $NAMESPACE --timeout=300s" "等待部署完成"
    
    # 健康检查
    if [[ "$FORCE" != "true" ]]; then
        execute_command "kubectl wait --for=condition=ready pod -l app=langgraph-multi-agent -n $NAMESPACE --timeout=300s" "等待Pod就绪"
    fi
    
    log_success "Kubernetes部署完成"
    
    # 显示访问信息
    log_info "获取访问信息..."
    kubectl get ingress -n "$NAMESPACE"
    kubectl get services -n "$NAMESPACE"
}

# 部署后验证
post_deploy_verification() {
    log_info "执行部署后验证..."
    
    case "$ENVIRONMENT" in
        local)
            execute_command "curl -f http://localhost:8000/health" "API健康检查"
            execute_command "curl -f http://localhost:8000/api/v1/mvp2/health" "MVP2适配器健康检查"
            ;;
        *)
            # Kubernetes环境的验证
            local service_url=$(kubectl get ingress -n "$NAMESPACE" -o jsonpath='{.items[0].spec.rules[0].host}')
            if [[ -n "$service_url" ]]; then
                execute_command "curl -f https://$service_url/health" "API健康检查"
                execute_command "curl -f https://$service_url/api/v1/mvp2/health" "MVP2适配器健康检查"
            fi
            ;;
    esac
    
    log_success "部署后验证完成"
}

# 主函数
main() {
    log_info "开始部署 LangGraph多智能体系统"
    log_info "环境: $ENVIRONMENT"
    log_info "版本: $VERSION"
    log_info "命名空间: $NAMESPACE"
    
    # 检查依赖
    check_dependencies
    
    # 运行测试
    run_tests
    
    # 构建镜像
    build_image
    
    # 根据环境执行部署
    case "$ENVIRONMENT" in
        local)
            deploy_local
            ;;
        dev|staging|prod)
            deploy_kubernetes
            ;;
        *)
            log_error "不支持的环境: $ENVIRONMENT"
            exit 1
            ;;
    esac
    
    # 部署后验证
    post_deploy_verification
    
    log_success "部署完成！"
}

# 执行主函数
main "$@"