# Phase 1 — Observability (Concepts)

The mental model for **metrics-based monitoring**: how a number gets from
inside your Flask app to a panel in Grafana to a Slack alert in `#all-toks`.

Read top-to-bottom: metrics → scrape pipeline → four golden signals → alerts.

---

## 1.1 — What is a metric?

A **metric** is a numeric measurement of something happening in your app,
sampled at a point in time.

```
                   ┌──────────────────────────────────────┐
                   │           APP (Flask)                │
                   │                                      │
                   │   request comes in → counter++       │
                   │   request completes → histogram obs  │
                   │   error returned    → error_count++  │
                   │                                      │
                   │   These live in MEMORY inside the    │
                   │   prometheus_client Python library.  │
                   └──────────────┬───────────────────────┘
                                  │
                                  │  GET /metrics
                                  ▼
                   ┌──────────────────────────────────────┐
                   │  /metrics endpoint (plain text)      │
                   │                                      │
                   │  app_requests_total{                 │
                   │    method="GET",                     │
                   │    endpoint="/api/data"              │
                   │  } 1247                              │
                   │                                      │
                   │  app_request_duration_seconds_bucket │
                   │    {le="0.1"} 1100                   │
                   │    {le="0.5"} 1200                   │
                   │    {le="1.0"} 1247                   │
                   └──────────────────────────────────────┘
```

### The three metric types you actually use

| Type      | What it does                                | Example                       |
| --------- | ------------------------------------------- | ----------------------------- |
| Counter   | Goes up only (never resets, never down)     | `app_requests_total`          |
| Histogram | Buckets of "how long did X take"            | `app_request_duration_seconds`|
| Gauge     | A value that can go up or down              | `temperature`, `queue_depth`  |

**Counters give you rates** (via `rate()`). **Histograms give you percentiles**
(via `histogram_quantile()`). That's 90% of all SRE PromQL right there.

---

## 1.2 — The Scrape Pipeline

Prometheus is a **pull-based** system. It doesn't wait for your app to send
data — it scrapes the `/metrics` endpoint on a schedule.

```
                  ┌───────────────────────────────┐
                  │      PROMETHEUS               │
                  │  (config: scrape every 15s)   │
                  └───────────────┬───────────────┘
                                  │
                                  │  every 15s:
                                  │  GET http://app:5001/metrics
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │       FLASK APP               │
                  │  returns current counter      │
                  │  values as plain text         │
                  └───────────────┬───────────────┘
                                  │
                                  │  response body
                                  ▼
                  ┌───────────────────────────────┐
                  │     PROMETHEUS TSDB           │
                  │  (time-series DB on disk)     │
                  │                               │
                  │  metric_name{labels}  value   │
                  │  @ timestamp                  │
                  │                               │
                  │  Stored forever (until        │
                  │  retention policy kicks in).  │
                  └───────────────┬───────────────┘
                                  │
                                  │  PromQL query
                                  ▼
                  ┌───────────────────────────────┐
                  │         GRAFANA               │
                  │  draws lines on dashboards    │
                  └───────────────────────────────┘
```

### Why pull (and not push)?

- **Targets can come and go** — Prometheus discovers them, the app doesn't
  need to know where Prometheus lives.
- **Health check for free** — if the scrape fails, Prometheus knows the
  target is down (this is what `up == 0` powers — see the `AppDown` alert).
- **Rate limiting is the scraper's choice**, not the app's.

---

## 1.3 — The Four Golden Signals

Google's SRE book says you only need four metrics to know if a service is healthy.
This dashboard panel-by-panel maps to them:

```
                ┌─────────────────────────────────────────┐
                │       FOUR GOLDEN SIGNALS               │
                │  (the only dashboard you really need)   │
                └─────────────────────────────────────────┘

  ┌────────────────────────┐    ┌────────────────────────┐
  │  ① TRAFFIC             │    │  ② ERRORS              │
  │                        │    │                        │
  │  rate(requests_total)  │    │  rate(errors_total) /  │
  │                        │    │  rate(requests_total)  │
  │  "Is anyone using us?" │    │                        │
  │                        │    │  "Are we breaking?"    │
  └────────────────────────┘    └────────────────────────┘

  ┌────────────────────────┐    ┌────────────────────────┐
  │  ③ LATENCY             │    │  ④ SATURATION          │
  │                        │    │                        │
  │  histogram_quantile(   │    │  CPU%, memory%,        │
  │    0.95,               │    │  queue_depth           │
  │    rate(bucket[5m])    │    │                        │
  │  )                     │    │  "How close to full?"  │
  │                        │    │                        │
  │  "Are we slow?"        │    │                        │
  └────────────────────────┘    └────────────────────────┘
```

