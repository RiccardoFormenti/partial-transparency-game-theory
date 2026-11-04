# Zoo-ladder results

This folder holds the data for the paper's zoo-ladder table (Table 8): four nested zoos at full
transparency, each with its Nash headline and, in place of the paper's Moran column, its
replicator-dynamics headline. It is computed by `replication/full_transparency/zoo_ladder.py`,
which runs `nash` and `replicator` on each zoo and collects one row per zoo in `ladder.json`.

## Layout

```
zoo_ladder/
  README.md                this file
  <side>/
    ladder.json            one row of the table per zoo
    <zoo>/
      equilibria.json      \
      lrsnash_input.txt     |  the same files, in the same format, as
      lrsnash_output.txt    |  results/full_transparency/<zoo>/<side>/;
      replicator.json       |  see results/full_transparency/README.md
      replicator_runs.csv  /
```

To compute or recompute, run from `true/`:

```bash
conda run -n py-random python -m replication.full_transparency.zoo_ladder                # floor side
conda run -n py-random python -m replication.full_transparency.zoo_ladder --side hinge   # hinge side
```

A run overwrites every file of that side, and takes a few minutes. The same data and the same
numpy and scipy versions always give the same files, except the timing line in
`lrsnash_output.txt`. Only the floor side, the side of the paper's table, has been computed.

The replicator dynamics run to the usual horizon 10⁵, except in `body8+trolls`, which runs to
10⁹ (`HORIZONS` in `zoo_ladder.py`; see [below](#body8trolls-slow-escapes-from-full-defection)
for why). Each zoo's horizon is in its `replicator.json` (`settings.horizon`) and in
`ladder.json`.

`true/checks/check_zoo_ladder.py` checks the saved floor-side ladder: that its `body8` files
equal those of `results/full_transparency/body8/floor/` (all five agree, apart from lrsnash's
timing line), that `ladder.json` agrees with each zoo's files and horizon, that the zoos are
nested, and that the Nash columns match the paper's Table 8.

### Zoos

The ladder's four zoos (Figure 2), each holding the one before:

| zoo | bots |
|---|---|
| `nonprovers+dupoc` | CooperateBot, DBot, DefectBot, DupocBot, EBot, OBot, TitForTatBot (7) |
| `body8` | `nonprovers+dupoc` + CupodBot (8) |
| `body8+trolls` | `body8` + CupodTrollBot, DupocTrollBot (10) |
| `body8+trolls+provers` | `body8+trolls` + CIMCIC, DIMDID (12) |

The sides `floor` and `hinge` are as in `results/full_transparency/README.md`.

## `ladder.json`

### Top-level entries

| key | type | meaning |
|---|---|---|
| `side` | `"floor"` or `"hinge"` | How hinge cells are resolved. |
| `zoos` | list | One row per zoo, in ladder order (see [below](#entries-of-zoos)). |

### Entries of `zoos`

Every value is read from the zoo's files in `<side>/<zoo>/`.

| key | type | meaning |
|---|---|---|
| `zoo` | string | The zoo's name. |
| `bots` | list of strings | The zoo's bots, in the order of its files. |
| `nash.n_components` | integer | The number of components of Nash equilibria (`n_components` of `equilibria.json`). The table's "components" column. |
| `nash.n_equilibria` | integer | The number of extreme equilibria. |
| `nash.cooperative_component` | `{"id", "bots"}` | The component that contains a fully cooperative equilibrium (Pr[(C, C)] = 1): its `id` and `bots` in `equilibria.json`. The table's "cooperative component" column. The run stops with an error if a zoo has no such component, or more than one. |
| `replicator.horizon` | float | How long each start of the replicator dynamics is integrated. |
| `replicator.n_starts` | integer | The number of starts. |
| `replicator.n_converged` | integer | How many of them converged by the horizon. |
| `replicator.cooperative_basin` | float | The share of all starts that converge to the cooperative component. |
| `replicator.cooperative_basin_ci95` | [low, high] | Its 95% Wilson interval. |
| `replicator.cooperation` | `{"mean", "min", "max"}` | Pr[(C, C)] in the population each start ends in (column `cooperation` of `replicator_runs.csv`), averaged over all starts, converged or not, and its smallest and largest values. The mean is the expected cooperation rate of the population reached from a uniformly random start. |
| `replicator.basins` | list of `{"id", "bots", "basin"}` | Every component that at least one start reaches, with its basin. The starts not listed did not converge (`n_starts` − `n_converged`). |

## Floor-side results

| zoo | Nash: components (extreme) | cooperative component | replicator: cooperative basin | mean Pr[(C, C)] |
|---|---|---|---|---|
| `nonprovers+dupoc` | 3 (21) | {Coop, Dup, TFT} | 100% | 1.000 |
| `body8` | 3 (21) | {Coop, Dup, TFT} | 100% | 1.000 |
| `body8+trolls` | 3 (35) | {Coop, Dup, TFT} | 85.4% [83.1, 87.5] | 0.866 |
| `body8+trolls+provers` | 3 (69) | {CIM, Coop, Dup, TFT} | 100% | 1.000 |

The Nash columns match the paper's Table 8.

### `body8+trolls`: slow escapes from full defection

In `body8+trolls`, 854 starts reach the cooperative component, 93 converge to the
full-defection component {DefectBot, OBot}, and 53 do not converge by the horizon (10⁵). These
two last groups are one phenomenon: DupocBot slowly invading full defection.

- Among DefectBot, OBot and DupocBot every pairing pays 0, except DupocBot against itself,
  which pays 2. Near full defection DupocBot's growth rate is therefore about 2·x, where x is
  its share. It grows, but only at second order, and leaving takes a time of about 1/(2x).
- The 93 starts that converge to full defection end with DupocBot's share between 10⁻²¹⁴ and
  5·10⁻⁷, below the tolerance 10⁻⁶ that counts it absent. Their escape times are at least 10⁶
  and up to astronomically long.
- The 53 unconverged starts end with DupocBot's share between 5·10⁻⁷ and 1: they are leaving
  full defection at the horizon. 12 of them have already reached DupocBot alone, but too late
  to count as converged.

So the full-defection component is not an attractor of the exact dynamics, but populations
that arrive with little DupocBot stay near it for a very long time. The cooperative basin of
85.4% is the one at the horizon 10⁵. A longer horizon would first add most of the 53
unconverged starts, then only a few starts per tenfold increase. 14 of the 93 starts have
DupocBot's share below 10⁻²⁰ and would need a horizon beyond 10¹⁹. In the other three zoos
every start converges to the cooperative component.
