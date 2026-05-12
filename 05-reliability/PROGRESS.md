# Phase 5 — Reliability: SLOs & Error Budgets

## Goal
Define measurable reliability targets for the Flask app, track error budget consumption,
and alert when budget is burning faster than the 30-day window allows.

## Sub-phases

| # | Sub-phase | Status |
|---|-----------|--------|
| 5.1 | Define SLOs | **COMPLETE** — 99% availability, p95 latency < 300ms |
| 5.2 | Prometheus recording rules | **COMPLETE** |
| 5.3 | Error budget Grafana dashboard | **COMPLETE** |
| 5.4 | Burn rate alerts | **COMPLETE** — validated firing at 61.5x burn rate |

---

## What was built

### SLOs defined
| SLO | Target | Window |
|-----|--------|--------|
| Availability | ≥ 99% of requests succeed | 30 days |
| Latency | p95 < 300ms | 30 days |

### Recording rules (`01-observability/prometheus/config/slo-rules.yml`)
| Metric | Description |
|--------|-------------|
| `slo:availability:rate5m` | Success rate over 5m window |
| `slo:availability:rate1h` | Success rate over 1h window (used for burn rate) |
| `slo:latency_p95:rate5m` | p95 latency over 5m window |
| `slo:error_budget_remaining:rate1h` | Fraction of error budget remaining |

### Grafana dashboard (`01-observability/grafana/dashboards/slo-dashboard.json`)
- Availability SLI gauge (red < 95%, yellow < 99%, green ≥ 99%)
- Error budget remaining gauge (red < 10%, yellow < 25%, green ≥ 25%)
- SLO target stat (99%)
- Latency p95 stat (red ≥ 500ms, yellow ≥ 300ms, green < 300ms)
- Availability over time vs SLO target line
- Latency p95 over time vs SLO target line

### Burn rate alerts (`01-observability/prometheus/config/alerts.yml`)
| Alert | Condition | Severity | Meaning |
|-------|-----------|----------|---------|
| `SloBudgetFastBurn` | burn rate > 14.4x for 2m | critical | Budget exhausted in < 2 days — page now |
| `SloBudgetSlowBurn` | burn rate > 1x for 15m | warning | Budget draining steadily — open a ticket |

---

## Key concepts learned

- **SLI** = the measurement (e.g. success rate = 0.97)
- **SLO** = the target (e.g. success rate ≥ 0.99)
- **Error budget** = allowed failure room (1% of requests can fail)
- **Burn rate** = how fast budget is being consumed vs the allowed rate
  - 1x = exactly on track to exhaust in 30 days
  - 14.4x = budget exhausted in 2 days → page immediately
- Recording rules pre-compute expensive PromQL so dashboards stay fast
- `rate()` needs ≥ 2 Prometheus scrapes — NaN = not enough history, not a bug

---

## Experiment: Error budget burn validation

Sent equal success + error traffic (50/50 split) to the Flask app.

Results:
- `slo:availability:rate5m` = 0.5 (50% success — SLO breached)
- Burn rate = 61.5x → `SloBudgetFastBurn` fired after 2m (FIRING confirmed)
- `SloBudgetSlowBurn` entered PENDING (fires after 15m sustained)
- Error budget gauge showed 0% remaining

**Conclusion:** Burn rate alerting catches budget exhaustion before the full window elapses,
giving the on-call engineer time to act before the SLO is permanently breached.
