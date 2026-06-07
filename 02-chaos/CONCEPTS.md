# Phase 2 — Chaos Engineering (Concepts)

You can't trust monitoring you've never seen fire. Chaos engineering is the
discipline of **deliberately breaking your system in controlled ways** to
verify that your alerts, runbooks, and recovery procedures actually work
*before* a real incident proves they don't.

Read top-to-bottom: principles → the experiment loop → what each chaos type
catches → the postmortem.

---

## 2.1 — The Core Idea

```
                       ┌──────────────────────────┐
                       │   "Hope is not a         │
                       │    strategy."            │
                       │                          │
                       │   You only know your     │
                       │   alert works if you've  │
                       │   seen it fire.          │
                       └──────────────────────────┘
                                  │
                                  ▼
              ┌────────────────────────────────────────┐
              │  Inject failure on purpose,            │
              │  in a controlled way,                  │
              │  and observe how the system responds.  │
              │                                        │
              │  Did the alert fire?                   │
              │  Did Slack get pinged?                 │
              │  Did the runbook actually help?        │
              │  How long until detection?             │
              │  How long until recovery?              │
              └────────────────────────────────────────┘
```

### Three principles

1. **Hypothesize first.** Write down what you *expect* to happen before
   you break anything. The gap between expectation and reality is where
   the learning lives.
2. **Blast radius matters.** Start in dev. Only graduate to prod once
   you've proven the experiment is contained.
3. **Every experiment ends with a postmortem.** No exceptions — even
   successful ones. Especially successful ones.

---

## 2.2 — The Experiment Loop

```
        ┌─────────────────────┐
        │   ① HYPOTHESIZE     │   "If I kill the Flask container,
        │                     │    HighErrorRate should fire within
        │   write down what   │    2 minutes and Slack should ping."
        │   you expect        │
        └──────────┬──────────┘
                   │
                   ▼
        ┌─────────────────────┐
        │   ② INJECT          │   docker stop sre-lab-app
        │                     │
        │   break it on       │   (or: flood /api/error,
        │   purpose           │    or: hammer /api/slow)
        └──────────┬──────────┘
                   │
                   ▼
        ┌─────────────────────┐
        │   ③ OBSERVE         │   Watch Prometheus graphs.
        │                     │   Wait for AlertManager.
        │   what actually     │   Check Slack.
        │   happens?          │   Time everything.
        └──────────┬──────────┘
                   │
                   ▼
        ┌─────────────────────┐
        │   ④ RECOVER         │   docker start sre-lab-app
        │                     │
        │   bring it back     │   Verify alert auto-resolves.
        └──────────┬──────────┘
                   │
                   ▼
        ┌─────────────────────┐
        │   ⑤ POSTMORTEM      │   What surprised you?
        │                     │   What's missing?
        │   write it down     │   What's the action item?
        └─────────────────────┘
```

### What you learn from each step

- **Hypothesize** forces you to know your own system. If you can't predict
  what'll happen, you don't actually understand it yet.
- **Inject** has to be reversible. Always.
- **Observe** is where reality bites. Phase 2 Experiment 1 found that
  killing the app produced **zero alerts** — because the existing alerts
  depended on metrics emitted *by the dead app*. That's a gap you only
  find by trying.
- **Recover** also tests your auto-resolution path. An alert that fires
  but never clears is almost as bad as one that doesn't fire at all.
- **Postmortem** turns a one-time experiment into permanent institutional
  knowledge.

---

## 2.3 — The Three Experiments in this Lab

```
   ┌────────────────────────────────────────────────────────────┐
   │  EXPERIMENT 1: Kill the app                                │
   │  ──────────────────────────                                │
   │  Inject:    docker stop sre-lab-app                        │
   │  Expected:  HighErrorRate fires                            │
   │  Reality:   ZERO alerts — app can't emit metrics if dead   │
   │  Fix:       Add AppDown alert using up{} == 0              │
   │  Lesson:    Alerts that depend on the target's own metrics │
   │             have a blind spot when the target is gone.     │
   │             Use Prometheus-generated signals (like `up`).  │
   └────────────────────────────────────────────────────────────┘

   ┌────────────────────────────────────────────────────────────┐
   │  EXPERIMENT 2: Error flood                                 │
   │  ─────────────────────────                                 │
   │  Inject:    bash generate_errors.sh (2 req/s to /api/error)│
   │  Expected:  HighErrorRate fires after 1m sustained         │
   │  Reality:   Fired → Slack pinged → resolved after recovery │
   │  Lesson:    Confirms the canonical alert path works        │
   │             end-to-end (Prometheus → AlertManager → Slack).│
   └────────────────────────────────────────────────────────────┘

   ┌────────────────────────────────────────────────────────────┐
   │  EXPERIMENT 3: Latency spike                               │
   │  ───────────────────────────                               │
   │  Inject:    bash generate_latency.sh (hits /api/slow)      │
   │  Expected:  HighLatency (p95 > 5s) fires after 2m          │
   │  Reality:   Fired — but p95 ≈ p50 because /api/slow is     │
   │             UNIFORMLY slow. Real degradation would diverge.│
   │  Lesson:    A synthetic latency endpoint is not the same   │
   │             shape as a real partial degradation. To get    │
   │             p95 ≫ p50, you need a mix of fast + slow.      │
   └────────────────────────────────────────────────────────────┘
```

---

## 2.4 — Why this is "real SRE"

```
   Without chaos:                With chaos:
   ──────────────                ───────────
   "We have alerts."             "We have alerts that fire."
   "We have a runbook."          "We have a runbook that works."
   "We have monitoring."         "We know our monitoring's blind spots."
   "We'll know if it breaks."    "We've seen what breaking looks like."
```

You can't learn this from reading docs. The Experiment 1 alerting gap
isn't documented anywhere — it falls out of the act of breaking the system
and watching the dashboard stay green while everything is on fire.

### Chaos engineering vs. testing

| Aspect    | Unit/Integration Tests       | Chaos Engineering              |
| --------- | ---------------------------- | ------------------------------ |
| Asks      | "Does the code work?"        | "Does the *system* survive?"   |
| Scope     | One function / one service   | The whole stack + the humans   |
| Failure   | A bug in code                | A bug in operations / response |
| Output    | Green CI                     | A postmortem + a follow-up     |

Tests stop a bug from shipping. Chaos stops an outage from being a surprise.

---

## 2.5 — Postmortem Discipline

Every experiment ends with a postmortem document. Template structure:

```
   ┌────────────────────────────────────────┐
   │  POSTMORTEM: <experiment name>         │
   ├────────────────────────────────────────┤
   │  Hypothesis  — what you expected       │
   │  Method      — exactly what you did    │
   │  Timeline    — t=0 inject, t=… alert   │
   │  Outcome     — what really happened    │
   │  Surprises   — what didn't match       │
   │  Action items— what to fix next        │
   └────────────────────────────────────────┘
```

**Blameless** is the keyword. Postmortems are about *systems and processes*,
not about who typed which command. If a human action caused the issue, the
question is: "what should the system have done to make that action safe?"

---

## TL;DR cheat sheet

```
Chaos engineering = deliberately breaking things in controlled ways
                    to verify your monitoring + runbooks actually work.

Loop: Hypothesize → Inject → Observe → Recover → Postmortem

Three traps it catches:
  1. Alerts that can't fire (app-emitted metrics, dead app)
  2. Alerts that fire but no one is paged (routing gap)
  3. Alerts that page but the runbook doesn't work (response gap)

Every experiment ends with a written postmortem — no exceptions.
```
