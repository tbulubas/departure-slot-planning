# Copyright (c) 2026 Taras Bulubas. All rights reserved.
# Use requires prior written permission; see LICENSE.

"""Pictures of a plan: slot usage, flights pushed into slots, slot prices."""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.figure import Figure

from slot_capacity.instance import HOUR, SLOT_MINUTES, SlotInstance, format_time
from slot_capacity.solution import Plan, rows

ON_TIME = "#2a9d8f"
CAPACITY = "#264653"
PAST = "#e9e9e9"
NOW = "#c1121f"
PRICE = "#6a4c93"
DELAY_MAP = plt.get_cmap("YlOrRd")


def _parking_x(instance: SlotInstance) -> float:
    return instance.window_end + 1.5 * SLOT_MINUTES


def _time_axis(ax, instance: SlotInstance) -> None:
    majors = list(range(instance.start, instance.window_end + 1, 30))
    ax.set_xticks([*majors, _parking_x(instance)])
    ax.set_xticklabels([*(format_time(t) for t in majors), "park"])
    ax.set_xticks(range(instance.start, instance.window_end + 1, SLOT_MINUTES), minor=True)
    ax.set_xlim(instance.start - 2, instance.window_end + 2.5 * SLOT_MINUTES)


def _now_line(ax, instance: SlotInstance, label: bool = False) -> None:
    ax.axvline(instance.now, color=NOW, linestyle="--", linewidth=1.2, zorder=5)
    if label:
        ax.text(instance.now, 1.02, " NOW", color=NOW, transform=ax.get_xaxis_transform(),
                ha="left", va="bottom", fontsize=9, fontweight="bold")


def _shade_past(ax, instance: SlotInstance) -> None:
    for slot in instance.slots:
        if instance.is_past(slot):
            ax.axvspan(slot.start, slot.end, color=PAST, zorder=0, linewidth=0)
    ax.axvspan(instance.window_end, instance.window_end + 2.5 * SLOT_MINUTES, color="#f4f1ea", zorder=0, linewidth=0)


