# Phase 6 — Distributed Tracing (Concepts)

## Why This Matters (for SREs)

**Metrics tell you _when_ something broke. Logs tell you _what_ broke. Traces tell you _where_ it's slow.**

In a monolith, a slow request is easy to debug — you just look at the code. But in a distributed system (microservices, multiple database queries, external API calls), a request bounces through multiple services, each adding latency. A slow request might be due to:
- A database query that started at 5ms but took 3 seconds
- An external API call that hung
- Waiting for a response from another service
- All of the above, happening in sequence vs. parallel

Distributed tracing answers: *"This request took 6 seconds. Show me a timeline of every operation that happened and where the time went."* That's the SRE superpower — you don't have to guess, you just look at the waterfall.

**Portfolio angle:** Demonstrates maturity in production observability. Most engineers can cobble together metrics + logs; distributed tracing shows you understand the full request lifecycle and can debug complex systems at scale.

---

This doc covers the mental models for distributed tracing in the `sre-lab` stack.
Read top-to-bottom: concepts → where Tempo fits → what happens inside the Flask app → a practical Grafana walkthrough.

---

## 6.1 — Concepts: Trace, Spans, and trace_id

A **trace** is the full story of one request as it travels through your system.
A **span** is one unit of work inside that trace (one function, one query, one API call).
Every span in the same trace shares the same **trace_id** — that's the glue.

```
                        ┌───────────────────────────────┐
                        │           TRACE               │
                        │   trace_id: abc-123-def       │
                        │  (the whole request)          │
                        └──────────────┬────────────────┘
                                       │
                       ────────────────┼────────────────
                       │               │               │
                       ▼               ▼               ▼
              ┌────────────────┐ ┌──────────┐ ┌──────────────┐
              │     SPAN 1     │ │  SPAN 2  │ │    SPAN 3    │
              │ handle_request │ │ query_db │ │ call_payment │
              │   (parent)     │ │  (child) │ │    (child)   │
              └────────────────┘ └──────────┘ └──────────────┘
              all 3 spans carry trace_id = abc-123-def
```

### Waterfall view (what you see in Grafana → Tempo)

Time flows left to right. Each bar is a span. Indentation = parent/child.

```
  Time (ms)  0────10────20────30────40────50────60────70────80────90────100
             │                                                            │
  Span 1     ████████████████████████████████████████████████████████████  100ms
  handle_request  (parent — runs for the whole request)
             │                                                            │
  Span 2         ████████████████████                                      40ms
  └─ query_db    (10ms → 50ms)
             │                                                            │
  Span 3                              █████████████████████             45ms
     └─ call_payment_api              (50ms → 95ms)
             │                                                            │
             └─ All three spans share trace_id: abc-123-def ─────────────┘
```

**Read it like this:**
- `handle_request` started at 0ms, ended at 100ms (total request time).
- `query_db` ran from 10ms to 50ms — that's 40ms blocking the request.
- `call_payment_api` ran from 50ms to 95ms — fired right after the DB returned.
- You can immediately see *where the time went*. That's the whole point.

---

## 6.2 — Tempo in the Observability Stack

Tempo is the **traces** backend. It sits next to Prometheus (metrics) and Loki (logs).
All three feed into one Grafana, which is where you actually look at things.

```
                          ┌──────────────────────┐
                          │     FLASK APP        │
                          │  (instrumented with  │
                          │    OpenTelemetry)    │
                          └──────────┬───────────┘
                                     │
            ─────────────────────────┼────────────────────────
            │                        │                        │
       (metrics)                  (logs)                  (traces)
       /metrics endpoint        stdout JSON           OTLP gRPC :4317
            │                        │                        │
            ▼                        ▼                        ▼
    ┌───────────────┐         ┌─────────────┐         ┌──────────────┐
    │  PROMETHEUS   │         │  PROMTAIL   │         │    TEMPO     │
    │  (scrapes)    │         │  (tails &   │         │  (receives & │
    │               │         │   ships)    │         │    stores)   │
    └───────┬───────┘         └──────┬──────┘         └──────┬───────┘
            │                        │                        │
            │                        ▼                        │
            │                 ┌─────────────┐                 │
            │                 │    LOKI     │                 │
            │                 │ (log store) │                 │
            │                 └──────┬──────┘                 │
            │                        │                        │
            └────────────┬───────────┴────────────┬───────────┘
                         │                        │
                         ▼                        ▼
                  ┌──────────────────────────────────┐
                  │            GRAFANA               │
                  │  ┌────────┐ ┌──────┐ ┌────────┐  │
                  │  │Metrics │ │ Logs │ │Traces  │  │
                  │  │ panels │ │panels│ │ panels │  │
                  │  └────────┘ └──────┘ └────────┘  │
                  │  One pane of glass for all three  │
                  └──────────────────────────────────┘
```

