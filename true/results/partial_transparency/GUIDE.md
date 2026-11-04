# Partial-transparency results: quick guide

This folder holds the (t, α) grid on the eight-bot zoo `body8`, floor side. For each grid
point it has the tournament the lifted bots play, the Nash equilibria of the resulting game,
and the replicator basins. This page shows where things are and how to read them.
[README.md](README.md) explains every entry in every file.

## Layout

```
partial_transparency/body8/floor/
  behavioral/                 one folder per signal family
    grid.json                 the index: every grid point, its signal and tournament, and its game
    games/g00/ … g61/         one folder per distinct game
      equilibria.json         Nash equilibria and components
      replicator.json         replicator basins, per component
      replicator_runs.csv     one row per replicator start
      lrsnash_input.txt       the solver's input
      lrsnash_output.txt      the solver's raw output
  syntactic/                  the same, with games g00 … g55
```

- **The grid.** t runs from 1 to 0 in steps of 0.01. α ∈ {0, 0.2, 0.4, 0.5, 0.6, 0.8, 1}.
  That gives 707 points per family.
- **The endpoints.** t = 1 is full transparency, where the signal names the opponent exactly.
  t = 0 is the uniform signal, which says nothing about it.
- **The families.** `behavioral` blurs bots that play alike; `syntactic` blurs bots whose
  source code is alike.

## Finding a grid point's results

Grid points whose tournaments come out the same play the same game, and each game is solved
once. So a result is found in two steps: look up the point's game id in `grid.json`, then open
`games/<id>/`. Game ids are numbered separately in each family, so g05 in `behavioral` is not
g05 in `syntactic`.

```python
import json
from fractions import Fraction
from pathlib import Path

root = Path("true/results/partial_transparency/body8/floor/behavioral")
grid = json.loads((root / "grid.json").read_text())
point = next(p for p in grid["points"] if p["t"] == 0.3 and p["alpha"] == 0.5)
game = root / "games" / point["game"]

eq = json.loads((game / "equilibria.json").read_text())
rep = json.loads((game / "replicator.json").read_text())
fully_cooperative = any(Fraction(c["cooperation"]["max"]) == 1 for c in eq["components"])
basins = {c["id"]: c["basin"] for c in rep["components"]}
```

t is stored rounded to 10 decimals, so the exact comparison `p["t"] == 0.3` works. Each game's
JSON files also list the grid points that play it (`points`).

## `grid.json`

| key | what |
|---|---|
| `points` | One entry per (t, α): its `game` id, its tournament `cells`, and `mutual_cooperation`, the share of ordered pairs that play (C, C). |
| `channels` | One entry per t: `temperature` (0 at t = 1; `null` means ∞, at t = 0), the measured `transparency`, the signal matrix `channel[i][j]`, each bot's `mass` (what it compares with α) and `shortfall` (1 − mass, what its decision is computed from). |
| `games` | One entry per game: its `id`, the grid `points` that play it, and the replicator `horizon` it needed. |
| `twins`, `ceiling`, `unreached` | The twin flags. On body8 they are empty, 1 and empty: every t is reached. |
| `bots`, `ts`, `alphas`, `distances`, `settings` | The zoo order, the grid, the distance the signal blurs over, and the numerical settings. |

## The game files

`equilibria.json` and `replicator.json` have the same format as at full transparency
(`../full_transparency/README.md`), with three added keys: `family`, `game` and `points`.

- **Order.** Every matrix and vector is in the order of `bots`.
- **Cells.** `cells[i][j]` is `bots[i]`'s action, then `bots[j]`'s, for example `"CD"`. The
  game's payoff matrix `A` is built from them, with T, R, P, S = 3, 2, 0, −1.
- **Exact values.** Values in `equilibria.json` are exact fractions written as strings
  (`"11/18"`).
- **Strategies** are `{bot: probability}` and list only the bots played with positive
  probability.
- **Components.** Each one in `equilibria.json` has its bots and its range of Pr[(C, C)] and
  of payoff. `replicator.json` and `replicator_runs.csv` use the same component ids.
- **Replicator dynamics.** They start from the same 1000 points (seed 20260514) in every game.
  `settings.horizon` is the time integrated to: 10⁵, or longer for the few games that needed it.

## Recomputing and checking

From `true/`:

```bash
conda run -n py-random python -m replication.partial_transparency.grid           # about 7 minutes
conda run -n py-random python checks/check_partial_transparency.py               # checks the saved files
```

A run gives the same files every time, except the timing line in `lrsnash_output.txt`.
