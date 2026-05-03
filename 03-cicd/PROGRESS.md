# Phase 3: CI/CD Ownership — Progress Log

## 3.1 — Lint + test in CI (DONE)
- pytest tests added under `01-observability/app/tests/`
- ruff config added (`01-observability/app/pyproject.toml` or `ruff.toml`)
- GitHub Actions workflow `.github/workflows/ci.yml` runs on every PR + push to `main`
- Validated: failing test or lint error blocks the workflow

## 3.2 — Docker build + push to GHCR (IN PROGRESS)

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

### Validation checklist (do after first merge to main)
- [ ] Workflow run shows both jobs green
- [ ] `ghcr.io/alvynstar/sre-lab-app:sha-<short>` exists in Packages
- [ ] `ghcr.io/alvynstar/sre-lab-app:main` and `:latest` also exist
- [ ] `docker pull ghcr.io/alvynstar/sre-lab-app:latest` succeeds locally
- [ ] Open a PR with a no-op change → confirm image is **built but not pushed**

## 3.3 — Deploy to kind cluster (NEXT)
## 3.4 — Grafana deploy annotations (PLANNED)
## 3.5 — Rollback drill + postmortem (PLANNED)
