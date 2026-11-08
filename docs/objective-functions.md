# Objective functions for departure delay — alternatives

Working note. The exact problem is defined later in
`problem-statement.md`; this note collects the options for the objective
and what each of them does to a departure plan.

## Setting

- departures (flights) `i = 1..n`, each with a planned time `p_i` (e.g.
  the scheduled departure) and a weight `w_i`
- time slots `k` with a departure capacity `C_k` (possibly several capacity
  layers, e.g. per 10 min and per 60 min)
- **parking slots**: an overflow with unlimited capacity for departures that
  do not get a regular slot within the planning window
- sequenced time `s_i`, individual delay `d_i = s_i - p_i`

Generic objective: `min Σ_i w_i · f(d_i)` over **all** departures of the
planning window, with a penalty shape `f`, plus possibly a global term
(`max_i d_i`, a count, a fairness measure).

**Every shape is zero for `d < 0`**, for every departure: a departure
sequenced before its planned time costs nothing (or is excluded by
constraints). All formulas below are meant as `f(max(d, 0))`.

## Why not quadratic: the long planning window

The main reason to replace the quadratic penalty `d²` is **numerical
stability**.

The objective sums over every departure of the window, near-term and far
ahead. When the window is long, the terms differ by orders of magnitude
(time `0` is the moment of planning, `p` the planned departure in minutes):

| departure | `p` | delay `d` | `d²` | falling trees `d/(1+p)` | `d·arctan(d/15)` |
|---|---:|---:|---:|---:|---:|
| next 30 min | 15 | 5 | 25 | 0.31 | 1.6 |
| in 2 hours | 120 | 30 | 900 | 0.25 | 33 |
| in 8 hours | 480 | 120 | 14 400 | 0.25 | 174 |
| late in a 24 h window | 840 | 600 | 360 000 | 0.71 | 927 |
| parking slot | | "∞" | must exceed every other term | open | open |

With the quadratic penalty, weights that differ by another order of
magnitude push the range of objective coefficients to 6–7 orders of
magnitude. Consequences:

- **The relative gap swallows the near term.** A MIP stops at a relative gap
  of e.g. `10⁻⁴`. With an objective around `10⁷`, that is an absolute
  tolerance of `10³` — more than the whole cost of a 30-minute delay on a
  near-term departure (`30² = 900`). The solver reports "optimal" while the
  part of the plan that is executed first is not optimised at all.
- **The far future decides the near term.** The largest terms belong to
  departures far ahead, whose times are only provisional and will be
  replanned anyway, or which end on parking slots.
- **Tolerances and scaling.** LP optimality and feasibility tolerances are
  relative; a wide coefficient range makes the LP badly scaled and the
  results depend on solver settings.
- **Parking needs the biggest number in the model.** A parking slot is an
  "infinite" delay. Under `d²` its penalty must exceed every in-window cost,
  i.e. be at least `(window length)²`, and it becomes the dominant
  coefficient of the whole model.

## Falling trees model

The alternative (Taras Bulubas, departure planning 2013–2016) stays
**linear** in the sequenced time, but a later planned departure gets a
smaller coefficient:

```
G = Σ_i f(p_i, s_i),     f(p, s) = max(s - p, 0) / (1 + p)
```

with `p` the planned and `s` the sequenced departure time, measured from
the moment of planning. Every departure is a straight line rising from its
planned time; the later it is planned, the more it leans towards the
ground — like a forest of trees felled by a blast, the farther from the
centre the flatter. The lean angle of tree `i` is
`α_i = arctan(1/(1 + p_i))`, and `α_0 > α_1 > α_2 > …`.

Properties:

- **Linear objective.** No curvature, no PWL, no binaries for the
  objective: LP-friendly in every model type, including continuous time.
- **The slope is the pressure.** `∂f/∂s = 1/(1 + p)` is constant per
  departure: what one more minute costs, i.e. how hard the departure presses
  on an earlier slot. Near-term departures press hardest.
- **Relative delay.** `d/(1 + p)` measures the delay against the time left
  until the planned departure: 10 minutes matter for a flight due in 10
  minutes, hardly for one due in 8 hours, whose time is provisional anyway.
  It is hyperbolic discounting of the delay cost over the planning window.
- **Bounded slopes.** The slopes lie in `[1/(1 + H), 1]` for a window of
  length `H`; the far future cannot outweigh the near term. The cost
  coefficients of the time-indexed model, `d/(1 + q)`, still grow with the
  window, but linearly (largest for a flight due now and parked), not with
  its square.
- **NOW is a hard limit.** No flight is planned or sequenced before NOW, so
  `q = T(p) − NOW ≥ 0` and the slopes differ for different planned times.
