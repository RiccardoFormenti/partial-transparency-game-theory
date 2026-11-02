"""Nash equilibria of the symmetric game a payoff matrix defines, in exact arithmetic.

Both players pick a bot type; the row player gets A[i, j] and the column player A[j, i], so
the game is (A, Aᵀ). An equilibrium is a pair (ξ, η) of mixed strategies, each a best reply
to the other. The set of equilibria is a finite union of polytopes, described by its extreme
equilibria.

1. lrsnash enumerates the extreme equilibria, by vertex enumeration on the best-response
   polytopes. A is first shifted to be positive, which does not change the equilibria.
2. Each is checked to be an equilibrium of the unshifted A. The list is checked to be
   complete against lrsnash's own count, against the pure equilibria found directly, and
   against symmetry: the game is symmetric, so the mirror (η, ξ) of an extreme equilibrium
   is one too.
3. An equilibrium is symmetric when ξ = η; `mirror` pairs each asymmetric one with (η, ξ).
4. Components: the connected components of the graph whose nodes are the row strategies and
   the column strategies of extreme equilibria, and whose edges are the extreme equilibria.
   The equilibrium set is the union of conv(X) × conv(Y) over the maximal bicliques X × Y of
   this graph (Avis, Rosenberg, Savani and von Stengel 2010), so two extreme equilibria lie
   in one component iff a path in the graph joins them.
5. Pr[(C, C)], the probability that both bots cooperate, read from the cells: A alone cannot
   tell which action pair a payoff came from.
Payoffs and Pr[(C, C)] are bilinear in (ξ, η), so over a component they range between their
smallest and largest values at its extreme equilibria.

Replicates copy/app/src/pd_runner/egt/nash/, with two differences:
- lrsnash is the only solver. The original's is pygambit, with lrsnash as an optional
  cross-check.
- The original puts two extreme equilibria in one component when their midpoint is an
  equilibrium. That merges separate components: in the coordination game A = I, (e1, e1)
  and (e2, e2) are isolated, but their midpoint is the third equilibrium, so it reports two
  components where there are three.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

Matrix = list[list[Fraction]]
Strategy = tuple[Fraction, ...]  # a probability for each bot, in zoo order
Pair = tuple[Strategy, Strategy]  # (row player's strategy, column player's strategy)


@dataclass(frozen=True)
class Equilibrium:
    row: Strategy  # ξ
    col: Strategy  # η
    row_payoff: Fraction  # ξᵀ A η
    col_payoff: Fraction  # ηᵀ A ξ
    symmetric: bool  # ξ = η
    mirror: int  # index of (η, ξ); an equilibrium's own index when it is symmetric
    component: int
    cooperation: Fraction  # Pr[(C, C)]


def exact(A) -> Matrix:
    """A as Fractions, each entry read as the decimal it prints as (3.0 -> 3, 0.1 -> 1/10)."""
    M = [[Fraction(str(a)) for a in row] for row in A]
    if not M or any(len(row) != len(M) for row in M):
        raise ValueError("A must be a non-empty square matrix")
    return M


def lrsnash_input(A: Matrix) -> str:
    """The game (A, Aᵀ) in lrsnash's format, shifted so that the smallest payoff is 1."""
    shift = 1 - min(min(row) for row in A)
    rows = [[a + shift for a in row] for row in A]
    cols = [list(c) for c in zip(*rows)]  # the column player's payoffs, Aᵀ

    def block(M: Matrix) -> str:
        return "\n".join(" ".join(str(x) for x in row) for row in M)

    return f"{len(A)} {len(A)}\n\n{block(rows)}\n\n{block(cols)}\n"


def _lrsnash_binary() -> str:
    # Running a conda environment's python directly leaves its bin/ off PATH.
    found = shutil.which("lrsnash") or shutil.which("lrsnash", path=str(Path(sys.executable).parent))
    if found is None:
        raise FileNotFoundError("lrsnash not found: install lrslib (conda install -c conda-forge lrslib)")
    return found


