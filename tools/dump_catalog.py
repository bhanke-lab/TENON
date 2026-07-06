"""
Dump the full Comact product catalog grouped by species → thickness → grade.

Permanent fixture-onboarding + diagnostic tool. Run this whenever:
  - A new fixture's answer key surfaces a product you don't recognize
    ("does this even exist in catalog?").
  - You suspect catalog drift (something active on the live Comact that
    isn't in AllProducts.xml - see FAS OPT Unsel HMW gap, 2026-05-05).
  - You want a per-(species × thickness × grade) sanity check before
    writing a new auto_activate rule in mapping.yaml.

Output sections:
  - TOTAL counts (products / grades / colors / thicknesses).
  - Per-species counts.
  - Grade × species matrix (catches "FAS OPT × HMW = 0 at every thickness"
    type structural gaps).
  - Per-species dump grouped by thickness, sorted by grade then color.

Usage:
  python tools/dump_catalog.py
  python tools/dump_catalog.py --species HMW
  python tools/dump_catalog.py --catalog tests/fixtures/_catalogs/allproducts_2026-05-06.xml
  python tools/dump_catalog.py tests/fixtures/_catalogs/allproducts_2026-05-06.xml

Reads the latest catalog from tests/fixtures/_catalogs/ by default
(globs allproducts_*.xml, takes the lex-max).
"""

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Make `from src...` work no matter where this is invoked from.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.parse_products import load_products  # noqa: E402

CATALOGS_DIR = REPO_ROOT / "tests" / "fixtures" / "_catalogs"

def latest_catalog() -> Path:
    candidates = sorted(CATALOGS_DIR.glob("allproducts_*.xml"))
    if not candidates:
        sys.exit(f"No catalogs found in {CATALOGS_DIR}")
    return candidates[-1]

def main() -> None:
    ap = argparse.ArgumentParser(description="Dump the Comact product catalog.")
    ap.add_argument(
        "catalog_pos",
        nargs="?",
        help="Path to allproducts_*.xml. Defaults to lex-max in tests/fixtures/_catalogs/.",
    )
    ap.add_argument("--catalog", dest="catalog_flag", help="Same as the positional argument.")
    ap.add_argument(
        "--species",
        default="HMW",
        help="Species code for the per-product detail dump (default: HMW).",
    )
    args = ap.parse_args()

    catalog_path = Path(args.catalog_pos or args.catalog_flag or latest_catalog())
    if not catalog_path.is_file():
        sys.exit(f"Catalog not found: {catalog_path}")

    products = load_products(str(catalog_path))
    focus = args.species.upper()

    print(f"CATALOG: {catalog_path}")
    print(f"TOTAL:   {len(products)} products\n")

    grades = Counter(p.grade for p in products)
    print(f"=== {len(grades)} DISTINCT GRADES ===")
    for g, n in sorted(grades.items()):
        print(f"    {n:>4}  {g!r}")

    colors = Counter(p.color for p in products)
    print(f"\n=== {len(colors)} DISTINCT COLORS ===")
    for c, n in sorted(colors.items()):
        print(f"    {n:>4}  {c!r}")

    print(f"\n=== {focus} PRODUCTS (every one) ===")
    rows = [p for p in products if p.species == focus]
    if not rows:
        print(f"    (no products for species {focus!r})")
    for p in sorted(rows, key=lambda x: (x.thick, x.grade, x.color)):
        print(f"    {p.thick:>4}  {p.grade:<20} {p.color:<10} {p.name}")

    print("\n=== GRADE × SPECIES MATRIX ===")
    matrix: dict = defaultdict(lambda: defaultdict(int))
    species_set = sorted({p.species for p in products})
    grade_set = sorted({p.grade for p in products})
    for p in products:
        matrix[p.grade][p.species] += 1

    header = "  " + " ".join(f"{s:>9}" for s in species_set)
    print(f"{'grade':<22}{header}")
    for g in grade_set:
        row = " ".join(f"{matrix[g][s]:>9}" for s in species_set)
        print(f"{g:<22}{row}")


if __name__ == "__main__":
    main()