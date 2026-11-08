# Problem statement — departure slot capacity

Departures of an airport compete for departure slots of limited capacity.
At the planning moment **NOW** the plan assigns every flight a slot — or a
parking slot when none is left — so that flights are delayed as little as
possible, individually and in total, and no single flight is delayed
heavily so that others can go on time.

## Input

- **NOW** — the planning moment, `HH:MM`.
- **Flights** — each with its planned departure time **T(p) ≥ NOW**, `HH:MM`.
- **Slots** — 10 minutes long, aligned to the full hour (06:00, 06:10, …).
  The slot grid starts at the beginning of the hour that contains NOW and
  ends at a full hour, the end of the planning window.
- **Capacity** — the number of departures per slot: one default value and
  overrides for individual slots (e.g. 1 during a runway inspection, 0 for a
  closure).
- **Parking slots** — unlimited capacity; a parked flight counts as
  departing a given *parking delay* after the end of the window.

## Rules

1. Every flight gets exactly one slot or a parking slot.
2. A slot takes at most its capacity of departures.
3. No flight departs before its planned time T(p): it may only take the slot
   that contains T(p) or a later one.
4. **NOW is a hard limit.** Nothing is planned before NOW: every planned
   time T(p) and every sequenced candidate T(s) is at least NOW; slots that
   are over before NOW are not available.
5. The **sequenced time T(s)** of a flight in a slot is the slot start, but
   not before T(p) and not before NOW. The delay is `d = T(s) − T(p) ≥ 0`.

## Objective

Minimise the sum of the delay costs `f(d)` of all flights. Two costs are
compared:

| cost | formula | |
|---|---|---|
| quadratic | `d²` | the classic choice |
| falling trees | `d / (1 + q/τ)` | linear, `q = T(p) − NOW ≥ 0` the lead time, `τ` the time scale |

Both are 0 for `d ≤ 0`. Background and the reasons for the falling trees
model: [objective-functions.md](objective-functions.md); the model:
[mip-model.md](mip-model.md).

## Open points

- Parking penalty: here a parked flight counts as departing `parking delay`
  minutes after the end of the window. To be replaced by the original rule.
- Time scale `τ` of the falling trees (`τ = 1` minute gives `d / (1 + q)`).

---

© 2026 Taras Bulubas. All rights reserved. See [LICENSE](../LICENSE).
