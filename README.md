# comact-runsetup-translator

Translates Baillie sawing orders (Run Set Up) into the Active Products list the Comact TrimExpert needs to run, and (later) the Bin Sorter sort assignments.

For the current ruleset, see `mapping.yaml`. For what changed and why, see `git log`.

## Why this exists

Every sawing order has to be translated three ways at the mill:

1. Sawyer write-ups (manual - out of scope).
2. **Comact TrimExpert Active Products** - Phase 1 of this tool.
3. **Bin Sorter sort assignments** - Phase 2.

Today this is tribal-knowledge work that gets repeated every species changeover. Automating it cuts changeover time, mis-sorts, and "why is the Comact making 3B?" calls.

Only the **Lumber** section of the Run Set Up is in scope. Cants, Ties, and Pallet boards bypass the Comact and Bin Sorter, so the tool reads past those sections and leaves them untouched.

## Two loops

### Build-time / training loop

Each captured setup is a labeled training example:

1. `python scaffold_fixture.py <species> <YYYY-MM-DD>` creates `tests/fixtures/<species>_<YYYY-MM-DD>/` and seeds `catalog.txt` from the latest XML in `tests/fixtures/_catalogs/`.
2. Drop the Run Set Up `.xlsx` (and CSV export) into the new fixture folder.
3. At the Comact, screenshot Active + Available products per thickness the Run Set Up touches.
4. Transcribe screenshots into `answer_key.csv` (`thick,grade,color,width_token,length_token`, one row per active product).
5. `python tests/check_match.py tests/fixtures/<fixture>` prints predicted vs ground-truth diff.
6. If a pattern shows up across ≥2 fixtures, edit `mapping.yaml` and commit.
7. Every commit re-runs `check_match.py` against ALL fixtures - impossible to fix one setup while breaking another.

> **This is NOT machine learning.** With ~5–50 setups, ML would learn spurious correlations and lose auditability. Instead this is a rules engine with a growing test corpus - rules are discovered and codified by hand, validated automatically against every prior labeled example.

### Run-time / production loop (goal state)

1. Run Set Up `.xlsx` arrives via email (Baillie Group template).
2. The tool is triggered (CLI in Phase 1A, Excel ribbon button in Phase 1B).
3. The tool reads the Lumber section, runs the match engine, and writes a new `.xlsx` preserving original formatting (logo, merged cells, header colors, fonts) with three columns appended to the right of the Lumber rows:
   - **Comact Products** - newline-delimited active product names.
   - **Instance IDs** - matching `instanceId`s, same order.
   - **Match Count** - flag rows with `0` in red (rule gap, not a real zero).
4. The augmented `.xlsx` is sent back as a reply on the original email thread.
5. (Phase 1C) A second `Comact Setup` sheet in the same workbook - deduped active products grouped by thickness, printable for the operator.

## Quickstart

​
.venvScriptsActivate.ps1
pip install -r requirements.txt
Run the diff harness against an existing fixture
python tests/check_match.py tests/fixtures/sma_2026-04-27
Scaffold a new fixture (creates folder, seeds catalog.txt from latest XML)
python scaffold_fixture.py <species> <YYYY-MM-DD>

## Capture protocol (per setup, ~5 min total)

**At the laptop, when the Run Set Up email arrives:**

1. `python scaffold_fixture.py <species> <YYYY-MM-DD>` (lowercase species: sma, hmw, rok, ash, ...).
2. Save the `.xlsx` attachment as `runsetup.xlsx` in the new folder; Save As CSV → `runsetup.csv`.
3. Drop a fresh `allproducts_<YYYY-MM-DD>.xml` into `tests/fixtures/_catalogs/` only if the Comact catalog was refreshed. The next scaffold run picks it up automatically.

**At the Comact, during/after changeover (~2 min):**

1. For each thickness the Run Set Up touches:
   - Filter Active Products → screenshot → `screenshots/<thick>_active.jpg` (e.g. `8_4_active.jpg`).
   - Filter Available Products → screenshot → `screenshots/<thick>_available.jpg`.
   - If anything was deselected for a non-obvious reason, capture a 30-sec voice memo → `notes/<thick>.m4a`. **That's the tribal knowledge the corpus is really chasing.**

