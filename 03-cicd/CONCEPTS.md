# Phase 3 — CI/CD Ownership (Concepts)

The mental model for **owning the path from `git push` to a running pod**:
every safety gate, every artifact, every rollback lever.

Read top-to-bottom: pipeline shape → safety gates → image registry → deploy
→ rollback.

---

## 3.1 — What CI/CD Actually Is

```
                  ┌──────────────────────────────────┐
                  │   CI  (Continuous Integration)   │
                  │   ───────────────────────────    │
                  │   On every push, automatically:  │
                  │     • lint                       │
                  │     • run tests                  │
                  │     • build artifact (image)     │
                  │   Goal: catch bugs in minutes,   │
                  │   not in production.             │
                  └──────────────┬───────────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────────┐
                  │   CD  (Continuous Delivery /     │
                  │       Deployment)                │
                  │   ───────────────────────────    │
                  │   Ship the artifact to a target  │
                  │   environment automatically.     │
                  │   Goal: make deploys boring.     │
                  └──────────────────────────────────┘
```

**SRE framing:** CI/CD is your **error-budget protector**. Every manual
step is a chance for a human to break prod at 2am. Automation moves the
risky moments from "someone is tired and typing fast" to "the same script
that ran 1000 times yesterday."

---

## 3.2 — The Full Pipeline (this lab)

```
   ┌─────────────────────────────────────────────────────────────────┐
   │                  THE PIPELINE                                   │
   └─────────────────────────────────────────────────────────────────┘

      git push
         │
         ▼
   ┌──────────────────────┐
   │ GITHUB ACTIONS       │
   │ trigger: push or PR  │
   └──────────┬───────────┘
              │
              ▼
   ┌──────────────────────┐    ┌──────────────────────┐
   │ ① LINT (ruff)        │───▶│ ② TEST (pytest)     │
   │ catches style/bugs   │    │ catches behaviour    │
   │ before they merge    │    │ regressions          │
   └──────────────────────┘    └─────────┬────────────┘
                                         │  ✅ pass
                                         ▼
                              ┌──────────────────────┐
                              │ ③ BUILD IMAGE        │
                              │ docker build         │
                              └─────────┬────────────┘
                                        │
                                        ▼
                              ┌──────────────────────┐
                              │ ④ PUSH TO GHCR       │
                              │ (only on main)       │
                              │ tags:                │
                              │   sha-<short>        │
                              │   main               │
                              │   latest             │
                              └─────────┬────────────┘
                                        │
                                        ▼
                              ┌──────────────────────┐
                              │ ⑤ DEPLOY TO KIND     │
                              │ kubectl apply        │
                              │ ServiceMonitor scrape│
                              └─────────┬────────────┘
                                        │
                                        ▼
                              ┌──────────────────────┐
                              │ ⑥ GRAFANA ANNOTATION │
                              │ vertical line on the │
                              │ dashboard for every  │
                              │ deploy event.        │
                              └──────────────────────┘
```

---

## 3.3 — Safety Gates: Why Each Stage Exists

```
   STAGE        FAILURE IT PREVENTS                       LESSON
   ─────────    ──────────────────────────────────       ──────────────────
   Lint         "unused import" / style drift            cheap, fast feedback
   Tests        "I changed this and that broke"          regression detection
   Build        "works on my machine"                    reproducible artifact
   Image push   "we lost the binary we deployed"         immutable record
   Deploy       "I forgot to apply the new manifest"     automation, no humans
   Annotation   "did latency spike before/after deploy?" cause/effect overlay
```

### Branch protection — the most important rule

```
                ┌────────────────────────────────┐
                │   main branch                  │
                │   ────────────                 │
                │   ✗ direct push  BLOCKED       │
                │   ✓ PR required                │
                │   ✓ all status checks must pass│
                │   ✓ approvals (optional)       │
                └────────────────────────────────┘
```

**Why:** without this, anyone (including you, half-asleep) can push broken
code to main and trigger a deploy. With it, every change goes through the
pipeline. The pipeline becomes the only path to prod.

---

## 3.4 — Immutable Image Tags (Why `latest` is a Trap)

