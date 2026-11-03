"""Nash equilibria of each zoo's full-transparency game, saved under results/full_transparency/.

At full transparency a bot of type i meeting type j plays the outcome table's cell
(`Zoo.cells`), so the game is the payoff matrix of those cells, with T, R, P, S = 3, 2, 0, -1
(`payoffs`). Its equilibria are computed by `equilibria`.

Each zoo and side writes to results/full_transparency/<zoo>/<side>/:
  equilibria.json     the game (bots, cells, A), every extreme equilibrium, every component.
                      Exact values are strings ("1/2"); a strategy lists the bots it plays
                      with positive probability; cells[i][j] is the row bot's action, then
                      the column bot's.
  lrsnash_input.txt   the game given to lrsnash (A shifted so that the smallest payoff is 1)
  lrsnash_output.txt  lrsnash's output, which the equilibria are read from
results/full_transparency/README.md describes every entry of these files.

Usage (from true/):
  python -m replication.full_transparency.nash                 body8, both sides
  python -m replication.full_transparency.nash <zoo>           another zoo, e.g. body8+trolls
  python -m replication.full_transparency.nash all             every zoo
Add --side floor or --side hinge for one side only.
"""

from __future__ import annotations

import argparse
import json
from fractions import Fraction
from pathlib import Path

from ..general.equilibria import (Equilibrium, Strategy, analyse, exact, lrsnash_input,
                                  parse_lrsnash, run_lrsnash)
from ..general.payoffs import payoff_matrix
from ..general.zoo import SIDES, ZOOS, Zoo, load_zoo

RESULTS = Path(__file__).resolve().parents[2] / "results" / "full_transparency"
PAYOFFS = {"T": 3, "R": 2, "P": 0, "S": -1}


def full_transparency_cells(zoo: Zoo) -> dict[tuple[str, str], tuple[str, str]]:
    """(row bot, column bot) -> (row bot's action, column bot's action)."""
    return {key: (cell.row, cell.col) for key, cell in zoo.cells.items()}


def _support(bots: tuple[str, ...], s: Strategy) -> dict[str, str]:
    return {b: str(p) for b, p in zip(bots, s) if p > 0}


def _range(values: list[Fraction]) -> dict[str, str]:
    return {"min": str(min(values)), "max": str(max(values))}


def _components(bots: tuple[str, ...], found: list[Equilibrium]) -> list[dict]:
    out = []
    for k in sorted({e.component for e in found}):
        members = [i for i, e in enumerate(found) if e.component == k]
        eqs = [found[i] for i in members]
        used = {b for e in eqs for b, p, q in zip(bots, e.row, e.col) if p > 0 or q > 0}
        out.append({
            "id": k,
            "equilibria": members,
            "bots": [b for b in bots if b in used],
            "n_symmetric": sum(e.symmetric for e in eqs),
            "row_payoff": _range([e.row_payoff for e in eqs]),
            "cooperation": _range([e.cooperation for e in eqs]),
        })
    return out


def _record(zoo: Zoo, cells: dict, A: list, found: list[Equilibrium]) -> dict:
    bots = zoo.bots
    return {
        "zoo": zoo.name,
        "side": zoo.side,
        "bots": list(bots),
        "payoffs": {k: str(v) for k, v in PAYOFFS.items()},
        "cells": [["".join(cells[(r, c)]) for c in bots] for r in bots],
        "A": [[str(a) for a in row] for row in A],
        "n_equilibria": len(found),
        "n_symmetric": sum(e.symmetric for e in found),
        "n_components": len({e.component for e in found}),
        "components": _components(bots, found),
        "equilibria": [{
            "index": i,
            "row": _support(bots, e.row),
            "col": _support(bots, e.col),
            "row_payoff": str(e.row_payoff),
            "col_payoff": str(e.col_payoff),
            "symmetric": e.symmetric,
            "mirror": e.mirror,
            "component": e.component,
            "cooperation": str(e.cooperation),
        } for i, e in enumerate(found)],
    }


def _shown(r: dict[str, str]) -> str:
    return r["min"] if r["min"] == r["max"] else f"{r['min']} to {r['max']}"


def _extreme(n: int) -> str:
    return f"{n} extreme {'equilibrium' if n == 1 else 'equilibria'}"


def run(name: str, side: str) -> dict:
    """Compute, save and print the equilibria of one zoo on one side."""
    zoo = load_zoo(name, side)
    cells = full_transparency_cells(zoo)
    A = exact(payoff_matrix(zoo.bots, cells, **PAYOFFS))
    game = lrsnash_input(A)
    output = run_lrsnash(game)
    record = _record(zoo, cells, A, analyse(zoo.bots, cells, A, parse_lrsnash(output, len(A))))

    out = RESULTS / name / side
    out.mkdir(parents=True, exist_ok=True)
    (out / "lrsnash_input.txt").write_text(game)
    (out / "lrsnash_output.txt").write_text(output)
    (out / "equilibria.json").write_text(json.dumps(record, indent=2) + "\n")

    print(f"{name}, {side} side: {_extreme(record['n_equilibria'])} "
          f"({record['n_symmetric']} symmetric) in {record['n_components']} components")
    for c in record["components"]:
        print(f"  component {c['id']}: {_extreme(len(c['equilibria']))}, "
              f"Pr[(C, C)] {_shown(c['cooperation'])}, row payoff {_shown(c['row_payoff'])}, "
              f"bots {', '.join(c['bots'])}")
    print(f"  saved to {out}\n")
    return record


def main() -> None:
    p = argparse.ArgumentParser(description="Nash equilibria of the full-transparency game.")
    p.add_argument("zoo", nargs="?", default="body8", choices=list(ZOOS) + ["all"])
    p.add_argument("--side", choices=SIDES, help="one side only (default: both)")
    args = p.parse_args()
    for name in ZOOS if args.zoo == "all" else [args.zoo]:
        for side in [args.side] if args.side else SIDES:
            run(name, side)


if __name__ == "__main__":
    main()
