# 部署指南

本文档详细说明了 LangGraph 多智能体系统的部署方案和最佳实践。

## 📋 部署前准备

### 系统要求

**最低配置:**
- CPU: 2 核心
- 内存: 4GB RAM
- 存储: 10GB 可用空间
- 网络: 100Mbps

**推荐配置:**
- CPU: 4+ 核心
- 内存: 8GB+ RAM
- 存储: 50GB+ SSD
- 网络: 1Gbps

### 软件依赖

- Python 3.9+
- pip 21.0+
- Git 2.0+
- (可选) Docker 20.10+
- (可选) Docker Compose 1.29+

## 🐳 Docker 部署

### 1. 创建 Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY pyproject.toml ./

# 安装 Python 依赖
RUN pip install --no-cache-dir -e .

# 复制应用代码
COPY . .

# 创建必要目录
RUN mkdir -p logs checkpoints config

# 设置环境变量
ENV PYTHONPATH=/app
ENV ENVIRONMENT=production

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["python", "scripts/start_system.py", "--env", "production", "--mode", "daemon"]
```

### 2. 创建 docker-compose.yml

```yaml
version: '3.8'

services:
  agent-system:
    build: .
    container_name: langgraph-agent-system
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    volumes:
      - ./config:/app/config:ro
      - ./logs:/app/logs
      - ./data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  # 可选：数据库
  postgres:
    image: postgres:13
    container_name: agent-system-db
    environment:
      - POSTGRES_DB=agent_system
      - POSTGRES_USER=agent_user
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  # 可选：Redis
  redis:
    image: redis:6-alpine
    container_name: agent-system-redis
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### 3. 部署命令

```bash
# 构建和启动
docker-compose up -d

# 查看日志
docker-compose logs -f agent-system

# 停止服务
docker-compose down

# 重新构建
docker-compose up -d --build
```

## 🖥️ 直接部署

### 1. 环境准备

```bash
# 创建用户
sudo useradd -m -s /bin/bash agent-system
sudo su - agent-system

# 安装 Python 3.9+
sudo apt update
sudo apt install python3.9 python3.9-pip python3.9-venv

# 创建虚拟环境
python3.9 -m venv venv
source venv/bin/activate
```

### 2. 安装应用

```bash
# 克隆代码
git clone <repository-url>
cd langgraph-agent-system

# 安装依赖
pip install -e .

# 创建必要目录
mkdir -p logs checkpoints data
```

### 3. 配置系统

```bash
# 复制配置文件
cp config/production.yaml config/local.yaml

# 编辑配置
nano config/local.yaml
```

### 4. 创建 systemd 服务

```bash
# 创建服务文件
sudo nano /etc/systemd/system/agent-system.service
```

```ini
[Unit]
Description=LangGraph Agent System
After=network.target

[Service]
Type=simple
User=agent-system
Group=agent-system
WorkingDirectory=/home/agent-system/langgraph-agent-system
Environment=PATH=/home/agent-system/langgraph-agent-system/venv/bin
Environment=ENVIRONMENT=production
ExecStart=/home/agent-system/langgraph-agent-system/venv/bin/python scripts/start_system.py --env production --mode daemon
Restart=always
RestartSec=10

# 日志配置
StandardOutput=journal
StandardError=journal
SyslogIdentifier=agent-system

[Install]
WantedBy=multi-user.target
```

```bash
# 启用和启动服务
sudo systemctl daemon-reload
sudo systemctl enable agent-system
sudo systemctl start agent-system

# 查看状态
sudo systemctl status agent-system

# 查看日志
sudo journalctl -u agent-system -f
```

## 🔧 反向代理配置

### Nginx 配置

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/your/cert.pem;
    ssl_certificate_key /path/to/your/key.pem;

    # 安全头
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

    # 限制请求大小
    client_max_body_size 10M;

    # 代理到应用
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 健康检查端点
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }

    # 静态文件（如果有）
    location /static/ {
        alias /path/to/static/files/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # 日志
    access_log /var/log/nginx/agent-system-access.log;
    error_log /var/log/nginx/agent-system-error.log;
}
```

## 🔒 安全配置

### 1. 防火墙设置

```bash
# UFW 配置
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 2. SSL/TLS 证书

