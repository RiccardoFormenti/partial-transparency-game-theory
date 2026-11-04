"""Nash equilibria and replicator dynamics at each (t, α) of the grid, saved under
results/partial_transparency/.

At each grid point the lifted bots play a tournament (`sweep`), and its cells define a game
as the outcome table does at full transparency: A[i][j] is R, S, T or P as cell (i, j) is
(C, C), (C, D), (D, C) or (D, D). Each game is solved as at full transparency: its extreme
Nash equilibria and components (`full_transparency.nash`), and the component each of 1000
starts of the replicator dynamics reaches (`full_transparency.replicator`).

The grid runs t from 1 to 0 in steps of T_STEP (0.01, or --t-step), each value rounded to 10
decimals so that it is stored as 0.3, not 0.30000000000000004. α takes the original's values
(`sweep.ALPHAS`). With any step that divides 0.2, the grid holds the original's t values.

The dial's endpoints are Definition 32's, not the original's:
  t = 1      the point mass (T = 0). Each bot sees its opponent exactly, so the tournament is
             the full-transparency table and its game that of results/full_transparency/.
  t = 0      the uniform signal (T = ∞). Every opponent sends the same signal, so each bot plays
             one action against everyone: the opaque Prisoner's Dilemma.
  0 < t < 1  the softmax at the temperature whose channel has transparency t, found by bisection
             on log T (`signals.temperature_for`).
The original uses T = 1e4 at t = 0, a signal within 1e-4 of uniform, and in the syntactic family
T = 1e-6 at t = 1, which blurs syntactic twins. On body8's floor side neither changes any
tournament of the grid (checks/check_partial_transparency.py).

Twins, bots at distance 0, receive the same signal at every T > 0, so no T > 0 reaches
transparency 1: the most any reaches is the ceiling. A t above the ceiling has no temperature and
gets the point mass, whose transparency is 1, not t. The run flags both, in grid.json and on
screen. body8 has no twins in either family.

Grid points whose tournaments have the same cells play the same game, which is solved once.

The replicator dynamics run to time 1e5. A game in which some start has not converged by then
is integrated again, 10 times longer, until every start converges or the time reaches
MAX_HORIZON. Near a monoculture that a neutral type ties with, a type that loses only to
itself dies out like 1/t, not exponentially. On the fine grid a few games need 1e7 or 1e8.

Writes to results/partial_transparency/body8/floor/<family>/:
  grid.json    the channel at each t, the tournament at each (t, α), and the game it plays
  games/<id>/  the game's equilibria.json, lrsnash_input.txt, lrsnash_output.txt,
               replicator.json and replicator_runs.csv, as nash and replicator write them at
               full transparency, with the family and the grid points added
results/partial_transparency/README.md describes every entry.

Usage (from true/):
  python -m replication.partial_transparency.grid                       both families
  python -m replication.partial_transparency.grid --family behavioral   one family
Add --t-step <step> for another t step (it must divide 1), and --horizon <time> for another
first horizon than 1e5.
"""

from __future__ import annotations

import argparse
import json
import math
from fractions import Fraction
from pathlib import Path

from ..full_transparency import nash, replicator
from ..general.replicator import HORIZON
from ..general.zoo import Zoo, load_zoo
from . import signals
from .play import TIE_TOLERANCE, decision_mass, shortfall
from .signals import ceiling, softmax_channel, twin_classes
from .sweep import ALPHAS, FAMILIES, Tournament, distances, sweep

ZOO, SIDE = "body8", "floor"
RESULTS = Path(__file__).resolve().parents[2] / "results" / "partial_transparency"
T_STEP = 0.01
OPAQUE_TEMPERATURE = math.inf  # t = 0: the uniform signal
TOP_TEMPERATURE = 0.0  # t = 1, and any t above the ceiling: the point mass
CALIBRATION = 1e-3  # how far a channel's transparency may lie from its t
MAX_HORIZON = 1e9  # the longest the replicator dynamics are integrated


def t_values(step: float = T_STEP) -> tuple[float, ...]:
    """1, 1 - step, ..., 0, each rounded to 10 decimals. `step` must divide 1."""
    n = round(1 / step)
    if n < 1 or abs(n * step - 1) > 1e-9:
        raise ValueError(f"the t step must divide 1, got {step}")
    return tuple(round(1 - i / n, 10) for i in range(n + 1))


def _signal(temperature: float) -> str:
    if temperature == 0:
        return "point mass"
    return "uniform" if math.isinf(temperature) else "softmax"


