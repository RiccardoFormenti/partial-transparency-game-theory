"""How a lifted bot plays on a signal (Section 3.4, Appendix D.3.2).

The bot runs its own test against every hypothesis in the signal: its test bit at
hypothesis h is its own action against h at full transparency (`Zoo.action`). It then
cooperates iff the aggregated weight of the hypotheses it would cooperate with is at
least α:
  sum  (every lifted bot)    the total weight of those hypotheses
  max  (MaxConfidenceBot)    the largest single weight among them
  min  (MinConfidenceBot)    1 - the largest single weight of a hypothesis it would defect on

Replicates copy/app/src/pd_runner/tau/play.py. The min rule cooperates when the largest
failing weight equals 1 - α exactly; the paper's wording ("every hypothesis of weight at
least 1 - α passes") would defect there. No grid point of the paper sits on that boundary.
"""

from __future__ import annotations

import math

from ..general.zoo import Zoo

# A mass that is mathematically α can land an ulp below it after summing floats.
MASS_TOLERANCE = 1e-12


def decision_mass(zoo: Zoo, actor: str, signal: dict[str, float]) -> float:
    """The quantity `actor` compares with α."""
    passing = [p for h, p in signal.items() if p > 0 and zoo.action(actor, h) == "C"]
    failing = [p for h, p in signal.items() if p > 0 and zoo.action(actor, h) != "C"]
    aggregator = zoo.aggregators[actor]
    if aggregator == "sum":
        return math.fsum(passing)
    if aggregator == "max":
        return max(passing, default=0.0)
    if aggregator == "min":
        return 1.0 - max(failing, default=0.0)
    raise ValueError(f"unknown aggregator {aggregator!r} for {actor}")


def action(zoo: Zoo, actor: str, signal: dict[str, float], alpha: float) -> str:
    """What `actor` plays when its belief about the opponent is `signal`."""
    return "C" if decision_mass(zoo, actor, signal) >= alpha - MASS_TOLERANCE else "D"
