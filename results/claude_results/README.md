# Does more transparency lead to more cooperation at equilibrium?

An analysis of `results/partial_transparency/body8/floor/behavioral/`: the eight-bot zoo, floor
side, behavioral family, on the full grid of 101 transparencies t × 7 cautions α (707 points,
62 distinct games). The syntactic family is not analysed here yet.

**Answer: yes, at every caution α, and by both criteria.**

- **Nash.** The most cooperative equilibrium never loses cooperation as t grows. The sets of
  equilibrium cooperation levels are nested, {0} ⊂ {0, 1} ⊂ {0, 11/18, 1}, and the number of
  components never falls as t grows.
- **Replicator.** All 1000 starts reach full cooperation exactly when t ≥ t\*(α), and full
  defection below it. The outcome is the best Nash equilibrium at every one of the 707 points.

Over all 35,350 ordered pairs t₁ < t₂ at a fixed α, neither criterion is ever lower at t₂.

## Layout

```
claude_results/
  README.md                this file
  summary.py               per-point table and checks  -> summary_behavioral.csv, facts_behavioral.json
  figures.py               figures                     -> figures/*.pdf (paper), figures/*.png (preview)
  summary_behavioral.csv   one row per (t, α): game, Nash set, replicator outcome, tournament
  facts_behavioral.json    every number quoted below
  figures/
```

To recompute, from `true/`:

```bash
conda run -n py-random python results/claude_results/summary.py
conda run -n py-random python results/claude_results/figures.py
```

`summary.py` asserts every structural claim below (the agreement between Nash and replicator,
monotonicity, nesting, and the DupocBot window) and stops if one fails.

## Three measures of cooperation

Each is Pr[(C, C)], the probability that two bots drawn independently from a population both
cooperate. They differ in the population.

| measure | population | source |
|---|---|---|
| Nash | a Nash equilibrium of the game at (t, α); each component has one level, 0, 11/18 or 1 | `games/<g>/equilibria.json` |
| Replicator | where each of the 1000 uniform starts ends | `games/<g>/replicator_runs.csv` |
| Tournament | the uniform mix of the eight bots, before any selection | `grid.json`, `mutual_cooperation` |

## Findings

**1. Cooperation is monotone in t, with one threshold per α.** These are the thresholds t\*(α),
the least t at which the population ends cooperative:

| α | 0 | 0.2 | 0.4 | 0.5 | 0.6 | 0.8 | 1 |
|---|---|---|---|---|---|---|---|
| t\* | 0 | 0.28 | 0.01 | 0.11 | 0.24 | 0.50 | 1 |
| 11/18 component from | – | 0.72 | 0.36 | 0.28 | 0.39 | 0.69 | 1 |

Averaged over the six non-trivial α, equilibrium cooperation is 1 at t = 1, 0.83 at t = 0.5,
0.5 at t = 0.25 and 0 at t = 0.

**2. Transparency does not make bots cooperate more often; it makes cooperation an
equilibrium.** Averaged over α, tournament cooperation is flat: 0.31, 0.26, 0.27 and 0.29 at
t = 1, 0.5, 0.25 and 0. At a single α it is not even monotone: 8,141 of the 35,350 pairs
violate it. At α = 0.2, blurring raises it from 0.31 to 0.59, because bots that cannot tell
opponents apart cooperate with everyone. Yet below t\* = 0.28 equilibrium cooperation there is 0.
Opacity adds cooperation that defectors can exploit, and selection removes it.

**3. Why: DupocBot's window.** DupocBot cooperates iff its mass (the weight its signal puts on
bots it would cooperate with) is ≥ α. Cooperation needs it to:

- recognize itself: mass ≥ α facing DupocBot;
- not be exploited: mass < α facing OBot and DefectBot.

This window alone predicts the replicator outcome at **605 of the 606** non-trivial points. The
one exception is (t, α) = (0.5, 0.8). There, DupocBot no longer recognizes itself, but
TitForTatBot sustains cooperation on its own for one more grid step. Opacity breaks cooperation
in two ways:

- **Low caution (α = 0.2):** DupocBot starts to cooperate with OBot at t = 0.27, and is
  exploited.
- **High caution (α ≥ 0.4):** DupocBot stops cooperating with itself; it no longer recognizes a
  fellow cooperator.

At t = 0 all of DupocBot's masses equal 3/8, the share of the zoo it cooperates with at full
transparency. That is why t\*(α) is U-shaped in α, lowest at α = 0.4, just above 3/8.

## Caveats

- **Worst case.** The fully defecting component exists at every point with α > 0 (Theorem 2.9).
  "More transparency, more cooperation" holds for the best equilibrium and for the one the
  dynamics select, not for the worst.
- **All or nothing.** Every basin is 0 or 1, so the replicator evidence is a threshold, not a
  gradual rise. The gradual rise in Figure 1a comes from averaging over α.
- **α = 0 is trivial.** Every bot cooperates whatever its signal, so it is left out of all
  averages.
- **Scope.** The results hold for body8, floor side, behavioral family. The partial-transparency
  README reports syntactic thresholds within 0.07 of these.

## Figures and draft captions

### Figure 1: `fig1_phase_diagram`

> **More transparency sustains more cooperation at equilibrium (behavioral family).**
> (b) For each caution α and transparency t, blue marks the grid points whose game has a fully
> cooperative Nash equilibrium. All 1000 replicator starts reach it there. Gray marks the points
> where every Nash equilibrium, and every replicator end state, is fully defecting. Each row
> switches once, at the threshold t\*(α): cooperation never returns as transparency falls. At
> α = 0 every bot cooperates whatever its signal. (a) Mean over the six cautions α > 0. Blue:
> cooperation at equilibrium (the best Nash equilibrium and the replicator outcome coincide at
> every point). Gray: cooperation in the uniform population of the eight bots, before selection.

### Figure 2: `fig2_equilibrium_sets`

> **The equilibrium set grows with transparency, and the dynamics pick its best element.**
> For each caution α, the cooperation Pr[(C, C)] of every Nash component, drawn from the least t
> at which it exists. The fully defecting component (gray) exists everywhere. The fully
> cooperative one (blue) appears at t\*. The partially cooperative one (orange, 11/18) appears
> only at higher t. The gray band is the outcome of the replicator dynamics, the same for all
> 1000 starts. The thin line is the cooperation of the uniform population before selection,
> which does not rise with t.

### Figure 3: `fig3_dupoc_window`

> **Why opacity destroys cooperation.** DupocBot cooperates iff its mass, the weight its signal
> puts on bots it would cooperate with, is at least α. Black: its mass facing itself. Red: facing
> OBot (thick) and DefectBot (thin). Inside the blue window DupocBot recognizes itself and is not
> exploited. Horizontal bars: the grid's outcome at each α. The window predicts it at 605 of 606
> points. The exception is (0.5, 0.8), where TitForTatBot alone sustains cooperation. At low α,
> cooperation fails when OBot exploits DupocBot; at high α, when DupocBot fails to recognize
> itself. All masses meet at 3/8 at t = 0, which is why the threshold is lowest at α = 0.4.

## Design notes

- **Colors** come from the dataviz reference palette and were run through its validator.
  - Cooperation blue against partial-cooperation orange, and blue against exploiter red,
    separate under protan, deutan and tritan vision.
  - Defection is a neutral gray.
  - Every color-coded element also carries a direct label or a legend entry.
- **Size and type.** Figures are at most 6.0 in wide (the JAIR text block is about 6.3 in),
  set in Helvetica 7–7.5 pt, with fonts embedded in the PDFs (Type 42).
