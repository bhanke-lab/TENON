"""
Diff harness: compare match_all() predictions against answer_key.csv ground truth.

Partial-fixture-aware: only diffs thicknesses present in answer_key.csv.

Usage:
    python tests/check_match.py tests/fixtures/sma_2026-04-27
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.parse_runsetup import load_runsetup
from src.parse_products import load_products
from src.match import load_mapping, match_all


def load_answer_key(path: Path):
    keys = set()
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            keys.add(
                (
                    row["thick"].strip(),
                    row["grade"].strip(),
                    row["color"].strip(),
                    row["width_token"].strip(),
                    row["length_token"].strip(),
                )
            )
    return keys


def get(p, *names, default=""):
    """Read attribute or dict key, trying multiple names."""
    for n in names:
        if isinstance(p, dict) and n in p:
            return p[n]
        if hasattr(p, n):
            return getattr(p, n)
    return default


def product_key(p):
    return (
        str(get(p, "thick")),
        str(get(p, "grade")),
        str(get(p, "color")),
        str(get(p, "width_token", "width")),
        str(get(p, "length_token", "length")),
    )


def main(fixture_dir: Path):
    runsetup_path = fixture_dir / "runsetup.csv"
    answer_key_path = fixture_dir / "answer_key.csv"
    mapping_path = ROOT / "mapping.yaml"

    # Resolve catalog: prefer shared _catalogs/ via catalog.txt; fall back to
    # legacy per-fixture allproducts.xml so unmigrated fixtures still work.
    catalog_pointer = fixture_dir / "catalog.txt"
    legacy_xml = fixture_dir / "allproducts.xml"
    if catalog_pointer.exists():
        catalog_name = catalog_pointer.read_text(encoding="utf-8").strip()
        products_path = fixture_dir.parent / "_catalogs" / catalog_name
        if not products_path.exists():
            sys.exit(
                f"catalog.txt points to '{catalog_name}' but "
                f"{products_path} does not exist."
            )
    elif legacy_xml.exists():
        products_path = legacy_xml
    else:
        sys.exit(
            f"No catalog found for {fixture_dir.name}: "
            f"expected either catalog.txt or allproducts.xml."
        )
        
    runsetup = load_runsetup(runsetup_path)
    products = load_products(products_path)
    mapping = load_mapping(mapping_path)
    results, _w_unmapped, _l_unmapped, predicted = match_all(runsetup, products, mapping)

    predicted_keys = {
        (p.thick, p.grade, p.color, p.width_token, p.length_token)
        for p in predicted.values()
    }

    if not answer_key_path.exists():
        print(f"No answer_key.csv at {answer_key_path}")
        print(f"Predicted {len(predicted_keys)} unique products. Cannot diff.")
        return

    answer_key = load_answer_key(answer_key_path)
    documented = {k[0] for k in answer_key}

    pred_in_scope = {p for p in predicted_keys if p[0] in documented}
    correct = pred_in_scope & answer_key
    extra   = pred_in_scope - answer_key
    missing = answer_key - pred_in_scope

    print(f"Fixture:                {fixture_dir.name}")
    print(f"Documented thicknesses: {sorted(documented)}  (others ignored)")
    print(f"Answer key:             {len(answer_key)} active products")
    print(f"Predicted (in scope):   {len(pred_in_scope)}")
    print(f"  ✓ Correct:            {len(correct)}")
    print(f"  ✗ Extra:              {len(extra)}  (predicted but NOT active)")
    print(f"  ✗ Missing:            {len(missing)}  (active but NOT predicted)")
    print()

    def dump(label, s):
        if not s:
            return
        print(f"=== {label} ===")
        for p in sorted(s):
            print(f"  {p[0]:5} {p[1]:18} {p[2]:6} w={p[3]:18} l={p[4]}")
        print()

    dump("EXTRA (false positives)", extra)
    dump("MISSING (false negatives)", missing)
    if not extra and not missing:
        print(" Perfect match across documented thicknesses.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tests/check_match.py <fixture_dir>")
        sys.exit(1)

    main(Path(sys.argv[1]).resolve())