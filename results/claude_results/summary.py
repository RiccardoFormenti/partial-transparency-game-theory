"""Per-grid-point summary of the partial-transparency results, behavioral family.

For every grid point (t, α) of results/partial_transparency/body8/floor/behavioral/, this reads
the game the point plays and collects three views of cooperation. Each is a probability
Pr[(C, C)] that two bots drawn independently from a population both cooperate:

- **Nash:** the cooperation of each component of the game's Nash equilibria (equilibria.json).
  On body8 every component has a single cooperation level: 1, 0 or 11/18.
- **Replicator:** the cooperation of the population each of the 1000 starts ends at
  (replicator_runs.csv), and the share of starts that reach a fully cooperative component.
- **Tournament:** the cooperation of the uniform population of all eight bots, before any
  selection. This is grid.json's `mutual_cooperation`, the share of ordered pairs whose cell
  is CC.

It also tests one mechanism. DupocBot cooperates iff its mass (the weight its signal puts on
bots it would cooperate with) is ≥ α. Cooperation needs it to recognize itself, mass ≥ α facing
DupocBot, without being exploited, mass < α facing OBot and DefectBot. `dupoc_window` predicts
each point's outcome from that window alone and lists where the prediction fails.

Run from true/:

    conda run -n py-random python results/claude_results/summary.py

It writes summary_behavioral.csv and facts_behavioral.json next to this file and prints the
facts. figures.py draws the figures from the same table.
"""
import json
from fractions import Fraction
from itertools import combinations
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
FAMILY = "behavioral"
DATA = HERE.parent / "partial_transparency" / "body8" / "floor" / FAMILY


def load_grid():
    return json.loads((DATA / "grid.json").read_text())


def component_kind(component):
    """'cooperation' (Pr[(C, C)] = 1 somewhere in it), 'defection' (0 throughout) or 'partial'."""
    lo, hi = Fraction(component["cooperation"]["min"]), Fraction(component["cooperation"]["max"])
    if hi == 1:
        return "cooperation"
    if hi == 0:
        return "defection"
    return "partial"


def summarize_game(game_dir, bots):
    """One game's Nash set and replicator outcome, as a flat dict."""
    eq = json.loads((game_dir / "equilibria.json").read_text())
    rep = json.loads((game_dir / "replicator.json").read_text())
    runs = pd.read_csv(game_dir / "replicator_runs.csv")
    assert eq["bots"] == bots and rep["bots"] == bots

    kinds = {c["id"]: component_kind(c) for c in eq["components"]}
    levels = sorted({Fraction(c["cooperation"][end]) for c in eq["components"]
                     for end in ("min", "max")})
    coop_ids = [i for i, k in kinds.items() if k == "cooperation"]
    coop_starts = sum(c["n_starts"] for c in rep["components"] if c["id"] in coop_ids)
    assert rep["n_converged"] == rep["n_starts"] == len(runs)

    row = {
        "n_equilibria": eq["n_equilibria"],
        "n_components": eq["n_components"],
        "ne_coop_levels": ";".join(str(x) for x in levels),
        "ne_coop_min": float(levels[0]),
        "ne_coop_max": float(levels[-1]),
        "has_cooperation": "cooperation" in kinds.values(),
        "has_partial": "partial" in kinds.values(),
        "has_defection": "defection" in kinds.values(),
        "n_starts": rep["n_starts"],
        "coop_basin": coop_starts / rep["n_starts"],
        "rep_coop_mean": runs["cooperation"].mean(),
        "rep_coop_min": runs["cooperation"].min(),
        "rep_coop_max": runs["cooperation"].max(),
        "rep_payoff_mean": runs["payoff"].mean(),
        "horizon": rep["settings"]["horizon"],
    }
    for b in bots:
        row[f"end:{b}"] = runs[f"end:{b}"].mean()
    return row


