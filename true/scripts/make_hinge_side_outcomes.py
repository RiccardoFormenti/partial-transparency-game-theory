"""Derive true/data/hinge_side_outcomes.json from copy's hand-typed HINGE_SIDE_PAIRS.

Usage (from the project root, after make_full_transparency_table.py):
  python true/scripts/make_hinge_side_outcomes.py copy/app/src/pd_runner/eval/sprime_floors.py \
      true/data/full_transparency_outcome_table.json true/data/hinge_side_outcomes.json

Keeps one entry per hinge cell of full_transparency_outcome_table.json, oriented like
that table's entry, with its floor-side value alongside for cross-checking.
"""
import hashlib
import json
import sys
from pathlib import Path

floors_src, table_path, dst = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(floors_src.parents[2]))  # .../app/src
from pd_runner.eval.sprime_floors import HINGE_SIDE_PAIRS  # noqa: E402

table = json.loads(table_path.read_text(encoding="utf-8"))
entries = []
for f in table["floors"]:
    d = f["dichotomy"]
    assert d == f"dich_{f['left_bot']}_vs_{f['right_bot']}", d
    entries.append({"dichotomy": d, "left_bot": f["left_bot"], "right_bot": f["right_bot"],
                    "floor_side": f["pair"], "hinge_side": list(HINGE_SIDE_PAIRS[d])})

out = {
    "provenance": {
        "derived_from": "copy/app/src/pd_runner/eval/sprime_floors.py (HINGE_SIDE_PAIRS)",
        "source_sha256": hashlib.sha256(floors_src.read_bytes()).hexdigest(),
        "note": "Typed by hand in the original code from the Lean dich_ statements "
                "(arith/, not available); NOT machine-checked against Lean here. "
                "Kept: the 18 dichotomies of full_transparency_outcome_table.json. "
                "Pairs are read from left_bot's side; floor_side repeats the table's value.",
    },
    "hinge_cells": entries,
}
dst.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"{len(entries)} hinge cells written")
