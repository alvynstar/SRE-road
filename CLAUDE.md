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

## Phase 3 — CI/CD Ownership (IN PROGRESS)

### Sub-phases
| # | Sub-phase | Status |
|---|-----------|--------|
| 3.1 | pytest + ruff + GitHub Actions CI | **COMPLETE** |
| 3.2 | Docker build + push to GHCR | **COMPLETE** — image public at `ghcr.io/alvynstar/sre-lab-app`, validated end-to-end |
| 3.3 | Deploy image to `sre-lab` kind cluster | **NEXT** |
| 3.4 | Grafana deploy annotations | PLANNED |
| 3.5 | Rollback drill + postmortem | PLANNED |

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

### Future phases
- Phase 4: Log aggregation (Loki) — see `04-logs-loki/README.md`

### Incidents debugged so far (Phase 1)
- Port 5000 conflict with local Docker registry → remapped Flask to 5001
- Prometheus scrape returning HTML instead of metrics → fixed Content-Type header
- Stale scrape config after port change → updated prometheus.yml
- kind cluster EOF after 13 months → created fresh sre-lab cluster

### Issues debugged so far (Phase 2)
- Prometheus lifecycle API disabled by default → added `--web.enable-lifecycle` flag and recreated container (`docker-compose up -d --force-recreate prometheus`, not `restart`)
- `AppDown` alert silently never fired → label mismatch (`job="flask-app"` vs `sre-lab-app`); fixed by aligning with `prometheus.yml` job name
- Chaos script `generate_errors.sh` only sent 1/240 requests → `bc` not installed in Git Bash; replaced with native bash arithmetic (`COUNT=$((DURATION * RATE))`). Diagnosed with `bash -x` trace mode.

### Issues debugged so far (Phase 3)
- Classic GitHub branch protection silently doesn't enforce on private free-tier repos (banner: "won't be enforced until you move to GitHub Team or Enterprise"). Options: make repo public, switch to Repository Rulesets, or pay. Chose public after passing a full-history secret scan.
- GHCR package created as **private by default** even when source repo is public. Anonymous `docker pull` fails until visibility flipped manually in package settings → Danger Zone → Public.
- "Require approvals: 1" in branch protection blocks solo developers — GitHub does not let you approve your own PR. Set approvals to 0 (untick the sub-checkbox) and leave "Require a pull request" ticked to keep the PR-flow gate without the approval gate.

## Repo Structure (Roadmap View)
```
sre-lab/
├── 01-observability/   ← Phase 1 (DONE)
├── 02-chaos/           ← Phase 2 (DONE — all 3 experiments validated end-to-end)
│   ├── scripts/        ← chaos load generators
│   ├── postmortems/    ← experiment writeups
│   └── PROGRESS.md
├── 03-cicd/            ← Phase 3 (IN PROGRESS — 3.1 + 3.2 done; 3.3 next)
└── 04-logs-loki/       ← Phase 4 (PLANNED)
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