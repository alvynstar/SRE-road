# Postmortem: Phase 3.5 Rollback Drill

**Date:** 2026-05-09  
**Severity:** High (100% error rate on /api/data)  
**Duration:** ~30 minutes (bad deploy → rollback complete)  
**Author:** toks

---

## Summary

A deliberate bad deploy was merged to main as part of a Phase 3.5 rollback drill. The `/api/data` endpoint was modified to return HTTP 500 for all requests, causing a 100% error rate on that endpoint. The issue was detected via Grafana's Error Rate panel and resolved by running `git revert` on the bad commit, which triggered CI to redeploy the good version automatically.

---

## Timeline

| Time | Event |
|------|-------|
| 12:08 | Bad deploy merged to main via PR #9 |
| 12:08 | CI pipeline ran — lint + tests passed, bad image pushed to GHCR |
| 12:08 | Bad image deployed to kind cluster + Docker Compose via CI |
| 12:08 | Grafana annotation appeared (cyan vertical line on dashboard) |
| ~12:20 | Traffic generated to port 5001 — error rate spiked to ~2 req/s |
| ~12:08 | `git revert HEAD -m 1 --no-edit` executed on main |
| ~12:09 | CI ran — good image built, pushed, and redeployed |
| ~12:09 | Error rate dropped to 0, Grafana annotation confirmed rollback deploy |

---

## Root Cause

`/api/data` was intentionally modified in `app.py` (lines 23-28) to return HTTP 500 for every request instead of the normal 200 response. The change also incremented `app_errors_total` metric, making the error rate visible in Prometheus and Grafana. The bad code passed CI tests because the test was also updated to expect a 500 response.

## What Went Well

- Grafana annotation immediately showed when the bad deploy happened (cyan vertical line)
- Error Rate panel clearly showed the spike — easy to correlate with the deploy annotation
- `git revert` successfully triggered CI and redeployed the good version automatically
- Second Grafana annotation confirmed the rollback deploy timestamp

## What Went Wrong

- `kubectl rollout undo deployment/sre-lab-app` failed with "no rollout history found" — because the deployment manifest always uses the `latest` tag; Kubernetes only creates a new revision when the spec changes, so there was nothing to undo
- Had to use `git revert` as the rollback method instead — more steps, slower than a direct kubectl rollback
- Docker Compose app also had to be manually rebuilt after rollback (it doesn't auto-update from GHCR)

---

## Action Items

| Action | Owner | Priority |
|--------|-------|----------|
| Update CI workflow to inject the exact SHA tag into deployment.yaml so `kubectl rollout undo` works | toks | High |
| Add a rollback runbook to `03-cicd/runbooks/` documenting both `kubectl rollout undo` and `git revert` paths | toks | Medium |

---

## Lessons Learned

- **`latest` tag breaks rollback:** Using `latest` in the deployment manifest means Kubernetes sees only one revision. Always use immutable SHA tags in production so `kubectl rollout undo` is available as a fast rollback option.
- **Git revert is a valid rollback — but slower:** It works, but requires CI to complete (~90s) before the fix is live. Direct kubectl rollback would be near-instant.
- **Grafana annotations are powerful:** The deploy markers made it immediately obvious when the incident started and when it was resolved — no need to cross-reference git logs and timestamps manually.
