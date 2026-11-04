"""Replicator dynamics of each zoo's full-transparency game, saved under results/full_transparency/.

The game is the one `nash` solves. Starts drawn uniformly on the simplex are integrated, and
their end states matched to the Nash components of equilibria.json (`replicator`), so `nash`
must have run first.

Each zoo and side writes to results/full_transparency/<zoo>/<side>/:
  replicator.json      the game, the settings, and for each Nash component how many starts
                       reach it and where in it they end
  replicator_runs.csv  one row per start: where it starts, where it ends, what it reaches
results/full_transparency/README.md describes every entry of these files.

Usage (from true/):
  python -m replication.full_transparency.replicator               body8, floor side
  python -m replication.full_transparency.replicator <zoo>         another zoo, e.g. body8+trolls
  python -m replication.full_transparency.replicator all           every zoo
Add --side hinge for the hinge side, and --horizon <time> to integrate longer than 1e5.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np

from ..general.equilibria import (Equilibrium, Matrix, analyse, cooperation_rate, exact,
                                  lrsnash_input, parse_lrsnash, run_lrsnash)
from ..general.payoffs import payoff_matrix
from ..general.replicator import (ATOL, HORIZON, MAX_DISTANCE, RTOL, TOL, Run, basins,
                                  sample_starts, wilson_interval)
from ..general.zoo import SIDES, ZOOS, Zoo, load_zoo
from .nash import PAYOFFS, RESULTS, full_transparency_cells

N_STARTS = 1000
SEED = 20260514  # the original's
DIGITS = 9  # decimals kept in replicator.json; replicator_runs.csv keeps every digit


def _round(v: float) -> float:
    return round(float(v), DIGITS) + 0.0  # + 0.0 turns -0.0 into 0.0


def _range(values: list[float]) -> dict[str, float]:
    return {"min": _round(min(values)), "max": _round(max(values))}


def _present(bots: tuple[str, ...], x: np.ndarray) -> tuple[str, ...]:
    return tuple(b for b, p in zip(bots, x) if p >= TOL)


def _interval(k: int, n: int) -> list[float]:
    return [_round(v) for v in wilson_interval(k, n)]


def _component(k: int, bots: tuple[str, ...], found: list[Equilibrium], runs: list[Run],
               payoff: list[float], cooperation: list[float]) -> dict:
    eqs = [e for e in found if e.component == k]
    used = {b for e in eqs for b, p, q in zip(bots, e.row, e.col) if p > 0 or q > 0}
    reached = [i for i, r in enumerate(runs) if r.component == k]
    entry = {
        "id": k,
        "bots": [b for b in bots if b in used],
        "n_starts": len(reached),
        "basin": len(reached) / len(runs),
        "basin_ci95": _interval(len(reached), len(runs)),
    }
    if reached:
        ends = np.array([runs[i].end for i in reached])
        supports = Counter(_present(bots, runs[i].end) for i in reached)
        entry |= {
            "shares": {b: _range(ends[:, j].tolist()) for j, b in enumerate(bots)
                       if ends[:, j].max() >= TOL},
            "supports": [{"bots": list(s), "n_starts": c} for s, c in supports.most_common()],
            "payoff": _range([payoff[i] for i in reached]),
            "cooperation": _range([cooperation[i] for i in reached]),
            "max_distance": _round(max(runs[i].distance for i in reached)),
        }
    return entry


def _record(zoo: Zoo, A: Matrix, found: list[Equilibrium], runs: list[Run],
            payoff: list[float], cooperation: list[float], horizon: float,
            about: dict | None = None) -> dict:
    bots, n = zoo.bots, len(runs)
    unconverged = [i for i, r in enumerate(runs) if not r.converged]
    return {
        "zoo": zoo.name,
        "side": zoo.side,
        **(about or {}),
        "bots": list(bots),
        "payoffs": {k: str(v) for k, v in PAYOFFS.items()},
        "A": [[str(a) for a in row] for row in A],
        "settings": {
            "n_starts": n,
            "seed": SEED,
            "horizon": horizon,
            "tolerance": TOL,
            "max_distance": MAX_DISTANCE,
            "integrator": "LSODA on log-shares",
            "rtol": RTOL,
            "atol": ATOL,
        },
        "n_starts": n,
        "n_converged": n - len(unconverged),
        "components": [_component(k, bots, found, runs, payoff, cooperation)
                       for k in sorted({e.component for e in found})],
        "unconverged": {
            "n_starts": len(unconverged),
            "share": len(unconverged) / n,
            "share_ci95": _interval(len(unconverged), n),
            "runs": unconverged,
        },
    }


def _write_runs(path: Path, bots: tuple[str, ...], runs: list[Run], payoff: list[float],
                cooperation: list[float]) -> None:
    with path.open("w", newline="") as f:
        out = csv.writer(f)
        out.writerow(["run", "converged", "component", "distance", "payoff", "cooperation"]
                     + [f"start:{b}" for b in bots] + [f"end:{b}" for b in bots])
        for i, r in enumerate(runs):
            out.writerow([i, r.converged, "" if r.component is None else r.component,
                          "" if r.distance is None else repr(r.distance),
                          repr(payoff[i]), repr(cooperation[i])]
                         + [repr(float(p)) for p in r.start] + [repr(float(p)) for p in r.end])


def _check_against_nash(out: Path, bots: tuple[str, ...], found: list[Equilibrium]) -> None:
    """Component ids refer to equilibria.json: it must hold the equilibria computed here."""
    path = out / "equilibria.json"
    if not path.exists():
        raise FileNotFoundError(f"{path} is missing: compute the Nash equilibria first")
    saved = json.loads(path.read_text())
    if saved["bots"] != list(bots) or [e["component"] for e in saved["equilibria"]] != [
            e.component for e in found]:
        raise ValueError(f"{path} is out of date: recompute the Nash equilibria")


def _shown(r: dict[str, float]) -> str:
    lo, hi = f"{r['min']:.6g}", f"{r['max']:.6g}"
    return lo if lo == hi else f"{lo} to {hi}"


def solve(zoo: Zoo, cells: dict[tuple[str, str], tuple[str, str]], out: Path,
          horizon: float = HORIZON, about: dict | None = None,
          n_starts: int = N_STARTS) -> dict:
    """Compute and save to `out` the basins of the game `cells` define over the zoo's bots,
    integrating each of `n_starts` starts up to `horizon`.

    `out` must hold that game's equilibria.json (`nash.solve`). `about` adds entries to
    replicator.json, after `zoo` and `side`.
    """
    A = exact(payoff_matrix(zoo.bots, cells, **PAYOFFS))
    found = analyse(zoo.bots, cells, A, parse_lrsnash(run_lrsnash(lrsnash_input(A)), len(A)))
    _check_against_nash(out, zoo.bots, found)

    runs = basins(A, found, sample_starts(len(A), n_starts, SEED), horizon)
    Af = np.array(A, dtype=float)
    payoff = [float(r.end @ Af @ r.end) for r in runs]
    cooperation = [float(cooperation_rate(zoo.bots, cells, r.end, r.end)) for r in runs]
    record = _record(zoo, A, found, runs, payoff, cooperation, horizon, about)

    out.mkdir(parents=True, exist_ok=True)
    (out / "replicator.json").write_text(json.dumps(record, indent=2) + "\n")
    _write_runs(out / "replicator_runs.csv", zoo.bots, runs, payoff, cooperation)
    return record


def run(name: str, side: str, out: Path | None = None, horizon: float = HORIZON) -> dict:
    """Compute, save and print the basins of one zoo on one side, integrating each start up
    to `horizon`.

    Reads equilibria.json from, and saves to, `out`, by default
    results/full_transparency/<zoo>/<side>/.
    """
    zoo = load_zoo(name, side)
    out = out or RESULTS / name / side
    record = solve(zoo, full_transparency_cells(zoo), out, horizon)

    print(f"{name}, {side} side: {record['n_starts']} starts to time {horizon:g}, "
          f"{record['n_converged']} converged")
    for c in record["components"]:
        lo, hi = c["basin_ci95"]
        line = (f"  component {c['id']} ({', '.join(c['bots'])}): {c['n_starts']} starts, "
                f"basin {c['basin']:.4g} (95% CI {lo:.4g} to {hi:.4g})")
        if c["n_starts"]:
            line += (f", Pr[(C, C)] {_shown(c['cooperation'])}, "
                     f"payoff {_shown(c['payoff'])}")
        print(line)
    print(f"  not converged: {record['unconverged']['n_starts']} starts")
    print(f"  saved to {out}\n")
    return record


def main() -> None:
    p = argparse.ArgumentParser(description="Replicator dynamics of the full-transparency game.")
    p.add_argument("zoo", nargs="?", default="body8", choices=list(ZOOS) + ["all"])
    p.add_argument("--side", choices=SIDES, default="floor", help="default: floor")
    p.add_argument("--horizon", type=float, default=HORIZON, help=f"default: {HORIZON:g}")
    args = p.parse_args()
    for name in ZOOS if args.zoo == "all" else [args.zoo]:
        run(name, args.side, horizon=args.horizon)


if __name__ == "__main__":
    main()
