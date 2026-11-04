"""The paper's figures, one function each, saved next to this file as figure_<X>.pdf and
figure_<X>.png. figures.txt describes them.

  figure_A    cooperation at equilibrium against transparency, mean over α
  figure_B    critical transparency against caution α
  figure_C    cooperation at equilibrium against transparency, one panel per α
  figure_D    figures C and B side by side
  figure_E    the Nash components at each (t, α)

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
from matplotlib.lines import Line2D
from matplotlib.transforms import ScaledTranslation

HERE = Path(__file__).resolve().parent
# The (t, α) grid with α ∈ {0.5, 0.6, ..., 1}, one folder per family.
SWEEP = HERE.parent / "partial_transparency/alpha_0.5-1/body8/floor"

# Viridis at six even steps.
VIRIDIS = ["#440154", "#414487", "#2a788e", "#22a884", "#7ad151", "#fde725"]
NASH_MAX, NASH_MIN = VIRIDIS[0], VIRIDIS[2]
SELECTED = "#a7dcce"  # VIRIDIS[3] at 40% on white: a band the max Nash line runs inside


def game_cooperation(folder, at_max):
    """The game's max and min Nash Pr[(C, C)], and the replicator outcome's mean.

    With `at_max`, checks that every start ends in a component of maximum Pr[(C, C)].
    """
    gid = folder.name
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
            assert low == high, f"{gid}: component {c['id']} is not constant"
            assert not at_max or low == nash_max, f"{gid}: starts end below max Nash cooperation"
            selected += c["basin"] * float(low)
    assert rep["n_converged"] == rep["n_starts"], f"{gid}: unconverged starts"
    return float(nash_max), float(nash_min), selected


def grid_cooperation(family="behavioral", at_max=True):
    """The grid's t (ascending) and α, and at each grid point (t, α) its game's
    `game_cooperation`."""
    source = SWEEP / family
    grid = json.loads((source / "grid.json").read_text())
    games = {g["id"]: game_cooperation(source / "games" / g["id"], at_max) for g in grid["games"]}
    coop = {(p["t"], p["alpha"]): games[p["game"]] for p in grid["points"]}
    return np.array(sorted(grid["ts"])), sorted(grid["alphas"]), coop


def mean_over_alpha():
    """At each grid t, the equal-weight mean over the grid's α of `game_cooperation`,
    behavioral family."""
    ts, alphas, coop = grid_cooperation()
    means = [np.mean([coop[(t, a)] for a in alphas], axis=0) for t in ts]
    nash_max, nash_min, selected = np.array(means).T
    return ts, nash_max, nash_min, selected


def by_alpha(family="behavioral", at_max=True):
    """For each α: the grid's t (ascending), and the max Nash and replicator Pr[(C, C)] there."""
    ts, alphas, coop = grid_cooperation(family, at_max)
    curves = {}
    for a in alphas:
        nash_max, _, selected = np.array([coop[(t, a)] for t in ts]).T
        curves[a] = ts, nash_max, selected
    return curves


def critical(ts, selected):
    """The critical transparency: the lowest grid t from which on the replicator dynamics end
    in full cooperation. Checks that they end in full defection below it, so the switch lies
    between that t and the grid t just below it."""
    on = np.isclose(selected, 1, rtol=0, atol=1e-9)
    i = np.argmax(on)
    assert np.allclose(selected[:i], 0, rtol=0, atol=1e-9) and on[i:].all(), \
        "not one switch from defection to cooperation"
    return ts[i]


