# Postmortem — Phase 4.5: Error Flood Investigation with Loki

**Date:** 2026-05-10
**Experiment:** Re-run error flood from Phase 2, investigated with LogQL
**Severity:** Simulated P2 (high error rate, no data loss)

---

## What happened

Flooded `/api/error` at ~2 req/s for ~5 minutes using a PowerShell loop.
Error rate climbed to ~0.9 req/s as seen in the "Error Rate per Second" Grafana panel.

---

## Detection

| Signal | What it showed |
|--------|---------------|
| Prometheus (`app_errors_total`) | Error rate spike to ~0.9 req/s — visible in Grafana Error Rate panel |
| Loki logs | 142 ERROR entries with `endpoint=/api/error`, `status=500` |

**LogQL query used to isolate errors:**
```
{container="/sre-lab-app"} | json | levelname = `ERROR`
```

---

## Root cause

Intentional — `/api/error` endpoint always returns HTTP 500 with `{"status": "error", "message": "Simulated failure"}`.

---

## What logs revealed vs metrics alone

- **Metrics** showed the shape: error rate rising, plateau, then drop
- **Logs** showed the detail: every entry confirmed `endpoint=/api/error` and `status=500` — no ambiguity about which endpoint was failing
- The Loki volume bar chart mirrored the Prometheus spike exactly, confirming both signals tracked the same event

---

## Gap discovered

`/api/error` does **not** increment `app_requests_total` or record `app_request_duration_seconds`.
During the flood, Traffic and Latency p95 panels were flat — the error flood was invisible to those signals.

**Fix needed:** All endpoints should record request count and duration, even error paths.

---

## Lessons learned

1. Metrics give you the alarm; logs give you the evidence — you need both to investigate an incident
2. Correlating the Grafana time range across Prometheus panels and the Loki Explore view pins down exactly when the incident started and ended
3. Incomplete instrumentation (error endpoints not tracked in request metrics) creates blind spots in dashboards
