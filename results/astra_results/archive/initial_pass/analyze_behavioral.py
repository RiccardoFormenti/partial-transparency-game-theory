#!/usr/bin/env python3
"""Audit saved behavioral results and build the figures; never rerun or overwrite a game.

Run from the repository root:
    conda run -n py-random python true/results/astra_results/analyze_behavioral.py

All generated files, caches, and this script live under results/astra_results.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import sys
from fractions import Fraction
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TRUE = HERE.parent.parent
SOURCE = HERE.parent / "partial_transparency/body8/floor/behavioral"
os.environ.setdefault("MPLCONFIGDIR", str(HERE / ".mplconfig"))
sys.path.insert(0, str(TRUE))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import PercentFormatter
from scipy.stats import norm

from replication.general.equilibria import analyse, exact, lrsnash_input, parse_lrsnash
from replication.full_transparency.nash import _record
from replication.general.zoo import load_zoo
from replication.partial_transparency.signals import transparency

FIGURES = HERE / "figures"
TABLES = HERE / "tables"
INK = "#20313D"
MUTED = "#61727D"
TEAL = "#007F78"
TEAL_LIGHT = "#DBEFEB"
GRAY = "#CED5D9"
GOLD = "#B46C19"
PURPLE = "#7963A5"
BG = "#FFFFFF"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def wilson(k, n):
    """Pointwise 95% Wilson interval, never pooling repeated grid games."""
    z = norm.ppf(0.975)
    p = k / n
    d = 1 + z * z / n
    center = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (0.0 if k == 0 else max(0, center - half),
            1.0 if k == n else min(1, center + half))


def read_and_audit():
    grid = json.loads((SOURCE / "grid.json").read_text())
    bots = grid["bots"]
    require(grid["family"] == "behavioral", "Wrong signal family")
    require(len(grid["points"]) == len(grid["ts"]) * len(grid["alphas"]), "Incomplete grid")
    require(len({(p['t'], p['alpha']) for p in grid['points']}) == len(grid['points']), "Duplicate point")
    require(not grid["twins"] and not grid["unreached"], "Unreached transparency levels")
    zoo = load_zoo("body8", "floor")
    channels = {c['t']: c for c in grid['channels']}
    for c in channels.values():
        ch = np.asarray(c['channel'])
        require(np.allclose(ch.sum(axis=1), 1, atol=1e-12, rtol=0), "Signal not normalized")
        measured = transparency({b: dict(zip(bots, row)) for b, row in zip(bots, ch)})
        require(abs(measured - c['transparency']) < 1e-12, "Information calibration mismatch")

    games, components, composition, provenance = [], [], [], []
    game_data = {}
    common_starts = None
    max_gain = max_cc_error = max_payoff_error = 0.0
    input_paths = [SOURCE / "grid.json"]
    for g in grid["games"]:
        gid = g["id"]
        folder = SOURCE / "games" / gid
        eq = json.loads((folder / "equilibria.json").read_text())
        rep = json.loads((folder / "replicator.json").read_text())
        runs = pd.read_csv(folder / "replicator_runs.csv")
        for name in ('equilibria.json', 'replicator.json', 'replicator_runs.csv',
                     'lrsnash_input.txt', 'lrsnash_output.txt'):
            input_paths.append(folder / name)
        require(eq['bots'] == rep['bots'] == bots, f"{gid}: bot ordering")
        require(eq['A'] == rep['A'], f"{gid}: payoff mismatch")
        require(eq['points'] == rep['points'] == g['points'], f"{gid}: grid mapping")
        require(rep['settings']['horizon'] == g['horizon'], f"{gid}: horizon")

        # Reparse the complete raw enumeration and recheck exact best responses,
        # pure equilibria, mirrors, component ranges and all recorded values.
        A_exact = exact(eq['A'])
        cells = {(a, b): tuple(eq['cells'][i][j])
                 for i, a in enumerate(bots) for j, b in enumerate(bots)}
        require(lrsnash_input(A_exact) == (folder / 'lrsnash_input.txt').read_text(),
                f"{gid}: solver input")
        pairs = parse_lrsnash((folder / 'lrsnash_output.txt').read_text(), len(bots))
        found = analyse(tuple(bots), cells, A_exact, pairs)
        about = {k: eq[k] for k in ('family', 'game', 'points')}
        require(_record(zoo, cells, A_exact, found, about) == eq, f"{gid}: exact enumeration")
        C = (np.asarray(eq['cells']) == 'CC').astype(float)
        A = np.asarray(A_exact, dtype=float)
        payoff_for_cell = {'CC': 2, 'CD': -1, 'DC': 3, 'DD': 0}
        require(np.array_equal(A, [[payoff_for_cell[c] for c in row] for row in eq['cells']]),
                f"{gid}: payoffs do not follow actions")
        require(len(runs) == rep['n_starts'] == 1000, f"{gid}: sample size")
        require(runs['converged'].all() and rep['n_converged'] == 1000, f"{gid}: unconverged runs")
        require(runs['run'].tolist() == list(range(1000)), f"{gid}: run IDs")
        X = runs[[f'start:{b}' for b in bots]].to_numpy()
        Y = runs[[f'end:{b}' for b in bots]].to_numpy()
        require((X > 0).all() and (Y >= 0).all(), f"{gid}: negative or boundary start")
        require(np.allclose(X.sum(1), 1, atol=1e-12, rtol=0) and
                np.allclose(Y.sum(1), 1, atol=1e-12, rtol=0), f"{gid}: normalization")
        if common_starts is None:
            common_starts = X
            expected = np.random.default_rng(rep['settings']['seed']).dirichlet(np.ones(len(bots)), 1000)
            require(np.allclose(X, expected, atol=1e-14, rtol=0), "Seed / Dirichlet starts")
        require(np.array_equal(X, common_starts), f"{gid}: starts are not paired")
        c_start = np.einsum('ri,ij,rj->r', X, C, X)
        c_end = np.einsum('ri,ij,rj->r', Y, C, Y)
        payoff = np.einsum('ri,ij,rj->r', Y, A, Y)
        cc_error = float(np.max(np.abs(c_end - runs.cooperation)))
        payoff_error = float(np.max(np.abs(payoff - runs.payoff)))
        gain = float(np.max(Y @ A.T - payoff[:, None]))
        max_gain = max(max_gain, gain)
        max_cc_error = max(max_cc_error, cc_error)
        max_payoff_error = max(max_payoff_error, payoff_error)
        require(cc_error < 1e-12 and payoff_error < 1e-12, f"{gid}: endpoint observables")
        require(gain <= rep['settings']['tolerance'] + 1e-12, f"{gid}: profitable endpoint deviation")
        require(runs.distance.max() <= rep['settings']['max_distance'], f"{gid}: component distance")
        require(np.all((abs(c_end) < 1e-9) | (abs(c_end - 1) < 1e-9)),
                f"{gid}: outcomes are not binary; adapt figure and interval definitions")
        success = int(np.sum(abs(c_end - 1) < 1e-9))
        ci_low, ci_high = wilson(success, len(runs))
        rates = [e.cooperation for e in found]
        symmetric_rates = [e.cooperation for e in found if e.symmetric]
        for comp in eq['components']:
            low, high = (Fraction(comp['cooperation'][s]) for s in ('min', 'max'))
            require(low == high, f"{gid}: nonconstant component; plot its range instead")
            rc = next(c for c in rep['components'] if c['id'] == comp['id'])
            subset = runs[runs.component == comp['id']]
            require(len(subset) == rc['n_starts'], f"{gid}: component count")
            require(abs(rc['basin'] - len(subset) / len(runs)) < 1e-12, f"{gid}: basin")
            if len(subset):
                require(np.allclose(subset.cooperation, float(low), atol=1e-9, rtol=0),
                        f"{gid}: selected component cooperation")
            components.append(dict(game=gid, component=comp['id'], cooperation_exact=str(low),
                                   cooperation=float(low), n_extreme=len(comp['equilibria']),
                                   n_symmetric=comp['n_symmetric'], n_starts=len(subset),
                                   basin=rc['basin'], bots=';'.join(comp['bots'])))
        for b, value in zip(bots, Y.mean(axis=0)):
            composition.append(dict(game=gid, bot=b, mean_final_share=float(value)))
        q25, q75 = np.quantile(c_start, [.25, .75])
        item = dict(game=gid, n_points=len(g['points']), n_equilibria=len(found),
                    n_components=len(eq['components']), n_symmetric=len(symmetric_rates),
                    nash_min=float(min(rates)), nash_max=float(max(rates)),
                    symmetric_nash_min=float(min(symmetric_rates)),
                    symmetric_nash_max=float(max(symmetric_rates)),
                    n_starts=len(runs), n_converged=int(runs.converged.sum()),
                    n_cooperative=success, cooperative_basin=success / len(runs),
                    basin_ci95_low=ci_low, basin_ci95_high=ci_high,
                    selected_cooperation=float(np.clip(c_end.mean(), 0, 1)),
                    initial_cooperation_mean=float(c_start.mean()),
                    initial_cooperation_q25=float(q25), initial_cooperation_q75=float(q75),
                    equal_mix_cooperation=float(C.mean()), horizon=rep['settings']['horizon'],
                    max_deviation_gain=gain, max_component_distance=float(runs.distance.max()))
        games.append(item)
        game_data[gid] = eq

    records = []
    by_id = {g['game']: g for g in games}
    for p in grid['points']:
        eq = game_data[p['game']]
        require(eq['cells'] == p['cells'], "Point mapped to wrong game")
        short = np.asarray(channels[p['t']]['shortfall'])
        actions = np.where(short <= (1 - p['alpha']) * (1 + grid['settings']['tie_tolerance']), 'C', 'D')
        require([[actions[i, j] + actions[j, i] for j in range(len(bots))]
                 for i in range(len(bots))] == p['cells'], "Point action rule mismatch")
        require(abs(p['mutual_cooperation'] - by_id[p['game']]['equal_mix_cooperation']) < 1e-12,
                "Uniform tournament cooperation mismatch")
        records.append(dict(t=p['t'], alpha=p['alpha'], measured_t=channels[p['t']]['transparency'],
                            **by_id[p['game']]))
    points = pd.DataFrame(records).sort_values(['alpha', 't']).reset_index(drop=True)
    games_df = pd.DataFrame(games)
    components_df = pd.DataFrame(components)
    thresholds = []
    for a, group in points.groupby('alpha'):
        winners = group[group.nash_max == 1]
        first = winners.iloc[0]
        below = group[group.t < first.t]
        last = below.iloc[-1] if len(below) else None
        thresholds.append(dict(alpha=a, first_cooperative_t=first.t,
                               last_defecting_t=None if last is None else last.t,
                               first_cooperative_measured_t=first.measured_t,
                               information_bits=3 * first.measured_t,
                               first_cooperative_game=first.game,
                               last_defecting_game=None if last is None else last.game,
                               n_grid_cooperative=len(winners), n_grid_points=len(group),
                               nash_decreases=int(np.sum(np.diff(group.nash_max) < -1e-10)),
                               selected_decreases=int(np.sum(np.diff(group.selected_cooperation) < -1e-10))))
    thresholds_df = pd.DataFrame(thresholds)
    comparisons = len(grid['alphas']) * (len(grid['ts']) - 1)
    agrees = np.isclose(points.nash_max, points.cooperative_basin, atol=1e-9, rtol=0)
    full_game = points[(points.t == 1) & (points.alpha == .5)].iloc[0].game
    audit = dict(family='behavioral', zoo='body8', side='floor', n_grid_points=len(points),
                 n_distinct_games=len(games_df), n_actual_runs=int(games_df.n_starts.sum()),
                 n_distinct_initial_populations=len(common_starts),
                 n_extreme_equilibria_checked=int(games_df.n_equilibria.sum()),
                 n_components_checked=len(components_df),
                 seed=20260514, max_cooperation_recompute_error=max_cc_error,
                 max_payoff_recompute_error=max_payoff_error,
                 max_endpoint_deviation_gain=max_gain,
                 max_reported_component_distance=float(games_df.max_component_distance.max()),
                 max_transparency_calibration_error=float(abs(points.measured_t - points.t).max()),
                 all_runs_converged=bool((games_df.n_converged == games_df.n_starts).all()),
                 n_grid_agreements=int(agrees.sum()),
                 n_adjacent_comparisons=comparisons,
                 n_selected_decreases=int(thresholds_df.selected_decreases.sum()),
                 n_nash_max_decreases=int(thresholds_df.nash_decreases.sum()),
                 defection_equilibrium_at_every_positive_alpha=bool((points.loc[points.alpha > 0, 'nash_min'] == 0).all()),
                 symmetric_and_all_nash_max_agree=bool((points.nash_max == points.symmetric_nash_max).all()),
                 all_components_have_constant_cooperation=True,
                 full_transparency_game=full_game,
                 pointwise_wilson_1000_of_1000=list(wilson(1000, 1000)),
                 pointwise_wilson_0_of_1000=list(wilson(0, 1000)),
                 python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,
                 scipy=scipy.__version__, matplotlib=matplotlib.__version__)
    for p in input_paths:
        provenance.append(dict(path=str(p.relative_to(TRUE.parent)),
                               sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    for name, frame in [('grid_metrics', points), ('game_metrics', games_df),
                        ('nash_components', components_df), ('thresholds', thresholds_df),
                        ('final_composition_by_game', pd.DataFrame(composition)),
                        ('source_manifest', pd.DataFrame(provenance))]:
        frame.to_csv(TABLES / f'{name}.csv', index=False, float_format='%.12g')
    (HERE / 'audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    return points, thresholds_df, components_df, audit


def style():
    plt.rcParams.update({
        'font.family': 'DejaVu Sans', 'font.size': 9,
        'axes.titlesize': 11, 'axes.titleweight': 'bold', 'axes.labelsize': 9,
        'text.color': INK, 'axes.labelcolor': INK, 'xtick.color': MUTED, 'ytick.color': MUTED,
        'axes.edgecolor': GRAY, 'axes.spines.top': False, 'axes.spines.right': False,
        'axes.linewidth': .7, 'xtick.major.size': 3, 'ytick.major.size': 3,
        'figure.facecolor': BG, 'axes.facecolor': BG, 'savefig.facecolor': BG,
        'pdf.fonttype': 42, 'ps.fonttype': 42, 'svg.fonttype': 'none',
        'mathtext.fontset': 'dejavusans', 'savefig.dpi': 300,
    })


def heading(fig, title, subtitle):
    fig.text(.065, .955, title, fontsize=17, weight='bold', va='top')
    fig.text(.065, .900, subtitle, fontsize=9, color=MUTED, va='top')


def footnote(fig, text):
    fig.text(.065, .025, text, fontsize=8, color=MUTED, va='bottom', linespacing=1.5)


def save(fig, name):
    for ext in ('pdf', 'svg', 'png'):
        fig.savefig(FIGURES / f'{name}.{ext}', bbox_inches=None)
    plt.close(fig)


def base_axis(ax):
    ax.set_xlim(-.02, 1.02)
    ax.set_xticks([0, .2, .4, .6, .8, 1])
    ax.set_ylim(-.045, 1.055)
    ax.set_yticks([0, .5, 1])
    ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    ax.grid(axis='y', color='#E9ECEE', linewidth=.7, zorder=0)
    ax.set_axisbelow(True)


def figure_phase(points, thresholds):
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 6.1))
    fig.subplots_adjust(left=.09, right=.97, bottom=.29, top=.76, wspace=.17)
    heading(fig, 'Transparency unlocks cooperative equilibria',
            'Behavioral signals  |  Eight-program library, floor case  |  Cooperation = Pr[(C, C)]')
    for panel, (ax, metric, title) in enumerate(zip(axes, ['nash_max', 'cooperative_basin'],
                ['A   Nash enumeration: cooperation attainable',
                 'B   Replicator dynamics: cooperation selected'])):
        for row, (a, group) in enumerate(points.groupby('alpha')):
            colors = [TEAL if v > .5 else GRAY for v in group[metric]]
            # One stroke per actual grid point; no interpolation along alpha.
            ax.vlines(group.t, row - .30, row + .30, colors=colors, linewidth=3.2)
            threshold = thresholds[thresholds.alpha == a].iloc[0]
            ax.scatter([threshold.first_cooperative_t], [row], s=45,
                       facecolor='white', edgecolor=INK, linewidth=1.15, zorder=5)
            if panel == 0:
                x = threshold.first_cooperative_t
                ax.annotate(f'{x:.2f}', (x, row), xytext=(7 if x < .85 else -8, -2),
                            textcoords='offset points', ha='left' if x < .85 else 'right',
                            va='center', fontsize=8, weight='bold', color=INK,
                            bbox=dict(facecolor='white', alpha=.95, edgecolor='none', pad=1.5))
        ax.set_xlim(-.025, 1.025)
        ax.set_ylim(6.55, -.55)
        ax.set_xticks([0, .2, .4, .6, .8, 1])
        ax.set_yticks(range(7), [f'{a:g}' for a in sorted(points.alpha.unique())])
        ax.set_xlabel(r'Transparency $t = I(B;S)/\log_2 8$', labelpad=9)
        ax.set_title(title, loc='left', fontsize=10.5, pad=15)
        ax.spines['left'].set_visible(False)
        ax.tick_params(axis='y', length=0)
        if panel == 0:
            ax.set_ylabel(r'Caution $\alpha$', labelpad=13)
        ax.grid(axis='x', color='#E9ECEE', linewidth=.6, zorder=0)
        ax.set_axisbelow(True)
    fig.legend(handles=[Patch(facecolor=TEAL, label='100%'), Patch(facecolor=GRAY, label='0%'),
                        Line2D([], [], marker='o', color='none', markeredgecolor=INK,
                               markerfacecolor='white', label='First cooperative grid point')],
               loc='lower center', bbox_to_anchor=(.5, .14), ncol=3, frameon=False, fontsize=9)
    footnote(fig, 'Exact Nash maxima and observed cooperative basins agree at all 707 grid points (transparency spacing 0.01).\n'
                  '1,000 shared initial populations per game; 62 distinct games. Rings locate the sampled onsets.\n'
                  'Pointwise 95% basin intervals: [99.62%, 100%] for 1,000/1,000 successes; [0%, 0.38%] for 0/1,000.')
    save(fig, '01_transparency_and_cooperation')


def figure_landscape(points, thresholds, components):
    fig, axes = plt.subplots(2, 3, figsize=(11.0, 6.5))
    fig.subplots_adjust(left=.085, right=.97, bottom=.20, top=.79, hspace=.40, wspace=.22)
    heading(fig, 'Cooperation is selected even while defection remains an equilibrium',
            'Every distinct Nash cooperation level is shown; the teal curve follows the observed evolutionary outcome.')
    for ax, a in zip(axes.flat, [0.2, 0.4, 0.5, 0.6, 0.8, 1.0]):
        d = points[points.alpha == a]
        for p in d.itertuples():
            values = components[components.game == p.game].cooperation.unique()
            values = values[~np.isclose(values, p.selected_cooperation, atol=1e-9, rtol=0)]
            ax.scatter(np.full(len(values), p.t), values, s=12, color=PURPLE, alpha=.6,
                       linewidths=0, zorder=3)
        q = thresholds[thresholds.alpha == a].iloc[0]
        ax.axvspan(q.last_defecting_t, q.first_cooperative_t, color=GOLD, alpha=.18, zorder=1)
        curve = d[d.t < 1] if a == 1 else d
        ax.step(curve.t, curve.selected_cooperation, where='post', color=TEAL, lw=2.5, zorder=4)
        # Sparse hollow circles let the full Nash level remain visible beneath the line.
        ax.scatter(d.t.iloc[::5], d.selected_cooperation.iloc[::5], s=15,
                   facecolors='white', edgecolors=TEAL, linewidths=.8, zorder=5)
        if a == 1:
            ax.scatter([1], [1], color=TEAL, s=26, zorder=6)
        base_axis(ax)
        ax.set_title(rf'$\alpha = {a:g}$', loc='left', pad=8)
        ax.text(.98, 1.09, rf'first C: $t={q.first_cooperative_t:.2f}$',
                transform=ax.transAxes, ha='right', fontsize=8, color=MUTED)
    for ax in axes[:, 0]:
        ax.set_ylabel('Mutual cooperation')
    for ax in axes[-1, :]:
        ax.set_xlabel('Transparency t')
    fig.legend(handles=[Line2D([], [], marker='o', ls='none', color=PURPLE, markersize=4,
                               label='Other Nash cooperation levels'),
                        Line2D([], [], color=TEAL, lw=2.5, label='Nash outcome selected by dynamics'),
                        Patch(facecolor=GOLD, alpha=.2, label='Last-D / first-C grid bracket')],
               loc='lower center', bbox_to_anchor=(.5, .095), ncol=3, frameon=False, fontsize=9)
    footnote(fig, 'All components have constant cooperation; the teal and purple levels cover the complete Nash outcome set.\n'
                  'Curves connect sampled values. At alpha = 0, every equilibrium and every trajectory is fully cooperative.')
    save(fig, '02_equilibrium_landscape')


def figure_thresholds(thresholds):
    fig, ax = plt.subplots(figsize=(8.8, 5.5))
    fig.subplots_adjust(left=.10, right=.88, bottom=.22, top=.78)
    heading(fig, 'Moderate caution permits cooperation at low transparency',
            'First cooperative grid point; exact Nash enumeration and 1,000/1,000 replicator runs give the same onset.')
    for row in thresholds.itertuples():
        x, y = row.alpha, row.first_cooperative_t
        if not math.isnan(row.last_defecting_t):
            ax.vlines(x, row.last_defecting_t, y, color=INK, lw=1.7, zorder=4)
            ax.hlines(row.last_defecting_t, x-.009, x+.009, color=INK, lw=1, zorder=4)
        ax.vlines(x, 0, y, color=GRAY, lw=1, zorder=1)
        ax.scatter([x], [y], s=80 if x not in (0, 1) else 52,
                   color=TEAL if x not in (0, 1) else INK,
                   edgecolor='white', linewidth=1, zorder=5)
        offset = (10, 2) if x == .4 else (0, 10 if x != 1 else -22)
        ax.annotate(f'{y:.2f}', (x, y), xytext=offset,
                    textcoords='offset points', ha='left' if x == .4 else 'center',
                    fontsize=10, weight='bold')
    ax.set_xlim(-.04, 1.04)
    ax.set_ylim(-.045, 1.07)
    ax.set_xticks([0, .2, .4, .5, .6, .8, 1])
    ax.set_xlabel(r'Caution $\alpha$', labelpad=10)
    ax.set_ylabel('Transparency at first cooperative grid point', labelpad=9)
    ax.set_yticks([0, .2, .4, .6, .8, 1])
    ax.grid(axis='y', color='#E9ECEE', linewidth=.8)
    ax.set_axisbelow(True)
    bits = ax.secondary_yaxis('right', functions=(lambda t: 3*t, lambda b: b/3))
    bits.set_ylabel('Information about opponent (bits)', labelpad=12, color=MUTED)
    bits.set_yticks([0, .6, 1.2, 1.8, 2.4, 3])
    bits.spines['right'].set_color(GRAY)
    ax.annotate('0.03 bits at the first\ncooperative grid point', xy=(.4, .01), xytext=(.31, .43),
                fontsize=10, color=TEAL, weight='bold', ha='left',
                arrowprops=dict(arrowstyle='-', color=TEAL, lw=1.1, connectionstyle='angle3,angleA=0,angleB=90'))
    ax.text(.02, .74, '$\\alpha = 0$\nCooperation is unconditional', fontsize=8.5, color=MUTED)
    ax.text(.99, .77, '$\\alpha = 1$\nFull transparency required', fontsize=8.5, color=MUTED, ha='right')
    footnote(fig, 'Markers show tested values, not exact continuous thresholds. Black ticks show the preceding defecting grid point.\n'
                  'No interpolation across caution levels. The alpha = 0 case is degenerate; alpha = 1 has an endpoint jump.')
    save(fig, '03_transparency_thresholds')


def figure_selection(points):
    fig, axes = plt.subplots(2, 3, figsize=(11.0, 6.5))
    fig.subplots_adjust(left=.085, right=.97, bottom=.20, top=.79, hspace=.40, wspace=.22)
    heading(fig, 'Evolution amplifies the cooperative possibilities of transparency',
            'The same 1,000 initial populations are evaluated before selection and at their converged endpoints.')
    for ax, a in zip(axes.flat, [.2, .4, .5, .6, .8, 1.]):
        d = points[points.alpha == a]
        ax.fill_between(d.t, d.initial_cooperation_q25, d.initial_cooperation_q75,
                        step='post', color=GRAY, alpha=.55, linewidth=0, zorder=1)
        curve = d[d.t < 1] if a == 1 else d
        ax.step(curve.t, curve.initial_cooperation_mean, where='post', color=MUTED, lw=1.4, zorder=2)
        ax.step(curve.t, curve.selected_cooperation, where='post', color=TEAL, lw=2.5, zorder=3)
        if a == 1:
            ax.scatter([1], [d.initial_cooperation_mean.iloc[-1]], color=MUTED, s=18, zorder=4)
            ax.vlines(1, d.initial_cooperation_q25.iloc[-1], d.initial_cooperation_q75.iloc[-1],
                      color=GRAY, lw=3, zorder=1)
        ax.scatter([0, 1], [d.selected_cooperation.iloc[0], d.selected_cooperation.iloc[-1]],
                   color=TEAL, s=18, zorder=4)
        base_axis(ax)
        ax.set_title(rf'$\alpha = {a:g}$', loc='left', pad=8)
    for ax in axes[:, 0]:
        ax.set_ylabel('Mutual cooperation')
    for ax in axes[-1, :]:
        ax.set_xlabel('Transparency t')
    fig.legend(handles=[Line2D([], [], color=TEAL, lw=2.5, label='After selection'),
                        Line2D([], [], color=MUTED, lw=1.4, label='Before selection: mean'),
                        Patch(facecolor=GRAY, alpha=.6, label='Before selection: middle 50% of starts')],
               loc='lower center', bbox_to_anchor=(.5, .095), ncol=3, frameon=False, fontsize=9)
    footnote(fig, 'Each value is $x^\\top C x$, where C marks mutual-cooperation cells. Initial populations are Dirichlet(1).\n'
                  'The gray band describes variation across initial populations, not confidence. Curves connect sampled values.')
    save(fig, '04_cooperation_before_and_after_selection')


def main():
    FIGURES.mkdir(exist_ok=True)
    TABLES.mkdir(exist_ok=True)
    points, thresholds, components, audit = read_and_audit()
    style()
    figure_phase(points, thresholds)
    figure_landscape(points, thresholds, components)
    figure_thresholds(thresholds)
    figure_selection(points)
    print(json.dumps(audit, indent=2))
    print(thresholds[['alpha', 'last_defecting_t', 'first_cooperative_t']].to_string(index=False))
    print(f'Wrote 4 figures in PDF/SVG/PNG and 6 audit tables to {HERE}')


if __name__ == '__main__':
    main()
