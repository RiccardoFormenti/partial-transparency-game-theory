"""Payoff matrices from tournament outcomes (Example 1, Section 6.1.1).

A[i, j] is the payoff of a bot of type i meeting type j: R, S, T or P as cell (i, j) is
(C, C), (C, D), (D, C) or (D, D). The paper's values are T, R, P, S = 3, 2, 0, -1.

Replicates copy/app/src/pd_runner/egt/ingest.py, but takes T, R, P, S as in the paper.
The original's (b, c) form, with T = b, R = b - c, P = 0, S = -c, only covers games with
T - R = P - S, so it cannot test any other Prisoner's Dilemma.
"""

from __future__ import annotations

import numpy as np


def payoff_matrix(bots: tuple[str, ...], cells: dict[tuple[str, str], tuple[str, str]],
                  T: float = 3.0, R: float = 2.0, P: float = 0.0, S: float = -1.0) -> np.ndarray:
    if not T > R > P > S:
        raise ValueError(f"not a Prisoner's Dilemma: need T > R > P > S, got {T, R, P, S}")
    value = {("C", "C"): R, ("C", "D"): S, ("D", "C"): T, ("D", "D"): P}
    A = np.empty((len(bots), len(bots)))
    for i, a in enumerate(bots):
        for j, b in enumerate(bots):
            pair = tuple(cells[(a, b)])
            if pair not in value:
                raise ValueError(f"cell ({a}, {b}) is {pair}, not a pair of C/D actions")
            A[i, j] = value[pair]
    return A
