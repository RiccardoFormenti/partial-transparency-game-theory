"""Derive true/data/partial_transparency_bit_table.json from the S' Lean tau export.

Usage (from the project root):
  python true/scripts/make_partial_transparency_table.py \
      copy/app/generated/sprime_tau_rows.json true/data/partial_transparency_bit_table.json

Merges each template's `rows[].bits` (theorem bits) and its `floor_bits` into one
16-slot row, flagging floor bits. Drops only fields that are derivable:
`rows[].order` (the row's non-floor slots, in paper order) and `floor_bits[].module`
(always the row's module). Replaces the (now invalid) `source_digest` with a
`provenance` block pointing at the original file.
"""
import hashlib
import json
import sys
from pathlib import Path

src, dst = Path(sys.argv[1]), Path(sys.argv[2])

# Slot -> zoo bot, from pd_runner.tau.def4_theorems (LEAN_SLOT ∘ TEMPLATE_OF_BOT).
BOT_NAMES = {
    "coop": "CooperateBot", "defect": "DefectBot", "tftSim": "TitForTatBot",
    "dupoc": "DupocBot", "ebot": "EBot", "obot": "OBot", "dbot": "DBot",
    "cupodTroll": "CupodTrollBot", "dupocTroll": "DupocTrollBot", "cupod": "CupodBot",
    "dimcid": "DIMCID", "cimcic": "CIMCIC", "dimdid": "DIMDID", "prudent": "PrudentBot",
    "maxconfidence": "MaxConfidenceBot", "minconfidence": "MinConfidenceBot",
}

raw = src.read_bytes()
data = json.loads(raw)
order = data["order"]
assert sorted(order) == sorted(BOT_NAMES)
rows = {r["template"]: r for r in data["rows"]}
floors = {(f["template"], f["slot"]): f for f in data["floor_bits"]}
assert len(rows) == len(data["rows"]) and len(floors) == len(data["floor_bits"])

table = []
for tmpl in order:
    row = rows[tmpl]
    theorem_slots = [s for s in order if s in row["bits"]]
    assert row["order"] == "[" + ", ".join(theorem_slots) + "]", tmpl
    bits = {}
    for slot in order:
        fb = floors.get((tmpl, slot))
        if slot in row["bits"]:
            assert fb is None, (tmpl, slot)
            bits[slot] = {"action": row["bits"][slot], "floor": False}
        else:
            assert fb is not None, (tmpl, slot)
            assert fb["module"] == row["module"], (tmpl, slot)
            bits[slot] = {"action": fb["action"], "floor": True, "name": fb["name"],
                          "dichotomy": fb["dichotomy"], "hinge": fb["hinge"]}
    table.append({"template": tmpl, "bot": BOT_NAMES[tmpl], "name": row["name"],
                  "module": row["module"], "bits": bits})

out = {
    "system": data["system"],
    "schema_version": data["schema_version"],
    "provenance": {
        "derived_from": "copy/app/generated/sprime_tau_rows.json",
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_digest": data["source_digest"],
        "changes": [
            "rows[].bits and floor_bits merged into one 16-slot row per template; "
            "floor bits flagged with floor=true and keep name, dichotomy, hinge",
            "dropped rows[].order: always the row's non-floor slots in `order`",
            "dropped floor_bits[].module: always equal to its row's module",
            "added `bot` (zoo bot name per template), taken from "
            "pd_runner.tau.def4_theorems, not from the Lean export",
        ],
        "note": "source_digest is the Lean export's digest of the ORIGINAL file; "
                "it does not validate this derived file.",
    },
    "order": order,
    "rows": table,
}

# Pretty-print, but keep each bit on one line so a row reads as a table.
marks = {}
for row in table:
    for slot, bit in row["bits"].items():
        key = f"@@{row['template']}/{slot}@@"
        marks[json.dumps(key)] = json.dumps(bit, ensure_ascii=False)
        row["bits"][slot] = key
text = json.dumps(out, indent=2, ensure_ascii=False)
for key, bit in marks.items():
    text = text.replace(key, bit)
dst.write_text(text + "\n", encoding="utf-8")
print(f"{len(table)} rows x {len(order)} bits, "
      f"{sum(b['floor'] for b in map(json.loads, marks.values()))} floor bits")
