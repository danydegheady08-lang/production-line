"""The simulation runs and is tested WITHOUT matplotlib (exercise 3.5)."""

import sys

from simulation_state import SimulationState


def test_same_seed_gives_same_factory():
    a, b = SimulationState(seed=42), SimulationState(seed=42)
    for _ in range(260):
        a.tick()
        b.tick()
    assert a.snapshot() == b.snapshot()


def test_reference_run_of_the_lecture_animation():
    """Seed 42, 260 frames: the numbers the original script produced."""
    s = SimulationState(seed=42)
    for _ in range(260):
        s.tick()
    c = s.snapshot()["counters"]
    assert sum(c["made"].values()) == 37
    assert c["rejected"] == 3
    assert c["shipped"] == 4


def test_snapshot_is_a_copy():
    s = SimulationState(seed=42)
    for _ in range(50):
        s.tick()
    view = s.snapshot()
    view["counters"]["shipped"] = 999
    view["bins"]["barrel"] = 999
    view["items"].clear()
    assert s.counters["shipped"] != 999
    assert s.bins["barrel"] != 999
    assert len(s.items) > 0


def test_simulation_never_imports_a_renderer():
    assert "matplotlib" not in sys.modules
