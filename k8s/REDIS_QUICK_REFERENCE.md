# Redis Kubernetes Quick Reference

## Quick Deploy Commands

### Helm - Development
```bash
helm install redis ./k8s/helm/redis/ -n project-template -f ./k8s/helm/redis/values-dev.yaml
```

### Helm - Staging
```bash
helm install redis ./k8s/helm/redis/ -n project-template -f ./k8s/helm/redis/values-staging.yaml
```

### Helm - Production
```bash
helm install redis ./k8s/helm/redis/ -n project-template -f ./k8s/helm/redis/values-prod.yaml \
  --set secrets.redisPassword="CHANGE-ME"
```

### Kubectl Manifests
```bash
kubectl apply -f k8s/manifests/redis/
```

---

## Quick Verification

```bash
# Check deployment status
kubectl get deploy,svc,pvc -n project-template -l app.kubernetes.io/name=redis

# Check pod logs
kubectl logs -n project-template -l app.kubernetes.io/name=redis -f

# Test Redis connection
kubectl run -it --rm debug --image=redis:7-alpine -n project-template -- \
  redis-cli -h redis.project-template.svc.cluster.local ping
```

---

## Key Files

### Manifests
- `k8s/manifests/redis/deployment.yaml` - Main deployment
- `k8s/manifests/redis/service.yaml` - Service (port 6379)
- `k8s/manifests/redis/pvc.yaml` - 5Gi storage
- `k8s/manifests/redis/secret.yaml` - Password secret

### Helm Chart
- `k8s/helm/redis/Chart.yaml` - Chart metadata (v1.0.0)
- `k8s/helm/redis/values.yaml` - Default values
- `k8s/helm/redis/values-dev.yaml` - Dev overrides (1 replica, 2Gi)
- `k8s/helm/redis/values-staging.yaml` - Staging overrides (2 replicas, 10Gi)
- `k8s/helm/redis/values-prod.yaml` - Prod overrides (2 replicas, 20Gi)
- `k8s/helm/redis/templates/` - Helm templates

---

## Connection Details

**Host:** `redis.project-template.svc.cluster.local`
**Port:** `6379`
**Password:** From `redis-secret` or helm values
**Persistence:** AOF enabled at `/data`

---

## Environment Specifications

| Aspect | Dev | Staging | Prod |
|--------|-----|---------|------|
| Replicas | 1 | 2 | 2 |
| Storage | 2Gi | 10Gi | 20Gi |
| CPU Req | 25m | 100m | 250m |
| CPU Limit | 50m | 200m | 500m |
| Mem Req | 64Mi | 256Mi | 512Mi |
| Mem Limit | 128Mi | 512Mi | 1Gi |
| Pod Anti-Affinity | None | Preferred | Required |
| Node Selector | None | None | cache-workload |

---

## Common Tasks

**Update password:**
```bash
helm upgrade redis ./k8s/helm/redis/ --set secrets.redisPassword="new-pass"
```

**Scale replicas:**
```bash
helm upgrade redis ./k8s/helm/redis/ --set replicaCount=3
```

**Increase storage:**
```bash
helm upgrade redis ./k8s/helm/redis/ --set persistence.size=20Gi
```

**View Helm values:**
```bash
helm get values redis -n project-template
```

**Validate Helm chart:**
```bash
helm lint ./k8s/helm/redis/
helm template redis ./k8s/helm/redis/ -f ./k8s/helm/redis/values-prod.yaml
```

---

See `REDIS_K8S_SETUP.md` for detailed documentation.
