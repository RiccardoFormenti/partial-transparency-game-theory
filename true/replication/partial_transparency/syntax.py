"""Syntactic distance between bots (Appendix B.4.1).

Each bot's Lean source (data/bots) is parsed into its abstract syntax tree: the `Prog` and
`Formula` constructors as node labels, proof budgets erased, other bots as opaque leaves
(`ref:DefectBot`). The distance between two bots is the tree edit distance with unit insert,
delete and relabel costs, divided by the size of the larger tree.

Replicates copy/app/src/pd_runner/tau/syntax.py with a stricter parser: anything it does not
recognize raises, where the original silently drops unknown tokens (a typo such as `.slf`
for `.self` yields a wrong tree without an error). The tree edit distance is computed by the
plain recursion on rightmost roots rather than the original's Zhang–Shasha tables, so the two
check each other.
"""

from __future__ import annotations

import re
from functools import lru_cache

from ..general.zoo import DATA, Zoo

BOTS_DIR = DATA / "bots"

Tree = tuple[str, tuple["Tree", ...]]  # (label, children)

# Constructor arities; `.search` and `.box` take a proof budget first, which is erased.
ARITY = {".const": 1, ".self": 0, ".opp": 0, ".bot": 1, ".sim": 2, ".ite": 4, ".search": 4,
         ".plays": 3, ".impl": 2, ".neg": 1, ".box": 2, ".eq": 2, ".diag": 2}
BUDGET_FIRST = {".search", ".box"}

# The original multiplies the [0, 1] distance by 10. For 0 < t < 1 the calibration absorbs
# any factor, but t = 0 uses a fixed temperature, so the factor sets how close to uniform
# the opaque channel is. Kept for comparability.
SCALE = 10.0

_REF = re.compile(r"[A-Z][A-Za-z0-9]*")  # a bot name: references are capitalized
_BUDGET_OP = re.compile(r"[-+*/]|[0-9]+")  # as in (2 * k + 64)


def _strip_comments(text: str) -> str:
    """Remove `/- ... -/` blocks (which nest in Lean) and `--` line comments."""
    out, depth, i = [], 0, 0
    while i < len(text):
        if text.startswith("/-", i):
            depth, i = depth + 1, i + 2
        elif depth and text.startswith("-/", i):
            depth, i = depth - 1, i + 2
        else:
            if not depth:
                out.append(text[i])
            i += 1
    if depth:
        raise ValueError("unterminated block comment")
    return re.sub(r"--[^\n]*", "", "".join(out))


def bot_definition(name: str) -> tuple[tuple[str, ...], str]:
    """The budget parameters of `def <name>` (its `(k : Nat)` arguments) and its body: the
    text after `:=` up to the next top-level line."""
    pattern = re.compile(rf"^def\s+{re.escape(name)}(?![\w.'])", re.MULTILINE)
    found = []
    for path in sorted(BOTS_DIR.rglob("*.lean")):
        text = _strip_comments(path.read_text(encoding="utf-8"))
        for match in pattern.finditer(text):
            assign = text.index(":=", match.end())
            groups = re.findall(r"\(([^():]*):\s*Nat\s*\)", text[match.end():assign])
            end = re.compile(r"^\S", re.MULTILINE).search(text, assign)
            found.append((tuple(p for g in groups for p in g.split()),
                          text[assign + 2:end.start() if end else len(text)]))
    if len(found) != 1:
        raise ValueError(f"expected one `def {name}` under {BOTS_DIR}, found {len(found)}")
    return found[0]


def parse(source: str, name: str, params: tuple[str, ...] = ()) -> Tree:
    """The syntax tree of one bot body. `params` are its budget variables; `name` labels a
    reference to itself."""
    tokens = re.findall(r"\(|\)|[^\s()]+", source)
    pos = 0

    def peek() -> str | None:
        return tokens[pos] if pos < len(tokens) else None

    def take(expected: str | None = None) -> str:
        nonlocal pos
        tok = peek()
        if tok is None:
            raise ValueError(f"{name}: unexpected end of term")
        if expected is not None and tok != expected:
            raise ValueError(f"{name}: expected {expected!r}, found {tok!r}")
        pos += 1
        return tok

    def ref(tok: str) -> Tree:
        return ("ref:self-recursive" if tok == name else f"ref:{tok}", ())

    def skip_budget() -> None:
        """Consume one budget: a parameter, a numeral, or a parenthesized expression."""
        tok = take()
        if tok != "(":
            if tok not in params and not tok.isdigit():
                raise ValueError(f"{name}: {tok!r} is not a budget")
            return
        depth = 1
        while depth:
            tok = take()
            if tok in ("(", ")"):
                depth += 1 if tok == "(" else -1
            elif tok not in params and not _BUDGET_OP.fullmatch(tok):
                raise ValueError(f"{name}: {tok!r} in a budget expression")

    def term() -> Tree:
        tok = take()
        if tok == "(":
            nxt = peek() or ""
            if _REF.fullmatch(nxt) and nxt not in params:  # `(CupodBot k)`: a reference
                leaf = ref(take())
                while peek() != ")":
                    skip_budget()
            else:
                leaf = term()
            take(")")
            return leaf
        if tok in ("Action.C", "Action.D"):
            return (f"action:{tok[-1]}", ())
        if tok in ARITY:
            n = ARITY[tok]
            if tok in BUDGET_FIRST:
                skip_budget()
                n -= 1
            return (tok[1:], tuple(term() for _ in range(n)))
        if _REF.fullmatch(tok) and tok not in params:
            return ref(tok)
        raise ValueError(f"{name}: unrecognized token {tok!r}")

    tree = term()
    if pos != len(tokens):
        raise ValueError(f"{name}: trailing tokens {tokens[pos:pos + 6]}")
    return tree


@lru_cache(maxsize=None)
def bot_tree(name: str) -> Tree:
    params, body = bot_definition(name)
    return parse(body, name, params)


def size(tree: Tree) -> int:
    return 1 + sum(size(c) for c in tree[1])


def tree_edit_distance(a: Tree, b: Tree) -> int:
    """Minimum number of node inserts, deletes and relabels turning tree a into tree b."""

    @lru_cache(maxsize=None)
    def forests(f: tuple[Tree, ...], g: tuple[Tree, ...]) -> int:
        # Compare the rightmost trees of the two forests: delete its root, insert the
        # other's root, or match the two roots and their subforests.
        if not f and not g:
            return 0
        if not g:
            return forests(f[:-1] + f[-1][1], g) + 1
        if not f:
            return forests(f, g[:-1] + g[-1][1]) + 1
        (fl, fc), (gl, gc) = f[-1], g[-1]
        return min(forests(f[:-1] + fc, g) + 1,
                   forests(f, g[:-1] + gc) + 1,
                   forests(fc, gc) + forests(f[:-1], g[:-1]) + (fl != gl))

    return forests((a,), (b,))


def syntactic_distances(zoo: Zoo) -> dict[tuple[str, str], float]:
    """SCALE · ted / larger size, for every pair of zoo members.

    MaxConfidenceBot and MinConfidenceBot have no source of their own: as hypotheses they
    are DupocBot (`Zoo.presents_as`), so they get DupocBot's tree.
    """
    trees = {b: bot_tree(zoo.presents_as[b]) for b in zoo.bots}
    out = {}
    for a in zoo.bots:
        for b in zoo.bots:
            if (b, a) in out:
                out[(a, b)] = out[(b, a)]
            else:
                ta, tb = trees[a], trees[b]
                out[(a, b)] = SCALE * tree_edit_distance(ta, tb) / max(size(ta), size(tb))
    return out