def build_table(grid=None):
    """One row per grid point, in grid.json's order (t descending, then α ascending)."""
    grid = grid or load_grid()
    bots = grid["bots"]
    games = {g["id"]: summarize_game(DATA / "games" / g["id"], bots) for g in grid["games"]}
    channels = {c["t"]: c for c in grid["channels"]}
    rows = []
    for p in grid["points"]:
        ch = channels[p["t"]]
        rows.append({"t": p["t"], "alpha": p["alpha"], "game": p["game"],
                     "temperature": ch["temperature"], "transparency": ch["transparency"],
                     "tournament_coop": p["mutual_cooperation"], **games[p["game"]]})
    return pd.DataFrame(rows)


def dupoc_masses(grid=None, against=("DupocBot", "OBot", "DefectBot")):
    """DupocBot's mass facing each bot of `against`, at each t, ascending in t."""
    grid = grid or load_grid()
    ix = {b: i for i, b in enumerate(grid["bots"])}
    rows = [{"t": c["t"], **{b: c["mass"][ix["DupocBot"]][ix[b]] for b in against}}
            for c in grid["channels"]]
    return pd.DataFrame(rows).sort_values("t").reset_index(drop=True)


def dupoc_window(df, grid=None):
    """Grid points (α > 0) where 'DupocBot recognizes itself and no defector exploits it'
    disagrees with the replicator outcome.

    The comparison with α is grid.json's own rule: C iff shortfall ≤ (1 − α)(1 + tie_tolerance).
    """
    grid = grid or load_grid()
    ix = {b: i for i, b in enumerate(grid["bots"])}
    tol = grid["settings"]["tie_tolerance"]
    shortfall = {c["t"]: c["shortfall"][ix["DupocBot"]] for c in grid["channels"]}
    misses = []
    for r in df[df["alpha"] > 0].itertuples():
        cooperates = lambda b: shortfall[r.t][ix[b]] <= (1 - r.alpha) * (1 + tol)
        predicted = cooperates("DupocBot") and not (cooperates("OBot") or cooperates("DefectBot"))
        if predicted != (r.coop_basin == 1):
            misses.append({"t": r.t, "alpha": r.alpha, "predicted_cooperation": predicted})
    return misses


def violations(series):
    """Ordered pairs t1 < t2 with value(t1) > value(t2): breaches of 'more t, at least as much'.

    `series` is indexed by t."""
    s = series.sort_index()
    return sum(1 for (_, a), (_, b) in combinations(s.items(), 2) if a > b + 1e-12)


