#!/bin/bash

# API Keys Management Script for Kubernetes

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Function to update API keys
update_api_keys() {
    print_status "Updating API keys in Kubernetes secrets..."
    
    # Check if api-keys-secret.yml exists
    if [ ! -f "api-keys-secret.yml" ]; then
        print_error "api-keys-secret.yml not found!"
        return 1
    fi
    
    # Apply the secrets
    kubectl apply -f api-keys-secret.yml
    
    if [ $? -eq 0 ]; then
        print_success "API keys updated successfully!"
        
        # Restart backend deployment to pick up new keys
        print_status "Restarting backend deployment..."
        kubectl rollout restart deployment/backend -n anote-local
        
        print_success "Backend deployment restarted!"
    else
        print_error "Failed to update API keys"
        return 1
    fi
}

# Function to check current API keys
check_api_keys() {
    print_status "Checking current API keys in Kubernetes..."
    
    echo ""
    echo "=== Current Secrets ==="
    kubectl get secrets -n anote-local
    
    echo ""
    echo "=== API Keys Secret Details ==="
    kubectl describe secret api-keys-secret -n anote-local
    
    echo ""
    echo "=== Datadog Secret Details ==="
    kubectl describe secret datadog-secret -n anote-local
}

# Function to verify API keys are working
verify_api_keys() {
    print_status "Verifying API keys are working..."
    
    # Get the current backend pod
    BACKEND_POD=$(kubectl get pods -n anote-local -l app=backend -o jsonpath='{.items[0].metadata.name}')
    
    if [ -z "$BACKEND_POD" ]; then
        print_error "No backend pod found!"
        return 1
    fi
    
    print_status "Checking environment variables in pod: $BACKEND_POD"
    
    # Check if API keys are set
    echo ""
    echo "=== Environment Variables ==="
    kubectl exec $BACKEND_POD -n anote-local -- env | grep -E "(OPENAI_API_KEY|SEC_API_KEY|ANTHROPIC_API_KEY|STRIPE_SECRET_KEY)" | sed 's/=.*/=***HIDDEN***/'
    
    # Check pod logs for any API key errors
    echo ""
    echo "=== Recent Logs (checking for API key errors) ==="
    kubectl logs $BACKEND_POD -n anote-local --tail=20 | grep -i -E "(api.*key|error|exception)" || echo "No API key errors found in recent logs"
}

# Function to show current pod status
show_status() {
    print_status "Current pod status:"
    kubectl get pods -n anote-local
    
    echo ""
    print_status "Service status:"
    kubectl get services -n anote-local
}

# Function to test connectivity
test_connectivity() {
    print_status "Testing connectivity..."
    
    # Port forward backend
    print_status "Setting up port forwarding..."
    kubectl port-forward svc/backend 5000:5000 -n anote-local &
    PORT_FORWARD_PID=$!
    
    # Wait for port forward to be ready
    sleep 5
    
    # Test connection
    if curl -f http://localhost:5000/ >/dev/null 2>&1; then
        print_success "Backend is accessible!"
    else
        print_warning "Backend may still be starting up..."
    fi
    
    # Clean up port forward
    kill $PORT_FORWARD_PID 2>/dev/null
}

# Function to edit API keys
edit_api_keys() {
    print_status "Opening API keys file for editing..."
    
    if [ ! -f "api-keys-secret.yml" ]; then
        print_error "api-keys-secret.yml not found!"
        return 1
    fi
    
    # Create backup
    cp api-keys-secret.yml api-keys-secret.yml.backup
    
    # Open editor
    ${EDITOR:-nano} api-keys-secret.yml
    
    print_status "API keys file edited. Run 'update' to apply changes."
}

# Main script logic
case "$1" in
    "update")
        update_api_keys
        ;;
    "check")
        check_api_keys
        ;;
    "verify")
        verify_api_keys
        ;;
    "status")
        show_status
        ;;
    "test")
        test_connectivity
        ;;
    "edit")
        edit_api_keys
        ;;
    "help"|"--help"|"-h")
        echo "API Keys Management Script"
        echo ""
        echo "Usage: $0 {command}"
        echo ""
        echo "Commands:"
        echo "  update    Update API keys in Kubernetes"
        echo "  check     Check current API keys in secrets"
        echo "  verify    Verify API keys are working in pods"
        echo "  status    Show current pod and service status"
        echo "  test      Test backend connectivity"
        echo "  edit      Edit API keys file"
        echo "  help      Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 update    # Apply API keys to Kubernetes"
        echo "  $0 verify    # Check if API keys are working"
        echo "  $0 edit      # Edit API keys file"
        ;;
    *)
        echo "API Keys Management Script"
        echo ""
        echo "Usage: $0 {command}"
        echo ""
        echo "Available commands: update, check, verify, status, test, edit, help"
        echo ""
        echo "Run '$0 help' for detailed usage information."
        ;;
esac