def _channels(zoo: Zoo, dist: dict[tuple[str, str], float],
              tournaments: list[Tournament]) -> list[dict]:
    """One entry per t: the channel its tournaments use, the mass each bot compares with α,
    and its shortfall 1 - mass, which `play.action` decides on."""
    bots, out = zoo.bots, {}
    for r in tournaments:
        if r.t in out:
            continue
        channel = softmax_channel(bots, dist, r.temperature)
        out[r.t] = {
            "t": r.t,
            "signal": _signal(r.temperature),
            "temperature": None if math.isinf(r.temperature) else r.temperature,
            "transparency": r.transparency,
            "reached": abs(r.transparency - r.t) <= CALIBRATION,
            "channel": [[channel[b][h] for h in bots] for b in bots],
            "mass": [[decision_mass(zoo, a, channel[b]) for b in bots] for a in bots],
            "shortfall": [[shortfall(zoo, a, channel[b]) for b in bots] for a in bots],
        }
    return list(out.values())


def _games(bots: tuple[str, ...], tournaments: list[Tournament]) -> dict[str, list[Tournament]]:
    """game id -> the tournaments that play it. Ids g00, g01, ... follow the grid's order."""
    ids: dict[tuple, str] = {}
    games: dict[str, list[Tournament]] = {}
    for r in tournaments:
        game = ids.setdefault(tuple(r.cells[(a, b)] for a in bots for b in bots), f"g{len(ids):02d}")
        games.setdefault(game, []).append(r)
    return games


def _replicator(zoo: Zoo, cells: dict[tuple[str, str], tuple[str, str]], folder: Path,
                horizon: float, about: dict) -> dict:
    """The game's basins, integrated 10 times longer while some start has not converged, up
    to MAX_HORIZON."""
    while True:
        rep = replicator.solve(zoo, cells, folder, horizon, about)
        if rep["n_converged"] == rep["n_starts"] or horizon >= MAX_HORIZON:
            return rep
        horizon *= 10


def _cells(bots: tuple[str, ...], cells: dict[tuple[str, str], tuple[str, str]]) -> list[list[str]]:
    return [["".join(cells[(r, c)]) for c in bots] for r in bots]


def _dumps(v, indent: int = 0) -> str:
    """JSON indented by 2, with each list of numbers or strings on one line."""
    pad = "  " * (indent + 1)
    if isinstance(v, dict) and v:
        items = [f"{pad}{json.dumps(k)}: {_dumps(x, indent + 1)}" for k, x in v.items()]
    elif isinstance(v, list) and any(isinstance(x, (dict, list)) for x in v):
        items = [pad + _dumps(x, indent + 1) for x in v]
    else:
        return json.dumps(v)
    brackets = "{}" if isinstance(v, dict) else "[]"
    return brackets[0] + "\n" + ",\n".join(items) + "\n" + "  " * indent + brackets[1]


def _game_line(game: str, rs: list[Tournament], eq: dict, rep: dict) -> str:
    where = ", ".join(f"({r.t:g}, {r.alpha:g})" for r in rs[:4])
    if len(rs) > 4:
        where += f", … ({len(rs)} points)"
    coop = [Fraction(c["cooperation"]["max"]) for c in eq["components"]]
    basins = ", ".join(f"{c['id']}: {100 * c['basin']:.1f}%" for c in rep["components"]
                       if c["n_starts"])
    n = eq["n_components"]
    return (f"  {game}  (t, α) = {where}\n"
            f"       Nash: {n} component{'s' * (n != 1)} ({eq['n_equilibria']} extreme), "
            f"best Pr[(C, C)] per component {', '.join(str(c) for c in coop)}\n"
            f"       replicator to time {rep['settings']['horizon']:g}: "
            f"{rep['n_converged']} of {rep['n_starts']} converged; "
            f"basins {basins or 'none'}")


