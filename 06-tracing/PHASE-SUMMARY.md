# Phase 6 Summary — Distributed Tracing: Closing the SRE Observability Triangle

## What This Phase Completed

After Phase 1–5, we had **metrics** (Prometheus) and **logs** (Loki). We could answer:
- "Is the service broken?" → Metrics + alerts
- "What error happened?" → Logs + dashboards
- "When did it start?" → Correlation by timestamp

But we still couldn't answer: **"Where is the time actually spent?"**

Phase 6 added **distributed tracing** via Tempo + OpenTelemetry, completing the observability triangle:

| Pillar | Question | Tool | Backend |
|--------|----------|------|---------|
| **Metrics** | Is it broken? | Prometheus scraping `/metrics` | Prometheus |
| **Logs** | What happened? | Promtail tailing stdout | Loki |
| **Traces** | Where is it slow? | OTel SDK exporting spans | **Tempo** |

All three converge in Grafana, unified by a single `trace_id` across logs and traces.

---

## What Was Built

### 1. Infrastructure (Docker Compose)
- **Tempo service** running OTLP receivers on ports 4317 (gRPC) and 4318 (HTTP)
- **Persistent `tempo_data` volume** — traces survive restarts
- **Service dependencies** (`depends_on: tempo`) — app waits for Tempo before starting
- **Explicit `OTEL_EXPORTER_OTLP_ENDPOINT` env var** — wiring is visible and overridable

### 2. Application Instrumentation (Flask)
- **OpenTelemetry SDK** configured to export spans to Tempo via gRPC
- **Auto-instrumentation** — Flask routes wrapped automatically; every request gets a span with HTTP method, path, status, duration
- **TraceIdFilter** — injects `trace_id` and `span_id` into every JSON log line
- **Manual spans** — `/api/slow` route marks the 6-second sleep as a child span
- **Error handling** — `/api/error` route records exceptions and sets error status on spans

### 3. Grafana Integration
- **Tempo datasource** — configured to query traces from Tempo on port 3200
- **Derived fields on Loki datasource** — regex extracts `trace_id` from JSON logs
- **One-click log-to-trace jumps** — click a trace_id in a log line and jump to the full waterfall view

---

## Why This Matters for SRE

**Scenario:** A customer reports that API requests are taking 6 seconds. Your alerts don't fire (still under SLO). Your error rate is normal. But *something* is slow.

**Without tracing:**
1. Check Prometheus dashboard for anomalies
2. Check Loki for errors or warnings around the timestamp
3. Grep logs for the request ID (if you're logging it)
4. Read through code to figure out what operations happen in sequence
5. Guess where the bottleneck is, deploy a fix, see if it helps

**With tracing:**
1. Find any request from that timeframe in Loki
2. Click the `trace_id` link
3. Grafana shows a waterfall with every operation and timing
4. You immediately see: "This child span (database query) took 5.8 seconds. That's your bottleneck."
5. You can rule out other operations with certainty, not guesses

**Portfolio value:** Demonstrates you understand:
- Request lifecycle across a service boundary (even in a monolith, you're decomposing work into spans)
- Instrumentation at the application level (not just infrastructure)
- How to correlate data across three different backends (Prometheus, Loki, Tempo)
- The full observability stack — you're not just consuming dashboards, you're building the tooling

---

## Journey: Phases 1–6 (Complete)

| Phase | Topic | Teaches | Outcome |
|-------|-------|---------|---------|
| **1** | Observability | Metrics + alerting; Four Golden Signals | Alert when service breaks |
| **2** | Chaos | Validate that alerts actually work | Confidence in observability |
| **3** | CI/CD | Automated testing, builds, deployments | Move fast without breaking things |
| **4** | Logs | Structured logging + aggregation | Understand *what* went wrong |
| **5** | SLOs | Error budgets + burn rate alerts | Reliability as a product feature |
| **6** | **Tracing** | **Request lifecycle visibility** | **Understand *where* time went** |

By the end of Phase 6, you have a production-grade observability system that can debug any reliability issue, from "the service is down" (Phase 1) to "that request is slow but not slow enough to trigger an alert" (Phase 6).

---

## Key Skills Demonstrated

### Technical
- ✅ OpenTelemetry SDK instrumentation (not just adding print statements)
- ✅ Parent/child span relationships and trace context propagation
- ✅ Log-to-trace correlation via derived fields (UX/API-level thinking)
- ✅ Infrastructure orchestration (services, volumes, environment variables)
- ✅ Multi-backend observability (metrics ≠ logs ≠ traces)

### SRE Mindset
- ✅ "Why does this matter?" before "how does this work?"
- ✅ Understanding the request journey (the customer's perspective)
- ✅ Persistence (traces, logs, metrics all need storage)
- ✅ Environment configurability (env vars, not hardcoding)
- ✅ Validation, not assumption (tested every link in the pipeline)

---

## What to Highlight in Interviews

**"Walk me through how you'd debug a slow request."**
> I'd find a log entry from that timeframe and click the trace_id to jump to Tempo. The waterfall shows every operation and its timing, so I can immediately see if it's a slow database query, a slow external API, or something else. If it's a microservice environment, I'd see which service is the bottleneck. That's why we instrument applications with OpenTelemetry — it's not just for fun, it's for actually diagnosing production issues fast.

**"How do you correlate logs and traces?"**
> We inject the trace_id into every JSON log line using a logging filter. Then in Grafana, we configure a derived field on the Loki datasource with a regex to extract the trace_id. When you click that link, Grafana queries Tempo for that trace_id and renders the waterfall. One click from log to trace, no page navigation.

**"Why not just use logs?"**
> Logs tell you *what* happened but not *when* or *where* relative to other operations. If a request goes through 5 services and you log at each one, you have 5 separate log entries that you have to correlate by timestamp. With traces, you get one timeline showing the exact sequence and timing. It's the difference between reading 5 separate books versus reading a single integrated story.

---

## Files to Share

- **CONCEPTS.md** — The mental models (read this first)
- **PROGRESS.md** — What was built and validated
- **01-observability/app/app.py** — Application instrumentation (see OTel setup, TraceIdFilter, error handling)
- **01-observability/docker-compose.yml** — Infrastructure (Tempo service, dependencies, env vars)

## Next Steps (If Continuing)

Potential Phase 7 directions:
- **Trace sampling** — for high-traffic services, store only 1 in 100 traces to control costs
- **Service map** — visualize which services call which (requires multi-service environment)
- **Trace-to-metrics** — automatically generate RED metrics from spans
- **SLO-driven tracing** — combine SLOs (Phase 5) with traces for root cause analysis of SLO violations

But Phase 6 is a natural stopping point — the full observability stack is complete and validated end-to-end.
