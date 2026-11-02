"""Signals: the belief a lifted bot receives about its opponent (Sections 3.4 and B.4).

A signal is a probability distribution over the zoo: how likely each member is to be the
opponent. A channel gives the signal for every possible true opponent.

Behavioral channel (Definition 32): a softmax over the Hamming distance between two bots'
action rows,
    σ_T(B)[B'] ∝ exp(-d(B, B') / T),
with the point mass at T = 0 and the uniform distribution at T = ∞.

Transparency (Definition 34): the mutual information between the true opponent, drawn
uniformly from the zoo, and the signal, divided by log2 n. The dial t ∈ [0, 1] is turned
into a temperature by inverting it, so the channel at t = 0.4 measures 0.4.

Replicates copy/app/src/pd_runner/tau/signal.py. Two of its choices, kept so results can
be compared, differ from the paper:
- t = 0 uses the finite temperature OPAQUE_TEMPERATURE, not the uniform distribution of
  Definition 32. Pass opaque_temperature=math.inf for the paper's version.
- Bots with identical rows ("twins") cannot be told apart at any T > 0, so transparency
  has a ceiling below 1. A dial at or above the ceiling returns the point mass, whose
  transparency is 1, not t. (The original's syntactic family returns MIN_TEMPERATURE
  there instead, which keeps twins blurred even at t = 1: see `top_temperature`.)
"""

from __future__ import annotations

import math

from ..general.zoo import Zoo

Channel = dict[str, dict[str, float]]  # true opponent -> {hypothesis: probability}

# The original's endpoints: t = 0 is OPAQUE_TEMPERATURE, and the dial is inverted by a
# bisection over [MIN_TEMPERATURE, OPAQUE_TEMPERATURE], stopped at this relative width.
OPAQUE_TEMPERATURE = 1e4
MIN_TEMPERATURE = 1e-6
BISECTION_TOLERANCE = 1e-4


def behavioral_distances(zoo: Zoo) -> dict[tuple[str, str], int]:
    """d(B, B'): the number of zoo members against which B and B' play differently."""
    return {(a, b): sum(zoo.action(a, m) != zoo.action(b, m) for m in zoo.bots)
            for a in zoo.bots for b in zoo.bots}


def softmax_channel(bots: tuple[str, ...], distances: dict[tuple[str, str], float],
                    temperature: float) -> Channel:
    """σ_T for every true opponent: the point mass at T = 0, uniform at T = ∞."""
    if temperature < 0:
        raise ValueError(f"temperature must be non-negative, got {temperature}")
    if temperature == 0:
        return {b: {h: float(h == b) for h in bots} for b in bots}
    if math.isinf(temperature):
        return {b: {h: 1 / len(bots) for h in bots} for b in bots}
    channel = {}
    for b in bots:
        # d(b, b) = 0 is the smallest distance, so no weight overflows.
        weights = {h: math.exp(-distances[(b, h)] / temperature) for h in bots}
        total = math.fsum(weights.values())
        channel[b] = {h: w / total for h, w in weights.items()}
    return channel


def transparency(channel: Channel) -> float:
    """I(B; S) / log2 n for B uniform over the zoo and S drawn from the channel."""
    bots = tuple(channel)
    n = len(bots)
    if n < 2:
        return 0.0
    marginal = {s: math.fsum(channel[b].get(s, 0.0) for b in bots) / n for s in bots}
    information = math.fsum(p / n * math.log2(p / marginal[s])
                            for b in bots for s, p in channel[b].items() if p > 0)
    return information / math.log2(n)


def twin_classes(bots: tuple[str, ...], distances: dict[tuple[str, str], float]
                 ) -> list[tuple[str, ...]]:
    """Groups of two or more bots at distance 0 from one another."""
    classes = {tuple(h for h in bots if distances[(b, h)] == 0) for b in bots}
    return sorted(c for c in classes if len(c) > 1)


def ceiling(bots: tuple[str, ...], distances: dict[tuple[str, str], float]) -> float:
    """The most transparency any T > 0 reaches: the limit T -> 0, where each signal is
    uniform over the true opponent's twins. 1 when the zoo has no twins."""
    limit = {}
    for b in bots:
        twins = [h for h in bots if distances[(b, h)] == 0]
        limit[b] = {h: 1 / len(twins) if h in twins else 0.0 for h in bots}
    return transparency(limit)


def temperature_for(bots: tuple[str, ...], distances: dict[tuple[str, str], float], t: float,
                    opaque_temperature: float = OPAQUE_TEMPERATURE,
                    top_temperature: float = 0.0) -> float:
    """The temperature whose channel has transparency t.

    `opaque_temperature` is used at t = 0, `top_temperature` at or above the ceiling.
    """
    if not -1e-9 <= t <= 1 + 1e-9:
        raise ValueError(f"t must be in [0, 1], got {t}")
    t = min(max(t, 0.0), 1.0)
    if t == 0:
        return opaque_temperature
    if t >= ceiling(bots, distances) - 1e-9:
        return top_temperature
    # Transparency decreases in T (checks/check_signals.py verifies it on every zoo), so
    # bisecting on log T finds the crossing.
    low, high = MIN_TEMPERATURE, OPAQUE_TEMPERATURE
    while high / low >= 1 + BISECTION_TOLERANCE:
        mid = math.sqrt(low * high)
        if transparency(softmax_channel(bots, distances, mid)) > t:
            low = mid
        else:
            high = mid
    return math.sqrt(low * high)


def channel_at(bots: tuple[str, ...], distances: dict[tuple[str, str], float], t: float,
               opaque_temperature: float = OPAQUE_TEMPERATURE,
               top_temperature: float = 0.0) -> Channel:
    """The channel at dial t."""
    return softmax_channel(bots, distances, temperature_for(
        bots, distances, t, opaque_temperature, top_temperature))