def facts(df):
    """The numbers README.md quotes, checked along the way."""
    alphas = sorted(df["alpha"].unique())
    ts = sorted(df["t"].unique())
    nontrivial = [a for a in alphas if a > 0]
    out = {"family": FAMILY, "n_points": len(df), "n_games": df["game"].nunique(),
           "alphas": alphas, "nontrivial_alphas": nontrivial, "per_alpha": {}}

    # The replicator outcome is all-or-nothing, and it is cooperative exactly where a fully
    # cooperative Nash component exists.
    assert set(df["coop_basin"]) <= {0.0, 1.0}
    assert (df["has_cooperation"] == (df["coop_basin"] == 1)).all()
    assert (df["rep_coop_mean"].round(9) == df["ne_coop_max"]).all()
    assert (df["rep_coop_min"].round(9) == df["rep_coop_max"].round(9)).all()
    out["nash_replicator_agree"] = True

    # Theorem 2.9: the constant DefectBot profile, so a fully defecting component, survives
    # at every grid point where some bot can defect (α > 0).
    assert df.loc[df["alpha"] > 0, "has_defection"].all()
    assert (df.loc[df["alpha"] > 0, "ne_coop_min"] == 0).all()
    assert set(df.loc[df["has_partial"], "ne_coop_levels"]) == {"0;11/18;1"}

    n_pairs = 0
    for a in alphas:
        d = df[df["alpha"] == a].set_index("t")
        coop_ts = sorted(d.index[d["coop_basin"] == 1])
        threshold = coop_ts[0] if coop_ts else None
        # Monotone: cooperative exactly on {t ≥ threshold}.
        assert coop_ts == [t for t in ts if threshold is not None and t >= threshold]
        n_pairs += len(list(combinations(d.index, 2)))
        partial_ts = sorted(d.index[d["has_partial"]])
        if partial_ts:  # the 11/18 component, where present, also lives on {t ≥ its lowest t}
            assert partial_ts == [t for t in ts if t >= partial_ts[0]]
            # Nested sets of equilibrium cooperation: {0} ⊂ {0, 1} ⊂ {0, 11/18, 1} as t grows.
            assert partial_ts[0] >= threshold
        out["per_alpha"][str(a)] = {
            "threshold_t": threshold,
            "partial_lowest_t": partial_ts[0] if partial_ts else None,
            "violations_nash_best": violations(d["ne_coop_max"]),
            "violations_replicator": violations(d["rep_coop_mean"]),
            "violations_n_components": violations(d["n_components"]),
            "violations_tournament": violations(d["tournament_coop"]),
            "tournament_coop_at_t1": d.loc[1.0, "tournament_coop"],
            "tournament_coop_range": [d["tournament_coop"].min(), d["tournament_coop"].max()],
            "tournament_coop_at_threshold_minus": (
                None if threshold in (None, 0.0)
                else d.loc[max(t for t in ts if t < threshold), "tournament_coop"]),
        }
    out["n_ordered_pairs_checked"] = n_pairs
    for key in ("violations_nash_best", "violations_replicator", "violations_n_components",
                "violations_tournament"):
        out[f"total_{key}"] = sum(v[key] for v in out["per_alpha"].values())

    # Averaged over the non-trivial cautions: the share sustaining cooperation, and the
    # cooperation of the uniform population.
    nt = df[df["alpha"] > 0].groupby("t")
    out["share_cooperative_at"] = {str(t): float(nt["coop_basin"].mean()[t])
                                   for t in (1.0, 0.5, 0.25, 0.0)}
    out["mean_tournament_coop_at"] = {str(t): float(nt["tournament_coop"].mean()[t])
                                      for t in (1.0, 0.5, 0.25, 0.0)}

    misses = dupoc_window(df)
    out["dupoc_window"] = {"n_points": int((df["alpha"] > 0).sum()),
                           "n_predicted": int((df["alpha"] > 0).sum()) - len(misses),
                           "misses": misses}
    return out


def main():
    df = build_table()
    df.to_csv(HERE / f"summary_{FAMILY}.csv", index=False)
    f = facts(df)
    (HERE / f"facts_{FAMILY}.json").write_text(json.dumps(f, indent=2) + "\n")

    print(f"{FAMILY}: {f['n_points']} grid points, {f['n_games']} games")
    print("Nash and replicator agree at every point:", f["nash_replicator_agree"])
    print(f"ordered pairs (t1 < t2) checked: {f['n_ordered_pairs_checked']}; violations of "
          f"monotonicity: Nash best {f['total_violations_nash_best']}, replicator "
          f"{f['total_violations_replicator']}, number of components "
          f"{f['total_violations_n_components']}, tournament {f['total_violations_tournament']}")
    print(f"{'alpha':>6} {'t*':>6} {'11/18 from':>11} {'tourn. t=1':>11} {'tourn. range':>15} "
          f"{'viol. tourn.':>13}")
    for a, v in f["per_alpha"].items():
        lo, hi = v["tournament_coop_range"]
        th = "-" if v["threshold_t"] is None else f"{v['threshold_t']:.2f}"
        pt = "-" if v["partial_lowest_t"] is None else f"{v['partial_lowest_t']:.2f}"
        print(f"{a:>6} {th:>6} {pt:>11} {v['tournament_coop_at_t1']:>11.3f} "
              f"{f'[{lo:.3f}, {hi:.3f}]':>15} {v['violations_tournament']:>13}")
    print("share of non-trivial α with cooperation:", f["share_cooperative_at"])
    print("mean tournament cooperation over non-trivial α:", f["mean_tournament_coop_at"])
    w = f["dupoc_window"]
    print(f"DupocBot's window predicts {w['n_predicted']} of {w['n_points']} points; "
          f"misses: {w['misses']}")


if __name__ == "__main__":
    main()
