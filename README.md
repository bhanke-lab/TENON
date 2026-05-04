# Comact Run Set Up Translator

Translates Baillie Group Run Set Up sheets into Comact TrimExpert active product
selections for the Wagner Lumber mill in Owego, NY.

## What it does

- Reads a Run Set Up `.xlsx` (Baillie format) emailed from up the chain
- Cross-references against the Comact `AllProducts.xml` catalog
- Outputs a copy of the `.xlsx` with three new columns (Comact Products,
  Instance IDs, Match Count) appended to the Lumber section, original
  formatting preserved
- (Phase 1C) Adds a `Comact Setup` sheet — printable, deduped, grouped by
  thickness — for the optimizer operator

## Status

Phase 1A (Python prototype). Full plan in the Notion planning doc.

## Quick start

python -m venv .venv
.venvScriptsActivate.ps1
pip install -r requirements.txt
pytest

## Project layout

- `src/parse_runsetup.py` — Run Set Up CSV/XLSX → normalized rows
- `src/parse_products.py` — `AllProducts.xml` → product catalog
- `src/match.py` — match engine
- `mapping.yaml` — translation rules (grade map, color map, width/length predicates)
- `translate.py` — CLI entry point
- `tests/fixtures/<species>_<date>/` — labeled training examples (one per real Run Set Up)