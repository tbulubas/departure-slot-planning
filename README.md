# Departure Slot Capacity Planning

Departures of an airport compete for 10-minute departure slots of limited
capacity. At the planning moment NOW every flight gets a slot — or a parking
slot when none is left — so that the flights are delayed as little as
possible, individually and in total, without delaying one flight heavily so
that others can go on time.

The project compares two delay costs in the same time-indexed MILP (OR-Tools
+ SCIP):

- the **quadratic** cost `d²`, and
- the **falling trees** model `d / (1 + q)`: linear in the delay `d`, with a
  smaller slope for flights planned further ahead (`q` minutes from NOW).

Both keep the planned order, but they push the flights into the slots with
very different force — visible in the slot prices — and the quadratic cost
needs coefficients that grow with the square of the planning window.

- Problem statement: [docs/problem-statement.md](docs/problem-statement.md)
- Mathematical model: [docs/mip-model.md](docs/mip-model.md)
- Background on delay costs: [docs/objective-functions.md](docs/objective-functions.md)

## Author

**Taras Bulubas** — taras.bulubas@gmail.com

All work on this project was done on my own hardware and in my private time.
All new and original ideas in it — the problem, the modelling approach and
its formulation, including the falling trees model — are my own and the
result of many years of work in optimisation, operations research and
algorithms.

**Use of AI.** Claude (an AI assistant by Anthropic) was used to help write
the code and the documentation, following my specifications and decisions.

**License.** © 2026 Taras Bulubas. All rights reserved. This repository is
published for viewing only; any use requires my prior written permission —
see [LICENSE](LICENSE). The one exception is the notebook, which you may run
and modify in Google Colab for personal, non-commercial exploration.

## Development environment

Requires Python 3.12 and GNU make 3.82+. The solver is SCIP, shipped with
OR-Tools, so nothing else has to be installed.

All dependencies are declared in [pyproject.toml](pyproject.toml):

| Group            | Packages     | Used for                    |
|------------------|--------------|-----------------------------|
| runtime          | `ortools`    | the MILP (SCIP) and the slot prices (GLOP) |
| extra `dev`      | `pytest`     | tests                       |
| extra `plot`     | `matplotlib` | plan pictures               |
| extra `notebook` | `jupyterlab`, `ipywidgets`, `pandas` (+ `plot`) | the interactive notebook |

On Windows install make once, e.g. with `winget install ezwinports.make`,
and open a new terminal.

| Target           | What it does                                                       |
|------------------|--------------------------------------------------------------------|
| `make` / `make help` | list the targets                                               |
| `make venv`      | create `.venv` with Python 3.12 and install the project with all extras |
| `make test`      | run the tests with pytest                                          |
| `make run`       | solve the example; another instance with `ARGS="--now 06:20 --flights 06:20,06:25 --capacity 1"` |
| `make notebook`  | open `notebooks/slot_capacity.ipynb` in JupyterLab                 |
| `make notebook-check` | run all notebook cells headless and store the outputs         |
| `make clean`     | remove caches and build metadata                                   |
| `make distclean` | `clean` and remove `.venv`                                         |
| `make recreate`  | `distclean`, then `venv` — a fresh environment                     |

Without make:

```bash
py -3.12 -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev,plot,notebook]"
```

IntelliJ IDEA: see [docs/intellij.md](docs/intellij.md).

## Usage

```bash
.venv/Scripts/python -m slot_capacity --example --prices
.venv/Scripts/python -m slot_capacity --now 06:23 --flights 06:23,06:25,06:25,06:30 --capacity 1 --slot-capacity 06:40=0
```

| Option | Meaning |
|---|---|
| `--now HH:MM` | planning moment NOW |
| `--flights HH:MM,...` | planned departure times |
| `--example` | the morning bank of 24 departures |
| `--capacity N` | departures per 10-minute slot |
| `--slot-capacity 06:30=1,...` | capacity of single slots |
| `--end HH:00` | end of the planning window |
| `--parking-delay MIN` | a parked flight counts as departing this much after the window |
| `--objective quadratic\|falling-trees\|both` | delay cost |
| `--tau MIN` | time scale of the falling trees, `d / (1 + q/τ)` |
| `--prices` | show the slot prices |

Every plan is checked by an independent `verify()`.

## Notebook

[notebooks/slot_capacity.ipynb](notebooks/slot_capacity.ipynb) explains the
problem and both costs, solves an example with both, draws how the flights
are pushed into the slots, shows the slot prices, the growth of the
coefficients with the planning window, and closes with an interactive
explorer: NOW, the planned departures and the capacity of every slot can be
changed there.

## Tests

```bash
make test
```

The model is checked against an exhaustive search on small random
instances.

## Layout

```
src/slot_capacity/
  instance.py    flights, 10-minute slots, NOW, the example
  objective.py   quadratic and falling trees delay costs
  model.py       the time-indexed MILP (SCIP), slot prices, coefficient range
  solution.py    plan, independent verify(), metrics
  draw.py        pictures of a plan
  cli.py         command line interface
tests/           pytest, exhaustive.py
notebooks/       slot_capacity.ipynb
docs/            problem statement, model, background, IntelliJ
```
