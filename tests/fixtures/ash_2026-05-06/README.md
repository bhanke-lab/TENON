# Fixture: ash 2026-05-06

## Drop here

- `runsetup.xlsx` - original email attachment
- `runsetup.csv` - Save As CSV from the .xlsx
- `allproducts.xml` - only if catalog refreshed since last fixture
- `screenshots/<thick>_active.jpg` - Active Products, per thickness
- `screenshots/<thick>_available.jpg` - Available Products, per thickness
- `notes/<thick>.m4a` - voice memo if a deselect was non-obvious
- `live_counts.txt` - append `[<SPECIES>] active=N available=N total=N` from
  the bottom-of-pane counts at the Comact (template pre-seeded)

Then transcribe screenshots into `answer_key.csv` and run:

```bash
python tests/check_match.py tests/fixtures/ash_2026-05-06
```
