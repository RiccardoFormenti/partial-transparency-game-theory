"""Replicator dynamics on a payoff matrix: which equilibrium a population of bots reaches.

A population is a mix x of bot types (x_i ≥ 0, Σ x_i = 1). A bot of type i meets a random
member of the population and expects (Ax)_i; a type grows when that beats the average:

    ẋ_i = x_i · g_i(x),   g_i(x) = (Ax)_i − xᵀAx.

1. Starts are drawn uniformly on the simplex (Dirichlet(1)), so every type is present at
   the start. Selection never brings back an absent type, and a start without some types
   asks the question of a smaller zoo.
2. Each start is integrated in log-shares z_i = log x_i, where ż_i = g_i(x) and
   x = softmax(z). Shares then stay positive and sum to 1 exactly, however small they get.
3. A start has converged when, at both HORIZON / 2 and HORIZON, x is a symmetric Nash
   equilibrium up to TOL: no type grows faster than TOL, every type is absent (x_i < TOL) or
   ties the best (g_i ≥ −TOL), these sets are the same at both times, and x moved less than
   TOL between them. A cycle fails the test, even a heteroclinic one, which slows down near
   each type it passes: there the next type grows. A start that has not converged is
   counted as such, never assigned to an equilibrium.
4. A converged end state is matched to the Nash component (`equilibria`) it lies in. Label a
   mixed strategy by the types it does not play and the types that are best replies to it.
   For a symmetric equilibrium (x, x), the strategies with at least x's labels form a face F
   of the best-response polytope, with x ∈ F. Every type is absent from x or a best reply
   to it, so for y, y′ ∈ F the pair (y, y′) has every label: it is an equilibrium. So F's
   vertices are extreme strategies that all pair with each other, and lie in x's component
   (`equilibria`, step 4). The code finds F from the end state's labels (its absent and its
   tied types), checks that F's vertices lie in one component, and that the end state lies
   within MAX_DISTANCE of F.
5. A component's basin is the share of starts that converge to it. Since starts are
   independent draws, the 95% Wilson interval bounds the error of that estimate.

Interior trajectories that converge do so to Nash equilibria (the folk theorem of
evolutionary game theory; Hofbauer and Sigmund 2003). So every converged start reaches some
component, and its labels pick out a face. When either fails, `basins` raises an error.

Replicates copy/app/src/pd_runner/egt/replicator/, with these differences:
- The original integrates x with fixed-step RK4, clipping negative shares to 0.
- The original's convergence test is a speed below 1e-7. A heteroclinic cycle passes that
  test near each type. On A = [[0, −2, 1], [1, 0, −2], [−2, 1, 0]] (rock-paper-scissors, a
  loss costing more than a win earns), it reports every start as converged to one type.
- The original groups end states by the types above a share of 1e-3. That splits a
  continuum of equilibria into several "attractors".
- The original also starts at each single-type state. Each is a rest point, so it reports
  every type as an attractor, even types that others invade.
- The original's basin is a share of the converged starts, with the uniform mix included
  among them. Here it is a share of all starts, and unconverged starts are their own count.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import nnls

from .equilibria import Equilibrium, Matrix, payoffs_against

HORIZON = 1e5  # time integrated; payoffs are of order 1, so this is long
TOL = 1e-6  # absent share, tied growth rate, and movement over the last half of HORIZON
MAX_DISTANCE = 1e-4  # how far a converged end state may lie from its component
RTOL, ATOL = 1e-10, 1e-12  # integration error, per log-share
Z95 = 1.959963984540054  # the standard normal's 97.5% quantile


@dataclass(frozen=True)
class Run:
    start: np.ndarray  # x at time 0
    end: np.ndarray  # x at HORIZON
    converged: bool
    component: int | None  # the Nash component `end` lies in; None when not converged
    distance: float | None  # sup-norm distance from `end` to a symmetric equilibrium in it


@dataclass(frozen=True)
class _Vertex:
    """An extreme row strategy of the equilibria, with its labels."""

    x: np.ndarray
    present: frozenset[int]  # the types it plays
    best: frozenset[int]  # the types that are best replies to it
    component: int


def growth_rates(A: np.ndarray, x: np.ndarray) -> np.ndarray:
    """g_i(x) = (Ax)_i − xᵀAx: each type's payoff against x, minus the population's average."""
    payoffs = A @ x
    return payoffs - x @ payoffs


def softmax(z: np.ndarray) -> np.ndarray:
    w = np.exp(z - z.max())
    return w / w.sum()


def sample_starts(n_types: int, n_starts: int, seed: int) -> np.ndarray:
    """n_starts mixes drawn uniformly on the simplex, one per row."""
    return np.random.default_rng(seed).dirichlet(np.ones(n_types), size=n_starts)


def integrate(A: np.ndarray, start: np.ndarray, times: tuple[float, ...]) -> np.ndarray:
    """x at each of `times` (a row each), from `start` at time 0."""
    if np.any(start <= 0) or not np.isclose(start.sum(), 1):
        raise ValueError(f"a start must have every share positive, summing to 1: {start}")
    sol = solve_ivp(lambda _, z: growth_rates(A, softmax(z)), (0, times[-1]), np.log(start),
                    method="LSODA", t_eval=times, rtol=RTOL, atol=ATOL)
    if not sol.success:
        raise RuntimeError(f"integration failed from {start}: {sol.message}")
    return np.array([softmax(z) for z in sol.y.T])


def labels(A: np.ndarray, x: np.ndarray) -> tuple[frozenset[int], frozenset[int]] | None:
    """(present types, best replies) when (x, x) is a Nash equilibrium up to TOL, else None."""
    g = growth_rates(A, x)
    present = frozenset(int(i) for i in np.flatnonzero(x >= TOL))
    best = frozenset(int(i) for i in np.flatnonzero(g >= -TOL))
    if g.max() > TOL or not present <= best:
        return None
    return present, best


def _vertices(A: Matrix, found: list[Equilibrium]) -> list[_Vertex]:
    """Every extreme row strategy, once. By symmetry they are also the column strategies."""
    out: dict = {}
    for e in found:
        if e.row not in out:
            v = payoffs_against(A, e.row)
            top = max(v)
            out[e.row] = _Vertex(x=np.array([float(p) for p in e.row]),
                                 present=frozenset(i for i, p in enumerate(e.row) if p > 0),
                                 best=frozenset(j for j, a in enumerate(v) if a == top),
                                 component=e.component)
    return list(out.values())


def _locate(x: np.ndarray, present: frozenset[int], best: frozenset[int],
            vertices: list[_Vertex]) -> tuple[int, float]:
    """The component of the face with labels (present, best), and x's distance to the face."""
    face = [v for v in vertices if v.present <= present and best <= v.best]
    components = {v.component for v in face}
    if len(components) != 1:
        raise ValueError(f"the end state {x} matches faces of {len(components)} components")
    V = np.column_stack([v.x for v in face])
    weights, _ = nnls(V, x)
    distance = float(np.abs(V @ (weights / weights.sum()) - x).max())
    if distance > MAX_DISTANCE:
        raise ValueError(f"the end state {x} is {distance:.1e} from its face")
    return components.pop(), distance


def basins(A: Matrix, found: list[Equilibrium], starts: np.ndarray) -> list[Run]:
    """Integrate each start; match the converged end states to their Nash components.

    `found` are the extreme equilibria of (A, Aᵀ), from `equilibria.analyse`.
    """
    Af = np.array(A, dtype=float)
    vertices = _vertices(A, found)
    runs = []
    for start in starts:
        half, end = integrate(Af, start, (HORIZON / 2, HORIZON))
        found_labels = labels(Af, end)
        converged = (found_labels is not None and found_labels == labels(Af, half)
                     and float(np.abs(end - half).max()) < TOL)
        component, distance = _locate(end, *found_labels, vertices) if converged else (None, None)
        runs.append(Run(start=start, end=end, converged=converged, component=component,
                        distance=distance))
    return runs


def wilson_interval(k: int, n: int) -> tuple[float, float]:
    """95% interval for a probability, from k successes in n independent trials."""
    p, z2 = k / n, Z95 ** 2
    centre = (p + z2 / (2 * n)) / (1 + z2 / n)
    half = Z95 * float(np.sqrt(p * (1 - p) / n + z2 / (4 * n * n))) / (1 + z2 / n)
    return max(0.0, centre - half), min(1.0, centre + half)
