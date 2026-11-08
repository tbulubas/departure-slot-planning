# Copyright (c) 2026 Taras Bulubas. All rights reserved.
# Use requires prior written permission; see LICENSE.

"""The two delay costs compared in this project (docs/mip-model.md, section 2).

    quadratic       f(d) = d²
    falling trees   f(d) = d / (1 + q/τ)

d = T(s) − T(p) is the delay in minutes and q the lead time: minutes from NOW
until the planned departure (T(p) ≥ NOW, so q ≥ 0). τ is the time scale
of the falling trees; τ = 1 minute gives d / (1 + q). Both costs are 0 for
d ≤ 0.
"""

from __future__ import annotations

from dataclasses import dataclass

QUADRATIC = "quadratic"
FALLING_TREES = "falling-trees"
OBJECTIVES = (QUADRATIC, FALLING_TREES)


@dataclass(frozen=True)
class Objective:
    """A delay cost: its name and, for falling trees, the time scale τ in minutes."""

    name: str = FALLING_TREES
    tau: float = 1.0

    def __post_init__(self) -> None:
        if self.name not in OBJECTIVES:
            raise ValueError(f"objective must be one of {', '.join(OBJECTIVES)}, got {self.name!r}")
        if self.tau <= 0:
            raise ValueError("tau must be positive")

    @property
    def text(self) -> str:
        """ASCII label for consoles."""
        if self.name == QUADRATIC:
            return "quadratic d^2"
        return "falling trees d/(1+q)" if self.tau == 1 else f"falling trees d/(1+q/{self.tau:g})"

    @property
    def label(self) -> str:
        if self.name == QUADRATIC:
            return "quadratic d²"
        return "falling trees d/(1+q)" if self.tau == 1 else f"falling trees d/(1+q/{self.tau:g})"

    def slope(self, lead_time: int) -> float:
        """Falling trees: cost of one minute of delay, 1 / (1 + q/τ)."""
        return 1.0 / (1.0 + lead_time / self.tau)

    def cost(self, delay: float, lead_time: int) -> float:
        """f(d) for a flight with the given lead time q; 0 for d ≤ 0."""
        d = max(delay, 0.0)
        if self.name == QUADRATIC:
            return d * d
        return d * self.slope(lead_time)

    def pressure(self, delay: float, lead_time: int) -> float:
        """f'(d): what one more minute of delay costs (the push towards an earlier slot)."""
        if delay < 0:
            return 0.0
        if self.name == QUADRATIC:
            return 2.0 * delay
        return self.slope(lead_time)
