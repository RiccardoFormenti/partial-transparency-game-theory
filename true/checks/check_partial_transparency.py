"""Check the saved (t, α) grid (results/partial_transparency/body8/floor/): its t values are evenly
spaced decimals holding the original's, its endpoints are the point mass and the uniform
signal, its t = 1 game is the full-transparency one, every cell
follows from the saved channel, every game folder holds its points' game, the original's
endpoints would not change it, and the twin flag fires on a zoo with twins.

Usage (from the project root):  python true/checks/check_partial_transparency.py
"""

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "true")]

from replication.full_transparency.nash import RESULTS as FULL  # noqa: E402
from replication.general.zoo import load_zoo  # noqa: E402
from replication.partial_transparency import grid  # noqa: E402
from replication.partial_transparency.play import TIE_TOLERANCE, decision_mass, shortfall  # noqa: E402
from replication.partial_transparency.signals import ceiling, transparency, twin_classes  # noqa: E402
from replication.partial_transparency.sweep import ALPHAS, FAMILIES, TS, distances, sweep  # noqa: E402

ADDED = ("family", "game", "points")  # the keys grid adds to the full-transparency files
failures = 0


def check(ok: bool, text: str) -> None:
    global failures
    failures += not ok
    print(f"  {'OK  ' if ok else 'FAIL'} {text}")


def without_added(path: Path) -> dict:
    return {k: v for k, v in json.loads(path.read_text()).items() if k not in ADDED}


