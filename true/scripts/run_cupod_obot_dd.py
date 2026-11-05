"""Rerun the experiments with CupodBot vs OBot set to (D, D) on the floor side.

That cell is a hinge cell, dich_CupodBot_vs_OBot: (C, D) on the floor side, (D, D) on the hinge
side. So the variant is the floor side with this one hinge search succeeding and the other 17
still failing. On the hinge side nothing changes.

The change is made in memory, as checks/check_zoo.py does: `data/` and the replication code stay
as they are. Three entries change, so that the loader's cross-checks still pass: the cell's
floor value in the outcome table, its copy in the hinge-side table, and CupodBot's test bit at
OBot. OBot's test bit at CupodBot is D already.

Writes to results/cupod_obot_dd/, in the layout of results/:
  full_transparency/body8/<side>/
  zoo_ladder/floor/
  partial_transparency/body8/floor/<family>/
  partial_transparency/alpha_0.5-1/body8/floor/<family>/

It is the cheap version of each run: --starts replicator starts per game (default 100), the
first ones of the same seeded draws as the original runs, so each pairs with an original start.
The t grid stays 0.01, since games are solved once each and t* is read off that grid.

Some grid games of this variant cycle forever: their orbits are closed, around a centre, so no
horizon converges and integrating costs time in proportion to the horizon. grid.py would raise
the horizon to 1e9, which would take months. So each game is first probed: if any start needs
more than CYCLE_RHS_CALLS right-hand-side calls to reach CYCLE_HORIZON, the whole game is
integrated to CYCLE_HORIZON only, and its starts count as unconverged. Over every game of the
original results and of this variant that had finished, the most any non-cycling game needs is
1600, the games that need horizons up to 1e8 included; a cycling game needs about 17000.

Usage (from true/):
  python scripts/run_cupod_obot_dd.py                         every stage, 100 starts
  python scripts/run_cupod_obot_dd.py --stages full ladder    some stages
  python scripts/run_cupod_obot_dd.py --stages ladder --starts 1000
"""

import argparse
import sys
from pathlib import Path

import numpy as np  # noqa: E402
from scipy.integrate import solve_ivp  # noqa: E402

TRUE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TRUE))

from replication.full_transparency import nash, replicator, zoo_ladder  # noqa: E402
from replication.general import zoo  # noqa: E402
from replication.general.payoffs import payoff_matrix  # noqa: E402
from replication.general.replicator import (ATOL, HORIZON, RTOL, growth_rates,  # noqa: E402
                                            sample_starts, softmax)
from replication.partial_transparency import grid  # noqa: E402
from replication.partial_transparency.sweep import FAMILIES  # noqa: E402

OUT = TRUE / "results" / "cupod_obot_dd"
DICHOTOMY = "dich_CupodBot_vs_OBot"
FINE_ALPHAS = (0.5, 0.6, 0.7, 0.8, 0.9, 1.0)  # the alpha_0.5-1 grid
STAGES = ("full", "ladder", "grid")
CYCLE_HORIZON = 1e3
CYCLE_RHS_CALLS = 5000

real_read, real_solve, real_replicator = zoo._read, replicator.solve, grid._replicator


def read_with_dd(name: str) -> dict:
    """`zoo._read`, with the cell at (D, D). Each entry must hold the value it is known to."""
    data = real_read(name)
    if name == "full_transparency_outcome_table.json":
        (entry,) = [e for e in data["floors"] if e["dichotomy"] == DICHOTOMY]
        assert (entry["left_bot"], entry["right_bot"], entry["pair"]) == (
            "CupodBot", "OBot", ["C", "D"]), entry
        entry["pair"] = ["D", "D"]
    elif name == "hinge_side_outcomes.json":
        (entry,) = [e for e in data["hinge_cells"] if e["dichotomy"] == DICHOTOMY]
        assert (entry["floor_side"], entry["hinge_side"]) == (["C", "D"], ["D", "D"]), entry
        entry["floor_side"] = ["D", "D"]
    elif name == "partial_transparency_bit_table.json":
        (row,) = [r for r in data["rows"] if r["bot"] == "CupodBot"]
        assert row["bits"]["obot"]["action"] == "C", row["bits"]["obot"]
        row["bits"]["obot"]["action"] = "D"
    return data


def cycles(z: zoo.Zoo, cells: dict, n_starts: int) -> bool:
    """Whether some start keeps the integrator as busy as a closed orbit does."""
    A = payoff_matrix(z.bots, cells, **nash.PAYOFFS)
    for start in sample_starts(len(A), n_starts, replicator.SEED):
        sol = solve_ivp(lambda _, y: growth_rates(A, softmax(y)), (0, CYCLE_HORIZON),
                        np.log(start), method="LSODA", rtol=RTOL, atol=ATOL)
        if sol.nfev > CYCLE_RHS_CALLS:
            return True
    return False


def bounded_replicator(z: zoo.Zoo, cells: dict, folder: Path, horizon: float, about: dict,
                       n_starts: int) -> dict:
    """`grid._replicator`, without raising the horizon of a game that cycles."""
    if cycles(z, cells, n_starts):
        print(f"  {about['game']} cycles: integrated to {CYCLE_HORIZON:g} only")
        return replicator.solve(z, cells, folder, CYCLE_HORIZON, about, n_starts)
    return real_replicator(z, cells, folder, horizon, about, n_starts)


def full(starts: int) -> None:
    """results/full_transparency/: Nash on both sides, replicator on the floor side, as saved."""
    for side in zoo.SIDES:
        nash.run("body8", side, OUT / "full_transparency" / "body8" / side)
    replicator.run("body8", "floor", OUT / "full_transparency" / "body8" / "floor")


def ladder(starts: int) -> None:
    zoo_ladder.RESULTS = OUT / "zoo_ladder"
    zoo_ladder.run("floor")


def sweeps(starts: int) -> None:
    grid.RESULTS = OUT / "partial_transparency"
    grid._replicator = bounded_replicator
    for family in FAMILIES:
        grid.run(family, n_starts=starts)
        grid.run(family, alphas=FINE_ALPHAS, subset="alpha_0.5-1", n_starts=starts)


def main() -> None:
    p = argparse.ArgumentParser(description="Rerun the experiments with Cupod vs OBot at (D, D).")
    p.add_argument("--stages", nargs="+", choices=STAGES, default=STAGES,
                   help="default: all of them")
    p.add_argument("--starts", type=int, default=100, help="replicator starts per game")
    args = p.parse_args()

    zoo._read = read_with_dd
    # replicator.run and zoo_ladder.run take no number of starts: set it where they call solve.
    replicator.solve = lambda z, cells, out, horizon=HORIZON, about=None, n_starts=args.starts: \
        real_solve(z, cells, out, horizon, about, n_starts)

    cell = zoo.load_zoo("body8", "floor").cells[("CupodBot", "OBot")]
    assert (cell.row, cell.col) == ("D", "D"), cell
    print(f"CupodBot vs OBot on the floor side: {cell.row}{cell.col}; {args.starts} starts\n")
    run = {"full": full, "ladder": ladder, "grid": sweeps}
    for stage in args.stages:
        run[stage](args.starts)


if __name__ == "__main__":
    main()
