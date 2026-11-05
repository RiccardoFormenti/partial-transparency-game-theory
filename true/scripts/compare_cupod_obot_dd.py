"""Compare results/cupod_obot_dd/ (CupodBot vs OBot at (D, D)) with the original results.

Starts are paired: the variant's n starts are the first n of the original's seeded draws, so
every replicator number below is taken over those same n starts on both sides, and a difference
is the cell's doing, not sampling. Saved to results/cupod_obot_dd/comparison.txt.

Usage (from true/):  python scripts/compare_cupod_obot_dd.py
"""

import csv
import json
import re
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

TRUE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TRUE))

from replication.general.replicator import (ATOL, RTOL, growth_rates,  # noqa: E402
                                            sample_starts, softmax)

RESULTS = TRUE / "results"
NEW = RESULTS / "cupod_obot_dd"
SEED = 20260514  # the replicator starts' (full_transparency.replicator)
ORBIT_STARTS, ORBIT_TIME = 20, 2e3  # time averages of a cycling game: starts, and how long
AMPLITUDE_STARTS, AMPLITUDE_TIME = 2, 2e4  # is the amplitude constant? starts, and how long
SWEEPS = {"default grid": "body8/floor", "alpha_0.5-1": "alpha_0.5-1/body8/floor"}
FAMILIES = ("behavioral", "syntactic")
TIMING = re.compile(r"\*\d+\.\d+u ")  # lrsnash's resource-use line, which changes every run

lines: list[str] = []
failures = 0


def say(text: str = "") -> None:
    lines.append(text)
    print(text)


def control(ok: bool, text: str) -> None:
    """A check the comparison itself relies on: failing one means the comparison is not valid."""
    global failures
    failures += not ok
    say(f"  {'OK  ' if ok else 'FAIL'} control: {text}")


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def runs(folder: Path, n: int | None = None) -> list[dict]:
    with (folder / "replicator_runs.csv").open() as f:
        rows = list(csv.DictReader(f))
    return rows[:n]


def starts(rows: list[dict]) -> list[tuple]:
    return [tuple(v for k, v in r.items() if k.startswith("start:")) for r in rows]


def ends(rows: list[dict]) -> list[tuple]:
    return [tuple(v for k, v in r.items() if k.startswith("end:")) for r in rows]


def mean_end(rows: list[dict], bots: list[str]) -> str:
    """Each bot's mean end share over these starts, leaving out bots that are gone."""
    means = {b: sum(float(r[f"end:{b}"]) for r in rows) / len(rows) for b in bots}
    return ", ".join(f"{b} {m:.3f}" for b, m in means.items() if m >= 5e-4)


def nash_key(eq: dict) -> tuple:
    """The equilibria themselves, independent of component ids: each extreme equilibrium's
    strategies and payoffs, and each component's bots and ranges."""
    return (sorted((json.dumps(e["row"], sort_keys=True), json.dumps(e["col"], sort_keys=True),
                    e["row_payoff"], e["col_payoff"], e["cooperation"]) for e in eq["equilibria"]),
            sorted((c["bots"], c["cooperation"]["min"], c["cooperation"]["max"],
                    c["row_payoff"]["min"], c["row_payoff"]["max"]) for c in eq["components"]))


def nash_summary(eq: dict) -> tuple:
    """The headline: counts, and each component's Pr[(C, C)] range, ascending."""
    return (eq["n_components"], eq["n_equilibria"], tuple(sorted(
        (Fraction(c["cooperation"]["min"]), Fraction(c["cooperation"]["max"]))
        for c in eq["components"])))


def outcome(rows: list[dict]) -> tuple:
    """Over these starts: how many converged, and how many end at each Pr[(C, C)]."""
    ended = Counter(round(float(r["cooperation"]), 6) for r in rows)
    return sum(r["converged"] == "True" for r in rows), tuple(sorted(ended.items()))


def changed_cells(bots: list[str], old: list[list[str]], new: list[list[str]]) -> list[str]:
    return [f"{a} vs {b}: {old[i][j]} -> {new[i][j]}" for i, a in enumerate(bots)
            for j, b in enumerate(bots) if i < j and old[i][j] != new[i][j]]


