# 生产环境部署指南

## 🎯 概述

本文档提供Local High-Availability Market Data Hub的完整生产环境部署指南，确保系统在生产环境中稳定、安全、高性能运行。

## 📋 生产环境要求

### 系统要求
- **操作系统**: Ubuntu 22.04 LTS 或 24.04 LTS (推荐)
- **内存**: 最低 8GB，推荐 16GB+
- **CPU**: 最低 4核，推荐 8核+ (vnpy CTP需要充足计算资源)
- **存储**: 最低 100GB SSD (数据库和日志)
- **网络**: 稳定的互联网连接，延迟 <50ms to CTP servers

### 软件依赖
- **Node.js**: 18.x LTS 或更高
- **Python**: 3.12.x (vnpy要求)
- **数据库**: MySQL 8.0+ 或 PostgreSQL 14+
- **Redis**: 6.2+ (缓存和会话管理)
- **Nginx**: 1.20+ (反向代理)
- **Docker**: 24.0+ (可选，推荐容器化部署)

## 🔐 安全配置

### 1. CTP账户安全配置

创建安全的环境变量文件：

```bash
# /home/mdhub/.env.production (安全位置)
# ===================================================================
# 生产环境配置
# ===================================================================
ENVIRONMENT=production
LOG_LEVEL=WARN

# ===================================================================
# CTP真实账户配置 (⚠️ 绝对机密)
# ===================================================================
ENABLE_CTP_MOCK=false

# CTP连接信息 - 从券商获取
CTP_BROKER_ID=9999        # 券商代码
CTP_USER_ID=your_user_id  # 用户账号
CTP_PASSWORD=your_password # 交易密码
CTP_AUTH_CODE=your_auth_code # 认证码
CTP_APP_ID=your_app_id    # 应用标识

# CTP服务器地址 (生产环境)
CTP_MD_SERVER=tcp://180.168.146.187:10211  # 行情服务器
CTP_TD_SERVER=tcp://180.168.146.187:10201  # 交易服务器

# ===================================================================
# 生产数据库配置
# ===================================================================
DATABASE_URL=mysql://mdhub_user:secure_password@localhost:3306/mdhub_prod
DATABASE_POOL_SIZE=20
DATABASE_ECHO=false

# ===================================================================
# 网络安全配置
# ===================================================================
API_HOST=127.0.0.1
API_PORT=8000
ZMQ_BIND_ADDRESS=tcp://127.0.0.1
ZMQ_PUBLISHER_PORT=5555

# ===================================================================
# Redis配置
# ===================================================================
REDIS_URL=redis://localhost:6379/0

# ===================================================================
# 性能优化配置
# ===================================================================
ZMQ_QUEUE_SIZE=50000
HEALTH_CHECK_INTERVAL_SECONDS=60
DATABASE_POOL_RECYCLE=7200
```

### 2. 文件权限设置

```bash
# 设置环境文件安全权限
sudo chown mdhub:mdhub /home/mdhub/.env.production
sudo chmod 600 /home/mdhub/.env.production

# 验证权限
ls -la /home/mdhub/.env.production
# 应显示: -rw------- 1 mdhub mdhub
```

## 🗄️ 数据库部署

### MySQL 生产环境设置

```bash
# 1. 安装MySQL
sudo apt update
sudo apt install mysql-server mysql-client

# 2. 安全配置
sudo mysql_secure_installation

# 3. 创建生产数据库和用户
sudo mysql -u root -p
```

```sql
-- 创建生产数据库
CREATE DATABASE mdhub_prod CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建专用用户
CREATE USER 'mdhub_user'@'localhost' IDENTIFIED BY 'secure_password_here';

-- 授权
GRANT ALL PRIVILEGES ON mdhub_prod.* TO 'mdhub_user'@'localhost';
FLUSH PRIVILEGES;

-- 优化配置 (添加到 /etc/mysql/mysql.conf.d/mysqld.cnf)
```

```ini
# MySQL生产环境优化配置
[mysqld]
# 性能优化
innodb_buffer_pool_size = 4G          # 设为物理内存的70-80%
innodb_log_file_size = 512M
innodb_flush_log_at_trx_commit = 2     # 平衡性能和安全
max_connections = 200
query_cache_size = 256M

# 安全配置
bind-address = 127.0.0.1
skip-networking = false
sql_mode = STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO

# 字符集
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
```

### Redis部署

```bash
# 安装Redis
sudo apt install redis-server

# 配置Redis (/etc/redis/redis.conf)
sed -i 's/^# maxmemory <bytes>/maxmemory 2gb/' /etc/redis/redis.conf
sed -i 's/^# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/' /etc/redis/redis.conf

# 启动Redis
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

## 🚀 应用部署

### 1. 系统用户创建

```bash
# 创建专用用户
sudo useradd -m -s /bin/bash mdhub
sudo usermod -aG sudo mdhub  # 可选：如需sudo权限