### The three pillars, side by side

| Pillar  | What it answers     | Source       | Pipeline                  | Backend    |
| ------- | ------------------- | ------------ | ------------------------- | ---------- |
| Metrics | "Is it broken?"     | `/metrics`   | Prometheus scrapes        | Prometheus |
| Logs    | "What happened?"    | stdout JSON  | Promtail tails → ships    | Loki       |
| Traces  | "Where is it slow?" | OTel SDK     | App pushes via OTLP:4317  | Tempo      |

All three converge in Grafana. The magic moment is when you click a `trace_id`
in a log line and jump straight to the waterfall view in Tempo. That's why we
inject `trace_id` into logs — see 6.3.

---

## 6.3 — OpenTelemetry Instrumentation (Inside the Flask App)

This is what happens *inside* the Flask process when a request comes in.
The OTel SDK does most of the heavy lifting via **auto-instrumentation**.

```
                  ┌───────────────────────────────────────────┐
                  │  Incoming HTTP request                    │
                  │  GET /api/data                            │
                  └────────────────────┬──────────────────────┘
                                       │
                                       ▼
            ┌──────────────────────────────────────────────────┐
            │  ① OTel auto-instrumentation intercepts          │
            │     (opentelemetry-instrumentation-flask)        │
            │     Wraps the WSGI handler — no code changes     │
            └────────────────────┬─────────────────────────────┘
                                 │
                                 ▼
            ┌──────────────────────────────────────────────────┐
            │  ② A new SPAN is created                         │
            │     name:     "GET /api/data"                    │
            │     start_ts: 2026-05-13T08:00:00.000Z           │
            │     attrs:    http.method, http.route, ...       │
            └────────────────────┬─────────────────────────────┘
                                 │
                                 ▼
            ┌──────────────────────────────────────────────────┐
            │  ③ A trace_id is assigned to the span            │
            │     trace_id: abc-123-def-456                    │
            │     span_id:  9f8e7d6c                           │
            │     (child spans inherit this trace_id)          │
            └────────────────────┬─────────────────────────────┘
                                 │
                ─────────────────┴───────────────
                │                                │
                ▼                                ▼
   ┌────────────────────────┐    ┌──────────────────────────────┐
   │  ④a trace_id injected  │    │  ④b Span exported via OTLP   │
   │      into JSON log     │    │      gRPC → tempo:4317       │
   │                        │    │                              │
   │  {                     │    │   ┌──────────────────────┐   │
   │   "msg": "request",    │    │   │   TEMPO              │   │
   │   "trace_id":          │    │   │  (stores span,       │   │
   │     "abc-123-def-456", │    │   │   builds waterfall   │   │
   │   "span_id": "9f8e7d6c"│    │   │   on query)          │   │
   │   "level": "INFO"      │    │   └──────────────────────┘   │
   │  }                     │    │                              │
   │        │               │    └──────────────────────────────┘
   │        ▼               │
   │   stdout → Promtail    │
   │   → Loki               │
   └────────────────────────┘

                ▼ later, in Grafana ▼

   You see a log line in Loki with trace_id=abc-123-def-456.
   You click it. Grafana queries Tempo for that trace_id.
   The full waterfall appears. You see exactly where
   the request spent its time. That's the payoff.
```

### Why inject `trace_id` into logs?

Without it, your logs and traces live in two separate worlds:
- Loki: "something logged at 08:00:00"
- Tempo: "some span happened at 08:00:00"

With `trace_id` in every log line, Grafana wires the two together automatically.
One click on a log → full distributed trace. That's the SRE superpower.

### What "auto-instrumentation" actually does

You install `opentelemetry-instrumentation-flask` and it wraps Flask's WSGI handler.
Every request is now automatically wrapped in a span — no code changes required.

You only write code when you want **custom spans** for business logic:

```python
from opentelemetry import trace
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("artificial_delay"):
    time.sleep(6)  # this becomes a child span showing exactly where 6s went
```

---

## 6.4 — Correlating Logs ↔ Traces in Grafana (Derived Fields)

You injected `trace_id` into every JSON log line in 6.3. That's the *data*.
A **derived field** is the *UI* that turns that data into a clickable link.

