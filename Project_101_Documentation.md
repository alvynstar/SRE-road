# SRE Lab — Project 101 Documentation

**Project Name:** SRE Lab: Observability, Chaos Engineering & Reliability Portfolio  
**Version:** 1.0  
**Date:** June 5, 2026  
**Author:** Alvin (Infrastructure Engineer at Manulife)  
**Repository:** https://github.com/alvynstar/sre-lab  
**Status:** Phase 6 Complete

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [Features & Modules](#features--modules)
5. [Phase Breakdown](#phase-breakdown)
6. [Setup Instructions](#setup-instructions)
7. [Known TODOs & Future Work](#known-todos--future-work)
8. [Directory Structure](#directory-structure)
9. [Key Concepts & Lessons Learned](#key-concepts--lessons-learned)
10. [Troubleshooting Guide](#troubleshooting-guide)

---

## Project Overview

### Purpose

SRE Lab is a **comprehensive portfolio project** demonstrating real-world Site Reliability Engineering (SRE) skills through hands-on implementation of:

- **Observability**: Metrics, logs, and traces (Three Pillars)
- **Chaos Engineering**: Controlled failure testing and incident response
- **CI/CD Ownership**: Automated testing, building, and deployment
- **Log Aggregation**: Structured logging and log analysis
- **Reliability**: SLO/SLI definitions, error budgets, burn rate alerts
- **Distributed Tracing**: End-to-end request tracing with OpenTelemetry

### Goal

Build a production-ready observability stack and incident response procedures, validated through chaos experiments and postmortems. This project serves as both a learning tool and a portfolio demonstrating SRE capabilities to prospective employers.

### Target Audience

- Infrastructure/DevOps/SRE engineers transitioning into reliability roles
- Developers learning observability and incident management
- Hiring managers evaluating SRE portfolio projects

### Key Metrics

- **6 Phases** of incremental complexity
- **15+ Concept Documents** explaining mental models
- **3 Chaos Experiments** with postmortems
- **1 Docker Compose Stack** + **1 Kubernetes Stack**
- **4 Observability Backends** (Prometheus, Grafana, Loki, Tempo)
- **99% SLO** with burn rate alerts
- **100% CI/CD Pipeline** (lint, test, build, push, deploy)

---

## Architecture

### High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    FLASK APPLICATION                        │
│              (OpenTelemetry Instrumented)                   │
│  /metrics  /health  /api/data  /api/error  /api/slow       │
└──────┬──────────────┬──────────────┬────────────────────────┘
       │              │              │
   (metrics)       (logs)        (traces)
       │              │              │
       ▼              ▼              ▼
┌────────────┐  ┌──────────┐  ┌──────────────┐
│ PROMETHEUS │  │ PROMTAIL │  │ OTEL:4317    │
│  :9090     │  │          │  │              │
└─────┬──────┘  └────┬─────┘  └──────┬───────┘
      │              │               │
      │              ▼               ▼
      │          ┌──────────┐   ┌──────────┐
      │          │  LOKI    │   │  TEMPO   │
      │          │  :3100   │   │  :3200   │
      │          └────┬─────┘   └────┬─────┘
      │               │              │
      └───────────────┴──────────────┘
               │
               ▼
          ┌─────────────┐
          │   GRAFANA   │
          │   :3000     │
          │ (4 panels)  │
          └─────────────┘
```

### Stack Architecture

The project implements **two parallel observability stacks**:

#### Stack 1: Docker Compose (Local Development)
- Lightweight, all-in-one stack for development and chaos testing
- Services: Flask app, Prometheus, Grafana, AlertManager, Loki, Tempo
- Docker network isolation for safe testing
- Volume mounts for persistent config and data

#### Stack 2: Kubernetes (kind cluster)
- Production-like environment for realistic testing
- Deployed via Helm (`kube-prometheus-stack`)
- Service discovery with ServiceMonitor
- Demonstrates K8s-native monitoring patterns

### Data Flow

1. **Metrics Path**: Flask app → Prometheus scrapes `/metrics` → Time series DB → Grafana panels
2. **Logs Path**: Flask structured JSON logs → Promtail tails stdout → Loki → Grafana + LogQL queries
3. **Traces Path**: OpenTelemetry SDK → OTLP gRPC :4317 → Tempo → Waterfall view in Grafana
4. **Alerts Path**: Prometheus rules evaluate → AlertManager routes → Slack webhook → `#all-toks`

### Three Pillars Integration

```
METRICS (Is it broken?)     → Prometheus queries → Grafana gauges
  │
  ├─ LOGS (What happened?)  → LogQL filters → Log panels
  │
  └─ TRACES (Where slow?)   → Tempo waterfall → Span analysis
```

All three converge in Grafana with **derived fields** enabling one-click jumps from log line → trace waterfall.

---

## Technology Stack

### Core Technologies

| Component | Purpose | Version | Status |
|-----------|---------|---------|--------|
| **Python/Flask** | Application framework | 3.0.0 | ✓ Production |
| **Prometheus** | Metrics collection & storage | Latest | ✓ Production |
| **Grafana** | Visualization & dashboards | Latest | ✓ Production |
| **Loki** | Log aggregation | Latest | ✓ Production |
| **Tempo** | Distributed tracing | Latest | ✓ Production |
| **AlertManager** | Alert routing | Latest | ✓ Production |
| **Docker** | Containerization | CE | ✓ Production |
| **Kubernetes** | Orchestration (kind) | 1.28+ | ✓ Development |
| **GitHub Actions** | CI/CD pipeline | Native | ✓ Production |

### Python Dependencies

```
Flask==3.0.0
prometheus-client==0.19.0
gunicorn==21.2.0
python-json-logger==2.0.7
opentelemetry-sdk==1.24.0
opentelemetry-instrumentation-flask==0.45b0
opentelemetry-exporter-otlp-proto-grpc==1.24.0
```

### Development Tools

| Tool | Purpose | Location |
|------|---------|----------|
| pytest | Unit testing | `01-observability/app/tests/` |
| ruff | Linting | `01-observability/app/` |
| docker-compose | Local orchestration | `01-observability/` |
| kubectl | K8s management | System |
| helm | K8s package manager | System |
| gh (GitHub CLI) | Repo operations | System |

### Infrastructure

- **Container Registry**: GitHub Container Registry (GHCR)
  - Registry: `ghcr.io/alvynstar/sre-lab-app`
  - Access: Public (anonymous pull)
  - Tags: `sha-<commit>`, `main`, `latest`

- **Git Hosting**: GitHub
  - Repository: `public` (after secret-scan)
  - Branch protection: Enabled on `main`
  - Workflow runners: GitHub-hosted Ubuntu

- **Kubernetes**: kind (Kubernetes in Docker)
  - Cluster: `sre-lab`
  - Namespace: `monitoring` (kube-prometheus-stack)
  - Service discovery: Enabled via ServiceMonitor

---

## Features & Modules

### Phase 1: Observability (COMPLETE ✓)

**Goal:** Instrument a Flask app with Prometheus metrics and visualize via Grafana

**Key Features:**
- Flask application with three metric types (counters, histograms)
- Four Golden Signals dashboard (Traffic, Errors, Latency p95/p50)
- Prometheus alert rules (HighErrorRate, HighLatency, AppDown)
- AlertManager integration with Slack notifications
- Runbook documentation for each alert
- Kubernetes deployment via kube-prometheus-stack Helm chart

**Deliverables:**
- `01-observability/app/app.py` — Flask app with prometheus_client instrumentation
- `01-observability/docker-compose.yml` — Full stack orchestration
- `01-observability/prometheus/config/` — Scrape config, alert rules, SLO recording rules
- `01-observability/grafana/dashboards/` — Pre-built dashboards (JSON)
- `01-observability/runbooks/` — HighErrorRate.md, HighLatency.md
- `03-cicd/k8s/` — Kubernetes manifests (Deployment, Service, ServiceMonitor)

**Metrics Exposed:**
```
app_requests_total{method="GET", endpoint="/api/data"} — counter
app_request_duration_seconds_bucket{le="...", endpoint="/api/data"} — histogram
app_errors_total{endpoint="/api/error", status_code="500"} — counter
```

**Grafana Dashboards:**
1. **Flask App — Four Golden Signals** — Traffic rate, error rate, latency percentiles
2. **Flask App — Metrics + Logs** (Phase 4) — Combined metrics + logs view
3. **SLO Dashboard** (Phase 5) — Availability gauge, error budget gauge, burn rate timeseries

---

### Phase 2: Chaos Engineering (COMPLETE ✓)

**Goal:** Deliberately break the system in controlled ways to validate monitoring and recovery procedures

**Experiments Completed:**

| # | Name | What Broke | Alert Tested | Outcome |
|---|------|-----------|-------------|---------|
| 1 | Container Kill | Stopped Flask app | `AppDown` (newly added) | ✓ Alert fired, Slack notified |
| 2 | Error Flood | 50 errors/min to `/api/error` | `HighErrorRate` | ✓ Alert fired after 4min |
| 3 | Latency Spike | Continuous requests to `/api/slow` (6s each) | `HighLatency` | ✓ Alert fired after 3min |

**Key Insights:**
- App outages must be detected via `up` metric (not app-emitted metrics)
- Rate window + evaluation interval + `for:` duration = total MTTR
- p95 ≈ p50 indicates *all* requests slow (not partial degradation)

**Scripts:**
- `02-chaos/scripts/generate_errors.sh` — Floods `/api/error`
- `02-chaos/scripts/generate_latency.sh` — Floods `/api/slow`

**Postmortems:**
- `02-chaos/postmortems/experiment-01-container-kill.md`
- `02-chaos/postmortems/experiment-02-error-flood.md`
- `02-chaos/postmortems/experiment-03-latency-spike.md`

---

### Phase 3: CI/CD Ownership (COMPLETE ✓)

**Goal:** Automate code quality checks, build, and deployment pipeline

**Sub-phases:**

| 3.1 | **Lint + Test in CI** | pytest + ruff in GitHub Actions | ✓ Blocks on failure |
| 3.2 | **Docker Build + Push** | GHCR registry with SHA/main/latest tags | ✓ Builds all PRs, pushes main |
| 3.3 | **Deploy to K8s** | Deployment + Service + ServiceMonitor | ✓ Running in kind cluster |
| 3.4 | **Grafana Annotations** | Deploy markers on dashboards | ✓ Annotation API working |
| 3.5 | **Rollback Drill** | Test bad deploy + rollback via git revert | ✓ Error spike observed, rolled back |

**CI/CD Pipeline:**

```
PR opened/updated
  ↓
GitHub Actions trigger
  ├─ Lint with ruff (01-observability/app)
  ├─ Test with pytest (01-observability/app/tests)
  └─ Build Docker image (optional push)
  ↓
All green?
  ├─ NO → PR blocked
  └─ YES → Allow merge
  ↓
Merge to main
  ├─ Re-run lint + test (final check)
  ├─ Build + PUSH to GHCR
  │   - Tags: sha-<short>, main, latest
  │   - Auth: GITHUB_TOKEN (built-in)
  └─ (Manual K8s redeploy with latest tag)
```

**Key Configuration:**
- `.github/workflows/ci.yml` — Single workflow, two jobs (lint-test, docker-build-push)
- Branch protection: PR required, CI must pass, direct pushes blocked
- GHCR visibility: Public (flip from private after first push)
- Image tags: Immutable (SHA), mutable pointers (main, latest)

**Test Coverage:**
- `01-observability/app/tests/` — pytest test suite
- `requirements-dev.txt` — ruff, pytest, pytest-cov

---

### Phase 4: Log Aggregation with Loki (COMPLETE ✓)

**Goal:** Aggregate structured logs and correlate with metrics

**Features:**
- Flask app emits JSON logs (via `python-json-logger`)
- Promtail tails container stdout, extracts labels (level, endpoint, status)
- Loki stores logs indexed by labels
- Grafana LogQL queries filter and visualize logs
- **trace_id injection** — every log includes OTel trace ID for trace correlation

**JSON Log Format:**
```json
{
  "timestamp": "2026-05-13T08:00:00.000Z",
  "level": "INFO",
  "message": "request",
  "endpoint": "/api/data",
  "status": 200,
  "duration": 0.105,
  "trace_id": "abc123def456...",
  "span_id": "9f8e7d6c..."
}
```

**LogQL Examples:**
```
{container="/sre-lab-app"} | json | levelname = `ERROR`
{job="sre-lab-app"} | json | status >= 500
rate({container="/sre-lab-app"}[5m]) — log rate over 5m
```

**Files:**
- `04-logs-loki/loki/loki-config.yml` — Loki config (filesystem storage)
- `04-logs-loki/promtail/promtail-config.yml` — Promtail pipeline (Docker SD, JSON extraction)
- `01-observability/app/app.py` — TraceIdFilter class injecting trace_id into logs
- `01-observability/grafana/dashboards/flask-logs-and-metrics.json` — Combined dashboard

**Key Concepts:**
- Loki is **log-storage-only** (not a full ELK replacement) — Promtail does the parsing
- Labels are indexed (fast filtering), raw log text is compressed (storage-efficient)
- JSON pipeline stage extracts fields as labels (`levelname`, `endpoint`, `status`)
- Derived fields in Grafana link logs to traces via `trace_id`

---

### Phase 5: SLOs & Error Budgets (COMPLETE ✓)

**Goal:** Define and monitor reliability targets with burn rate alerts

**SLOs Defined:**

| SLO | Target | Window | Budget |
|-----|--------|--------|--------|
| Availability | ≥99% of requests succeed | 30 days | 1% allowed failures |
| Latency | p95 < 300ms | 30 days | N/A |

**Error Budget Mechanics:**
- Budget = 1% × 30 days = 7.2 hours of allowed downtime
- Burn rate 1x = exhaust budget in exactly 30 days (normal)
- Burn rate 14.4x = exhaust budget in 2 days → PAGE NOW
- Burn rate > 1x for 15min = draining steadily → TICKET

**Recording Rules** (`slo-rules.yml`):
```
slo:availability:rate5m — success rate over 5m
slo:availability:rate1h — success rate over 1h
slo:latency_p95:rate5m — p95 latency over 5m
slo:error_budget_remaining:rate1h — fraction remaining
```

**Alerts:**
```
SloBudgetFastBurn: burn_rate > 14.4x for 2m → CRITICAL (page)
SloBudgetSlowBurn: burn_rate > 1x for 15m → WARNING (ticket)
```

**SLO Dashboard** (6 panels):
1. Availability SLI gauge (red < 95%, yellow < 99%, green ≥ 99%)
2. Error budget remaining gauge (red < 10%, yellow < 25%, green ≥ 25%)
3. SLO target stat (99%)
4. Latency p95 stat (red ≥ 500ms, yellow ≥ 300ms, green < 300ms)
5. Availability over time (timeseries vs 99% target line)
6. Latency p95 over time (timeseries vs 300ms target line)

**Validation:**
- Error budget burn experiment: 50/50 success/error ratio → burn rate 61.5x → SloBudgetFastBurn fired in 2min
- Budget exhaustion message: "Error budget remaining = 0%"

**Files:**
- `01-observability/prometheus/config/slo-rules.yml` — Recording rules
- `01-observability/prometheus/config/alerts.yml` — Burn rate alert group
- `01-observability/grafana/dashboards/slo-dashboard.json` — Dashboard definition

---

### Phase 6: Distributed Tracing with Tempo & OpenTelemetry (COMPLETE ✓)

**Goal:** Implement end-to-end request tracing to answer "where is it slow?"

**Status:** All components deployed and validated end-to-end

**Components:**
- **OpenTelemetry SDK** — Auto-instrumentation of Flask requests
- **Tempo** — Trace backend (stores spans, builds waterfall views)
- **OTLP Receiver** — gRPC endpoint :4317 receives spans from app

**Key Features (Planned):**
1. **Auto-instrumentation** — Every request wrapped in a span automatically
2. **Custom spans** — Manual spans for business logic (e.g., artificial_delay)
3. **Trace ID injection** — trace_id in every log line for log↔trace correlation
4. **Grafana integration** — Derived fields enable one-click log→trace jump
5. **Waterfall view** — See request breakdown: which operation took longest?

**Implementation Status:**

| Item | Status |
|------|--------|
| Tempo config | ✓ Created (`tempo-config.yml`) |
| Flask OTel SDK | ✓ Added to requirements.txt |
| Auto-instrumentation | ✓ `FlaskInstrumentor().instrument_app(app)` |
| Custom spans | ✓ `artificial_delay` span on `/api/slow` |
| Trace ID injection | ✓ `TraceIdFilter` logs trace_id |
| OTEL exporter | ✓ `OTLPSpanExporter(endpoint="http://tempo:4317")` |
| Docker-compose | ✓ Tempo service added with persistent volume |
| Grafana datasource | ✓ Tempo datasource provisioned |
| Derived fields | ✓ Loki derived fields enable log→trace jumps |
| E2E validation | ✓ Waterfall view, log-to-trace correlation working |

**Files:**
- `06-tracing/CONCEPTS.md` — Educational reference for traces, spans, trace_id
- `06-tracing/tempo/tempo-config.yml` — Tempo config
- `01-observability/app/app.py` — Flask instrumentation (lines 6-24, 28-40, 92)
- `01-observability/app/requirements.txt` — OTel SDK packages (lines 5-8)

**Validation Complete:**
- ✓ Tempo datasource wired into Grafana (uid: tempo)
- ✓ Derived fields configured on Loki datasource for log→trace jumps
- ✓ End-to-end tested: request → span exported → waterfall view in Grafana
- ✓ One-click jumps from log line (with trace_id) to trace waterfall working
- ✓ Error traces marked red, child spans showing proper nesting, artificial_delay visible

---

### CONCEPTS.md Files (Educational References)

Each phase includes a **CONCEPTS.md** explaining the mental models:

| Phase | Document | Purpose |
|-------|----------|---------|
| 1 | `01-observability/CONCEPTS.md` | Metrics, scrape pipeline, four golden signals, alerts |
| 2 | `02-chaos/CONCEPTS.md` | Chaos engineering principles, MTTR, blast radius |
| 3 | `03-cicd/CONCEPTS.md` | CI/CD patterns, branch protection, image tagging |
| 4 | `04-logs-loki/CONCEPTS.md` | Log aggregation, JSON pipelines, derived fields |
| 5 | `05-reliability/CONCEPTS.md` | SLO/SLI/error budget, burn rate mechanics |
| 6 | `06-tracing/CONCEPTS.md` | Traces, spans, trace_id, waterfall views |

---

## Phase Breakdown

### Completion Status

| Phase | Name | Status | Complexity | Key Files |
|-------|------|--------|------------|-----------|
| 1 | Observability | ✓ Complete | Medium | app.py, prometheus.yml, alerts.yml |
| 2 | Chaos Engineering | ✓ Complete | Medium | generate_errors.sh, postmortems/ |
| 3 | CI/CD Ownership | ✓ Complete | High | ci.yml, deployment.yaml |
| 4 | Log Aggregation | ✓ Complete | Medium | loki-config.yml, promtail-config.yml |
| 5 | SLOs & Error Budgets | ✓ Complete | High | slo-rules.yml, slo-dashboard.json |
| 6 | Distributed Tracing | ✓ Complete | High | tempo-config.yml, app.py (OTel) |

### Total Effort

- **Completed**: 6 phases × ~80 hours each = ~480 hours
- **Total Project**: ~480 hours of hands-on SRE skill development across observability, chaos, CI/CD, logs, SLOs, and distributed tracing

---

## Setup Instructions

### Prerequisites

**System Requirements:**
- Windows 11 or macOS/Linux with WSL2
- 8GB RAM minimum (16GB recommended)
- 10GB disk space (Prometheus/Loki data)
- Internet connection (for Docker image pulls)

**Software Requirements:**
```
Docker Desktop                  (v4.10+)
Docker Compose                  (v2.0+)
kubectl                         (v1.25+)
kind                            (v0.18+)
Python                          (v3.11+)
git                             (v2.40+)
gh (GitHub CLI)                 (optional but useful)
```

### Installation Steps

#### 1. Clone the Repository

```bash
git clone https://github.com/alvynstar/sre-lab.git
cd sre-lab
```

#### 2. Set Up Environment Variables

Create `.env` file in `01-observability/`:

```bash
cd 01-observability
cat > .env << 'EOF'
# Grafana
GF_ADMIN_USER=admin
GF_ADMIN_PASSWORD=admin

# Slack (optional)
# Get from https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
EOF
```

#### 3. Start Docker Compose Stack

```bash
cd 01-observability
docker-compose up --build
```

**Wait for services to be healthy:**
```
✓ sre-lab-app (port 5001)
✓ sre-lab-prometheus (port 9090)
✓ sre-lab-grafana (port 3000)
✓ sre-lab-alertmanager (port 9093)
✓ sre-lab-loki (port 3100)
✓ sre-lab-tempo (port 3200)
```

#### 4. Access Services (Docker Compose)

```
Flask App:    http://localhost:5001
Prometheus:   http://localhost:9090
Grafana:      http://localhost:3000 (admin/admin)
AlertManager: http://localhost:9093
Loki:         http://localhost:3100
Tempo:        http://localhost:3200
```

#### 5. Set Up Kubernetes Stack (Optional)

```bash
# Create kind cluster
kind create cluster --name sre-lab

# Add kube-prometheus-stack Helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install into 'monitoring' namespace
kubectl create namespace monitoring
helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring

# Port-forward Grafana
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3001:80
# Access at http://localhost:3001 (admin/prom-operator)
```

#### 6. Verify Installation

**Generate some traffic:**
```bash
for i in {1..10}; do
  curl http://localhost:5001/api/data
  sleep 1
done
```

**Check Prometheus targets:**
```
http://localhost:9090/targets
```

Should show:
- `sre-lab-app` (UP)
- `prometheus` (UP)

**Check Grafana dashboard:**
1. Navigate to http://localhost:3000
2. Login: admin / admin
3. Dashboards → Flask App — Four Golden Signals
4. Traffic should show ~10 requests over last 10 minutes

---

### Running Chaos Experiments

#### Experiment 1: Container Kill

```bash
# Terminal 1: Monitor alerts
watch -n 5 'curl -s http://localhost:9090/api/v1/alerts | jq ".data.alerts[] | {name:.labels.alertname, state:.state}"'

# Terminal 2: Stop the app
docker-compose stop app

# Observe: AppDown alert fires in ~30 seconds
# Restart the app
docker-compose start app
```

#### Experiment 2: Error Flood

```bash
# Terminal 1: Monitor alert
watch -n 5 'curl -s http://localhost:9090/api/v1/alerts | jq ".data.alerts[] | {name:.labels.alertname, state:.state}"'

# Terminal 2: Run chaos script
cd 02-chaos/scripts
bash generate_errors.sh

# Observe: HighErrorRate fires after ~4 minutes
```

#### Experiment 3: Latency Spike

```bash
# Terminal 1: Monitor alert
watch -n 5 'curl -s http://localhost:9090/api/v1/alerts | jq ".data.alerts[] | {name:.labels.alertname, state:.state}"'

# Terminal 2: Run chaos script
cd 02-chaos/scripts
bash generate_latency.sh

# Observe: HighLatency fires after ~3 minutes
# Press Ctrl+C to stop
```

---

### Running Tests

```bash
cd 01-observability/app

# Install dev dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Run tests
pytest -v

# Run linting
ruff check .

# Run with coverage
pytest --cov=. -v
```

---

### Deploying to Kubernetes

```bash
# Ensure kind cluster is running
kubectl cluster-info --context kind-sre-lab

# Deploy app
kubectl apply -f 03-cicd/k8s/deployment.yaml
kubectl apply -f 03-cicd/k8s/service.yaml
kubectl apply -f 03-cicd/k8s/servicemonitor.yaml

# Verify deployment
kubectl get pods
kubectl get svc sre-lab-app

# Port-forward to test
kubectl port-forward svc/sre-lab-app 8080:80
curl http://localhost:8080/health
```

---

### Stopping the Stack

```bash
cd 01-observability

# Stop all services (keep data)
docker-compose stop

# Stop and remove containers (keep data)
docker-compose down

# Stop and remove everything (including data)
docker-compose down -v

# Remove kind cluster
kind delete cluster --name sre-lab
```

---

## Known TODOs & Future Work

### Phase 6: Distributed Tracing (COMPLETE)

**Completed Tasks:**
- ✓ Tempo receiving spans from Flask app (gRPC :4317)
- ✓ Tempo datasource provisioned in Grafana
- ✓ Derived fields configured on Loki datasource for log→trace jumps
- ✓ End-to-end validated: request → log with trace_id → one-click → trace waterfall
- ✓ Waterfall view, error marking, child span nesting all working

### Post-Phase-6 Roadmap (Future Phases)

#### Phase 7: Incident Response & Runbooks (Planned)

- Enhance runbooks with decision trees
- Add severity levels to incidents
- Build on-call rotation simulator
- Document escalation procedures

**Estimated Effort:** 40 hours

#### Phase 8: Advanced Monitoring (Planned)

- Custom metrics for business KPIs
- Anomaly detection (e.g., Prophet)
- ML-driven alerting
- Automated remediation examples

**Estimated Effort:** 50 hours

#### Phase 9: Security & Compliance (Planned)

- Secret scanning in CI/CD
- RBAC for monitoring stack
- Audit logging
- Secrets management (HashiCorp Vault example)

**Estimated Effort:** 40 hours

#### Phase 10: Cost Optimization (Planned)

- Metrics cardinality analysis
- Log retention policies
- Trace sampling
- Cost attribution per service

**Estimated Effort:** 30 hours

---

## Directory Structure

```
sre-lab/
├── .github/
│   └── workflows/
│       └── ci.yml                      # GitHub Actions CI/CD pipeline
│
├── 01-observability/                   # Phase 1: Metrics & Monitoring
│   ├── app/
│   │   ├── app.py                      # Flask app with Prometheus metrics
│   │   ├── Dockerfile                  # Container image
│   │   ├── requirements.txt             # Python dependencies
│   │   ├── requirements-dev.txt         # Dev dependencies (pytest, ruff)
│   │   ├── tests/                      # Unit tests
│   │   │   ├── test_app.py
│   │   │   └── test_health.py
│   │   └── pyproject.toml               # Ruff config
│   ├── prometheus/
│   │   └── config/
│   │       ├── prometheus.yml           # Scrape config, alert rules reference
│   │       ├── alerts.yml               # Alert rule definitions
│   │       └── slo-rules.yml            # SLO recording rules (Phase 5)
│   ├── alertmanager/
│   │   └── config/
│   │       └── alertmanager.yml         # Alert routing & Slack integration
│   ├── grafana/
│   │   ├── provisioning/
│   │   │   ├── datasources/
│   │   │   │   └── prometheus.yml       # Prometheus datasource config
│   │   │   └── dashboards/
│   │   │       └── dashboard.yml        # Grafana dashboard provisioning
│   │   └── dashboards/
│   │       ├── flask-golden-signals.json    # Phase 1 dashboard
│   │       ├── flask-logs-and-metrics.json  # Phase 4 dashboard
│   │       └── slo-dashboard.json           # Phase 5 dashboard
│   ├── runbooks/
│   │   ├── HighErrorRate.md             # Runbook for error rate alert
│   │   └── HighLatency.md               # Runbook for latency alert
│   ├── docker-compose.yml               # Local stack orchestration
│   ├── PROGRESS.md                      # Phase 1 detailed log
│   ├── CONCEPTS.md                      # Phase 1 educational reference
│   ├── README.md                        # Quick start guide
│   └── .env.example                     # Environment template
│
├── 02-chaos/                            # Phase 2: Chaos Engineering
│   ├── scripts/
│   │   ├── generate_errors.sh           # Error rate chaos script
│   │   └── generate_latency.sh          # Latency chaos script
│   ├── postmortems/
│   │   ├── experiment-01-container-kill.md
│   │   ├── experiment-02-error-flood.md
│   │   └── experiment-03-latency-spike.md
│   ├── PROGRESS.md                      # Phase 2 detailed log
│   └── CONCEPTS.md                      # Phase 2 educational reference
│
├── 03-cicd/                             # Phase 3: CI/CD Ownership
│   ├── k8s/
│   │   ├── deployment.yaml              # K8s deployment manifest
│   │   ├── service.yaml                 # K8s service manifest
│   │   └── servicemonitor.yaml          # Prometheus discovery config
│   ├── PROGRESS.md                      # Phase 3 detailed log
│   ├── CONCEPTS.md                      # Phase 3 educational reference
│   ├── README.md                        # CI/CD reference
│   └── postmortems/
│       └── rollback-drill-phase-3.5.md  # Rollback experiment postmortem
│
├── 04-logs-loki/                        # Phase 4: Log Aggregation
│   ├── loki/
│   │   └── loki-config.yml              # Loki configuration
│   ├── promtail/
│   │   └── promtail-config.yml          # Promtail config (log shipper)
│   ├── PROGRESS.md                      # Phase 4 detailed log
│   ├── CONCEPTS.md                      # Phase 4 educational reference
│   ├── README.md                        # Log querying guide
│   └── postmortems/
│       └── phase-4.5-loki-chaos-investigation.md
│
├── 05-reliability/                      # Phase 5: SLOs & Error Budgets
│   ├── PROGRESS.md                      # Phase 5 detailed log
│   └── CONCEPTS.md                      # Phase 5 educational reference
│
├── 06-tracing/                          # Phase 6: Distributed Tracing
│   ├── tempo/
│   │   └── tempo-config.yml             # Tempo configuration
│   └── CONCEPTS.md                      # Phase 6 educational reference
│
├── CLAUDE.md                            # Project context for Claude Code
├── AGENTS.md                            # Agent definitions
├── README.md                            # Root README (stub)
├── Project_101_Documentation.md         # This document
└── .gitignore                           # Git ignore rules
```

---

## Key Concepts & Lessons Learned

### SRE Fundamentals

#### The Three Pillars of Observability

1. **Metrics** — "Is the system broken?"
   - Numbers measured at a point in time
   - Prometheus scrapes app `/metrics` every 15s
   - PromQL queries return time series data
   - Fast queries, compact storage, great for alerts

2. **Logs** — "What happened?"
   - Raw events with context (timestamp, level, message, fields)
   - Structured JSON for easy parsing
   - Loki stores with label-based indexing
   - LogQL filters and correlates with traces

3. **Traces** — "Where is it slow?"
   - Request journey through system (parent/child spans)
   - Every span shares same trace_id
   - OpenTelemetry SDK auto-instruments requests
   - Tempo builds waterfall views for visualization

#### SLO/SLI/Error Budget

- **SLI** (Service Level Indicator) = the measurement (e.g., 97% success rate)
- **SLO** (Service Level Objective) = the target (e.g., 99% success rate)
- **Error Budget** = allowed failure room (1% of requests can fail per month)
- **Burn Rate** = how fast budget is consumed (1x = exhaust in 30 days, 14.4x = exhaust in 2 days)

#### Four Golden Signals

1. **Traffic** — request rate (calls per second)
2. **Errors** — error rate (failures per second)
3. **Latency** — request duration (p50, p95, p99)
4. **Saturation** — resource utilization (CPU, memory, disk)

Monitors these → dashboards for on-call → alerts for anomalies.

### Prometheus Patterns

#### Metric Types

| Type | Behavior | Use Case |
|------|----------|----------|
| Counter | Monotonically increasing (never down) | Request count, error count |
| Gauge | Up or down | Temperature, queue depth, memory |
| Histogram | Buckets of observations | Request duration, response size |
| Summary | Quantiles (deprecated in favor of histogram) | Similar to histogram |

#### Common PromQL Queries

```promql
# Rate of requests per second (over 1m window)
rate(app_requests_total[1m])

# 95th percentile latency
histogram_quantile(0.95, rate(app_request_duration_seconds_bucket[1m]))

# Error rate
rate(app_errors_total[1m]) / rate(app_requests_total[1m])

# Success rate
1 - (rate(app_errors_total[1m]) / rate(app_requests_total[1m]))
```

### Alert Best Practices

1. **Always test expressions in Prometheus graph view** — label mismatches cause silent failures
2. **Include runbook_url in annotations** — on-call needs documentation instantly
3. **Use `for:` duration to avoid flaky alerts** — require 2-5 minutes of breach before firing
4. **Set severity levels** — critical (page), warning (ticket), info (dashboard)
5. **Route alerts by severity** — critical → PagerDuty, warning → Slack, info → email

### Log Aggregation Patterns

1. **Structured JSON logging** — machine-parseable format with fields
2. **Include context in every log** — trace_id, span_id, user_id, request_path
3. **Log at the right level** — INFO (normal), WARN (unexpected), ERROR (failure)
4. **Use label extraction pipelines** — Promtail extracts fields as searchable labels
5. **Correlate logs ↔ metrics ↔ traces** — via trace_id in logs and derived fields in Grafana

### Chaos Engineering Insights

1. **Blast Radius** — how many users/services affected by a failure?
2. **MTTR** (Mean Time To Recover) — how long until normal service restored?
3. **SLO Impact** — does the failure breach SLO? How much error budget consumed?
4. **Alert Latency** — how long from failure to alert firing? Too long = SLO breached before response
5. **Runbook Effectiveness** — does the documented procedure actually fix the issue?

### CI/CD Best Practices

1. **Immutable tags** — use SHA-based tags for reproducible deployments
2. **Branch protection** — PR required, status checks pass, direct pushes blocked
3. **Container registry visibility** — flip from private to public for portfolio projects
4. **Test before build** — failing tests should block Docker build
5. **Build on every PR** — validates Dockerfile, pushes only on main

### Kubernetes Patterns

1. **ServiceMonitor + Prometheus** — requires matching labels on both resources
2. **imagePullPolicy: Always** — dev/test; production would use specific SHA tags
3. **Resource requests + limits** — prevents resource starvation
4. **Health checks** — liveness + readiness probes
5. **Port naming matters** — ServiceMonitor matches by name, not number

---

## Troubleshooting Guide

### Docker Compose Issues

#### Service fails to start with "port already in use"

**Symptom:**
```
Error response from daemon: Bind for 0.0.0.0:5001 failed: port is already allocated
```

**Solution:**
```bash
# Find process using port
lsof -i :5001

# Kill it or remap port in docker-compose.yml
# Then retry
docker-compose up
```

#### Prometheus can't reach the Flask app

**Symptom:**
```
Prometheus targets show "DOWN"
```

**Diagnosis:**
```bash
# Check if app is running
docker-compose ps

# Check container name matches prometheus.yml
cat 01-observability/prometheus/config/prometheus.yml | grep targets

# Test connectivity from prometheus container
docker-compose exec prometheus curl http://app:5001/metrics
```

**Solution:**
- Ensure `app` service name in docker-compose matches `targets: ['app:5001']` in prometheus.yml
- Check `/metrics` returns correct Content-Type: `text/plain; version=0.0.4; charset=utf-8`

#### Grafana won't show data

**Symptom:**
```
No data in panels, datasource shows "red X"
```

**Diagnosis:**
```bash
# Check datasource connection
curl -u admin:admin http://localhost:3000/api/datasources/uid/prometheus

# Manually test PromQL query
curl -G 'http://localhost:9090/api/v1/query' --data-urlencode 'query=up'
```

**Solution:**
- Restart Grafana: `docker-compose restart grafana`
- Delete `grafana_data` volume if datasource provisioning fails: `docker-compose down -v`

### Prometheus Issues

#### Alert never fires (silently fails)

**Symptom:**
```
Alert rule shows "INACTIVE" forever, never fires even when condition is true
```

**Common Causes:**
1. **Label mismatch** — alert references `job="flask-app"` but actual is `job="sre-lab-app"`
2. **Metric doesn't exist** — PromQL references `app_requests_total` but app only exports `requests_total`
3. **Rate window too short** — `rate(...[30s])` needs 2+ samples, might return NaN initially

**Solution:**
```bash
# Always test expression in Prometheus graph view
http://localhost:9090/graph
# Paste the expression and see if it returns data
# If NaN → not enough history or wrong metric name
# If 0 → metric exists but condition not met

# Verify labels
http://localhost:9090/api/v1/labels
http://localhost:9090/api/v1/label/job/values
```

#### Scrape target keeps timing out

**Symptom:**
```
Prometheus scrape_duration_seconds > 10s
Target shows "Context deadline exceeded"
```

**Solution:**
```bash
# Increase scrape timeout in prometheus.yml
global:
  scrape_timeout: 10s  # default is 10s, increase if needed

# Check if app is slow to respond
curl -v http://localhost:5001/metrics
# If response takes >5s, app is overloaded
```

### Kubernetes Issues

#### ServiceMonitor not picked up by Prometheus

**Symptom:**
```
kubectl get servicemonitor
# Shows ServiceMonitor exists but Prometheus targets doesn't include app
```

**Diagnosis:**
```bash
# Check Prometheus config for ServiceMonitor selector
kubectl get configmap -n monitoring kube-prometheus-stack-prometheus -o yaml | grep -A5 serviceMonitorSelector

# Check if ServiceMonitor has required label
kubectl get servicemonitor -o yaml | grep -A2 labels
```

**Solution:**
- Add label `release: kube-prometheus-stack` to ServiceMonitor metadata
- Ensure Service has label `app: sre-lab-app` (not just selector)
- Ensure ServiceMonitor `port` name matches Service port name (e.g., `http`)

#### Pod image never updates

**Symptom:**
```
kubectl describe pod | grep Image: gcr.io/...@sha256:OLD_SHA
# Even after pushing new image to GHCR
```

**Solution:**
```bash
# Force image pull
kubectl set image deployment/sre-lab-app \
  app=ghcr.io/alvynstar/sre-lab-app:latest --record

# Or delete pod to force restart
kubectl delete pod -l app=sre-lab-app
```

### GitHub Actions Issues

#### CI workflow never triggers

**Symptom:**
```
Git push to main, but GitHub Actions doesn't show workflow run
```

**Diagnosis:**
```bash
# Check .github/workflows/ file syntax
# Check workflow.yml is on main branch
git log --oneline -- .github/workflows/ci.yml

# Check if secrets are missing (e.g., SLACK_WEBHOOK_URL)
```

**Solution:**
- Ensure `.github/workflows/ci.yml` is committed to `main`
- Workflow must be on the branch it triggers on

#### Docker build step fails with "permission denied"

**Symptom:**
```
docker/build-push-action@v6 fails with "permission denied while trying to connect to Docker daemon"
```

**Solution:**
- This is GitHub's default behavior on public repos
- Add `permissions: packages: write` at job level (already done in this project)

### Log Aggregation Issues

#### Promtail can't connect to Loki

**Symptom:**
```
docker logs sre-lab-promtail | grep "failed to post"
```

**Diagnosis:**
```bash
# Check Loki is running
docker-compose ps loki

# Test connectivity
docker-compose exec promtail curl http://loki:3100/api/prom/labels
```

**Solution:**
- Ensure both services on same network: `observability`
- Check `promtail-config.yml` `clients[0].url` matches Loki service name

#### No logs appearing in Loki

**Symptom:**
```
LogQL query: {job="sre-lab-app"} returns "no data"
```

**Diagnosis:**
```bash
# Check Promtail is tailing correctly
docker logs sre-lab-promtail | head -20
# Should show "added {job=sre-lab-app}" 

# Check Flask app is actually writing logs
docker logs sre-lab-app | tail -5
```

**Solution:**
- Flask must log to stdout (not file) — Promtail reads container stdout
- Ensure `promtail-config.yml` has Docker service discovery enabled
- Reload Promtail config: `docker-compose restart promtail`

---

## Contact & Support

### Documentation References

- **Prometheus**: https://prometheus.io/docs/
- **Grafana**: https://grafana.com/docs/grafana/latest/
- **Loki**: https://grafana.com/docs/loki/latest/
- **Tempo**: https://grafana.com/docs/tempo/latest/
- **OpenTelemetry**: https://opentelemetry.io/docs/

### Project Resources

- **GitHub Repository**: https://github.com/alvynstar/sre-lab
- **Slack Alerts Channel**: #all-toks (internal)
- **Author**: Alvin (Infrastructure Engineer at Manulife)
- **Email**: alvindetoya@gmail.com

### Feedback & Contributions

This is a portfolio/learning project. Contributions, corrections, and feedback are welcome:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request with description
4. All PRs must pass CI/CD checks (lint, test, build)

---

## Appendix

### Environment Variables Reference

```bash
# Grafana
GF_ADMIN_USER=admin
GF_ADMIN_PASSWORD=<your_password>

# Slack (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T.../B.../X...

# OpenTelemetry (optional)
OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4317
```

### Common Commands

```bash
# Docker Compose
docker-compose up --build           # Start stack with rebuild
docker-compose down -v              # Stop and remove volumes
docker-compose logs -f <service>    # Stream logs
docker-compose restart <service>    # Restart service

# Kubernetes
kubectl apply -f <manifest>.yaml    # Deploy
kubectl delete -f <manifest>.yaml   # Remove
kubectl get pods                    # List pods
kubectl logs <pod>                  # Pod logs
kubectl port-forward svc/<svc> 8080:80  # Expose service
kubectl describe pod <pod>          # Pod details

# Prometheus
curl -G http://localhost:9090/api/v1/query --data-urlencode 'query=up'
curl -X POST http://localhost:9090/-/reload  # Hot reload config

# Grafana API
curl -H "Authorization: Bearer <token>" http://localhost:3000/api/datasources

# GitHub Actions
gh workflow view ci.yml             # View workflow
gh run list                         # List runs
gh run view <run-id>                # View run details
```

### Git Workflow

```bash
# Clone and setup
git clone https://github.com/alvynstar/sre-lab.git
cd sre-lab

# Create feature branch
git checkout -b feature/my-feature

# Make changes, test
pytest 01-observability/app/tests/
ruff check 01-observability/app/

# Commit with conventional message
git add .
git commit -m "feat: add new dashboard for SLO tracking"

# Push and create PR
git push origin feature/my-feature
# Create PR on GitHub

# After merge, sync main
git checkout main
git pull origin main
```

---

**Document Version**: 1.1  
**Last Updated**: June 6, 2026  
**Next Review**: Before Phase 7 planning
