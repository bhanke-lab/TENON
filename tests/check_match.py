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
    # Pre-check: confirm the fixture dir exists before any file reads.
    # A typo'd fixture name otherwise dies with FileNotFoundError on
    # runsetup.csv several layers down, which doesn't tell the operator
    # whether they typo'd the name or the fixture is malformed.
    if not fixture_dir.exists():
        fixtures_root = ROOT / "tests" / "fixtures"
        available = sorted(
            d.name for d in fixtures_root.iterdir()
            if d.is_dir() and d.name != "_catalogs"
        )
        msg = [f"Fixture not found: {fixture_dir}", "", "Available fixtures:"]
        msg.extend(f"  {name}" for name in available)
        sys.exit("\n".join(msg))

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

    # Pre-flight: catch catalog gaps before bucketing predictions.
    # If the answer key references products that don't exist in the catalog
    # FOR THIS RUN'S SPECIES, no amount of rule tuning will close the gap -
    # the catalog itself needs updating (re-pull AllProducts.xml or hand-add
    # the missing entries). Reports as a distinct failure mode (exit 2)
    # instead of being silently bucketed into "MISSING (false negatives)" -
    # that conflation is what cost ~5 turns of diagnosis on the FAS OPT
    # Unsel HMW gap (2026-05-05).
    #
    # Species-scoped: a cherry answer key entry that happens to match an HMW
    # product's (thick, grade, color, w, l) tuple is still a cherry catalog
    # gap. Without the species filter the cross-species shadow hides it.
    catalog_keys = {product_key(p) for p in products if p.species == runsetup.species}
    catalog_gaps = answer_key - catalog_keys
    if catalog_gaps:
        print("⚠️  CATALOG GAP - answer key contains products not in catalog:")
        for p in sorted(catalog_gaps):
            print(f"    {p[0]:5} {p[1]:18} {p[2]:6} w={p[3]:18} l={p[4]}")
        print()
        print("Fix the catalog (add to AllProducts.xml or re-pull from the live")
        print("Comact) before tuning mapping.yaml - rule changes can't conjure")
        print("products that don't exist in the master catalog.")
        sys.exit(2)

    # Cross-check live operator counts (if captured) against catalog counts.
    # The pre-flight above catches catalog gaps surfaced by THIS fixture's
    # answer key. live_counts.txt catches drift for products not in this
    # answer key but present on the live Comact - e.g., next time Nate
    # hand-adds something at the UI, the count divergence flags it before
    # the next fixture trips over it. Warning only; doesn't exit.
    live_counts_path = fixture_dir / "live_counts.txt"
    if live_counts_path.exists():
        catalog_by_species = {}
        for p in products:
            catalog_by_species[p.species] = catalog_by_species.get(p.species, 0) + 1
        drifts = []
        for raw in live_counts_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            # Format: [<SPECIES>] active=<N> available=<N> total=<N>
            try:
                species_part, rest = line.split("]", 1)
                species = species_part.lstrip("[").strip()
                kv = {}
                for token in rest.split():
                    if "=" in token:
                        k, v = token.split("=", 1)
                        kv[k] = v
                live_total = int(kv["total"])
            except (ValueError, KeyError):
                print(f"⚠️  live_counts.txt: could not parse line: {line!r}")
                continue
            catalog_total = catalog_by_species.get(species, 0)
            if live_total != catalog_total:
                drifts.append((species, live_total, catalog_total))
        if drifts:
            print("⚠️  CATALOG DRIFT - live operator counts disagree with catalog:")
            for species, live, cat in drifts:
                delta = live - cat
                print(f"    {species}: live={live} catalog={cat} (delta={delta:+d})")
            print()
            print("Live = Active+Available counts under the [<SPECIES>] filter")
            print("on the Comact. Catalog = products in the current XML for that")
            print("species. Drift means re-pull AllProducts.xml or hand-patch")
            print("_catalogs/<latest>.xml. Warning only - diff continues.")
            print()

    documented = {k[0] for k in answer_key}

    pred_in_scope = {p for p in predicted_keys if p[0] in documented}
    correct = pred_in_scope & answer_key
    extra   = pred_in_scope - answer_key
    missing = answer_key - pred_in_scope

    print(f"Fixture:                {fixture_dir.name}")
    print(f"Documented thicknesses: {sorted(documented)}  (others ignored)")
    print(f"Answer key:             {len(answer_key)} active products")
    print(f"Predicted (in scope):   {len(pred_in_scope)}")
    print(f"  ✓ Correct:      {len(correct)}")
    print(f"  ✗ Extra:        {len(extra)} (predicted but NOT active)")
    print(f"  ? Missing-rule: {len(missing)} (active but NOT predicted; investigate for new rule or operator override)")
    print()

    def dump(label, s):
        if not s:
            return
        print(f"=== {label} ===")
        for p in sorted(s):
            print(f"  {p[0]:5} {p[1]:18} {p[2]:6} w={p[3]:18} l={p[4]}")
        print()

    dump("EXTRA (false positives)", extra)
    dump("MISSING-RULE (active but no rule coverage; investigate for new rule or operator override)", missing)
    if not extra and not missing:
        print(" Perfect match across documented thicknesses.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tests/check_match.py <fixture_dir>")
        sys.exit(1)

    main(Path(sys.argv[1]).resolve())