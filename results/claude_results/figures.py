"""Figures: does more transparency lead to more cooperation at equilibrium? Behavioral family.

Draws, from the table summary.py builds, into figures/ next to this file (PDF for the paper,
PNG for previews):

  fig1_phase_diagram       the cooperative region of the (t, α) grid, and its mean over α
  fig2_equilibrium_sets    per α: every Nash component's cooperation, the replicator outcome
                           and the cooperation of the uniform population, against t
  fig3_dupoc_window        why: the window of α in which DupocBot recognizes itself without
                           being exploited, against the grid's outcomes

Run from true/:

    conda run -n py-random python results/claude_results/figures.py

Colors are the dataviz reference palette, checked with its validator: cooperation blue against
partial-cooperation orange, and blue against exploiter red, separate under every color-vision
deficiency. Defection is a neutral gray.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

from summary import FAMILY, build_table, dupoc_masses

HERE = Path(__file__).resolve().parent
OUT = HERE / "figures"

WIDTH = 6.3  # inches: the JAIR text block

# Ink and chrome.
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, SURFACE = "#e1e0d9", "#c3c2b7", "#ffffff"
# Regimes.
COOP, COOP_DARK, COOP_WASH = "#2a78d6", "#184f95", "#cde2fb"
PARTIAL = "#eb6834"
DEFECT, DEFECT_WASH = "#a3a29b", "#ebeae5"
EXPLOIT = "#e34948"
HALF_STEP = 0.005  # half the grid's t step: each grid t owns [t - 0.005, t + 0.005]


def style():
    plt.rcParams.update({
        "font.family": ["Helvetica", "Arial Unicode MS"], "font.size": 7.5,
        "mathtext.fontset": "custom", "mathtext.rm": "Helvetica",
        "mathtext.it": "Helvetica:italic", "mathtext.bf": "Helvetica:bold",
        "axes.edgecolor": AXIS, "axes.linewidth": 0.6, "axes.labelcolor": INK2,
        "axes.labelsize": 7.5, "axes.titlesize": 7.5, "axes.titlecolor": INK,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.facecolor": SURFACE, "figure.facecolor": SURFACE,
        "xtick.color": AXIS, "ytick.color": AXIS, "xtick.labelcolor": INK2,
        "ytick.labelcolor": INK2, "xtick.labelsize": 7, "ytick.labelsize": 7,
        "xtick.major.width": 0.6, "ytick.major.width": 0.6,
        "xtick.major.size": 2.5, "ytick.major.size": 2.5,
        "grid.color": GRID, "grid.linewidth": 0.5,
        "legend.frameon": False, "legend.fontsize": 7, "legend.handlelength": 1.6,
        "lines.solid_capstyle": "round", "lines.solid_joinstyle": "round",
        "pdf.fonttype": 42, "savefig.dpi": 300,
    })


def save(fig, name):
    OUT.mkdir(exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"{name}.{ext}", bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)


def by_alpha(df, a):
    return df[df["alpha"] == a].sort_values("t")


def threshold(d):
    """The lowest t at which the population ends fully cooperative."""
    return d.loc[d["coop_basin"] == 1, "t"].min()


def t_star_label(t_star):
    return rf"$t$* = {t_star:g}"


def transparency_axis(ax, label=True, ends=True):
    ax.set_xlim(-HALF_STEP, 1 + HALF_STEP)
    ax.set_xticks([0, 0.2, 0.4, 0.6, 0.8, 1])
    ax.set_xticklabels(["0", "0.2", "0.4", "0.6", "0.8", "1"])
    if label:
        ax.set_xlabel(r"Transparency $t$", labelpad=3)
    if ends:
        for x, ha, text in ((0, "left", "← opaque: the signal is uniform"),
                            (1, "right", "full: the signal is the opponent's program →")):
            ax.annotate(text, xy=(x, 0), xycoords=("data", "axes fraction"),
                        xytext=(0, -21.5), textcoords="offset points", ha=ha, va="top",
                        fontsize=6.5, color=MUTED)


def panel_letter(ax, letter, dx=-0.075, y=1.0):
    ax.text(dx, y, letter, transform=ax.transAxes, fontsize=9, fontweight="bold",
            color=INK, va="bottom", ha="left")


# --------------------------------------------------------------------------------------------
# Figure 1: the phase diagram


def fig1_phase_diagram(df):
    alphas = sorted(df["alpha"].unique())
    fig = plt.figure(figsize=(WIDTH, 4.1))
    gs = fig.add_gridspec(2, 1, height_ratios=[1, 1.9], hspace=0.32)
    top, low = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])

    # (a) Averaged over the non-trivial cautions.
    mean = df[df["alpha"] > 0].groupby("t")[["coop_basin", "tournament_coop"]].mean()
    ts = mean.index.to_numpy()
    top.fill_between(ts, 0, mean["coop_basin"], step="mid", color=COOP, alpha=0.10, lw=0)
    top.step(ts, mean["coop_basin"], where="mid", color=COOP, lw=2)
    top.step(ts, mean["tournament_coop"], where="mid", color=INK2, lw=1)
    top.set_ylim(0, 1.1)
    top.set_yticks([0, 0.5, 1])
    top.set_yticklabels(["0", "0.5", "1"])
    top.grid(axis="y")
    top.set_axisbelow(True)
    top.set_ylabel(r"Pr[(C, C)]")
    transparency_axis(top, label=False, ends=False)
    top.tick_params(axis="x", labelbottom=False)
    top.text(0.505, 0.875, "At equilibrium: best Nash = replicator outcome",
             color=INK, fontsize=7, ha="left", va="bottom")
    top.text(0.505, 0.33, "Before selection: uniform population of the eight bots",
             color=INK2, fontsize=7, ha="left", va="bottom")
    top.set_title(r"Mean over the six cautions $\alpha \in \{0.2, 0.4, 0.5, 0.6, 0.8, 1\}$",
                  loc="left", color=INK2, fontsize=7, pad=4)
    panel_letter(top, "a")

    # (b) The (t, α) map: one row per caution, cooperative from its threshold up.
    height = 0.74
    for i, a in enumerate(alphas):
        d = by_alpha(df, a)
        t_star = threshold(d)
        x_b = t_star - HALF_STEP
        low.add_patch(Rectangle((-HALF_STEP, i - height / 2), x_b + HALF_STEP, height,
                                color=DEFECT_WASH, lw=0))
        low.add_patch(Rectangle((x_b, i - height / 2), 1 + HALF_STEP - x_b, height,
                                color=COOP_WASH, lw=0))
        if a == 0:
            low.text(0.5, i, "α = 0: every bot cooperates whatever its signal",
                     ha="center", va="center", fontsize=6.5, color=INK2)
            continue
        low.plot([x_b, x_b], [i - height / 2, i + height / 2], color=COOP_DARK, lw=1.6,
                 solid_capstyle="butt")
        if x_b > 0.1:
            low.text(x_b - 0.012, i, t_star_label(t_star), ha="right", va="center",
                     fontsize=7, color=INK)
        else:
            low.text(x_b + 0.012, i, t_star_label(t_star), ha="left", va="center",
                     fontsize=7, color=INK)
    low.text(0.75, 3, "cooperation", ha="center", va="center", fontsize=7.5,
             color=COOP_DARK, fontweight="bold")
    low.text(0.03, 5, "defection", ha="left", va="center", fontsize=7.5,
             color=INK2, fontweight="bold")
    low.set_ylim(-0.6, len(alphas) - 0.4)
    low.set_yticks(range(len(alphas)))
    low.set_yticklabels([f"{a:g}" for a in alphas])
    low.tick_params(axis="y", length=0)
    low.spines["left"].set_visible(False)
    low.set_ylabel(r"Caution $\alpha$")
    transparency_axis(low)
    handles = [
        Patch(color=COOP_WASH, label="Fully cooperative Nash equilibrium, reached from every start"),
        Patch(color=DEFECT_WASH, label="Only fully defecting equilibria"),
    ]
    low.legend(handles=handles, loc="lower left", bbox_to_anchor=(-0.008, 0.995), ncol=2,
               handlelength=1.2, handleheight=0.9, borderaxespad=0.1, columnspacing=1.6,
               labelcolor=INK2, fontsize=6.8)
    panel_letter(low, "b", y=1.075)
    save(fig, "fig1_phase_diagram")


# --------------------------------------------------------------------------------------------
# Figure 2: the Nash equilibrium set and the replicator outcome, per caution


def fig2_equilibrium_sets(df):
    nontrivial = sorted(a for a in df["alpha"].unique() if a > 0)
    fig, axes = plt.subplots(2, 3, figsize=(WIDTH, 3.75), sharex=True, sharey=True,
                             gridspec_kw={"hspace": 0.42, "wspace": 0.12})
    partial_y = 11 / 18
    for ax, a in zip(axes.flat, nontrivial):
        d = by_alpha(df, a)
        t_star = threshold(d)
        ax.set_ylim(-0.09, 1.1)
        ax.set_yticks([0, partial_y, 1])
        ax.set_yticklabels(["0", "11/18", "1"])
        ax.grid(axis="y")
        ax.set_axisbelow(True)
        ax.axvline(t_star, color=AXIS, lw=0.6, zorder=1)

        # The replicator outcome, as a highlight behind the component it selects.
        ax.step(d["t"], d["rep_coop_mean"], where="mid", color=INK, alpha=0.14, lw=7.5,
                solid_capstyle="butt", zorder=2)
        # Before selection.
        ax.step(d["t"], d["tournament_coop"], where="mid", color=INK2, lw=0.9, zorder=3)
        # The Nash components, each from the lowest t at which it exists.
        for has, y, color in (("has_defection", 0, DEFECT), ("has_partial", partial_y, PARTIAL),
                              ("has_cooperation", 1, COOP)):
            ts = d.loc[d[has], "t"]
            if ts.empty:
                continue
            lo = ts.min()
            if lo < 1:
                ax.plot([lo, 1], [y, y], color=color, lw=2, zorder=4)
            if lo > 0:  # a dot where the component appears; one present at t = 0 needs none
                ax.plot([lo], [y], "o", color=color, ms=4.2, mec=SURFACE, mew=1.1, zorder=5)

        ax.set_title(rf"$\alpha = {a:g}$", loc="left", fontweight="bold", pad=3)
        right = t_star > 0.15
        ax.text(t_star + (-0.025 if right else 0.025), 0.80, t_star_label(t_star),
                ha="right" if right else "left", va="center", fontsize=6.8, color=INK)
        ax.set_xlim(-0.03, 1.03)
        ax.set_xticks([0, 0.5, 1])
        ax.set_xticklabels(["0", "0.5", "1"])
    for ax in axes[1]:
        ax.set_xlabel(r"Transparency $t$")
    for ax in axes[:, 0]:
        ax.set_ylabel("Pr[(C, C)]")
    blank = Line2D([], [], alpha=0, label=" ")
    # Column-major for ncol=3, so that it reads row by row: Nash first, then the rest.
    handles = [
        Line2D([], [], color=COOP, lw=2, label="Fully cooperative Nash equilibria"),
        Line2D([], [], color=INK, alpha=0.14, lw=7.5, solid_capstyle="butt",
               label="Replicator outcome (all 1000 starts)"),
        Line2D([], [], color=PARTIAL, lw=2, label="Partially cooperative (11/18)"),
        Line2D([], [], color=INK2, lw=0.9, label="Uniform population, before selection"),
        Line2D([], [], color=DEFECT, lw=2, label="Fully defecting"),
        blank,
    ]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.085, 0.925), ncol=3,
               columnspacing=1.6, labelcolor=INK2)
    save(fig, "fig2_equilibrium_sets")


# --------------------------------------------------------------------------------------------
# Figure 3: why. DupocBot's window between recognition and exploitation


def fig3_dupoc_window(df):
    m = dupoc_masses()
    nontrivial = sorted(a for a in df["alpha"].unique() if a > 0)
    fig, ax = plt.subplots(figsize=(WIDTH, 3.35))

    ax.fill_between(m["t"], m["OBot"], m["DupocBot"], color=COOP_WASH, lw=0, zorder=0)
    # The grid's outcomes, one row per caution.
    for a in nontrivial:
        d = by_alpha(df, a)
        x_b = threshold(d) - HALF_STEP
        if x_b > 0:
            ax.plot([0, x_b], [a, a], color=DEFECT, lw=3.2, solid_capstyle="butt", zorder=1)
        ax.plot([x_b, 1], [a, a], color=COOP, lw=3.2, solid_capstyle="butt", zorder=1)
        ax.text(1.012, a, rf"$\alpha = {a:g}$", ha="left", va="center", fontsize=6.8,
                color=INK2)
    ax.plot(m["t"], m["DupocBot"], color=INK, lw=1.6, zorder=3)
    ax.plot(m["t"], m["OBot"], color=EXPLOIT, lw=1.6, zorder=3)
    ax.plot(m["t"], m["DefectBot"], color=EXPLOIT, lw=0.9, alpha=0.6, zorder=3)
    meet = m.loc[m["t"] == 0, "DupocBot"].item()
    ax.plot([0], [meet], "o", color=INK, ms=4.5, mec=SURFACE, mew=1.1, zorder=4, clip_on=False)

    # Direct labels on the curves.
    ax.annotate("DupocBot's mass facing itself", xy=(0.36, 0.700), xytext=(0.20, 0.93),
                fontsize=7, color=INK, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6, shrinkB=1))
    ax.annotate("facing OBot", xy=(0.47, 0.121), xytext=(0.53, 0.28), fontsize=7,
                color=INK, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6, shrinkB=1))
    ax.annotate("facing DefectBot", xy=(0.62, 0.021), xytext=(0.66, 0.13), fontsize=7,
                color=INK2, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6, shrinkB=1))
    ax.text(0.012, 0.035, "At t = 0 all three masses are 3/8", fontsize=6.5, color=INK2,
            ha="left", va="center")
    # The three regions.
    ax.text(0.02, 1.05, "Above: DupocBot defects against itself, it no longer recognizes a "
                        "fellow cooperator", fontsize=6.8, color=INK2, ha="left", va="center")
    ax.text(0.98, -0.065, "Below: DupocBot cooperates with a defector, which exploits it",
            fontsize=6.8, color=INK2, ha="right", va="center")
    ax.text(0.78, 0.70, "Inside: cooperation\ncan be an equilibrium", fontsize=7.5,
            color=COOP_DARK, fontweight="bold", ha="center", va="center", linespacing=1.3)

    ax.set_xlim(0, 1)
    ax.set_ylim(-0.1, 1.1)
    ax.set_yticks([0, 0.2, meet, 0.6, 0.8, 1])
    ax.set_yticklabels(["0", "0.2", "3/8", "0.6", "0.8", "1"])
    ax.set_ylabel(r"Caution $\alpha$, and DupocBot's mass")
    ax.spines["left"].set_bounds(0, 1)
    transparency_axis(ax)
    ax.set_xlim(0, 1)
    handles = [
        Patch(color=COOP_WASH, label="DupocBot recognizes itself, unexploited"),
        Line2D([], [], color=COOP, lw=3.2, solid_capstyle="butt",
               label="Grid: population ends cooperative"),
        Line2D([], [], color=DEFECT, lw=3.2, solid_capstyle="butt", label="ends defecting"),
    ]
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(-0.008, 1.03), ncol=3,
              handlelength=1.4, handleheight=0.9, columnspacing=1.4, labelcolor=INK2,
              fontsize=6.8, borderaxespad=0)
    save(fig, "fig3_dupoc_window")


def main():
    style()
    df = build_table()
    fig1_phase_diagram(df)
    fig2_equilibrium_sets(df)
    fig3_dupoc_window(df)
    print(f"{FAMILY}: wrote {sorted(p.name for p in OUT.iterdir())}")


if __name__ == "__main__":
    main()
