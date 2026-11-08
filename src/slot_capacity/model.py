# Copyright (c) 2026 Taras Bulubas. All rights reserved.
# Use requires prior written permission; see LICENSE.

"""The time-indexed MILP of docs/mip-model.md, solved with SCIP.

Numbers in comments refer to docs/mip-model.md. x[i, k] = 1 when flight i
departs in slot k, y[i] = 1 when it is parked.

slot_prices() solves the LP relaxation with GLOP to read the dual values of
the capacity constraints (4): the price of a slot, i.e. the pressure of the
flights queued for it. With one capacity layer the LP has integral optima,
so the prices belong to the optimal plan.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from ortools.linear_solver import pywraplp

from slot_capacity.instance import Slot, SlotInstance
from slot_capacity.objective import Objective
from slot_capacity.solution import Plan

_STATUS = {
    pywraplp.Solver.OPTIMAL: "optimal",
    pywraplp.Solver.FEASIBLE: "feasible",
    pywraplp.Solver.INFEASIBLE: "infeasible",
    pywraplp.Solver.NOT_SOLVED: "not solved",
}


def costs(instance: SlotInstance, objective: Objective) -> dict[tuple[str, int | None], float]:
    """(1)–(2): c[i, k] = f(d_ik) for every eligible pair, c[i, None] for parking."""
    out: dict[tuple[str, int | None], float] = {}
    for f in instance.flights:
        q = instance.lead_time(f)
        for slot in instance.slots:
            if instance.eligible(f, slot):
                out[f.name, slot.index] = objective.cost(instance.delay(f, slot), q)
        out[f.name, None] = objective.cost(instance.delay(f, None), q)
    return out


@dataclass(frozen=True)
class CoefficientRange:
    """Smallest positive and largest objective coefficient of the model."""

    smallest: float
    largest: float

    @property
    def ratio(self) -> float:
        return self.largest / self.smallest if self.smallest > 0 else float("inf")


def coefficient_range(instance: SlotInstance, objective: Objective) -> CoefficientRange:
    values = [c for c in costs(instance, objective).values() if c > 0]
    return CoefficientRange(min(values), max(values)) if values else CoefficientRange(0.0, 0.0)


def _build(solver: pywraplp.Solver, instance: SlotInstance, objective: Objective, integer: bool):
    c = costs(instance, objective)
    var = solver.BoolVar if integer else (lambda name: solver.NumVar(0.0, 1.0, name))
    x = {key: var(f"x[{key[0]},{'P' if key[1] is None else key[1]}]") for key in c}

    # (3) every flight gets exactly one slot or a parking slot
    for f in instance.flights:
        solver.Add(sum(v for (name, _), v in x.items() if name == f.name) == 1, f"assign[{f.name}]")

    # (4) slot capacity; parking has none
    capacity: dict[int, pywraplp.Constraint] = {}
    for slot in instance.slots:
        users = [v for (_, k), v in x.items() if k == slot.index]
        if users:
            capacity[slot.index] = solver.Add(sum(users) <= slot.capacity, f"capacity[{slot.label}]")

    # (5) total delay cost
    solver.Minimize(sum(c[key] * v for key, v in x.items()))
    return x, capacity


def solve(
    instance: SlotInstance,
    objective: Objective,
    time_limit: float | None = None,
    gap: float | None = None,
) -> Plan:
    """Optimal plan for one objective with SCIP.

    gap: relative MIP gap at which SCIP may stop (None = SCIP's default).
    """
    solver = pywraplp.Solver.CreateSolver("SCIP")
    if solver is None:
        raise RuntimeError("SCIP is not available in this OR-Tools build")
    x, _ = _build(solver, instance, objective, integer=True)
    if time_limit is not None:
        solver.SetTimeLimit(int(time_limit * 1000))
    params = pywraplp.MPSolverParameters()
    if gap is not None:
        params.SetDoubleParam(pywraplp.MPSolverParameters.RELATIVE_MIP_GAP, gap)

    start = time.perf_counter()
    status = solver.Solve(params)
    seconds = time.perf_counter() - start

    plan = Plan(
        objective=objective,
        status=_STATUS.get(status, "error"),
        seconds=seconds,
        variables=solver.NumVariables(),
        constraints=solver.NumConstraints(),
    )
    if status in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        plan.value = solver.Objective().Value()
        plan.bound = solver.Objective().BestBound()
        plan.slots = {name: k for (name, k), v in x.items() if v.solution_value() > 0.5}
    return plan


def slot_prices(instance: SlotInstance, objective: Objective, method: str = "extra") -> dict[int, float]:
    """Price of every usable slot: what one more departure in that slot is worth.

    method "extra" re-solves the LP with the capacity of each slot raised by
    one and returns the saving — well defined and easy to explain. Method
    "dual" returns the dual value of the capacity constraint (4) from one LP
    solve; when the LP is degenerate, any value between the saving of one
    more and the loss of one less departure is a valid dual, and the solver
    picks one of them. Slots that no flight can use have no price.
    """
    if method not in ("extra", "dual"):
        raise ValueError("method must be 'extra' or 'dual'")
    solver = pywraplp.Solver.CreateSolver("GLOP")
    _, capacity = _build(solver, instance, objective, integer=False)
    if solver.Solve() != pywraplp.Solver.OPTIMAL:
        raise RuntimeError("the LP relaxation has no optimal solution")
    if method == "dual":
        # GLOP reports the dual of a ≤ row in a minimisation as ≤ 0
        return {k: max(-row.dual_value(), 0.0) for k, row in capacity.items()}

    base = solver.Objective().Value()
    prices = {}
    for k, row in capacity.items():
        row.SetUb(row.ub() + 1)
        solver.Solve()
        prices[k] = max(base - solver.Objective().Value(), 0.0)
        row.SetUb(row.ub() - 1)
    return prices


def usable_slots(instance: SlotInstance) -> list[Slot]:
    """Slots that at least one flight may take."""
    return [s for s in instance.slots if any(instance.eligible(f, s) for f in instance.flights)]