- **Planned order is strictly optimal** (one capacity layer). Exchange
  argument with `p_a < p_b`, slots `s < u`: crossed minus in-order is
  `(1/(1+p_a) − 1/(1+p_b)) · (u − s) > 0`. So the model is first planned,
  first served like the quadratic one, but strictly — the degeneracy of the
  plain linear model is gone.
- **Continuous, but with a kink.** Zero for `d < 0`, slope `1/(1 + p)` from
  the first minute: the pressure jumps at `d = 0`.
- **Units matter.** `1 + p` depends on the time unit (minutes vs seconds).
  A time scale `τ`, `f = (s − p)/(1 + p/τ)`, makes it unit-free and sets
  how fast the trees fall.

## Alternative: `d · arctan(d/τ)`

```
g(d) = d · arctan(d/τ)   for d ≥ 0,     g(d) = 0   for d < 0
```

Derivatives, with `x = d/τ`:

```
g'(d)  = arctan(x) + x / (1 + x²)          pressure, rises from 0 to π/2
g''(d) = (2/τ) / (1 + x²)²   > 0           strictly convex on d ≥ 0
```

Behaviour:

- **Quadratic start.** For `d ≪ τ`: `arctan(x) ≈ x`, so `g ≈ d²/τ`.
- **Linear tail.** For `d ≫ τ`: `g ≈ (π/2)·d − τ`, a straight line with
  slope `π/2`.
- `τ` is the knee between the two regimes. Without `τ` (`d·arctan(d)` in
  minutes) the quadratic part ends after about one minute.
- It is the smooth counterpart of the Huber penalty (quadratic near zero,
  linear far out), like the pseudo-Huber `τ²(√(1 + x²) − 1)` or
  `log cosh`.

Properties:

- **Smooth at zero.** `g(0) = 0` and `g'(0) = 0`: continuous and
  continuously differentiable, also with the zero branch for `d < 0` — no
  kink, no jump of the pressure.
- **Bounded pressure.** `g'` increases from 0 to `π/2` and never exceeds
  it; with `d²` the pressure `2d` grows without limit.
- **Convex → planned order.** By the exchange argument below, first
  planned, first served stays optimal. In the linear tail `g''` decays like
  `1/d⁴`, so for long delays the preference becomes weak, close to the
  degenerate linear case.
- **Linear growth, not bounded.** The range of terms grows with the window
  (`927` at 600 min vs `360 000` for `d²`) — far better than quadratic, but
  not bounded like falling trees.
- **First minutes are almost free.** `g'(0) = 0`: small delays carry almost
  no pressure, so they are spread freely. Falling trees presses from the
  first minute.

The two ideas combine: `g(d)/(1 + p)` — convex near zero, linear tail,
falling slopes for later planned departures.

## The two departures of the hand sketch

Planned at 10 and 20, slots at 20 and 30:

| shape | sol 1: in order (10→20, 20→30) | sol 2: crossed (10→30, 20→20) |
|---|---:|---:|
| linear `d` | 20 | 20 (tie) |
| quadratic `d²` | **200** | 400 |
| falling trees `d/(1+p)` | **1.39** | 1.82 |
| `d·arctan(d/15)` | **11.76** | 18.55 |

## The shape decides who waits

With one capacity layer and equal weights, **the total delay depends only on
which slots are used, not on who gets them**. As long as the plan uses the
earliest possible slots (in the experiment below every shape does), the shape
of `f` does not change *how much* delay there is, only *who* takes it.

Exchange argument: departures `a` and `b` with `p_a < p_b` and slots `s < u`,
both usable by both. The two pairings have delays `{s - p_a, u - p_b}` (in
order) and `{u - p_a, s - p_b}` (crossed). Both pairs have the same sum and
the crossed pair is more spread, so

- `f` **convex** (quadratic, `d·arctan(d/τ)`, `d^q` with `q > 1`): the
  in-order pairing is never worse → **first planned, first served** is
  optimal;
- `f` **concave** (`sqrt`, `d^q` with `q < 1`, a threshold count): the
  crossed pairing is never worse → later departures jump ahead and a few
  early ones absorb the delay;
- `f` **linear**: indifferent → massive degeneracy, the solver returns an
  arbitrary order. Falling trees breaks the tie by the slopes, not by
  curvature.

### Scratch experiment

15 departures in a wave, one slot every 5 min, time-indexed assignment
solved with SCIP:

