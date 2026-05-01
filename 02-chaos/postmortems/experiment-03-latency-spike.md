# Postmortem — Experiment 03: Latency Spike

**Date:** 2026-04-29  
**Experiment:** Continuously hit `/api/slow` (6s response time) to push p95 latency above the 5s alert threshold.

---

## What We Broke
Ran `scripts/generate_latency.sh` which fired concurrent requests to `/api/slow`. Each request sleeps 6 seconds before responding, pushing `histogram_quantile(0.95, ...)` above 5s.

---

## Timeline

| Time   | Event |
|--------|-------|
| 16:43  | `generate_latency.sh` started — hitting `/api/slow` once per second (each takes ~6s) |
| ~16:44 | Grafana p95 panel climbed above 5s as concurrent slow requests accumulated |
| ~16:44 | Alert moved to **Pending** state (p95 crossed 5s threshold) |
| 16:45  | Alert moved to **Firing** state (sustained for 2m — `for: 2m`) |
| 16:45  | Slack notification received in `#all-toks` |
| ~16:46 | Script stopped (Ctrl+C) |
| ~16:48 | Alert moved to **Resolved** in Prometheus and Slack |

---

## Detection
- [x] Alert fired automatically in Prometheus (Pending → Firing) — fired ~2 minutes after p95 crossed threshold
- [x] Slack notification received in `#all-toks`
- [x] Grafana p95 panel showed spike clearly (climbed to ~7.5s)
- [ ] **p50 did NOT stay low — it also climbed to ~7.5s** — see Key Observation below

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
| Time from load start to p95 crossing 5s | ~1 minute (16:43 → ~16:44) |
| Time from p95 crossing to alert firing | 2 minutes (by design — `for: 2m`) |
| Time from alert to Slack notification | <30 seconds (effectively immediate) |
| Time from traffic stop to p95 dropping below threshold | ~2 minutes (16:46 → ~16:48) |
| **Total time to fire** | ~2 minutes from script start |

> Note: Total time-to-fire was ~2 minutes — the floor for this alert. The `for: 2m` window dominates the timing because each `/api/slow` request takes 6 seconds, so p95 crosses the threshold almost immediately. In a real incident, a slowly-degrading dependency would take longer to push p95 above 5s.

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

## Key Observation — p95 ≈ p50

| Signal | Peak |
|--------|------|
| p95 latency | ~7.5s |
| p50 latency | ~7.5s |
| Errors | None (panel shows "No data") |

**Why both climbed together:** `/api/slow` is *uniformly* slow — every request takes 6 seconds. So 50% of requests are slow AND 95% of requests are slow. The two percentiles converge.

**What this would look like in a real incident:** A real partial degradation (e.g., a slow database query hitting 1 in 10 requests) would show p95 spiking to 7s while p50 stays at 100ms. That **divergence between p50 and p95** is the textbook signal of partial degradation, and it's what an experienced SRE looks for to distinguish "everything is slow" from "some things are slow."

**Errors panel stayed at "No data":** Confirms that latency and errors are independent signals. The slow endpoint returned HTTP 200 — just slowly. The `HighErrorRate` alert correctly stayed silent throughout.

**Improvement idea for future experiment:** Modify the chaos script (or add a new endpoint) that is slow only on a percentage of requests — e.g., 10% sleep 6s, 90% return immediately. That would produce realistic p95/p50 divergence and make this a more representative drill.

---

## What Worked
- Alert progression worked end-to-end: Inactive → Pending → Firing in Prometheus
- Slack notification arrived in `#all-toks` essentially immediately after firing
- Auto-resolved within ~2 minutes of stopping the chaos script
- Grafana p95 panel clearly showed the spike — visually obvious without needing PromQL
- `HighErrorRate` correctly stayed silent (no errors during a latency-only event)

## Gaps Found / Limitations
- The chaos doesn't reproduce a *realistic* latency anomaly because every request is slow. Real production latency issues usually affect a subset of requests, producing p95/p50 divergence. See "Key Observation" above.
- 2-minute time-to-fire feels long for a chaos drill but is intentional — `for: 2m` exists to suppress flapping. Worth revisiting only if a real production incident shows it's too slow.

---

## Follow-up Actions

| Action | Priority | Owner | Status |
|--------|----------|-------|--------|
| Add a `/api/sometimes-slow` endpoint that fails only ~10% of the time to produce realistic p95/p50 divergence | Medium | Alvin | Open |
| Consider per-endpoint latency alert (`HighLatency` currently treats all endpoints the same) | Low | Alvin | Open |
| Re-test the experiment with realistic partial degradation (after sometimes-slow endpoint exists) | Low | Alvin | Open |
