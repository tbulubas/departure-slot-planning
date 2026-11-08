# Copyright (c) 2026 Taras Bulubas. All rights reserved.
# Use requires prior written permission; see LICENSE.

import pytest

from slot_capacity import SlotInstance, example_instance, format_time, parse_time


def test_parse_and_format_time():
    assert parse_time("06:05") == 365
    assert parse_time("6:05") == 365
    assert format_time(365) == "06:05"
    assert format_time(24 * 60 + 5) == "24:05"
    assert parse_time(format_time(24 * 60 + 5)) == 24 * 60 + 5
    for bad in ("0605", "06:5", "06:60", "x:10"):
        with pytest.raises(ValueError):
            parse_time(bad)


def test_grid_starts_at_the_full_hour_of_now():
    inst = SlotInstance.create("06:23", ["06:30", "06:45"])
    assert inst.start == parse_time("06:00")
    assert [s.label for s in inst.slots[:3]] == ["06:00", "06:10", "06:20"]
    assert all(s.start % 10 == 0 for s in inst.slots)
    assert [inst.is_past(s) for s in inst.slots[:3]] == [True, True, False]
    # latest planned 06:45 → full hour 07:00, plus one hour
    assert inst.window_end == parse_time("08:00")
    assert len(inst.slots) == 12


def test_eligibility_and_sequenced_time():
    inst = SlotInstance.create("06:23", {"A": "06:23", "B": "06:35"})
    a, b = inst.flight("A"), inst.flight("B")
    s0610, s0620, s0630, s0640 = (inst.slots[k] for k in (1, 2, 3, 4))
    assert not inst.eligible(a, s0610)  # over before NOW
    assert inst.eligible(a, s0620)
    assert inst.sequenced_time(a, s0620) == parse_time("06:23")  # not before NOW
    assert inst.delay(a, s0620) == 0
    assert inst.lead_time(a) == 0 and inst.lead_time(b) == 12
    assert not inst.eligible(b, s0620)  # ends before the planned time: no early departure
    assert inst.eligible(b, s0630)
    assert inst.delay(b, s0630) == 0  # departs at T(p) inside its own slot
    assert inst.delay(b, s0640) == 5
    assert inst.delay(b, None) == inst.parking_time - b.planned


def test_capacity_overrides_and_closed_slots():
    inst = SlotInstance.create("06:00", ["06:05"], default_capacity=2, capacities={"06:10": 0, "06:20": 5})
    caps = {s.label: s.capacity for s in inst.slots}
    assert caps["06:00"] == 2 and caps["06:10"] == 0 and caps["06:20"] == 5
    assert not inst.eligible(inst.flights[0], inst.slots[1])


def test_invalid_input():
    with pytest.raises(ValueError):
        SlotInstance.create("06:00", [])
    with pytest.raises(ValueError):
        SlotInstance.create("06:00", ["06:05"], capacities={"06:05": 1})  # off the grid
    with pytest.raises(ValueError):
        SlotInstance.create("06:00", ["07:30"], end="07:00")  # planned after the window
    with pytest.raises(ValueError):
        SlotInstance.create("06:00", ["06:30"], end="06:30")  # not a full hour
    with pytest.raises(ValueError, match="before NOW"):
        SlotInstance.create("06:23", ["06:15", "06:30"])  # NOW is a hard limit


def test_example():
    inst = example_instance()
    assert len(inst.flights) == 24
    assert format_time(inst.window_end) == "09:00"
