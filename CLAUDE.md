# PlanningSlotCapacity — project guide for Claude

Departure slot capacity planning: flights compete for capacity-limited
departure slots (plus parking slots with unlimited capacity) and the model
decides who gets which slot and how much delay each one takes. Aviation
terms are used openly in this project. The first focus is **how to model the
objective function** — global vs individual delay, and the shape of the
individual penalty (linear, quadratic, arctangent, threshold, …), in a MILP
and in CP. The user's alternative to the quadratic penalty is the
**falling trees model**: linear `(s − p)/(1 + p)`, later planned departures
get a smaller slope — motivated by numerical stability over a long planning
window.

- Working note on the objective alternatives: `docs/objective-functions.md`
- Problem statement: `docs/problem-statement.md` (comes from the user — ask,
  do not invent the problem)

## Layout

Follows the standard of the user's `PlanningRopeBridge`,
`PlanningLinesSweeping` and `PlanningTrainWagons` projects (use them as the
reference):

- `src/<package>/`, `pyproject.toml` (setuptools, no `requirements.txt`),
  `tests/` with pytest
- `Makefile` with `venv`, `test`, `run`, `clean`, `distclean`, `recreate`;
  Python 3.12 via the py launcher, `scripts/check_venv.py` guards the version
- `docs/` — `problem-statement.md`, `mip-model.md`, `intellij.md`
- `.run/` — shared IntelliJ run configurations
- Copyright header in every source file:
  ```
  # Copyright (c) 2026 Taras Bulubas. All rights reserved.
  # Use requires prior written permission; see LICENSE.
  ```
- `LICENSE` — all rights reserved; README has the Author / Use of AI /
  License sections like the sibling projects

Package `slot_capacity`: `instance.py` (flights, 10-minute slots aligned to
the full hour, NOW, per-slot capacity, parking, the example), `objective.py`
(quadratic, falling trees), `model.py` (time-indexed MILP with SCIP — no
CP-SAT for now; slot prices via GLOP LP; coefficient range), `solution.py`
(plan, independent `verify()`, metrics), `draw.py` (plan and price
pictures), `cli.py`. `tests/exhaustive.py` is the independent optimality
check. `notebooks/slot_capacity.ipynb` (`make notebook`, `make
notebook-check`) is stored with its outputs — keep them free of local
paths.

## Running and testing

The user is on Windows 11 and uses the local `.venv`; do not use or suggest
conda. After changing dependencies in `pyproject.toml`, run `make venv`.