def run(family: str, ts: tuple[float, ...] = t_values(), horizon: float = HORIZON) -> dict:
    """Solve, save and print the game of every grid point of one family."""
    zoo = load_zoo(ZOO, SIDE)
    bots = zoo.bots
    dist = distances(zoo, family)
    twins, top = twin_classes(bots, dist), ceiling(bots, dist)
    tournaments = sweep(zoo, family, ts, ALPHAS, OPAQUE_TEMPERATURE, TOP_TEMPERATURE)
    channels = _channels(zoo, dist, tournaments)
    unreached = [c["t"] for c in channels if not c["reached"]]
    games = _games(bots, tournaments)
    game_of = {(r.t, r.alpha): game for game, rs in games.items() for r in rs}

    out = RESULTS / ZOO / SIDE / family
    print(f"{ZOO}, {SIDE} side, {family} family: {len(tournaments)} grid points, "
          f"{len(games)} distinct games")
    for c in twins:
        print(f"  WARNING: twins {', '.join(c)}: no T > 0 reaches transparency 1, only the "
              f"ceiling {top:.6g}; the point mass at t = 1 separates them")
    for t in unreached:
        (c,) = [c for c in channels if c["t"] == t]
        print(f"  WARNING: no channel has transparency t = {t:g}; it gets the {c['signal']}, "
              f"of transparency {c['transparency']:.6g}")
    if not twins and not unreached:
        print(f"  no twins: every t of the grid is reached (ceiling {top:.6g})")

    results = {}
    for game, rs in games.items():
        about = {"family": family, "game": game,
                 "points": [{"t": r.t, "alpha": r.alpha} for r in rs]}
        folder = out / "games" / game
        eq = nash.solve(zoo, rs[0].cells, folder, about)
        rep = _replicator(zoo, rs[0].cells, folder, horizon, about)
        results[game] = (eq, rep)
        print(_game_line(game, rs, eq, rep))
        if rep["n_converged"] < rep["n_starts"]:
            print(f"  WARNING: {game}: {rep['n_starts'] - rep['n_converged']} starts have not "
                  f"converged by time {MAX_HORIZON:g}")

    record = {
        "zoo": ZOO,
        "side": SIDE,
        "family": family,
        "bots": list(bots),
        "ts": list(ts),
        "alphas": list(ALPHAS),
        "settings": {
            # the bisection's bracket and stopping width, on T (signals.temperature_for)
            "min_temperature": signals.MIN_TEMPERATURE,
            "max_temperature": signals.OPAQUE_TEMPERATURE,
            "bisection_tolerance": signals.BISECTION_TOLERANCE,
            "calibration": CALIBRATION,
            "tie_tolerance": TIE_TOLERANCE,
            "horizon": horizon,
            "max_horizon": MAX_HORIZON,
        },
        "distances": [[dist[(a, b)] for b in bots] for a in bots],
        "twins": [list(c) for c in twins],
        "ceiling": top,
        "unreached": unreached,
        "n_games": len(games),
        "channels": channels,
        "points": [{
            "t": r.t,
            "alpha": r.alpha,
            "game": game_of[(r.t, r.alpha)],
            "mutual_cooperation": r.mutual_cooperation,
            "cells": _cells(bots, r.cells),
        } for r in tournaments],
        "games": [{"id": game, "horizon": results[game][1]["settings"]["horizon"],
                   "points": [{"t": r.t, "alpha": r.alpha} for r in rs]}
                  for game, rs in games.items()],
    }
    (out / "grid.json").write_text(_dumps(record) + "\n")

    print("  game at each grid point (rows t, columns α). A row is shown where it changes, and")
    print("  holds down to the next row shown:")
    print("      t  " + " ".join(f"{a:>4g}" for a in ALPHAS))
    previous = None
    for t in ts:
        row = [game_of[(t, a)] for a in ALPHAS]
        if row != previous or t == ts[-1]:
            print(f"  {t:5g}  " + " ".join(f"{g:>4s}" for g in row))
        previous = row
    stale = sorted(p.name for p in (out / "games").iterdir() if p.name not in games)
    if stale:
        print(f"  WARNING: games/ holds folders from an earlier run, not part of this grid: "
              f"{', '.join(stale)}")
    print(f"  saved to {out}\n")
    return record


def main() -> None:
    p = argparse.ArgumentParser(description="Nash equilibria and replicator dynamics on the "
                                            "(t, α) grid, body8, floor side.")
    p.add_argument("--family", choices=FAMILIES, help="one family only (default: both)")
    p.add_argument("--t-step", type=float, default=T_STEP, help=f"default: {T_STEP:g}")
    p.add_argument("--horizon", type=float, default=HORIZON,
                   help=f"the first horizon (default: {HORIZON:g})")
    args = p.parse_args()
    ts = t_values(args.t_step)
    for family in [args.family] if args.family else FAMILIES:
        run(family, ts, args.horizon)


if __name__ == "__main__":
    main()
