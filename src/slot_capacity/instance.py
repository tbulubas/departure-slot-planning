# Copyright (c) 2026 Taras Bulubas. All rights reserved.
# Use requires prior written permission; see LICENSE.

"""Flights, departure slots and the planning moment NOW.

All times are integer minutes after midnight. Slots are 10 minutes long and
aligned to the full hour (06:00, 06:10, …); the slot grid starts at the
beginning of the hour that contains NOW.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

SLOT_MINUTES = 10
HOUR = 60


def parse_time(value: str | int) -> int:
    """'HH:MM' (or minutes as int) → minutes after midnight."""
    if isinstance(value, int):
        minutes = value
    else:
        hours, sep, mins = value.strip().partition(":")
        if not sep or not hours.isdigit() or not mins.isdigit() or len(mins) != 2:
            raise ValueError(f"time must be HH:MM, got {value!r}")
        minutes = int(hours) * HOUR + int(mins)
        if int(mins) >= HOUR:
            raise ValueError(f"minutes must be below 60, got {value!r}")
    if not 0 <= minutes < 48 * HOUR:
        raise ValueError(f"time out of range: {value!r}")
    return minutes


def format_time(minutes: int | float) -> str:
    """Minutes after midnight → 'HH:MM'; after midnight of the next day 24:00, 24:10, …"""
    m = int(minutes)
    return f"{m // HOUR:02d}:{m % HOUR:02d}"


def hour_floor(minutes: int) -> int:
    return minutes - minutes % HOUR


def hour_ceil(minutes: int) -> int:
    return -(-minutes // HOUR) * HOUR


@dataclass(frozen=True)
class Flight:
    """A departure: its name and planned departure time T(p)."""

    name: str
    planned: int


@dataclass(frozen=True)
class Slot:
    """A 10-minute departure slot [start, start + 10)."""

    index: int
    start: int
    capacity: int

    @property
    def end(self) -> int:
        return self.start + SLOT_MINUTES

    @property
    def label(self) -> str:
        return format_time(self.start)


@dataclass(frozen=True)
class SlotInstance:
    """One planning situation.

    Attributes:
        now: the planning moment NOW, a hard limit: no flight is planned or
            sequenced before NOW; slots that end at or before NOW are past.
        flights: the departures, each with its planned time T(p) ≥ NOW.
        default_capacity: departures per slot unless overridden.
        capacities: overrides, slot start → capacity (e.g. 0 for a closure).
        end: end of the planning window, a full hour; None takes the full
            hour after the latest planned departure (or NOW) plus one hour.
        parking_delay: a parked flight counts as departing this many minutes
            after the end of the window.
    """

    now: int
    flights: tuple[Flight, ...]
    default_capacity: int = 3
    capacities: tuple[tuple[int, int], ...] = field(default=())
    end: int | None = None
    parking_delay: int = 60

    def __post_init__(self) -> None:
        if not self.flights:
            raise ValueError("at least one flight is needed")
        names = [f.name for f in self.flights]
        if len(set(names)) != len(names):
            raise ValueError("flight names must be unique")
        if self.default_capacity < 0:
            raise ValueError("capacity must not be negative")
        for start, capacity in self.capacities:
            if start % SLOT_MINUTES:
                raise ValueError(f"slot {format_time(start)} is not on the 10-minute grid")
            if capacity < 0:
                raise ValueError(f"capacity of slot {format_time(start)} must not be negative")
        if self.end is not None and self.end % HOUR:
            raise ValueError("the window must end at a full hour")
        if self.window_end <= self.now:
            raise ValueError("the window must end after NOW")
        early = [f.name for f in self.flights if f.planned < self.now]
        if early:
            raise ValueError(f"planned before NOW {format_time(self.now)}: {', '.join(early)}")
        late = [f.name for f in self.flights if f.planned >= self.window_end]
        if late:
            raise ValueError(f"planned after the end of the window: {', '.join(late)}")
        if self.parking_delay < 0:
            raise ValueError("parking delay must not be negative")

    @classmethod
    def create(
        cls,
        now: str | int,
        flights: Mapping[str, str | int] | Iterable[str | int],
        default_capacity: int = 3,
        capacities: Mapping[str | int, int] | None = None,
        end: str | int | None = None,
        parking_delay: int = 60,
    ) -> SlotInstance:
        """Build an instance from 'HH:MM' strings.

        flights is either name → planned time, or a list of planned times
        (the flights are then named F01, F02, … in the order given).
        """
        if isinstance(flights, Mapping):
            items = [Flight(str(name), parse_time(t)) for name, t in flights.items()]
        else:
            items = [Flight(f"F{i:02d}", parse_time(t)) for i, t in enumerate(flights, start=1)]
        caps = tuple(sorted((parse_time(k), int(v)) for k, v in (capacities or {}).items()))
        return cls(
            now=parse_time(now),
            flights=tuple(items),
            default_capacity=default_capacity,
            capacities=caps,
            end=None if end is None else parse_time(end),
            parking_delay=parking_delay,
        )

    # ---- the slot grid ----------------------------------------------------

    @property
    def start(self) -> int:
        """Start of the slot grid: the full hour containing NOW."""
        return hour_floor(self.now)

    @property
    def window_end(self) -> int:
        if self.end is not None:
            return self.end
        latest = max([self.now, *(f.planned for f in self.flights)])
        return hour_ceil(latest + 1) + HOUR

    @property
    def parking_time(self) -> int:
        """The time a parked flight is counted as departing."""
        return self.window_end + self.parking_delay

    @property
    def slots(self) -> tuple[Slot, ...]:
        overrides = dict(self.capacities)
        return tuple(
            Slot(k, t, overrides.get(t, self.default_capacity))
            for k, t in enumerate(range(self.start, self.window_end, SLOT_MINUTES))
        )

    def is_past(self, slot: Slot) -> bool:
        return slot.end <= self.now

    def eligible(self, flight: Flight, slot: Slot) -> bool:
        """A flight may take a slot that is not over before NOW or before its planned time.

        Early departures are excluded: a flight never leaves before T(p).
        """
        return slot.end > self.now and slot.end > flight.planned and slot.capacity > 0

    def sequenced_time(self, flight: Flight, slot: Slot | None) -> int:
        """T(s): the slot start, but not before T(p) or NOW; parking for None."""
        if slot is None:
            return self.parking_time
        return max(slot.start, flight.planned, self.now)

    def delay(self, flight: Flight, slot: Slot | None) -> int:
        return self.sequenced_time(flight, slot) - flight.planned

    def lead_time(self, flight: Flight) -> int:
        """q: minutes from NOW until the planned departure (T(p) ≥ NOW, so q ≥ 0)."""
        return flight.planned - self.now

    def flight(self, name: str) -> Flight:
        for f in self.flights:
            if f.name == name:
                return f
        raise KeyError(name)

    @property
    def sorted_flights(self) -> tuple[Flight, ...]:
        """Flights by planned time, then by name."""
        return tuple(sorted(self.flights, key=lambda f: (f.planned, f.name)))


EXAMPLE_FLIGHTS = (
    "06:02", "06:05", "06:08", "06:14", "06:18", "06:21", "06:25", "06:28",
    "06:30", "06:31", "06:34", "06:36", "06:38", "06:40", "06:41", "06:44",
    "06:47", "06:50", "06:52", "06:55", "07:00", "07:05", "07:15", "07:25",
)
"""A morning bank of 24 departures."""

EXAMPLE_CAPACITIES = {"06:30": 1, "06:40": 1, "06:50": 2}
"""Reduced capacity in the peak of the bank (e.g. a runway inspection)."""


def example_instance(now: str = "06:00") -> SlotInstance:
    """24 departures, 3 per slot, reduced to 1–2 in the peak of the bank."""
    return SlotInstance.create(now, EXAMPLE_FLIGHTS, default_capacity=3, capacities=EXAMPLE_CAPACITIES)