# 切换到mdhub用户
sudo su - mdhub
```

### 2. 代码部署

```bash
# 克隆代码到生产服务器
cd /home/mdhub
git clone https://github.com/your-org/xiaoy_mdhub.git
cd xiaoy_mdhub

# 安装依赖
npm run install:all
npm run setup:vnpy

# 构建生产版本
npm run build
```

### 3. 环境配置

```bash
# 复制并配置环境文件
cp apps/api/.env.example /home/mdhub/.env.production
cp apps/web/.env.example /home/mdhub/.env.web.production

# 编辑生产环境配置
nano /home/mdhub/.env.production
nano /home/mdhub/.env.web.production
```

### 4. 数据库初始化

```bash
# 运行数据库迁移
cd apps/api
python -m alembic upgrade head

# 验证数据库连接
python -c "
from app.services.database_service import DatabaseService
db = DatabaseService()
print('Database connection:', 'SUCCESS' if db.health_check() else 'FAILED')
"
```

## 🔄 进程管理 (使用systemd)

### 1. API服务配置

创建 `/etc/systemd/system/mdhub-api.service`:

```ini
[Unit]
Description=Market Data Hub API Service
After=network.target mysql.service redis.service
Wants=mysql.service redis.service

[Service]
Type=exec
User=mdhub
Group=mdhub
WorkingDirectory=/home/mdhub/xiaoy_mdhub/apps/api
Environment=PATH=/home/mdhub/xiaoy_mdhub/apps/api/.venv/bin
EnvironmentFile=/home/mdhub/.env.production
ExecStart=/home/mdhub/xiaoy_mdhub/apps/api/.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

# 安全限制
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=strict
ReadWritePaths=/home/mdhub/xiaoy_mdhub/apps/api/logs

[Install]
WantedBy=multi-user.target
```

### 2. Web服务配置

创建 `/etc/systemd/system/mdhub-web.service`:

```ini
[Unit]
Description=Market Data Hub Web Service
After=network.target mdhub-api.service
Wants=mdhub-api.service

[Service]
Type=exec
User=mdhub
Group=mdhub
WorkingDirectory=/home/mdhub/xiaoy_mdhub/apps/web
Environment=PATH=/home/mdhub/xiaoy_mdhub/node_modules/.bin
Environment=NODE_ENV=production
EnvironmentFile=/home/mdhub/.env.web.production
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 3. 启动服务

```bash
# 重载systemd配置
sudo systemctl daemon-reload

# 启动并启用服务
sudo systemctl enable mdhub-api mdhub-web
sudo systemctl start mdhub-api mdhub-web

# 检查服务状态
sudo systemctl status mdhub-api mdhub-web
```

## 🌐 Nginx反向代理配置

### 安装Nginx

```bash
sudo apt install nginx
```

### 配置文件 `/etc/nginx/sites-available/mdhub`

```nginx
# Market Data Hub Nginx Configuration
upstream mdhub_api {
    server 127.0.0.1:8000;
    keepalive 32;
}

upstream mdhub_web {
    server 127.0.0.1:3000;
    keepalive 32;
}

# HTTP到HTTPS重定向
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS主配置
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL证书配置
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;
    
    # 现代SSL配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # 安全头
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    # API代理
    location /api/ {
        proxy_pass http://mdhub_api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 10s;
    }
    
    # WebSocket代理
    location /ws {
        proxy_pass http://mdhub_api/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
    
    # 前端应用
    location / {
        proxy_pass http://mdhub_web;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 10s;
    }
    
    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        proxy_pass http://mdhub_web;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### 启用配置

```bash
# 启用站点
sudo ln -s /etc/nginx/sites-available/mdhub /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx
```

## 📊 监控和日志

### 1. 日志配置

创建日志目录和轮转配置：

```bash
# 创建日志目录
sudo mkdir -p /var/log/mdhub
sudo chown mdhub:mdhub /var/log/mdhub

# 配置logrotate (/etc/logrotate.d/mdhub)
sudo tee /etc/logrotate.d/mdhub << EOF
/var/log/mdhub/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 mdhub mdhub
    postrotate
        systemctl reload mdhub-api mdhub-web
    endscript
}
EOF
```

### 2. 健康检查脚本

创建 `/home/mdhub/scripts/health-check.sh`:

```bash
#!/bin/bash

# 健康检查脚本
LOG_FILE="/var/log/mdhub/health-check.log"
API_URL="http://127.0.0.1:8000/health"
WEB_URL="http://127.0.0.1:3000"

echo "$(date): Starting health check" >> $LOG_FILE