```bash
# 使用 Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo crontab -e
# 添加以下行：
# 0 12 * * * /usr/bin/certbot renew --quiet
```

### 3. 环境变量安全

```bash
# 创建环境变量文件
nano .env
```

```bash
SECRET_KEY=your-very-secure-secret-key-here
DATABASE_URL=postgresql://user:password@localhost/agent_system
REDIS_URL=redis://localhost:6379
LOG_LEVEL=INFO
```

```bash
# 设置文件权限
chmod 600 .env
```

## 📊 监控和日志

### 1. 日志管理

```bash
# 创建日志轮转配置
sudo nano /etc/logrotate.d/agent-system
```

```
/home/agent-system/langgraph-agent-system/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 agent-system agent-system
    postrotate
        systemctl reload agent-system
    endscript
}
```

### 2. 系统监控

```bash
# 安装监控工具
sudo apt install htop iotop

# 查看系统资源
htop
iotop
df -h
free -h
```

### 3. 应用监控

使用内置的健康检查端点：

```bash
# 基本健康检查
curl http://localhost:8000/health

# 详细系统信息
curl http://localhost:8000/health/system

# 性能指标
curl http://localhost:8000/health/metrics
```

## 🔄 备份和恢复

### 1. 数据备份

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/agent-system"
DATE=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份配置文件
tar -czf $BACKUP_DIR/config_$DATE.tar.gz config/

# 备份数据库（如果使用）
# pg_dump agent_system > $BACKUP_DIR/database_$DATE.sql

# 备份应用数据
tar -czf $BACKUP_DIR/data_$DATE.tar.gz data/

# 清理旧备份（保留7天）
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
```

### 2. 恢复流程

```bash
#!/bin/bash
# restore.sh

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

# 停止服务
sudo systemctl stop agent-system

# 恢复数据
tar -xzf $BACKUP_FILE -C /

# 恢复数据库（如果需要）
# psql agent_system < database_backup.sql

# 启动服务
sudo systemctl start agent-system

echo "Restore completed"
```

## 🚀 性能优化

### 1. 系统调优

```bash
# 内核参数优化
sudo nano /etc/sysctl.conf
```

```
# 网络优化
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 1200

# 文件系统优化
fs.file-max = 2097152
fs.inotify.max_user_watches = 524288
```

### 2. 应用优化

在 `config/production.yaml` 中调整：

```yaml
# 增加工作进程数
server:
  workers: 8

# 优化消息队列
message_bus:
  max_queue_size: 5000
  processing_interval_seconds: 0.001

# 增加并发任务数
task_manager:
  max_concurrent_tasks: 500
```

## 🔍 故障排除

### 常见问题和解决方案

1. **服务无法启动**
   ```bash
   # 检查日志
   sudo journalctl -u agent-system -n 50

   # 检查配置
   python -c "from src.core.config import ConfigManager; print(ConfigManager().load_config('production'))"
   ```

2. **内存不足**
   ```bash
   # 检查内存使用
   free -h

   # 优化配置，减少并发数
   ```

3. **数据库连接问题**
   ```bash
   # 检查数据库状态
   sudo systemctl status postgresql

   # 测试连接
   psql -h localhost -U agent_user -d agent_system
   ```

4. **网络问题**
   ```bash
   # 检查端口占用
   netstat -tlnp | grep :8000

   # 检查防火墙
   sudo ufw status
   ```

## 📞 支持

如果遇到部署问题，请：

1. 查看日志文件获取详细错误信息
2. 检查配置文件语法
3. 验证系统要求是否满足
4. 参考故障排除章节

更多支持：
- 📧 Email: support@example.com
- 📖 文档: [项目文档](README.md)
- 🐛 问题报告: [GitHub Issues](https://github.com/your-repo/issues)