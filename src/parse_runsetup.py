"""
Part of TENON (github.com/bhanke-lab/TENON).

parse_runsetup.py - Load a Baillie Run Set Up CSV into structured rows.

Phase 1 parses only the Lumber section. Cants, Ties, and Pallet sections
are read later.

Each Lumber row becomes a normalized record (LumberRow). The whole sheet
becomes a RunSetUp with metadata + the rows.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

# Baillie species name -> Comact species code. Extend as we hit new species.
SPECIES_MAP = {
    "Soft Maple": "SMA",
    "Hard Maple": "HMW",
    "Red Oak": "ROK",
    "White Oak": "WOK",
    "Cherry": "CHERRY",
    "Ash": "ASH",
    "Walnut": "WALNUT",
    "Tulip": "TUL",
    "Poplar": "TUL",
    "Yellow Poplar": "TUL",
    "Basswood": "BASSWOOD",
    "Birch": "BIRCH",
}


@dataclass
class LumberRow:
    destination: str
    thick: str
    sort: str
    grade_code: str
    color_code: str
    min_width_in: float
    min_length_ft: float
    max_length_ft: float
    price: float
    notes: str
    limit_pct: float | None
    sorts: int | None = None
    sticks: bool | None = None
    source_row: int | None = None


@dataclass
class RunSetUp:
    date: str
    species: str          # Comact code (SMA, HMW, etc.)
    species_raw: str      # original ("Soft Maple")
    log_volume: int | None
    targets: dict
    grade_targets: dict
    thickness_targets: dict
    lumber_rows: list = field(default_factory=list)


def load_runsetup(path):
    return load_runsetup_from_rows(_read_csv(Path(path)))

def load_runsetup_from_rows(rows):
    date = _find_label_value(rows, "Date:")
    species_raw = _find_label_value(rows, "Species:")
    species = SPECIES_MAP.get(species_raw, species_raw)
    log_volume_str = _find_label_value(rows, "Log Volume:")

    try:
        log_volume = int(log_volume_str)
    except (ValueError, TypeError):
        log_volume = None

    targets = _parse_target_block(rows, "Targets")
    grade_targets = _parse_target_block(rows, "Grade Targets")
    thickness_targets = _parse_target_block(rows, "Thickness Targets")
    lumber_rows = _parse_lumber_section(rows)

    return RunSetUp(
        date=date,
        species=species,
        species_raw=species_raw,
        log_volume=log_volume,
        targets=targets,
        grade_targets=grade_targets,
        thickness_targets=thickness_targets,
        lumber_rows=lumber_rows,
    )


def _read_csv(path):
    last_err = None
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            with path.open(newline="", encoding=enc) as f:
                return [[c.strip() for c in row] for row in csv.reader(f)]
        except UnicodeDecodeError as e:
            last_err = e
            continue
    raise last_err


def _find_label_value(rows, label):
    """
    Find the first cell containing `label`. Try, in order:
    (1) inline form "Label: value" in the same cell,
    (2) the next non-empty cell on the same row,
    (3) the cell directly below the label.
    """
    for r_idx, row in enumerate(rows):
        for i, cell in enumerate(row):
            if label in cell:
                # (1) inline "Label: value"
                if ":" in cell and cell.split(":", 1)[1].strip():
                    return cell.split(":", 1)[1].strip()
                # (2) next non-empty cell on the same row
                for nxt in row[i + 1:]:
                    if nxt:
                        return nxt
                # (3) cell directly below
                if r_idx + 1 < len(rows) and i < len(rows[r_idx + 1]):
                    below = rows[r_idx + 1][i].strip()
                    if below:
                        return below
    return ""


def _parse_target_block(rows, header):
    """
    Read a 2-column key/value block whose top-left cell matches header.
    The Run Set Up has three of these side-by-side: Targets, Grade Targets,
    Thickness Targets. Each is parsed independently.
    """
    result = {}
    header_col = None
    start_idx = None

    for r_idx, row in enumerate(rows):
        for c_idx, cell in enumerate(row):
            if cell == header:
                header_col = c_idx
                start_idx = r_idx + 1
                break
        if start_idx is not None:
            break

    if start_idx is None:
        return result

    for row in rows[start_idx:]:
        if header_col >= len(row):
            break

        key = row[header_col].strip()
        val = row[header_col + 1].strip() if header_col + 1 < len(row) else ""

        if not key:
            break

        pct = _parse_percent(val)
        if pct is None:
            break

        result[key] = pct

    return result


def _parse_lumber_section(rows):
    # Find the Lumber column-header row.
    header_idx = None
    for i, row in enumerate(rows):
        if row and row[0].strip() == "Destination":
            header_idx = i
            break

    if header_idx is None:
        return []

    headers = rows[header_idx]
    out = []
    last_destination = ""
    last_thick = ""
    last_sorts = None
    last_sticks = None
    last_sort = ""

    for r_idx in range(header_idx + 1, len(rows)):
        row = rows[r_idx]
        if not any(c for c in row):
            continue
        if row[0].strip() in {"Cants", "Ties", "Pallet"}:
            break

        def cell(name):
            return _cell_at(row, headers, name)

        destination = cell("Destination") or last_destination
        thick = cell("Thickness") or last_thick
        sort = cell("Sort") or last_sort
        sorts_str = cell("Sorts")
        sticks_str = cell("Sticks")
        sorts = int(sorts_str) if sorts_str.isdigit() else last_sorts
        sticks = (sticks_str.upper() == "YES") if sticks_str else last_sticks
        grade_code = cell("Grade").upper()

        if not grade_code:
            continue

        out.append(LumberRow(
            destination=destination,
            thick=thick,
            sort=sort,
            grade_code=grade_code,
            color_code=cell("Color").upper(),
            min_width_in=_parse_inches(cell("Min. Width")),
            min_length_ft=_parse_feet(cell("Min. Length")),
            max_length_ft=_parse_feet(cell("Max Length")),
            price=_parse_dollars(cell("Price")),
            notes=cell("Special Instruction/Comments"),
            limit_pct=_parse_percent(cell("Limit")),
            sorts=sorts,
            sticks=sticks,
            source_row=r_idx,
        ))

        last_destination = destination
        last_thick = thick
        last_sorts = sorts
        last_sticks = sticks
        last_sort = sort

    return out


def _cell_at(row, headers, header_name):
    try:
        idx = headers.index(header_name)
    except ValueError:
        return ""

    return row[idx].strip() if idx < len(row) else ""


def _parse_inches(s):
    s = s.replace('"', "").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


def _parse_feet(s):
    s = s.replace("'", "").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


def _parse_dollars(s):
    s = s.replace("$", "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


def _parse_percent(s):
    s = s.strip()
    if not s:
        return None

    try:
        if s.endswith("%"):
            return float(s[:-1].strip()) / 100.0

        f = float(s)
        return f / 100.0 if f > 1 else f
    except ValueError:
        return None


if __name__ == "__main__":
    import sys

    default = "tests/fixtures/sma_2026-04-27/runsetup.csv"
    path = sys.argv[1] if len(sys.argv) > 1 else default
    rs = load_runsetup(path)

    print(f"Loaded Run Set Up from {path}\n")
    print(f"Date:              {rs.date}")
    print(f"Species:           {rs.species_raw} -> {rs.species}")
    print(f"Log volume:        {rs.log_volume}")
    print(f"Targets:           {rs.targets}")
    print(f"Grade targets:     {rs.grade_targets}")
    print(f"Thickness targets: {rs.thickness_targets}")
    print()
    print(f"Lumber rows ({len(rs.lumber_rows)}):")
    for r in rs.lumber_rows:
        print(
            f"  {r.destination:8s} {r.thick:5s} {r.grade_code:3s} {r.color_code:8s}"
            f"  W>={r.min_width_in:>4} L={r.min_length_ft:>4}-{r.max_length_ft:<4}'"
            f"  ${r.price:<6}  limit={r.limit_pct}"
        )
        if r.notes:
            print(f"           notes: {r.notes}")