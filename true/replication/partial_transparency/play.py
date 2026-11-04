"""How a lifted bot plays on a signal (Section 3.4, Appendix D.3.2).

The bot runs its own test against every hypothesis in the signal: its test bit at
hypothesis h is its own action against h at full transparency (`Zoo.action`). It then
cooperates iff the aggregated weight of the hypotheses it would cooperate with is at
least α:
  sum  (every lifted bot)    the total weight of those hypotheses
  max  (MaxConfidenceBot)    the largest single weight among them
  min  (MinConfidenceBot)    1 - the largest single weight of a hypothesis it would defect on

The comparison is made on the complement: the bot cooperates iff its shortfall, 1 - mass, is
at most 1 - α. The shortfall is computed from the weights it is made of, not by subtraction:
  sum  the total weight of the hypotheses it would defect on
  max  the total weight of every hypothesis but the heaviest it would cooperate with
  min  the largest weight of a hypothesis it would defect on
This matters near α = 1. A softmax gives every hypothesis positive weight, so at α = 1 a bot
that would defect on any hypothesis must defect. Its mass, 1 minus that weight, rounds to 1
once the weight falls below about 1e-16, but its shortfall is the weight itself.

Replicates copy/app/src/pd_runner/tau/play.py, which compares the mass with α - 1e-12. The two
differ only where the shortfall is positive but within about 1e-12 of 1 - α. On body8's floor
side that happens at α = 1 in the behavioral family at t = 0.99 and 0.98, where the original
lets DBot cooperate although it would defect on hypotheses of weight 1e-15 to 1e-13. No point
of the original's grid is affected (checks/check_sweep.py).

The min rule cooperates when the largest failing weight equals 1 - α exactly; the paper's
wording ("every hypothesis of weight at least 1 - α passes") would defect there. No grid point
of the paper sits on that boundary.
"""

from __future__ import annotations

import math

from ..general.zoo import Zoo

# A shortfall that is mathematically 1 - α (k/n under the uniform signal, say) can land a few
# ulps above it after summing floats. Relative to 1 - α, so that at α = 1 only a shortfall of
# exactly 0 cooperates.
TIE_TOLERANCE = 1e-12


def _split(zoo: Zoo, actor: str, signal: dict[str, float]
           ) -> tuple[dict[str, float], list[float]]:
    """The weights of the hypotheses `actor` would cooperate with, and of the others."""
    passing = {h: p for h, p in signal.items() if p > 0 and zoo.action(actor, h) == "C"}
    failing = [p for h, p in signal.items() if p > 0 and zoo.action(actor, h) != "C"]
    return passing, failing


def decision_mass(zoo: Zoo, actor: str, signal: dict[str, float]) -> float:
    """The quantity `actor` compares with α."""
    passing, failing = _split(zoo, actor, signal)
    aggregator = zoo.aggregators[actor]
    if aggregator == "sum":
        return math.fsum(passing.values())
    if aggregator == "max":
        return max(passing.values(), default=0.0)
    if aggregator == "min":
        return 1.0 - max(failing, default=0.0)
    raise ValueError(f"unknown aggregator {aggregator!r} for {actor}")


def shortfall(zoo: Zoo, actor: str, signal: dict[str, float]) -> float:
    """1 - `decision_mass`, computed from the weights it is made of."""
    passing, failing = _split(zoo, actor, signal)
    aggregator = zoo.aggregators[actor]
    if aggregator == "sum":
        return math.fsum(failing)
    if aggregator == "max":
        if not passing:
            return 1.0
        top = max(passing, key=passing.get)
        return math.fsum(p for h, p in signal.items() if h != top)
    if aggregator == "min":
        return max(failing, default=0.0)
    raise ValueError(f"unknown aggregator {aggregator!r} for {actor}")


def action(zoo: Zoo, actor: str, signal: dict[str, float], alpha: float) -> str:
    """What `actor` plays when its belief about the opponent is `signal`."""
    return "C" if shortfall(zoo, actor, signal) <= (1 - alpha) * (1 + TIE_TOLERANCE) else "D"