**Back at the laptop (~5 min):**

1. Transcribe screenshots into `answer_key.csv` - one row per active product. Use exact strings as they appear in the catalog.
2. `python tests/check_match.py tests/fixtures/<fixture>`.
3. If a pattern shows up across ≥2 fixtures, edit `mapping.yaml`. Commit fixture + any rule changes together.

## Public API

- `parse_runsetup.load_runsetup(path)` - returns object with `species_raw`, `species`, `date`, `lumber_rows`.
- `parse_products.load_products(xml_path)` - returns iterable of products with `instance_id`, `name`, `thick`, `width_token`, `length_token`, `grade`, `color`, `species`.
- `match.load_mapping(path)` - `yaml.safe_load`.
- `match.match_for_row(row, products, run_species, mapping, ...)` - returns list of matched products for one Run Set Up row.
- `match.match_all(runsetup, products, mapping)` - returns 3-tuple `(out, width_unmapped, length_unmapped)` where `out = [(row, [products]), ...]`.

## Vocabulary map (Run Set Up → Comact)

`mapping.yaml` is the source of truth. The shape is roughly:

| Run Set Up term | Comact grade code(s) | Notes |
|---|---|---|
| **PR** (Prime) | `FAS` family ∩ catalog at this thickness × species, plus species/thickness-specific `auto_activate` blocks | "Prime" = FAS + SEL combined. Variant scope is catalog-intersected, not hardcoded. |
| **1C / 2C** | `1COM` / `2COM` family ∩ catalog at this thickness × species | Color drives the variant. Multi-destination color union: when ≥2 destinations at the same thick/grade specify different colors, all color variants in catalog activate. |
| **3A** | `3ACOM OPT` ∩ catalog at this thickness × species - **auto-activated** | Activates per-thickness from the catalog regardless of whether the Run Set Up has a 3A row. |
| **3B / Pallet** | `3B OPT` | Brown 1&2COM dumps here per the Prolam note. |
| **SG** | `SUBG`, `3B`, `WORMY`, `1COMB` family ∩ catalog | Catch-all driven by the Run Set Up "all 3b - all sound pallet - all brown 1&2com here" note. |
| Color UNSEL | grade × thickness × species dependent - **NOT** "all colors" | Per-grade-per-thickness-per-species rules in `mapping.yaml`, grown one fixture at a time. |
| Color SAP+BTR | `SAP` suffix only | At least one sap face. |
| Min Width X" | Width token band (`RandomW`, `Rw > 5`, `Rw 5-8`, ...) | All width bands whose min ≥ row.min_width. |
| Length min/max | Length token (`RandomL +3"`, `Sel 6`, `6-7'`) | Specific bands per length spec. |

## Catalog facts (`tests/fixtures/_catalogs/allproducts_*.xml`)

- ~10 species: SMA, ASH, HMW, CHERRY, ROK, WOK, WALNUT, TUL, BASSWOOD, BIRCH.
- 8 thicknesses: 4/4, 5/4, 6/4, 7/4, 8/4, 10/4, 12/4, 16/4.
- 4 colors: Unsel, `?`, SAP, 1White.
- Product names follow `{thick} x {width_token} x {length_token} {GRADE} {COLOR_DESC} {SPECIES}`. Species is always the last whitespace-separated token (split from the right).

## Roadmap

1. ✅ **Stage 1 - Rule discovery harness.** Parsers, match engine, diff harness, fixture scaffolder, and a corpus of labeled fixtures across multiple species and thicknesses. `mapping.yaml` is the codified ruleset; commit history is the trail of how each rule was found.
2. ⏳ **Stage 2 - `translate.py` CLI.** Round-trip an annotated `.xlsx` (Comact Products / Instance IDs / Match Count columns appended to the Lumber section, with red flags on zero-match rows).
3. ⏳ **Stage 3 - Operator-facing output.** A second `Comact Setup` sheet in the workbook, deduped active products grouped by thickness, printable for the operator.
4. ⏳ **Stage 4 - Excel ribbon button.** One-click trigger from the Run Set Up workbook itself.
5. ⏳ **Stage 5 - Bin Sorter extension.** Phase 2 - same pattern, different target system.
