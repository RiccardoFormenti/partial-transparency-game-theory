# CupodBot vs OBot at (D, D)

The experiments of `results/`, rerun with one change: on the floor side, CupodBot vs OBot is
(D, D) instead of (C, D). That cell is the hinge cell `dich_CupodBot_vs_OBot`, whose hinge side is
already (D, D). So this is the floor side with this one hinge search succeeding and the other 17
failing. The value is assumed, not proven in Lean. No other cell has to change with it: no zoo bot
simulates its opponent against OBot.

`data/` and `replication/` are unchanged. `scripts/run_cupod_obot_dd.py` makes the change in memory.

```
cupod_obot_dd/
  README.md             this file
  comparison.txt        every comparison with the original results
  run.log               the runs' output (see Caveats)
  full_transparency/    body8, both sides
  zoo_ladder/           floor side
  partial_transparency/ body8/ and alpha_0.5-1/, both families
```

The files have the formats described in the READMEs of `results/full_transparency/`,
`results/zoo_ladder/` and `results/partial_transparency/`. To recompute, from `true/`:

```bash
conda run -n py-random python scripts/run_cupod_obot_dd.py
conda run -n py-random python scripts/compare_cupod_obot_dd.py
```

## How this differs from the original runs

- **100 replicator starts per game**, not 1000 (the `alpha_0.5-1` grid always used 100). They are
  the first 100 of the same seeded draws, so `comparison.txt` compares the same starts on both
  sides. The t grid is the same, 0.01.
- **Cycling games are not integrated past 1000.** Five games of the behavioral family never
  converge (see below), so `grid.py`'s raising of the horizon up to 1e9 would take months. The
  run probes each game first. A game in which some start needs more than 5000 right-hand-side
  calls to reach time 1000 is integrated to 1000 only, and its starts are saved as unconverged.
  Such a game has `horizon: 1000` in `grid.json`. Non-cycling games need at most 1600 calls, and
  cycling ones about 17000.

## What changes

**Unchanged:**

- Full transparency: every Nash equilibrium, on both sides, and every start reaching full
  cooperation. Only the mix inside the cooperative component moves: mean DupocBot share 0.654 to
  0.602, TitForTatBot 0.131 to 0.174.
- Zoo ladder: every Nash column.
- Syntactic family: every t\*, and the outcome at every grid point. Nash counts change at 48 of 707
  points (default grid) and 122 of 606 (`alpha_0.5-1`), with the same cooperation levels.

**Changed, all in the behavioral family except the first:**

- `body8+trolls`: over the same 100 starts, 93 end cooperative before and 97 now; 6 starts change
  side. 100 starts cannot pin this difference down.
- t\* moves:

  | α | 0.2 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 |
  |---|---|---|---|---|---|---|---|
  | old | 0.28 | 0.01 | 0.11 | 0.24 | 0.37 | 0.50 | 0.67 |
  | new | 0.28 | 0.02 | 0.14 | 0.29 | 0.44 | 0.48 | 0.66 |

  α = 0 and α = 1 stay at 0 and 1.
- Eight grid points that used to end fully defecting now cycle forever: t = 0.03 at α = 0.7,
  t = 0.13 to 0.15 at α = 0.8, t = 0.34 to 0.37 at α = 0.9.
- So cooperation is no longer monotone in t. Replicator Pr[(C, C)] falls from about 0.2 to 0 as t
  rises from 0.03 to 0.04 (α = 0.7), from 0.15 to 0.16 (α = 0.8) and from 0.37 to 0.38 (α = 0.9).
  At the same three steps the best Nash cooperation falls from 1/3 to 0, and the number of Nash
  components falls.
- New Nash cooperation levels appear: 1/6 and 1/3.

`results/figures/figures.py` cannot draw the behavioral family from these files: its assertion that
every start converges fails. Its syntactic data passes.

### The cycles

Every cycling game has the same rest point: CupodBot 1/4, DupocBot 1/4, EBot 1/6, TitForTatBot 1/3,
with payoff 1/2 and Pr[(C, C)] = 1/6. On those four bots' simplex its eigenvalues are ±0.408i and
−0.5, so the linearisation has a centre. The other four bots die out. Each start then keeps its own
closed orbit: between t ≈ 2000 and t ≈ 20000 no share's minimum or maximum moves by more than
4 × 10⁻⁵, and for g38 the range is unchanged to 5 digits up to t = 10⁵.

The time-averaged shares are the rest point. The time-averaged Pr[(C, C)] depends on the orbit:
0.17 to 0.24 over 20 starts, about 0.20 on average. It is quadratic in the shares, so it does not
equal the rest point's 1/6.

## Caveats

- That these are closed orbits is numerical evidence, not a proof. Support and time averages come
  from 20 starts per game, the amplitude check from 2.
- At a cycling game, the end state and `cooperation` in `replicator_runs.csv` are a snapshot of an
  orbit at time 1000, not an outcome.
- In `comparison.txt`, the step "alpha 0.8, t 0.14 -> 0.15: 0.205 -> 0.201" is noise: both points
  cycle, and the two numbers are finite-time averages. The real drops are the three listed above.
- With 100 starts, a basin below about 3.7% can go unseen. No game's starts split between outcomes.
- `run.log` also holds a grid run that was stopped at g38. The final grid run follows the line
  `=== grid rerun ===`. Its "not converged by time 1e+09" warnings come from `grid.py`'s fixed
  wording: those games were integrated to 1000.
