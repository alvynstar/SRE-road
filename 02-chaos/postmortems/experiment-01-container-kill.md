# Postmortem — Experiment 01: Flask Container Kill

**Date:** 2026-04-29  
**Experiment:** Deliberately stopped the `sre-lab-app` container to test whether monitoring detects a complete app outage.

---

## What We Broke
Stopped the Flask container (`docker stop sre-lab-app`). This removed the `/metrics` endpoint from the network, causing Prometheus scrapes to fail.

---

## Timeline

| Time  | Event |
|-------|-------|
| 05:53 | `docker stop sre-lab-app` executed |
| 05:58 | Prometheus target turned red — error: `dial tcp: lookup app on 127.0.0.11:53: no such host` |
| 05:58 | Alert fired in Prometheus — **NO** |
| 05:58 | Slack notification received — **NO** |
| 06:00 | `docker start sre-lab-app` executed |
| 06:01 | Prometheus target turned green again |

---

## Detection
- [ ] Alert fired in Prometheus automatically
- [ ] Slack notification received
- [x] Manually noticed at localhost:9090/targets — scrape error visible
- [ ] Grafana dashboard showed drop

---

## Root Cause
The Flask container was stopped, removing it from the Docker `observability` network. Prometheus attempted to scrape `http://app:5001/metrics` but the DNS name `app` no longer resolved — resulting in `dial tcp: lookup app on 127.0.0.11:53: no such host`. With no metrics coming in, the counter-based alert rules (`HighErrorRate`, `HighLatency`) had nothing to evaluate and stayed inactive.

---

## Impact (if this were production)
- All API traffic to the Flask app would return connection errors
- No alert would fire automatically (see Gaps below)
- On-call team would only find out from users reporting errors or from manually checking Prometheus targets
- Time to detection: dependent on human checking, not automated alerting

---

## MTTR
| Phase | Duration |
|-------|----------|
| Time to detect (manual check of Prometheus targets) | ~10 seconds |
| Time to diagnose (identified scrape failure + alerting gap) | ~2 minutes |
| Time to recover (`docker start sre-lab-app`) | ~30 seconds |
| **Total MTTR** | ~3 minutes |

> Note: Detection was manual. Without someone actively watching Prometheus, this incident would have had infinite detection time — no automated alert would have fired.

---

## What Worked
<!-- Fill in honestly after running the experiment -->
- Prometheus target page showed the failure immediately (visual)
- Container restart was fast and automatic reconnection happened

## Gaps Found
- **No alert rule for scrape failure.** When the app went completely down, zero alerts fired. The only way to detect it was manual inspection of the Prometheus targets page.
- The `HighErrorRate` and `HighLatency` alerts only fire on *observed traffic* — if there's no traffic (because the app is down), the counters don't move, so the alerts never trigger.

---

## Follow-up Actions

| Action | Priority | Owner | Status |
|--------|----------|-------|--------|
| Add `AppDown` alert (`up{job="sre-lab-app"} == 0`) to `prometheus/config/alerts.yml` | High | Alvin | DONE |
| Enable Prometheus lifecycle API (`--web.enable-lifecycle`) for hot reloads | High | Alvin | DONE |
| Test the new alert rule by repeating Experiment 1 | High | Alvin | DONE — Slack notification confirmed |
| Consider adding a synthetic health check (e.g., Blackbox Exporter hitting `/health`) | Medium | Alvin | Open |

### Validation Notes
- First attempt failed: alert expression used `job="flask-app"` but actual job name in `prometheus.yml` is `sre-lab-app`. Label mismatches cause alerts to silently never fire.
- After fixing the label and reloading Prometheus, `AppDown` moved Inactive → Pending → Firing within ~30 seconds of stopping the container.
- Slack notification received in `#all-toks`.
- Alert auto-resolved when container was started again.
