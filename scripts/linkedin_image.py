# Copyright (c) 2026 Taras Bulubas. All rights reserved.
# Use requires prior written permission; see LICENSE.

"""Render the images of the README and the LinkedIn post.

images/departure-slot-linkedin.png  the two-flight example with both delay costs
images/example-plan.png             the morning bank planned with falling trees, with slot prices
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from slot_capacity import FALLING_TREES, Objective, example_instance, slot_prices, solve, verify  # noqa: E402
from slot_capacity.draw import plot_plan, plot_two_flights  # noqa: E402

IMAGES = Path(__file__).resolve().parent.parent / "images"


def main() -> None:
    IMAGES.mkdir(exist_ok=True)

    fig = plot_two_flights()
    path = IMAGES / "departure-slot-linkedin.png"
    fig.savefig(path, dpi=200)
    print(f"written {path.relative_to(IMAGES.parent)}")

    instance = example_instance()
    objective = Objective(FALLING_TREES)
    plan = solve(instance, objective)
    errors = verify(instance, plan)
    if plan.status != "optimal" or errors:
        sys.exit(f"no valid optimal plan: {plan.status}; {'; '.join(errors)}")
    fig = plot_plan(instance, plan, slot_prices(instance, objective),
                    title="24 departures, runway inspection 06:30–06:50, falling trees, NOW 06:00")
    path = IMAGES / "example-plan.png"
    fig.savefig(path, dpi=110)
    print(f"written {path.relative_to(IMAGES.parent)}")


if __name__ == "__main__":
    main()
