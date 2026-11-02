"""Check replication/partial_transparency/signals.py against copy's tau/signal.py, and the assumptions both rely on.

Usage (from the project root):  python true/checks/check_signals.py
"""

import math
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "true"), str(ROOT / "copy" / "app" / "src")]

from pd_runner.tau import signal as original  # noqa: E402
from pd_runner.tau.matrix import get_zoo  # noqa: E402
from replication.general.zoo import SIDES, ZOOS, load_zoo  # noqa: E402
from replication.partial_transparency import signals  # noqa: E402

warnings.simplefilter("ignore")
POLICY = {"floor": "engine_side", "hinge": "hinge_side"}
T_GRID = (1.0, 0.8, 0.6, 0.4, 0.2, 0.0)  # the sweep's transparency grid (linear_ts(6))
failures = 0


def check(ok: bool) -> str:
    global failures
    failures += not ok
    return "OK" if ok else "FAIL"


print("Per zoo and side, against the original:")
print("  distances | twins and ceiling | temperature, channel and measured t on the t grid")
print("Assumption of the bisection: transparency decreases in T (largest increase found).")
print("t = 0 endpoint: largest |weight - 1/n|, i.e. how far the opaque channel is from uniform.\n")
for name in ZOOS:
    for side in SIDES:
        zoo = load_zoo(name, side)
        ref = get_zoo(name).load(source="sprime", floor_policy=POLICY[side])
        bots = zoo.bots
        dist = signals.behavioral_distances(zoo)
        same_dist = dist == original.behavioral_distance_matrix(ref)

        ceil = signals.ceiling(bots, dist)
        same_ceiling = (abs(ceil - original.transparency(ref, 1e-8)) < 1e-12
                        and signals.twin_classes(bots, dist) == sorted(original.behavioral_twins(ref)))

        temp_diff = weight_diff = calib_err = 0.0
        for t in T_GRID:
            temp, ref_temp = signals.temperature_for(bots, dist, t), \
                original.temperature_for_transparency(ref, t)
            temp_diff = max(temp_diff, abs(temp - ref_temp) / max(ref_temp, 1e-300))
            mine = signals.softmax_channel(bots, dist, temp)
            theirs = original.signal_family_at_temperature(ref, ref_temp)
            weight_diff = max(weight_diff, max(abs(mine[b][h] - theirs[b].weights.get(h, 0.0))
                                               for b in bots for h in bots))
            if 0 < t < ceil:
                calib_err = max(calib_err, abs(signals.transparency(mine) - t))

        grid = [signals.MIN_TEMPERATURE * (signals.OPAQUE_TEMPERATURE / signals.MIN_TEMPERATURE)
                ** (i / 400) for i in range(401)]
        values = [signals.transparency(signals.softmax_channel(bots, dist, T)) for T in grid]
        rise = max(0.0, max(b - a for a, b in zip(values, values[1:])))

        opaque = signals.channel_at(bots, dist, 0.0)
        off_uniform = max(abs(p - 1 / len(bots)) for s in opaque.values() for p in s.values())

        print(f"{name:22s} {side:5s} distances {check(same_dist)} | "
              f"ceiling {ceil:.4f} {check(same_ceiling)} | "
              f"T rel.diff {temp_diff:.0e}, weights diff {weight_diff:.0e}, "
              f"|t - measured| ≤ {calib_err:.0e} {check(temp_diff < 1e-9 and weight_diff < 1e-12 and calib_err < 1e-3)} | "
              f"monotone {check(rise < 1e-12)} | t=0 off-uniform {off_uniform:.1e}")

print("\nEndpoints follow Definition 32:", end=" ")
zoo = load_zoo("body8", "floor")
dist = signals.behavioral_distances(zoo)
point = signals.softmax_channel(zoo.bots, dist, 0.0)
uniform = signals.softmax_channel(zoo.bots, dist, math.inf)
print(check(signals.transparency(point) == 1.0 and abs(signals.transparency(uniform)) < 1e-15
            and signals.channel_at(zoo.bots, dist, 1.0) == point
            and signals.channel_at(zoo.bots, dist, 0.0, opaque_temperature=math.inf) == uniform))

print("FAILED" if failures else "ALL OK")
sys.exit(1 if failures else 0)
