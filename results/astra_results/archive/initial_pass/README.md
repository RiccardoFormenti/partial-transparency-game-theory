# Behavioral transparency and cooperation

The saved behavioral-family results support a positive, precisely scoped answer:
**at every tested fixed caution level above zero, more transparency eventually
enables fully cooperative Nash equilibria, and all 1,000 sampled replicator
trajectories select full cooperation from that point onward.** There are no
downward steps in maximum Nash cooperation or selected cooperation on the grid.
Full-defection equilibria continue to exist at every positive caution level,
including full transparency. Thus the result is about attainable cooperation
and evolutionary selection, rather than cooperation in every equilibrium.

## Start with these figures

All figures are provided as vector PDF, editable SVG, and 300-dpi PNG in `figures/`.
Their PDFs were rendered with Poppler and visually reviewed. The file prefixes
give the recommended reading order.

1. **`01_transparency_and_cooperation`**: the principal result. Side-by-side strips
   compare the greatest attainable Nash cooperation with the observed basin of
   full cooperation. They agree at all 707 points. All seven caution levels are
   included, including the degenerate alpha = 0 and strict alpha = 1 endpoints.
2. **`02_equilibrium_landscape`**: the qualification that strengthens the
   interpretation. The complete set of Nash cooperation levels is shown at each
   positive caution level, alongside the selected level. Defection survives as
   a Nash outcome, but none of the sampled populations select it above the
   cooperative onset. Intermediate cooperation also exists at some points.
3. **`03_transparency_thresholds`**: the required transparency is not monotone
   in caution. Of the tested positive caution levels, alpha = 0.4 requires the
   least transparency. Its first cooperative point is t = 0.01, approximately
   0.03 bits of mutual information about the opponent. The plot does not
   interpolate across the unevenly spaced caution values.
4. **`04_cooperation_before_and_after_selection`**: the effect is not merely a
   higher rate of cooperation among the unselected programs. For example, at
   alpha = 0.2, average initial cooperation is 57.65% at t = 0 and 32.84% at t = 1,
   while cooperation after selection moves from 0% to 100%. The gray bands
   describe population heterogeneity, not statistical uncertainty.

Use Figures 1 and 3 for a compact main-text presentation, with Figures 2 and 4 as
interpretive support. `paper_figures.tex` contains captions and a paragraph ready
to adapt for Section 5.2. The attached draft's Section 5.1 and Appendix F.1
guided the terminology and the distinction between equilibrium enumeration and
selection. Draft placeholders were treated as document content, not task instructions.

## Findings

| Caution alpha | Last sampled point with only defecting Nash outcomes | First sampled point with a cooperative Nash outcome and 1,000/1,000 cooperative runs |
|---:|---:|---:|
| 0 | None | 0.00 |
| 0.2 | 0.27 | 0.28 |
| 0.4 | 0.00 | 0.01 |
| 0.5 | 0.10 | 0.11 |
| 0.6 | 0.23 | 0.24 |
| 0.8 | 0.49 | 0.50 |
| 1 | 0.99 | 1.00 |

At and above the first cooperative grid point, maximum Nash cooperation and
observed selected cooperation are both 1. Below it they are both 0. The minimum
Nash cooperation is 0 everywhere for alpha > 0. At alpha = 0 all lifted programs
cooperate unconditionally, so both minimum and maximum Nash cooperation equal 1
at every transparency level. There are 493 cooperative grid points and 214
defecting grid points, representing 31 cooperative and 31 defecting distinct
games. These counts describe this design; they are not estimates under a
distribution over caution and transparency.

The six positive caution values give 600 adjacent transparency comparisons, and
including alpha = 0 gives 700. There are zero decreases in maximum Nash or
selected cooperation. All five interior caution settings tested here cooperate
at every grid point with t >= 0.50. At alpha = 1 the full-support softmax assigns
positive probability to every hypothesis for every finite positive temperature:
only the unconditional cooperator can satisfy that strict threshold, and
cooperative equilibrium returns at the point-mass endpoint t = 1.

At full transparency the Nash cooperation levels are 0, 11/18, and 1, and all
sampled runs select 1. All 93 connected equilibrium components encountered in
these 62 games have a constant mutual-cooperation value. Consequently, plotting
one level per component covers the entire Nash outcome set, including continua;
it does not merely sample the extreme equilibria. Maximum cooperation over
symmetric equilibria agrees with the maximum over all equilibria at all points,
so the comparison to one-population replicator dynamics is consistent.

## Definitions and uncertainty

- **Scope:** the saved `body8/floor/behavioral` library and the fixed Prisoner's
  Dilemma payoffs T = 3, R = 2, P = 0, S = -1. No syntactic-family results enter
  the analysis.
- **Transparency:** t = I(B; S) / log2(8), using the uniform prior over the eight
  opponent programs, as in Appendix F.1. This is a fixed channel calibration,
  not mutual information recomputed under each evolving population.
