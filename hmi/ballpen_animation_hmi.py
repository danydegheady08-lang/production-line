"""
ballpen_animation_hmi.py
========================
The FRONT END of the ball-pen line, rebuilt as a small HMI.

  3.3  alarm: when the rejected counter exceeds ALARM_REJECTED the title turns
       red and shows "ALARM: HIGH REJECT RATE"
  3.4  every bin is a colored bar that grows with the stock and turns yellow
       when it is full (capped at BIN_CAP units)
  3.5  this file only draws. All state lives in SimulationState and the
       renderer reads it through snapshot() and nothing else.

Run:  python ballpen_animation_hmi.py
"""

import sys

from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle
import matplotlib.pyplot as plt

from simulation_state import (
    COMPONENT_TYPES, LANE_Y, PEN_Y,
    X_MAKER, X_QC, X_BIN, X_ASSEMBLY, X_FINAL_QC, X_PACKAGING, X_SHIPPED,
    SimulationState,
)

COLORS = {
    "barrel": "#3498db", "tip": "#9b59b6", "cartridge": "#2ecc71",
    "cap": "#e74c3c", "pen": "#f39c12",
}
TOTAL_FRAMES = 260
ALARM_REJECTED = 5          # 3.3: alarm when rejected > 5
BIN_CAP = 5                 # 3.4: bar is capped at 5 units
BIN_UNIT = 0.16             # height of one unit in world coordinates
COLOR_NORMAL, COLOR_FULL = "#5dade2", "#f1c40f"
TITLE = "Ball Pen Production Line"


class Renderer:
    """Draws whatever snapshot() says. It has no factory logic of its own."""

    def __init__(self, state: SimulationState):
        self.state = state
        self.fig, self.ax = plt.subplots(figsize=(12, 5.5), dpi=80)
        self.ax.set_xlim(0, 15.5)
        self.ax.set_ylim(-1, 10)
        self.ax.set_aspect("equal")
        self.ax.axis("off")
        self.fig.patch.set_facecolor("#f7f9fc")

        self.title = self.ax.text(7.75, 9.5, TITLE, ha="center", fontsize=18,
                                  weight="bold", color="#222")
        self._draw_background()

        self.counter_text = self.ax.text(7.75, -0.55, "", ha="center",
                                         fontsize=11, weight="bold")
        self.bin_labels = {
            ct: self.ax.text(X_BIN, LANE_Y[ct] - 0.8, "", ha="center",
                             fontsize=8, weight="bold")
            for ct in COMPONENT_TYPES
        }
        # 3.4: one bar per bin, created once and resized every frame
        self.bars = {}
        for ct in COMPONENT_TYPES:
            bar = Rectangle((X_BIN - 0.3, LANE_Y[ct] - 0.4), 0.6, 0.0,
                            facecolor=COLOR_NORMAL, edgecolor="#333",
                            linewidth=1, zorder=3)
            self.ax.add_patch(bar)
            self.bars[ct] = bar

        self.frame_artists = []
        self.shipped_dots = []

    def _station(self, x, y, w, h, label, color):
        self.ax.add_patch(FancyBboxPatch(
            (x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.04",
            facecolor=color, edgecolor="#333", linewidth=1.2, zorder=2))
        if label:
            self.ax.text(x, y, label, ha="center", va="center",
                         fontsize=8.5, weight="bold", zorder=3)

    def _draw_background(self):
        ax = self.ax
        for ct in COMPONENT_TYPES:
            y = LANE_Y[ct]
            self._station(X_MAKER, y, 1.3, 0.9, f"Make\n{ct}", "#fff3cd")
            self._station(X_QC, y, 1.0, 0.9, "QC", "#cce5ff")
            self._station(X_BIN, y, 1.0, 0.9, "", "#fffacd")   # 3.4: no "Bin" text
            ax.plot([X_MAKER + 0.65, X_BIN - 0.5], [y, y], color="#bbb", lw=1, zorder=1)
            ax.plot([X_BIN + 0.5, X_ASSEMBLY - 0.9], [y, PEN_Y], color="#bbb", lw=1, zorder=1)
        self._station(X_ASSEMBLY, PEN_Y, 1.8, 5.0, "Assembly", "#ffe4e1")
        self._station(X_FINAL_QC, PEN_Y, 1.2, 0.9, "Final\nQC", "#cce5ff")
        self._station(X_PACKAGING, PEN_Y, 1.2, 0.9, "Pack", "#d4edda")
        self._station(X_SHIPPED, PEN_Y, 1.5, 6.0, "Shipped", "#e8f5e9")
        for a, b in ((X_ASSEMBLY + 0.9, X_FINAL_QC - 0.6),
                     (X_FINAL_QC + 0.6, X_PACKAGING - 0.6),
                     (X_PACKAGING + 0.6, X_SHIPPED - 0.75)):
            ax.plot([a, b], [PEN_Y, PEN_Y], color="#bbb", lw=1, zorder=1)

    def draw(self, view):
        """Redraw everything from one snapshot."""
        for a in self.frame_artists:
            a.remove()
        self.frame_artists.clear()

        for it in view["items"]:
            radius = 0.22 if it["kind"] == "pen" else 0.17
            c = Circle((it["x"], it["y"]), radius, facecolor=COLORS[it["type"]],
                       edgecolor="#222", linewidth=1, zorder=5)
            self.ax.add_patch(c)
            self.frame_artists.append(c)

        # 3.4: bin bars, capped, yellow when full
        for ct in COMPONENT_TYPES:
            n = view["bins"][ct]
            bar = self.bars[ct]
            bar.set_height(min(n, BIN_CAP) * BIN_UNIT)
            bar.set_facecolor(COLOR_FULL if n >= BIN_CAP else COLOR_NORMAL)
            self.bin_labels[ct].set_text(f"x{n}" if n else "")

        # shipped tray: one dot per shipped pen
        shipped = view["counters"]["shipped"]
        while len(self.shipped_dots) < shipped:
            idx = len(self.shipped_dots)
            col, row = idx % 4, idx // 4
            dot = Circle((X_SHIPPED - 0.55 + col * 0.32, PEN_Y - 2 + row * 0.45), 0.12,
                         facecolor=COLORS["pen"], edgecolor="#333", zorder=4)
            self.ax.add_patch(dot)
            self.shipped_dots.append(dot)

        # 3.3: alarm
        rejected = view["counters"]["rejected"]
        if rejected > ALARM_REJECTED:
            self.title.set_text(f"{TITLE}   ALARM: HIGH REJECT RATE")
            self.title.set_color("#d00000")
        else:
            self.title.set_text(TITLE)
            self.title.set_color("#222")

        m = view["counters"]["made"]
        self.counter_text.set_text(
            f"Made:  barrels {m['barrel']}   tips {m['tip']}   "
            f"cartridges {m['cartridge']}   caps {m['cap']}        "
            f"Rejected: {rejected}        Shipped: {shipped}")

    def update(self, _frame):
        self.state.tick()                 # advance the factory ...
        self.draw(self.state.snapshot())  # ... and draw its snapshot
        return self.frame_artists


def build(seed=42, speed=0.13, defect_rate=0.05):
    state = SimulationState(seed=seed, speed=speed, defect_rate=defect_rate)
    return Renderer(state)


if __name__ == "__main__":
    renderer = build()
    ani = FuncAnimation(renderer.fig, renderer.update, frames=TOTAL_FRAMES,
                        interval=50, blit=False)
    out = "ballpen_production_line_hmi.gif"
    ani.save(out, writer=PillowWriter(fps=20))
    print(f"Saved animation to {out}")
