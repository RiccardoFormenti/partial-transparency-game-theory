"""The ladder of nested zoos at full transparency (Table 8), saved under results/zoo_ladder/.

Each zoo of the ladder holds the one before (Figure 2): nonprovers+dupoc, body8,
body8+trolls, body8+trolls+provers. For each, `nash` and `replicator` solve its
full-transparency game, and the ladder keeps one row per zoo:
  Nash        the number of components and of extreme equilibria, and the bots of the
              fully cooperative component, the one in which Pr[(C, C)] reaches 1
  replicator  the share of starts that reach that component (its basin), and Pr[(C, C)]
              in the populations the starts end in, averaged over the starts
The paper's Table 8 has a Moran column in place of the replicator one.

The replicator dynamics run to the usual horizon 1e5, except for the zoos in HORIZONS. In
body8+trolls, DupocBot escapes full defection only slowly, so its basins keep changing long
after 1e5 (results/zoo_ladder/README.md).

Writes to results/zoo_ladder/<side>/:
  ladder.json  one entry per zoo: the table's row
  <zoo>/       the zoo's equilibria.json, lrsnash_input.txt, lrsnash_output.txt,
               replicator.json and replicator_runs.csv, the same files nash and replicator
               write to results/full_transparency/<zoo>/<side>/
results/zoo_ladder/README.md describes ladder.json.

Usage (from true/):
  python -m replication.full_transparency.zoo_ladder                floor side
  python -m replication.full_transparency.zoo_ladder --side hinge   hinge side
"""

from __future__ import annotations

import argparse
import csv
import json
from fractions import Fraction
from pathlib import Path

from ..general.replicator import HORIZON
from ..general.zoo import SIDES
from . import nash, replicator

RESULTS = Path(__file__).resolve().parents[2] / "results" / "zoo_ladder"
LADDER = ("nonprovers+dupoc", "body8", "body8+trolls", "body8+trolls+provers")
HORIZONS = {"body8+trolls": 1e9}  # zoos integrated longer than HORIZON
ABBREV = {"CooperateBot": "Coop", "DefectBot": "Def", "TitForTatBot": "TFT", "DupocBot": "Dup",
          "CupodBot": "Cup", "CupodTrollBot": "CupT", "DupocTrollBot": "DupT", "DBot": "DB",
          "EBot": "EB", "OBot": "OB", "CIMCIC": "CIM", "DIMDID": "DIMDID"}  # the paper's


def _round(v: float) -> float:
    return round(v, replicator.DIGITS) + 0.0  # + 0.0 turns -0.0 into 0.0


def _cooperative(equilibria: dict) -> dict:
    """The component holding a fully cooperative equilibrium; the ladder needs exactly one."""
    full = [c for c in equilibria["components"] if Fraction(c["cooperation"]["max"]) == 1]
    if len(full) != 1:
        raise ValueError(f"{equilibria['zoo']}: {len(full)} fully cooperative components")
    return full[0]


def ladder_row(folder: Path) -> dict:
    """The ladder's row for the zoo whose nash and replicator files are in `folder`."""
    eq = json.loads((folder / "equilibria.json").read_text())
    rep = json.loads((folder / "replicator.json").read_text())
    with (folder / "replicator_runs.csv").open() as f:
        cooperation = [float(r["cooperation"]) for r in csv.DictReader(f)]
    coop = _cooperative(eq)
    (basin,) = [c for c in rep["components"] if c["id"] == coop["id"]]
    return {
        "zoo": eq["zoo"],
        "bots": eq["bots"],
        "nash": {
            "n_components": eq["n_components"],
            "n_equilibria": eq["n_equilibria"],
            "cooperative_component": {"id": coop["id"], "bots": coop["bots"]},
        },
        "replicator": {
            "horizon": rep["settings"]["horizon"],
            "n_starts": rep["n_starts"],
            "n_converged": rep["n_converged"],
            "cooperative_basin": basin["basin"],
            "cooperative_basin_ci95": basin["basin_ci95"],
            "cooperation": {"mean": _round(sum(cooperation) / len(cooperation)),
                            "min": _round(min(cooperation)), "max": _round(max(cooperation))},
            "basins": [{"id": c["id"], "bots": c["bots"], "basin": c["basin"]}
                       for c in rep["components"] if c["n_starts"]],
        },
    }


def _set(bots: list[str]) -> str:
    return "{" + ", ".join(ABBREV.get(b, b) for b in bots) + "}"


def _print(side: str, rows: list[dict]) -> None:
    print(f"Zoo ladder, {side} side")
    print(f"  {'zoo':22s} {'Nash':8s} {'cooperative component':30s} "
          f"replicator: cooperative basin, mean Pr[(C, C)], horizon")
    for r in rows:
        n, rep = r["nash"], r["replicator"]
        counts = f"{n['n_components']} ({n['n_equilibria']})"
        print(f"  {r['zoo']:22s} {counts:8s} "
              f"{_set(n['cooperative_component']['bots']):30s} "
              f"{100 * rep['cooperative_basin']:.1f}%, {rep['cooperation']['mean']:.3f}, "
              f"{rep['horizon']:g}")


def run(side: str) -> list[dict]:
    """Solve every zoo of the ladder on one side; save, print and return the table's rows."""
    out = RESULTS / side
    for name in LADDER:
        nash.run(name, side, out / name)
        replicator.run(name, side, out / name, HORIZONS.get(name, HORIZON))
    rows = [ladder_row(out / name) for name in LADDER]
    (out / "ladder.json").write_text(json.dumps({"side": side, "zoos": rows}, indent=2) + "\n")
    _print(side, rows)
    print(f"  saved to {out}")
    return rows


def main() -> None:
    p = argparse.ArgumentParser(description="The ladder of nested zoos at full transparency.")
    p.add_argument("--side", choices=SIDES, default="floor", help="default: floor")
    run(p.parse_args().side)


if __name__ == "__main__":
    main()
