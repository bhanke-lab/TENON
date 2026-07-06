"""
Part of TENON (github.com/bhanke-lab/TENON).

match.py - Match Run Set Up Lumber rows to Comact AllProducts entries
using the rules in mapping.yaml.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import yaml


def load_mapping(path):
    with Path(path).open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def match_for_row(row, products, run_species, mapping,
                  width_unmapped=None, length_unmapped=None,
                  apply_width_filter=False, apply_length_filter=False):
    """
    Return the subset of `products` satisfying this Lumber row.

    Hard constraints (always applied): species, thick, grade, color.
    Soft constraints (opt-in): width_band.min >= row.min_width_in,
                               length_band.min >= row.min_length_ft.

    The width/length tokens on Comact products describe which bin a board
    falls into, not whether the product is eligible for a destination.
    Activation is grade/color/thick/species driven; widths/lengths are
    plumbing inside the optimizer. Filters stay off by default until we
    confirm semantics against a labeled fixture.
    """
    allowed_grades = set(mapping["grade_map"].get(row.grade_code, []))
    # v0.15: species-specific grade exclusions. Some species never take a
    # destination the base grade_map lists (e.g. WALNUT PR -> never SEL OPT).
    for ex in (mapping.get("grade_map_species_exclude", {})
               .get(row.grade_code, {})
               .get(run_species, [])):
        allowed_grades.discard(ex)
    allowed_colors = set(mapping["color_map"].get(row.color_code, []))
    width_tokens = mapping["width_tokens"]
    length_tokens = mapping["length_tokens"]

    matches = []
    for p in products:
        if p.species != run_species:
            continue
        if p.thick != row.thick:
            continue
        if p.grade not in allowed_grades:
            continue
        if p.color not in allowed_colors:
            continue

        # Track unmapped tokens regardless of filter mode (for diagnostics).
        if p.width_token not in width_tokens and width_unmapped is not None:
            width_unmapped.add(p.width_token)
        if p.length_token not in length_tokens and length_unmapped is not None:
            length_unmapped.add(p.length_token)

        if apply_width_filter:
            wband = width_tokens.get(p.width_token)
            if wband is None or wband["min"] < row.min_width_in:
                continue

        if apply_length_filter:
            lband = length_tokens.get(p.length_token)
            if lband is None or lband["min"] < row.min_length_ft:
                continue

        matches.append(p)
    return matches

def apply_multi_destination_union(rows, products, run_species, mapping, predicted):
    """
    v0.8 rule: when 2+ rows at the same (thick, grade_code) specify different
    color_codes (e.g. one destination wants UNSEL, another SAP+BTR), activate
    ALL color variants present in catalog at that thick x grade x species.
    Mutates predicted (instance_id -> Product) in place; returns added IDs.
    """
    by_grade = defaultdict(set)
    for r in rows:
        by_grade[(r.thick, r.grade_code)].add(r.color_code)

    added = set()
    for (thick, grade_code), colors in by_grade.items():
        if len(colors) <= 1:
            continue
        allowed_grades = set(mapping["grade_map"].get(grade_code, []))
        # v0.15: honor species-specific grade exclusions here too, so the
        # union post-pass can't re-add an excluded destination (WALNUT SEL OPT).
        for ex in (mapping.get("grade_map_species_exclude", {})
                   .get(grade_code, {})
                   .get(run_species, [])):
            allowed_grades.discard(ex)
        for p in products:
            if p.species != run_species:
                continue
            if p.thick != thick:
                continue
            if p.grade not in allowed_grades:
                continue
            if p.instance_id not in predicted:
                predicted[p.instance_id] = p
                added.add(p.instance_id)
    return added
def apply_auto_activate(thicks_in_runsetup, products, run_species, mapping, predicted):
    """
    v0.8 rule: apply mapping["auto_activate"] entries. Each entry has
    grade (str), colors (list[str]), species ("ANY" or list[str]),
    thicknesses ("ANY" or list[str]).
    Only activates at thicknesses the run actually touches (so we don't
    light up 8/4 HMW FAS1W on a 4/4-only run).
    """
    added = set()
    for rule in mapping.get("auto_activate", []):
        species_scope = rule.get("species", "ANY")
        if species_scope != "ANY" and run_species not in species_scope:
            continue
        # v0.15: per-rule species blocklist, so an ANY rule can skip species
        # that deselect (e.g. TUL / BASSWOOD never auto-take 6/4 3ACOM).
        if run_species in rule.get("exclude_species", []):
            continue
        thick_scope = rule.get("thicknesses", "ANY")
        if thick_scope == "ANY":
            allowed_thicks = thicks_in_runsetup
        else:
            allowed_thicks = set(thick_scope) & thicks_in_runsetup
        rule_colors = set(rule["colors"])
        for p in products:
            if p.species != run_species:
                continue
            if p.thick not in allowed_thicks:
                continue
            if p.grade != rule["grade"]:
                continue
            if p.color not in rule_colors:
                continue
            if p.instance_id not in predicted:
                predicted[p.instance_id] = p
                added.add(p.instance_id)
    return added


def match_all(runsetup, products, mapping):
    """
    Returns (per_row_results, width_unmapped, length_unmapped, predicted).
    per_row_results keeps the row-by-row breakdown for diagnostic output.
    predicted is the v0.8 post-pass set (dict instance_id -> Product) used
    by check_match.py for the diff against the answer key. It includes
    products from row matches PLUS multi-destination union PLUS auto-activate
    rules; the latter two aren't tied to any single row.
    """
    width_unmapped = set()
    length_unmapped = set()
    out = []
    predicted = {}  # instance_id -> Product
    for row in runsetup.lumber_rows:
        ms = match_for_row(
            row,
            products,
            runsetup.species,
            mapping,
            width_unmapped=width_unmapped,
            length_unmapped=length_unmapped,
        )
        out.append((row, ms))
        for p in ms:
            predicted[p.instance_id] = p

    # v0.8 post-passes
    apply_multi_destination_union(
        runsetup.lumber_rows, products, runsetup.species, mapping, predicted
    )
    apply_auto_activate(
        {r.thick for r in runsetup.lumber_rows},
        products,
        runsetup.species,
        mapping,
        predicted,
    )
    return out, width_unmapped, length_unmapped, predicted


if __name__ == "__main__":
    import sys
    from parse_runsetup import load_runsetup
    from parse_products import load_products

    REPO_ROOT = Path(__file__).resolve().parent.parent

    # Default smoke-test fixture. Override with: python src/match.py <fixture-dir>
    fixture = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / "tests" / "fixtures" / "sma_2026-04-27"

    catalog_txt = (fixture / "catalog.txt").read_text().strip()
    runsetup_path = str(fixture / "runsetup.csv")
    products_path = str(REPO_ROOT / "tests" / "fixtures" / "_catalogs" / catalog_txt)
    mapping_path = str(REPO_ROOT / "mapping.yaml")

    rs = load_runsetup(runsetup_path)
    products = load_products(products_path)
    mapping = load_mapping(mapping_path)

    print(
        f"Run: {rs.species_raw} ({rs.species}), {rs.date}, "
        f"{len(rs.lumber_rows)} Lumber rows"
    )
    print(
        "Catalog: "
        f"{len(products)} total products, "
        f"{sum(1 for p in products if p.species == rs.species)} in {rs.species}\n"
    )

    results, w_unmapped, l_unmapped, predicted = match_all(rs, products, mapping)

    unique = {}

    for row, matches in results:
        header = (
            f"{row.destination:8s} {row.thick:5s} {row.grade_code:3s} "
            f"{row.color_code:8s}  W>={row.min_width_in:>4} "
            f"L>={row.min_length_ft:>4}'  -> {len(matches)} matches"
        )
        print(header)
        for p in matches:
            print(f"    [{p.instance_id}] {p.name}")
            unique[p.instance_id] = p.name
        print()

    # Products added by post-passes (auto-activate / multi-destination union)
    auto_added_ids = set(predicted) - set(unique)
    if auto_added_ids:
        print("Post-pass additions (auto-activate / multi-destination union):")
        for iid in sorted(auto_added_ids):
            p = predicted[iid]
            print(f"    [{iid}] {p.name}  <-- post-pass")
        print()

    print("=" * 70)
    print(f"From row matches:           {len(unique)}")
    print(f"After v0.8 post-passes:     {len(predicted)}")
    print("Target (4/27/26 SMA):       21")
    print("=" * 70)

    if w_unmapped:
        print(f"\nWidth tokens not in mapping.yaml: {sorted(w_unmapped)}")
    if l_unmapped:
        print(f"Length tokens not in mapping.yaml: {sorted(l_unmapped)}")

    # ----- diagnostic: show every product available for this species -----
    species_filter = "SMA"
    print()
    print("=" * 70)
    print(f"Catalog dump: all {species_filter} products grouped by thick → grade")
    print("=" * 70)
    by_thick = defaultdict(list)
    for p in products:
        if p.species == species_filter:
            by_thick[p.thick].append(p)
    for thick in sorted(by_thick.keys()):
        plist = by_thick[thick]
        print(f"\n--- {thick} ({len(plist)} products) ---")
        for p in sorted(plist, key=lambda x: (x.grade, x.color, x.width_token)):
            print(
                f"  [{p.instance_id}] {p.grade:25} {p.color:6} "
                f"w={p.width_token:15} l={p.length_token:15}  {p.name}"
            )