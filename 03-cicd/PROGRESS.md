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

## 3.3 — Deploy to kind cluster (NEXT)

### Goal
Replace the Docker Compose Flask container with a Kubernetes Deployment that pulls the image from GHCR. The `sre-lab` kind cluster (already running for Phase 1's kube-prometheus-stack) becomes the runtime.

### Open questions to answer in the design phase
- Plain manifests vs Helm chart vs Kustomize?
- Namespace: deploy into `default`, `monitoring`, or new `sre-lab-app` namespace?
- How does kind pull from GHCR (LoadBalancer? port-forward? ingress)?
- ServiceMonitor wiring so kube-prometheus-stack scrapes the new pod
- imagePullPolicy: `Always` vs `IfNotPresent` and what each means for deploys

## 3.4 — Grafana deploy annotations (PLANNED)
## 3.5 — Rollback drill + postmortem (PLANNED)