def full_transparency() -> None:
    say("=" * 78 + "\n1. FULL TRANSPARENCY, body8\n" + "=" * 78)
    old_dir, new_dir = (r / "body8" for r in (RESULTS / "full_transparency",
                                              NEW / "full_transparency"))
    old, new = (load(d / "floor" / "equilibria.json") for d in (old_dir, new_dir))
    say(f"floor cells changed: {changed_cells(old['bots'], old['cells'], new['cells'])}")
    say(f"floor Nash: {old['n_components']} components ({old['n_equilibria']} extreme) -> "
        f"{new['n_components']} components ({new['n_equilibria']} extreme)")
    say(f"floor equilibria identical, strategy by strategy: {nash_key(old) == nash_key(new)}")
    for c in new["components"]:
        say(f"  component {c['id']}: {', '.join(c['bots'])}; Pr[(C, C)] {c['cooperation']['min']}"
            f" to {c['cooperation']['max']}; payoff {c['row_payoff']['min']} to "
            f"{c['row_payoff']['max']}")
    n = len(runs(new_dir / "floor"))
    a, b = runs(old_dir / "floor", n), runs(new_dir / "floor")
    control(starts(a) == starts(b), f"the {n} floor starts are the original's first {n}")
    say(f"floor replicator, same {n} starts: old {outcome(a)}  new {outcome(b)}")
    moved = max(abs(float(x[f"end:{bot}"]) - float(y[f"end:{bot}"]))
                for x, y in zip(a, b) for bot in old["bots"])
    say(f"  largest change in any bot's end share over these starts: {moved:.3g}")
    say(f"  mean end shares: old {mean_end(a, old['bots'])}")
    say(f"                   new {mean_end(b, old['bots'])}")
    same = all((old_dir / "hinge" / f).read_text() == (new_dir / "hinge" / f).read_text()
               for f in ("equilibria.json", "lrsnash_input.txt"))
    control(same, "hinge side, where the cell was DD already, is byte-identical")
    say()


def ladder() -> None:
    say("=" * 78 + "\n2. ZOO LADDER, floor side\n" + "=" * 78)
    old_dir, new_dir = RESULTS / "zoo_ladder" / "floor", NEW / "zoo_ladder" / "floor"
    old = {z["zoo"]: z for z in load(old_dir / "ladder.json")["zoos"]}
    for z in load(new_dir / "ladder.json")["zoos"]:
        name, o = z["zoo"], old[z["zoo"]]
        eo, en = (load(d / name / "equilibria.json") for d in (old_dir, new_dir))
        say(f"{name}")
        cells = changed_cells(eo["bots"], eo["cells"], en["cells"])
        say(f"  cells changed: {cells or 'none (CupodBot is not in this zoo)'}")
        say(f"  Nash: {o['nash']['n_components']} ({o['nash']['n_equilibria']}) -> "
            f"{z['nash']['n_components']} ({z['nash']['n_equilibria']}); identical: "
            f"{nash_key(eo) == nash_key(en)}; cooperative component "
            f"{z['nash']['cooperative_component']['bots']}")
        n = z["replicator"]["n_starts"]
        a, b = runs(old_dir / name, n), runs(new_dir / name)
        control(starts(a) == starts(b), f"starts are the original's first {n}")
        say(f"  replicator, horizon {z['replicator']['horizon']:g}, same {n} starts: "
            f"old {outcome(a)}  new {outcome(b)}")
        flipped = sum((float(x["cooperation"]) > 0.5) != (float(y["cooperation"]) > 0.5)
                      for x, y in zip(a, b))
        say(f"  starts whose end state changed side (cooperative vs not): {flipped} of {n}")
        say(f"  mean end shares: old {mean_end(a, z['bots'])}")
        say(f"                   new {mean_end(b, z['bots'])}")
        say(f"  (old, all {o['replicator']['n_starts']} starts: cooperative basin "
            f"{o['replicator']['cooperative_basin']}, {o['replicator']['n_converged']} converged)")
    say()


def path(A: np.ndarray, start: np.ndarray, times: np.ndarray) -> np.ndarray:
    """x at each of `times` (a row each), integrated as `general.replicator.integrate` does."""
    sol = solve_ivp(lambda _, z: growth_rates(A, softmax(z)), (0, times[-1]), np.log(start),
                    method="LSODA", t_eval=times, rtol=RTOL, atol=ATOL)
    return np.array([softmax(z) for z in sol.y.T])


