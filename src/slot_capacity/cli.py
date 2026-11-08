# Copyright (c) 2026 Taras Bulubas. All rights reserved.
# Use requires prior written permission; see LICENSE.

"""Command line interface: plan departures with both delay costs and compare them."""

from __future__ import annotations

import argparse
import sys

from slot_capacity.instance import EXAMPLE_CAPACITIES, EXAMPLE_FLIGHTS, SlotInstance, format_time
from slot_capacity.model import coefficient_range, slot_prices, solve
from slot_capacity.objective import OBJECTIVES, Objective
from slot_capacity.solution import Plan, metrics, rows, verify


def parse_capacities(text: str) -> dict[str, int]:
    """'06:30=1,06:40=0' → {'06:30': 1, '06:40': 0}."""
    out: dict[str, int] = {}
    for item in filter(None, (part.strip() for part in text.split(","))):
        slot, sep, value = item.partition("=")
        if not sep:
            raise ValueError(f"capacity must be SLOT=N, got {item!r}")
        out[slot.strip()] = int(value)
    return out


def format_instance(instance: SlotInstance) -> str:
    overrides = ", ".join(f"{format_time(t)}={c}" for t, c in instance.capacities) or "none"
    return (
        f"NOW {format_time(instance.now)}, window {format_time(instance.start)}-{format_time(instance.window_end)},"
        f" {len(instance.flights)} flights, {len(instance.slots)} slots of 10 min,"
        f" capacity {instance.default_capacity} per slot (overrides: {overrides}),"
        f" parking counts as departing at {format_time(instance.parking_time)}"
    )


def format_plan(instance: SlotInstance, plan: Plan, prices: dict[int, float] | None = None) -> str:
    lines = [f"== {plan.objective.text}: {plan.status}"
             f" ({plan.variables} variables, {plan.constraints} constraints, {plan.seconds:.2f} s)"]
    if not plan.has_plan:
        return "\n".join(lines)
    lines.append(f"{'flight':<7}{'T(p)':>6}{'slot':>7}{'T(s)':>7}{'delay':>7}{'cost':>11}{'pressure':>10}")
    grid = instance.slots
    for r in rows(instance, plan):
        slot = "park" if r.slot is None else grid[r.slot].label
        lines.append(
            f"{r.flight.name:<7}{format_time(r.flight.planned):>6}{slot:>7}{format_time(r.sequenced):>7}"
            f"{r.delay:>7}{r.cost:>11.4g}{r.pressure:>10.4g}"
        )
    m = metrics(instance, plan, plan.objective.tau)
    lines.append(
        f"objective {plan.value:.6g}; total delay {m.total_delay} min, max {m.max_delay} min,"
        f" {m.delayed} delayed, {m.parked} parked, {m.overtakes} overtakes"
    )
    used = {k: 0 for k in range(len(grid))}
    for k in plan.slots.values():
        if k is not None:
            used[k] += 1
    cells = []
    for slot in grid:
        if instance.is_past(slot):
            continue
        cell = f"{slot.label} {used[slot.index]}/{slot.capacity}"
        if prices is not None and slot.index in prices:
            cell += f" ({prices[slot.index]:.3g})"
        cells.append(cell)
    title = "slots used/capacity (price)" if prices is not None else "slots used/capacity"
    lines.append(f"{title}: " + ", ".join(cells))
    errors = verify(instance, plan)
    lines.append("check: OK" if not errors else "check FAILED:\n  " + "\n  ".join(errors))
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="slot-capacity", description=__doc__)
    p.add_argument("--example", action="store_true", help="the morning bank of 24 departures")
    p.add_argument("--now", default="06:00", help="planning moment NOW, HH:MM (default 06:00)")
    p.add_argument("--flights", help="planned departures, comma separated HH:MM")
    p.add_argument("--capacity", type=int, default=3, help="departures per 10-minute slot (default 3)")
    p.add_argument("--slot-capacity", default="", metavar="SLOT=N,...",
                   help="capacity overrides, e.g. 06:30=1,06:40=0")
    p.add_argument("--end", help="end of the window, a full hour HH:00 (default: automatic)")
    p.add_argument("--parking-delay", type=int, default=60,
                   help="a parked flight counts as departing this many minutes after the window (default 60)")
    p.add_argument("--objective", choices=[*OBJECTIVES, "both"], default="both")
    p.add_argument("--tau", type=float, default=1.0, help="time scale of the falling trees in minutes (default 1)")
    p.add_argument("--prices", action="store_true", help="also show the slot prices (LP duals)")
    p.add_argument("--time-limit", type=float, help="seconds per solve")
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    try:
        if args.flights:
            flights = [t.strip() for t in args.flights.split(",") if t.strip()]
            capacities = parse_capacities(args.slot_capacity)
        elif args.example:
            flights = list(EXAMPLE_FLIGHTS)
            capacities = {**EXAMPLE_CAPACITIES, **parse_capacities(args.slot_capacity)}
        else:
            sys.exit("give --flights or --example")
        instance = SlotInstance.create(
            args.now, flights, default_capacity=args.capacity, capacities=capacities,
            end=args.end, parking_delay=args.parking_delay,
        )
    except ValueError as error:
        sys.exit(f"invalid input: {error}")

    print(format_instance(instance))
    names = OBJECTIVES if args.objective == "both" else (args.objective,)
    for name in names:
        objective = Objective(name, args.tau)
        plan = solve(instance, objective, time_limit=args.time_limit)
        prices = slot_prices(instance, objective) if args.prices else None
        print()
        print(format_plan(instance, plan, prices))
        r = coefficient_range(instance, objective)
        print(f"objective coefficients {r.smallest:.3g} .. {r.largest:.3g} (ratio {r.ratio:.3g})")
