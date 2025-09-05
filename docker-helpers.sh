#!/bin/bash

# Docker Compose & Kubernetes Helper Scripts

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null; then
        print_warning "Port $port is already in use"
        lsof -Pi :$port -sTCP:LISTEN
        return 1
    else
        print_success "Port $port is available"
        return 0
    fi
}

# Function to clean up Docker resources
cleanup_docker() {
    print_status "Cleaning up Docker resources..."
    
    # Stop all containers
    docker-compose -f backend/docker-compose.yml down --remove-orphans
    docker-compose -f frontend/docker-compose.yml down --remove-orphans
    
    # Remove unused networks
    docker network prune -f
    
    # Remove unused volumes (be careful with this)
    read -p "Remove unused volumes? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker volume prune -f
    fi
    
    print_success "Docker cleanup completed"
}

# Function to start services with proper order
start_services() {
    print_status "Starting services in correct order..."
    
    # Check ports first
    print_status "Checking port availability..."
    check_port 8000 || return 1
    check_port 3000 || return 1
    check_port 6379 || return 1
    check_port 10001 || return 1
    check_port 8126 || return 1
    
    # Create network if it doesn't exist
    if ! docker network ls | grep -q anote-network; then
        print_status "Creating anote-network..."
        docker network create anote-network
    fi
    
    # Start backend first
    print_status "Starting backend services..."
    cd backend
    docker-compose up -d
    
    # Wait for backend to be healthy
    print_status "Waiting for backend to be healthy..."
    sleep 10
    
    # Start frontend
    print_status "Starting frontend..."
    cd ../frontend
    docker-compose up -d
    
    print_success "All services started successfully!"
    
    # Show status
    docker-compose -f ../backend/docker-compose.yml ps
    docker-compose ps
}

# Function to check service health
check_health() {
    print_status "Checking service health..."
    
    # Check backend
    if curl -f http://localhost:8000/health >/dev/null 2>&1; then
        print_success "Backend is healthy"
    else
        print_error "Backend is not responding"
    fi
    
    # Check frontend
    if curl -f http://localhost:3000 >/dev/null 2>&1; then
        print_success "Frontend is healthy"
    else
        print_error "Frontend is not responding"
    fi
    
    # Check Redis
    if docker exec anote-redis redis-cli ping >/dev/null 2>&1; then
        print_success "Redis is healthy"
    else
        print_error "Redis is not responding"
    fi
    
    # Check Datadog Agent
    if docker exec datadog-agent agent status >/dev/null 2>&1; then
        print_success "Datadog Agent is healthy"
    else
        print_warning "Datadog Agent may not be configured properly"
    fi
}

# Function to show logs
show_logs() {
    local service=$1
    local lines=${2:-50}
    
    case $service in
        "backend")
            docker-compose -f backend/docker-compose.yml logs -f --tail=$lines backend
            ;;
        "frontend")
            docker-compose -f frontend/docker-compose.yml logs -f --tail=$lines frontend
            ;;
        "redis")
            docker-compose -f backend/docker-compose.yml logs -f --tail=$lines redis
            ;;
        "datadog")
            docker-compose -f backend/docker-compose.yml logs -f --tail=$lines datadog-agent
            ;;
        *)
            print_error "Unknown service: $service"
            print_status "Available services: backend, frontend, redis, datadog"
            ;;
    esac
}

# Function to test connectivity
test_connectivity() {
    print_status "Testing container connectivity..."
    
    # Test frontend to backend
    if docker exec $(docker-compose -f frontend/docker-compose.yml ps -q frontend) curl -f http://backend:5000/health >/dev/null 2>&1; then
        print_success "Frontend can reach backend"
    else
        print_error "Frontend cannot reach backend"
    fi
    
    # Test backend to Redis
    if docker exec anote-backend redis-cli -h redis ping >/dev/null 2>&1; then
        print_success "Backend can reach Redis"
    else
        print_error "Backend cannot reach Redis"
    fi
}

# Function to setup Kubernetes
setup_kubernetes() {
    print_status "Setting up Kubernetes deployment..."
    
    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed"
        return 1
    fi
    
    # Apply Kubernetes configuration
    kubectl apply -f backend/kubernetes-local.yml
    
    # Wait for pods to be ready
    print_status "Waiting for pods to be ready..."
    kubectl wait --for=condition=ready pod -l app=backend -n anote-local --timeout=300s
    kubectl wait --for=condition=ready pod -l app=redis -n anote-local --timeout=300s
    kubectl wait --for=condition=ready pod -l app=datadog-agent -n anote-local --timeout=300s
    
    print_success "Kubernetes deployment completed!"
    
    # Show pod status
    kubectl get pods -n anote-local
}

# Function to check Kubernetes logs
k8s_logs() {
    local pod_name=$1
    local container_name=${2:-""}
    
    if [ -z "$pod_name" ]; then
        print_error "Pod name is required"
        print_status "Usage: $0 k8s-logs <pod-name> [container-name]"
        print_status "Available pods:"
        kubectl get pods -n anote-local --no-headers | awk '{print "  " $1}'
        return 1
    fi
    
    if [ -n "$container_name" ]; then
        kubectl logs $pod_name -c $container_name -n anote-local -f
    else
        kubectl logs $pod_name -n anote-local -f
    fi
}

# Main script logic
case "$1" in
    "start")
        start_services
        ;;
    "stop")
        cleanup_docker
        ;;
    "health")
        check_health
        ;;
    "logs")
        show_logs $2 $3
        ;;
    "test")
        test_connectivity
        ;;
    "k8s-setup")
        setup_kubernetes
        ;;
    "k8s-logs")
        k8s_logs $2 $3
        ;;
    "check-ports")
        check_port 8000
        check_port 3000
        check_port 6379
        check_port 10001
        check_port 8126
        ;;
    *)
        echo "Docker Compose & Kubernetes Helper Script"
        echo ""
        echo "Usage: $0 {command} [options]"
        echo ""
        echo "Commands:"
        echo "  start              Start all services in correct order"
        echo "  stop               Stop and clean up all services"
        echo "  health             Check health of all services"
        echo "  logs <service>     Show logs for specific service"
        echo "  test               Test connectivity between services"
        echo "  k8s-setup          Setup Kubernetes deployment"
        echo "  k8s-logs <pod>     Show Kubernetes pod logs"
        echo "  check-ports        Check if required ports are available"
        echo ""
        echo "Services: backend, frontend, redis, datadog"
        echo ""
        echo "Examples:"
        echo "  $0 start"
        echo "  $0 logs backend"
        echo "  $0 k8s-logs backend-xxx"
        echo "  $0 health"
        ;;
esac
