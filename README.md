# comact-runsetup-translator

Translates Baillie sawing orders (Run Set Up) into the Active Products list
the Comact TrimExpert needs to run, and (later) the Bin Sorter sort
assignments.

## Status — 2026-05-04

**Capture loop is online.** The end-to-end pipeline runs:
parse Run Set Up → run rules → diff against ground-truth answer key.

- **Fixture #1:** `tests/fixtures/sma_2026-04-27/` — 8/4 Soft Maple,
  partial (8/4 verified product-by-product; 4/4 and 10/4 not backfilled).
- **Mapping version:** v0.7 (`mapping.yaml`).
- **Baseline diff vs ground truth (8/4 SMA):** 5 correct · 3 extras · 2 missing.
  - Extras: `1COM SAP OPT`, `2COM SAP OPT`, `FASB OPT Unsel`
    (UNSEL-isn't-all-colors symptom).
  - Missing: `3ACOM OPT Unsel`, `WORMY ?`
    (optimizer auto-activates downgrade grades w/ no Run Set Up row).
- **Next:** capture fixture #2 from a real production setup, repeat.
  No `mapping.yaml` edits until ≥2 fixtures show the same pattern —
  one data point would overfit to Soft Maple.

## Why this exists

Every sawing order has to be translated three ways at the mill:

1. Sawyer write-ups (manual — out of scope).
2. **Comact TrimExpert Active Products** — Phase 1 of this tool.
3. **Bin Sorter sort assignments** — Phase 2.

Today this is tribal-knowledge work that gets repeated every species
changeover. Automating it cuts changeover time, mis-sorts, and "why is
the Comact making 3B?" calls.

Only the **Lumber** section of the Run Set Up is in scope. Cants, Ties,
and Pallet boards bypass the Comact and Bin Sorter, so the tool reads
past those sections and leaves them untouched.

## Two loops

### Build-time / training loop

Each captured setup is a labeled training example:

1. Save the Run Set Up `.xlsx` (and CSV export) under
   `tests/fixtures/<species>_<YYYY-MM-DD>/`.
2. At the Comact, screenshot Active + Available products per thickness
   that the Run Set Up touches.
3. Transcribe screenshots into `answer_key.csv`
   (`thick,grade,color,width_token,length_token`, one row per active product).
4. Run `python tests/check_match.py tests/fixtures/<fixture>` →
   prints predicted vs ground-truth diff.
5. If a pattern shows up across ≥2 fixtures, edit `mapping.yaml` and commit.
6. Every commit re-runs `check_match.py` against ALL fixtures →
   impossible to fix one setup while breaking another.

> **This is NOT machine learning.** With ~5–50 setups, ML would learn
> spurious correlations and lose auditability. Instead this is a rules
> engine with a growing test corpus — rules are discovered and codified
> by hand, validated automatically against every prior labeled example.

### Run-time / production loop (goal state)

1. Run Set Up `.xlsx` arrives via email (Baillie Group template).
2. The tool is triggered (CLI in Phase 1A, Excel ribbon button in Phase 1B).
3. The tool reads the Lumber section, runs the match engine, and writes
   a new `.xlsx` preserving original formatting (logo, merged cells,
   header colors, fonts) with three columns appended to the right of the
   Lumber rows:
   - **Comact Products** — newline-delimited active product names.
   - **Instance IDs** — matching `instanceId`s, same order.
   - **Match Count** — flag rows with `0` in red (rule gap, not a real zero).
4. The augmented `.xlsx` is sent back as a reply on the original email thread.
5. (Phase 1C) A second `Comact Setup` sheet in the same workbook —
   deduped active products grouped by thickness, printable for the operator.

## Public API

- `parse_runsetup.load_runsetup(path)` — returns object with
  `species_raw`, `species`, `date`, `lumber_rows`.
- `parse_products.load_products(xml_path)` — returns iterable of products
  with `instance_id`, `name`, `thick`, `width_token`, `length_token`,
  `grade`, `color`, `species`.
- `match.load_mapping(path)` — `yaml.safe_load`.
- `match.match_for_row(row, products, run_species, mapping, ...)` —
  returns list of matched products for one Run Set Up row.
- `match.match_all(runsetup, products, mapping)` — returns 3-tuple
  `(out, width_unmapped, length_unmapped)` where
  `out = [(row, [products]), ...]`.

## Quickstart
.venvScriptsActivate.ps1
pip install -r requirements.txt
Run the diff harness against the seed fixture
python tests/check_match.py tests/fixtures/sma_2026-04-27

Expected output today: `5 correct · 3 extras · 2 missing`.

## Capture protocol (per setup, ~5 min total)

**At the laptop, when the Run Set Up email arrives:**
1. `mkdir tests/fixtures/<species>_<YYYY-MM-DD>/`
   (lowercase species: SMA, HMW, ROK, ASH, ...).
2. Save the `.xlsx` attachment as `runsetup.xlsx`; Save As CSV → `runsetup.csv`.
3. Drop a fresh `allproducts.xml` only if the Comact catalog was refreshed.

**At the Comact, during/after changeover (~2 min):**
1. For each thickness the Run Set Up touches:
   - Filter Active Products → screenshot → `screenshots/<thick>_active.jpg`
     (e.g. `8_4_active.jpg`).
   - Filter Available Products → screenshot → `screenshots/<thick>_available.jpg`.
   - If anything was deselected for a non-obvious reason, capture a
     30-sec voice memo → `notes/<thick>.m4a`. **That's the tribal
     knowledge the corpus is really chasing.**

**Back at the laptop (~5 min):**
1. Transcribe screenshots into `answer_key.csv` — one row per active
   product. Use exact strings as they appear in the catalog.
2. `python tests/check_match.py tests/fixtures/<fixture>`.
3. If a pattern shows up across ≥2 fixtures, edit `mapping.yaml`.
   Commit fixture + any rule changes together.

## Vocabulary map (Run Set Up → Comact)

| Run Set Up term | Comact grade code(s)                              | Notes                                                  |
| --------------- | ------------------------------------------------- | ------------------------------------------------------ |
| **PR** (Prime) | `(FAS / FASS / SEL / SEL SAP / FAS OPT) ∩ catalog at this thickness × species`, plus auto_activate blocks for the rest | "Prime" = FAS + SEL combined. Variant scope is **catalog-intersected, not hardcoded**. FASS / SEL SAP gated by SAP+BTR or multi-destination color union. FASB OPT [Unsel] auto-on at HMW [8/4, 10/4, 12/4, 16/4]. FAS OPT [Unsel] auto-on at HMW [4/4, 6/4]. FAS1W / FAS2W auto-on at 8/4 HMW. See `mapping.yaml` for the authoritative list. |
| **1C** | `(1COM OPT, 1COM SAP OPT, 1COMB OPT) ∩ catalog at this thickness × species` | Color drives the variant. **Multi-destination color union** applies: when ≥2 destinations at the same thick/grade specify different colors (UNSEL + SAP+BTR), all color variants in catalog activate. `1COMB OPT` is the brown variant — present in catalog at 4/4 + 5/4 only. |
| **2C** | `(2COM OPT, 2COM SAP OPT) ∩ catalog at this thickness × species` | Same multi-destination color union as 1C. **Open: ** at HMW 4/4 the operator runs `2COM OPT Unsel` even when only a SAP+BTR 2C row exists in the RSU (asymmetric vs 1C). May become a `2COM OPT [Unsel]` auto_activate rule once a 3rd HMW fixture confirms. |
| **3A** | `3ACOM OPT (SAP / Unsel) ∩ catalog at this thickness × species` — **auto-activated**, no RSU row required | 3ACOM activates per-thickness from the catalog regardless of whether the Run Set Up has a 3A destination row. Operator treats it as a downgrade-flow grade. Verified across SMA 8/4 (Unsel only) + HMW 4/4 / 6/4 / 8/4. |
| **3B / Pallet** | 3B OPT                                            | Brown 1&2COM dumps here per the Prolam note.           |
| **SG** | `(SUBG OPT, 3B OPT, WORMY ?, WORMY MARK ?, 1COMB OPT) ∩ catalog at this thickness × species` | Prolam catch-all driven by the Run Set Up note "all 3b — all sound pallet — all brown 1&2com here". Future runs without that note may need a narrower SG (e.g. SUBG-only). WORMY/WORMY MARK auto-activation is provisional pending a 3rd species fixture with WORMY in catalog. |
| Color UNSEL | grade × thickness × species dependent — **NOT** "all colors" | Operator picks the natural color flavor of each grade × thickness × species. Examples: PR UNSEL @ 8/4 SMA → SAP only (no FASB Unsel); 1C/2C UNSEL @ 8/4 SMA → Unsel only (no SAP). No static `color_map.UNSEL` captures this — encoded as per-grade-per-thickness-per-species rules in `mapping.yaml` and grown one fixture at a time. |
| Color SAP+BTR   | `SAP` suffix only                                 | At least one sap face.                                 |
| Min Width X" | Width token band (`RandomW`, `Rw > 5`, `Rw SEL`, `Rw 5-8`, etc.) | Pick all width bands whose min ≥ row.min_width. Width tokens are bin descriptors, not row filters — physical board width routes to whichever active bin matches. |
| Length min/max | Length token (`RandomL +3"`, `Sel 6`, `6-7'`) | `Sel 6` = 6' selects only; `RandomL +3"` = 7'+; specific bands for 6-7'. |

## Catalog facts (`allproducts.xml`, Wagner_20250806)

- 443 total products.
- 10 species: SMA(66), ASH(64), HMW(58), CHERRY(57), ROK(51), WOK(45),
  WALNUT(36), TUL(24), BASSWOOD(22), BIRCH(20).
- 8 thicknesses: 4/4(109), 5/4(106), 8/4(89), 6/4(80), 10/4(29),
  12/4(13), 16/4(10), 7/4(7).
- 4 colors: Unsel(230), `?`(118), SAP(71), 1White(24).
- Product names follow `{thick} x {width_token} x {length_token} {GRADE} {COLOR_DESC} {SPECIES}`.
  Species is always the last whitespace-separated token (split from the right).

**SMA cross-thickness rules of thumb:**
- `SEL OPT Unsel` only in 6/4.
- `3B OPT` / `1COMB OPT` / `SUBG OPT` only in 4/4 and 5/4.
- 10/4+ is SAP-only.

## Open mysteries (the diff is actively tracking these)

**1. UNSEL color preference** — UNSEL is grade × thickness × species dependent.
At 8/4 SMA: PR UNSEL → SAP only (FASS, SEL SAP); 1C/2C UNSEL → Unsel only.
A thickness-conditional rule will be encoded once ≥2 fixtures show the same pattern.

**2. Auto-activation** — Run Set Up rows are not exhaustive. The optimizer
auto-activates downgrade-flow grades (3ACOM, WORMY) per thickness even when
no row in the Run Set Up references them. WORMY MARK was *not* auto-active
at 8/4 — only one of the two is selected per setup. More fixtures needed
to encode.

**3. FASB OPT Unsel deselected at 8/4 PR** — hypothesis: at 8/4 SMA the
heart is too dark for true Unsel-color prime, so only sap-faced boards
qualify. The rule resolves once ASH or HMW at 8/4 lands — if FASB Unsel
is active there, the rule is species-specific; if not, thickness-general.

## Roadmap

1. ✅ Mapping tables, parsers, match engine, diff harness.
2. ⏳ Accumulate fixtures (~7/week). Encode patterns in `mapping.yaml`
   as they emerge across ≥2 fixtures.
3. ⏳ `tests/test_softmaple_4_27.py` — pytest assertion (partial-fixture-aware).
4. ⏳ `translate.py` CLI + `openpyxl` `.xlsx` round-trip writer
   (3 columns appended to Lumber section, red flag on Match Count = 0).
5. ⏳ Phase 1C: `Comact Setup` printable second sheet.
6. ⏳ Phase 1B: Excel ribbon button shells out to Python.
7. ⏳ Phase 2: Bin Sorter extension.
