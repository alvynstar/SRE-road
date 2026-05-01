# Postmortem — Experiment 03: Latency Spike

**Date:** <!-- Fill in when you run this -->  
**Experiment:** Continuously hit `/api/slow` (6s response time) to push p95 latency above the 5s alert threshold.

---

## What We Broke
Ran `scripts/generate_latency.sh` which fired concurrent requests to `/api/slow`. Each request sleeps 6 seconds before responding, pushing `histogram_quantile(0.95, ...)` above 5s.

---

## Timeline

| Time | Event |
|------|-------|
| T+0:00 | `generate_latency.sh` started |
| T+0:__ | Grafana Latency p95 panel began climbing |
| T+0:__ | Alert moved to **Pending** state (p95 crossed 5s) |
| T+0:__ | Alert moved to **Firing** state (2 minutes sustained) |
| T+0:__ | Slack notification received in #all-toks |
| T+0:__ | Script stopped (Ctrl+C) |
| T+0:__ | Alert moved to **Resolved** |

---

## Detection
- [ ] Alert fired automatically in Prometheus (Pending → Firing)
- [ ] Slack notification received
- [ ] Grafana p95 panel showed spike clearly
- [ ] p50 stayed low (confirming this was not affecting all requests)

---

## Root Cause
The `/api/slow` endpoint introduces a 6-second artificial delay. With concurrent requests in flight, the 95th percentile of `app_request_duration_seconds` exceeded 5 seconds. The `HighLatency` alert fires after this condition is sustained for 2 minutes.

---

## Impact (if this were production)
- 5% of users (p95) would experience 6+ second response times
- If this were a real slow dependency (database, third-party API), users would see timeouts
- Latency often precedes errors — if the downstream is slow enough, requests time out and return 500s

---

## MTTR
| Phase | Duration |
|-------|----------|
| Time from load start to p95 crossing 5s | __ minutes |
| Time from p95 crossing to alert firing | 2 minutes (by design — `for: 2m`) |
| Time from alert to Slack notification | __ seconds |
| Time from traffic stop to p95 dropping below threshold | __ minutes |

---

## Runbook Validation
<!-- Walk through HighLatency.md during the experiment and check each step -->

| Step | Works as documented? | Notes |
|------|---------------------|-------|
| `curl -w "\nTime: %{time_total}s\n" http://localhost:5001/health` | YES / NO | |
| PromQL p95 vs p50 comparison query | YES / NO | |
| `docker stats` showing resource pressure | YES / NO | |
| Grafana p95 vs p50 panels side-by-side | YES / NO | |

---

## Key Observation
<!-- Important: note whether p50 stayed low while p95 spiked -->
- p95 latency: __ seconds at peak
- p50 latency: __ seconds at peak
- Interpretation: if p50 stayed low, the problem was isolated to the slow endpoint (not systemic)

---

## What Worked
<!-- Fill in after running -->
- 
- 

## Gaps Found
<!-- Fill in any surprises -->
- 

---

## Follow-up Actions

| Action | Priority | Owner |
|--------|----------|-------|
| <!-- e.g., reduce `for: 2m` to `for: 1m` if 2 min felt too slow --> | | |
| <!-- e.g., add per-endpoint latency alert to isolate which endpoint is slow --> | | |
