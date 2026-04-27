# Phase 1: Observability — Progress Log

## What We Built

### Stack 1 — Docker Compose (Local)
A local observability pipeline running three containers:

| Service | Port | Role |
|---|---|---|
| Flask App | 5001 | Exposes `/metrics`, `/health`, `/api/data` |
| Prometheus | 9090 | Scrapes Flask every 10s, stores time series |
| Grafana | 3000 | Visualizes Prometheus data |

### Stack 2 — Kubernetes (kind cluster)
A full kube-prometheus-stack deployed via Helm into a dedicated `sre-lab` kind cluster:

| Pod | Role |
|---|---|
| prometheus | Scrapes all K8s targets via service discovery |
| grafana | Pre-built Kubernetes dashboards |
| alertmanager | Handles alert routing |
| kube-state-metrics | Cluster-level metrics (deployments, pods, etc.) |
| node-exporter | Node-level metrics (CPU, memory, disk) |

---

## Incidents We Debugged

### Incident 1 — Port Conflict
**Symptom:** `docker-compose up` failed with `Bind for 0.0.0.0:5000 failed`  
**Root cause:** `local-registry` Docker container was already using port 5000  
**Fix:** Remapped Flask to port 5001 across 4 files — `docker-compose.yml`, `app.py`, `Dockerfile`, `prometheus.yml`  
**SRE lesson:** Never kill a shared service to free a port. Remap your own service instead.

### Incident 2 — Wrong Content-Type
**Symptom:** Prometheus targets showed DOWN with error `received unsupported Content-Type "text/html"`  
**Root cause:** Flask's `/metrics` endpoint returned raw bytes without setting the correct `Content-Type` header  
**Fix:** Used `Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)` from the prometheus_client library  
**SRE lesson:** Always read the actual error message — the API response told us exactly what was wrong.

### Incident 3 — Stale Scrape Config
**Symptom:** Prometheus still showed `app:5000` as the scrape target after port change  
**Root cause:** `prometheus.yml` was not updated when the port changed  
**Fix:** Updated `targets: ['app:5001']` in `prometheus.yml`  
**SRE lesson:** Config changes must be applied consistently across all files — one missed reference breaks the whole chain.

### Incident 4 — kind Cluster API Server EOF
**Symptom:** `kubectl cluster-info` returned EOF errors  
**Root cause:** The `explorecalifornia.com` kind cluster was 13 months old and in a bad state  
**Fix:** Created a fresh dedicated `sre-lab` kind cluster  
**SRE lesson:** Old, unmaintained infrastructure accumulates drift. A clean environment is often faster than debugging stale state.

---

## Key Concepts Learned

**Prometheus scraping** — Prometheus pulls metrics from targets at a defined interval. Targets must expose metrics in the Prometheus text format at a `/metrics` endpoint.

**PromQL** — Query language for Prometheus. Key queries:
```promql
# Request rate per second
rate(app_requests_total[1m])

# 95th percentile latency
histogram_quantile(0.95, rate(app_request_duration_seconds_bucket[1m]))
```

**Helm** — Package manager for Kubernetes. A chart bundles all the YAML needed to deploy a complex application. `helm install` replaces writing hundreds of lines of YAML manually.

**Kubernetes control plane** — The brain of a K8s cluster. Contains the API server, scheduler, etcd, and controller manager. Does not run application workloads — only manages the cluster.

**Service discovery** — Instead of hardcoding scrape targets, Prometheus queries the Kubernetes API to automatically discover what's running and scrape it dynamically.

**Secrets management** — Hardcoded passwords in `docker-compose.yml` are a security risk. Moved Grafana credentials to `.env` (gitignored) with `.env.example` as the committed template.

---

## Current State

### Docker Compose stack
```bash
cd sre-lab/01-observability
docker-compose up
```
- Flask: http://localhost:5001
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

### Kubernetes stack
```bash
kubectl config use-context kind-sre-lab
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3001:80
```
- Grafana: http://localhost:3001 (admin / admin)

---

## Next Steps

- [ ] Create a custom Grafana dashboard for the Flask app
- [ ] Configure Prometheus alert rules (latency, error rate)
- [ ] Add error metrics to the Flask app and simulate failures
- [ ] Write a runbook for each alert
- [ ] Explore log aggregation with Loki
- [ ] Simulate a K8s incident and practice incident response
