"""Check replication/general/replicator.py against copy's egt/replicator/ and textbook games,
and the saved full-transparency results against equilibria.json.

Usage (from the project root):  python true/checks/check_replicator.py
"""

import json
import sys
import warnings
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "true"), str(ROOT / "copy" / "app" / "src")]

from pd_runner.egt.replicator.basins import estimate_basins  # noqa: E402
from pd_runner.egt.replicator.dynamics import integrate as copy_integrate  # noqa: E402
from pd_runner.egt.replicator.dynamics import replicator_field  # noqa: E402
from replication.full_transparency.nash import RESULTS, full_transparency_cells  # noqa: E402
from replication.general.equilibria import (analyse, exact, lrsnash_input,  # noqa: E402
                                            parse_lrsnash, run_lrsnash)
from replication.general.payoffs import payoff_matrix  # noqa: E402
from replication.general.replicator import (basins, growth_rates, integrate,  # noqa: E402
                                            sample_starts, wilson_interval)
from replication.general.zoo import load_zoo  # noqa: E402

warnings.simplefilter("ignore")
failures = 0


def check(ok: bool, text: str) -> None:
    global failures
    failures += not ok
    print(f"  {'OK  ' if ok else 'FAIL'} {text}")


def solve(A, bots=None, cells=None):
    """The exact matrix and extreme equilibria of (A, Aᵀ); cells only matter for Pr[(C, C)]."""
    bots = bots or tuple(f"type{i}" for i in range(len(A)))
    cells = cells or {(a, b): ("D", "D") for a in bots for b in bots}
    A = exact(A)
    return A, analyse(bots, cells, A, parse_lrsnash(run_lrsnash(lrsnash_input(A)), len(A)))


zoo = load_zoo("body8", "floor")
cells = full_transparency_cells(zoo)
A, found = solve(payoff_matrix(zoo.bots, cells), zoo.bots, cells)
Af = np.array(A, dtype=float)
starts = sample_starts(len(A), 50, seed=7)

print("1. body8 floor: the dynamics agree with copy's")
xs = sample_starts(len(A), 100, seed=8)
diff = max(np.abs(x * growth_rates(Af, x) - replicator_field(Af, x)).max() for x in xs)
check(diff < 1e-12, f"x_i g_i(x) = copy's replicator_field at 100 points (max diff {diff:.1e})")

diff = 0.0
for x0 in starts:  # x-space DOP853: integrates the same ODE in other coordinates
    ref = solve_ivp(lambda _, x: x * growth_rates(Af, x), (0, 1e3), x0, method="DOP853",
                    rtol=1e-12, atol=1e-14).y[:, -1]
    diff = max(diff, np.abs(integrate(Af, x0, (1e3,))[0] - ref).max())
check(diff < 1e-7, f"x(1000) = x-space DOP853's, from 50 starts (max diff {diff:.1e})")

diff, both = 0.0, 0
for x0, run in zip(starts, basins(A, found, starts)):
    theirs = copy_integrate(Af, x0)
    both += theirs.converged and run.converged
    diff = max(diff, np.abs(run.end - theirs.x).max())
check(both == len(starts) and diff < 1e-4,
      f"end states = copy's (RK4, stopped at speed 1e-7): {both} of {len(starts)} starts "
      f"converged in both, max diff {diff:.1e}")

print("\n2. Textbook games")
cases = [  # name, A, starts, expected {component: share}, None meaning not converged
    ("coordination", [[1, 0], [0, 1]], 1000, {0: 0.5, 2: 0.5}),
    ("hawk-dove, V = 2, C = 4", [[-1, 2], [0, 1]], 100, {1: 1.0}),
    ("rock-paper-scissors, win 2, loss 1", [[0, -1, 2], [2, 0, -1], [-1, 2, 0]], 50, {0: 1.0}),
    ("rock-paper-scissors, win 1, loss 2", [[0, -2, 1], [1, 0, -2], [-2, 1, 0]], 50, {None: 1.0}),
]
for name, M, n, expected in cases:
    M_exact, eqs = solve(M)
    runs = basins(M_exact, eqs, sample_starts(len(M), n, seed=1))
    counts = {k: sum(r.component == k for r in runs) for k in expected}
    ok = sum(counts.values()) == n and all(
        lo <= share <= hi for k, share in expected.items()
        for lo, hi in [wilson_interval(counts[k], n)])
    check(ok, f"{name}: {counts} of {n}, expected shares {expected}")

M = np.array(cases[3][1], dtype=float)
copy = estimate_basins(M, ["R", "P", "S"], n_samples=50, seed=1)
print(f"  (copy on the last: {copy.n_unconverged} unconverged, attractors "
      f"{[a.support(['R', 'P', 'S']) for a in copy.attractors]})")

print("\n3. body8 floor: what copy's grouping reports")
copy = estimate_basins(Af, list(zoo.bots), n_samples=200)
print(f"  copy: {len(copy.attractors)} attractors")
for a in copy.attractors:
    print(f"    {a.support(list(zoo.bots))}: basin {copy.basin_fraction(a):.3f}, "
          f"from single types {a.vertex_sources}")

print("\n4. Saved results agree with equilibria.json")
for path in sorted(RESULTS.glob("*/*/replicator.json")):
    rep = json.loads(path.read_text())
    eq = json.loads((path.parent / "equilibria.json").read_text())
    same = rep["bots"] == eq["bots"] and rep["A"] == eq["A"] and [
        (c["id"], c["bots"]) for c in rep["components"]] == [
        (c["id"], c["bots"]) for c in eq["components"]]
    total = sum(c["n_starts"] for c in rep["components"]) + rep["unconverged"]["n_starts"]
    check(same and total == rep["n_starts"],
          f"{path.parent.relative_to(RESULTS)}: same game and components; starts add up")

print("\nFAILED" if failures else "\nALL OK")
sys.exit(1 if failures else 0)
