# Copyright (c) 2026 Taras Bulubas. All rights reserved.
# Use requires prior written permission; see LICENSE.

"""Independent optimality check: enumerate every assignment of a tiny instance."""

from __future__ import annotations

import itertools

from slot_capacity import Objective, SlotInstance
from slot_capacity.solution import plan_cost


def exhaustive(instance: SlotInstance, objective: Objective) -> float:
    """Best objective value over all feasible assignments (slot or parking per flight)."""
    grid = instance.slots
    options = [
        [None, *(s.index for s in grid if s.end > instance.now and s.end > f.planned and s.capacity > 0)]
        for f in instance.flights
    ]
    best = float("inf")
    for choice in itertools.product(*options):
        used: dict[int, int] = {}
        for k in choice:
            if k is not None:
                used[k] = used.get(k, 0) + 1
        if any(n > grid[k].capacity for k, n in used.items()):
            continue
        slots = {f.name: k for f, k in zip(instance.flights, choice)}
        best = min(best, plan_cost(instance, slots, objective))
    return best
