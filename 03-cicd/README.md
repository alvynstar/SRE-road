# Phase 3: CI/CD Ownership (PLANNED)

**Status:** Not started — placeholder for future work.

## Goal
Own the full pipeline that takes Flask app code from a pull request to running in the `sre-lab` kind cluster, with monitoring of the deploy itself.

## Planned Work
- GitHub Actions workflow that runs on every PR:
  - Lint Python code (ruff or flake8)
  - Run unit tests
  - Build the Flask Docker image
  - Push image to a registry (local or GHCR)
- Deploy stage that loads the new image into the `sre-lab` kind cluster
- Add Grafana annotations for deploy events so latency/error spikes can be correlated with releases
- Rollback drill: deploy a deliberately broken image, watch alerts fire (`HighErrorRate`, `AppDown`), execute rollback, write a postmortem

## SRE Skills This Phase Builds
- Pipeline ownership end-to-end (not just config)
- Deploy observability (annotations, deploy markers)
- Rollback procedures and drills
- Connecting "code change" → "production behavior" via metrics

## Prerequisites
- Phase 1 complete (observability stack)
- Phase 2 complete (chaos engineering, alerts validated)

## Files (to be created)
- `03-cicd/.github/workflows/ci.yml` — PR pipeline
- `03-cicd/.github/workflows/deploy.yml` — deploy pipeline
- `03-cicd/k8s/` — Kubernetes manifests for deploying the Flask app
- `03-cicd/runbooks/RollbackProcedure.md`
- `03-cicd/postmortems/` — postmortems from rollback drills
- `03-cicd/PROGRESS.md` — phase log
