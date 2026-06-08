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

## Phase 6 — Distributed Tracing with Tempo & OpenTelemetry (COMPLETE)

### What was built
- OpenTelemetry SDK fully instrumented in Flask app (lines 6–24 of `app.py`)
- Auto-instrumentation wraps all HTTP routes automatically — no manual route instrumentation needed
- `TraceIdFilter` class injects `trace_id` and `span_id` into every JSON log line for log-to-trace correlation
- Manual `artificial_delay` span on `/api/slow` route to show child span nesting
- Error span on `/api/error` route with exception recording and error status marking
- Tempo backend configured and running on ports 4317 (OTLP gRPC), 4318 (OTLP HTTP), 3200 (API)
- Infrastructure fixes: app `depends_on: tempo`, explicit `OTEL_EXPORTER_OTLP_ENDPOINT` env var, persistent `tempo_data` volume
- Grafana Tempo datasource provisioned, Loki derived fields enable one-click log→trace jumps
- End-to-end validation: waterfall view in Grafana, log-to-trace correlation working, error traces marked red
- **Portfolio documentation**: CONCEPTS.md enhanced with "Why This Matters" intro + practical Grafana walkthrough; PHASE-SUMMARY.md created for interview talking points

### Sub-phases
| # | Sub-phase | Status |
|---|-----------|--------|
| 6.1 | Concepts & architecture | **COMPLETE** — trace/span/trace_id mental model in CONCEPTS.md |
| 6.2 | Infrastructure gaps fixed | **COMPLETE** — startup ordering, persistent storage, explicit env vars |
| 6.3 | End-to-end validation | **COMPLETE** — waterfall view, log-to-trace jumps, error marking all working |
| 6.4 | Portfolio documentation | **COMPLETE** — CONCEPTS.md enhanced for interviews; PHASE-SUMMARY.md with "why this matters" + skills demonstrated |

### Key files
- `01-observability/app/app.py` — Flask app with OTel SDK setup, auto-instrumentation, manual spans, error recording
- `01-observability/docker-compose.yml` — Tempo service, app `depends_on: tempo`, OTEL env var, persistent volume
- `06-tracing/tempo/tempo-config.yml` — Tempo configuration (OTLP receivers, local filesystem storage)
- `06-tracing/PROGRESS.md` — Phase 6 detailed progress log with validation results
- `06-tracing/CONCEPTS.md` — **ENHANCED** Educational reference: mental models, architecture, practical Grafana walkthrough ("How to Read a Waterfall")
- `06-tracing/PHASE-SUMMARY.md` — **NEW** Portfolio summary: what was built, why it matters for SRE, skills demonstrated, interview talking points, team discussion points
- `01-observability/grafana/provisioning/datasources/prometheus.yml` — Tempo datasource + Loki derived fields

### Portfolio Angle
Phase 6 completes the observability triangle. You can now answer:
- **Metrics:** "Is it broken?" (Phase 1–3)
- **Logs:** "What happened?" (Phase 4)
- **Traces:** "Where is it slow?" (Phase 6)

All three are wired together via `trace_id` in JSON logs + Grafana derived fields. This demonstrates:
- ✅ Multi-pillar observability (not just "we use Prometheus")
- ✅ Request lifecycle understanding (why a 6-second request takes 6 seconds)
- ✅ Application-level instrumentation (OTel SDK, not just infra metrics)
- ✅ Correlation patterns (logs ↔ traces via trace_id injected into JSON)
- ✅ SRE problem-solving mindset (tools serve a purpose: debug issues faster)

**Interview talking point:** *"Metrics tell you when something broke. Logs tell you what broke. Traces tell you where it's slow. Here's how I correlate all three with a trace_id in JSON logs and one click in Grafana."*

### Key lessons learned
- **Traces = request journey**: Every request gets a tracking number (trace_id), every operation is a span. The waterfall shows exactly where time went.
- **Log-to-trace correlation is the SRE superpower**: Injecting trace_id into logs + derived fields enables one-click jumps from "error in logs" to "full request breakdown" without changing interfaces.
- **Startup ordering matters**: `depends_on: tempo` ensures Tempo is listening before the app tries to send spans. Without it, early spans are silently lost.
- **Infrastructure wiring belongs in config**: Moving `OTEL_EXPORTER_OTLP_ENDPOINT` from hardcoded defaults to explicit env var makes the tracing target visible and environment-overridable.
- **Persistent storage for observability**: Named volumes for Tempo preserve trace history across restarts. Same principle as Prometheus and Loki.
- **Error spans must be marked**: Recording exceptions and setting error status makes failed requests visually distinct in waterfalls — critical for incident investigation.
- **Portfolio narrative > implementation details**: Document *why* something matters (for SREs, for interviews) before *how* it works. PHASE-SUMMARY.md is more valuable than code samples alone for portfolio review.

---

## Phase 7 — Kubernetes Advanced Operations (IN PROGRESS)

### What we're building
Multi-node Kubernetes cluster with cluster-level observability, persistent storage, network policies, and operational procedures. Moving from "single-node kind with basic Deployments" (Phase 3) to production-like K8s infrastructure.

### Sub-phases
| # | Sub-phase | Status |
|---|-----------|--------|
| 7.1 | Scale to 3-node kind cluster | **TODO** — multi-node environment |
| 7.2 | Cluster-level observability | **TODO** — node metrics, kubelet, resource usage |
| 7.3 | Persistent storage + StatefulSet | **TODO** — database-like workload example |
| 7.4 | Network policies + resource limits | **TODO** — see what happens when limits breach |
| 7.5 | Operational procedures | **TODO** — drain, cordon, upgrade runbooks |

### Why Phase 7 matters
You can't debug a broken app without understanding the cluster it runs on. Resource contention, node failures, storage exhaustion are common prod issues. Phase 7 teaches cluster operations SRE.

### Key files (TBD)
- `07-kubernetes/kind-config.yaml` — 3-node cluster config
- `07-kubernetes/PROGRESS.md` — phase log
- `07-kubernetes/terraform/` or `manifests/` — IaC (to be decided)

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
├── 05-reliability/     ← Phase 5 (DONE — SLOs, error budget dashboard, burn rate alerts)
├── 06-tracing/         ← Phase 6 (DONE — distributed tracing with Tempo + OTel)
└── 07-kubernetes/      ← Phase 7 (IN PROGRESS — multi-node K8s, cluster ops)
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