"""Load a zoo: its bots, their full-transparency outcomes, and the lifted bots' test bits.

Inputs (all in `data/`):
  full_transparency_outcome_table.json  outcome(L, R) per Lean theorem; hinge cells hold
                                        their floor-side value
  hinge_side_outcomes.json              the other value of each hinge cell (hand-typed in
                                        the original code, not checked against Lean)
  partial_transparency_bit_table.json   the lifted bots' test bits, proven in Lean

A zoo is loaded on one SIDE: "floor" (every hinge search fails, the paper's main results)
or "hinge" (every hinge search succeeds, Appendix D.2 and D.3.3).

The test bit of a lifted bot X at hypothesis Y is X's own action against Y (Proposition 25),
so the cell table is all the next steps need. The bit table is used only to verify that, and
to record where each bit comes from (`Zoo.bit_sources`).

MaxConfidenceBot and MinConfidenceBot (Appendix D.3.2) use DupocBot's test with another
aggregator. As opponents they are treated as DupocBot: their cells are copies of DupocBot's.

Usage (from true/):  python -m replication.general.zoo <zoo> <side>     e.g.  ... body8 floor
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data"

# The paper's zoos (Figure 2). Keys match the original code's, so runs can be compared.
BODY8 = ("CooperateBot", "CupodBot", "DBot", "DefectBot", "DupocBot", "EBot", "OBot",
         "TitForTatBot")
ZOOS: dict[str, tuple[str, ...]] = {
    "nonprovers+dupoc": tuple(b for b in BODY8 if b != "CupodBot"),
    "body8": BODY8,
    "body8+trolls": tuple(sorted(BODY8 + ("CupodTrollBot", "DupocTrollBot"))),
    "body8+trolls+provers": tuple(sorted(
        BODY8 + ("CupodTrollBot", "DupocTrollBot", "CIMCIC", "DIMDID"))),
    "body8+natives": tuple(sorted(BODY8 + ("MaxConfidenceBot", "MinConfidenceBot"))),
}

# Bots that aggregate DupocBot's test differently; every other bot sums ("sum").
NATIVE_AGGREGATORS = {"MaxConfidenceBot": "max", "MinConfidenceBot": "min"}

SIDES = ("floor", "hinge")

# Lean proves DupocBot vs CupodBot outright (Theorem 24), but the lifted bots' bits for this
# pair only on the floor side. The only place a floor bit may sit on a non-hinge cell.
PROVEN_CELL_WITH_FLOOR_BITS = ({"DupocBot", "CupodBot"}, "outcome_DupocBot_vs_CupodBot")


@dataclass(frozen=True)
class Cell:
    """outcome(row bot, column bot), read from the row bot's side."""

    row: str  # the row bot's action, "C" or "D"
    col: str  # the column bot's action
    theorem: str  # the Lean theorem the value comes from
    hinge: bool  # True when the value depends on the side


@dataclass(frozen=True)
class Zoo:
    name: str
    side: str
    bots: tuple[str, ...]
    cells: dict[tuple[str, str], Cell]
    aggregators: dict[str, str]  # bot -> "sum" | "max" | "min"
    presents_as: dict[str, str]  # bot -> the bot it is treated as when it is the opponent
    bit_sources: dict[tuple[str, str], str]  # (actor, hypothesis) -> where the bit comes from

    def action(self, actor: str, opponent: str) -> str:
        """What `actor` plays against `opponent`; also `actor`'s test bit at `opponent`."""
        return self.cells[(actor, opponent)].row

    @property
    def hinge_cells(self) -> tuple[tuple[str, str], ...]:
        return tuple(k for k, c in self.cells.items() if c.hinge)


