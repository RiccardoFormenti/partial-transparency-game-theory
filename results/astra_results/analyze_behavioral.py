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


def summarize_transparency(points):
    """Average conditions with explicit weights; check effects within each condition."""
    positive = points[points.alpha > 0]
    alphas = sorted(positive.alpha.unique())
    means = positive.groupby('t')[['nash_max', 'selected_cooperation', 'nash_min']].mean().reset_index()
    means['n_conditions'] = len(alphas)
    all_conditions = points.groupby('t')[['nash_max', 'selected_cooperation']].mean()
    means['nash_max_including_alpha0'] = means.t.map(all_conditions.nash_max)
    means['selected_including_alpha0'] = means.t.map(all_conditions.selected_cooperation)
    rows = []
    for alpha, group in positive.groupby('alpha'):
        group = group.sort_values('t')
        for metric in ('nash_max', 'selected_cooperation'):
            values = group[metric].to_numpy()
            adjacent = np.diff(values)
            i, j = np.triu_indices(len(values), 1)
            pairwise = values[j] - values[i]
            rows.append(dict(alpha=alpha, metric=metric, opaque=values[0], transparent=values[-1],
                             endpoint_gain=values[-1] - values[0],
                             adjacent_increase=int((adjacent > 1e-9).sum()),
                             adjacent_unchanged=int((abs(adjacent) <= 1e-9).sum()),
                             adjacent_decrease=int((adjacent < -1e-9).sum()),
                             pairwise_increase=int((pairwise > 1e-9).sum()),
                             pairwise_unchanged=int((abs(pairwise) <= 1e-9).sum()),
                             pairwise_decrease=int((pairwise < -1e-9).sum())))
    effects = pd.DataFrame(rows)
    summary = dict(conditions=[float(a) for a in alphas], weight_per_condition=1/len(alphas),
                   alpha0_exclusion='All lifted programs cooperate unconditionally at every transparency.',
                   averaging='Equal weights over six fixed tested settings, not over Nash equilibria.',
                   mean_agreement=bool(np.allclose(means.nash_max, means.selected_cooperation, atol=1e-9, rtol=0)))
    for metric, group in effects.groupby('metric'):
        summary[metric] = {c: int(group[c].sum()) for c in effects.columns
                           if c.startswith(('adjacent_', 'pairwise_'))}
        summary[metric]['conditions_with_positive_endpoint_gain'] = int((group.endpoint_gain > 1e-9).sum())
    means.to_csv(TABLES / 'cooperation_by_transparency.csv', index=False, float_format='%.12g')
    effects.to_csv(TABLES / 'within_condition_transparency_effects.csv', index=False, float_format='%.12g')
    (HERE / 'transparency_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return means, summary


def figure_relationship(means):
    fig, ax = plt.subplots(figsize=(9.2, 5.9))
    fig.subplots_adjust(left=.11, right=.96, bottom=.25, top=.75)
    heading(fig, 'More transparency, more cooperation at equilibrium',
            'Behavioral family  |  Mean across six fixed nonzero-caution settings  |  Exact Nash + replicator analysis')
    ax.fill_between(means.t, 0, means.nash_max, step='post', color=TEAL_LIGHT, alpha=.8, zorder=1)
    ax.step(means.t, means.nash_max, where='post', color=INK, lw=2.3, zorder=3)
    indices = np.unique(np.r_[np.arange(0, len(means), 5),
                              np.flatnonzero(np.abs(np.diff(means.nash_max)) > 1e-9) + 1])
    ax.scatter(means.t.iloc[indices], means.selected_cooperation.iloc[indices],
               s=40, facecolor='white', edgecolor=TEAL, linewidth=1.7, zorder=5)
    ax.hlines(0, 0, 1, color=MUTED, ls=(0, (2, 3)), lw=1, zorder=2)
    ax.text(.43, .48, '0% to 100%', fontsize=24, color=TEAL, weight='bold')
    ax.text(.43, .37, 'from opacity to full transparency', fontsize=10, color=MUTED)
    ax.text(.43, .28, 'Both methods agree at every\ntested transparency level.',
            fontsize=10, color=INK, linespacing=1.5, va='top')
    ax.text(.38, .055, 'Minimum Nash cooperation remains at 0%', fontsize=8, color=MUTED)
    base_axis(ax)
    ax.set_ylim(-.03, 1.07)
    ax.set_yticks([0, .25, .5, .75, 1])
    ax.set_xlabel(r'Transparency $t$', fontsize=10, labelpad=9)
    ax.set_ylabel('Mean mutual cooperation at equilibrium', fontsize=10, labelpad=11)
    ax.legend(handles=[Line2D([], [], color=INK, lw=2.3, label='Maximum Nash cooperation'),
                       Line2D([], [], marker='o', ls='none', markeredgecolor=TEAL,
                              markerfacecolor='white', markeredgewidth=1.6, markersize=6,
                              label='Replicator-selected cooperation')],
              loc='lower left', bbox_to_anchor=(0, 1.025), ncol=2, frameon=False,
              fontsize=9, borderaxespad=0)
    footnote(fig, 'Equal weights over the six tested settings with alpha > 0; no averaging over Nash equilibria.\n'
                  'Steps guide the eye between 0.01-spaced samples. Replicator means use 1,000 shared starts per game.\n'
                  'The excluded alpha = 0 setting cooperates unconditionally at every transparency level.')
    save(fig, '01_transparency_and_cooperation')


def figure_landscape(points, components):
    fig, axes = plt.subplots(2, 3, figsize=(11.0, 6.5))
    fig.subplots_adjust(left=.085, right=.97, bottom=.20, top=.79, hspace=.40, wspace=.22)
    heading(fig, 'The positive effect holds within every fixed condition',
            'Caution is held fixed within each panel. Transparency alone varies; maximum and selected cooperation never decrease.')
    for ax, a in zip(axes.flat, [0.2, 0.4, 0.5, 0.6, 0.8, 1.0]):
        d = points[points.alpha == a]
        for p in d.itertuples():
            values = components[components.game == p.game].cooperation.unique()
            values = values[~np.isclose(values, p.selected_cooperation, atol=1e-9, rtol=0)]
            ax.scatter(np.full(len(values), p.t), values, s=10, color=PURPLE, alpha=.5,
                       linewidths=0, zorder=2)
        curve = d[d.t < 1] if a == 1 else d
        ax.step(curve.t, curve.nash_max, where='post', color=INK, lw=2.1, zorder=3)
        if a == 1:
            ax.scatter([1], [1], color=INK, s=36, zorder=3)
        indices = np.unique(np.r_[np.arange(0, len(d), 5),
                                  np.flatnonzero(np.abs(np.diff(d.nash_max)) > 1e-9) + 1])
        ax.scatter(d.t.iloc[indices], d.selected_cooperation.iloc[indices], s=21,
                   facecolors='white', edgecolors=TEAL, linewidths=1.2, zorder=4)
        base_axis(ax)
        ax.set_title(rf'Fixed $\alpha = {a:g}$', loc='left', pad=8, fontsize=10)
    for ax in axes[:, 0]:
        ax.set_ylabel('Mutual cooperation at equilibrium')
    for ax in axes[-1, :]:
        ax.set_xlabel('Transparency t')
    fig.legend(handles=[Line2D([], [], color=INK, lw=2.1, label='Maximum Nash cooperation'),
                        Line2D([], [], marker='o', ls='none', markeredgecolor=TEAL,
                               markerfacecolor='white', markersize=5, markeredgewidth=1.2,
                               label='Replicator-selected cooperation'),
                        Line2D([], [], marker='o', ls='none', color=PURPLE, markersize=4,
                               label='Other Nash cooperation levels')],
               loc='lower center', bbox_to_anchor=(.5, .095), ncol=3, frameon=False, fontsize=9)
    footnote(fig, 'Zero decreases across all 600 adjacent comparisons at fixed alpha > 0; all six settings rise from 0% to 100%.\n'
                  'Lines connect sampled values. All Nash cooperation levels are shown; defecting equilibria persist.')
    save(fig, '02_equilibrium_landscape')


def main():
    FIGURES.mkdir(exist_ok=True)
    TABLES.mkdir(exist_ok=True)
    points, thresholds, components, audit = read_and_audit()
    means, summary = summarize_transparency(points)
    style()
    figure_relationship(means)
    figure_landscape(points, components)
    print(json.dumps(audit, indent=2))
    print(json.dumps(summary, indent=2))
    print(f'Wrote 2 figures in PDF/SVG/PNG and 8 audit tables to {HERE}')


if __name__ == '__main__':
    main()
