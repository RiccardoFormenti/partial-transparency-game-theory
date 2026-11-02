"""Check replication/partial_transparency/play.py and sweep.py, and replication/general/payoffs.py,
against copy's tau/play.py, tau/sweep.py,
tau/channels.py and egt/ingest.py, on every zoo, side, family and grid point.

Also reports what changes under the paper's definitions (uniform signal at t = 0, point
mass at t = 1 in both families), and decisions that sit within 1e-6 of α.

Usage (from the project root):  python true/checks/check_sweep.py
"""

import math
import sys
import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "true"), str(ROOT / "copy" / "app" / "src")]

from pd_runner.egt.ingest import payoff_matrix_from_tournament  # noqa: E402
from pd_runner.tau.channels import all_families  # noqa: E402
from pd_runner.tau.matrix import get_zoo  # noqa: E402
from pd_runner.tau.signal import behavioral_distance_matrix  # noqa: E402
from pd_runner.tau.sweep import run_tournament  # noqa: E402
from replication.general.payoffs import payoff_matrix  # noqa: E402
from replication.general.zoo import SIDES, ZOOS, load_zoo  # noqa: E402
from replication.partial_transparency.play import decision_mass  # noqa: E402
from replication.partial_transparency.signals import softmax_channel  # noqa: E402
from replication.partial_transparency.sweep import FAMILIES, distances, sweep  # noqa: E402

warnings.simplefilter("ignore")
POLICY = {"floor": "engine_side", "hinge": "hinge_side"}
failures = 0
changes = []

print("Per zoo, side and family, over the 6 x 7 grid:")
print("  cells / temperatures / payoffs: equal to the original at every point")
print("  t=1: does t = 1 reproduce the full-transparency table (as replicated | with point mass)")
print("  paper: grid points whose tournament changes under the paper's endpoints")
print("  near-ties: decisions with |mass - α| < 1e-6, for 0 < t < 1 and 0 < α < 1. (At α = 1 every")
print("    t < 1 is a tie in effect: a softmax gives every hypothesis positive weight, so a bot")
print("    cooperates only if it cooperates with every zoo member, whatever t is.)\n")
for name in ZOOS:
    for side in SIDES:
        zoo = load_zoo(name, side)
        ref = get_zoo(name).load(source="sprime", floor_policy=POLICY[side])
        full = {(r, c): (zoo.action(r, c), zoo.action(c, r)) for r in zoo.bots for c in zoo.bots}
        for family in FAMILIES:
            fam = all_families(ref)["syntactic"] if family == "syntactic" else None
            dist = behavioral_distance_matrix(ref)
            mine = sweep(zoo, family)
            cells_ok = temp_ok = pay_ok = True
            for r in mine:
                theirs = run_tournament(ref, r.t, r.alpha, dist, family=fam)
                cells_ok &= r.cells == theirs.cells
                temp_ok &= math.isclose(r.temperature, theirs.temperature, rel_tol=1e-9,
                                        abs_tol=1e-300)
                pay_ok &= np.array_equal(payoff_matrix(zoo.bots, r.cells),
                                         payoff_matrix_from_tournament(theirs, bots=ref.bots).A)
            ok = cells_ok and temp_ok and pay_ok
            failures += not ok

            anchor = all(r.cells == full for r in mine if r.t == 1 and r.alpha > 0)
            point = sweep(zoo, family, ts=(1.0,), top_temperature=0.0)
            anchor_point = all(r.cells == full for r in point if r.alpha > 0)

            paper = sweep(zoo, family, opaque_temperature=math.inf, top_temperature=0.0)
            changed = [(r.t, r.alpha, sum(r.cells[k] != q.cells[k] for k in r.cells))
                       for r, q in zip(mine, paper) if r.cells != q.cells]
            changes += [(name, side, family, *c) for c in changed]

            near = 0
            dist_mine = distances(zoo, family)
            for r in mine:
                if not (0 < r.t < 1 and 0 < r.alpha < 1):
                    continue
                channel = softmax_channel(zoo.bots, dist_mine, r.temperature)
                near += sum(abs(decision_mass(zoo, actor, channel[opp]) - r.alpha) < 1e-6
                            for actor in zoo.bots for opp in zoo.bots)
            print(f"{name:22s} {side:5s} {family:10s} {'OK' if ok else 'DIFFERS'} | "
                  f"t=1 {'yes' if anchor else 'NO '} | {'yes' if anchor_point else 'NO '} | "
                  f"paper: {len(changed):2d} points | near-ties {near}")

print("\nGrid points that change under the paper's endpoints (zoo, side, family, t, α, cells):")
for c in changes:
    print("  ", *c)
print("FAILED" if failures else "ALL OK")
sys.exit(1 if failures else 0)
