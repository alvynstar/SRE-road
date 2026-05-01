# Phase 4: Log Aggregation with Loki (PLANNED)

**Status:** Not started — placeholder for future work.

## Goal
Add structured logging to the Flask app, ship logs into Loki, and build dashboards that correlate metrics + logs so you can pivot from "p95 latency spiked at 19:54" to "here are the actual log lines that caused it."

## Planned Work
- Add Loki + Promtail to the Docker Compose stack (or via Helm into the kind cluster)
- Add structured JSON logging to the Flask app (replace `print` / default Flask logger with a structured logger)
- Wire Promtail to collect Flask container logs and push them to Loki
- Add Loki as a Grafana datasource
- Build a combined dashboard: latency p95 panel + matching log query panel — clicking a spike scopes the log panel to that time window
- Practice using LogQL to find errors during a chaos experiment (re-run Experiment 2 and use Loki to investigate)

## SRE Skills This Phase Builds
- Logs as a first-class signal alongside metrics
- LogQL query language
- Three-pillar observability (metrics + logs + traces — traces come later)
- Faster MTTR through metric → log correlation

## Prerequisites
- Phase 1 complete (observability stack and Grafana)
- Phase 2 complete (chaos experiments to use as log investigation drills)

## Files (to be created)
- `04-logs-loki/loki/loki-config.yml`
- `04-logs-loki/promtail/promtail-config.yml`
- `04-logs-loki/grafana/dashboards/flask-logs-and-metrics.json`
- `04-logs-loki/PROGRESS.md` — phase log
