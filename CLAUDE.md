# SRE Lab — Context for Claude Code

## Who I am
Infrastructure Engineer at Manulife (Azure, GCP), transitioning to SRE.
Background: Terraform, Ansible, Jenkins, Python, Bash, HIPAA/PCI compliance.

## My goal
Build real, demonstrable SRE skills — observability, K8s operations,
CI/CD ownership, incident management, chaos engineering.

## How to work with me
- Explain the concept before writing code
- Don't just give me answers — ask me to debug first
- Point out when I'm doing something non-SRE (e.g. manual fixes instead of automation)
- Push me to write runbooks and postmortems for every incident simulation

## Current Phase: Phase 1 — Observability (Active)

### What's been completed
- Docker Compose stack running locally: Flask app (port 5001), Prometheus (9090), Grafana (3000)
- Flask app instrumented with Prometheus client — exposes request count and latency metrics
- Prometheus scraping Flask `/metrics` endpoint every 10s
- kube-prometheus-stack deployed via Helm into a dedicated `sre-lab` kind cluster
- Grafana dashboards available at localhost:3000 (Docker) and localhost:3001 (K8s via port-forward)
- Secrets management in place — `.env` gitignored, `.env.example` committed

### What's been completed (continued)
- Error counter metric added to Flask app (`app_errors_total` with endpoint + status_code labels)
- `/api/error` endpoint added to simulate 500 failures
- Four Golden Signals Grafana dashboard built and auto-provisioned (no manual UI setup)
- Dashboard panels: Traffic, Error Rate, Latency p95, Latency p50
- Tested with live traffic — error rate spike confirmed visible in real time

### What's been completed (continued)
- Prometheus alert rules configured (`alerts.yml`) with two rules:
  - `HighErrorRate` — fires when error rate > 0.7 req/s for 1 minute
  - `HighLatency` — fires when p95 latency > 5s for 2 minutes
- Alert lifecycle confirmed: Inactive → Pending → Firing
- Fixed docker-compose volume mount to expose entire `prometheus/config/` folder

### What's next (next session)
- Configure AlertManager to route alerts to Slack/email/PagerDuty
- Write a runbook for each alert

### Incidents debugged so far
- Port 5000 conflict with local Docker registry → remapped Flask to 5001
- Prometheus scrape returning HTML instead of metrics → fixed Content-Type header
- Stale scrape config after port change → updated prometheus.yml
- kind cluster EOF after 13 months → created fresh sre-lab cluster

### Key files
- `01-observability/app/app.py` — Flask app with Prometheus metrics
- `01-observability/docker-compose.yml` — local stack orchestration
- `01-observability/prometheus/config/prometheus.yml` — scrape config
- `01-observability/PROGRESS.md` — detailed progress log

### Next phases (planned)
- Phase 2: Alert rules + runbooks
- Phase 3: Chaos engineering / incident simulation
- Phase 4: CI/CD ownership
- Phase 5: Log aggregation (Loki)

## Session update reminder
At the end of each session, update this file with what was completed and what's next.