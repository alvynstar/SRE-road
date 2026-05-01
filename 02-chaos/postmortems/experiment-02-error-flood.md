# Postmortem — Experiment 02: Error Rate Flood

**Date:** 2026-04-29  
**Experiment:** Flooded `/api/error` at 2 req/s for 120 seconds to trigger the `HighErrorRate` alert.

---

## What We Broke
Ran `scripts/generate_errors.sh` which hit `/api/error` continuously, pushing `rate(app_errors_total[1m])` above the 0.7 req/s threshold.

---

## Timeline

| Time   | Event |
|--------|-------|
| 19:52  | `generate_errors.sh` started — flooding `/api/error` at 2 req/s |
| ~19:53 | Alert moved to **Pending** state in Prometheus (rate crossed 0.7 req/s) |
| 19:56  | Alert moved to **Firing** state (sustained for 1m+) |
| 19:56  | Slack notification received in `#all-toks` |
| 19:54  | Script ended naturally (240 requests / 120s after 19:52 start) |
| ~19:57 | Alert moved to **Resolved** in Prometheus |
| ~19:57 | Slack resolved notification received |

---

## Detection
- [x] Alert fired automatically in Prometheus (Inactive → Pending → Firing) — fired ~4 minutes after flood started
- [x] Slack notification received without manual intervention
- [ ] Grafana error rate panel showed spike — _verify and check_
- [x] Slack resolved notification received after traffic stopped

---

## Root Cause
The `/api/error` endpoint was hit repeatedly. Each request increments `app_errors_total`. The 1-minute rate exceeded 0.7 req/s, which is the `HighErrorRate` alert threshold.

---

## Impact (if this were production)
- Users hitting the affected endpoint would receive 500 errors
- At 2 req/s error rate, roughly 120 failed requests occurred during this experiment
- If this were a real deployment issue, users would see consistent failures

---

## MTTR
| Phase | Duration |
|-------|----------|
| Time from flood start to alert firing | ~4 minutes (19:52 → 19:56) |
| Time from alert to Slack notification | <30 seconds (effectively immediate) |
| Time from traffic stop to alert resolved | ~3 minutes (19:54 → ~19:57) |

> Note: 4 minutes is longer than the alert's `for: 1m` window. The flood itself is at 2 req/s, well above the 0.7 threshold — but the `rate()` function needs ~1 minute of samples to compute, and the alert needs another 1 minute of sustained breach before firing. So the floor is roughly 2 minutes with default `evaluation_interval: 15s`. If we ever needed faster detection, we'd shorten the `for:` window or use a shorter rate window (e.g., `[30s]`).

---

## Runbook Validation
<!-- Walk through HighErrorRate.md during the experiment and check each step -->

| Step | Works as documented? | Notes |
|------|---------------------|-------|
| `curl http://localhost:5001/health` | YES / NO | |
| `docker logs sre-lab-app --tail=100` | YES / NO | |
| `docker stats` | YES / NO | |
| Grafana error rate panel visible | YES / NO | |
| PromQL query returned useful data | YES / NO | |

---

## What Worked
- Alert progression worked end-to-end: Inactive → Pending → Firing in Prometheus
- Slack notification arrived in `#all-toks` essentially immediately after the alert fired
- Manual `curl` confirmed `/api/error` returns HTTP 500 with the expected JSON body
- The chaos script reliably hit 2 req/s for the full duration (after fixing the `bc` dependency)

## Gaps Found
- **Chaos script depended on `bc` which is not installed in Git Bash.** The script silently completed only 1 request instead of 240. Fixed by replacing `echo "$DURATION / $INTERVAL" | bc` with native bash arithmetic: `COUNT=$((DURATION * RATE))`.
- **SRE lesson:** scripts with external dependencies should either declare them up front or stick to portable shell builtins. Running with `bash -x` (trace mode) made the bug obvious.

---

## Follow-up Actions

| Action | Priority | Owner | Status |
|--------|----------|-------|--------|
| Fixed chaos script `bc` dependency — now uses bash builtin arithmetic | High | Alvin | DONE |
| Confirm Slack receives the **resolved** notification after script ends | Medium | Alvin | DONE |
| Verify Grafana error rate panel shows the spike for the documented window | Medium | Alvin | Open |
| Consider shortening `for: 1m` to `for: 30s` if faster detection is required for real incidents | Low | Alvin | Open |
