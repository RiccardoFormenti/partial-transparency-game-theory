# Full-transparency Nash results

This folder holds the Nash equilibria of each zoo's game at full transparency, as computed by
`replication/full_transparency/nash.py`. This file explains every entry of every result file.

## Layout

```
full_transparency/
  README.md                this file
  <zoo>/<side>/
    equilibria.json        the game and all its extreme equilibria and components
    lrsnash_input.txt      the game as given to the solver lrsnash
    lrsnash_output.txt     lrsnash's raw output, which equilibria.json is read from
```

To compute or recompute, run from `true/`:

```bash
conda run -n py-random python -m replication.full_transparency.nash                 # body8, both sides
conda run -n py-random python -m replication.full_transparency.nash body8+trolls    # one zoo
conda run -n py-random python -m replication.full_transparency.nash all             # every zoo
```

Add `--side floor` or `--side hinge` to compute one side only. A run overwrites the three files
of that zoo and side. The same data always gives the same files, except the timing line in
`lrsnash_output.txt`.

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
