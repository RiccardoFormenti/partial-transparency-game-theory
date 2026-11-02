"""Derive true/data/full_transparency_outcome_table.json from the S' Lean export.

Usage (from the project root):
  python true/scripts/make_full_transparency_table.py \
      copy/app/generated/sprime_outcome_theorems.json true/data/full_transparency_outcome_table.json

Changes: drop every entry involving an excluded bot, drop the always-constant
`staggered`/`fuel_pad` fields, and replace the (now invalid) `source_digest`
with a `provenance` block pointing at the original file.
"""
import hashlib
import json
import sys
from pathlib import Path

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
EXCLUDED = ["MirrorBot", "WaryBot", "GuardianBot", "JustBot"]
DROPPED_FIELDS = ["staggered", "fuel_pad"]

raw = src.read_bytes()
data = json.loads(raw)
assert data["companions"] == [], "companions expected empty"


def keep(entry):
    return entry["left_bot"] not in EXCLUDED and entry["right_bot"] not in EXCLUDED


def strip(entry):
    for f in DROPPED_FIELDS:
        assert entry[f] in (False, 0), (entry["name"], f, entry[f])
    return {k: v for k, v in entry.items() if k not in DROPPED_FIELDS}


theorems = [strip(t) for t in data["theorems"] if keep(t)]
floors = [strip(f) for f in data["floors"] if keep(f)]

out = {
    "system": data["system"],
    "schema_version": data["schema_version"],
    "provenance": {
        "derived_from": "copy/app/generated/sprime_outcome_theorems.json",
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_digest": data["source_digest"],
        "excluded_bots": EXCLUDED,
        "dropped_fields": DROPPED_FIELDS,
        "note": "source_digest is the Lean export's digest of the ORIGINAL file; "
                "it does not validate this derived file.",
    },
    "theorems": theorems,
    "floors": floors,
    "companions": data["companions"],
}
dst.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"theorems {len(data['theorems'])} -> {len(theorems)}, "
      f"floors {len(data['floors'])} -> {len(floors)}")