def _read(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def _stated_cells(side: str) -> dict[tuple[str, str], Cell]:
    """Every ordered pair the outcome table states, with hinge cells set to `side`."""
    table = _read("full_transparency_outcome_table.json")
    other = {h["dichotomy"]: h for h in _read("hinge_side_outcomes.json")["hinge_cells"]}
    if len(other) != len(table["floors"]):
        raise ValueError(f"{len(table['floors'])} hinge cells but {len(other)} hinge-side values")
    stated: dict[tuple[str, str], Cell] = {}
    for entry in table["theorems"] + table["floors"]:
        key = (entry["left_bot"], entry["right_bot"])
        if key in stated:
            raise ValueError(f"{key} is stated twice ({stated[key].theorem}, {entry['name']})")
        pair = tuple(entry["pair"])
        is_hinge = "dichotomy" in entry
        if is_hinge:
            h = other[entry["dichotomy"]]
            if (h["left_bot"], h["right_bot"]) != key or tuple(h["floor_side"]) != pair:
                raise ValueError(f"hinge-side entry {entry['dichotomy']} does not match the table")
            if side == "hinge":
                pair = tuple(h["hinge_side"])
        stated[key] = Cell(pair[0], pair[1], entry["name"], is_hinge)
    return stated


def _zoo_cells(bots: tuple[str, ...], presents_as: dict[str, str], side: str
               ) -> dict[tuple[str, str], Cell]:
    """The ordered cell table over `bots`, read in whichever orientation the table states."""
    stated = _stated_cells(side)
    cells = {}
    for r in bots:
        for c in bots:
            br, bc = presents_as[r], presents_as[c]
            fwd, rev = stated.get((br, bc)), stated.get((bc, br))
            if fwd is None and rev is None:
                raise ValueError(f"no outcome stated for {br} vs {bc}")
            if fwd is not None and rev is not None and br != bc and (
                    (fwd.row, fwd.col) != (rev.col, rev.row) or fwd.hinge != rev.hinge):
                raise ValueError(f"{fwd.theorem} and {rev.theorem} disagree")
            cell = fwd if fwd is not None else Cell(rev.col, rev.row, rev.theorem, rev.hinge)
            if br == bc and cell.row != cell.col:
                raise ValueError(f"{cell.theorem}: self-play must be symmetric")
            cells[(r, c)] = cell
    return cells


def _bit_sources(bots: tuple[str, ...], cells: dict[tuple[str, str], Cell],
                 presents_as: dict[str, str], side: str) -> dict[tuple[str, str], str]:
    """Check every test bit against its cell; return where each bit comes from."""
    rows = {r["bot"]: r for r in _read("partial_transparency_bit_table.json")["rows"]}
    slot = {r["bot"]: r["template"] for r in rows.values()}
    pair, theorem = PROVEN_CELL_WITH_FLOOR_BITS
    sources = {}
    for actor in bots:
        for hyp in bots:
            bit, cell = rows[actor]["bits"][slot[hyp]], cells[(actor, hyp)]
            if bit["floor"] and not cell.hinge:
                if {presents_as[actor], presents_as[hyp]} != pair or bit["dichotomy"] != theorem:
                    raise ValueError(f"floor bit on the proven cell {actor} vs {hyp}")
                source = "floor bit, proven cell"
            elif cell.hinge and not bit["floor"]:
                raise ValueError(f"proven bit on the hinge cell {actor} vs {hyp}")
            elif cell.hinge and side == "hinge":
                # Lean states only the floor-side bit; the value is the hinge-side cell's.
                sources[(actor, hyp)] = "hinge side, no Lean bit"
                continue
            else:
                source = "floor bit" if bit["floor"] else "theorem"
            if bit["action"] != cell.row:
                raise ValueError(f"bit {actor} at {hyp} is {bit['action']}, cell says {cell.row}")
            sources[(actor, hyp)] = source
    return sources


def load_zoo(name: str, side: str) -> Zoo:
    if name not in ZOOS:
        raise ValueError(f"unknown zoo {name!r}; choose one of {sorted(ZOOS)}")
    if side not in SIDES:
        raise ValueError(f"unknown side {side!r}; choose one of {SIDES}")
    bots = ZOOS[name]
    presents_as = {b: "DupocBot" if b in NATIVE_AGGREGATORS else b for b in bots}
    cells = _zoo_cells(bots, presents_as, side)
    return Zoo(
        name=name,
        side=side,
        bots=bots,
        cells=cells,
        aggregators={b: NATIVE_AGGREGATORS.get(b, "sum") for b in bots},
        presents_as=presents_as,
        bit_sources=_bit_sources(bots, cells, presents_as, side),
    )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("zoo", choices=sorted(ZOOS))
    p.add_argument("side", choices=SIDES)
    args = p.parse_args()
    zoo = load_zoo(args.zoo, args.side)
    width = max(map(len, zoo.bots))
    print(f"{zoo.name}, {zoo.side} side: row bot's action first, * = hinge cell")
    for r in zoo.bots:
        cells = (zoo.cells[(r, c)] for c in zoo.bots)
        print(f"{r:{width}s}  " + " ".join(c.row + c.col + ("*" if c.hinge else " ") for c in cells))
    print("bit sources:", dict(Counter(zoo.bit_sources.values())))


if __name__ == "__main__":
    main()
