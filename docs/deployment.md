# Deployment Guide

Complete guide for deploying ChainReaction to production environments.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Deployment Options](#deployment-options)
- [Configuration](#configuration)
- [Docker Deployment](#docker-deployment)
- [Cloud Deployment](#cloud-deployment)
- [Monitoring](#monitoring)
- [Security](#security)
- [Maintenance](#maintenance)

## Overview

ChainReaction consists of three main components for deployment:

1. **Backend API** (Python/FastAPI)
2. **Frontend Dashboard** (Next.js)
3. **Database** (Neo4j)

## Prerequisites

### Production Requirements

- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum (8GB recommended)
- 20GB disk space
- SSL certificate for HTTPS

### External Services

- OpenAI API key (for DSPy analysis)
- Tavily API key (for news monitoring)
- SMTP server (optional, for email alerts)

## Deployment Options

### 1. Docker Compose (Recommended)

Best for single-server deployments and small teams.

### 2. Kubernetes

Best for scalable, enterprise deployments.

### 3. Cloud Platform

Best for managed infrastructure (AWS, GCP, Azure).

## Configuration

### Environment Variables

Create a production `.env` file:

```bash
# Application
APP_ENV=production
APP_DEBUG=false
LOG_LEVEL=INFO
SECRET_KEY=your-secure-secret-key-here

# API
API_HOST=0.0.0.0
API_PORT=8000
API_KEY=your-production-api-key
CORS_ORIGINS=https://your-domain.com

# Neo4j
NEO4J_URI=bolt://neo4j:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-secure-neo4j-password

# OpenAI
OPENAI_API_KEY=sk-your-production-key

# News APIs
TAVILY_API_KEY=tvly-your-production-key

# Monitoring
MONITOR_INTERVAL=300
CONFIDENCE_THRESHOLD=0.7

# Security
RATE_LIMIT_PER_MINUTE=100
SESSION_TIMEOUT_MINUTES=60
```

### Secret Management

For production, use a secrets manager:

```bash
# AWS Secrets Manager
aws secretsmanager create-secret --name chainreaction/prod \
  --secret-string file://secrets.json

# HashiCorp Vault
vault kv put secret/chainreaction \
  api_key=your-key \
  neo4j_password=your-password
```

## Docker Deployment

### Dockerfile (Backend)

```dockerfile
# backend/Dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy source code
COPY src/ src/

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Dockerfile (Frontend)

```dockerfile
# frontend/Dockerfile
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["node", "server.js"]
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: 
      context: .
      dockerfile: backend/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - APP_ENV=production
      - NEO4J_URI=bolt://neo4j:7687
    env_file:
      - .env
    depends_on:
      neo4j:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - chainreaction
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend
    restart: unless-stopped
    networks:
      - chainreaction

  neo4j:
    image: neo4j:5-community
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
      - NEO4J_PLUGINS=["apoc"]
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    restart: unless-stopped
    networks:
      - chainreaction
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7474"]
      interval: 30s
      timeout: 10s
      retries: 5

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - backend
      - frontend
    restart: unless-stopped
    networks:
      - chainreaction

volumes:
  neo4j_data:
  neo4j_logs:

networks:
  chainreaction:
    driver: bridge
```

### Nginx Configuration

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8000;
    }

    upstream frontend {
        server frontend:3000;
    }

    server {
        listen 80;
        server_name your-domain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        ssl_certificate /etc/nginx/certs/fullchain.pem;
        ssl_certificate_key /etc/nginx/certs/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;

        # API routes
        location /api/ {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /health {
            proxy_pass http://backend;
        }

        # Frontend routes
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
```

### Deployment Commands

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f backend

# Scale services
docker-compose up -d --scale backend=3

# Stop services
docker-compose down
```

## Cloud Deployment

### AWS (ECS/Fargate)

1. Create ECR repositories:
```bash
aws ecr create-repository --repository-name chainreaction/backend
aws ecr create-repository --repository-name chainreaction/frontend
```

2. Push images:
```bash
aws ecr get-login-password | docker login --username AWS --password-stdin $AWS_ACCOUNT.dkr.ecr.$REGION.amazonaws.com

docker tag chainreaction-backend:latest $AWS_ACCOUNT.dkr.ecr.$REGION.amazonaws.com/chainreaction/backend:latest
docker push $AWS_ACCOUNT.dkr.ecr.$REGION.amazonaws.com/chainreaction/backend:latest
```

3. Create ECS task definition and service

### Google Cloud (Cloud Run)

```bash
# Build and push
gcloud builds submit --tag gcr.io/$PROJECT_ID/chainreaction-backend

# Deploy
gcloud run deploy chainreaction-backend \
  --image gcr.io/$PROJECT_ID/chainreaction-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Azure (Container Apps)

```bash
# Create container app environment
az containerapp env create \
  --name chainreaction-env \
  --resource-group myResourceGroup \
  --location eastus

# Deploy backend
az containerapp create \
  --name chainreaction-backend \
  --resource-group myResourceGroup \
  --environment chainreaction-env \
  --image chainreaction-backend:latest \
  --target-port 8000 \
  --ingress external
```

## Monitoring

### Health Checks

Configure load balancer health checks:

- **Endpoint:** `/health`
- **Interval:** 30 seconds
- **Timeout:** 10 seconds
- **Unhealthy threshold:** 3

### Logging

Use structured logging with log aggregation:

```yaml
# docker-compose.yml addition
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"
```

For cloud deployments, integrate with:
- AWS CloudWatch Logs
- Google Cloud Logging
- Azure Monitor Logs
- Datadog / New Relic

### Metrics

Key metrics to monitor:

| Metric            | Description           | Alert Threshold |
| ----------------- | --------------------- | --------------- |
| Request latency   | API response time     | > 500ms         |
| Error rate        | 5xx responses / total | > 1%            |
| Active risks      | Current risk count    | > 10            |
| Neo4j connections | Active DB connections | > 80% pool      |
| Memory usage      | Container memory      | > 80%           |
| CPU usage         | Container CPU         | > 70%           |

### Alerting

Configure alerts for:
- API errors (5xx status codes)
- High latency (> 500ms p95)
- Service unavailable
- Neo4j connection failures
- High memory/CPU usage

## Security

### API Security

1. **API Key Rotation**
```bash
# Generate new API key
openssl rand -base64 32

# Update in secrets manager
# Notify clients of rotation
```

2. **Rate Limiting**
```python
# Already configured in src/api/auth.py
RATE_LIMIT_PER_MINUTE = 100
```

3. **Input Validation**
- All inputs validated with Pydantic
- SQL/Cypher injection prevention
- XSS protection

### Network Security

1. **Firewall Rules**
```bash
# Allow only necessary ports
ufw allow 80/tcp
ufw allow 443/tcp
ufw deny 7687/tcp  # Neo4j internal only
```

2. **TLS Configuration**
- Minimum TLS 1.2
- Strong cipher suites
- HSTS enabled

### Access Control

1. **Principle of Least Privilege**
- API keys with specific roles
- Neo4j read-only users for dashboard

2. **Audit Logging**
- Log all API key usage
- Track data access patterns

## Maintenance

### Backup Procedures

```bash
# Neo4j backup
docker exec neo4j neo4j-admin dump --database=neo4j --to=/backups/neo4j-$(date +%Y%m%d).dump

# Export data
curl -X GET "http://localhost:8000/api/v1/export?format=json" \
  -H "X-API-Key: admin-key" > backup-$(date +%Y%m%d).json
```

### Update Procedures

```bash
# Pull latest images
docker-compose pull

# Rolling update
docker-compose up -d --no-deps backend

# Verify health
curl http://localhost:8000/health

# Rollback if needed
docker-compose up -d --no-deps backend:previous-tag
```

### Scaling

```bash
# Horizontal scaling
docker-compose up -d --scale backend=3

# Kubernetes scaling
kubectl scale deployment chainreaction-backend --replicas=5
```

### Database Maintenance

```bash
# Neo4j maintenance
docker exec neo4j neo4j-admin check-consistency --database=neo4j

# Clear old data
curl -X DELETE "http://localhost:8000/api/v1/cleanup?older_than=90d" \
  -H "X-API-Key: admin-key"
```

## Troubleshooting

### Common Issues

**Service won't start:**
```bash
# Check logs
docker-compose logs backend

# Verify environment
docker-compose config

# Check port conflicts
lsof -i :8000
```

**Database connection errors:**
```bash
# Test Neo4j connection
docker exec neo4j cypher-shell -u neo4j -p password "RETURN 1"

# Verify network
docker network inspect chainreaction_chainreaction
```

**High latency:**
```bash
# Check resource usage
docker stats

# Analyze slow queries
# Enable Neo4j query logging
```

### Recovery Procedures

**Restore from backup:**
```bash
# Stop services
docker-compose stop

# Restore Neo4j
docker exec neo4j neo4j-admin load --from=/backups/neo4j-backup.dump

# Restart services
docker-compose up -d
```