```
                     ┌─────────────────────────────────────┐
                     │   LOG LINE IN LOKI (raw JSON)       │
                     │  { ...                              │
                     │    "trace_id":                      │
                     │      "944f6d9c30d5...",  ◄── value  │
                     │    ...                              │
                     │  }                                  │
                     └────────────────┬────────────────────┘
                                      │
                                      ▼
                ┌──────────────────────────────────────────┐
                │  GRAFANA LOKI DATASOURCE                 │
                │  jsonData.derivedFields:                 │
                │    matcherRegex: "trace_id":"([a-f0-9]+) │
                │    datasourceUid: tempo                  │
                │    url: ${__value.raw}                   │
                │  → captures the hex string               │
                │  → renders a "TraceID" button            │
                └────────────────┬─────────────────────────┘
                                 │
                                 ▼
                ┌──────────────────────────────────────────┐
                │  GRAFANA LOG DETAILS PANEL               │
                │                                          │
                │   Links                                  │
                │   ─────                                  │
                │   TraceID  [ Tempo ] ◄── click           │
                │                                          │
                └────────────────┬─────────────────────────┘
                                 │
                                 ▼
                ┌──────────────────────────────────────────┐
                │  TEMPO QUERY                             │
                │  GET /api/traces/944f6d9c30d5...         │
                │  → full waterfall renders in right pane  │
                └──────────────────────────────────────────┘
```

### What the regex does

```
matcherRegex:  "trace_id":\s*"([a-f0-9]{32})"
                              ▲       ▲
                              │       └── 32 hex chars (OTel trace ID format)
                              └────────── capture group → ${__value.raw}
```

Grafana scans every log line. When the regex matches, it captures the trace ID
and renders it as a clickable button next to the field. Clicking the button
issues a Tempo query for that exact trace ID — and Grafana renders the waterfall
in the right split pane without ever leaving Explore.

### Provisioning gotcha

Grafana caches provisioned datasources in `grafana_data`. If you change
`derivedFields` in the YAML but the datasource already exists in the DB,
a `docker compose restart grafana` is enough to re-apply it — but the API
must be queried with valid admin credentials to verify, otherwise the
auth-failure response looks like an empty `jsonData` and you'll chase a
ghost. Always confirm with:

```bash
curl -s -u admin:$GF_ADMIN_PASSWORD \
  http://localhost:3000/api/datasources/uid/loki | jq .jsonData
```

---

## 6.5 — Practical Walkthrough: Reading a Waterfall in Grafana

Here's what you *actually* do as an SRE when you get paged about a slow request:

### Step 1: Find a log entry with the error or latency spike
```
Grafana Explore → Loki → {container="/sre-lab-app"} | json
↓
See a log line with status=500 or duration=high
Example: {"timestamp":"2026-06-07T09:05:22Z","trace_id":"944f6d9c30d5...","level":"ERROR"}
```

### Step 2: Click the trace_id link
```
In the log details, look for the trace_id field.
You'll see a "Tempo" button next to it.
Click it.
```

### Step 3: Grafana queries Tempo and shows the waterfall
```
Waterfall view loads in a split pane (right side of screen)

  Time (ms)   0──────10────20────30────40────50────60
  ┌─────────────────────────────────────────────────┐
  │ GET /api/slow (parent span)              6100ms │  ◄─ total request time
  │   └─ artificial_delay (child span)       6000ms │  ◄─ the sleep
  │   └─ [100ms unaccounted for]                    │  ◄─ overhead/other work
  └─────────────────────────────────────────────────┘

  Or for an error case:
  ┌─────────────────────────────────────────────────┐
  │ GET /api/error (parent span, RED)         150ms │  ◄─ marked as error
  │   └─ [event] Exception: Simulated failure      │  ◄─ exception details
  │   └─ [exception traceback]                     │
  └─────────────────────────────────────────────────┘
```

### Step 4: Diagnose
- **If time is in one child span** → that's your bottleneck (slow query, slow API call, etc.)
- **If time is spread across many spans** → contention or sequential operations that should be parallel
- **If spans are red** → failed dependencies, retries, or error propagation
- **If a span has unexpected gaps** → GC pauses, lock contention, or external waits

### Real example: Why did this request take 6 seconds?
```
Log shows: duration=6123, trace_id=abc123
Click trace_id.
Waterfall shows:
  GET /api/slow (6123ms total)
    └─ artificial_delay (6000ms child span)
       └─ time.sleep(6)  ◄─ THERE IT IS. The 6 seconds are in the sleep.

You've narrowed it down in 3 clicks instead of reading code or running a profiler.
That's the superpower.
```

---

## TL;DR cheat sheet

```
Trace      = the whole request (one trace_id)
Span       = one unit of work inside a trace
trace_id   = the glue connecting spans + logs

Metrics → Prometheus → Grafana          (is it broken?)
Logs    → Promtail → Loki → Grafana     (what happened?)
Traces  → OTLP:4317 → Tempo → Grafana   (where is it slow?)

OTel auto-instrumentation = spans for free, no code changes
Inject trace_id into logs = jump from log line to full waterfall
```
