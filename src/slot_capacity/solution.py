# Copyright (c) 2026 Taras Bulubas. All rights reserved.
# Use requires prior written permission; see LICENSE.

"""A departure plan, its independent check and its key figures.

verify() does not use the model: it recomputes everything from the
instance and the slot of each flight.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from slot_capacity.instance import Flight, SlotInstance, format_time
from slot_capacity.objective import FALLING_TREES, QUADRATIC, Objective


@dataclass
class Plan:
    """The slot of every flight (slot index, or None for a parking slot).

    Attributes:
        objective: the delay cost the plan was optimised for.
        status: solver status, e.g. "optimal".
        value: objective value reported by the solver, None without a plan.
        bound: best bound reported by the solver.
        slots: flight name → slot index, None = parked.
        seconds: solve time.
        variables, constraints: model size.
    """

    objective: Objective
    status: str
    value: float | None = None
    bound: float | None = None
    slots: dict[str, int | None] = field(default_factory=dict)
    seconds: float = 0.0
    variables: int = 0
    constraints: int = 0

    @property
    def has_plan(self) -> bool:
        return bool(self.slots)


@dataclass(frozen=True)
class Row:
    """One flight of a plan."""

    flight: Flight
    slot: int | None
    sequenced: int
    delay: int
    cost: float
    pressure: float

    @property
    def parked(self) -> bool:
        return self.slot is None


def rows(instance: SlotInstance, plan: Plan) -> list[Row]:
    """The flights of a plan in planned order."""
    slots = instance.slots
    out = []
    for f in instance.sorted_flights:
        k = plan.slots[f.name]
        slot = None if k is None else slots[k]
        delay = instance.delay(f, slot)
        q = instance.lead_time(f)
        out.append(Row(f, k, instance.sequenced_time(f, slot), delay,
                       plan.objective.cost(delay, q), plan.objective.pressure(delay, q)))
    return out


def plan_cost(instance: SlotInstance, slots: dict[str, int | None], objective: Objective) -> float:
    """Objective value of an assignment, recomputed from the instance."""
    grid = instance.slots
    total = 0.0
    for f in instance.flights:
        k = slots[f.name]
        total += objective.cost(instance.delay(f, None if k is None else grid[k]), instance.lead_time(f))
    return total


def verify(instance: SlotInstance, plan: Plan, tolerance: float = 1e-6) -> list[str]:
    """Errors of a plan; an empty list means the plan is valid."""
    errors: list[str] = []
    grid = instance.slots
    names = {f.name for f in instance.flights}
    if set(plan.slots) != names:
        missing = sorted(names - set(plan.slots))
        extra = sorted(set(plan.slots) - names)
        if missing:
            errors.append(f"flights without a slot: {', '.join(missing)}")
        if extra:
            errors.append(f"unknown flights: {', '.join(extra)}")
        return errors

    used = [0] * len(grid)
    for f in instance.flights:
        k = plan.slots[f.name]
        if k is None:
            continue
        if not 0 <= k < len(grid):
            errors.append(f"{f.name}: slot index {k} out of range")
            continue
        slot = grid[k]
        if slot.end <= instance.now:
            errors.append(f"{f.name}: slot {slot.label} is already over at NOW {format_time(instance.now)}")
        if slot.end <= f.planned:
            errors.append(f"{f.name}: slot {slot.label} ends before the planned time {format_time(f.planned)}")
        used[k] += 1
    for slot, n in zip(grid, used):
        if n > slot.capacity:
            errors.append(f"slot {slot.label}: {n} departures, capacity {slot.capacity}")

    if plan.value is not None:
        value = plan_cost(instance, plan.slots, plan.objective)
        if abs(value - plan.value) > tolerance * max(1.0, abs(value)):
            errors.append(f"objective {plan.value:g} reported, {value:g} recomputed")
    return errors


@dataclass(frozen=True)
class Metrics:
    """Key figures of a plan, independent of the objective it was optimised for."""

    total_delay: int
    max_delay: int
    delayed: int
    parked: int
    overtakes: int
    quadratic: float
    falling_trees: float


def overtakes(instance: SlotInstance, slots: dict[str, int | None]) -> int:
    """Pairs of flights where the later planned one departs strictly earlier."""
    grid = instance.slots
    times = [
        (f.planned, instance.sequenced_time(f, None if slots[f.name] is None else grid[slots[f.name]]))
        for f in instance.flights
    ]
    return sum(1 for pa, sa in times for pb, sb in times if pa < pb and sa > sb)


def metrics(instance: SlotInstance, plan: Plan, tau: float = 1.0) -> Metrics:
    rs = rows(instance, plan)
    delays = [r.delay for r in rs]
    return Metrics(
        total_delay=sum(delays),
        max_delay=max(delays),
        delayed=sum(1 for d in delays if d > 0),
        parked=sum(1 for r in rs if r.parked),
        overtakes=overtakes(instance, plan.slots),
        quadratic=plan_cost(instance, plan.slots, Objective(QUADRATIC)),
        falling_trees=plan_cost(instance, plan.slots, Objective(FALLING_TREES, tau)),
    )
