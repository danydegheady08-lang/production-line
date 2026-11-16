"""
simulation_state.py   (exercise 3.5)
====================================
The BACK END of the animation: all state and all rules, and not one line of
drawing code. This module does not import matplotlib.

    state = SimulationState(seed=42)
    state.tick()                 # advance the factory by one frame
    view = state.snapshot()      # a plain copy of the data, safe to draw

Why this separation matters
---------------------------
The renderer only ever calls snapshot(), a read-only copy of the numbers it
needs. It can never change the factory by accident, and the simulation does not
know that a renderer exists. That is what lets us swap matplotlib for a Tkinter
window, a web page or a real HMI without touching a single line in this file:
the new front end just calls snapshot() as well. It also makes the logic
testable on its own, without opening a window (see test_simulation_state.py).
"""

import random
from copy import deepcopy

COMPONENT_TYPES = ["barrel", "tip", "cartridge", "cap"]

# World coordinates. They describe WHERE things are on the line, which the rules
# need (a part is "at QC" when its x reaches X_QC), so they belong to the state.
X_MAKER, X_QC, X_BIN = 1.5, 3.5, 5.5
X_ASSEMBLY, X_FINAL_QC = 8.0, 10.0
X_PACKAGING, X_SHIPPED = 12.0, 14.0
LANE_Y = {"barrel": 8, "tip": 6, "cartridge": 4, "cap": 2}
PEN_Y = 5.0


class SimulationState:
    """Holds items, bins and counters, and advances them with tick()."""

    def __init__(self, seed=42, speed=0.13, defect_rate=0.05, pen_defect_rate=0.02):
        self.rng = random.Random(seed)       # its own generator, reproducible
        self.speed = speed
        self.defect_rate = defect_rate
        self.pen_defect_rate = pen_defect_rate

        self.frame = 0
        self.items = []                                          # things in motion
        self.bins = {ct: 0 for ct in COMPONENT_TYPES}            # parts in stock
        self.spawn_timers = {ct: self.rng.randint(0, 15) for ct in COMPONENT_TYPES}
        self.arrivals_at_assembly = 0
        self.counters = {
            "made": {ct: 0 for ct in COMPONENT_TYPES},
            "rejected": 0,
            "shipped": 0,
        }

    # -- public API ----------------------------------------------------------

    def tick(self):
        """Advance the whole factory by one frame (the same order as before)."""
        self._maybe_spawn_components()
        to_remove = []
        self._step_components(to_remove)
        self._step_pens(to_remove)
        for it in to_remove:
            if it in self.items:
                self.items.remove(it)
        self._maybe_dispatch_assembly()
        self._maybe_emit_pen()
        self.frame += 1

    def snapshot(self):
        """A deep copy of everything a renderer may need. Changing the copy
        cannot change the simulation."""
        return {
            "frame": self.frame,
            "items": deepcopy(self.items),
            "bins": dict(self.bins),
            "counters": deepcopy(self.counters),
        }

    # -- rules (internal) ----------------------------------------------------

    def _maybe_spawn_components(self):
        for ct in COMPONENT_TYPES:
            self.spawn_timers[ct] -= 1
            if self.spawn_timers[ct] <= 0:
                self.counters["made"][ct] += 1
                self.items.append({
                    "type": ct, "kind": "component",
                    "x": X_MAKER, "y": LANE_Y[ct],
                    "defective": self.rng.random() < self.defect_rate,
                    "stage": "to_qc",
                })
                self.spawn_timers[ct] = self.rng.randint(22, 38)

    def _step_components(self, to_remove):
        for it in self.items:
            if it["kind"] != "component":
                continue
            stage = it["stage"]
            if stage == "to_qc":
                it["x"] += self.speed
                if it["x"] >= X_QC:
                    it["stage"] = "falling" if it["defective"] else "to_bin"
            elif stage == "to_bin":
                it["x"] += self.speed
                if it["x"] >= X_BIN:
                    self.bins[it["type"]] += 1
                    to_remove.append(it)
            elif stage == "falling":
                it["y"] -= self.speed * 1.4
                if it["y"] < -0.5:
                    self.counters["rejected"] += 1
                    to_remove.append(it)
            elif stage == "to_assembly":
                tx, ty = X_ASSEMBLY - 0.5, PEN_Y
                dx, dy = tx - it["x"], ty - it["y"]
                dist = (dx * dx + dy * dy) ** 0.5
                if dist < self.speed:
                    self.arrivals_at_assembly += 1
                    to_remove.append(it)
                else:
                    it["x"] += self.speed * dx / dist
                    it["y"] += self.speed * dy / dist

    def _step_pens(self, to_remove):
        next_stage = {
            "to_final_qc": ("to_packaging", X_FINAL_QC),
            "to_packaging": ("to_shipped", X_PACKAGING),
            "to_shipped": ("done", X_SHIPPED),
        }
        for it in self.items:
            if it["kind"] != "pen":
                continue
            stage = it["stage"]
            nxt, target = next_stage[stage]
            it["x"] += self.speed
            if it["x"] >= target:
                if stage == "to_final_qc" and it.get("defective"):
                    self.counters["rejected"] += 1
                    to_remove.append(it)
                elif nxt == "done":
                    self.counters["shipped"] += 1
                    to_remove.append(it)
                else:
                    it["stage"] = nxt

    def _maybe_dispatch_assembly(self):
        in_flight = sum(1 for i in self.items
                        if i["kind"] == "component" and i["stage"] == "to_assembly")
        ready = all(self.bins[ct] >= 1 for ct in COMPONENT_TYPES)
        if in_flight == 0 and ready and self.frame % 12 == 0:
            for ct in COMPONENT_TYPES:
                self.bins[ct] -= 1
                self.items.append({
                    "type": ct, "kind": "component",
                    "x": X_BIN, "y": LANE_Y[ct],
                    "defective": False,
                    "stage": "to_assembly",
                })

    def _maybe_emit_pen(self):
        if self.arrivals_at_assembly >= 4:
            self.arrivals_at_assembly -= 4
            self.items.append({
                "type": "pen", "kind": "pen",
                "x": X_ASSEMBLY + 0.5, "y": PEN_Y,
                "defective": self.rng.random() < self.pen_defect_rate,
                "stage": "to_final_qc",
            })
