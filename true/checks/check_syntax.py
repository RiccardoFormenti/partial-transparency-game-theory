"""Check replication/partial_transparency/syntax.py against copy's tau/syntax.py.

Usage (from the project root):  python true/checks/check_syntax.py
"""

import itertools
import re
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "true"), str(ROOT / "copy" / "app" / "src")]

from pd_runner.tau import syntax as original  # noqa: E402
from pd_runner.tau.matrix import get_zoo  # noqa: E402
from replication.general.zoo import SIDES, ZOOS, load_zoo  # noqa: E402
from replication.partial_transparency import syntax  # noqa: E402

warnings.simplefilter("ignore")
failures = 0


def check(ok: bool) -> str:
    global failures
    failures += not ok
    return "OK" if ok else "FAIL"


def canonical(node) -> tuple:
    return (node.label, tuple(canonical(c) for c in node.children))


defined = sorted({m for path in syntax.BOTS_DIR.rglob("*.lean")
                  for m in re.findall(r"^def\s+(\w+)", syntax._strip_comments(path.read_text()),
                                      re.MULTILINE)})
trees, unreadable = {}, {}
for n in defined:
    try:
        trees[n] = syntax.bot_tree(n)
    except ValueError as e:
        unreadable[n] = str(e)
names = sorted(trees)
in_zoos = {b for bots in ZOOS.values() for b in bots}
print(f"1. {len(names)} of the {len(defined)} definitions in data/bots parse, to the original's "
      f"trees: {check(all(trees[n] == canonical(original.bot_ast(n)) for n in names))}")
for n, err in unreadable.items():
    try:
        theirs = f"the original parses it as {canonical(original.bot_ast(n))}"
    except ValueError as e:
        theirs = f"the original rejects it too ({e})"
    print(f"   not parsed: {err}; {theirs}; in a zoo: {check(n not in in_zoos) and 'no'}")

pairs = list(itertools.combinations_with_replacement(names, 2))
ted = {(a, b): syntax.tree_edit_distance(trees[a], trees[b]) for a, b in pairs}
print(f"2. Tree edit distance equals the original's Zhang–Shasha on all {len(pairs)} pairs:",
      check(all(ted[(a, b)] == original.tree_edit_distance(original.bot_ast(a),
                                                            original.bot_ast(b))
                for a, b in pairs)))

dist = {**ted, **{(b, a): d for (a, b), d in ted.items()}}
broken = sum(dist[(a, c)] > dist[(a, b)] + dist[(b, c)]
             for a, b, c in itertools.product(names, repeat=3))
norm = {k: d / max(syntax.size(trees[k[0]]), syntax.size(trees[k[1]])) for k, d in dist.items()}
broken_norm = sum(norm[(a, c)] > norm[(a, b)] + norm[(b, c)] + 1e-12
                  for a, b, c in itertools.product(names, repeat=3))
print(f"3. Raw distance satisfies the triangle inequality: {check(broken == 0)}; the "
      f"normalized one fails it on {broken_norm} of {len(names) ** 3} triples "
      "(the paper calls it a pseudo-distance)")

print("4. Malformed sources: rejected here / accepted by the original")
params, source = syntax.bot_definition("CIMCIC")
for label, bad in {"typo .slf for .self": source.replace(".self", ".slf", 1),
                   "unknown action Action.X": source.replace("Action.C", "Action.X", 1),
                   "missing argument": source.replace("(.const Action.D)", "", 1)}.items():
    try:
        syntax.parse(bad, "CIMCIC", params)
        mine = "accepted"
    except ValueError:
        mine = "rejected"
    try:
        theirs = f"accepted as {canonical(original.parse_prog(bad, 'CIMCIC'))}" \
            if canonical(original.parse_prog(bad, "CIMCIC")) != trees["CIMCIC"] else "accepted"
    except ValueError:
        theirs = "rejected"
    print(f"   {label:24s} {check(mine == 'rejected')} {mine} / {theirs}")

print("5. Zoo distance matrices equal the original's; syntactic twins")
for name in ZOOS:
    for side in SIDES:
        zoo = load_zoo(name, side)
        ref = get_zoo(name).load(source="sprime", floor_policy={"floor": "engine_side",
                                                                "hinge": "hinge_side"}[side])
        mine, theirs = syntax.syntactic_distances(zoo), original.syntactic_distance_matrix(ref)
        same = all(abs(mine[k] - theirs[k]) < 1e-12 for k in mine)
        print(f"   {name:22s} {side:5s} {check(same)}  twins: "
              f"{sorted(original.syntactic_twins(ref)) or 'none'}")

print("FAILED" if failures else "ALL OK")
sys.exit(1 if failures else 0)
