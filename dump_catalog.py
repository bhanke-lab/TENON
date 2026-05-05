# dump_catalog.py
from collections import Counter, defaultdict
from src.parse_products import load_products

products = load_products("tests/fixtures/_catalogs/allproducts_2026-05-04.xml")

print(f"TOTAL: {len(products)} products\n")

# Every distinct grade string, with frequency
grades = Counter(p.grade for p in products)
print(f"=== {len(grades)} DISTINCT GRADES ===")
for g, n in sorted(grades.items()):
    print(f"  {n:>4}  {g!r}")

# Every distinct color string
colors = Counter(p.color for p in products)
print(f"\n=== {len(colors)} DISTINCT COLORS ===")
for c, n in sorted(colors.items()):
    print(f"  {n:>4}  {c!r}")

# Every distinct (grade, color, species, thick) tuple — the real fingerprint
print(f"\n=== HMW PRODUCTS (every one) ===")
hmw = [p for p in products if p.species == "HMW"]
for p in sorted(hmw, key=lambda x: (x.thick, x.grade, x.color)):
    print(f"  {p.thick:>4}  {p.grade:<20}  {p.color:<10}  {p.name}")

# Cross-tab: grade × species, just counts
print(f"\n=== GRADE × SPECIES MATRIX ===")
matrix = defaultdict(lambda: defaultdict(int))
species_set = sorted({p.species for p in products})
grade_set = sorted({p.grade for p in products})
for p in products:
    matrix[p.grade][p.species] += 1
header = "  " + "  ".join(f"{s:>9}" for s in species_set)
print(f"{'grade':<22}{header}")
for g in grade_set:
    row = "  ".join(f"{matrix[g][s]:>9}" for s in species_set)
    print(f"{g:<22}{row}")