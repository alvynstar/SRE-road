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

## Teaching Style
Use a Socratic/mentorship approach: explain concepts and ask guiding questions before writing code. Treat me as a learner who wants to understand patterns, not just get working code.

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

## Phase 2 — Chaos Engineering (COMPLETE)

### What we're doing
Deliberately breaking the Phase 1 stack in controlled ways to validate that monitoring, alerts, runbooks, and recovery procedures actually work. Three experiments planned — each one ends with a postmortem.

### Experiments
| # | Experiment | Status |
|---|-----------|--------|
| 1 | Kill Flask container — discover alerting gap | **COMPLETE** — gap found, `AppDown` alert added and validated |
| 2 | Error rate flood — validate HighErrorRate end-to-end | **COMPLETE** — alert + Slack confirmed firing and resolving |
| 3 | Latency spike — validate HighLatency end-to-end | **COMPLETE** — alert + Slack confirmed; learned p95≈p50 because `/api/slow` is uniformly slow (real partial degradation would diverge) |

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

---

## Phase 3 — CI/CD Ownership (COMPLETE)

### Sub-phases
| # | Sub-phase | Status |
|---|-----------|--------|
| 3.1 | pytest + ruff + GitHub Actions CI | **COMPLETE** |
| 3.2 | Docker build + push to GHCR | **COMPLETE** — image public at `ghcr.io/alvynstar/sre-lab-app`, validated end-to-end |
| 3.3 | Deploy image to `sre-lab` kind cluster | **COMPLETE** — Deployment + Service + ServiceMonitor created; Prometheus auto-scraping app |
| 3.4 | Grafana deploy annotations | **COMPLETE** — vertical annotation line on Four Golden Signals dashboard after every deploy |
| 3.5 | Rollback drill + postmortem | **COMPLETE** — bad deploy simulated, error spike observed in Grafana, rolled back via git revert; postmortem written |

### What was built (3.1 + 3.2)
- pytest tests for Flask app under `01-observability/app/tests/`
- ruff lint config; both lint + tests run on every PR and push to main
- `docker-build-push` job in `.github/workflows/ci.yml` — builds on every event, pushes only on main
- Image tagged with `sha-<short>` (immutable), `main`, `latest` on every push to main
- GHCR package `sre-lab-app` made public — anonymous `docker pull` works
- Branch protection on `main` — PR required, status checks must pass, direct pushes blocked
- Repo flipped from private to public after secret-scan to enable free branch protection + unlimited Actions minutes

### Key files
- `.github/workflows/ci.yml` — CI workflow (lint+test → docker-build-push)
- `01-observability/app/tests/` — pytest test files
- `03-cicd/PROGRESS.md` — sub-phase log

### Key lessons learned

**Prometheus / Alerting**
- Always validate alert expressions in Prometheus graph view before trusting them — label mismatches cause silent failures
- `docker-compose up -d --force-recreate <service>` (not `restart`) is required after adding new flags like `--web.enable-lifecycle`

**GitHub / CI**
- GHCR packages are **private by default** even when the source repo is public — flip visibility manually in package settings
- Branch protection on free-tier private repos is not enforced — make repo public or use Repository Rulesets
- On Windows self-hosted runners: use `Invoke-RestMethod` instead of `curl`; avoid `shell: bash` unless WSL is installed
- Store secrets via `gh secret set --body "value"` — piping via `|` adds a trailing newline that breaks tokens

**Kubernetes**
- Using `latest` image tag means `kubectl rollout undo` has no history to roll back to — use SHA tags in production deployments
- ServiceMonitor requires label `release: kube-prometheus-stack` and matching port names to be picked up by Prometheus

**Grafana**
- Annotations must include `dashboardUID` to appear on a specific dashboard — global annotations (no UID) are hidden by default
- Datasource provisioning fails with "data source not found" when `grafana_data` volume has old auto-generated UIDs conflicting with explicit `uid:` fields — fix by deleting the volume so Grafana recreates from provisioning files
- Deleting `grafana_data` volume invalidates all existing API tokens — regenerate service account token and update GitHub secret after any volume wipe

---

## Phase 4 — Log Aggregation with Loki (COMPLETE)

### Sub-phases
| # | Sub-phase | Status |
|---|-----------|--------|
| 4.1 | Add Loki + Promtail to Docker Compose | **COMPLETE** — logs flowing from container to Loki |
| 4.2 | Structured JSON logging in Flask app | **COMPLETE** — `python-json-logger` emitting `levelname`, `endpoint`, `status`, `duration` |
| 4.3 | Validate log pipeline with LogQL | **COMPLETE** — filtered logs by level and endpoint in Grafana Explore |
| 4.4 | Combined metrics + logs dashboard | **COMPLETE** — "Flask App — Metrics + Logs" dashboard with 4 panels |

### What was built
- Loki single-node config (`04-logs-loki/loki/loki-config.yml`) — filesystem storage, schema v13, auth disabled
- Promtail config (`04-logs-loki/promtail/promtail-config.yml`) — Docker service discovery, JSON pipeline stage extracting `level`/`endpoint`/`status` as labels
- Flask app emits structured JSON logs on every request using `python-json-logger`
- Grafana Loki datasource provisioned with `uid: loki` to match dashboard references
- Combined dashboard (`flask-logs-and-metrics.json`) — Error Rate, Traffic, Latency p95 (Prometheus) + App Logs (Loki)

