# Runbook: HighErrorRate

## Alert Summary
- **Alert name:** HighErrorRate
- **Condition:** Error rate > 0.7 req/s for 1 minute
- **Severity:** Critical
- **Notification:** Slack

## What this means
The application is returning HTTP 500 errors above the acceptable threshold. This indicates something in the request pipeline is failing — either inside the app or in a dependency it relies on.

## Likely Causes
1. A dependency is down (database, external API, cache, message queue)
2. An unhandled exception in the application code
3. Resource exhaustion (CPU/memory) causing the app to crash mid-request
4. A bad deployment introduced a bug that causes consistent failures
5. The `/api/error` endpoint is being called repeatedly (in this lab environment)

## Investigation Steps

### 1. Check if the app is still responding
```bash
curl http://localhost:5001/health
```
- Returns `{"status": "healthy"}` → app is up, errors are coming from a specific endpoint
- Connection refused or timeout → app is down, restart it

### 2. Identify which endpoint is generating errors
Query Prometheus to see error breakdown by endpoint:
```
sum by (endpoint) (rate(app_errors_total[5m]))
```
Go to: http://localhost:9090

### 3. Check application logs
```bash
docker logs <flask-container-name> --tail=100
```
Look for stack traces, unhandled exceptions, or connection errors to dependencies.

### 4. Check container resource usage
```bash
docker stats
```
Look for CPU or memory near 100% — this can cause requests to fail.

### 5. Check Grafana Error Rate panel
Go to: http://localhost:3000 → Four Golden Signals dashboard
Correlate the error spike with traffic spike or latency spike.

## Remediation

| Cause | Action |
|---|---|
| App is down | `docker compose restart app` |
| Dependency is down | Restart the affected service; check its logs |
| Bad deployment | Roll back to the previous image |
| Resource exhaustion | Scale up or reduce traffic; investigate memory leaks |
| Code bug | Fix and redeploy; hotfix if in production |

## Escalation
If errors persist after 10 minutes of investigation and the above steps don't resolve it, escalate to the service owner with:
- Grafana screenshot of the error rate panel
- Relevant log lines from `docker logs`
- Which endpoint is affected

## Related Alerts
- HighLatency — error spikes often accompany latency spikes if the app is struggling
