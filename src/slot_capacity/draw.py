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