### Sub-phases (updated)
| # | Sub-phase | Status |
|---|-----------|--------|
| 4.1 | Add Loki + Promtail to Docker Compose | **COMPLETE** |
| 4.2 | Structured JSON logging in Flask app | **COMPLETE** |
| 4.3 | Validate log pipeline with LogQL | **COMPLETE** |
| 4.4 | Combined metrics + logs dashboard | **COMPLETE** |
| 4.5 | Re-run chaos experiment + LogQL investigation | **COMPLETE** — correlated Prometheus spike with Loki logs; fixed instrumentation gap on `/api/error` |

### Key files
- `04-logs-loki/loki/loki-config.yml` — Loki config
- `04-logs-loki/promtail/promtail-config.yml` — Promtail config
- `01-observability/app/app.py` — Flask app with structured JSON logging
- `01-observability/grafana/dashboards/flask-logs-and-metrics.json` — combined dashboard
- `01-observability/grafana/provisioning/datasources/prometheus.yml` — Prometheus + Loki datasources
- `04-logs-loki/postmortems/phase-4.5-loki-chaos-investigation.md` — postmortem with LogQL queries

### Key lessons learned (Phase 4)
- Metrics give you the alarm; logs give you the evidence — you need both to investigate an incident
- LogQL filter syntax: `{container="/sre-lab-app"} | json | levelname = \`ERROR\``
- Error endpoints must also record `request_count` and `request_duration` — omitting them creates dashboard blind spots
- Correlate Loki log volume bar chart with Prometheus spike to confirm both signals track the same event

---

## Phase 5 — SLOs & Error Budgets (COMPLETE)

### Sub-phases
| # | Sub-phase | Status |
|---|-----------|--------|
| 5.1 | Define SLOs (availability + latency) | **COMPLETE** — 99% availability, p95 < 300ms |
| 5.2 | Prometheus recording rules | **COMPLETE** — `slo:availability:rate5m/1h`, `slo:latency_p95:rate5m`, `slo:error_budget_remaining:rate1h` |
| 5.3 | Error budget Grafana dashboard | **COMPLETE** — availability gauge, error budget gauge, SLO target, latency p95 + timeseries panels |
| 5.4 | Burn rate alerts | **COMPLETE** — `SloBudgetFastBurn` (>14.4x for 2m) and `SloBudgetSlowBurn` (>1x for 15m) validated firing |

### What was built
- SLO recording rules (`slo-rules.yml`) — pre-computed SLIs stored as metrics for efficient querying
- SLO dashboard (`slo-dashboard.json`) — 6 panels: availability gauge, error budget gauge, SLO target, latency p95, and two timeseries with SLO target lines
- Burn rate alerts in `alerts.yml` — FastBurn fires when budget exhausted in < 2 days; SlowBurn fires when burning steadily
- Validated at 61.5x burn rate with `SloBudgetFastBurn` firing in Prometheus

### Key files
- `05-reliability/PROGRESS.md` — phase log
- `01-observability/prometheus/config/slo-rules.yml` — recording rules
- `01-observability/prometheus/config/alerts.yml` — burn rate alert group added
- `01-observability/grafana/dashboards/slo-dashboard.json` — SLO dashboard

### Key lessons learned (Phase 5)
- SLI = measurement, SLO = target, error budget = allowed failure room — these three concepts drive all SRE reliability decisions
- Recording rules pre-compute expensive PromQL expressions so dashboards stay fast at scale
- Burn rate > 14.4x = page now (budget gone in 2 days); burn rate > 1x = ticket (budget draining steadily)
- `rate()` needs at least 2 Prometheus scrapes — NaN means not enough history yet, not a bug

---

## Phase 6 — (PLANNED)

---

## Repo Structure (Roadmap View)
```
sre-lab/
├── 01-observability/   ← Phase 1 (DONE)
├── 02-chaos/           ← Phase 2 (DONE — all 3 experiments validated end-to-end)
│   ├── scripts/        ← chaos load generators
│   ├── postmortems/    ← experiment writeups
│   └── PROGRESS.md
├── 03-cicd/            ← Phase 3 (DONE — all 5 sub-phases complete)
├── 04-logs-loki/       ← Phase 4 (DONE — all 5 sub-phases complete)
└── 05-reliability/     ← Phase 5 (DONE — SLOs, error budget dashboard, burn rate alerts)
```

## Secrets & Env
- Never commit API keys; always store in `.env` and verify `.env` is gitignored.
- When reading `.env` values, check for stray quotes around keys (common bug source).
- Before any `git push`, scan staged diff for secret-like strings.

## Docker & CI Checks
- Before running `docker build`, confirm `Dockerfile` exists and check `.dockerignore` won't exclude needed files (nginx.conf, config dirs).
- For docker-compose volume mounts, mount the config directory, not just a single file, when multiple configs are referenced.
- For GitHub Actions on Linux, proactively add system deps (portaudio, xvfb for Qt apps) before pushing.

## Session update reminder
At the end of each session, update this file with what was completed and what's next.