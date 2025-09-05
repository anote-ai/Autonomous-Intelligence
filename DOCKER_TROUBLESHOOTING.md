# Docker Compose & Kubernetes Troubleshooting Guide

## 🐳 Docker Compose & Networking

### 1. Running Datadog Agent in Docker Compose

**Problem**: How to monitor containers with Datadog Agent

**Solution**: Add Datadog Agent service to your docker-compose.yml:

```yaml
datadog-agent:
  image: gcr.io/datadoghq/agent:latest
  container_name: datadog-agent
  restart: unless-stopped
  environment:
    - DD_API_KEY=${DD_API_KEY:-your-datadog-api-key}
    - DD_SITE=us5.datadoghq.com
    - DD_LOGS_ENABLED=true
    - DD_APM_ENABLED=true
    - DD_DOGSTATSD_NON_LOCAL_TRAFFIC=true
  ports:
    - "8126:8126"  # APM traces
    - "8125:8125/udp"  # DogStatsD metrics
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
    - /proc/:/host/proc/:ro
    - /sys/fs/cgroup/:/host/sys/fs/cgroup:ro
  networks:
    - anote-network
```

**Environment Setup**:
```bash
# Create .env file in backend directory
echo "DD_API_KEY=your-actual-datadog-api-key" >> backend/.env
```

### 2. Fixing Port Conflicts

**Problem**: "Port 6379 already allocated" or "Port 3000 already allocated"

**Common Causes**:
- Another service using the same port
- Previous containers still running
- Ray and Redis both trying to use port 6379

**Solutions**:

```bash
# Check what's using the port
lsof -i :6379
lsof -i :3000

# Stop all containers
docker-compose down

# Remove orphaned containers
docker-compose down --remove-orphans

# Check for running containers
docker ps

# Kill specific containers if needed
docker kill <container-name>
```

**Port Mapping Strategy**:
- Backend Flask: `8000:5000` (host:container)
- Redis: `6379:6379`
- Ray Dashboard: `10001:10001` (avoid conflict with Redis)
- Frontend: `3000:3000`
- Datadog APM: `8126:8126`
- Datadog StatsD: `8125:8125/udp`

### 3. Connecting Frontend and Backend Containers

**Problem**: Frontend can't reach backend API

**Solution**: Use Docker service names in the same network

**Backend docker-compose.yml**:
```yaml
services:
  backend:
    # ... other config
    networks:
      - anote-network

networks:
  anote-network:
    driver: bridge
```

**Frontend docker-compose.yml**:
```yaml
services:
  frontend:
    environment:
      - REACT_APP_BACK_END_HOST=http://backend:5000  # Use service name
    networks:
      - anote-network

networks:
  anote-network:
    external: true  # Reference the network from backend
```

**Key Points**:
- Use service names (`backend`, `redis`) instead of `localhost`
- Both services must be on the same network (`anote-network`)
- Frontend uses `external: true` to reference backend's network

### 4. Troubleshooting Frontend-Backend Connectivity

**Common Issues & Solutions**:

1. **Network not found**:
```bash
# Create the network first
docker network create anote-network

# Or start backend first, then frontend
docker-compose -f backend/docker-compose.yml up -d
docker-compose -f frontend/docker-compose.yml up -d
```

2. **CORS errors**:
```python
# In backend/app.py, ensure CORS is configured:
from flask_cors import CORS
CORS(app, origins=["http://localhost:3000", "http://frontend:3000"])
```

3. **DNS resolution issues**:
```bash
# Test connectivity from frontend container
docker exec -it <frontend-container> ping backend
docker exec -it <frontend-container> curl http://backend:5000/health
```

4. **Environment variable not set**:
```bash
# Check environment variables in container
docker exec -it <frontend-container> env | grep REACT_APP
```

## 🐍 Python & Dependency Issues

### 1. Python Version Compatibility

**Problem**: `unsupported operand type(s) for |: type and type` (Python 3.9 vs 3.10+)

**Error Example**:
```python
# This requires Python 3.10+
def process_file(file_path: str | Path) -> str:
    pass
```

**Solution**: Upgrade Dockerfile to Python 3.10+

```dockerfile
# Change from:
FROM python:3.9-slim

# To:
FROM python:3.10-slim
```

**Alternative**: Use Union types for Python 3.9:
```python
from typing import Union
from pathlib import Path

def process_file(file_path: Union[str, Path]) -> str:
    pass
```

### 2. Missing Git Executable

