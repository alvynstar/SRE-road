# Phase 5 — SLOs & Error Budgets (Concepts)

The mental model for the **language SREs use to argue about reliability**:
how a fuzzy goal like "the service should be reliable" becomes a number,
a budget, and an alert that pages you at exactly the right rate.

Read top-to-bottom: SLI / SLO / SLA → error budget → burn rate → recording
rules.

---

## 5.1 — The Three Letters: SLI, SLO, SLA

```
   ┌──────────────────────────────────────────────────────────────┐
   │                                                              │
   │   SLI — Service Level INDICATOR                              │
   │   ─────────────────────────────                              │
   │   A *measurement*. A live number you can graph.              │
   │   Example:  "right now, 99.4% of requests succeed"           │
   │                                                              │
   │   SLO — Service Level OBJECTIVE                              │
   │   ─────────────────────────────                              │
   │   A *target* for the SLI. An internal promise.               │
   │   Example:  "we want availability to stay ≥ 99% over 30 days"│
   │                                                              │
   │   SLA — Service Level AGREEMENT                              │
   │   ─────────────────────────────                              │
   │   A *contract* with consequences. Usually money.             │
   │   Example:  "if we drop below 99.5%, customer gets a refund" │
   │                                                              │
   │   SLA = SLO + lawyers.                                       │
   │                                                              │
   └──────────────────────────────────────────────────────────────┘
```

### How they relate in time

```
       SLI:  ━━━━━━┓     ┏━━━━━━━━━━━━━━━━━━━┓    ┏━━━━━━━
                   ┗━━━━━┛                    ┗━━━━┛
                  (live signal, fluctuating)

       SLO:  ─────────────────────────────────────────  ◄── 99% target
                                                              line on graph

       SLA:  threshold below SLO, externally promised
```

**Why two numbers (SLO and SLA)?** You set the SLO **stricter** than the SLA
on purpose. The gap between them is your **safety margin** — room to fix
problems before they cost the company money.

---

## 5.2 — This Lab's SLOs

```
   ┌────────────────────────────────────────────────────────┐
   │   SLO 1 — Availability                                 │
   │   ─────────────────────                                │
   │   Target:  99% of requests succeed (non-5xx)           │
   │   Window:  rolling 30 days                             │
   │                                                        │
   │   SLI expr:                                            │
   │     (sum(rate(app_requests_total[5m]))                 │
   │      - sum(rate(app_errors_total[5m])))                │
   │      / sum(rate(app_requests_total[5m]))               │
   │                                                        │
   │   "Of all requests in the last 5m, what fraction       │
   │    did NOT return an error?"                           │
   ├────────────────────────────────────────────────────────┤
   │   SLO 2 — Latency                                      │
   │   ─────────────                                        │
   │   Target:  95% of requests complete in < 300ms         │
   │   Window:  rolling 30 days                             │
   │                                                        │
   │   SLI expr:                                            │
   │     histogram_quantile(0.95,                           │
   │       sum(rate(                                        │
   │         app_request_duration_seconds_bucket[5m]        │
   │       )) by (le))                                      │
   └────────────────────────────────────────────────────────┘
```

---

## 5.3 — The Error Budget

This is the **single most important SRE idea**. Internalize it.

```
   ┌──────────────────────────────────────────────────────────────┐
   │   If your SLO is 99%, you're explicitly saying:              │
   │                                                              │
   │      "We are OK with 1% of requests failing."                │
   │                                                              │
   │   That 1% is your ERROR BUDGET.                              │
   │                                                              │
   │      ┌────────────────────────────────────────────────┐      │
   │      │ Allowed failures in 30 days @ 1M req/day = ?  │      │
   │      │   1% × 30,000,000 = 300,000 failures         │      │
   │      │   That's your budget for the month.           │      │
   │      └────────────────────────────────────────────────┘      │
   └──────────────────────────────────────────────────────────────┘

       Error budget left           = (1 - actual_failure_rate)
                                      / (1 - SLO_target)

       Example:
           availability over 1h = 0.995  (so failure rate = 0.005)
           SLO target           = 0.99   (so allowed failure = 0.01)

           budget remaining = (0.995 - 0.99) / (1 - 0.99)
                            = 0.005 / 0.01
                            = 0.5  (50% of monthly budget left)
```

### Why this changes everything

```
   ┌─────────────────────────────────────────────────────────────┐
   │   WITHOUT error budget:                                     │
   │   ──────────────────────                                    │
   │   Product team: "We want to ship feature X."                │
   │   Ops team:     "It's risky. We say no."                    │
   │   → endless arguing about gut feel                          │
   │                                                             │
   │   WITH error budget:                                        │
   │   ───────────────────                                       │
   │   Product team: "We want to ship feature X."                │
   │   Ops team:     "We have 65% of this month's budget left.   │
   │                  Ship it. We'll watch the graph."           │
   │   OR                                                        │
   │   Ops team:     "We have 5% left. Freeze releases until     │
   │                  next window."                              │
   │   → factual, repeatable, no politics                        │
   └─────────────────────────────────────────────────────────────┘
```

The error budget gives **shipping speed** and **reliability** a common
currency. They're no longer opposed values — they're a balance you can
measure.

---

## 5.4 — Burn Rate (and why it determines who gets paged)

