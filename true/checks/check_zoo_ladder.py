"""Check the saved zoo ladder (results/zoo_ladder/floor/): its body8 files are those of
results/full_transparency/body8/floor/, its zoos are nested, ladder.json agrees with each
zoo's files and horizon, and its Nash columns against the paper's Table 8.

Usage (from the project root):  python true/checks/check_zoo_ladder.py
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "true")]

from replication.full_transparency.nash import RESULTS as FULL  # noqa: E402
from replication.full_transparency.zoo_ladder import (HORIZONS, LADDER, RESULTS,  # noqa: E402
                                                      ladder_row)
from replication.general.replicator import HORIZON  # noqa: E402

FILES = ("equilibria.json", "lrsnash_input.txt", "lrsnash_output.txt", "replicator.json",
         "replicator_runs.csv")
TIMING = re.compile(r"\*\d+\.\d+u ")  # lrsnash's resource-use line, which changes every run
PAPER = {  # Table 8: the number of components, and the fully cooperative component's bots
    "nonprovers+dupoc": (3, ["CooperateBot", "DupocBot", "TitForTatBot"]),
    "body8": (3, ["CooperateBot", "DupocBot", "TitForTatBot"]),
    "body8+trolls": (3, ["CooperateBot", "DupocBot", "TitForTatBot"]),
    "body8+trolls+provers": (3, ["CIMCIC", "CooperateBot", "DupocBot", "TitForTatBot"]),
}
LADDER_DIR = RESULTS / "floor"
failures = 0


def check(ok: bool, text: str) -> None:
    global failures
    failures += not ok
    print(f"  {'OK  ' if ok else 'FAIL'} {text}")


def lines(path: Path) -> list[str]:
    return [line for line in path.read_text().splitlines() if not TIMING.match(line)]


print("1. body8 in the ladder = results/full_transparency/body8/floor")
for name in FILES:
    new, old = lines(LADDER_DIR / "body8" / name), lines(FULL / "body8" / "floor" / name)
    diff = [i + 1 for i, (a, b) in enumerate(zip(new, old)) if a != b]
    if len(new) != len(old):
        check(False, f"{name}: {len(new)} lines, the old one {len(old)}")
    else:
        check(not diff, f"{name}: " + (f"{len(diff)} lines differ, first line {diff[0]}" if diff
                                       else "identical" + ", apart from the timing line"
                                       * (name == "lrsnash_output.txt")))

print("\n2. ladder.json agrees with each zoo's files, and the zoos are nested")
saved = json.loads((LADDER_DIR / "ladder.json").read_text())
check([r["zoo"] for r in saved["zoos"]] == list(LADDER), f"zoos in order: {', '.join(LADDER)}")
for row in saved["zoos"]:
    check(row == ladder_row(LADDER_DIR / row["zoo"]), f"{row['zoo']}: row = its files' row")
    horizon = HORIZONS.get(row["zoo"], HORIZON)
    check(row["replicator"]["horizon"] == horizon, f"{row['zoo']}: horizon {horizon:g}")
for inner, outer in zip(saved["zoos"], saved["zoos"][1:]):
    check(set(inner["bots"]) < set(outer["bots"]), f"{inner['zoo']} is inside {outer['zoo']}")

print("\n3. Nash columns against the paper's Table 8")
for row in saved["zoos"]:
    n = row["nash"]
    mine = (n["n_components"], n["cooperative_component"]["bots"])
    check(mine == PAPER[row["zoo"]], f"{row['zoo']}: {mine[0]} components, cooperative "
                                     f"component {mine[1]}; paper {PAPER[row['zoo']]}")

print("\nFAILED" if failures else "\nALL OK")
sys.exit(1 if failures else 0)
