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

## Phase 1 — Observability (COMPLETE)

### What was built
- Docker Compose stack: Flask app (5001), Prometheus (9090), Grafana (3000), AlertManager (9093)
- Flask app instrumented with `app_requests_total`, `app_request_duration_seconds`, `app_errors_total`
- Endpoints: `/health`, `/metrics`, `/api/data`, `/api/error`, `/api/slow` (added for Phase 2)
- Four Golden Signals Grafana dashboard auto-provisioned (Traffic, Error Rate, Latency p95, Latency p50)
- Prometheus alert rules: `HighErrorRate` (>0.7 req/s for 1m), `HighLatency` (p95 >5s for 2m), `AppDown` (`up == 0` for 30s — added during Phase 2 Experiment 1)
- AlertManager → Slack integration confirmed working (`#all-toks`)
- Runbooks: `HighErrorRate.md`, `HighLatency.md` in `01-observability/runbooks/`
- kube-prometheus-stack deployed via Helm into `sre-lab` kind cluster

### Key files
- `01-observability/app/app.py` — Flask app with all metrics and endpoints
- `01-observability/docker-compose.yml` — full stack orchestration
- `01-observability/prometheus/config/prometheus.yml` — scrape config
- `01-observability/prometheus/config/alerts.yml` — alert rules
- `01-observability/alertmanager/config/alertmanager.yml` — Slack routing
- `01-observability/runbooks/` — HighErrorRate.md, HighLatency.md
- `01-observability/PROGRESS.md` — detailed phase log

---

## Current Phase: Phase 2 — Chaos Engineering (Active)

### What we're doing
Deliberately breaking the Phase 1 stack in controlled ways to validate that monitoring, alerts, runbooks, and recovery procedures actually work. Three experiments planned — each one ends with a postmortem.

### Experiments
| # | Experiment | Status |
|---|-----------|--------|
| 1 | Kill Flask container — discover alerting gap | **COMPLETE** — gap found, `AppDown` alert added and validated |
| 2 | Error rate flood — validate HighErrorRate end-to-end | **COMPLETE** — alert + Slack confirmed firing and resolving |
| 3 | Latency spike — validate HighLatency end-to-end | In progress — app rebuilt with `/api/slow`, endpoint verified (6s response confirmed) |

### Experiment 1 takeaway
- Stopping the app produced **zero alerts** because `HighErrorRate`/`HighLatency` depend on metrics emitted by the app itself.
- Fix: added `AppDown` rule using `up{job="sre-lab-app"} == 0` (Prometheus generates `up` itself, so it works even when the target is dead).
- Enabled `--web.enable-lifecycle` flag on Prometheus to allow hot config reloads (`POST /-/reload`).
- First attempt of the alert silently never fired due to a label mismatch (`job="flask-app"` vs actual `sre-lab-app`) — always validate the expression in Prometheus graph view before trusting an alert.

### Key files
- `02-chaos/PROGRESS.md` — detailed phase log
- `02-chaos/scripts/generate_errors.sh` — floods `/api/error` at 2 req/s
- `02-chaos/scripts/generate_latency.sh` — hits `/api/slow` continuously
- `02-chaos/postmortems/` — postmortem templates (fill in live during each experiment)

### What's next after Phase 2
- Phase 3: CI/CD ownership — see `03-cicd/README.md` for plan
- Phase 4: Log aggregation (Loki) — see `04-logs-loki/README.md` for plan

### Incidents debugged so far (Phase 1)
- Port 5000 conflict with local Docker registry → remapped Flask to 5001
- Prometheus scrape returning HTML instead of metrics → fixed Content-Type header
- Stale scrape config after port change → updated prometheus.yml
- kind cluster EOF after 13 months → created fresh sre-lab cluster

### Issues debugged so far (Phase 2)
- Prometheus lifecycle API disabled by default → added `--web.enable-lifecycle` flag and recreated container (`docker-compose up -d --force-recreate prometheus`, not `restart`)
- `AppDown` alert silently never fired → label mismatch (`job="flask-app"` vs `sre-lab-app`); fixed by aligning with `prometheus.yml` job name
- Chaos script `generate_errors.sh` only sent 1/240 requests → `bc` not installed in Git Bash; replaced with native bash arithmetic (`COUNT=$((DURATION * RATE))`). Diagnosed with `bash -x` trace mode.

## Repo Structure (Roadmap View)
```
sre-lab/
├── 01-observability/   ← Phase 1 (DONE)
├── 02-chaos/           ← Phase 2 (in progress — Exp 3 pending)
│   ├── scripts/        ← chaos load generators
│   ├── postmortems/    ← experiment writeups
│   └── PROGRESS.md
├── 03-cicd/            ← Phase 3 (PLANNED)
└── 04-logs-loki/       ← Phase 4 (PLANNED)
```

## Session update reminder
At the end of each session, update this file with what was completed and what's next.