| shape                     | Σ delay | max | # > 15 min | overtakes |
|---------------------------|--------:|----:|-----------:|----------:|
| linear `d`                |     330 |  35 |         10 |    0 (\*) |
| quadratic `d²`            |     330 |  35 |         10 |         0 |
| falling trees `d/(1+p)`   |     330 |  35 |         10 |         0 |
| `d·arctan(d/15)`          |     330 |  35 |         10 |         0 |
| count `d > 15` (step)     |     330 |  70 |          4 |        42 |

(\*) by chance; any order is optimal for the linear shape.

Same total delay everywhere. The convex shapes and falling trees keep the
planned order and cap the worst delay at 35 min; the step pushes the three
earliest departures to 60–70 min to keep most of the others punctual.

## Catalogue of shapes

All shapes are `0` for `d < 0`.

| shape | formula | curvature | what it rewards |
|---|---|---|---|
| linear | `d` | — | total delay only; degenerate |
| quadratic | `d²` | convex | spreading the delay, planned order, small max; unbounded |
| falling trees | `d/(1 + p)` | linear per departure, slope falls with `p` | planned order strictly, bounded, LP-friendly |
| `d·arctan(d/τ)` | `d·arctan(d/τ)` | strictly convex; quadratic start, linear tail | planned order, smooth at 0, bounded pressure |
| power | `d^q` | convex for `q > 1`, concave for `q < 1` | one knob from fair to punctual |
| piecewise linear tiers | e.g. slopes 1 / 3 / 10 after 15 / 60 min | convex | quadratic-like, LP-friendly; unbounded |
| convex then capped | `min(d², M)` or convex PWL up to a cap | convex, then flat | fair near term, bounded far ahead |
| threshold count | `[d > θ]` | step | punctuality KPI exactly; very degenerate |
| max | `max_i d_i` | — | worst case only; degenerate for everyone else |
| lexicographic | `max`, then `Σ f(d)` | — | worst case first, then efficiency |
| OWA / leximin | sorted delays (largest first) with decreasing weights | convex | equity; linearisable |

Points to settle:

- **Requirements on the delay cost.** It should be continuous and
  increasing in the delay; where it is convex and where concave has
  distinct effects on the plan (to be worked out).
- **Whose objective?** A per-minute cost that grows with delay (knock-on
  delays, missed connections, compensation steps) is convex. A punctuality
  KPI (share of departures within θ minutes) is a step, i.e. concave beyond
  θ. They pull in opposite directions.
- **Global vs individual.** `Σ f(d_i)` with convex `f` already acts as a
  fairness term; an explicit `max` or OWA term makes it explicit and
  controllable.
- **Scale and weights.** `d²` lets one long delay dominate everything;
  falling trees and `d·arctan` need a time scale `τ`. All interact with the
  weights `w_i`.

## How each shape fits each model type

| model | linear / falling trees / convex PWL | quadratic | `d·arctan(d/τ)` | step / concave |
|---|---|---|---|---|
| **time-indexed MILP** `x_ik` | coefficient `w_i f(k - p_i)` | same, precomputed | same, precomputed | same, precomputed — the shape is free |
| **continuous-time MILP** `s_i` + big-M sequencing | linear; convex PWL as LP epigraph `z_i ≥ a_j d_i + b_j` | MIQP (convex) or PWL epigraph | PWL epigraph / tangent cuts, no binaries (convex) | PWL with SOS2 / binaries; weak LP bound |
| **CP / CP-SAT** integer `d_i` | linear | `AddMultiplicationEquality` | `AddElement` table, scaled to integers | `AddElement` table |

Observations:

- In the **time-indexed** model every shape is just a cost coefficient.
  With a single capacity layer the constraint matrix is a bipartite
  b-matching (totally unimodular): the LP relaxation is integral and the
  problem is a min-cost flow, **whatever the shape**. Nested or rolling
  capacity windows break this property. Parking slots are just one more
  column per departure.
- In the **continuous-time** model the shape matters: linear and convex
  shapes stay LP-friendly (falling trees needs nothing at all), concave
  ones need binaries and give weak bounds.
- In **CP-SAT** any shape on an integer delay is a table, but the
  coefficients must be integers: the range of the table grows like `d²`
  for quadratic and like `d` for `d·arctan`.

## Experiments to run

On the same instances, for each shape:

- Σ delay, max delay, # over θ, # overtakes (order changes), OWA value,
  delay histogram
- near-term vs far-ahead: how the result in the first hour changes when the
  window grows from 2 h to 24 h, at a fixed relative gap
- coefficient range, solve time and gap for time-indexed MILP,
  continuous-time MILP, CP-SAT
- the Pareto front Σ delay vs max delay, and where each shape lands on it

---

© 2026 Taras Bulubas. All rights reserved. See [LICENSE](../LICENSE).
