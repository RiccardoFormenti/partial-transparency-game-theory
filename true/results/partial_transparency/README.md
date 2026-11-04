# Partial-transparency results

This folder holds, for the eight-bot zoo `body8` on the floor side, the game the lifted bots
play at each point (t, α) of the grid, its Nash equilibria, and which of them a population
reaches under the replicator dynamics. It is computed by
`replication/partial_transparency/grid.py`. This file explains how each grid point's game is
built and every entry of `grid.json`. The game folders hold the same files as
`results/full_transparency/`, whose README describes them.

## Layout

```
partial_transparency/
  README.md                    this file
  body8/floor/<family>/
    grid.json                  the channel at each t, the tournament at each (t, α), its game
    games/<game>/
      equilibria.json          \
      lrsnash_input.txt         |  the game's Nash equilibria and replicator basins, in the
      lrsnash_output.txt        |  format of results/full_transparency/<zoo>/<side>/,
      replicator.json           |  with three entries added (see below)
      replicator_runs.csv      /
```

`<family>` is `behavioral` or `syntactic`, the two ways a signal blurs (see
[The channel](#the-channel)). `<game>` is `g00`, `g01`, …: grid points whose tournaments have the
same cells play the same game, which is solved once.

To compute or recompute, run from `true/`:

```bash
conda run -n py-random python -m replication.partial_transparency.grid                       # both families
conda run -n py-random python -m replication.partial_transparency.grid --family behavioral   # one family
```

Add `--t-step <step>` for another t step than 0.01 (it must divide 1), and `--horizon <time>`
for another first horizon of the replicator dynamics than 10⁵ (see
[The tournament and its game](#the-tournament-and-its-game)). Both families take about six
minutes. A run overwrites `grid.json` and every game folder of that
family. If an earlier run left game folders that are not part of the new grid, it warns
and does not delete them. The same data and the same numpy and scipy versions always give the
same files, except the timing line in `lrsnash_output.txt`.

`true/checks/check_partial_transparency.py` checks the saved files (see
[What is guaranteed](#what-is-guaranteed)).

### Other grids

`--alphas <α> ...` runs other cautions, `--starts <n>` another number of replicator starts per
game (the first n of the same 1000 seeded draws), and `--subset <name>` saves to
`partial_transparency/<name>/body8/floor/<family>/`, leaving the default grid in place. The files
are the same as here. The check script checks only the default grid.

- **`alpha_0.5-1/`**: α ∈ {0.5, 0.6, 0.7, 0.8, 0.9, 1}, the same t grid, 100 starts per game:

  ```bash
  conda run -n py-random python -m replication.partial_transparency.grid \
      --alphas 0.5 0.6 0.7 0.8 0.9 1 --starts 100 --subset alpha_0.5-1
  ```

## The grid

- **Transparency** t runs from 1 to 0 in steps of 0.01: 101 values. Each is rounded to 10
  decimals, so 0.3 is stored as `0.3`, not `0.30000000000000004`.
- **Caution** α takes the original's values: α ∈ {0, 0.2, 0.4, 0.5, 0.6, 0.8, 1}.

That makes 707 grid points per family. The original's grid
(`copy/app/src/pd_runner/egt/pipeline.py`: `linear_ts(6)` and `DEFAULT_ALPHAS`) has the same α
and t ∈ {1, 0.8, 0.6, 0.4, 0.2, 0}, a subset of the t values here. Any t step that divides 0.2
keeps that subset.

At α = 0 every bot cooperates whatever its signal, since its mass is never below 0. That column
is the same all-cooperating game at every t. It is kept because it is part of the grid.

## The channel

A signal is a probability distribution over the zoo: how likely each bot is to be the
opponent. The channel gives the signal for every true opponent B:

    σ_T(B)[h] ∝ exp(−d(B, h) / T)

Here d is a distance between bots and T ≥ 0 a temperature. The family fixes d:

- **behavioral:** d(B, h) is the number of zoo members that B and h play differently against
  at full transparency.
- **syntactic:** d(B, h) is 10 × the tree edit distance between the two bots' Lean syntax
  trees, divided by the size of the larger tree (`replication/partial_transparency/syntax.py`).

**Transparency** is the mutual information between the true opponent, drawn uniformly from the
zoo, and its signal, divided by log₂ n. It is 1 when the signal always names the opponent and
0 when the signal says nothing about it.

**From t to T.** Transparency decreases as T grows. So for 0 < t < 1 the temperature is found by
bisection on log T over [10⁻⁶, 10⁴], until the bracket's ends are within a factor 1 + 10⁻⁴.
The channel at that T is the channel of t. On body8 the transparency it reaches is within
3.1 × 10⁻⁵ of t.

### The endpoints

The two ends of the dial are Definition 32's:

| t | signal | T | meaning |
|---|---|---|---|
| 1 | the point mass on the true opponent | 0 | Each bot sees its opponent exactly. The tournament is the full-transparency table, and its game is the one in `results/full_transparency/body8/floor/`. |
| 0 | uniform over the zoo | ∞ | Every opponent sends the same signal, so each bot plays one action against everyone: C if it cooperates with a share ≥ α of the zoo at full transparency, D otherwise. This is the opaque Prisoner's Dilemma. |

**The original code's endpoints** (`copy/app/src/pd_runner/tau/signal.py`, `tau/channels.py`)
are different:

- **At t = 0 it uses T = 10⁴, not the uniform signal.** Its reason is to keep "the α knife edge
  observable". On body8 the signal is then within 9 × 10⁻⁵ of 1/8, and its transparency is
  about 10⁻⁸. The difference shows when α equals a share k/8 that some bot cooperates with. At
  the uniform signal that bot plays C against everyone. At T = 10⁴ its mass lies within 10⁻⁴ of
  k/8, above or below depending on the opponent, so it plays C against some opponents and D
  against others. That split is an artifact of the finite temperature.
- **At t = 1 in the syntactic family it uses T = 10⁻⁶, not 0.** That softmax keeps syntactic
  twins blurred together even at t = 1. The behavioral family uses the point mass there, as here.

On body8 neither difference changes any tournament of the grid. The shares body8's bots
cooperate with are 0, 1/8, 3/8, 5/8, 3/4 and 1, and none is a grid α other than 0 and 1, where
there is no split. body8 has no syntactic twins, and its smallest syntactic distance is 3, so
T = 10⁻⁶ gives weights e^(−3 × 10⁶) = 0 off the true opponent.

### Twins

Twins are bots at distance 0. They receive the same signal at every T > 0, so no T > 0 tells
them apart and none reaches transparency 1.

The most any T > 0 reaches is the **ceiling**: the transparency of the limit T → 0, where each
signal is uniform over the true opponent's twins. A grid t above the ceiling has no
temperature. It gets the point mass, whose transparency is 1, not t.

The run flags both cases. It prints a warning, and `grid.json` records them in `twins`,
`ceiling` and `unreached`. **body8 has no twins in either family**: its ceiling is 1 and every t
is reached. On the zoo `body8+natives`, DupocBot, MaxConfidenceBot and MinConfidenceBot are
twins in both families, with ceiling 0.857. The check script confirms the flag fires there.

## The tournament and its game

At (t, α) every ordered pair of bots meets, self-play included.

1. When bot i meets bot j, it receives the signal `channel[j]` for j.
2. It tests every hypothesis h in the signal. Its test at h is its own action against h at
   full transparency.
3. Its **mass** is the total weight of the hypotheses it would cooperate with. Every body8 bot
   aggregates this way, by sum.
4. It plays C iff the mass is ≥ α. This is decided on the complement, as explained
   [below](#comparing-the-mass-with-α): its **shortfall**, 1 − mass, the total weight of the
   hypotheses it would defect on, must be ≤ 1 − α.

The tournament's cells define a game exactly as the outcome table does at full transparency.
`A[i][j]` is R = 2, S = −1, T = 3 or P = 0 as `cells[i][j]` is `CC`, `CD`, `DC` or `DD`, and the
game is (A, Aᵀ). Each game is solved as at full transparency:

- every extreme Nash equilibrium and component, by lrsnash, in exact arithmetic;
- the component each of 1000 starts of the replicator dynamics reaches.

The starts are the same 1000 points (seed 20260514) in every game.

**Horizon.** The replicator dynamics run to time 10⁵. If some start has not converged by then,
the whole game is integrated again, 10 times longer, until every start converges or the time
reaches 10⁹. Each game's `replicator.json` records the horizon it used (`settings.horizon`), and
so does `grid.json`.

Some games need it because of how a share dies out near a monoculture. Take a monoculture of a
type R and a type M that earns as much as R against R, so it is neutral there, but loses to R
when it meets itself. Its share ε then shrinks like ε′ = −c·ε², so ε ≈ 1/(c·t). That is
algebraic, not exponential, decay. Game g11 of the behavioral family, at (t, α) = (0.5, 0.8),
is the extreme case.
There M is DupocBot, which defects against itself, and R is TitForTatBot, so c = 2. At
t = 10⁵ DupocBot's share is still 5 × 10⁻⁶, above the 10⁻⁶ that counts as absent, so no start
had converged. At 10⁷ all have.

### Comparing the mass with α

A bot plays C iff its shortfall is ≤ (1 − α)(1 + 10⁻¹²). Mathematically this is the rule
"mass ≥ α"; the difference is numerical, and it shows at α = 1.

- **Why the complement.** At α = 1 and t < 1, a softmax gives every bot some weight. So any bot
  that would defect on some bot must defect, and only CooperateBot, which cooperates with
  everyone, cooperates. Its mass, 1 minus the weight it would defect on, rounds to 1 once that
  weight is below about 10⁻¹⁶. The shortfall is that weight itself, which floats hold exactly.
- **Why a relative tolerance.** A shortfall that is 1 − α in exact arithmetic can land a few ulps
  above it after a floating-point sum: under the uniform signal it is k/n. The tolerance is
  relative to 1 − α, so at α = 1 only a shortfall of exactly 0 cooperates.

The original compares the mass with α − 10⁻¹² (`copy/app/src/pd_runner/tau/play.py`). The
two rules differ only where the shortfall is positive but within about 10⁻¹² of 1 − α. On the
original's grid that never happens (`true/checks/check_sweep.py`). On the fine t grid it
happens in the behavioral family at α = 1 and t = 0.99 and 0.98. There, when DBot meets OBot
(and, at t = 0.99, DefectBot), the signal it receives puts only 10⁻¹⁵ to 10⁻¹³ on the bots it
would defect on. Under the original's rule DBot cooperates against them, and those two grid
points get games of their own.

## Conventions in `grid.json`

- **Bot order:** every matrix is indexed in the order of `bots`. Row i is `bots[i]`.
- **Floats:** t is rounded to 10 decimals (see [The grid](#the-grid)). Every other number is
  stored in full.
- **Grid order:** `channels` follows `ts`. `points` runs over `ts` in the outer loop and `alphas`
  in the inner one.

## `grid.json`

### Top-level entries

| key | type | meaning |
|---|---|---|
| `zoo` | `"body8"` | The zoo. |
| `side` | `"floor"` | How hinge cells are resolved (see `results/full_transparency/README.md`). |
| `family` | `"behavioral"` or `"syntactic"` | The distance the channel blurs over. |
| `bots` | list of n strings | The zoo's bots, in the order of every matrix. n = 8. |
| `ts` | list of numbers | The grid's transparencies. |
| `alphas` | list of numbers | The grid's cautions. |
| `settings` | object | See [below](#entries-of-settings). |
| `distances` | n × n numbers | `distances[i][j]` = d(`bots[i]`, `bots[j]`). It is symmetric with a zero diagonal. |
| `twins` | list of lists of strings | The groups of two or more bots at distance 0 from one another. Empty when there are none. **A non-empty list is the twin flag.** |
| `ceiling` | number | The most transparency any T > 0 reaches. It is 1 iff `twins` is empty. |
| `unreached` | list of numbers | The grid t whose channel's transparency differs from t by more than `settings.calibration`. **A non-empty list is the second flag.** |
| `n_games` | integer | The number of distinct games, which is the length of `games`. |
| `channels` | list | One entry per t (see [below](#entries-of-channels)). |
| `points` | list | One entry per (t, α) (see [below](#entries-of-points)). |
| `games` | list | One entry per game (see [below](#entries-of-games)). |

### Entries of `settings`

| key | meaning |
|---|---|
| `min_temperature`, `max_temperature` | The bisection's bracket on T: 10⁻⁶ and 10⁴. |
| `bisection_tolerance` | The bisection stops when the bracket's high end is within a factor 1 + this (10⁻⁴) of the low end. |
| `calibration` | The largest gap between a channel's transparency and its t for the channel to count as reaching t (10⁻³). |
| `tie_tolerance` | A bot plays C iff its shortfall is ≤ (1 − α)(1 + this), with this = 10⁻¹². |
| `horizon` | The first time the replicator dynamics are integrated to (10⁵). |
| `max_horizon` | The longest they are integrated to (10⁹). |

### Entries of `channels`

| key | type | meaning |
|---|---|---|
| `t` | number | The transparency asked for. |
| `signal` | `"point mass"`, `"softmax"` or `"uniform"` | The kind of channel: the point mass at t = 1 (or above the ceiling), the softmax for 0 < t < 1, uniform at t = 0. |
| `temperature` | number or `null` | T. It is 0 for the point mass and `null` for the uniform signal, whose T is ∞. |
| `transparency` | number | The channel's transparency, as measured. |
| `reached` | boolean | `true` when \|`transparency` − `t`\| ≤ `settings.calibration`. |
| `channel` | n × n numbers | `channel[i][j]` = σ_T(`bots[i]`)[`bots[j]`]: the weight the signal gives `bots[j]` when the true opponent is `bots[i]`. Each row sums to 1. |
| `mass` | n × n numbers | `mass[i][j]` = what `bots[i]` compares with α when it meets `bots[j]`: the sum of `channel[j][h]` over the hypotheses h it cooperates with at full transparency. |
| `shortfall` | n × n numbers | `shortfall[i][j]` = 1 − `mass[i][j]`, computed as the sum of `channel[j][h]` over the hypotheses h it defects on. This is what decides `bots[i]`'s action (see [Comparing the mass with α](#comparing-the-mass-with-α)). |

### Entries of `points`

| key | type | meaning |
|---|---|---|
| `t`, `alpha` | numbers | The grid point. |
| `game` | string | The id of the game played here, the folder `games/<game>/`. |
| `mutual_cooperation` | number | The share of the n² ordered pairs, self-play included, whose cell is `CC`. |
| `cells` | n × n strings | `cells[i][j]` = what happens when `bots[i]` meets `bots[j]`: `bots[i]`'s action, then `bots[j]`'s. The first letter is C iff `shortfall[i][j]` ≤ (1 − α)(1 + `tie_tolerance`), and the second iff `shortfall[j][i]` is (with `shortfall` from this t's channel). So `cells[j][i]` is `cells[i][j]` reversed, and the diagonal is `CC` or `DD`. |

### Entries of `games`

| key | type | meaning |
|---|---|---|
| `id` | string | `g00`, `g01`, … in the order the games first appear in `points`. |
| `horizon` | number | The time its replicator dynamics were integrated to: 10⁵, or longer when some start had not converged by then. |
| `points` | list of `{"t", "alpha"}` | Every grid point that plays this game. Two points play the same game iff their `cells` are equal. |

## `games/<game>/`

The five files are those of `results/full_transparency/<zoo>/<side>/`, written by the same code
(`replication/full_transparency/nash.py` and `replicator.py`), and their README describes every
entry. In them, `cells` and `A` are this game's: the tournament's cells at the game's grid
points, not the full-transparency table.

`equilibria.json` and `replicator.json` each have three entries added after `zoo` and `side`:

| key | type | meaning |
|---|---|---|
| `family` | string | As in `grid.json`. |
| `game` | string | The game's id, its folder's name. |
| `points` | list of `{"t", "alpha"}` | The grid points that play this game, as in `grid.json`'s `games`. |

## What is guaranteed

Before writing a game's files, the run checks everything listed under "What is guaranteed" in
`results/full_transparency/README.md` (every equilibrium exact and complete, every converged
start matched to a component).

`true/checks/check_partial_transparency.py` also checks, for each family:

- **Grid:** t runs from 1 to 0 in equal steps, rounded to 10 decimals, and holds the original's
  t values. α is the original's.
- **t = 1:** the channel is the point mass and the tournament is the full-transparency table.
  Its game's `equilibria.json` and `replicator.json` equal those of
  `results/full_transparency/body8/floor/`, apart from the three added entries. Its
  `lrsnash_input.txt` and `replicator_runs.csv` are identical.
- **t = 0:** the channel is exactly uniform, of transparency 0. Each bot plays C against everyone
  iff it cooperates with a share ≥ α of the zoo.
- **Consistency:** every channel row sums to 1, and its transparency, masses and shortfalls
  recompute from it. Each mass and shortfall add up to 1. Every cell follows from the
  shortfalls. Every channel reaches its t.
- **α = 1:** at every t < 1, only CooperateBot cooperates.
- **Games:** points share a game iff their cells are equal. `games/` holds exactly the grid's
  games. Each folder's files hold its points' cells, agree with each other, and record the
  horizon of `grid.json`. Every start of every game converged.
- **Endpoints:** the original's endpoints (T = 10⁴ at t = 0; T = 10⁻⁶ at t = 1 in the syntactic
  family) give the same tournament at every grid point.
- **Twin flag:** it fires on `body8+natives`, which has twins.

`true/checks/check_sweep.py` checks that, on the original's grid, the tournaments computed with
the original's endpoints equal the original code's.

## Results: `body8/floor`

The behavioral family has 62 distinct games over its 707 grid points, the syntactic family 56.
Ids are numbered per family, so the same id can name different games in the two families. Two
games are the same in both:

- `g00`: everyone cooperates (the α = 0 column).
- `g01`: the full-transparency game.

The run prints which game each grid point plays, as a t × α map.

**Replicator dynamics.** In all 118 games, every start converges. Four games needed a longer
horizon: behavioral g11 (10⁷), and syntactic g10 and g12 (10⁸) and g30 (10⁶). In every game all
1000 starts reach the same component. The population ends fully cooperative (Pr[(C, C)] = 1 at
every start) exactly at the grid points whose game has a fully cooperative Nash component.
Everywhere else it ends fully defecting (Pr[(C, C)] = 0).

At each α, the population is cooperative from t = 1 down to a threshold, and defecting below
it. The threshold, the lowest grid t at which the population still ends cooperative:

| α | 0 | 0.2 | 0.4 | 0.5 | 0.6 | 0.8 | 1 |
|---|---|---|---|---|---|---|---|
| behavioral | 0 | 0.28 | 0.01 | 0.11 | 0.24 | 0.50 | 1 |
| syntactic | 0 | 0.32 | 0.01 | 0.07 | 0.20 | 0.57 | 1 |

- **α = 0:** every bot cooperates unconditionally, so the population cooperates at every t,
  including t = 0.
- **α = 1:** the population cooperates only at t = 1. At every t < 1 only CooperateBot
  cooperates, so all of those points play one game.
- **The threshold is not monotone in α.** It is lowest at α = 0.4, where cooperation lasts down
  to t = 0.01 and is lost only at the uniform signal. Lower and higher caution both need more
  transparency.
- **The two families' thresholds differ by at most 0.07** (at α = 0.8).

The same as a map, C for cooperative and D for defecting. A row is shown where it changes, and
holds down to the next row shown:

```
behavioral                          syntactic
    t   0  0.2 0.4 0.5 0.6 0.8  1       t   0  0.2 0.4 0.5 0.6 0.8  1
    1   C   C   C   C   C   C   C       1   C   C   C   C   C   C   C
 0.99   C   C   C   C   C   C   D    0.99   C   C   C   C   C   C   D
 0.49   C   C   C   C   C   D   D    0.56   C   C   C   C   C   D   D
 0.27   C   D   C   C   C   D   D    0.31   C   D   C   C   C   D   D
 0.23   C   D   C   C   D   D   D    0.19   C   D   C   C   D   D   D
  0.1   C   D   C   D   D   D   D    0.06   C   D   C   D   D   D   D
    0   C   D   D   D   D   D   D       0   C   D   D   D   D   D   D
```
