"""
parse_products.py — Load the Comact AllProducts.xml catalog into structured
Product records.

Naming convention assumed:
    `{thick} x {width} x {length} {GRADE} {COLOR} {SPECIES}`

Structured fields (thick / width / length / grade / price / volumePrice) are
read directly from the XML. Color and species are derived from the trailing
tokens of the product name string.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

# Color descriptors that may appear between GRADE and SPECIES in the name.
# Anything else in that slot is treated as part of the grade and color = "?".
KNOWN_COLORS = {"Unsel", "SAP", "1White", "?"}
@dataclass(frozen=True)
class Product:
    instance_id: str
    historical_id: str
    name: str
    thick: str
    width_token: str
    length_token: str
    grade: str
    color: str
    species: str
    price: float
    volume_price: float
def load_products(xml_path):
    """Parse AllProducts.xml into a list of Product records."""
    xml_path = Path(xml_path)
    if not xml_path.exists():
        raise FileNotFoundError(f"Products XML not found: {xml_path}")
    tree = ET.parse(xml_path)
    root = tree.getroot()
    # Find the elements that represent products. Try common tag names.
    elements = []
    for tag in ("board", "Board", "product", "Product", "item", "Item"):
        elements = root.findall(f".//{tag}")
        if elements:
            break
    if not elements:
        elements = list(root)
    products = []
    for el in elements:
        name = _get(el, "name") or _get(el, "Name")
        if not name:
            continue
        color, species = _color_and_species_from_name(name)
        products.append(Product(
            instance_id=_get(el, "instanceId"),
            historical_id=_get(el, "historicalId"),
            name=name,
            thick=_get(el, "thick"),
            width_token=_get(el, "width"),
            length_token=_get(el, "length"),
            grade=_get(el, "grade"),
            color=color,
            species=species,
            price=_to_float(_get(el, "price")),
            volume_price=_to_float(_get(el, "volumePrice")),
        ))
    return products
def _get(el, field):
    """Read a field from an element. Child element text first, then attribute."""
    child = el.find(field)
    if child is not None and child.text is not None:
        return child.text.strip()
    return el.get(field, "").strip()
def _color_and_species_from_name(name):
    tokens = name.split()
    if not tokens:
        return "?", ""
    species = tokens[-1]
    color = tokens[-2] if len(tokens) >= 2 and tokens[-2] in KNOWN_COLORS else "?"
    return color, species
def _to_float(s):
    """Parse a price string. Rounds to 4 decimals to handle XML float quirks like 1.8000001."""
    if not s:
        return 0.0
    try:
        return round(float(s), 4)
    except ValueError:
        return 0.0
if __name__ == "__main__":
    import sys
    from collections import Counter
    default = "tests/fixtures/softmaple_2026-04-27/allproducts.xml"
    path = sys.argv[1] if len(sys.argv) > 1 else default
    products = load_products(path)
    print(f"Loaded {len(products)} products from {path}\n")
    print("First 5 products:")
    for p in products[:5]:
        print(f"  {p.name}")
        print(f"    thick={p.thick!r}  width={p.width_token!r}  length={p.length_token!r}")
        print(f"    grade={p.grade!r}  color={p.color!r}  species={p.species!r}")
        print(f"    price=${p.price}  volume_price=${p.volume_price}")
    print()
    print("Counts by species:", dict(Counter(p.species for p in products).most_common()))
    print("Counts by thick: ", dict(Counter(p.thick for p in products).most_common()))
    print("Counts by color: ", dict(Counter(p.color for p in products).most_common()))