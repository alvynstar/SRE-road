# Phase 3: CI/CD Ownership — Progress Log

## 3.1 — Lint + test in CI (DONE)
- pytest tests added under `01-observability/app/tests/`
- ruff config added (`01-observability/app/pyproject.toml` or `ruff.toml`)
- GitHub Actions workflow `.github/workflows/ci.yml` runs on every PR + push to `main`
- Validated: failing test or lint error blocks the workflow

## 3.2 — Docker build + push to GHCR (DONE)

### Decisions
- **Registry:** GHCR (`ghcr.io/alvynstar/sre-lab-app`) — auth via built-in `GITHUB_TOKEN`, no extra secrets
- **Tagging strategy:** every build gets three tags
  - `sha-<short>` — immutable, answers "which commit is running?"
  - `main` — mutable pointer to current main
  - `latest` — alias for default-branch tip
- **Push policy:** build on every PR (validates Dockerfile), push only on `main`

### Workflow structure
- New job `docker-build-push` in `.github/workflows/ci.yml`
- `needs: lint-and-test` → broken tests block the image build
- `permissions: packages: write` granted at job level (scoped to this run)
- `docker/build-push-action` with `push: ${{ github.event_name != 'pull_request' }}`
- GitHub Actions cache (`type=gha`) speeds repeat builds

### One-time post-merge step
After the first successful push to `main`, GHCR creates the package as **private** by default.
For a public portfolio repo, flip it to public:
1. GitHub → profile → **Packages** → `sre-lab-app`
2. **Package settings** → **Change visibility** → Public
3. Also link the package to this repo under "Manage Actions access" so future
   workflow runs in this repo can push without re-authorizing

### Validation evidence
- [x] PR #1 ran `Lint and test Flask app` (13s) + `Build and push Flask image to GHCR` (28s) — both green
- [x] PR run built image but did **not** push (PR gate confirmed working via `push: ${{ github.event_name != 'pull_request' }}`)
- [x] After merge, post-merge run #3 on `main` (45s total) built **and** pushed to GHCR
- [x] Package `sre-lab-app` appeared at https://github.com/users/alvynstar/packages/container/sre-lab-app
- [x] Three tags present: `sha-d10cba9` (immutable), `main`, `latest`
- [x] Package visibility flipped from private (default) to public for anonymous pulls
- [x] Branch protection on `main` enforced — direct pushes blocked, PR + green CI required

### Lessons learned
- **Branch protection on private free repos is decorative** — saved rules show "Not enforced" until repo is public or upgraded to paid plan. Made repo public after secret-scan.
- **GHCR packages default to private** even when source repo is public. Visibility is a separate per-package setting, must be flipped manually after first push.
- **Solo developers must untick "Require approvals"** — GitHub does not allow self-approval. Keeping approvals=0 still enforces the PR flow without locking yourself out.
- **GHA build was 51s on first PR run** thanks to layer cache (`type=gha`). Subsequent builds even faster when only `app.py` changes.
- **Deprecation warning noted** on `actions/checkout@v4`, `setup-python@v5`, `docker/build-push-action@v6` (Node.js 20 EOL). Track for a future maintenance PR; not blocking.

## 3.3 — Deploy to kind cluster (DONE)

### Implementation
Created three Kubernetes manifests in `03-cicd/k8s/`:

| File | Purpose |
|---|---|
| `deployment.yaml` | Runs 1 replica of `ghcr.io/alvynstar/sre-lab-app:latest` on port 5001 |
| `service.yaml` | Exposes the pod internally on port 80 → 5001 (added `app: sre-lab-app` label for ServiceMonitor discovery) |
| `servicemonitor.yaml` | Tells kube-prometheus-stack (Prometheus) to scrape the app on the `http` port every 30s |

### Key decisions made
- **Manifests:** Plain YAML files (simplest for learning, easy to version in git)
- **Namespace:** `default` (same as Phase 1 stack for simplicity; production would use dedicated namespace)
- **imagePullPolicy:** `Always` (pulls latest tag every time — ensures fresh image)
- **Resources:** 128Mi—256Mi memory, 100m—500m CPU (prevents resource starvation)
- **Service discovery:** ServiceMonitor labeled with `release: kube-prometheus-stack` so Prometheus picks it up

### Validation evidence
- [x] `kubectl apply` created Deployment + Service + ServiceMonitor without errors
- [x] Pod status: `1/1 Running` within 22s (image pull + start)
- [x] Health check: `curl http://localhost:8080/health` returns `{"status": "healthy"}`
- [x] Prometheus targets list now includes `sre-lab-app` (verified via API)
- [x] App metrics scraped: `app_requests_total` visible in Prometheus after generating traffic

### Debugging steps taken
1. **Initial ServiceMonitor not picked up:** Prometheus only watches ServiceMonitors with label `release: kube-prometheus-stack` (per kube-prometheus-stack config)
2. **Service not matched by ServiceMonitor:** Service needed label `app: sre-lab-app` (not just selector, but metadata label)
3. **Port mismatch initially:** Fixed by ensuring ServiceMonitor references `port: http` which exists in Service

### Lessons learned
- Kubernetes service discovery requires **explicit labels on both Service and ServiceMonitor** — not obvious from YAML syntax
- `imagePullPolicy: Always` ensures dev/test workflows use fresh images, but production would use explicit SHA tags
- Port naming in Services matters for ServiceMonitors — matching port names is less error-prone than port numbers

## 3.4 — Grafana deploy annotations (PLANNED)
## 3.5 — Rollback drill + postmortem (PLANNED)