def plot_plan(
    instance: SlotInstance,
    plan: Plan,
    prices: dict[int, float] | None = None,
    title: str | None = None,
    figsize: tuple[float, float] | None = None,
) -> Figure:
    """Slot usage on top, one row per flight (planned ○ → sequenced ■), prices below."""
    rs = rows(instance, plan)
    n = len(rs)
    heights = [1.4, max(2.5, 0.22 * n)] + ([1.4] if prices is not None else [])
    if figsize is None:
        figsize = (11, sum(heights) + 0.9)
    fig, axes = plt.subplots(len(heights), 1, sharex=True, figsize=figsize,
                             gridspec_kw={"height_ratios": heights}, constrained_layout=True)
    ax_cap, ax_fl = axes[0], axes[1]

    # slot usage
    used = [0] * len(instance.slots)
    for r in rs:
        if r.slot is not None:
            used[r.slot] += 1
    parked = sum(1 for r in rs if r.parked)
    _shade_past(ax_cap, instance)
    for slot, u in zip(instance.slots, used):
        ax_cap.bar(slot.start, slot.capacity, width=SLOT_MINUTES, align="edge", fill=False,
                   edgecolor=CAPACITY, linewidth=1.0, zorder=2)
        if u:
            full = u >= slot.capacity
            ax_cap.bar(slot.start + 1, u, width=SLOT_MINUTES - 2, align="edge", zorder=3,
                       color=DELAY_MAP(0.75) if full else ON_TIME)
    if parked:
        ax_cap.bar(_parking_x(instance) - 4, parked, width=8, align="edge", color="#7f7f7f", zorder=3)
    top = max([s.capacity for s in instance.slots] + used + [parked, 1])
    ax_cap.set_ylim(0, top + 0.6)
    ax_cap.set_ylabel("departures\nper slot")
    ax_cap.yaxis.get_major_locator().set_params(integer=True)
    _now_line(ax_cap, instance, label=True)

    # flights
    _shade_past(ax_fl, instance)
    for t in range(instance.start, instance.window_end + 1, SLOT_MINUTES):
        ax_fl.axvline(t, color="#d0d0d0", linewidth=0.6, zorder=1)
    worst = max([r.delay for r in rs] + [SLOT_MINUTES])
    norm = Normalize(vmin=0, vmax=worst)
    for y, r in enumerate(rs):
        x_end = _parking_x(instance) if r.parked else r.sequenced
        color = ON_TIME if r.delay == 0 else DELAY_MAP(0.35 + 0.65 * norm(r.delay))
        if r.delay > 0:
            ax_fl.annotate("", xy=(x_end, y), xytext=(r.flight.planned, y),
                           arrowprops={"arrowstyle": "-|>", "color": color, "lw": 1.6,
                                       "shrinkA": 3, "shrinkB": 4}, zorder=3)
        ax_fl.plot(r.flight.planned, y, "o", mfc="white", mec=CAPACITY, ms=6, zorder=4)
        ax_fl.plot(x_end, y, "P" if r.parked else "s", color=color, mec=CAPACITY, ms=7, zorder=4)
        if r.delay > 0:
            ax_fl.text(x_end + 1.2, y, f"+{r.delay}", va="center", fontsize=7, color="#444444")
    ax_fl.set_yticks(range(n))
    ax_fl.set_yticklabels([f"{r.flight.name} {format_time(r.flight.planned)}" for r in rs], fontsize=7)
    ax_fl.set_ylim(n - 0.5, -0.5)
    ax_fl.set_ylabel("flights by planned time")
    _now_line(ax_fl, instance)

    # prices
    if prices is not None:
        ax_pr = axes[2]
        _shade_past(ax_pr, instance)
        for slot in instance.slots:
            if slot.index in prices:
                ax_pr.bar(slot.start, prices[slot.index], width=SLOT_MINUTES, align="edge",
                          color=PRICE, edgecolor="white", zorder=2)
        ax_pr.set_ylabel("slot price\n(one more\ndeparture)")
        _now_line(ax_pr, instance)

    _time_axis(axes[-1], instance)
    axes[-1].set_xlabel("time (slots of 10 min, ○ planned T(p), ■ sequenced T(s), P parked)")
    fig.suptitle(title or f"{plan.objective.label} — {plan.status}", fontsize=11)
    return fig


def plot_prices(instance: SlotInstance, prices: dict[str, dict[int, float]], figsize=(11, 3.2)) -> Figure:
    """Slot prices of several objectives side by side, each on its own scale."""
    fig, axes = plt.subplots(1, len(prices), figsize=figsize, constrained_layout=True)
    if len(prices) == 1:
        axes = [axes]
    for ax, (label, p) in zip(axes, prices.items()):
        _shade_past(ax, instance)
        for slot in instance.slots:
            if slot.index in p:
                ax.bar(slot.start, p[slot.index], width=SLOT_MINUTES, align="edge", color=PRICE, edgecolor="white")
        _now_line(ax, instance)
        majors = list(range(instance.start, instance.window_end + 1, HOUR))
        ax.set_xticks(majors)
        ax.set_xticklabels([format_time(t) for t in majors])
        ax.set_xlim(instance.start, instance.window_end)
        ax.set_title(label, fontsize=10)
    axes[0].set_ylabel("slot price (one more departure)")
    return fig


