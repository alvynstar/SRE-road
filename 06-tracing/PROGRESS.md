# Phase 6: Distributed Tracing with Tempo & OpenTelemetry — Progress Log

## Goal

Enable end-to-end request tracing so you can see exactly where time is spent in a request — from entry to exit. Answer the question: *"Why did this request take 6 seconds?"*

## Sub-phases

| # | Sub-phase | Status |
|---|-----------|--------|
| 6.1 | Concepts & architecture | **COMPLETE** — trace/span/trace_id mental model documented |
| 6.2 | Infrastructure gaps fixed | **COMPLETE** — startup ordering, persistent storage, explicit env vars |
| 6.3 | End-to-end validation | **COMPLETE** — waterfall view in Grafana, log-to-trace jumps working |

---

## What Was Built

### Infrastructure Fixes (`01-observability/docker-compose.yml`)

| Fix | Purpose | Impact |
|-----|---------|--------|
| `depends_on: tempo` on app service | Guarantee Tempo is ready before app starts | Prevents silent trace loss on startup |
| `OTEL_EXPORTER_OTLP_ENDPOINT` env var | Make trace endpoint visible in config | Enables environment-specific overrides |
| `tempo_data` persistent volume | Preserve traces across restarts | No more trace history loss on shutdown |

### Application Instrumentation (`01-observability/app/app.py`)

| Component | Lines | Purpose |
|-----------|-------|---------|
| OpenTelemetry SDK setup | 16–21 | Configure OTLP/gRPC exporter to Tempo |
| Flask auto-instrumentation | 24 | Wrap all routes with HTTP spans automatically |
| `TraceIdFilter` class | 28–34 | Inject `trace_id` and `span_id` into every JSON log |
| Error span on `/api/error` | 84–90 | Record exceptions and set error status on failed requests |
| Manual span on `/api/slow` | 92–93 | Mark the 6-second artificial delay as a child span |

### Grafana Integration

**Existing (no changes needed):**
- Tempo datasource provisioned at `http://tempo:3200` with `uid: tempo`
- Loki datasource has `derivedFields` configured to extract `trace_id` from log JSON
- Clicking a `trace_id` in a log line jumps to the waterfall view in Tempo

---

## Validation Results

### V1 — Stack Startup ✓

```bash
docker-compose up -d
docker-compose ps
```

**Result:** All services healthy in correct order:
- `sre-lab-tempo` starts first (no dependencies)
- `sre-lab-app` waits for Tempo before starting (new `depends_on: tempo`)
- `sre-lab-prometheus`, `sre-lab-grafana` wait for their dependencies

**Evidence:** New `depends_on` block enforced startup order. OTEL endpoint env var visible in Compose.

---

### V2 — Tempo Receiving Spans ✓

```bash
curl http://localhost:5001/api/data
curl http://localhost:5001/api/slow
curl http://localhost:3200/api/search?limit=5
```

**Result:** Tempo API returns JSON with `traces` array containing multiple entries.

**Output format:**
```json
{
  "traces": [
    {
      "traceID": "abc123def456...",
      "rootServiceName": "sre-lab-app",
      "rootTraceName": "GET /api/slow",
      "startTime": 1718123456000000000,
      "duration": 6123000000
    },
    ...
  ]
}
```

**Evidence:** Traces are arriving at Tempo within 1 second of request completion. Batch span processor working correctly.

---

### V3 — Waterfall View in Grafana ✓

**Steps:**
1. Grafana Explore (compass icon)
2. Datasource: Tempo
3. Service Name: `sre-lab-app`
4. Click any `/api/slow` trace

**Waterfall visible:**
- Outer span: `GET /api/slow` (6.1s total)
  - Inner child span: `artificial_delay` (6.0s, the sleep)
  - Nested under parent with 0.1s overhead

**Evidence:** Auto-instrumentation + manual child span both visible. Span nesting preserved. Duration accounting correct (parent > child sum + overhead).

---

### V4 — Log-to-Trace Jump ✓

**Steps:**
1. Grafana Explore
2. Datasource: Loki
3. Query: `{container="/sre-lab-app"} | json`
4. Expand any log line
5. Look for `trace_id` field

**Result:** 
- Every log line includes `trace_id` field (32-char hex string)
- "Tempo" link button appears next to the trace_id value
- Clicking the button jumps to the waterfall for that exact request
- Waterfall loads in right split pane without page navigation

**Evidence:** `TraceIdFilter` successfully injects trace_id. Derived fields regex matches and creates clickable link. Grafana internal datasource link works correctly.

---

### V5 — Error Traces Show Red Event ✓

**Steps:**
1. `curl http://localhost:5001/api/error`
2. Grafana Explore → Tempo
3. Search traces from `sre-lab-app`
4. Find the `/api/error` trace
5. Click it to view waterfall

**Result:**
- Waterfall shows `simulated_error` span
- Span colored red (error status)
- Event bar shows "Exception" with message: "Simulated failure"
- Stack trace visible in event details

**Evidence:** `span.record_exception(exc)` + `span.set_status(StatusCode.ERROR)` working. Error context propagated to Tempo and rendered in waterfall.

---

## Key Concepts Learned

### Traces, Spans, and trace_id

A **trace** is the complete journey of one request through your system. A **span** is one unit of work (function, API call, database query) inside that trace. All spans in the same trace share the same **trace_id** — that's the glue linking them together.

```
Request: GET /api/slow (trace_id: abc-123)
  │
  ├─ HTTP span: GET /api/slow (parent, 6.1s total)
  │  └─ Manual span: artificial_delay (child, 6.0s sleep)
  │
  └─ [All three linked by trace_id: abc-123]
```

### Waterfall View

The waterfall is a timeline showing every span's start/end time and parent/child relationships. You immediately see where time went:
- If latency spike is in one child span → that's where to investigate
- If all child spans are fast but parent is slow → overhead elsewhere
- If error span is red → failed request is visible at a glance

### Log-to-Trace Correlation (The SRE Superpower)

By injecting `trace_id` into every log line, you wire logs and traces together. One click takes you from "I see an error in the logs" to "Here's the full request breakdown in a waterfall." That's the entire point of distributed tracing.

### Persistent Storage Matters

Without the `tempo_data` volume, every `docker-compose down` erases all trace history. With it, traces survive restarts and you can investigate issues from hours or days ago. Same principle as Prometheus and Loki — observability data must be persistent.

### Environment Variables > Hardcoding

Moving `OTEL_EXPORTER_OTLP_ENDPOINT` to `docker-compose.yml` makes the wiring visible and overridable. In production you might route to a different Tempo instance (e.g., a remote collector). Env vars let you do that without code changes.

---

## Next Steps

Phase 6 is **COMPLETE**. The distributed tracing system is fully functional:
- ✅ App instruments every request automatically
- ✅ Manual spans mark important operations
- ✅ Logs include trace IDs for correlation
- ✅ Tempo stores all traces
- ✅ Grafana displays waterfalls
- ✅ One-click log-to-trace jumps work
- ✅ Error traces are visually distinct

Potential enhancements (future roadmap):
- [ ] Trace sampling (for high-traffic services, store only 1 in 100 traces)
- [ ] Span processors for custom attributes (e.g., user_id, customer_id)
- [ ] Trace-to-metrics (generate RED metrics from traces)
- [ ] Service map visualization (see which services call which)
- [ ] Histogram analysis (latency distribution across spans)
