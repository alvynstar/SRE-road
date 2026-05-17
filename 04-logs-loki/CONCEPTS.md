# Phase 4 — Log Aggregation with Loki (Concepts)

The mental model for the **second pillar of observability**: how a `print`
statement inside Flask becomes a searchable, filterable, queryable log line
inside Grafana — and why that's different from metrics.

Read top-to-bottom: why logs ≠ metrics → the pipeline → structured logging
→ LogQL → log/metric correlation.

---

## 4.1 — Why Logs (and How They're Different from Metrics)

```
   ┌─────────────────────────────────────────────────────────────┐
   │   METRICS answer:  "Is it broken?"  (numbers, aggregates)   │
   │   LOGS answer:     "What happened?" (events, with detail)   │
   └─────────────────────────────────────────────────────────────┘

   Metrics:                          Logs:
   ─────────                          ─────
   error_rate{endpoint="/api/x"}     {timestamp, level:"ERROR",
     = 0.8 req/s                       endpoint:"/api/x",
                                       user_id:"u-123",
   → "Errors are happening."           message:"Payment declined",
                                       stack:"..."}
                                     → "Specifically THIS error
                                        happened to user u-123
                                        at this exact time."
```

You need **both**. Metrics fire the alert. Logs explain it.

### The cost trade-off

```
  STORAGE COST                LOOKUP SPEED
  ────────────                ────────────
  Metrics:  tiny              very fast (indexed numbers)
  Logs:     huge              slow on raw text, fast with labels
```

This is why Loki indexes **labels** (small set of tags) but stores log
**content** as opaque chunks — same model as Prometheus, applied to text.

---

## 4.2 — The Log Pipeline

```
                ┌────────────────────────────────┐
                │      FLASK APP (container)     │
                │                                │
                │  logger.info("request",        │
                │    extra={endpoint:"/api/x",   │
                │           status:200})         │
                │                                │
                │  → writes JSON to stdout       │
                └─────────────┬──────────────────┘
                              │
                              │  stdout
                              ▼
                ┌────────────────────────────────┐
                │   DOCKER LOG DRIVER            │
                │   captures every stdout line   │
                │   as a JSON file on disk       │
                │   (/var/lib/docker/containers) │
                └─────────────┬──────────────────┘
                              │
                              │  Promtail tails the file
                              ▼
                ┌────────────────────────────────┐
                │       PROMTAIL                 │
                │   ─────────────                │
                │   • discovers containers       │
                │     via Docker socket          │
                │   • tails their log files      │
                │   • parses JSON pipeline stage │
                │   • extracts labels:           │
                │       level, endpoint, status  │
                │   • ships to Loki              │
                └─────────────┬──────────────────┘
                              │
                              │  HTTP push
                              ▼
                ┌────────────────────────────────┐
                │         LOKI                   │
                │   ─────────────                │
                │   • indexes labels             │
                │   • compresses log content     │
                │   • stores chunks on disk      │
                │   • answers LogQL queries      │
                └─────────────┬──────────────────┘
                              │
                              │  LogQL via Explore
                              ▼
                ┌────────────────────────────────┐
                │       GRAFANA                  │
                │   Loki datasource              │
                │   panel / Explore view         │
                └────────────────────────────────┘
```

### Why Promtail is a tail-er, not a receiver

Apps don't have to know Loki exists. They just write to **stdout** like
any normal 12-factor app. Promtail does the dirty work of discovering
containers, reading files, parsing formats. If you swap Loki for
something else tomorrow, the app doesn't change at all.

---

## 4.3 — Structured Logging (and why `print()` is not enough)

```
   ┌─────────────────────────────────────────────────────────────┐
   │  UNSTRUCTURED (bad)                                         │
   │  ────────────────                                           │
   │  "2026-05-13 08:00 INFO request to /api/data took 0.1s"     │
   │                                                             │
   │  To filter by endpoint, you have to regex-parse every line. │
   │  Slow, fragile, breaks the day someone reformats the string.│
   └─────────────────────────────────────────────────────────────┘

   ┌─────────────────────────────────────────────────────────────┐
   │  STRUCTURED (good)                                          │
   │  ─────────────────                                          │
   │  {                                                          │
   │    "asctime":  "2026-05-13 08:00:00",                       │
   │    "levelname":"INFO",                                      │
   │    "message":  "request",                                   │
   │    "endpoint": "/api/data",                                 │
   │    "status":   200,                                         │
   │    "duration": 0.105,                                       │
   │    "trace_id": "abc-123-def"   ← from Phase 6               │
   │  }                                                          │
   │                                                             │
   │  Now every field is queryable as a label.                   │
   │  Filter by levelname, group by endpoint, etc.               │
   └─────────────────────────────────────────────────────────────┘
```

