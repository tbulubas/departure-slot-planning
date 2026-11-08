# Copyright (c) 2026 Taras Bulubas. All rights reserved.
# Use requires prior written permission; see LICENSE.

import random

import pytest
from exhaustive import exhaustive

from slot_capacity import (
    FALLING_TREES,
    OBJECTIVES,
    Flight,
    QUADRATIC,
    Objective,
    SlotInstance,
    coefficient_range,
    example_instance,
    metrics,
    slot_prices,
    solve,
    verify,
)


def tiny_instance(seed: int) -> SlotInstance:
    """3–5 flights in one hour, capacity 0–2 per slot, a short window."""
    rng = random.Random(seed)
    now = rng.choice([0, 3, 12])
    planned = [rng.randrange(now, 50) for _ in range(rng.randint(3, 5))]
    caps = {k * 10: rng.randint(0, 2) for k in range(6) if rng.random() < 0.5}
    return SlotInstance(
        now=now,
        flights=tuple(Flight(f"F{i}", p) for i, p in enumerate(planned)),
        default_capacity=1,
        capacities=tuple(sorted(caps.items())),
        end=60,
        parking_delay=rng.choice([0, 30]),
    )


@pytest.mark.parametrize("seed", range(25))
@pytest.mark.parametrize("name", OBJECTIVES)
def test_optimal_against_exhaustive_search(seed, name):
    inst = tiny_instance(seed)
    objective = Objective(name, tau=rng_tau(seed))
    plan = solve(inst, objective)
    assert plan.status == "optimal"
    assert verify(inst, plan) == []
    assert plan.value == pytest.approx(exhaustive(inst, objective), rel=1e-6, abs=1e-6)


def rng_tau(seed: int) -> float:
    return (1.0, 5.0, 30.0)[seed % 3]


@pytest.mark.parametrize("name", OBJECTIVES)
def test_example_keeps_the_planned_order(name):
    inst = example_instance()
    plan = solve(inst, Objective(name))
    assert plan.status == "optimal"
    assert verify(inst, plan) == []
    m = metrics(inst, plan)
    assert m.overtakes == 0
    assert m.parked == 0


def test_both_objectives_give_the_same_delays_on_the_example():
    inst = example_instance()
    q = metrics(inst, solve(inst, Objective(QUADRATIC)))
    ft = metrics(inst, solve(inst, Objective(FALLING_TREES)))
    assert (q.total_delay, q.max_delay, q.delayed) == (ft.total_delay, ft.max_delay, ft.delayed)


def test_parking_when_capacity_runs_out():
    inst = SlotInstance.create("06:00", ["06:00"] * 4, default_capacity=0, capacities={"06:00": 1, "06:10": 1},
                               end="07:00")
    plan = solve(inst, Objective(QUADRATIC))
    assert verify(inst, plan) == []
    assert metrics(inst, plan).parked == 2


def test_verify_finds_errors():
    inst = SlotInstance.create("06:00", {"A": "06:05", "B": "06:06"}, default_capacity=1, end="07:00")
    plan = solve(inst, Objective(QUADRATIC))
    plan.slots = {"A": 0, "B": 0}
    assert any("capacity" in e for e in verify(inst, plan))
    plan.slots = {"A": 0}
    assert any("without a slot" in e for e in verify(inst, plan))


def test_slot_prices_are_the_pressure_of_the_queue():
    # four flights due at NOW, one per slot: each slot price is the cost of
    # shifting the queue behind it by one slot
    inst = SlotInstance.create("06:00", ["06:00"] * 4, default_capacity=1, end="07:00")
    for method in ("extra", "dual"):
        ft = slot_prices(inst, Objective(FALLING_TREES), method=method)
        # lead time 0 → slope 1; the price steps are slot length × slope
        assert [ft[k] - ft[k + 1] for k in range(3)] == pytest.approx([10.0, 10.0, 10.0])
        assert ft[4] == pytest.approx(0.0)
        q = slot_prices(inst, Objective(QUADRATIC), method=method)
        # quadratic: steps are f(d) − f(d − 10) of the flight at the boundary
        assert [q[k] - q[k + 1] for k in range(3)] == pytest.approx([100.0, 300.0, 500.0])
    # one more departure in the last used slot helps nobody
    assert slot_prices(inst, Objective(FALLING_TREES))[3] == pytest.approx(0.0)
    assert slot_prices(inst, Objective(FALLING_TREES))[0] == pytest.approx(30.0)


def test_coefficients_grow_quadratically_vs_linearly_with_the_window():
    # window 2 h → 12 h, parking right after the window: the longest delay grows 6×
    short = SlotInstance.create("06:00", ["06:00", "06:30"], end="08:00", parking_delay=0)
    long = SlotInstance.create("06:00", ["06:00", "06:30"], end="18:00", parking_delay=0)
    rq = [coefficient_range(i, Objective(QUADRATIC)).largest for i in (short, long)]
    rf = [coefficient_range(i, Objective(FALLING_TREES)).largest for i in (short, long)]
    assert rq[1] / rq[0] == pytest.approx(36.0)
    assert rf[1] / rf[0] == pytest.approx(6.0)