def component_levels(family="behavioral"):
    """The grid's t (ascending) and α, and at each grid point (t, α) the Pr[(C, C)] of each
    Nash component of its game, ascending."""
    source = SWEEP / family
    grid = json.loads((source / "grid.json").read_text())
    levels = {}
    for g in grid["games"]:
        eq = json.loads((source / "games" / g["id"] / "equilibria.json").read_text())
        coop = [tuple(Fraction(c["cooperation"][k]) for k in ("min", "max"))
                for c in eq["components"]]
        assert all(low == high for low, high in coop), f"{g['id']}: a component is not constant"
        levels[g["id"]] = tuple(sorted(low for low, _ in coop))
    points = {(p["t"], p["alpha"]): levels[p["game"]] for p in grid["points"]}
    return np.array(sorted(grid["ts"])), sorted(grid["alphas"]), points


def style():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "mathtext.fontset": "dejavusans",
        "font.size": 10, "axes.labelsize": 10, "legend.fontsize": 9,
        "xtick.labelsize": 9, "ytick.labelsize": 9,
        "axes.spines.top": False, "axes.spines.right": False,
        "legend.frameon": False,
        "pdf.fonttype": 42, "savefig.dpi": 300,
    })


def tint(color, share):
    """`color` laid at opacity `share` on white."""
    return share * np.array(matplotlib.colors.to_rgb(color)) + (1 - share)


def save(fig, name):
    for ext in ("pdf", "png"):
        fig.savefig(HERE / f"{name}.{ext}", bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)


def justified(ax, text, right, bottom, width, fontsize, linespacing=1.4, **kw):
    """`text` justified in a box `width` inches wide, the last line flush left, with the bottom
    right corner at the data point (right, bottom). Matplotlib has no justified text, so each
    word is placed on its own.

    As in TeX, a line may also break after a hyphen, and the breaks are chosen together to keep
    every gap near a normal space: a gap may stretch, or shrink to 3/4 of a space.
    """
    fig = ax.figure
    renderer = fig.canvas.get_renderer()

    def measure(s):
        t = ax.text(0, 0, s, fontsize=fontsize, **kw)
        w = t.get_window_extent(renderer).width / fig.dpi
        t.remove()
        return w

    space = measure("a a") - measure("aa")
    # (piece, its width, whether a space precedes it): words, split after their hyphens.
    pieces = []
    for word in re.findall(r"(?:\$[^$]*\$|\S)+", text):  # keeps $...$ whole
        parts = [word] if "$" in word else re.findall(r"[^-]+-?|-", word)
        pieces += [(p, measure(p), i == 0) for i, p in enumerate(parts)]
    n = len(pieces)

    def badness(i, j):
        """How far the gaps of a line of pieces[i:j] lie from a space, or None if it can't be set."""
        line = pieces[i:j]
        gaps = sum(spaced for _, _, spaced in line[1:])
        ink = sum(w for _, w, _ in line)
        if j == n:  # flush left, at normal spacing; not a lone word
            return None if ink + space * gaps > width else 0 if j - i > 1 else 100
        if not gaps or ink + 0.75 * space * gaps > width:
            return None
        hyphen = 0 if pieces[j][2] else 2
        return ((width - ink) / gaps / space - 1) ** 2 + hyphen

    best = {n: (0, [])}  # i -> least total badness of setting pieces[i:], and its line ends
    for i in reversed(range(n)):
        options = [(b + best[j][0], [j] + best[j][1]) for j in range(i + 1, n + 1)
                   if j in best and (b := badness(i, j)) is not None]
        if options:
            best[i] = min(options)
    assert 0 in best, f"no way to set the text {width} inches wide"
    ends = best[0][1]

    height = fontsize * linespacing / 72
    start = 0
    for k, end in enumerate(ends):
        line = pieces[start:end]
        gaps = sum(spaced for _, _, spaced in line[1:])
        gap = space if end == n else (width - sum(w for _, w, _ in line)) / gaps
        x = -width
        for i, (piece, w, spaced) in enumerate(line):
            x += gap if spaced and i else 0
            shift = ScaledTranslation(x, (len(ends) - 1 - k) * height, fig.dpi_scale_trans)
            ax.text(right, bottom, piece, fontsize=fontsize, va="baseline",
                    transform=ax.transData + shift, **kw)
            x += w
        start = end


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
              right=1.0, bottom=0.05, width=2.33, fontsize=8, color="#444444")
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


