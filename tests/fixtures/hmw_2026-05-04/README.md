# Fixture: hmw 2026-05-04

## Drop here
- `runsetup.xlsx` — original email attachment
- `runsetup.csv` — Save As CSV from the .xlsx
- `allproducts.xml` — only if catalog refreshed since last fixture
- `screenshots/<thick>_active.jpg` — Active Products, per thickness
- `screenshots/<thick>_available.jpg` — Available Products, per thickness
- `notes/<thick>.m4a` — voice memo if a deselect was non-obvious

Then transcribe screenshots into `answer_key.csv` and run:
```
python tests/check_match.py tests/fixtures/hmw_2026-05-04
```