zoo = load_zoo(grid.ZOO, grid.SIDE)
bots, n = zoo.bots, len(zoo.bots)
full = [["".join((zoo.action(r, c), zoo.action(c, r))) for c in bots] for r in bots]
for family in FAMILIES:
    out = grid.RESULTS / grid.ZOO / grid.SIDE / family
    saved = json.loads((out / "grid.json").read_text())
    channels = {c["t"]: c for c in saved["channels"]}
    points = {(p["t"], p["alpha"]): p for p in saved["points"]}
    print(f"{family} family")

    print(" 0. Grid")
    ts = saved["ts"]
    check(ts == list(grid.t_values(ts[0] - ts[1])) and set(TS) <= set(ts),
          f"{len(ts)} t values from 1 to 0 in steps of {ts[0] - ts[1]:.4g}, rounded to 10 "
          f"decimals, holding the original's {TS}")
    check(saved["alphas"] == list(ALPHAS) and len(points) == len(ts) * len(ALPHAS),
          f"α the original's {ALPHAS}; {len(points)} points")

    print(" 1. Endpoints")
    one, zero = channels[1.0], channels[0.0]
    check(one["signal"] == "point mass" and one["channel"] == [[float(i == j) for j in range(n)]
                                                              for i in range(n)]
          and one["transparency"] == 1.0, "t = 1 is the point mass, of transparency 1")
    check(all(p["cells"] == full for (t, a), p in points.items() if t == 1 and a > 0),
          "t = 1, α > 0: the tournament is the full-transparency table")
    (g,) = {p["game"] for (t, a), p in points.items() if t == 1 and a > 0}
    for name in ("equilibria.json", "replicator.json"):
        check(without_added(out / "games" / g / name) == without_added(FULL / grid.ZOO / grid.SIDE / name),
              f"t = 1: games/{g}/{name} = results/full_transparency/{grid.ZOO}/{grid.SIDE}/{name}, "
              f"apart from {', '.join(ADDED)}")
    for name in ("lrsnash_input.txt", "replicator_runs.csv"):
        check((out / "games" / g / name).read_bytes() == (FULL / grid.ZOO / grid.SIDE / name).read_bytes(),
              f"t = 1: games/{g}/{name} is identical")
    check(zero["signal"] == "uniform" and zero["temperature"] is None
          and all(p == 1 / n for row in zero["channel"] for p in row)
          and zero["transparency"] == 0.0, "t = 0 is exactly uniform, of transparency 0")
    share = {b: sum(zoo.action(b, h) == "C" for h in bots) / n for b in bots}
    check(all(p["cells"][i][j][0] == ("C" if share[b] >= a else "D")
              for (t, a), p in points.items() if t == 0
              for i, b in enumerate(bots) for j in range(n)),
          "t = 0: each bot plays C against everyone iff it cooperates with a share ≥ α of the zoo")

    print(" 2. Every cell follows from the saved channel")
    dist = distances(zoo, family)
    check(saved["distances"] == [[dist[(a, b)] for b in bots] for a in bots], "distances")
    ok = True
    for c in saved["channels"]:
        ch = {b: dict(zip(bots, row)) for b, row in zip(bots, c["channel"])}
        ok &= all(math.isclose(sum(row), 1, abs_tol=1e-12) for row in c["channel"])
        ok &= abs(transparency(ch) - c["transparency"]) < 1e-12
        ok &= c["mass"] == [[decision_mass(zoo, a, ch[b]) for b in bots] for a in bots]
        ok &= c["shortfall"] == [[shortfall(zoo, a, ch[b]) for b in bots] for a in bots]
        ok &= all(abs(m + s - 1) < 1e-12 for mr, sr in zip(c["mass"], c["shortfall"])
                  for m, s in zip(mr, sr))
    check(ok, "channels: rows sum to 1; transparency, masses and shortfalls recomputed from "
              "them; mass + shortfall = 1")
    check(all(p["cells"][i][j] == "".join(
        "C" if s <= (1 - p["alpha"]) * (1 + TIE_TOLERANCE) else "D"
        for s in (channels[p["t"]]["shortfall"][i][j], channels[p["t"]]["shortfall"][j][i]))
        for p in saved["points"] for i in range(n) for j in range(n)),
        "cells: each bot plays C iff its shortfall against the other is ≤ 1 - α")
    only_cooperate_bot = [["".join("C" if b == "CooperateBot" else "D" for b in (r, c))
                           for c in bots] for r in bots]
    check(all(p["cells"] == only_cooperate_bot for (t, a), p in points.items() if a == 1 and t < 1),
          "α = 1, t < 1: only CooperateBot cooperates, as every hypothesis has positive weight")
    errors = [abs(c["transparency"] - c["t"]) for c in saved["channels"]]
    check(all(c["reached"] for c in saved["channels"]) and not saved["unreached"],
          f"every channel's transparency is its t (max error {max(errors):.1e})")

    print(" 3. Game folders")
    by_cells: dict = {}
    for p in saved["points"]:
        by_cells.setdefault(json.dumps(p["cells"]), set()).add(p["game"])
    check(all(len(g) == 1 for g in by_cells.values()) and len(by_cells) == saved["n_games"],
          f"{saved['n_games']} games: points share a game iff their cells are equal")
    folders = sorted(p.name for p in (out / "games").iterdir())
    check(folders == [g["id"] for g in saved["games"]], "games/ holds exactly the grid's games")
    ok = True
    for g in saved["games"]:
        eq = json.loads((out / "games" / g["id"] / "equilibria.json").read_text())
        rep = json.loads((out / "games" / g["id"] / "replicator.json").read_text())
        ok &= all(eq[k] == rep[k] for k in ("bots", "A", "family", "game", "points"))
        ok &= (eq["family"], eq["game"], eq["points"]) == (family, g["id"], g["points"])
        ok &= all(points[(q["t"], q["alpha"])]["cells"] == eq["cells"] for q in g["points"])
        ok &= [(c["id"], c["bots"]) for c in rep["components"]] == [
            (c["id"], c["bots"]) for c in eq["components"]]
        ok &= sum(c["n_starts"] for c in rep["components"]) + rep["unconverged"]["n_starts"] \
            == rep["n_starts"]
        ok &= rep["settings"]["horizon"] == g["horizon"]
    check(ok, "each folder: its points' cells, the same game and components in both files, "
              "starts add up, the horizon of grid.json")
    reps = {g["id"]: json.loads((out / "games" / g["id"] / "replicator.json").read_text())
            for g in saved["games"]}
    longer = {k: f"{r['settings']['horizon']:g}" for k, r in reps.items()
              if r["settings"]["horizon"] > saved["settings"]["horizon"]}
    check(all(r["n_converged"] == r["n_starts"] for r in reps.values()),
          f"every start of every game converged (integrated longer than "
          f"{saved['settings']['horizon']:g}: {longer or 'none'})")

    print(" 4. The original's endpoints (T = 1e4 at t = 0; syntactic: T = 1e-6 at t = 1)")
    theirs = sweep(zoo, family, tuple(ts), tuple(saved["alphas"]))
    changed = [(r.t, r.alpha) for r in theirs
               if [["".join(r.cells[(a, b)]) for b in bots] for a in bots]
               != points[(r.t, r.alpha)]["cells"]]
    check(not changed, f"same tournaments at every grid point (differ at: {changed or 'none'})")
    print()

print("Twin flag, on body8+natives (DupocBot, MaxConfidenceBot, MinConfidenceBot are twins)")
natives = load_zoo("body8+natives", grid.SIDE)
for family in FAMILIES:
    dist = distances(natives, family)
    twins, top = twin_classes(natives.bots, dist), ceiling(natives.bots, dist)
    flagged = grid._channels(natives, dist, sweep(natives, family, (1.0, 0.9, 0.8),
                                                  opaque_temperature=grid.OPAQUE_TEMPERATURE,
                                                  top_temperature=grid.TOP_TEMPERATURE))
    unreached = [c["t"] for c in flagged if not c["reached"]]
    check(twins == [("DupocBot", "MaxConfidenceBot", "MinConfidenceBot")] and top < 0.9
          and unreached == [0.9],
          f"{family}: twins found, ceiling {top:.4f}; of t = 1, 0.9, 0.8 only 0.9 unreached")

print("\nFAILED" if failures else "\nALL OK")
sys.exit(1 if failures else 0)
