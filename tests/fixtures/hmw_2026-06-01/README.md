# Fixture: hmw 2026-06-01

## Drop here

- `runsetup.xlsx` - original email attachment
- `runsetup.csv` - Save As CSV from the .xlsx
- `screenshots/<thick>_active.jpg` - Active Products, per thickness
- `screenshots/<thick>_available.jpg` - Available Products, per thickness
- `notes/<thick>.m4a` - voice memo if a deselect was non-obvious
- `live_counts.txt` - append `[<SPECIES>] active=N available=N total=N` from
  the bottom-of-pane counts at the Comact (template pre-seeded)

## Auto-seeded

- `catalog.txt` - points at the latest `_catalogs/allproducts_*.xml`.
  If the catalog is refreshed mid-fixture, edit this manually to point
  at the new filename (or re-scaffold).

Then transcribe screenshots into `answer_key.csv` and run:

```
python tests/check_match.py tests/fixtures/hmw_2026-06-01
```
