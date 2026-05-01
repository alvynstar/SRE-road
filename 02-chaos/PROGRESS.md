# Phase 2: Chaos Engineering — Progress Log

## What We're Doing
Deliberately breaking the Phase 1 observability stack in controlled ways to validate that monitoring, alerts, runbooks, and recovery procedures work before a real incident forces you to find out.

Each experiment follows this loop:
```
Break it → Detect it → Respond (follow the runbook) → Recover → Write postmortem
```

---

## Chaos Engineering — Concept

Chaos Engineering is the practice of deliberately introducing failures into a system in a controlled way to find weaknesses *before* production does it for you.

| Your instinct | SRE term |
|---------------|----------|
| Worst case scenario | Blast radius |
| Resolve ASAP | MTTR (Mean Time to Recover) |
| Avoid cost | Cost of downtime / business impact |

---

## Experiments

| # | Experiment | Goal | Alert Tested | Status |
|---|-----------|------|-------------|--------|
| 1 | Kill Flask container | Test if app outage is detected | None → `AppDown` (added) | **COMPLETE** |
| 2 | Error rate flood | Validate `HighErrorRate` alert end-to-end | HighErrorRate | **COMPLETE** |
| 3 | Latency spike | Validate `HighLatency` alert end-to-end | HighLatency | **COMPLETE** |

---

## Experiment 1 — Findings (2026-04-29)

**What broke:** Stopped `sre-lab-app` container. Prometheus scrape failed with DNS lookup error.

**Critical gap discovered:** No alert fired when the app went down. The existing `HighErrorRate` and `HighLatency` rules depend on metrics emitted by the app itself — when the app is dead, no metrics flow, so nothing evaluates to a firing state. Slack stayed silent.

**Fix applied:**
- Added `AppDown` alert rule using `up{job="sre-lab-app"} == 0` — Prometheus generates the `up` metric itself on every scrape attempt, so it works even when the target is dead.
- Enabled Prometheus lifecycle API in `docker-compose.yml` (`--web.enable-lifecycle`) for hot reloads via `POST /-/reload`.

**Validation:** Re-ran the experiment after the fix. AppDown moved Inactive → Pending → Firing within ~30 seconds, Slack notification arrived in `#all-toks`, and alert auto-resolved when container was restarted.

**SRE lesson:** First attempt at the alert silently never fired because the expression used `job="flask-app"` while the actual scrape job is `sre-lab-app`. Label mismatches are one of the most common reasons alerts silently fail. Always test the expression in `http://localhost:9090/graph` before trusting the alert.

**Files changed:**
- `01-observability/prometheus/config/alerts.yml` — added `AppDown` rule
- `01-observability/docker-compose.yml` — added `--web.enable-lifecycle` flag

---

## Experiment 2 — Findings (2026-04-29)

**What broke:** Ran `scripts/generate_errors.sh` which floods `/api/error` at 2 req/s for 120 seconds, pushing `rate(app_errors_total[1m])` above the 0.7 req/s threshold.

**Result:** Full alert path validated.
- Alert moved Inactive → Pending → Firing in Prometheus (~4 minutes from flood start)
- Slack notification received in `#all-toks`
- Alert moved to **Resolved** ~3 minutes after the flood ended
- Slack resolved notification received

**Bug fixed mid-experiment:**
- Chaos script silently completed only 1 of 240 requests because `bc` is not installed in Git Bash. The line `COUNT=$(echo "$DURATION / $INTERVAL" | bc)` returned an empty string, so `seq 1 ` ran with no end argument.
- Fixed by replacing `bc` with native bash arithmetic: `COUNT=$((DURATION * RATE))`.
- Diagnosed by re-running with `bash -x generate_errors.sh` (trace mode).

**SRE lesson:** Chaos scripts with external dependencies fail silently. Either declare requirements up front (and check at script start) or stick to portable shell builtins. Trace mode (`bash -x`) is the fastest way to debug a script that "did nothing".

**MTTR observation:** ~4 minutes from flood start to firing is the floor for this alert because:
- `rate(...[1m])` needs ~1 minute of data to compute
- `for: 1m` requires 1 minute of sustained breach before firing
- `evaluation_interval: 15s` means up to 15s extra latency
- If faster detection were needed in production, shorten `for:` or use a shorter rate window like `[30s]`.