def run_lrsnash(game: str) -> str:
    """lrsnash's output for a game in its input format."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "game.nash"
        path.write_text(game)
        proc = subprocess.run([_lrsnash_binary(), str(path)], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"lrsnash failed (exit {proc.returncode}):\n{proc.stderr}")
    return proc.stdout


def parse_lrsnash(output: str, n: int) -> list[Pair]:
    """The extreme equilibria in lrsnash's output, for a game with n strategies per player.

    Blocks are separated by blank lines. In a block, a line `2 <η> <payoff>` gives a column
    strategy and `1 <ξ> <payoff>` a row strategy, and every (ξ, η) pairing is an extreme
    equilibrium. Lines starting with `*` are comments, one of which gives the count.
    """
    pairs: list[Pair] = []
    rows: list[Strategy] = []
    cols: list[Strategy] = []
    count = None
    for line in output.splitlines() + [""]:
        tokens = line.split()
        if not tokens:  # end of a block
            if bool(rows) != bool(cols):
                raise ValueError("lrsnash: a block lists strategies of only one player")
            pairs += [(x, y) for x in rows for y in cols]
            rows, cols = [], []
        elif tokens[0].startswith("*"):
            found = re.fullmatch(r"\*Number of equilibria found:\s*(\d+)", line.strip())
            if found:
                count = int(found.group(1))
        elif tokens[0] in ("1", "2") and len(tokens) == n + 2:
            strategy = tuple(Fraction(t) for t in tokens[1:n + 1])
            (rows if tokens[0] == "1" else cols).append(strategy)
        else:
            raise ValueError(f"lrsnash: unexpected line {line!r}")
    if count is None:
        raise ValueError("lrsnash: no '*Number of equilibria found' line")
    if count != len(pairs):
        raise ValueError(f"lrsnash reports {count} equilibria, but lists {len(pairs)}")
    return pairs


def payoffs_against(A: Matrix, mix: Strategy) -> list[Fraction]:
    """The payoff of each pure strategy against the mixed strategy `mix`."""
    return [sum((a * p for a, p in zip(row, mix)), Fraction(0)) for row in A]


def payoff(A: Matrix, s: Strategy, mix: Strategy) -> Fraction:
    return sum((p * v for p, v in zip(s, payoffs_against(A, mix))), Fraction(0))


def is_equilibrium(A: Matrix, row: Strategy, col: Strategy) -> bool:
    """Each strategy earns, against the other, the most any pure strategy does."""
    return (payoff(A, row, col) == max(payoffs_against(A, col))
            and payoff(A, col, row) == max(payoffs_against(A, row)))


def _check_strategy(s: Strategy, n: int) -> None:
    if len(s) != n or any(p < 0 for p in s) or sum(s) != 1:
        raise ValueError(f"not a probability vector over {n} strategies: {s}")


def components(pairs: list[Pair]) -> list[int]:
    """The component of each extreme equilibrium, numbered by first appearance."""
    parent: dict = {}

    def root(node):
        parent.setdefault(node, node)
        while parent[node] != node:
            node = parent[node]
        return node

    for row, col in pairs:
        parent[root(("row", row))] = root(("col", col))
    ids: dict = {}
    return [ids.setdefault(root(("row", row)), len(ids)) for row, _ in pairs]


def cooperation_rate(bots: tuple[str, ...], cells: dict[tuple[str, str], tuple[str, str]],
                     row: Strategy, col: Strategy) -> Fraction:
    """Pr[(C, C)] when the row bot is drawn from `row` and the column bot from `col`."""
    return sum((p * q for a, p in zip(bots, row) for b, q in zip(bots, col)
                if tuple(cells[(a, b)]) == ("C", "C")), Fraction(0))


def analyse(bots: tuple[str, ...], cells: dict[tuple[str, str], tuple[str, str]], A: Matrix,
            pairs: list[Pair]) -> list[Equilibrium]:
    """Check the extreme equilibria `pairs` of (A, Aᵀ), then classify them (steps 2 to 5).

    `cells[(a, b)]` is (a's action, b's action), the action pairs A was made from.
    """
    n = len(bots)
    if len(A) != n:
        raise ValueError(f"{n} bots but A is {len(A)} x {len(A)}")
    pairs = sorted(pairs)
    index = {p: k for k, p in enumerate(pairs)}
    if len(index) != len(pairs):
        raise ValueError("an equilibrium is listed twice")
    for row, col in pairs:
        _check_strategy(row, n)
        _check_strategy(col, n)
        if not is_equilibrium(A, row, col):
            raise ValueError(f"not an equilibrium of A: {row}, {col}")
    unmirrored = [p for p in pairs if (p[1], p[0]) not in index]
    if unmirrored:
        raise ValueError(f"the mirror of {unmirrored[0]} is missing: the list is incomplete")
    pure = [tuple(Fraction(int(i == k)) for i in range(n)) for k in range(n)]
    missing = [(x, y) for x in pure for y in pure if is_equilibrium(A, x, y) and (x, y) not in index]
    if missing:
        raise ValueError(f"the pure equilibrium {missing[0]} is missing: the list is incomplete")
    if not any(row == col for row, col in pairs):
        raise ValueError("no symmetric equilibrium, which every symmetric game has (Nash 1951)")
    component = components(pairs)
    return [Equilibrium(row=row, col=col, row_payoff=payoff(A, row, col),
                        col_payoff=payoff(A, col, row), symmetric=row == col,
                        mirror=index[(col, row)], component=component[k],
                        cooperation=cooperation_rate(bots, cells, row, col))
            for k, (row, col) in enumerate(pairs)]
