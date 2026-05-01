# Runbook: HighLatency

## Alert Summary
- **Alert name:** HighLatency
- **Condition:** p95 request duration > 5 seconds for 2 minutes
- **Severity:** Warning
- **Notification:** Slack

## What this means
95% of requests are taking longer than 5 seconds to complete. Users are experiencing slow responses. This does not mean the app is down — but left unresolved, it often leads to timeouts and then errors.

## p95 vs p50 — what to check first
| Metric | High | Meaning |
|---|---|---|
| p95 high, p50 normal | A small subset of requests are slow | Specific endpoint or edge case |
| p95 high, p50 high | Most requests are slow | Systemic issue — resource exhaustion or dependency |

Query both in Prometheus:
```
histogram_quantile(0.95, rate(app_request_duration_seconds_bucket[5m]))
histogram_quantile(0.50, rate(app_request_duration_seconds_bucket[5m]))
```

## Likely Causes
1. Resource exhaustion — CPU or memory saturated, requests queuing up
2. Too many concurrent requests overwhelming the single-threaded Flask server
3. A slow or unresponsive downstream dependency (database, external API)
4. Network degradation between services
5. A DoS or abnormal traffic spike

## Investigation Steps

### 1. Check if the app is still responding
```bash
curl -w "\nTime: %{time_total}s\n" http://localhost:5001/health
```
Note the response time — if health check itself is slow, the app is under stress.

### 2. Check p95 vs p50 in Prometheus
```
histogram_quantile(0.95, rate(app_request_duration_seconds_bucket[5m]))
histogram_quantile(0.50, rate(app_request_duration_seconds_bucket[5m]))
```
Use the result to determine if this is isolated or systemic.

### 3. Check resource usage
```bash
docker stats
```
Look for:
- CPU > 80% sustained → requests are queuing
- Memory near limit → possible swap usage, slowing everything down

### 4. Check traffic volume
In Prometheus:
```
sum(rate(app_requests_total[5m]))
```
Compare to baseline. A sudden spike in traffic can saturate a single-threaded server.

### 5. Check application logs for slow requests or timeouts
```bash
docker logs <flask-container-name> --tail=100
```
Look for timeout errors or unusually long request traces.

### 6. Check Grafana dashboard
Go to: http://localhost:3000 → Four Golden Signals dashboard
Review Traffic, Latency p95, and Latency p50 panels together.

## Remediation

| Cause | Action |
|---|---|
| CPU/memory exhaustion | Restart app; investigate and fix the resource leak |
| Traffic spike | Rate limit incoming requests; scale horizontally if possible |
| Slow dependency | Bypass or cache the dependency; restart it if possible |
| Network issue | Check connectivity between containers: `docker network inspect` |
| DoS / abnormal traffic | Block the source IP at the load balancer or firewall level |

## Escalation
If latency does not recover within 10 minutes, escalate with:
- Grafana screenshot showing p95 and p50 over time
- Output of `docker stats` at time of alert
- Whether error rate is also elevated (check HighErrorRate alert)

## Related Alerts
- HighErrorRate — sustained latency often precedes or accompanies error rate spikes
