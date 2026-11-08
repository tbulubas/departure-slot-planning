# The time-indexed MILP

The model of [problem-statement.md](problem-statement.md), implemented in
[`src/slot_capacity/model.py`](../src/slot_capacity/model.py) and solved
with SCIP (OR-Tools). Numbers in the code comments refer to this page.

## 1. Sets and data

| symbol | meaning |
|---|---|
| `i ∈ F` | flights |
| `k ∈ K` | 10-minute slots of the window, start `t_k` |
| `P` | the parking slot, unlimited capacity, time `t_P = window end + parking delay` |
| `K_i ⊆ K` | slots flight `i` may take: `t_k + 10 > T(p)_i` and `t_k + 10 > NOW` and `C_k > 0` |
| `C_k` | capacity of slot `k` |
| `s_ik = max(t_k, T(p)_i, NOW)` | sequenced time of flight `i` in slot `k` |
| `d_ik = s_ik − T(p)_i ≥ 0` | its delay; `d_iP = t_P − T(p)_i` |
| `q_i = T(p)_i − NOW ≥ 0` | lead time of flight `i`; NOW is a hard limit, no `T(p)` before it |

## 2. Cost coefficients

The delay cost is computed in advance for every pair, so its shape does
not change the structure of the model:

```
(1)  c_ik = f(d_ik, q_i)        for k ∈ K_i
(2)  c_iP = f(d_iP, q_i)
```

with

```
quadratic       f(d, q) = d²
falling trees   f(d, q) = d / (1 + q/τ)
```

## 3. Variables

`x_ik ∈ {0, 1}` — flight `i` departs in slot `k ∈ K_i ∪ {P}`.

## 4. Constraints

```
(3)  Σ_{k ∈ K_i ∪ {P}} x_ik = 1         for every flight i
(4)  Σ_{i : k ∈ K_i}   x_ik ≤ C_k       for every slot k ∈ K
```

## 5. Objective

```
(5)  min  Σ_i Σ_{k ∈ K_i ∪ {P}} c_ik · x_ik
```

## 6. Properties

- **Totally unimodular.** (3) and (4) form a bipartite b-matching (flights ×
  slots), so the LP relaxation already has integral optimal solutions — for
  *any* cost, quadratic or falling trees. SCIP solves it at the root node.
  Additional rows (rolling capacity windows, several runways) can break
  this property.
- **Planned order.** With flights interchangeable in the slots (one
  capacity layer), the quadratic cost (strictly convex) and the falling
  trees cost (slope `1/(1 + q/τ)` falling with `q`) both make *first
  planned, first served* optimal: swapping two crossed flights never
  increases the cost. Only flights with the same planned time tie, and
  they are interchangeable anyway.
- **Coefficient range.** The largest coefficient belongs to the longest
  delay: it grows with the square of the window length for the quadratic
  cost and linearly for falling trees, while the smallest positive
  coefficient of falling trees shrinks with the lead time.

## 7. Slot prices — the pressure on a slot

The price of slot `k` is what one more departure in that slot is worth: the
drop of the optimal cost (5) when `C_k` grows by one
(`slot_prices(method="extra")`). It equals a dual value of the capacity
constraint (4) (`method="dual"`); in degenerate cases the dual is not unique
and lies between the value of one more and one less departure.

The difference of the prices of two consecutive full slots is the cost of
moving the flight at their border by one slot — slot length × its slope for
falling trees, `f(d) − f(d − 10)` for the quadratic cost. The price of a
slot therefore adds up the pressure of all flights queued behind it.

---

© 2026 Taras Bulubas. All rights reserved. See [LICENSE](../LICENSE).
