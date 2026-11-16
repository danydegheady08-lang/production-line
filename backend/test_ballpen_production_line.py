"""pytest tests for the ball pen back end (exercises 2.4 and 2.5)."""

import random

import pytest

import ballpen_production_line as bp


def test_all_defective_line_never_ships_and_stops(monkeypatch):
    """2.4: random.random() always returns 0.0, so 0.0 < defect_rate is true
    for every part and every part is defective. Without a guard the line would
    loop forever. With max_attempts it must stop and ship nothing."""
    monkeypatch.setattr(random, "random", lambda: 0.0)

    line = bp.ProductionLine(max_attempts=200)
    line.run(target=3)

    assert len(line.shipped) == 0       # not a single pen ships
    assert line.stalled is True         # the guard stopped the loop
    assert line._attempts() == 200      # and it stopped exactly at the budget


def test_guard_does_not_disturb_a_healthy_line():
    """A normal line reaches its target long before the budget is used."""
    random.seed(42)
    line = bp.ProductionLine(max_attempts=1000)
    line.run(target=5)

    assert len(line.shipped) == 5
    assert line.stalled is False


def test_every_station_returns_a_list():
    """2.5: process() returns a list, also when the item is rejected."""
    random.seed(1)
    maker = bp.ComponentMaker("barrel")
    qc = bp.QualityControl(name="QC barrel")

    made = maker.process()
    assert isinstance(made, list) and len(made) == 1

    bad = bp.Component("barrel", 99, bp.Quality.DEFECTIVE)
    good = bp.Component("barrel", 100, bp.Quality.OK)
    assert qc.process(bad) == []        # rejected: empty list, not None
    assert qc.process(good) == [good]   # passed: list with one item


def test_pen_needs_all_five_components():
    pen = bp.BallPen(serial=1)
    assert not pen.is_complete()
    for name in ("barrel", "tip", "cartridge", "spring", "cap"):
        setattr(pen, name, bp.Component(name, 1))
    assert pen.is_complete()
    pen.spring = None
    assert not pen.is_complete()