- **Cooperation:** Pr[(C, C)], not the frequency of an individual C action or
  the population share of bots with a particular name. For a population x,
  cooperation is x^T C x, where C_ij = 1 exactly for a CC tournament cell.
- **Nash maximum:** max over all Nash equilibria of xi^T C eta. Nash enumeration
  is exact rational arithmetic; it supplies possibilities, not a probability
  distribution over equilibria. No arbitrary average over extreme equilibria
  or components is used.
- **Replicator selection:** fraction of all 1,000 starts that converge to full
  cooperation. Mean endpoint cooperation is identical here because all stored
  endpoints are either fully cooperative or fully defecting. The converged
  population mixes themselves need not be identical.
- **Sampling:** starts are Dirichlet(1), uniform over the eight-type simplex,
  seed 20260514. The same 1,000 starts are reused in every game. Identical games
  are solved only once and reused at multiple grid points: 707 parameter points
  represent 62 games and 62,000 stored trajectories, not 707,000 independently
  simulated trajectories. The numerical audit does not rerun the ODE solver.
- **Basin uncertainty:** a per-game, pointwise 95% Wilson interval is
  [0.99617324, 1] for 1,000/1,000 cooperative outcomes and [0, 0.00382676] for
  0/1,000. These are not simultaneous intervals over the sweep, and they do not
  quantify numerical integration error. No inference pools repeated games or
  treats repeated initial states as independent across transparency levels.
  Observing every start cooperate is not a proof of a global basin of measure 1.
- **Resolution:** t is sampled at increments of 0.01. The table provides the
  last-D / first-C pair, not an exactly located continuous threshold. No
  unobserved parameter values are imputed. Steps in Figures 2 and 4 guide the eye
  between samples; the bracket in Figure 2 makes the transition resolution
  explicit. In Figure 1 each colored stroke is one grid point. An endpoint at
  alpha = 1 is shown separately in Figures 2 and 4.
- **Calibration:** the maximum measured-versus-target t discrepancy is
  2.27512e-5. Both target and measured values are retained in the CSV outputs.
  The right axis of Figure 3 is the nominal conversion I = 3t; the 0.03-bit
  annotation rounds the measured information at the sampled onset.
- **Generalization:** these results establish a monotone threshold pattern on
  the tested grid, not a theorem for every continuous transparency value, every
  caution setting, other signal families, larger libraries, different payoffs,
  boundary initial populations, or other selection dynamics. Alpha = 0 is
  displayed explicitly and is not used to argue for an effect of transparency.

## Reproduction

From the repository root:

```bash
conda run -n py-random python true/results/astra_results/analyze_behavioral.py
```

This reads the original results without changing them. It rebuilds all four
figures and the six CSVs and writes `audit.json`. The existing conda environment
already has the required packages; exact versions are in `requirements.txt`
and the audit. The script locates its input and output directories relative to
its own file, so it can also run from another working directory.

For an independent visual check of a PDF (the output is kept in this folder):

```bash
pdftoppm -singlefile -scale-to 1700 -png \
  true/results/astra_results/figures/01_transparency_and_cooperation.pdf \
  true/results/astra_results/qa/01_transparency_and_cooperation
```

`tables/` contains:

- `grid_metrics.csv`: 707 parameter points, their game IDs, equilibrium extrema,
  selected cooperation, basin intervals, and initial cooperation summaries.
- `game_metrics.csv`: the same metrics once per distinct game.
- `nash_components.csv`: all 93 components, exact cooperation fractions,
  extreme-equilibrium counts, participating bots, and observed basin counts.
- `thresholds.csv`: the sampled onsets, preceding points, associated game IDs,
  measured information, and monotonicity checks.
- `final_composition_by_game.csv`: the mean final share of every bot per game.
- `source_manifest.csv`: SHA-256 hashes of all 311 numerical input files.

## Validation performed

The script reparses each raw lrsNash output and checks the complete saved
enumeration against it. It revalidates all 1,027 extreme equilibria in exact
arithmetic, including best responses, pure equilibria, mirrors, component
membership, and component cooperation ranges. It verifies solver inputs,
payoff matrices, grid-to-game mappings, channel calibration, and the threshold
action rule at all 707 points.

For all 62,000 trajectories it checks the shared initial populations,
normalization, convergence flags, component membership counts, reported
distances, final cooperation, final payoff, and absence of a profitable
endpoint deviation. The largest cooperation recomputation discrepancy is
2.11e-15; the largest payoff discrepancy is 3.33e-15. All saved runs converge.
The largest reported distance to a symmetric equilibrium is 2.385e-6, below
the stored 1e-4 assignment tolerance. The largest recomputed profitable
endpoint deviation is numerical noise, 5.56e-15. These checks corroborate the
saved endpoints; the full time trajectories and half-horizon convergence
states are not stored in these CSVs and were not independently reintegrated.

No original numerical results were modified. All analysis code, figures,
tables, draft extraction, rendering checks, and caches live here. The directory
is excluded by `true/results/astra_results/` in the repository `.gitignore`.
