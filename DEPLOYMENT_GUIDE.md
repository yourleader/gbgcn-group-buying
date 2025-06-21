# 🚀 GBGCN Group Buying System - Deployment Guide

Complete deployment guide for the Group-Buying Graph Convolutional Network (GBGCN) system based on the research paper "Group-Buying Recommendation for Social E-Commerce".

## 📋 Prerequisites

### System Requirements
- **OS**: Linux/macOS/Windows with WSL2
- **Memory**: 8GB RAM minimum (16GB recommended)
- **Storage**: 10GB free space
- **CPU**: 4+ cores recommended

### Software Dependencies
- **Docker**: 20.10+ and Docker Compose 2.0+
- **Python**: 3.9+ (for development)
- **PostgreSQL**: 13+ (managed via Docker)
- **Redis**: 6.2+ (managed via Docker)

## 🔧 Quick Deployment

### 1. Clone and Setup
```bash
# Clone the repository
git clone <repository-url>
cd groupbuy

# Make scripts executable
chmod +x scripts/*.sh

# Run complete setup
./scripts/quick_start.sh
```

### 2. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

### Key Environment Variables:
```env
# Database
DATABASE_URL=postgresql+asyncpg://groupbuy:password@localhost:5432/groupbuy
POSTGRES_USER=groupbuy
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=groupbuy

# Redis
REDIS_URL=redis://localhost:6379/0

# API
API_PORT=8000
API_HOST=0.0.0.0
SECRET_KEY=your_very_secure_secret_key
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# GBGCN Model Configuration
EMBEDDING_DIM=64
NUM_GCN_LAYERS=3
DROPOUT_RATE=0.1
LEARNING_RATE=0.001
ALPHA=0.6
BETA=0.4
MAX_EPOCHS=500
PATIENCE=20
BATCH_SIZE=512

# Business Rules
MIN_GROUP_SIZE=2
MAX_GROUP_SIZE=100
DEFAULT_GROUP_DURATION_DAYS=7
MIN_DISCOUNT_PERCENTAGE=0.05
MAX_DISCOUNT_PERCENTAGE=0.5
MODEL_RETRAIN_INTERVAL=86400  # 24 hours
```

### 3. Start Services
```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api
```

## 🐳 Docker Deployment

### Production Docker Compose
```yaml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:13
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Redis Cache
  redis:
    image: redis:6.2-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  # GBGCN API
  api:
    build: .
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
    ports:
      - "${API_PORT}:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./models:/app/models
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Background Worker (Celery)
  worker:
    build: .
    command: celery -A src.api.main worker --loglevel=info
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - postgres
      - redis
    volumes:
      - ./models:/app/models
      - ./logs:/app/logs
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

## ☁️ Cloud Deployment

### AWS Deployment

#### 1. ECS Deployment
```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com

docker build -t groupbuy-api .
docker tag groupbuy-api:latest <account>.dkr.ecr.us-east-1.amazonaws.com/groupbuy-api:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/groupbuy-api:latest

# Deploy using ECS task definition
aws ecs update-service --cluster groupbuy-cluster --service groupbuy-api --task-definition groupbuy-api:1
```

#### 2. RDS Configuration
```bash
# Create RDS PostgreSQL instance
aws rds create-db-instance \
  --db-instance-identifier groupbuy-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username groupbuy \
  --master-user-password your_password \
  --allocated-storage 20 \
  --vpc-security-group-ids sg-xxxxxxxx
```

#### 3. ElastiCache Redis
```bash
# Create Redis cluster
aws elasticache create-cache-cluster \
  --cache-cluster-id groupbuy-redis \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --num-cache-nodes 1
```

### Google Cloud Platform

#### 1. Cloud Run Deployment
```bash
# Build and deploy
gcloud builds submit --tag gcr.io/PROJECT_ID/groupbuy-api
gcloud run deploy groupbuy-api \
  --image gcr.io/PROJECT_ID/groupbuy-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

#### 2. Cloud SQL
```bash
# Create PostgreSQL instance
gcloud sql instances create groupbuy-db \
  --database-version POSTGRES_13 \
  --tier db-f1-micro \
  --region us-central1
```

### Kubernetes Deployment