def centre_spectrum(A: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Eigenvalues of the replicator dynamics at x, on the simplex over x's support."""
    idx = np.flatnonzero(x > 0)
    B, y, n, h = A[np.ix_(idx, idx)], x[idx], len(idx), 1e-6

    def flow(v: np.ndarray) -> np.ndarray:
        p = B @ v
        return v * (p - v @ p)

    J = np.column_stack([(flow(y + h * e) - flow(y - h * e)) / (2 * h) for e in np.eye(n)])
    Q = np.linalg.qr(np.column_stack([np.ones(n), np.eye(n)[:, :n - 1]]))[0][:, 1:]
    return np.linalg.eigvals(Q.T @ J @ Q)


def orbits(folder: Path) -> dict:
    """What a cycling game's population does: where it cycles, its time-averaged Pr[(C, C)]
    and payoff, whether its amplitude holds still, and the rest point it cycles around."""
    eq = load(folder / "equilibria.json")
    bots = eq["bots"]
    A = np.array([[float(Fraction(a)) for a in r] for r in eq["A"]])
    cc = np.array([[c == "CC" for c in r] for r in eq["cells"]], dtype=float)
    starts_ = sample_starts(len(A), ORBIT_STARTS, SEED)
    late = np.linspace(ORBIT_TIME / 2, ORBIT_TIME, 4001)
    coop, pay, support = [], [], Counter()
    for s in starts_:
        X = path(A, s, late)
        coop.append(float(np.einsum("ti,ij,tj->t", X, cc, X).mean()))
        pay.append(float(np.einsum("ti,ij,tj->t", X, A, X).mean()))
        support[tuple(b for b, m in zip(bots, X.max(0)) if m >= 1e-6)] += 1
    drift = 0.0
    for s in starts_[:AMPLITUDE_STARTS]:
        X = path(A, s, np.linspace(0, AMPLITUDE_TIME, 40001))
        q = len(X) // 10
        early, last = X[q:2 * q], X[-q:]  # two windows, a decade of time apart
        drift = max(drift, float(np.abs(early.max(0) - last.max(0)).max()),
                    float(np.abs(early.min(0) - last.min(0)).max()))
    rests = []
    for e in eq["equilibria"]:
        if e["symmetric"] and len(e["row"]) > 1 and set(e["row"]) <= set(support.most_common(1)[0][0]):
            x = np.array([float(Fraction(e["row"].get(b, "0"))) for b in bots])
            rests.append((e["row"], e["cooperation"], centre_spectrum(A, x)))
    return {"coop": coop, "pay": pay, "support": support, "drift": drift, "rests": rests}


def drops(grid: dict, values: dict) -> list[str]:
    """Every step up in t, at a fixed α, between adjacent grid t, where the value falls."""
    ts, out = sorted(grid["ts"]), []
    for a in grid["alphas"]:
        for lo, hi in zip(ts, ts[1:]):
            if values[(hi, a)] < values[(lo, a)] - 1e-9:
                out.append(f"alpha {a:g}, t {lo:g} -> {hi:g}: {float(values[(lo, a)]):.3f} -> "
                           f"{float(values[(hi, a)]):.3f}")
    return out


def thresholds(grid: dict, coop: dict) -> dict:
    """α -> (t*, one switch?). t* is the lowest t from which on every higher grid t ends fully
    cooperative; one switch means every t below it ends fully defecting."""
    out = {}
    for a in grid["alphas"]:
        ts = sorted(grid["ts"], reverse=True)
        star = None
        for t in ts:
            if coop[(t, a)] != 1:
                break
            star = t
        below = [coop[(t, a)] for t in ts if star is None or t < star]
        out[a] = (star, all(c == 0 for c in below))
    return out


def sweep(label: str, path: str, family: str) -> None:
    old_dir = RESULTS / "partial_transparency" / path / family
    new_dir = NEW / "partial_transparency" / path / family
    old, new = load(old_dir / "grid.json"), load(new_dir / "grid.json")
    say(f"--- {label}, {family}")
    control(old["ts"] == new["ts"] and old["alphas"] == new["alphas"] and old["bots"] == new["bots"],
            f"same grid, {len(new['points'])} points")
    dist = sum(x != y for r, s in zip(old["distances"], new["distances"]) for x, y in zip(r, s))
    say(f"  distance matrix entries changed: {dist}; temperatures changed at "
        f"{sum(x['temperature'] != y['temperature'] for x, y in zip(old['channels'], new['channels']))}"
        f" of {len(new['ts'])} t values; unreached {new['unreached']}; twins {new['twins']}")
    say(f"  distinct games: {old['n_games']} -> {new['n_games']}; horizons "
        f"{dict(sorted(Counter(g['horizon'] for g in old['games']).items()))} -> "
        f"{dict(sorted(Counter(g['horizon'] for g in new['games']).items()))}")

    n = load(new_dir / "games" / "g00" / "replicator.json")["n_starts"]
    cache: dict = {}

    def game(folder: Path, gid: str) -> dict:
        key = (folder, gid)
        if key not in cache:
            d = folder / "games" / gid
            rows = runs(d, n)
            cache[key] = {"eq": load(d / "equilibria.json"), "rows": rows, "out": outcome(rows),
                          "horizon": load(d / "replicator.json")["settings"]["horizon"]}
        return cache[key]

    op = {(p["t"], p["alpha"]): p for p in old["points"]}
    cell_diff, nash_diff, nash_exact_diff, out_diff = [], [], [], []
    same_cells, same_cells_differ = 0, 0
    pair_counts: Counter = Counter()
    for p in new["points"]:
        key = (p["t"], p["alpha"])
        o = op[key]
        go, gn = game(old_dir, o["game"]), game(new_dir, p["game"])
        if o["cells"] != p["cells"]:
            cell_diff.append(key)
            pair_counts.update(c.split(":")[0] for c in changed_cells(old["bots"], o["cells"],
                                                                     p["cells"]))
        else:
            same_cells += 1
            # The original may have raised the horizon for a start beyond the first n.
            same_cells_differ += (gn["out"] != go["out"] or nash_key(go["eq"]) != nash_key(gn["eq"])
                                  or (gn["horizon"] == go["horizon"]
                                      and ends(gn["rows"]) != ends(go["rows"])))
        if nash_summary(go["eq"]) != nash_summary(gn["eq"]):
            nash_diff.append(key)
        if nash_key(go["eq"]) != nash_key(gn["eq"]):
            nash_exact_diff.append(key)
        if go["out"] != gn["out"]:
            out_diff.append(key)
    total = len(new["points"])
    say(f"  tournaments that differ: {len(cell_diff)} of {total} points")
    for pair, c in pair_counts.most_common(12):
        say(f"      {pair}: {c} points")
    say(f"  Nash headline (counts, component Pr[(C, C)]) differs: {len(nash_diff)} of {total}; "
        f"any extreme equilibrium differs: {len(nash_exact_diff)} of {total}")
    say(f"  replicator outcome differs, same {n} starts: {len(out_diff)} of {total}")
    control(same_cells_differ == 0, f"the {same_cells} points with unchanged cells reproduce the "
                                    f"old equilibria and every end state exactly")

    def cooperation_map(g: dict, folder: Path, points: list[dict]) -> tuple[dict, dict]:
        ended, best = {}, {}
        for p in points:
            x = game(folder, p["game"])
            ended[(p["t"], p["alpha"])] = sum(float(r["cooperation"]) for r in x["rows"]) / n
            best[(p["t"], p["alpha"])] = max(Fraction(c["cooperation"]["max"])
                                             for c in x["eq"]["components"])
        return ended, best

    (eo, bo), (en, bn) = (cooperation_map(g, d, g["points"])
                          for g, d in ((old, old_dir), (new, new_dir)))
    to, tn = thresholds(old, {k: round(v, 6) for k, v in eo.items()}), \
        thresholds(new, {k: round(v, 6) for k, v in en.items()})
    say("  alpha   t* old   t* new   one switch old/new")
    for a in new["alphas"]:
        mark = "" if to[a][0] == tn[a][0] else "   <-- changed"
        say(f"  {a:5g}   {to[a][0]!s:>6}   {tn[a][0]!s:>6}   {to[a][1]}/{tn[a][1]}{mark}")
    # At an unconverged start the end state is a snapshot of an orbit, not an outcome.
    open_points = {(p["t"], p["alpha"]): p["game"] for p in new["points"]
                   if game(new_dir, p["game"])["out"][0] < n}
    below_best = [k for k in en if k not in open_points and abs(en[k] - float(bn[k])) > 1e-6]
    say(f"  converged points where the replicator ends below the best Nash: old "
        f"{sum(abs(eo[k] - float(bo[k])) > 1e-6 for k in eo)}, new {len(below_best)}"
        + (f"  e.g. {below_best[:6]}" if below_best else ""))
    say(f"  points with unconverged starts: old "
        f"{sum(game(old_dir, p['game'])['out'][0] < n for p in old['points'])}, "
        f"new {len(open_points)} in {len(set(open_points.values()))} games")
    for a in new["alphas"]:
        at = sorted(k[0] for k in open_points if k[1] == a)
        if at:
            say(f"      alpha {a:g}: {len(at)} points, t from {at[0]:g} to {at[-1]:g}; old outcome "
                f"there {sorted({round(eo[(t, a)], 6) for t in at})}")
    selected = dict(en)  # the replicator outcome, with an orbit's time average at open points
    for gid in sorted(set(open_points.values())):
        x, o = game(new_dir, gid), orbits(new_dir / "games" / gid)
        at = sorted(k for k, g in open_points.items() if g == gid)
        for k in at:
            selected[k] = float(np.mean(o["coop"]))
        say(f"      {gid} at {at}: {x['out'][0]} of {n} converged by {x['horizon']:g}")
        say(f"        cycles on {dict(o['support'])}")
        say(f"        over {ORBIT_STARTS} starts: time-averaged Pr[(C, C)] {min(o['coop']):.3f} to "
            f"{max(o['coop']):.3f}, mean {np.mean(o['coop']):.3f}; payoff {min(o['pay']):.3f} to "
            f"{max(o['pay']):.3f}")
        say(f"        largest change in a share's min or max between t ~ {AMPLITUDE_TIME / 10:g} "
            f"and t ~ {AMPLITUDE_TIME:g}: {o['drift']:.2e}")
        for row, coop_at_rest, spectrum in o["rests"]:
            say(f"        rest point {row}, Pr[(C, C)] {coop_at_rest}: eigenvalues "
                f"{np.round(spectrum, 5).tolist()}")
    islands = [k for k, v in en.items() if k not in open_points and v > 1e-6
               and tn[k[1]][0] is not None and k[0] < tn[k[1]][0]]
    say(f"  converged points below t* with any cooperation: {len(islands)}")
    split = lambda g, d: sum(len(game(d, p["game"])["out"][1]) > 1 and
                             game(d, p["game"])["out"][0] == n for p in g["points"])
    say(f"  converged points whose starts split between outcomes: old {split(old, old_dir)}, "
        f"new {split(new, new_dir)}")
    say("  steps up in t that LOWER cooperation:")
    for label_, o_, n_ in (("best Nash", bo, bn), ("replicator", eo, selected)):
        do, dn = drops(old, o_), drops(new, n_)
        say(f"    {label_}: old {len(do)}, new {len(dn)}")
        for line in dn:
            say(f"      {line}")
    n_comp = lambda g, d: {(p["t"], p["alpha"]): game(d, p["game"])["eq"]["n_components"]
                           for p in g["points"]}
    say(f"    number of Nash components: old {len(drops(old, n_comp(old, old_dir)))}, "
        f"new {len(drops(new, n_comp(new, new_dir)))}")
    levels = lambda g, d: sorted({str(Fraction(c["cooperation"]["max"])) for p in g["points"]
                                  for c in game(d, p["game"])["eq"]["components"]})
    say(f"  Nash cooperation levels on the grid: old {levels(old, old_dir)}, "
        f"new {levels(new, new_dir)}")
    say()


def main() -> None:
    full_transparency()
    ladder()
    say("=" * 78 + "\n3. PARTIAL TRANSPARENCY\n" + "=" * 78)
    for label, path in SWEEPS.items():
        for family in FAMILIES:
            sweep(label, path, family)
    say(f"control failures: {failures}")
    (NEW / "comparison.txt").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
