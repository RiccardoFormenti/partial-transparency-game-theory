# Full-transparency results

This folder holds, for each zoo's game at full transparency, its Nash equilibria (computed by
`replication/full_transparency/nash.py`) and which of them a population reaches under the
replicator dynamics (computed by `replication/full_transparency/replicator.py`). This file
explains every entry of every result file. The Nash files are described first; the replicator
files are described under [Replicator dynamics](#replicator-dynamics).

## Layout

```
full_transparency/
  README.md                this file
  <zoo>/<side>/
    equilibria.json        the game and all its extreme equilibria and components
    lrsnash_input.txt      the game as given to the solver lrsnash
    lrsnash_output.txt     lrsnash's raw output, which equilibria.json is read from
    replicator.json        how many starts reach each Nash component, and where in it they end
    replicator_runs.csv    one row per start of the replicator dynamics
```

To compute or recompute, run from `true/`:

```bash
conda run -n py-random python -m replication.full_transparency.nash                 # body8, both sides
conda run -n py-random python -m replication.full_transparency.nash body8+trolls    # one zoo
conda run -n py-random python -m replication.full_transparency.nash all             # every zoo
conda run -n py-random python -m replication.full_transparency.replicator           # body8, floor side
```

For `nash`, add `--side floor` or `--side hinge` to compute one side only. A run overwrites the
three files of that zoo and side. The same data always gives the same files, except the timing
line in `lrsnash_output.txt`.

`replicator` takes the same zoo argument, but computes the floor side only unless given
`--side hinge`. Run `nash` first: `replicator.json` refers to the components of
`equilibria.json`, and the run stops if that file is missing or holds other equilibria. A run
overwrites the two replicator files of that zoo and side. The same data and the same numpy and
scipy versions always give the same files.

### Zoos (`<zoo>`)

The paper's zoos (Figure 2), defined in `replication/general/zoo.py`:

| zoo | bots |
|---|---|
| `nonprovers+dupoc` | `body8` without CupodBot (7 bots) |
| `body8` | CooperateBot, CupodBot, DBot, DefectBot, DupocBot, EBot, OBot, TitForTatBot |
| `body8+trolls` | `body8` + CupodTrollBot, DupocTrollBot |
| `body8+trolls+provers` | `body8+trolls` + CIMCIC, DIMDID |
| `body8+natives` | `body8` + MaxConfidenceBot, MinConfidenceBot. At full transparency both play exactly as DupocBot does, so their rows and columns are copies of DupocBot's. |

### Sides (`<side>`)

Some cells of the outcome table ("hinge cells") depend on whether a proof search succeeds.

- `floor`: every hinge search fails. This is the side of the paper's main results.
- `hinge`: every hinge search succeeds (Appendix D.2 and D.3.3).

## The game and what is computed

Two players each pick a bot. When the row player picks `bots[i]` and the column player picks
`bots[j]`, the row player gets `A[i][j]` and the column player gets `A[j][i]`. The game is
therefore the symmetric bimatrix game (A, Aᵀ).

- A **mixed strategy** is a probability vector over the bots. When the row player mixes with ξ
  and the column player with η, the row player expects ξᵀAη and the column player expects ηᵀAξ.
- A **Nash equilibrium** is a pair (ξ, η) in which each strategy is a best reply to the other:
  ξᵀAη = maxᵢ (Aη)ᵢ and ηᵀAξ = maxⱼ (Aξ)ⱼ. No pure strategy does better against the other
  player's mix than the mix itself.
- An equilibrium is **symmetric** when ξ = η: both players use the same mix. These are the
  equilibria that describe a single population playing against itself.
- The set of all equilibria is usually infinite. It is a finite union of convex polytopes of
  the form conv(X) × conv(Y), where X is a set of row strategies and Y a set of column
  strategies. Their vertices are the **extreme equilibria**. There are finitely many, and the
  files list all of them. Every equilibrium is a mix of extreme ones, so they describe the
  whole set.
- A **component** is a maximal connected piece of the set of equilibria. Two extreme
  equilibria are in the same component iff they are joined by a chain of extreme equilibria,
  each sharing its row strategy or its column strategy with the next.

## Conventions in `equilibria.json`

- **Exact numbers are strings:** `"2"`, `"-1"`, `"11/18"`. In Python, read them with
  `fractions.Fraction(s)`. Nothing is rounded.
- **Bot order:** every matrix and every vector is in the order of `bots`.
- **Strategies:** a mixed strategy is stored as `{bot: probability}`, listing only the bots
  with positive probability. Bots not listed have probability 0. The probabilities sum to 1.
- **Indices:** they start at 0.

## `equilibria.json`

### Top-level entries

| key | type | meaning |
|---|---|---|
| `zoo` | string | The zoo's name (see [Zoos](#zoos-zoo)). |
| `side` | `"floor"` or `"hinge"` | How hinge cells are resolved (see [Sides](#sides-side)). |
| `bots` | list of n strings | The zoo's bots, in the order every matrix and vector below uses. n is the number of bots. |
| `payoffs` | object | The Prisoner's Dilemma payoffs used to build `A`: `T` (temptation: you defect, the other cooperates) = 3, `R` (reward: both cooperate) = 2, `P` (punishment: both defect) = 0, `S` (sucker: you cooperate, the other defects) = −1. |
| `cells` | n × n list of strings | `cells[i][j]` is what happens when `bots[i]` meets `bots[j]` at full transparency. The first letter is `bots[i]`'s action and the second is `bots[j]`'s, each `C` (cooperate) or `D` (defect). `cells[j][i]` is always `cells[i][j]` reversed, and the diagonal (self-play) is always `CC` or `DD`. |
| `A` | n × n list of strings | `A[i][j]` is the payoff `bots[i]` receives when it meets `bots[j]`: `R`, `S`, `T` or `P` as `cells[i][j]` is `CC`, `CD`, `DC` or `DD`. `A` is not symmetric: `A[j][i]` is what `bots[j]` receives. |
| `n_equilibria` | integer | The number of extreme equilibria, which is the length of `equilibria`. It is not the number of equilibria, which is usually infinite. |
| `n_symmetric` | integer | How many extreme equilibria are symmetric (ξ = η). |
| `n_components` | integer | The number of components, which is the length of `components`. |
| `components` | list | One entry per component (see [below](#entries-of-components)). |
| `equilibria` | list | One entry per extreme equilibrium (see [below](#entries-of-equilibria)). |

### Entries of `equilibria`

Each entry is one extreme equilibrium (ξ, η). The list is sorted by (ξ, η), each read as a full
probability vector in `bots` order. The sort only makes the indices reproducible; the order has
no other meaning.

| key | type | meaning |
|---|---|---|
| `index` | integer | The entry's position in the list. `mirror` and the components' `equilibria` refer to entries by this number. |
| `row` | `{bot: probability}` | ξ, the row player's mixed strategy. |
| `col` | `{bot: probability}` | η, the column player's mixed strategy. |
| `row_payoff` | string | The row player's expected payoff, ξᵀAη = Σᵢⱼ ξᵢ ηⱼ A[i][j]. It equals the best payoff any single bot could get against η. |
| `col_payoff` | string | The column player's expected payoff, ηᵀAξ = Σᵢⱼ ξᵢ ηⱼ A[j][i]. |
| `symmetric` | boolean | `true` when ξ = η. |
| `mirror` | integer | The index of (η, ξ), the same equilibrium with the two players swapped. Because the game is symmetric, it is always an extreme equilibrium too. For a symmetric equilibrium, `mirror` is its own index. |
| `component` | integer | The `id` of the component it belongs to. |
| `cooperation` | string | Pr[(C, C)]: the probability that both bots cooperate when the row bot is drawn from ξ and the column bot from η, independently. It is Σᵢⱼ ξᵢ ηⱼ · [`cells[i][j]` = `CC`]. |

### Entries of `components`

| key | type | meaning |
|---|---|---|
| `id` | integer | 0 to `n_components` − 1, in the order the components first appear in `equilibria`. So component 0 always contains equilibrium 0. |
| `equilibria` | list of integers | The indices of its extreme equilibria. |
| `bots` | list of strings | Every bot that has positive probability in `row` or `col` of at least one of its extreme equilibria, in `bots` order. These are the bots used anywhere in the component, since every equilibrium in it mixes its extreme ones. |
| `n_symmetric` | integer | How many of its extreme equilibria are symmetric. The component may contain further symmetric equilibria that are not extreme. In component 0 of `body8/floor`, for example, (ξ, ξ) is an equilibrium for every mix ξ of its four extreme strategies. |
| `row_payoff` | `{"min", "max"}` | The smallest and largest row payoff over the whole component, not only over its extreme equilibria. |
| `cooperation` | `{"min", "max"}` | The smallest and largest Pr[(C, C)] over the whole component. A component with `max` = 1 contains a fully cooperative equilibrium. |

The ranges cover the whole component because payoffs and Pr[(C, C)] are bilinear in (ξ, η). The
component is a union of products conv(X) × conv(Y), and a bilinear function on such a product
takes its smallest and largest values at pairs of vertices, which are extreme equilibria.

The file stores no column-payoff range. The column payoff of an equilibrium equals the row
payoff of its `mirror`, so you can read it from there.

### Recovering a component's shape

Let X be the distinct `row` strategies among a component's extreme equilibria, and Y the
distinct `col` strategies. Every extreme equilibrium of the component is a pair in X × Y.

- **Full product:** if the component has |X| · |Y| extreme equilibria, it is exactly
  conv(X) × conv(Y). Any mix of the strategies in X against any mix of the strategies in Y is
  an equilibrium.
- **Union of products:** otherwise, the component is a union of several such products, one
  for each maximal sub-grid X′ × Y′ whose pairs are all extreme equilibria. The file does not
  list these sub-grids, but they can be computed from the extreme equilibria.

## `lrsnash_input.txt`

This is the game in the input format of lrsnash (lrslib):

```
n n
                    <- blank line
n lines: the row player's payoffs
                    <- blank line
n lines: the column player's payoffs
```

- **First matrix:** entry (i, j) is `A[i][j]` + shift, the row player's payoff when the row
  player picks `bots[i]` and the column player picks `bots[j]`.
- **Second matrix:** entry (i, j) is `A[j][i]` + shift, the column player's payoff for the same
  choices. This is the transpose of the first matrix.
- **The shift:** shift = 1 − (smallest entry of `A`), so that the smallest payoff is 1. It is 2
  whenever some cell gives S = −1, as in `body8`. Adding the same constant to every payoff
  leaves best replies, and so the equilibria, unchanged. It does shift every payoff in the
  lrsnash files by that constant.

To rerun the solver by hand: `conda run -n py-random lrsnash lrsnash_input.txt`.

## `lrsnash_output.txt`

### Comment lines (starting with `*`)

| line | meaning |
|---|---|
| `*lrsnash:lrslib_v.…` | The lrslib version. It appears at the start and again at the end. |
| `*Number of equilibria found: N` | The number of extreme equilibria. The code checks that it equals the number it reads, and `n_equilibria`. |
| `*Player 1: vertices=… bases=… pivots=…`, `*Player 2: …` | Statistics of lrsnash's vertex enumeration. Not used. |
| `*0.003u 0.002s …Kb …` | CPU time (user and system), memory and similar resource use. Not used, and it changes between runs. |

### Equilibrium lines

All other lines come in blocks separated by blank lines. Each line is a player number, n
probabilities in `bots` order, and a payoff:

- `1  p₁ … pₙ  v` is a row-player strategy ξ. Here v is the column player's payoff
  (+ shift) in every equilibrium of the block that uses ξ. It depends only on ξ: v = maxⱼ (Aξ)ⱼ + shift.
- `2  q₁ … qₙ  u` is a column-player strategy η. Here u is the row player's payoff (+ shift),
  u = maxᵢ (Aη)ᵢ + shift.

So each line ends with the other player's payoff. Within a block, every pairing of a `1`
line with a `2` line is one extreme equilibrium. The same strategy can appear in several blocks.

Each pairing is one entry of `equilibria` in `equilibria.json`, with `row` = ξ, `col` = η,
`row_payoff` = u − shift and `col_payoff` = v − shift. The JSON is sorted, so its order differs
from lrsnash's.

For example, in `body8/floor` (shift 2), this block

```
2  1/2  0  0  0  0  1/6  1/3  0  7/2
1  1/2  0  0  0  0  1/6  1/3  0  7/2
```

is equilibrium 12. Both players mix CooperateBot 1/2, EBot 1/6 and OBot 1/3, and both earn
7/2 − 2 = 3/2.

## What is guaranteed

The code checks the following before writing anything for a zoo and side. If any check fails,
the run stops with an error and writes none of that zoo and side's files.

- Every listed pair is a Nash equilibrium of `A`, checked in exact arithmetic.
- Every strategy is a probability vector: nonnegative, summing to 1.
- The number of equilibria read equals lrsnash's own count.
- No equilibrium is listed twice.
- Every pure equilibrium, found directly by checking all n² pairs of bots, is in the list.
- The mirror of every listed equilibrium is in the list.
- At least one equilibrium is symmetric, which Nash (1951) guarantees for symmetric games.

Components are found as described in [The game and what is computed](#the-game-and-what-is-computed);
see `replication/general/equilibria.py`. The original code
(`copy/app/src/pd_runner/egt/nash/classification.py`) groups two extreme equilibria whenever
their midpoint is an equilibrium. That can merge separate components, so its component counts
can be lower than the counts here.

## Worked example: `body8/floor`

**Counts:** `n_equilibria` = 21, `n_symmetric` = 7, `n_components` = 3. In the paper's zoo-ladder
table this is written as "3 (21)".

**Component 0: full cooperation.**
- It has 16 extreme equilibria and bots {CooperateBot, DupocBot, TitForTatBot}.
- `row_payoff` is 2 and `cooperation` is 1 throughout.
- Its extreme equilibria use four strategies, the same for both players. Over (CooperateBot,
  DupocBot, TitForTatBot) they are (0, 1, 0), (0, 1/3, 2/3), (2/3, 1/3, 0) and (2/3, 1/9, 2/9).
- 16 = 4 × 4, so the component is the full product: either player may use any mix of the four,
  independently.
- **Why these four.** Among these three bots everyone earns R = 2. Two outsiders could earn
  more, and they bound the mixes:
  - **DefectBot** earns 3 against CooperateBot and 0 against the other two, so CooperateBot's
    share must be ≤ 2/3.
  - **OBot** earns 2 against CooperateBot, 3 against TitForTatBot and 0 against DupocBot, so
    2·(CooperateBot) + 3·(TitForTatBot) ≤ 2.
  
  The four strategies are the vertices of the region these two inequalities cut out.

**Component 1: full defection.**
- It has 4 extreme equilibria and bots {DefectBot, OBot}.
- `row_payoff` and `cooperation` are both 0.
- Its strategies are DefectBot alone and (DefectBot 2/3, OBot 1/3). 4 = 2 × 2, so it is every
  pair of DefectBot/OBot mixes with OBot's share ≤ 1/3. Above 1/3, CooperateBot would do better:
  it earns 2 against OBot and −1 against DefectBot.

**Component 2: an isolated mixed equilibrium.**
- It consists of equilibrium 12 alone: both players mix CooperateBot 1/2, EBot 1/6, OBot 1/3,
  with payoff 3/2.
- Its cooperation is 11/18. The `CC` cells among these bots are (Coop, Coop), (Coop, OBot),
  (EBot, EBot) and (OBot, Coop), so
  Pr[(C, C)] = 1/2·1/2 + 1/2·1/3 + 1/6·1/6 + 1/3·1/2 = 11/18.

# Replicator dynamics

The Nash files list every equilibrium. The replicator files say which of them a population of
bots actually reaches, and from how many starting mixes. The code is
`replication/general/replicator.py`; its docstring also lists how it differs from the original
code (`copy/app/src/pd_runner/egt/replicator/`).

## The model and what is computed

- A **population** is a mix x of the bots: xᵢ is the share of `bots[i]`, xᵢ ≥ 0, Σ xᵢ = 1. Each
  member meets a random member, so a bot of type i expects (Ax)ᵢ and the population's average
  payoff is xᵀAx.
- The **replicator dynamics** let a type grow when it beats the average:
  ẋᵢ = xᵢ · gᵢ(x), with growth rate gᵢ(x) = (Ax)ᵢ − xᵀAx.
- **Starts:** `n_starts` mixes drawn independently and uniformly on the simplex (a Dirichlet(1)
  draw). Every bot is present at a start. Starts at a single bot are not used: a population of
  one bot never changes, since selection cannot bring back an absent bot.
- **Integration:** each start is followed up to time `horizon` (10⁵; payoffs are of order 1,
  so this is long). The code integrates the log-shares log xᵢ, whose derivative is gᵢ(x), so
  shares stay positive and sum to 1 exactly, however small they get.
- **Convergence:** a start has converged when, at time `horizon`/2 and at time `horizon`, (x, x)
  is a symmetric Nash equilibrium up to the tolerance ε = `tolerance` (10⁻⁶):
  - no bot's growth rate exceeds ε, so no bot beats the average;
  - every bot is **absent** (share < ε) or ties the best (growth rate ≥ −ε);
  - the absent bots and the tied bots are the same at both times, and no share moved by ε or
    more between the two times.

  A population that keeps cycling fails this test, even one that slows down near each bot it
  passes, since there the next bot grows.
- **Which equilibrium:** if a population that starts with every bot present converges, its
  limit x gives a symmetric Nash equilibrium (x, x) (the folk theorem of evolutionary game
  theory). So every converged start ends in exactly one **component** of `equilibria.json`.
  The code finds it exactly from the end state's absent and tied bots. These pick out a convex
  set of symmetric equilibria (x′, x′), all in one component. The code then checks that the end
  state lies within `max_distance` of that set (see `replication/general/replicator.py` for the
  argument).
- **Basin of a component:** the share of starts that converge to it. It estimates the share of
  all starting mixes (by volume) from which the population reaches that component. Starts that
  have not converged are counted separately and never assigned to a component.

Many components are continua of equilibria, so starts that reach the same component end at
different mixes, and some bots of the component may be absent at some end states. Grouping end
states by the bots present would split one component into several groups. That is why the
results are grouped by component, with the mixes inside each component listed separately.

## Conventions in `replicator.json` and `replicator_runs.csv`

- **Floats:** shares, payoffs and probabilities are floating point, not exact. `replicator.json`
  rounds them to 9 decimals. `replicator_runs.csv` keeps every digit.
- **End state:** the population's mix at time `horizon`.
- **Present:** a bot is present at an end state when its share is at least `tolerance`.
  A bot whose share is below that is absent: in practice its share is usually far smaller,
  e.g. 10⁻¹⁰⁰.
- **Component ids** are those of `equilibria.json` in the same folder.
- **95% intervals** are Wilson score intervals for a proportion, from k of n independent
  starts. When k = 0, the upper end is about 3.8/n.

## `replicator.json`

### Top-level entries

| key | type | meaning |
|---|---|---|
| `zoo`, `side`, `bots`, `payoffs`, `A` | | As in `equilibria.json`. |
| `settings` | object | The method's settings (see [below](#entries-of-settings)). |
| `n_starts` | integer | The number of starts. |
| `n_converged` | integer | How many of them converged. |
| `components` | list | One entry per component of `equilibria.json`, in `id` order, including components that no start reaches (see [below](#entries-of-components-1)). |
| `unconverged` | object | The starts that did not converge (see [below](#entries-of-unconverged)). |

### Entries of `settings`

| key | meaning |
|---|---|
| `n_starts` | The number of starts. |
| `seed` | The seed of numpy's random generator (`numpy.random.default_rng`) that draws the starts. |
| `horizon` | How long each start is integrated. Convergence is tested at `horizon`/2 and `horizon`. |
| `tolerance` | ε of the convergence test, and the share below which a bot counts as absent. |
| `max_distance` | How far (largest difference in any bot's share) a converged end state may lie from a symmetric equilibrium of its component. If any end state lies farther, the run stops with an error. |
| `integrator` | The ODE solver (scipy's `solve_ivp` with LSODA) and the variables it integrates. |
| `rtol`, `atol` | The solver's relative and absolute error tolerances, per log-share. |

### Entries of `components`

Every component has these entries:

| key | type | meaning |
|---|---|---|
| `id` | integer | The component's `id` in `equilibria.json`. |
| `bots` | list of strings | The component's `bots` in `equilibria.json`: every bot played in one of its equilibria. |
| `n_starts` | integer | How many starts converge to it. |
| `basin` | float | `n_starts` divided by the total number of starts. |
| `basin_ci95` | [low, high] | The 95% interval for the basin. |

A component that at least one start reaches also has these:

| key | type | meaning |
|---|---|---|
| `shares` | `{bot: {"min", "max"}}` | The smallest and largest share of each bot over the end states in this component. Bots that are absent from every one of these end states are not listed. |
| `supports` | list of `{"bots", "n_starts"}` | The distinct sets of present bots among these end states, and how many end states have each set, most frequent first. |
| `payoff` | `{"min", "max"}` | The smallest and largest average payoff xᵀAx over these end states. |
| `cooperation` | `{"min", "max"}` | The smallest and largest Pr[(C, C)] over these end states: the probability that two members drawn independently from x both cooperate, Σᵢⱼ xᵢ xⱼ · [`cells[i][j]` = `CC`]. |
| `max_distance` | float | The largest distance from one of these end states to a symmetric equilibrium of the component. It is at most `settings.max_distance`. |

### Entries of `unconverged`

| key | type | meaning |
|---|---|---|
| `n_starts` | integer | How many starts did not converge by `horizon`. |
| `share` | float | `n_starts` divided by the total number of starts. |
| `share_ci95` | [low, high] | Its 95% interval. |
| `runs` | list of integers | Their row numbers (`run`) in `replicator_runs.csv`. |

## `replicator_runs.csv`

One row per start, in the order they were drawn.

| column | meaning |
|---|---|
| `run` | The start's number, from 0. |
| `converged` | `True` or `False`. |
| `component` | The `id` of the component it converges to; empty when it did not converge. |
| `distance` | The end state's distance to a symmetric equilibrium of that component; empty when it did not converge. |
| `payoff` | The average payoff xᵀAx at the end state. |
| `cooperation` | Pr[(C, C)] at the end state, as in `components`. |
| `start:<bot>` | The bot's share at the start, one column per bot in `bots` order. |
| `end:<bot>` | The bot's share at the end state. |

## What is guaranteed

The code checks the following before writing anything for a zoo and side. If any check fails,
the run stops with an error and writes neither replicator file.

- `equilibria.json` exists and holds the same bots and equilibria the run computes, so the
  component ids agree.
- Every start has every bot present, and the solver reports success for every start.
- Every converged end state matches the faces of exactly one component, and lies within
  `max_distance` of a symmetric equilibrium of that component.

`true/checks/check_replicator.py` also checks the code against the original's and against
textbook games, and checks that every saved `replicator.json` agrees with its
`equilibria.json`.

## Worked example: `body8/floor`

**Counts:** 1000 starts, all 1000 converged.

**Component 0 (full cooperation) is reached from every start:** basin 1, 95% interval
[0.996, 1].
- Every end state has payoff 2 and Pr[(C, C)] = 1.
- The end states form a continuum. Over them, CooperateBot's share ranges from 0 to 0.658,
  DupocBot's from 0.170 to 1, and TitForTatBot's from 0 to 0.628. All lie in the region
  described in the Nash example above: CooperateBot ≤ 2/3 and 2·CooperateBot + 3·TitForTatBot ≤ 2.
- Their supports are {CooperateBot, DupocBot, TitForTatBot} in 904 starts, {DupocBot,
  TitForTatBot} in 46, {DupocBot} in 40 and {CooperateBot, DupocBot} in 10. At every end state
  the three bots tie, so selection no longer changes their shares. A bot whose share fell
  below 10⁻⁶ on the way stays absent, although nothing outcompetes it at the end.
- The other five bots have share 0 to machine precision at every end state.

**Components 1 and 2 are reached from no start.** The 95% interval of each basin is
[0, 0.0038].
- Component 1 (full defection). At every one of its equilibria, a small DupocBot share grows.
  Against DefectBot and OBot, DupocBot earns 0, as they do against each other and against
  DupocBot, and DupocBot earns 2 against itself. So DupocBot beats the average.
- Component 2 (the isolated mix of CooperateBot, EBot and OBot). Among its own three bots it
  attracts: the population spirals into it. But DefectBot and DupocBot earn exactly its
  payoff 3/2 there, so whether it is stable depends on effects beyond the first order. No
  start ends there.

The original code, with its own 200 starts, reports 11 "attractors" here:
- one per bot, because it also starts at each single-bot population, which never changes;
- three more sets of present bots.

Four of the 11 are parts of component 0: {DupocBot} and the three others. The other seven are
reached from no start that has every bot present.
