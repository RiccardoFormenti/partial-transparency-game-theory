"""The paper's figures, one function each, saved next to this file as figure_<X>.pdf and
figure_<X>.png. figures.txt describes them.

  figure_A    cooperation at equilibrium against transparency

Run from true/ to draw them all:

    conda run -n py-random python results/figures/figures.py
"""
import json
import re
from fractions import Fraction
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.transforms import ScaledTranslation

HERE = Path(__file__).resolve().parent
# The (t, α) grid with α ∈ {0.5, 0.6, ..., 1}, behavioral family.
SOURCE = HERE.parent / "partial_transparency/alpha_0.5-1/body8/floor/behavioral"

# Viridis at six even steps.
VIRIDIS = ["#440154", "#414487", "#2a788e", "#22a884", "#7ad151", "#fde725"]
NASH_MAX, NASH_MIN = VIRIDIS[0], VIRIDIS[2]
SELECTED = "#a7dcce"  # VIRIDIS[3] at 40% on white: a band the max Nash line runs inside


def game_cooperation(gid):
    """The game's max and min Nash Pr[(C, C)], and the replicator outcome's mean.

    Checks that every start ends in a component of maximum Pr[(C, C)].
    """
    folder = SOURCE / "games" / gid
    eq = json.loads((folder / "equilibria.json").read_text())
    rep = json.loads((folder / "replicator.json").read_text())
    coop = {}
    for c in eq["components"]:
        low, high = (Fraction(c["cooperation"][k]) for k in ("min", "max"))
        coop[c["id"]] = (low, high)
    nash_max = max(high for _, high in coop.values())
    nash_min = min(low for low, _ in coop.values())
    selected = 0
    for c in rep["components"]:
        if c["n_starts"]:
            low, high = coop[c["id"]]
            assert low == high == nash_max, f"{gid}: starts end below max Nash cooperation"
            selected += c["basin"] * float(low)
    assert rep["n_converged"] == rep["n_starts"], f"{gid}: unconverged starts"
    return float(nash_max), float(nash_min), selected


def mean_over_alpha():
    """At each grid t, the equal-weight mean over the grid's α of `game_cooperation`."""
    grid = json.loads((SOURCE / "grid.json").read_text())
    games = {g["id"]: game_cooperation(g["id"]) for g in grid["games"]}
    ts = np.array(sorted(grid["ts"]))
    rows = {t: [] for t in ts}
    for p in grid["points"]:
        rows[p["t"]].append(games[p["game"]])
    assert all(len(r) == len(grid["alphas"]) for r in rows.values())
    nash_max, nash_min, selected = np.array([np.mean(rows[t], axis=0) for t in ts]).T
    return ts, nash_max, nash_min, selected


def style():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "mathtext.fontset": "dejavusans",
        "font.size": 10, "axes.labelsize": 10, "legend.fontsize": 9,
        "xtick.labelsize": 9, "ytick.labelsize": 9,
        "axes.spines.top": False, "axes.spines.right": False,
        "legend.frameon": False,
        "pdf.fonttype": 42, "savefig.dpi": 300,
    })


def save(fig, name):
    for ext in ("pdf", "png"):
        fig.savefig(HERE / f"{name}.{ext}", bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)


def justified(ax, text, right, bottom, width, fontsize, linespacing=1.4, **kw):
    """`text` wrapped to `width` inches and justified, the last line flush left, with the
    bottom right corner at the data point (right, bottom). Matplotlib has no justified text,
    so each word is placed on its own."""
    fig = ax.figure
    renderer = fig.canvas.get_renderer()

    def measure(s):
        t = ax.text(0, 0, s, fontsize=fontsize, **kw)
        w = t.get_window_extent(renderer).width / fig.dpi
        t.remove()
        return w

    space = measure("a a") - measure("aa")
    lines, line = [], []
    for word in re.findall(r"(?:\$[^$]*\$|\S)+", text):  # keeps $...$ whole
        w = measure(word)
        if line and sum(x for _, x in line) + space * len(line) + w > width:
            lines.append(line)
            line = []
        line.append((word, w))
    lines.append(line)
    height = fontsize * linespacing / 72
    for i, line in enumerate(lines):
        last = i == len(lines) - 1 or len(line) == 1
        gap = space if last else (width - sum(w for _, w in line)) / (len(line) - 1)
        x = -width
        for word, w in line:
            shift = ScaledTranslation(x, (len(lines) - 1 - i) * height, fig.dpi_scale_trans)
            ax.text(right, bottom, word, fontsize=fontsize, va="baseline",
                    transform=ax.transData + shift, **kw)
            x += w + gap


def figure_A():
    """Cooperation at equilibrium against transparency, behavioral family.

    At each grid t, the mean over α ∈ {0.5, 0.6, ..., 1} of the maximum and the minimum
    Pr[(C, C)] over the game's Nash equilibria, and of the Pr[(C, C)] the replicator dynamics
    end at. Every replicator start ends in an equilibrium of maximum Pr[(C, C)]
    (`game_cooperation` checks it), so the replicator band holds the max Nash line.
    """
    ts, nash_max, nash_min, selected = mean_over_alpha()
    fig, ax = plt.subplots(figsize=(4.6, 3.4))
    ax.step(ts, nash_min, where="post", color=NASH_MIN, lw=1.6, ls=(0, (1, 1.5)),
            label="min Nash", zorder=2.5)
    ax.step(ts, selected, where="post", color=SELECTED, lw=8, solid_capstyle="butt",
            label="replicator dynamics")
    ax.step(ts, nash_max, where="post", color=NASH_MAX, lw=1.6, label="max Nash")
    justified(ax, "replicator dynamics reach the maximum-cooperation program equilibrium "
              "from all starts, at every transparency-caution pair",
              right=1.0, bottom=0.05, width=2.0, fontsize=8.5, color="#444444")
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.03, 1.03)
    ax.set_xticks(np.linspace(0, 1, 6))
    ax.set_yticks(np.linspace(0, 1, 6))
    ax.set_xlabel(r"transparency $t$")
    ax.set_ylabel("cooperation at equilibrium")
    handles, labels = ax.get_legend_handles_labels()
    order = [2, 1, 0]  # max Nash, replicator, min Nash
    ax.legend([handles[i] for i in order], [labels[i] for i in order],
              loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=3,
              handlelength=1.8, columnspacing=1.4, borderaxespad=0)
    save(fig, "figure_A")


if __name__ == "__main__":
    style()
    figure_A()