#### 1. Kubernetes Manifests
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: groupbuy-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: groupbuy-api
  template:
    metadata:
      labels:
        app: groupbuy-api
    spec:
      containers:
      - name: api
        image: groupbuy-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: groupbuy-secrets
              key: database-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

#### 2. Deploy to Kubernetes
```bash
# Deploy to cluster
kubectl apply -f k8s/
kubectl expose deployment groupbuy-api --type=LoadBalancer --port=80 --target-port=8000
```

## 🔐 Security Configuration

### 1. SSL/TLS Setup
```bash
# Using Let's Encrypt with Certbot
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### 2. Firewall Configuration
```bash
# UFW setup
sudo ufw enable
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 5432/tcp   # PostgreSQL (internal only)
sudo ufw deny 6379/tcp   # Redis (internal only)
```

### 3. Environment Security
```bash
# Generate secure secrets
python -c "import secrets; print(secrets.token_urlsafe(32))"  # SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(16))"  # DB_PASSWORD
```

## 📊 Monitoring and Logging

### 1. Health Checks
```bash
# API health endpoint
curl http://localhost:8000/health

# GBGCN model status
curl http://localhost:8000/model/status
```

### 2. Logging Configuration
```yaml
# docker-compose.override.yml
version: '3.8'
services:
  api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 3. Prometheus Metrics
```python
# Add to main.py
from prometheus_fastapi_instrumentator import Instrumentator

instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)
```

## 🚀 Performance Optimization

### 1. Database Optimization
```sql
-- Create indexes for performance
CREATE INDEX idx_user_item_interactions_user_id ON user_item_interactions(user_id);
CREATE INDEX idx_group_members_group_id ON group_members(group_id);
CREATE INDEX idx_social_connections_user_id ON social_connections(user_id);
CREATE INDEX idx_groups_status_end_time ON groups(status, end_time);
```

### 2. Redis Caching
```python
# Cache configuration
REDIS_CACHE_TTL = 3600  # 1 hour
REDIS_MODEL_CACHE_TTL = 86400  # 24 hours
```

### 3. API Rate Limiting
```python
# Add rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Database Connection Issues
```bash
# Check PostgreSQL status
docker-compose logs postgres

# Test connection
docker-compose exec postgres psql -U groupbuy -d groupbuy -c "SELECT 1;"
```

#### 2. GBGCN Model Issues
```bash
# Check model logs
docker-compose logs api | grep GBGCN

# Verify model files
ls -la models/gbgcn/
```

#### 3. Performance Issues
```bash
# Monitor resource usage
docker stats

# Check database performance
docker-compose exec postgres psql -U groupbuy -d groupbuy -c "SELECT * FROM pg_stat_activity;"
```

### Debugging Commands
```bash
# Enter container for debugging
docker-compose exec api bash

# View real-time logs
docker-compose logs -f --tail=100 api

# Check database schema
docker-compose exec postgres psql -U groupbuy -d groupbuy -c "\dt"
```

## 📈 Scaling

### Horizontal Scaling
```yaml
# Scale API instances
services:
  api:
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
```

### Load Balancing
```nginx
# nginx.conf
upstream groupbuy_api {
    server api1:8000;
    server api2:8000;
    server api3:8000;
}

server {
    listen 80;
    location / {
        proxy_pass http://groupbuy_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🧪 Testing Deployment

### 1. Smoke Tests
```bash
# Run deployment smoke tests
python scripts/test_deployment.py
```

### 2. Load Testing
```bash
# Install hey for load testing
go install github.com/rakyll/hey@latest

# Test API under load
hey -n 1000 -c 10 http://localhost:8000/health
```

### 3. Integration Tests
```bash
# Run full test suite
pytest tests/ -v --tb=short
```

## 📚 Additional Resources

- **API Documentation**: http://localhost:8000/docs
- **GBGCN Paper**: [Group-Buying Recommendation for Social E-Commerce](groupBuyPaper.pdf)
- **Implementation Summary**: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- **Quick Start Guide**: [README.md](README.md)

## 📞 Support

For deployment issues:
1. Check logs: `docker-compose logs`
2. Verify configuration: `docker-compose config`
3. Test connectivity: `docker-compose exec api curl http://localhost:8000/health`
4. Review documentation: API_DOCUMENTATION.md

---

**Note**: This deployment guide covers production-ready deployment scenarios. For development setup, see [README.md](README.md). 