#!/bin/bash

################################################################################
# Kubernetes Push Script for Darwin Project
#
# This script:
# 1. Builds Docker images for specified or all services
# 2. Tags images with beta-<epoch> tag
# 3. Pushes images to registry-dal2.penguintech.io
# 4. Updates Kubernetes deployment in specified namespace
#
# Usage: ./scripts/k8s-push.sh [namespace] [service]
# Examples:
#   ./scripts/k8s-push.sh darwin-dev              # Push all services
#   ./scripts/k8s-push.sh darwin-dev flask-backend # Push only flask-backend
#   ./scripts/k8s-push.sh darwin-dev webui         # Push only webui
################################################################################

set -euo pipefail

# Configuration
NAMESPACE="${1:-darwin-dev}"
SERVICE="${2:-all}"  # all, flask-backend, or webui
REGISTRY="registry-dal2.penguintech.io"
TAG="beta-$(date +%s)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_section() {
    echo ""
    echo -e "${BLUE}=================================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=================================================================================${NC}"
}

# Check prerequisites
check_prerequisites() {
    log_section "Checking Prerequisites"

    if ! command -v docker &> /dev/null; then
        log_error "docker not found. Please install Docker."
        exit 1
    fi
    log_success "Docker is installed"

    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found. Please install kubectl."
        exit 1
    fi
    log_success "kubectl is installed"

    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_error "Namespace '$NAMESPACE' does not exist"
        exit 1
    fi
    log_success "Namespace '$NAMESPACE' exists"
}

# Build Docker images
build_images() {
    log_section "Building Docker Images"

    cd "$PROJECT_DIR"

    if [ "$SERVICE" = "all" ] || [ "$SERVICE" = "flask-backend" ]; then
        log_info "Building darwin-flask-backend..."
        docker build -t darwin-flask-backend:$TAG -t darwin-flask-backend:latest services/flask-backend/
        log_success "Built darwin-flask-backend:$TAG"
    fi

    if [ "$SERVICE" = "all" ] || [ "$SERVICE" = "webui" ]; then
        log_info "Building darwin-webui..."
        docker build -t darwin-webui:$TAG -t darwin-webui:latest services/webui/
        log_success "Built darwin-webui:$TAG"
    fi
}

# Tag images for registry
tag_images() {
    log_section "Tagging Images for Registry"

    if [ "$SERVICE" = "all" ] || [ "$SERVICE" = "flask-backend" ]; then
        docker tag darwin-flask-backend:$TAG $REGISTRY/darwin-flask-backend:$TAG
        docker tag darwin-flask-backend:$TAG $REGISTRY/darwin-flask-backend:latest
        log_success "Tagged flask-backend images"
    fi

    if [ "$SERVICE" = "all" ] || [ "$SERVICE" = "webui" ]; then
        docker tag darwin-webui:$TAG $REGISTRY/darwin-webui:$TAG
        docker tag darwin-webui:$TAG $REGISTRY/darwin-webui:latest
        log_success "Tagged webui images"
    fi
}

# Push images to registry
push_images() {
    log_section "Pushing Images to Registry"

    if [ "$SERVICE" = "all" ] || [ "$SERVICE" = "flask-backend" ]; then
        log_info "Pushing $REGISTRY/darwin-flask-backend:$TAG..."
        docker push $REGISTRY/darwin-flask-backend:$TAG
        docker push $REGISTRY/darwin-flask-backend:latest
        log_success "Pushed flask-backend images"
    fi

    if [ "$SERVICE" = "all" ] || [ "$SERVICE" = "webui" ]; then
        log_info "Pushing $REGISTRY/darwin-webui:$TAG..."
        docker push $REGISTRY/darwin-webui:$TAG
        docker push $REGISTRY/darwin-webui:latest
        log_success "Pushed webui images"
    fi
}

# Update Kubernetes deployments
update_deployments() {
    log_section "Updating Kubernetes Deployments"

    if [ "$SERVICE" = "all" ] || [ "$SERVICE" = "flask-backend" ]; then
        log_info "Updating flask-backend deployment..."
        kubectl set image deployment/flask-backend flask-backend=$REGISTRY/darwin-flask-backend:$TAG -n $NAMESPACE
        log_success "Updated flask-backend deployment"
    fi

    if [ "$SERVICE" = "all" ] || [ "$SERVICE" = "webui" ]; then
        log_info "Updating webui deployment..."
        kubectl set image deployment/webui webui=$REGISTRY/darwin-webui:$TAG -n $NAMESPACE
        log_success "Updated webui deployment"
    fi
}

# Wait for rollout to complete
wait_for_rollout() {
    log_section "Waiting for Rollout to Complete"

    if [ "$SERVICE" = "all" ] || [ "$SERVICE" = "flask-backend" ]; then
        log_info "Waiting for flask-backend rollout..."
        if kubectl rollout status deployment/flask-backend -n $NAMESPACE --timeout=300s; then
            log_success "flask-backend rollout completed"
        else
            log_error "flask-backend rollout failed or timed out"
            return 1
        fi
    fi

    if [ "$SERVICE" = "all" ] || [ "$SERVICE" = "webui" ]; then
        log_info "Waiting for webui rollout..."
        if kubectl rollout status deployment/webui -n $NAMESPACE --timeout=300s; then
            log_success "webui rollout completed"
        else
            log_error "webui rollout failed or timed out"
            return 1
        fi
    fi
}

# Verify deployment health
verify_health() {
    log_section "Verifying Deployment Health"

    # Get pod status
    kubectl get pods -n $NAMESPACE

    # Check flask-backend health
    local flask_pod
    flask_pod=$(kubectl get pods -n $NAMESPACE -l app=flask-backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    if [ -n "$flask_pod" ]; then
        log_info "Checking flask-backend health endpoint..."
        if kubectl exec $flask_pod -n $NAMESPACE -- wget -q -O- http://localhost:5000/healthz &>/dev/null; then
            log_success "flask-backend health check passed"
        else
            log_warning "flask-backend health check failed or inconclusive"
        fi
    fi

    # Check webui health
    local webui_pod
    webui_pod=$(kubectl get pods -n $NAMESPACE -l app=webui -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    if [ -n "$webui_pod" ]; then
        log_info "Checking webui health endpoint..."
        if kubectl exec $webui_pod -n $NAMESPACE -- wget -q -O- http://localhost:3000/healthz &>/dev/null; then
            log_success "webui health check passed"
        else
            log_warning "webui health check failed or inconclusive"
        fi
    fi
}

print_summary() {
    log_section "Deployment Summary"

    echo ""
    echo "Namespace: $NAMESPACE"
    echo "Registry: $REGISTRY"
    echo "Tag: $TAG"
    echo ""
    echo -e "${GREEN}Deployment completed successfully!${NC}"
    echo ""
    echo "Access the application:"
    log_info "Get ingress: kubectl get ingress -n $NAMESPACE"
    log_info "Port forward: kubectl port-forward -n $NAMESPACE deployment/webui 3000:3000"
}

main() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════════════════════════╗"
    echo "║           Darwin Project - Kubernetes Push & Deploy Script                   ║"
    echo "╚═══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    check_prerequisites
    build_images
    tag_images
    push_images
    update_deployments
    wait_for_rollout
    verify_health
    print_summary
}

main "$@"