# 检查API服务
if curl -f $API_URL > /dev/null 2>&1; then
    echo "$(date): API service OK" >> $LOG_FILE
else
    echo "$(date): API service FAILED" >> $LOG_FILE
    systemctl restart mdhub-api
fi

# 检查Web服务
if curl -f $WEB_URL > /dev/null 2>&1; then
    echo "$(date): Web service OK" >> $LOG_FILE
else
    echo "$(date): Web service FAILED" >> $LOG_FILE
    systemctl restart mdhub-web
fi

# 检查数据库连接
cd /home/mdhub/xiaoy_mdhub/apps/api
if python -c "from app.services.database_service import DatabaseService; db = DatabaseService(); exit(0 if db.health_check() else 1)"; then
    echo "$(date): Database OK" >> $LOG_FILE
else
    echo "$(date): Database FAILED" >> $LOG_FILE
fi
```

### 3. 定时任务设置

```bash
# 添加crontab任务
crontab -e

# 添加以下行：
# 每5分钟健康检查
*/5 * * * * /home/mdhub/scripts/health-check.sh

# 每天凌晨2点备份数据库
0 2 * * * /home/mdhub/scripts/backup-database.sh
```

## 🔒 安全最佳实践

### 1. 防火墙配置

```bash
# 启用UFW防火墙
sudo ufw enable

# 允许必要端口
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 拒绝其他端口（包括8000, 3000直接访问）
sudo ufw deny 8000
sudo ufw deny 3000
```

### 2. 自动更新配置

```bash
# 安装unattended-upgrades
sudo apt install unattended-upgrades

# 配置自动安全更新
sudo dpkg-reconfigure unattended-upgrades
```

### 3. 备份策略

创建 `/home/mdhub/scripts/backup-database.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/home/mdhub/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="mdhub_prod"

mkdir -p $BACKUP_DIR

# 数据库备份
mysqldump -u mdhub_user -p$DB_PASSWORD $DB_NAME | gzip > $BACKUP_DIR/mdhub_${DATE}.sql.gz

# 保留最近30天的备份
find $BACKUP_DIR -name "mdhub_*.sql.gz" -mtime +30 -delete

echo "$(date): Database backup completed: mdhub_${DATE}.sql.gz"
```

## 🚀 部署验证清单

### 部署前检查
- [ ] 服务器硬件配置满足要求
- [ ] 所有软件依赖已安装
- [ ] CTP账户信息已准备且测试通过
- [ ] 数据库已创建并配置
- [ ] SSL证书已申请并配置
- [ ] 防火墙规则已设置

### 部署后验证
- [ ] 所有systemd服务正常运行
- [ ] API健康检查通过: `curl https://your-domain.com/api/health`
- [ ] Web界面可正常访问: `https://your-domain.com`
- [ ] WebSocket连接正常工作
- [ ] CTP连接状态正常（非模拟模式）
- [ ] 数据库连接和查询正常
- [ ] 日志文件正常生成
- [ ] 监控和告警配置完成

### 性能验证
- [ ] 市场数据延迟 <5ms
- [ ] WebSocket连接稳定不断线
- [ ] 数据库查询响应时间 <100ms
- [ ] 内存使用在正常范围
- [ ] CPU使用率在可接受范围

## 🆘 故障排除

### 常见问题和解决方案

**1. CTP连接失败**
```bash
# 检查CTP配置
grep CTP_ /home/mdhub/.env.production

# 查看CTP连接日志
sudo journalctl -u mdhub-api -f | grep CTP
```

**2. 数据库连接问题**
```bash
# 测试数据库连接
mysql -u mdhub_user -p -h localhost mdhub_prod

# 检查数据库服务状态
sudo systemctl status mysql
```

**3. 高内存使用**
```bash
# 检查进程内存使用
ps aux --sort=-%mem | head

# 检查vnpy进程
ps aux | grep python
```

**4. WebSocket连接问题**
```bash
# 检查WebSocket日志
sudo journalctl -u mdhub-api -f | grep websocket

# 测试WebSocket连接
wscat -c ws://localhost:8000/ws
```

## 📞 紧急联系和支持

### 生产环境监控
- **服务状态**: `sudo systemctl status mdhub-api mdhub-web`
- **实时日志**: `sudo journalctl -u mdhub-api -f`
- **系统资源**: `htop`, `iotop`, `free -h`

### 紧急停止程序
```bash
# 停止所有服务
sudo systemctl stop mdhub-api mdhub-web

# 紧急情况下杀死进程
sudo pkill -f "uvicorn main:app"
sudo pkill -f "npm start"
```

---

**📧 技术支持**: 如遇到部署问题，请查看日志文件并联系技术团队。

**⚠️ 重要提醒**: 生产环境部署前，请务必在测试环境完全验证所有功能！