def plot_two_flights(
    planned: tuple[int, int] = (10, 20),
    slots: tuple[int, int] = (20, 30),
    forest: tuple[int, ...] = (0, 5, 15, 25),
    figsize: tuple[float, float] = (12, 6.75),
) -> Figure:
    """The hand sketch, drawn exactly: two flights, two slots, both costs side by side.

    Time is measured from NOW = 0. Every flight is a curve rising from its
    planned time: the same parabola shifted for the quadratic cost, a line
    with slope 1/(1 + p) for falling trees. Sol 1 keeps the planned order,
    sol 2 swaps the flights. Faint curves of further planned times show the
    family ("the forest").
    """
    from slot_capacity.objective import FALLING_TREES, QUADRATIC, Objective

    p1, p2 = planned
    s1, s2 = slots
    t_max = s2 + 6
    fig, axes = plt.subplots(1, 2, figsize=figsize)
    fig.subplots_adjust(left=0.06, right=0.98, top=0.80, bottom=0.17, wspace=0.16)
    sol_colors = {"sol 1": ON_TIME, "sol 2": DELAY_MAP(0.8)}

    for ax, name in zip(axes, (QUADRATIC, FALLING_TREES)):
        o = Objective(name)

        def f(p: int, t: float) -> float:
            return o.cost(t - p, p)

        ymax = 1.15 * max(f(p1, s2), f(p1, s1) + f(p2, s2))
        for p in forest:
            ts = [p + i * (t_max - p) / 200 for i in range(201)]
            ax.plot(ts, [f(p, t) for t in ts], color="#c8c8c8", linewidth=1.0, zorder=1)
        for k, p in enumerate((p1, p2), start=1):
            ts = [p + i * (t_max - p) / 200 for i in range(201)]
            ax.plot(ts, [f(p, t) for t in ts], color=CAPACITY, linewidth=2.0, zorder=2)
            ax.annotate(f"flight {k}", xy=(t_max - 0.3, min(f(p, t_max), 0.96 * ymax)), ha="right",
                        va="bottom", fontsize=10, color=CAPACITY)
        for s in slots:
            ax.axvline(s, color="#888888", linestyle="--", linewidth=1.0, zorder=0)
            ax.text(s, 1.0, f"slot {s}", transform=ax.get_xaxis_transform(), ha="center", va="bottom",
                    fontsize=9, color="#555555")

        solutions = {"sol 1": ((p1, s1), (p2, s2)), "sol 2": ((p1, s2), (p2, s1))}
        lines = []
        for label, pairs in solutions.items():
            costs = [f(p, s) for p, s in pairs]
            color = sol_colors[label]
            for k, ((p, s), c) in enumerate(zip(pairs, costs), start=1):
                ax.plot(s, c, "o", ms=11, color=color, mec="white", mew=1.5, zorder=4, clip_on=False)
                ax.text(s, c, str(k), ha="center", va="center", fontsize=8, color="white", clip_on=False,
                        fontweight="bold", zorder=5)
            (pa, sa), (pb, sb) = pairs
            ax.plot([sa, sb], [costs[0], costs[1]], color=color, linewidth=1.2, linestyle=":", zorder=3)
            terms = " + ".join(f"{c:.3g}" for c in costs)
            lines.append((label, color, f"{label}: {terms} = {sum(costs):.3g}", sum(costs)))
        best = min(lines, key=lambda item: item[3])[0]
        for i, (label, color, text, _) in enumerate(lines):
            mark = "  ✓ optimal" if label == best else ""
            ax.text(0.03, 0.95 - 0.075 * i, text + mark, transform=ax.transAxes, fontsize=11,
                    color=color, fontweight="bold" if label == best else "normal", va="top")

        ax.set_xlim(-1, t_max)
        ax.set_ylim(0, ymax)
        ticks = {0: "NOW", **{s: str(s) for s in slots}}
        for k, p in enumerate((p1, p2), start=1):
            ticks[p] = f"{p}\n$T(p)_{k}$"
        ax.set_xticks(sorted(ticks))
        ax.set_xticklabels([ticks[t] for t in sorted(ticks)])
        ax.set_xlabel("sequenced time $T(s)$, minutes after NOW")
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_title(r"quadratic  $f = d^2$" if name == QUADRATIC
                     else r"falling trees  $f = d\,/\,(1 + T(p))$", fontsize=13, pad=18)
    axes[0].set_ylabel("delay cost of the flight")

    fig.suptitle("Who should wait? Two flights, two slots, two delay costs", fontsize=16, fontweight="bold",
                 y=0.97)
    fig.text(0.5, 0.885, "Both keep the planned order. The quadratic cost bends every flight the same way; "
             "falling trees stays linear and lets later flights lean further over.",
             ha="center", fontsize=11, color="#444444")
    fig.text(0.5, 0.035, "sol 1: flights in planned order (1 → slot 20, 2 → slot 30)     "
             "sol 2: swapped (1 → slot 30, 2 → slot 20)     grey: flights planned at 0, 5, 15, 25",
             ha="center", fontsize=9.5, color="#555555")
    return fig