In this lab the dashboard shows Traffic, Error Rate, Latency p95, Latency p50.
Saturation belongs to Phase 7 (Kubernetes — CPU/memory limits + HPA signals).

### Why p95 and not average?

Averages **lie**. If 99 requests take 10ms and 1 takes 10s, the average is
~110ms — looks fine. But that one 10s request is a user staring at a spinner.
**p95 = "95% of requests were faster than this number"** — it catches the
tail. p99 catches the worst tail. Average catches nothing useful.

---

## 1.4 — Alerts & AlertManager Routing

Metrics + thresholds = alerts. Alerts + routing = Slack ping.

```
            ┌──────────────────────────────────────────┐
            │              PROMETHEUS                  │
            │                                          │
            │  Evaluates alert rules every 15s:        │
            │                                          │
            │    HighErrorRate                         │
            │      expr: rate(errors[5m]) > 0.7        │
            │      for: 1m                             │
            │      → fires after 1m sustained          │
            │                                          │
            │    AppDown                               │
            │      expr: up{job="sre-lab-app"} == 0    │
            │      for: 30s                            │
            │                                          │
            │  When firing → POST to AlertManager      │
            └──────────────┬───────────────────────────┘
                           │
                           ▼
            ┌──────────────────────────────────────────┐
            │            ALERTMANAGER                  │
            │                                          │
            │  Job: don't spam Slack.                  │
            │   • group similar alerts together        │
            │   • dedupe repeats                       │
            │   • route by labels (severity, team)     │
            │   • silence during maintenance           │
            │                                          │
            │  Routes:                                 │
            │   severity=page → #all-toks (Slack)      │
            │   severity=info → email digest           │
            └──────────────┬───────────────────────────┘
                           │
                           │  webhook POST
                           ▼
            ┌──────────────────────────────────────────┐
            │              SLACK                       │
            │  🚨 [FIRING] HighErrorRate              │
            │     endpoint=/api/error  rate=0.85       │
            └──────────────────────────────────────────┘
```

### The `for:` clause matters

`for: 1m` means "the condition has to be true for a full minute before this
fires." Without it, a single 1-second blip would page you at 3am. With it,
transient noise is filtered out and only sustained problems escape.

**Rule of thumb:**
- Critical alert (page): `for: 1–5m`
- Warning alert (ticket): `for: 15–60m`

### Why this exists (vs. just `if error: page()`)

Without AlertManager, every Prometheus instance would spam Slack directly
and every alert would be a separate message. AlertManager is the
**deduplication and routing layer** — same way a load balancer sits in
front of your app, AlertManager sits in front of your humans.

---

## 1.5 — Putting it all together

```
   ┌─────────┐    ┌────────────┐    ┌──────────┐
   │ FLASK   │───▶│ PROMETHEUS │───▶│ GRAFANA  │  ← dashboards
   │ /metrics│    │  (scrape + │    └──────────┘
   └─────────┘    │   store +  │
                  │   alert)   │───▶┌──────────┐    ┌────────┐
                  └────────────┘    │ALERTMGR  │───▶│ SLACK  │
                                    │(route)   │    │#all-toks│
                                    └──────────┘    └────────┘
```

This is the **metrics pillar**. Logs (Phase 4) and traces (Phase 6) plug into
Grafana the same way — different backends, same "one pane of glass" idea.

---

## TL;DR cheat sheet

```
Metric     = a number, sampled over time
Counter    = goes up only (use rate() to see "per second")
Histogram  = buckets for latency (use histogram_quantile() for p95)
Scrape     = Prometheus pulls /metrics every 15s

Four Golden Signals:
  Traffic     — rate(requests_total)
  Errors      — rate(errors_total) / rate(requests_total)
  Latency     — histogram_quantile(0.95, ...)
  Saturation  — CPU/mem/queue depth

Alert rule  = PromQL expr + threshold + for: duration
AlertManager = dedupe + route + silence → Slack
```
