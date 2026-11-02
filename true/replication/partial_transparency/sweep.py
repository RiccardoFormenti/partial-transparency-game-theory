"""Partial-transparency tournaments over the (t, α) grid (Section 6.2).

At one (t, α) every lifted bot meets every other, self-play included. Each receives, from
the channel at transparency t, the signal for its true opponent, and plays by `play.action`.

Signal families (Appendix B.4.1): behavioral, over the Hamming distance between action
rows, and syntactic, over the tree edit distance between source trees. Both are softmax
channels calibrated to the same transparency t (`signals`). The ε-uniform family is not
replicated.

Replicates copy/app/src/pd_runner/tau/sweep.py and the syntactic family of tau/channels.py.
The original calibrates the two families with separate code that differs at the top of
the dial: there the behavioral family uses the point mass, the syntactic one the
temperature MIN_TEMPERATURE. The latter leaves syntactically identical bots (DupocBot and
the two aggregator bots) blurred together even at t = 1, so t = 1 no longer reproduces
the full-transparency table. TOP_TEMPERATURE reproduces the original; pass
top_temperature=0.0 for the point mass in both families.

Usage (from true/):  python -m replication.partial_transparency.sweep <zoo> <side> <family>
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from .play import action
from .signals import (MIN_TEMPERATURE, OPAQUE_TEMPERATURE, behavioral_distances,
                      softmax_channel, temperature_for, transparency)
from ..general.zoo import SIDES, ZOOS, Zoo, load_zoo
from .syntax import syntactic_distances

FAMILIES = ("behavioral", "syntactic")
# The original pipeline's grid (egt/pipeline.py: linear_ts(6) and DEFAULT_ALPHAS).
TS = (1.0, 0.8, 0.6, 0.4, 0.2, 0.0)
ALPHAS = (0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0)
TOP_TEMPERATURE = {"behavioral": 0.0, "syntactic": MIN_TEMPERATURE}

Cells = dict[tuple[str, str], tuple[str, str]]  # (row, col) -> (row's action, col's action)


@dataclass(frozen=True)
class Tournament:
    family: str
    t: float
    alpha: float
    temperature: float
    transparency: float  # of the channel actually used
    cells: Cells

    @property
    def mutual_cooperation(self) -> float:
        """The fraction of ordered pairs, self-play included, that play (C, C)."""
        return sum(pair == ("C", "C") for pair in self.cells.values()) / len(self.cells)


def distances(zoo: Zoo, family: str) -> dict[tuple[str, str], float]:
    if family == "behavioral":
        return behavioral_distances(zoo)
    if family == "syntactic":
        return syntactic_distances(zoo)
    raise ValueError(f"unknown family {family!r}; choose one of {FAMILIES}")


def play_tournament(zoo: Zoo, channel: dict[str, dict[str, float]], alpha: float) -> Cells:
    return {(r, c): (action(zoo, r, channel[c], alpha), action(zoo, c, channel[r], alpha))
            for r in zoo.bots for c in zoo.bots}


def sweep(zoo: Zoo, family: str, ts: tuple[float, ...] = TS,
          alphas: tuple[float, ...] = ALPHAS, opaque_temperature: float = OPAQUE_TEMPERATURE,
          top_temperature: float | None = None) -> list[Tournament]:
    """One tournament per (t, α), t in the outer loop."""
    dist = distances(zoo, family)
    top = TOP_TEMPERATURE[family] if top_temperature is None else top_temperature
    out = []
    for t in ts:
        temperature = temperature_for(zoo.bots, dist, t, opaque_temperature, top)
        channel = softmax_channel(zoo.bots, dist, temperature)
        measured = transparency(channel)
        out += [Tournament(family, t, alpha, temperature, measured,
                           play_tournament(zoo, channel, alpha)) for alpha in alphas]
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="(C, C) rate of each tournament on the grid.")
    p.add_argument("zoo", choices=sorted(ZOOS))
    p.add_argument("side", choices=SIDES)
    p.add_argument("family", choices=FAMILIES)
    args = p.parse_args()
    results = sweep(load_zoo(args.zoo, args.side), args.family)
    print(f"{args.zoo}, {args.side} side, {args.family}: (C, C) rate, rows t, columns α")
    print("  t   " + " ".join(f"{a:>5}" for a in ALPHAS))
    for t in TS:
        rates = [r.mutual_cooperation for r in results if r.t == t]
        print(f"{t:4.1f}  " + " ".join(f"{x:5.3f}" for x in rates))


if __name__ == "__main__":
    main()