def figure_B():
    """Critical transparency against caution, both families.

    At each α, the lowest grid t from which on the replicator dynamics end in full cooperation;
    below it they end in full defection. Behavioral family solid, its points colored by α as
    in figure C; syntactic dashed and lighter, without points. In the syntactic family the
    replicator outcome can lie below max Nash cooperation, so its starts are not checked to
    end at it.
    """
    fig, ax = plt.subplots(figsize=(4.6, 3.4))
    draw_B(ax)
    save(fig, "figure_B")


def draw_B(ax):
    """Figure B on `ax`."""
    for family, ls, opacity in (("behavioral", "-", 1), ("syntactic", (0, (4, 2)), 0.6)):
        curves = by_alpha(family, at_max=False)
        alphas = list(curves)
        crit = [critical(ts, selected) for ts, _, selected in curves.values()]
        ax.plot(alphas, crit, color="#888888", lw=1.2, ls=ls, alpha=opacity, zorder=1,
                label=family)
        if family == "behavioral":
            ax.scatter(alphas, crit, c=VIRIDIS, s=45, edgecolors="white", linewidths=0.8,
                       zorder=2)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=2, handlelength=2.4,
              columnspacing=1.4, borderaxespad=0)
    ax.text(0.5, 0.9, "cooperation", fontsize=9, color="#444444")
    ax.text(1.0, 0.08, "defection", ha="right", fontsize=9, color="#444444")
    ax.set_xlim(0.47, 1.03)
    ax.set_ylim(-0.03, 1.03)
    ax.set_xticks(alphas)
    ax.set_yticks(np.linspace(0, 1, 6))
    ax.set_xlabel(r"caution $\alpha$")
    ax.set_ylabel(r"critical transparency $t^*$")


def figure_C():
    """Cooperation at equilibrium against transparency, one panel per α, behavioral family.

    Each panel is the Pr[(C, C)] the replicator dynamics end at, in the α's color. It equals
    max Nash cooperation (figure A). Each α switches once, at its critical transparency t*
    (figure B), from full defection to full cooperation.
    """
    fig = plt.figure(figsize=(7, 4.2), layout="constrained")
    draw_C(fig)
    save(fig, "figure_C")


def draw_C(fig):
    """Figure C's six panels in `fig`, a figure or a subfigure."""
    curves = by_alpha()
    axes = fig.subplots(2, 3, sharex=True, sharey=True)
    for ax, a, color in zip(axes.flat, curves, VIRIDIS, strict=True):
        ts, nash_max, selected = curves[a]
        t = critical(ts, selected)
        off, on = ts < t, ts >= t
        # Solid where cooperation is constant, dashed at the switch, a dot where it starts.
        ax.plot(np.r_[ts[off], t], np.r_[selected[off], selected[off][-1]], color=color, lw=1.8)
        ax.plot(ts[on], selected[on], color=color, lw=1.8)
        ax.plot([t, t], [selected[off][-1], selected[on][0]], color=color, lw=1.2,
                ls=(0, (3, 2)))
        ax.plot(t, selected[on][0], "o", color=color, ms=4)
        left = t > 0.5  # label the switch on its emptier side
        ax.text(t - 0.05 if left else t + 0.05, 0.5, rf"$t^* = {t:g}$", fontsize=8.5,
                ha="right" if left else "left", va="center", color="#444444")
        ax.set_title(rf"$\alpha = {a:g}$", fontsize=10)
    ax.set_xlim(-0.03, 1.03)
    ax.set_ylim(-0.05, 1.05)
    ax.set_xticks([0, 0.5, 1], ["0", "0.5", "1"])  # shared by every panel
    ax.set_yticks([0, 0.5, 1], ["0", "0.5", "1"])
    fig.supxlabel(r"transparency $t$", fontsize=10)
    fig.supylabel("cooperation at equilibrium", fontsize=10)
    fig.legend(handles=[Line2D([], [], color="#444444", lw=1.8, label="replicator dynamics")],
               loc="outside upper center", handlelength=1.8)