```
   ┌─────────────────────────────────────────────────────────────┐
   │  BAD: deploy with image:latest                              │
   │  ─────────────────────────────                              │
   │     today:    latest = sha-abc123  (working)                │
   │     tomorrow: latest = sha-def456  (broken)                 │
   │     rollback? "kubectl rollout undo"                        │
   │     → re-pulls latest → still broken. No way back.          │
   └─────────────────────────────────────────────────────────────┘

   ┌─────────────────────────────────────────────────────────────┐
   │  GOOD: deploy with image:sha-abc123                         │
   │  ─────────────────────────────────                          │
   │     each deploy pinned to one specific commit               │
   │     rollback = redeploy yesterday's SHA. Done.              │
   │                                                             │
   │     CI tags THREE things on each push to main:              │
   │       sha-abc123  ← the immutable one (use this for deploy) │
   │       main        ← convenience pointer                     │
   │       latest      ← convenience pointer                     │
   └─────────────────────────────────────────────────────────────┘
```

The same idea as git: branches move, commits don't. Deploy by SHA, navigate
by tag.

---

## 3.5 — The Registry (GHCR) Wire

```
                ┌──────────────────────────┐
                │   GITHUB ACTIONS RUNNER  │
                │  (builds the image)      │
                └────────────┬─────────────┘
                             │
                             │  docker push
                             │  with GITHUB_TOKEN
                             ▼
                ┌──────────────────────────┐
                │   GHCR                   │
                │   ghcr.io/alvynstar/     │
                │   sre-lab-app            │
                │                          │
                │   Public package:        │
                │   anyone can docker pull │
                └────────────┬─────────────┘
                             │
                             │  kubectl apply
                             │  (image: ghcr.io/.../sre-lab-app:sha-…)
                             ▼
                ┌──────────────────────────┐
                │   KIND CLUSTER           │
                │   ─────────────          │
                │   pulls the image,       │
                │   schedules the pod,     │
                │   exposes it via Service │
                └──────────────────────────┘
```

### Gotcha you hit in this lab

GHCR packages start **private** even when the source repo is public.
You have to flip the visibility manually under
*Package settings → Change visibility*. Otherwise `docker pull` fails
without credentials, your deploy can't pull the image, and the pod
sticks in `ImagePullBackOff`.

---

## 3.6 — Deploy Annotations: Closing the Causal Loop

```
   Without annotations:                With annotations:
   ────────────────────                ─────────────────
                                       (deploy line)
   error rate                             │
       │                                  │
       │     ╱╲                           │   ╱╲
       │    ╱  ╲                          │  ╱  ╲
       │   ╱    ╲                         │ ╱    ╲
       └──────────── time                 └──────────── time

   "Latency jumped. Did I cause it?"   "Latency jumped 30s after deploy.
   "Who knows."                         I caused it. Rollback."
```

Every successful deploy posts a `POST /api/annotations` to Grafana with
`dashboardUID` pointing at the Four Golden Signals dashboard. A vertical
line appears. From then on, every "weird spike" question has a fast,
visual answer: *was there a deploy?*

---

## 3.7 — Rollback Drill

```
              ┌────────────────────────────────────┐
              │  REAL ROLLBACK FLOW (what you did) │
              └────────────────────────────────────┘

       t=0    Deploy broken commit (sha-bad)
       t=1m   Error rate spike on dashboard
       t=2m   Slack alert fires (HighErrorRate)
       t=3m   git revert <bad-sha>  → push to main
       t=4m   CI rebuilds, retags, redeploys
       t=5m   Error rate drops back to baseline
       t=6m   Alert auto-resolves

              Postmortem:
                • Why did tests miss it?
                • Add a regression test.
                • Could it have been caught at PR review?
                • Tighten the lint/test gate.
```

**The rollback itself is just `git revert`.** That's the magic — your
deploy mechanism is just "build and push from main." Reverting in git
*is* the rollback. No special "rollback button" exists or needs to.

---

## TL;DR cheat sheet

```
CI    = lint + test + build on every push (catch bugs early)
CD    = deploy the built artifact automatically (make deploys boring)

Pipeline stages:
   push → lint → test → build → push to GHCR → deploy → annotate

Branch protection on main is non-negotiable.
Tag images by SHA, not `latest` (rollbacks need history).
Grafana annotations close the "did the deploy break it?" loop.
Rollback = git revert + redeploy (no special path).
```
