"""
ballpen_production_line.py  (homework version)
==============================================
Changes compared with the lecture version:

  Exercise 2.2  a fifth component, the spring, for a retractable pen
  Exercise 2.4  a maximum-attempts guard, so the line cannot loop forever
  Exercise 2.5  every Station.process() now returns a LIST instead of
                "an item or None"
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Deque, List, Optional


class Quality(Enum):
    """Quality grade assigned by inspection stations."""
    OK = auto()
    DEFECTIVE = auto()


@dataclass
class Component:
    """A generic part that goes into a pen."""
    name: str
    serial: int
    quality: Quality = Quality.OK


@dataclass
class BallPen:
    """Finished or in-progress pen: a composition of components."""
    serial: int
    barrel: Optional[Component] = None
    tip: Optional[Component] = None
    cartridge: Optional[Component] = None
    spring: Optional[Component] = None      # 2.2: retractable mechanism
    cap: Optional[Component] = None
    quality: Quality = Quality.OK
    packaged: bool = False

    def is_complete(self) -> bool:
        """Has every component been installed?"""
        return all([self.barrel, self.tip, self.cartridge, self.spring, self.cap])


class LineStalled(RuntimeError):
    """Raised when the line used up its attempts without finishing (2.4)."""


class Station(ABC):
    """Abstract base for any station on the line.

    2.5: process() ALWAYS returns a list, possibly empty.

        []        the item was discarded (replaces the old "return None")
        [x]       one output (the normal case)
        [x, y]    several outputs

    Why a list is more flexible: the caller never has to ask "is this None?"
    and can simply loop over the result, whatever its length. A station that
    one day has to emit more than one output (a cutting station that turns one
    sheet into four parts, a rework station that returns the repaired pen and
    a scrap record, a vision station that returns the pen plus a defect
    report) can do so without changing a single caller. With "item or None"
    that station would need a new return type and every caller would break.
    """

    def __init__(self, name: str, defect_rate: float = 0.0):
        self.name = name
        self.defect_rate = defect_rate
        self.processed = 0
        self.rejected = 0

    @abstractmethod
    def process(self, item) -> List[Any]:
        ...

    def _maybe_defect(self) -> Quality:
        """Helper: simulate manufacturing variance."""
        return (
            Quality.DEFECTIVE
            if random.random() < self.defect_rate
            else Quality.OK
        )

    def log(self, message: str) -> None:
        print(f"[{self.name:<18}] {message}")


class ComponentMaker(Station):
    """Manufactures one type of component (barrels, tips, ...)."""

    def __init__(self, component_name: str, defect_rate: float = 0.05):
        super().__init__(name=f"Make {component_name}", defect_rate=defect_rate)
        self.component_name = component_name
        self._counter = 0

    def process(self, _ignored=None) -> List[Component]:
        self._counter += 1
        self.processed += 1
        part = Component(
            name=self.component_name,
            serial=self._counter,
            quality=self._maybe_defect(),
        )
        self.log(f"produced {part.name}#{part.serial} -> {part.quality.name}")
        return [part]


class QualityControl(Station):
    """Discards defective components before they reach assembly."""

    def process(self, item: Component) -> List[Component]:
        self.processed += 1
        if item.quality is Quality.DEFECTIVE:
            self.rejected += 1
            self.log(f"REJECT {item.name}#{item.serial}")
            return []
        self.log(f"pass   {item.name}#{item.serial}")
        return [item]


class AssemblyStation(Station):
    """Combines five good components into a single pen."""

    def __init__(self, defect_rate: float = 0.02):
        super().__init__(name="Assembly", defect_rate=defect_rate)
        self._counter = 0

    def process(self, parts: dict) -> List[BallPen]:
        self._counter += 1
        self.processed += 1
        pen = BallPen(
            serial=self._counter,
            barrel=parts["barrel"],
            tip=parts["tip"],
            cartridge=parts["cartridge"],
            spring=parts["spring"],
            cap=parts["cap"],
            quality=self._maybe_defect(),  # assembly itself can fail
        )
        self.log(f"assembled Pen#{pen.serial} -> {pen.quality.name}")
        return [pen]


class FinalInspection(Station):
    """Final QC: a pen must be complete *and* non-defective."""

    def process(self, pen: BallPen) -> List[BallPen]:
        self.processed += 1
        if not pen.is_complete() or pen.quality is Quality.DEFECTIVE:
            self.rejected += 1
            self.log(f"REJECT Pen#{pen.serial}")
            return []
        self.log(f"pass   Pen#{pen.serial}")
        return [pen]


class Packaging(Station):
    """Wraps the pen, the last step before shipping."""

    def __init__(self):
        super().__init__(name="Packaging")

    def process(self, pen: BallPen) -> List[BallPen]:
        self.processed += 1
        pen.packaged = True
        self.log(f"packaged Pen#{pen.serial}")
        return [pen]


class ProductionLine:
    """Runs the whole line for a target number of pens."""

    COMPONENT_NAMES = ("barrel", "tip", "cartridge", "cap", "spring")

    def __init__(self, max_attempts: Optional[int] = None):
        self.makers = {n: ComponentMaker(n) for n in self.COMPONENT_NAMES}
        self.qcs = {n: QualityControl(name=f"QC {n}") for n in self.COMPONENT_NAMES}
        self.bins: dict[str, Deque[Component]] = {
            n: deque() for n in self.COMPONENT_NAMES
        }
        self.assembly = AssemblyStation()
        self.final_qc = FinalInspection(name="Final QC")
        self.packaging = Packaging()
        self.shipped: List[BallPen] = []

        # 2.4: guard against an endless loop. The budget counts every
        # component the makers have tried to produce.
        self.max_attempts = max_attempts
        self.stalled = False

    # -- internal helpers ----------------------------------------------------

    def _attempts(self) -> int:
        return sum(m.processed for m in self.makers.values())

    def _check_budget(self) -> None:
        if self.max_attempts is not None and self._attempts() >= self.max_attempts:
            raise LineStalled(
                f"stopped after {self._attempts()} attempts "
                f"with {len(self.shipped)} pens shipped"
            )

    def _refill_bins(self) -> None:
        """Make + inspect components until each bin has at least one."""
        for name in self.COMPONENT_NAMES:
            while not self.bins[name]:
                self._check_budget()
                for raw in self.makers[name].process():
                    for good in self.qcs[name].process(raw):
                        self.bins[name].append(good)

    def _assemble_one(self) -> List[BallPen]:
        parts = {n: self.bins[n].popleft() for n in self.COMPONENT_NAMES}
        shipped: List[BallPen] = []
        for pen in self.assembly.process(parts):
            for checked in self.final_qc.process(pen):
                shipped.extend(self.packaging.process(checked))
        return shipped

    # -- public API ----------------------------------------------------------

    def run(self, target: int) -> None:
        """Produce `target` shippable pens, or stop when the budget is used up."""
        print(f"\n=== Starting production: target = {target} pens ===\n")
        try:
            while len(self.shipped) < target:
                self._refill_bins()
                self.shipped.extend(self._assemble_one())
        except LineStalled as stop:
            self.stalled = True
            print(f"\n!!! LINE STALLED: {stop}")
        self._report()

    def _report(self) -> None:
        print("\n=== Production report ===")
        all_stations: list[Station] = [
            *self.makers.values(),
            *self.qcs.values(),
            self.assembly,
            self.final_qc,
            self.packaging,
        ]
        for s in all_stations:
            print(f"{s.name:<18} processed={s.processed:<4} rejected={s.rejected}")
        print(f"\nShipped pens: {len(self.shipped)}")


if __name__ == "__main__":
    random.seed(42)  # reproducible classroom output
    ProductionLine().run(target=5)