def figure_D():
    """Figures C and B side by side, as panels (a) and (b)."""
    fig = plt.figure(figsize=(10, 4.6), layout="constrained")
    left, right = fig.subfigures(1, 2, width_ratios=[6, 4])
    draw_C(left)
    draw_B(right.subplots())
    for sub, label in ((left, "(a)"), (right, "(b)")):
        sub.text(0, 1, label, fontsize=11, fontweight="bold", va="top")
    save(fig, "figure_D")


def figure_E():
    """The Nash components against transparency and caution, behavioral family.

    Only three sets of components occur, each component with a single Pr[(C, C)]: defection
    alone; defection and full cooperation; and those two with the partial cooperation 11/18.
    As t grows, each α gains them in that order: full cooperation at t* (figure B), the
    partial one at t**. The two boundaries connect their values at the six sampled α (dots),
    and the three regions between them are shaded in viridis tints, from 1 component to 3.
    """
    ts, alphas, points = component_levels()
    count = {(0,): 1, (0, 1): 2, (0, Fraction(11, 18), 1): 3}  # components' Pr[(C, C)]
    unknown = set(points.values()) - set(count)
    assert not unknown, f"unexpected component sets: {unknown}"
    t_full, t_partial = [], []
    for a in alphas:
        n = np.array([count[points[(t, a)]] for t in ts])
        assert np.all(np.diff(n) >= 0) and n[-1] == 3, f"α = {a}: components not gained in order"
        t_full.append(ts[np.argmax(n >= 2)])
        t_partial.append(ts[np.argmax(n == 3)])

    fig, ax = plt.subplots(figsize=(4.6, 3.4))
    regions = [  # (left edge, right edge, color, label)
        (np.zeros(len(alphas)), t_full, tint(VIRIDIS[0], 0.3), "1: defection only"),
        (t_full, t_partial, tint("#21918c", 0.4), "2: + full cooperation"),
        (t_partial, np.ones(len(alphas)), tint(VIRIDIS[5], 0.5), "3: + partial (11/18)"),
    ]
    for left, right, color, _ in regions:
        ax.fill_betweenx(alphas, left, right, color=color, lw=0)
    for edge in (t_full, t_partial):
        ax.plot(edge, alphas, color="#444444", lw=1.2, marker="o", ms=3.5, clip_on=False)
    # Labels inside the regions; the middle one runs along its band.
    ink = dict(fontsize=8.5, color="#333333", ha="center", va="center")
    ax.text(0.2, 0.86, "1: defection only", **ink)
    ax.text(0.8, 0.6, "3: + partial (11/18)", **ink)
    a0, a1 = 0.6, 0.8
    (x0, y0), (x1, y1) = ax.transData.transform([
        (np.interp(a0, alphas, t_full), a0), (np.interp(a1, alphas, t_full), a1)])
    mid = 0.7
    ax.text((np.interp(mid, alphas, t_full) + np.interp(mid, alphas, t_partial)) / 2, mid,
            "2: + full cooperation", rotation=np.degrees(np.arctan2(y1 - y0, x1 - x0)),
            rotation_mode="anchor", **ink)
    ax.set_xlim(0, 1)
    ax.set_ylim(alphas[0], alphas[-1])
    ax.set_xticks(np.linspace(0, 1, 6))
    ax.set_yticks(alphas, [f"{a:g}" for a in alphas])
    ax.set_xlabel(r"transparency $t$")
    ax.set_ylabel(r"caution $\alpha$")
    ax.set_title("Nash components", fontsize=10)
    save(fig, "figure_E")


if __name__ == "__main__":
    style()
    figure_A()
    figure_B()
    figure_C()
    figure_D()
    figure_E()
