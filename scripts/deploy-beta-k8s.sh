#!/bin/bash
# Deploy Darwin to K8s Beta Cluster
# Builds images and deploys to darwin-dev namespace

set -e

REGISTRY="registry-dal2.penguintech.io"
NAMESPACE="darwin-dev"
TIMESTAMP=$(date +%s)
SERVICES="${1:-all}"  # Deploy specific service or all

echo "=========================================="
echo "Darwin Beta K8s Deployment"
echo "=========================================="
echo "Registry: $REGISTRY"
echo "Namespace: $NAMESPACE"
echo "Timestamp: $TIMESTAMP"
echo "Services: $SERVICES"
echo ""

# Function to build and deploy a service
deploy_service() {
  local service=$1
  local image_name=$2

  echo "Building $service..."
  # Build from project root to include shared/ directory in context
  docker build \
    -t $REGISTRY/$image_name:beta-$TIMESTAMP \
    -t $REGISTRY/$image_name:beta-latest \
    -f services/$service/Dockerfile .

  echo "Pushing $service images..."
  docker push $REGISTRY/$image_name:beta-$TIMESTAMP || echo "Warning: Push failed for $image_name:beta-$TIMESTAMP"
  docker push $REGISTRY/$image_name:beta-latest || echo "Warning: Push failed for $image_name:beta-latest"

  echo "Updating K8s deployment for $service..."
  kubectl set image deployment/$service \
    $service=$REGISTRY/$image_name:beta-$TIMESTAMP \
    -n $NAMESPACE

  echo "Waiting for $service rollout..."
  kubectl rollout status deployment/$service -n $NAMESPACE --timeout=5m

  echo "✓ $service deployed successfully"
  echo ""
}

# Deploy requested services
if [ "$SERVICES" = "all" ]; then
  deploy_service "flask-backend" "darwin-flask-backend"
  deploy_service "webui" "darwin-webui"
elif [ "$SERVICES" = "flask-backend" ] || [ "$SERVICES" = "backend" ]; then
  deploy_service "flask-backend" "darwin-flask-backend"
elif [ "$SERVICES" = "webui" ] || [ "$SERVICES" = "web" ]; then
  deploy_service "webui" "darwin-webui"
else
  echo "Error: Unknown service '$SERVICES'"
  echo "Usage: $0 [all|flask-backend|webui]"
  exit 1
fi

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo "Application URL: https://darwin.penguintech.io"
echo "Internal LB: https://192.168.7.203 (Host: darwin.penguintech.io)"
echo ""
echo "Check status:"
echo "  kubectl get pods -n $NAMESPACE"
echo "  kubectl logs -n $NAMESPACE deployment/flask-backend --tail=100"
echo ""