```
   ┌──────────────────────────────────────────────────────────────┐
   │   BURN RATE = "how fast am I spending my budget?"            │
   │                                                              │
   │   burn_rate = actual_failure_rate / allowed_failure_rate     │
   │                                                              │
   │   1x  burn = on track to use exactly 100% of budget in 30d   │
   │   2x  burn = will exhaust budget in 15 days                  │
   │   14.4x    = will exhaust budget in ~2 days  ← PAGE NOW      │
   │   100x     = will exhaust budget in ~7 hours                 │
   └──────────────────────────────────────────────────────────────┘
```

### The multi-window alert philosophy

```
   ┌─────────────────────────────────────────────────────────────┐
   │   FAST BURN  (page someone)                                 │
   │   ─────────────────────────                                 │
   │   Condition: burn rate > 14.4x for 2 minutes                │
   │   Why 14.4? At that rate you burn 2% of monthly budget      │
   │              per hour. You can't sleep through this.        │
   │   Severity: PAGE — wake them up                             │
   │                                                             │
   │   SLOW BURN  (file a ticket)                                │
   │   ──────────────────────────                                │
   │   Condition: burn rate > 1x for 15 minutes                  │
   │   Why:       Slow but steady drain. Not on fire, but        │
   │              you'll exhaust the budget by month-end if      │
   │              nobody investigates.                           │
   │   Severity: TICKET — assign during business hours           │
   └─────────────────────────────────────────────────────────────┘
```

### Why two thresholds (not one)

```
   One threshold:                  Two thresholds:
   ──────────────                  ───────────────
   "alert if errors > X"            "page fast, ticket slow"

   Either:                          • Fast burst → page immediately
     - too sensitive → noise        • Slow drip → ticket, daytime
     - too lax → miss real          • Steady normal → no alert
       outages
                                    Catches both shapes of failure
                                    without paging on noise.
```

This is **the Google SRE alerting pattern**. The math: choose burn rates
such that the alert fires when you'd actually want a human involved, given
the size of the budget at stake.

---

## 5.5 — Recording Rules (the performance trick)

```
   ┌──────────────────────────────────────────────────────────────┐
   │   PROBLEM                                                    │
   │   ────────                                                   │
   │   The SLO expressions above are EXPENSIVE.                   │
   │   histogram_quantile() over high-cardinality data scans      │
   │   millions of points. If your dashboard runs it every 5s,    │
   │   Prometheus melts.                                          │
   └──────────────────────────────────────────────────────────────┘

                                  │
                                  ▼

   ┌──────────────────────────────────────────────────────────────┐
   │   SOLUTION: pre-compute on a schedule                        │
   │                                                              │
   │     groups:                                                  │
   │       - name: slo_rules                                      │
   │         interval: 15s                                        │
   │         rules:                                               │
   │           - record: slo:availability:rate5m                  │
   │             expr:   <the expensive expression>               │
   │                                                              │
   │   Now Prometheus runs the expression every 15s and stores    │
   │   the result as a NEW METRIC named `slo:availability:rate5m`.│
   │                                                              │
   │   Your dashboard queries that metric → cheap, instant.       │
   └──────────────────────────────────────────────────────────────┘
```

### Naming convention

```
   slo:availability:rate5m
   ─── ─────────── ──────
    │       │         │
    │       │         └── window or operation
    │       └──────────── what is being measured
    └──────────────────── what kind of metric (slo, sli, etc.)
```

Use **colons** in recording rule names (not underscores). Prometheus
itself doesn't care, but this is the conventional signal that "this
metric is computed, not raw."

---

## 5.6 — Putting it All Together

```
        ┌──────────────────────────────────────────────────────┐
        │             THE SLO STACK                            │
        └──────────────────────────────────────────────────────┘

   ┌──────────────────────┐
   │  RAW METRICS         │   app_requests_total
   │  (from /metrics)     │   app_errors_total
   │                      │   app_request_duration_seconds
   └──────────┬───────────┘
              │
              ▼
   ┌──────────────────────┐
   │  RECORDING RULES     │   slo:availability:rate5m
   │  (pre-computed SLIs) │   slo:latency_p95:rate5m
   │  every 15s           │   slo:error_budget_remaining:rate1h
   └──────────┬───────────┘
              │
        ┌─────┴─────┐
        ▼           ▼
   ┌────────┐  ┌──────────────────────┐
   │ SLO    │  │ BURN RATE ALERTS     │
   │ DASH-  │  │  fast burn → page    │
   │ BOARD  │  │  slow burn → ticket  │
   │        │  │                      │
   │ shows: │  └──────────────────────┘
   │  - SLI now
   │  - SLO target line
   │  - budget left as %
   │  - latency p95 vs target
   └────────┘
```

---

## TL;DR cheat sheet

```
SLI  = the live measurement              "we are at 99.4% right now"
SLO  = the internal target               "we promise ≥ 99%"
SLA  = the external contract             "if < 99.5% you get a refund"

Error budget = (1 - SLO_target)          "we're OK with 1% failure"
             = how much room you have    "300k bad requests / month"

Burn rate = real failure / budgeted failure
   14.4x → page (2-day budget burn)
    1x   → ticket (30-day budget burn)

Recording rules pre-compute expensive PromQL on a schedule
   → dashboards stay fast at scale.

Whole point: shipping speed and reliability become measurable
             trade-offs instead of opinions.
```
