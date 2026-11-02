"""Check replication/general/zoo.py against the original loader, and its rejection of bad data.

Usage (from the project root):  python true/checks/check_zoo.py
"""

import copy
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "true"), str(ROOT / "copy" / "app" / "src")]

from pd_runner.tau.matrix import get_zoo  # noqa: E402
from replication.general import zoo  # noqa: E402

warnings.simplefilter("ignore")
POLICY = {"floor": "engine_side", "hinge": "hinge_side"}
failures = 0

print("1. Same cells, hinge cells, test bits and aggregators as copy's load_tau_matrix")
for name in zoo.ZOOS:
    for side in zoo.SIDES:
        mine = zoo.load_zoo(name, side)
        ref = get_zoo(name).load(source="sprime", floor_policy=POLICY[side])
        pairs = [(r, c) for r in mine.bots for c in mine.bots]
        diffs = {
            "bots": mine.bots != ref.bots,
            "cells": sum((mine.cells[k].row, mine.cells[k].col)
                         != (ref.cell(*k).row_action, ref.cell(*k).col_action) for k in pairs),
            "hinge cells": set(mine.hinge_cells) != set(ref.floor_cells),
            "test bits": sum(mine.action(*k) != ref.test_bit(*k) for k in pairs),
            "aggregators": sum(mine.aggregators[b] != ref.aggregator(b) for b in mine.bots),
        }
        bad = {k: v for k, v in diffs.items() if v}
        failures += bool(bad)
        print(f"   {name:22s} {side:5s} {'OK' if not bad else f'DIFFERS: {bad}'}")

print("2. Corrupted inputs are rejected")
real_read = zoo._read


def flip(a):
    return "D" if a == "C" else "C"


def corrupted(name, change):
    def read(n):
        data = copy.deepcopy(real_read(n))
        if n == name:
            change(data)
        return data
    return read


def flip_bit(d):
    bit = d["rows"][3]["bits"]["coop"]
    bit["action"] = flip(bit["action"])


CASES = {
    "flipped test bit": ("partial_transparency_bit_table.json", flip_bit),
    "proven bit on hinge cell": ("partial_transparency_bit_table.json",
                                 lambda d: d["rows"][3]["bits"]["dbot"].update(floor=False)),
    "hinge table out of sync": ("hinge_side_outcomes.json",
                                lambda d: d["hinge_cells"][0].update(floor_side=["C", "C"])),
    "missing hinge-side value": ("hinge_side_outcomes.json", lambda d: d["hinge_cells"].pop()),
    "duplicate ordered pair": ("full_transparency_outcome_table.json",
                               lambda d: d["theorems"].append(dict(d["theorems"][0]))),
    "asymmetric self-play": ("full_transparency_outcome_table.json", lambda d: [
        e.update(pair=["C", "D"]) for e in d["theorems"]
        if e["left_bot"] == e["right_bot"] == "DupocBot"]),
    "missing cell": ("full_transparency_outcome_table.json", lambda d: d.update(theorems=[
        e for e in d["theorems"] if {e["left_bot"], e["right_bot"]} != {"DBot", "OBot"}])),
}
for label, (name, change) in CASES.items():
    zoo._read = corrupted(name, change)
    try:
        zoo.load_zoo("body8", "floor")
        failures += 1
        print(f"   {label:26s} NOT REJECTED")
    except ValueError as e:
        print(f"   {label:26s} rejected: {e}")
zoo._read = real_read

print("FAILED" if failures else "ALL OK")
sys.exit(1 if failures else 0)
