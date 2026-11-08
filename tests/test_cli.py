# Copyright (c) 2026 Taras Bulubas. All rights reserved.
# Use requires prior written permission; see LICENSE.

import matplotlib
import pytest

from slot_capacity import FALLING_TREES, Objective, example_instance, slot_prices, solve
from slot_capacity.cli import main, parse_capacities

matplotlib.use("Agg")


def test_parse_capacities():
    assert parse_capacities("06:30=1, 06:40=0") == {"06:30": 1, "06:40": 0}
    assert parse_capacities("") == {}
    with pytest.raises(ValueError):
        parse_capacities("06:30")


def test_cli_example(capsys):
    main(["--example", "--prices"])
    out = capsys.readouterr().out
    assert out.count("check: OK") == 2
    assert "quadratic" in out and "falling trees" in out


def test_cli_flights(capsys):
    main(["--now", "06:20", "--flights", "06:20,06:20,06:25", "--capacity", "1",
          "--slot-capacity", "06:30=0", "--objective", "falling-trees"])
    out = capsys.readouterr().out
    assert "check: OK" in out
    assert "06:30 0/0" in out


def test_cli_invalid_input():
    with pytest.raises(SystemExit):
        main(["--flights", "6.30"])


def test_draw():
    from slot_capacity.draw import plot_plan, plot_prices

    inst = example_instance("06:00")
    objective = Objective(FALLING_TREES)
    plan = solve(inst, objective)
    prices = slot_prices(inst, objective)
    fig = plot_plan(inst, plan, prices)
    assert len(fig.axes) == 3
    fig = plot_prices(inst, {"falling trees": prices})
    assert len(fig.axes) == 1


def test_two_flights_figure():
    from slot_capacity.draw import plot_two_flights

    fig = plot_two_flights()
    texts = [t.get_text() for ax in fig.axes for t in ax.texts]
    assert any(t.startswith("sol 1: 100 + 100 = 200") and "optimal" in t for t in texts)
    assert any(t.startswith("sol 1: 0.909 + 0.476 = 1.39") and "optimal" in t for t in texts)