**Files changed:**
- `02-chaos/scripts/generate_errors.sh` — replaced `bc` math with bash arithmetic (also renamed from `02-chaos/chaos/` during repo reorg)

---

## Experiment 3 — Findings (2026-04-29)

**What broke:** Ran `scripts/generate_latency.sh` which fires one request per second to `/api/slow` (each takes ~6s), pushing concurrent in-flight requests up and `histogram_quantile(0.95, ...)` above the 5s threshold.

**Result:** Full alert path validated.
- Script started at 16:43, alert fired at 16:45 (Pending → Firing)
- Slack notification received in `#all-toks`
- After Ctrl+C at ~16:46, alert resolved at ~16:48
- `HighErrorRate` correctly stayed silent — slow ≠ error

**Key insight — p95 ≈ p50:**
- Both percentiles climbed to ~7.5s in Grafana
- This is *not* the p95/p50 divergence pattern of a real partial degradation
- Reason: every `/api/slow` request is uniformly slow, so 50th and 95th percentiles converge
- Real-world note: when investigating production latency, a wide gap between p50 and p95 means *some* requests are slow; a small gap means *all* requests are slow. Different root causes, different fixes.

**Errors panel stayed at "No data":** Confirmed metrics independence. Latency and errors are separate signals — an alert on one doesn't fire the other.

**Follow-up filed:** Add a `/api/sometimes-slow` endpoint (slow only ~10% of requests) for a more realistic partial-degradation drill in a future experiment.

---

## Phase 2 Summary

All three alerts validated end-to-end against the full pipeline (Prometheus → AlertManager → Slack). Discovered and closed one critical alerting gap (`AppDown`). Fixed one chaos-script bug (`bc` dependency). Identified one realism gap in the latency drill (filed as follow-up).

**Total alerts in stack:** 3 (`AppDown`, `HighErrorRate`, `HighLatency`) — all tested.

---

## Files

| File | Purpose |
|------|---------|
| `scripts/generate_errors.sh` | Floods `/api/error` at 2 req/s to trigger HighErrorRate |
| `scripts/generate_latency.sh` | Hits `/api/slow` continuously to trigger HighLatency |
| `postmortems/experiment-01-container-kill.md` | Postmortem — fill in live during Experiment 1 |
| `postmortems/experiment-02-error-flood.md` | Postmortem — fill in live during Experiment 2 |
| `postmortems/experiment-03-latency-spike.md` | Postmortem — fill in live during Experiment 3 |

**App change (lives in Phase 1 stack):**
- `../01-observability/app/app.py` — `/api/slow` endpoint added (6s sleep, triggers HighLatency)

---

## How to Run Each Experiment

> **Prerequisite:** Stack must be running. From `01-observability/`: `docker-compose up -d`

### Experiment 1 — Kill Flask Container
```bash
docker stop sre-lab-app          # break it
# watch http://localhost:9090/targets — target turns red
# check http://localhost:9090/alerts do— does an alert fire?
docker start sre-lab-app         # recover
# fill in postmortems/experiment-01-container-kill.md
```

### Experiment 2 — Error Rate Flood
```bash
bash scripts/generate_errors.sh    # runs 120s at 2 req/s
# watch http://localhost:9090/alerts — Inactive → Pending → Firing
# check Slack #all-toks for notification
# follow ../01-observability/runbooks/HighErrorRate.md
# fill in postmortems/experiment-02-error-flood.md
```

### Experiment 3 — Latency Spike
```bash
# First time only — rebuild app to pick up /api/slow:
cd ../01-observability && docker-compose up -d --build app && cd ../02-chaos

bash scripts/generate_latency.sh   # runs until Ctrl+C
# watch http://localhost:9090/alerts — fires after 2 minutes sustained
# check Grafana p95 latency panel at http://localhost:3000
# follow ../01-observability/runbooks/HighLatency.md
# fill in postmortems/experiment-03-latency-spike.md
```

---

## Status Tracker
- [x] Experiment 1 complete + postmortem filled + gap fixed (AppDown alert) + fix validated
- [x] Experiment 2 complete + postmortem filled + chaos script bug fixed
- [x] Experiment 3 complete + postmortem filled + p95/p50 convergence insight documented
- [x] **Phase 2 COMPLETE** — ready to start Phase 3

---

## What's Next
- Phase 3: CI/CD ownership
- Phase 4: Log aggregation (Loki)