The Flask app uses `python-json-logger` so every log line is valid JSON.
Promtail's `json` pipeline stage parses it and promotes specific fields
(level, endpoint, status) to Loki **labels**.

### Labels vs. content

```
   LOG LINE:  {"levelname":"ERROR", "endpoint":"/api/data", "message":"timeout"}

   LOKI STORES:
     ┌─ LABELS (indexed, fast filter) ─┐
     │  levelname = "ERROR"            │
     │  endpoint  = "/api/data"        │  ← these power
     │  container = "/sre-lab-app"     │    LogQL selectors
     └─────────────────────────────────┘

     ┌─ CONTENT (compressed chunk) ────┐
     │  the full JSON line, raw text   │  ← grep'd at query time
     └─────────────────────────────────┘
```

**Rule of thumb:** label things you'd want to **filter** by. Don't label
things with infinite cardinality (user_id, request_id) — that explodes
the index.

---

## 4.4 — LogQL: PromQL's cousin for logs

LogQL has two parts: a **selector** (which streams to read) and an
**optional pipeline** (filter/parse the content).

```
   {container="/sre-lab-app"}  | json  | levelname = "ERROR"
    ─────────────────────────    ────    ──────────────────
            ▲                      ▲              ▲
            │                      │              │
   stream selector              parser     filter expression
   (uses LABELS — fast)        (read JSON  (works on parsed
                                fields)     fields)
```

### Three queries you'll actually use

```
1.  All logs from the app
    {container="/sre-lab-app"}

2.  Just errors
    {container="/sre-lab-app"} | json | levelname = "ERROR"

3.  Error rate as a metric (LogQL → number!)
    sum(rate({container="/sre-lab-app"} |~ "ERROR" [5m]))
```

The third one is the magic: **LogQL can turn logs into metrics on the fly.**
You can graph error count over time directly from log lines, without ever
adding a counter to the app.

---

## 4.5 — Correlation: Metrics + Logs Together

```
   ┌──────────────────────────────────────────────────────────────┐
   │   THE INVESTIGATION FLOW                                     │
   │                                                              │
   │   ┌──────────────┐                                           │
   │   │ ALERT FIRES  │   Prometheus: error rate spike            │
   │   └──────┬───────┘                                           │
   │          │                                                   │
   │          ▼                                                   │
   │   ┌──────────────┐   "Something's wrong, but                 │
   │   │ METRIC PANEL │    what's actually happening?"            │
   │   │ (Grafana)    │                                           │
   │   └──────┬───────┘                                           │
   │          │  switch from metric to log panel                  │
   │          │  (same dashboard, same time range)                │
   │          ▼                                                   │
   │   ┌──────────────┐   {container="/sre-lab-app"} | json       │
   │   │ LOKI LOGS    │     | levelname = "ERROR"                 │
   │   │ (filtered)   │   → 47 error lines for /api/error         │
   │   └──────┬───────┘   → root cause visible in `message`       │
   │          │                                                   │
   │          ▼                                                   │
   │   ┌──────────────┐   Bonus: each log line has trace_id       │
   │   │ DEEP LINK    │   → click → Tempo waterfall (Phase 6)     │
   │   └──────────────┘                                           │
   └──────────────────────────────────────────────────────────────┘
```

### Phase 4.5 lesson (the blind spot)

You discovered that `/api/error` was emitting an error log, but **not
incrementing `request_count`**, so the metric panel under-reported traffic
during the chaos run. The fix was a one-line `request_count.labels(...).inc()`
in the endpoint.

**Generalization:** every endpoint must record three things consistently:
- the request counter
- the duration histogram
- a structured log line

Inconsistency between metric and log creates a dashboard that lies.

---

## TL;DR cheat sheet

```
Metrics answer "is it broken?"     → Prometheus
Logs    answer "what happened?"    → Loki
Both    answer "why?"              → use them together

Pipeline:
   app stdout → Docker driver → Promtail (tail+parse) → Loki → Grafana

Structured JSON > unstructured text  (label fields, don't regex strings)

Labels = indexed, fast filter  (low cardinality only!)
Content = compressed chunks    (full-text searched at query time)

LogQL: {selector} | parser | filter
       can also do sum(rate(... [5m])) → logs-as-metrics
```