**Problem**: Libraries like `ragas` and `gitpython` require git

**Error**: `git executable not found`

**Solution**: Add git to Dockerfile:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-jdk \
    pkg-config \
    default-libmysqlclient-dev \
    git \  # Add this line
    curl \  # Add this line
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean
```

### 3. Dependency Installation Issues

**Common Problems**:

1. **Build tools missing**:
```dockerfile
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*
```

2. **Memory issues during pip install**:
```dockerfile
# Install heavy packages separately
RUN pip install --no-cache-dir torch==2.2.2
RUN pip install --no-cache-dir transformers==4.40.1
RUN pip install --no-cache-dir -r requirements.txt
```

3. **Version conflicts**:
```bash
# Check for conflicts
pip check

# Update specific packages
pip install --upgrade package-name
```

## ☸️ Kubernetes Troubleshooting

### 1. Checking Pod Logs

**Problem**: Pod not found or can't get logs

**Commands**:

```bash
# List all pods in namespace
kubectl get pods -n anote-local

# Get logs for specific pod
kubectl logs <pod-name> -n anote-local

# Get logs for specific container in pod
kubectl logs <pod-name> -c <container-name> -n anote-local

# Follow logs in real-time
kubectl logs -f <pod-name> -n anote-local

# Get logs from previous container instance
kubectl logs <pod-name> --previous -n anote-local
```

### 2. Common Kubernetes Issues

**Pod Status Issues**:

1. **ImagePullBackOff**:
```bash
# Check image exists
kubectl describe pod <pod-name> -n anote-local

# For local images, ensure imagePullPolicy: Never
```

2. **CrashLoopBackOff**:
```bash
# Check logs for crash reason
kubectl logs <pod-name> -n anote-local

# Check pod events
kubectl describe pod <pod-name> -n anote-local
```

3. **Pending**:
```bash
# Check resource constraints
kubectl describe pod <pod-name> -n anote-local

# Check node resources
kubectl top nodes
```

### 3. Ray and Flask Startup Issues

**Common Ray Issues**:

1. **Ray head node not starting**:
```bash
# Check Ray logs
kubectl logs <backend-pod> -n anote-local | grep -i ray

# Common fixes:
# - Ensure port 10001 is available
# - Check memory requirements
# - Verify Ray version compatibility
```

2. **Flask app not starting**:
```bash
# Check Flask logs
kubectl logs <backend-pod> -n anote-local | grep -i flask

# Common issues:
# - Missing environment variables
# - Database connection issues
# - Port binding problems
```

**Debugging Commands**:

```bash
# Get pod details
kubectl describe pod <pod-name> -n anote-local

# Check service endpoints
kubectl get endpoints -n anote-local

# Test service connectivity
kubectl run debug --image=busybox -it --rm -- nslookup backend.anote-local.svc.cluster.local

# Check secrets
kubectl get secrets -n anote-local
kubectl describe secret <secret-name> -n anote-local
```

### 4. Datadog Agent in Kubernetes

**Verification**:

```bash
# Check Datadog Agent pod
kubectl get pods -l app=datadog-agent -n anote-local

# Check Datadog Agent logs
kubectl logs -l app=datadog-agent -n anote-local

# Verify APM is working
kubectl port-forward svc/datadog-agent 8126:8126 -n anote-local
curl http://localhost:8126/v0.4/traces
```

## 🚀 Quick Start Commands

### Docker Compose
```bash
# Start backend with network
cd backend
docker-compose up -d

# Start frontend (uses external network)
cd ../frontend
docker-compose up -d

# Check logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Kubernetes
```bash
# Apply configurations
kubectl apply -f backend/kubernetes-local.yml

# Check status
kubectl get pods -n anote-local
kubectl get services -n anote-local

# Access services
kubectl port-forward svc/backend 5000:5000 -n anote-local
kubectl port-forward svc/datadog-agent 8126:8126 -n anote-local
```

## 🔧 Environment Variables

### Backend (.env)
```bash
DD_API_KEY=your-datadog-api-key
DB_HOST=redis
DB_PORT=6379
DB_USER=root
DB_PASSWORD=
DB_NAME=agents
FLASK_ENV=development
FLASK_DEBUG=1
```

### Frontend
```bash
REACT_APP_BACK_END_HOST=http://backend:5000
NODE_ENV=development
```

This guide should help you resolve most Docker Compose, Python dependency, and Kubernetes issues you encounter!
