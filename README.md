<p align="center">
  <img src="assets/logo.svg" alt="tenon" width="260">
</p>

<h1 align="center">TENON</h1>

<p align="center">cut once</p>

<p align="center">
  <img alt="commits" src="https://img.shields.io/github/commit-activity/t/bhanke-lab/TENON?label=commits">
  <img alt="last commit" src="https://img.shields.io/github/last-commit/bhanke-lab/TENON">
  <img alt="license" src="https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-blue">
</p>

<p align="center">
  <a href="#translatepy">translate.py</a> &bull;
  <a href="#quickstart">Quickstart</a> &bull;
  <a href="#two-loops">Two loops</a> &bull;
  <a href="#accuracy">Accuracy</a> &bull;
  <a href="#roadmap">Roadmap</a>
</p>

---

Translates sawing orders into the Active Products list
the Comact TrimExpert needs to run, and (later) the Bin Sorter sort assignments.

The name stands for Translator Engine for Native Optimizer Notation.
It reads a sawing order and compiles it into the exact configuration
the optimizer and sorting system needs. This same translation has historically
been performed by an experienced operator from memory at every changeover. It is
now codified in a rules engine backed by a labeled fixture corpus, automated to
dramatically reduce error and time spent.

Current version: v0.19 (`<commit-hash>`, 2026-07-20)
Accuracy: 92.3% recall / 92.3% precision across 51 fixtures, 10 species (706/59/59).

For the current ruleset, see `mapping.yaml`. For what changed and why, see `git log`.

---

## translate.py

<table width="100%">
  <tr>
    <td align="center" width="50%">
      <img src="docs/images/runsetup-input.png" alt="Run Set Up input" width="100%"><br>
      <sub><em>Run Set Up as it arrives by email</em></sub>
    </td>
    <td align="center" width="50%">
      <img src="docs/images/translated-output.png" alt="Translated output" width="100%"><br>
      <sub><em>Same sheet after translate.py: products, instance IDs, match count</em></sub>
    </td>
  </tr>
</table>

Reads a Baillie Group Run Set Up `.xlsx` and writes an augmented copy with
three columns appended to every Lumber row:

- `Comact Products`: newline-delimited active product names
- `Instance IDs`: matching `instanceId` values, same order
- `Match Count`: count of matched products; 0-match rows flagged red

Original formatting (merged cells, header colors, column widths, fonts)
is preserved end-to-end via `openpyxl`. The input file is never overwritten.

Usage

```bash
python translate.py --runsetup <path> \
   [--products <allproducts.xml>] \
   [--mapping <mapping.yaml>] \
   [--out <output.xlsx>]
```

Options

- `--runsetup`: Baillie Group Run Set Up `.xlsx` (required)
- `--products`: AllProducts.xml; defaults to newest file in `tests/fixtures/_catalogs/`
- `--mapping`: rules file; defaults to `mapping.yaml` in the repo root
- `--out`: output path; defaults to `<stem>_comact.xlsx` alongside the input

---

## Why this exists

Every sawing order has to be translated three ways at the mill:

1. Sawyer write-ups (manual, out of scope).
2. Comact TrimExpert Active Products: Phase 1 of this tool.
3. Bin Sorter sort assignments: Phase 2.

Today this is tribal-knowledge work that repeats every species changeover.
Automating it cuts changeover time, mis-sorts, and "why is the Comact making 3B?" calls.

Only the Lumber section of the Run Set Up is in scope. Cants, Ties, and Pallet
boards bypass the Comact and Bin Sorter entirely.

---

## Quickstart

Setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\Activate.ps1
# Mac/Linux
source .venv/bin/activate
pip install -r requirements.txt
```

Run the translator on a Run Set Up

```bash
python translate.py --runsetup path/to/runsetup.xlsx
```

Run the diff harness against an existing fixture

```bash
python tests/check_match.py tests/fixtures/tul_2026-07-01
```

Run all fixtures

```bash
python tests/check_all.py
```

Scaffold a new fixture

```bash
python scaffold_fixture.py <species> <YYYY-MM-DD>
```

---

## Two loops

<table width="100%">
  <tr>
    <td align="center" width="50%">
      <img src="docs/images/trimexpert-actives.png" alt="TrimExpert Active Products" width="100%"><br>
      <sub><em>Ground truth: Active Products pane at the Comact</em></sub>
    </td>
    <td align="center" width="50%">
      <img src="docs/images/check-match-diff.png" alt="check_match diff" width="100%"><br>
      <sub><em>check_match: predicted vs ground truth for one fixture</em></sub>
    </td>
  </tr>
</table>

### Build-time loop

Each captured setup is a labeled training example:

1. `python scaffold_fixture.py <species> <YYYY-MM-DD>` creates
   `tests/fixtures/<species>_<date>/` and seeds `catalog.txt` from the
   latest XML in `tests/fixtures/_catalogs/`.
2. Drop the Run Set Up `.xlsx` (and CSV export) into the new fixture folder.
3. At the Comact, screenshot Active + Available products per thickness the
   Run Set Up touches.
4. Transcribe screenshots into `answer_key.csv`
   (`thick,grade,color,width_token,length_token`, one row per active product).
5. `python tests/check_match.py tests/fixtures/<fixture>` prints predicted
   vs ground-truth diff.
6. If a pattern shows up across 2+ fixtures, edit `mapping.yaml` and commit.
7. Every commit re-runs `check_match.py` against ALL fixtures.

This is not machine learning. Within 20 setups ML would learn spurious
correlations and lose auditability: unacceptable in a zero-margin industry where
"why did the optimizer pick this?" needs a defensible answer. Rules are discovered
and codified by hand, validated automatically against every prior labeled example.

### Run-time loop

1. Run Set Up `.xlsx` arrives via email.
2. `python translate.py --runsetup <file>` (or later, an Excel ribbon button).
3. The augmented `.xlsx` goes back as a reply on the original email thread.
4. (Stage 3) A second `Comact Setup` sheet in the workbook: deduped active
   products grouped by thickness, printable for the operator at the machine.

---

## Capture protocol

At the local machine when the Run Set Up email arrives:

1. `python scaffold_fixture.py <species> <YYYY-MM-DD>`
   (lowercase species: sma, hmw, rok, ash, wok, walnut, cherry, birch, tul, basswood)
2. Save the `.xlsx` attachment as `runsetup.xlsx` in the new folder.
   Save As CSV -> `runsetup.csv`.
3. Fresh `allproducts_<date>.xml` goes into `tests/fixtures/_catalogs/`
   only if the Comact catalog was refreshed. The next scaffold run picks it up.

At the Comact during/after changeover:

1. For each thickness the Run Set Up touches:
   - Filter Active Products -> screenshot -> `screenshots/<thick>_active.jpg`
     (e.g. `8_4_active.jpg`).
   - Filter Available Products -> screenshot -> `screenshots/<thick>_available.jpg`.
   - If anything was deselected for a non-obvious reason, record a 30-sec voice
     memo as needed. (Not something I ever did, but it might help you so I kept it.) -> `notes/<thick>.m4a`.
2. Set the species filter and append one line to `live_counts.txt`:
   `[<SPECIES>] active=<N> available=<N>`. Catches catalog drift.

On local machine:

1. Transcribe screenshots into `answer_key.csv`. Use exact strings from the catalog.
2. `python tests/check_match.py tests/fixtures/<fixture>`.
3. If a pattern shows up across 2+ fixtures, edit `mapping.yaml`.
   Commit fixture + rule changes together.

---

## Project layout

```text
TENON/
├── translate.py                       # CLI entry point: Run Set Up .xlsx -> augmented .xlsx
├── mapping.yaml                       # Rules engine (grade_map, color_map, auto_activate)
├── scaffold_fixture.py                # Creates fixture folder + seeds catalog.txt
├── requirements.txt
├── assets/                            # Logo (logo.svg + alternates)
├── docs/                              # README screenshots (docs/images/)
├── src/
│   ├── parse_runsetup.py              # Lumber section parser -> LumberRow list
│   │                                  # load_runsetup(path) and load_runsetup_from_rows(rows)
│   ├── parse_products.py              # AllProducts.xml -> Product dataclasses
│   └── match.py                       # Match engine
├── tests/
│   ├── check_match.py                 # Per-fixture regression harness
│   ├── check_all.py                   # Full corpus summary
│   └── fixtures/
│       ├── _catalogs/                 # AllProducts.xml snapshots, pinned per fixture
│       └── <species>_<date>/          # One folder per labeled Run Set Up
│           ├── runsetup.xlsx
│           ├── runsetup.csv
│           ├── answer_key.csv
│           ├── catalog.txt            # One line: filename of the pinned catalog XML
│           ├── live_counts.txt
│           └── screenshots/
└── tools/
    ├── dump_catalog.py                # Catalog dump: grade x species matrix, drift + gap checks
    ├── fixture_mismatch_analysis.py   # Extras/missing frequency across the whole corpus
    └── fixture_row_debug.py           # Per-row match trace for one fixture
```

---

## Public API

`parse_runsetup`

- `load_runsetup(path)`: parse a Run Set Up file; returns object with
    `species`, `date`, `lumber_rows`.
- `load_runsetup_from_rows(rows)`: same, from pre-read row data (used by
    `translate.py` for the openpyxl path).
- `LumberRow.source_row`: 0-based grid row index in the source sheet;
    `ws_row = source_row + 1`.

`parse_products`

- `load_products(xml_path)`: returns list of `Product` dataclasses with
    `instance_id`, `name`, `thick`, `width_token`, `length_token`,
    `grade`, `color`, `species`.

`match`

- `load_mapping(path)`: `yaml.safe_load`.
- `match_for_row(row, products, run_species, mapping, ...)`: returns list
    of matched products for one Lumber row.
- `match_all(runsetup, products, mapping)`: returns
    `(results, width_unmapped, length_unmapped, predicted)` where
    `results = [(row, [products]), ...]` and `predicted` is a dict of
    `instance_id -> Product` covering all actives including post-pass entries.

---

## Vocabulary map (Run Set Up -> Comact)

`mapping.yaml` is the source of truth. The shape is roughly:

| Run Set Up term | Comact grade code(s) | Notes |
| --- | --- | --- |
| PR (Prime) | FAS family at this thickness x species, plus auto_activate blocks | "Prime" = FAS + SEL combined. Variant scope is catalog-intersected, not hardcoded. |
| 1C / 2C | 1COM / 2COM family at this thickness x species | Color drives the variant. Multi-destination union: when 2+ destinations at the same thick/grade specify different colors, all color variants activate. |
| 3A | 3ACOM OPT (auto-activated) | Fires per-thickness from the catalog regardless of whether the Run Set Up has a 3A row. Per-species excludes live in auto_activate. |
| 3B / Pallet | 3B OPT | Brown 1&2COM dumps here per the Prolam note. |
| SG | SUBG, 3B, WORMY, 1COMB family | Catch-all sub-grade bucket. |
| CHR | FAS, SEL, 1COM, 2COM, CHAR OPT at this thickness x species | Character grade catch-all. |
| UNSEL | grade x thickness x species dependent: not "all colors" | Per-grade per-thickness per-species rules in mapping.yaml, grown one fixture at a time. |
| SAP+BTR | SAP suffix only | At least one sap face. |
| Min Width X" | width token bands where min >= row.min_width | RandomW, Rw > 5, Rw SEL, etc. |
| Length min/max | length tokens intersecting the row's range | RandomL +3", Sel 6, 6-7', etc. |

---

## Catalog facts

Current catalog: `allproducts_2026-07-06.xml` (identical product set to 2026-06-12).

- 10 species: SMA, ASH, HMW, CHERRY, ROK, WOK, WALNUT, TUL, BASSWOOD, BIRCH.
- 8 thicknesses: 4/4, 5/4, 6/4, 7/4, 8/4, 10/4, 12/4, 16/4.
  (9/4 appears in Run Set Ups but has no catalog products; tool warns and continues.)
- 4 color descriptors: Unsel, ?, SAP, 1White.
- Product name format: `{thick} x {width_token} x {length_token} {GRADE} {COLOR} {SPECIES}`.
  Species is always the last whitespace-separated token.

---

## Accuracy

| Metric | Value |
| --- | --- |
| Fixtures | 51 |
| Species | 10 |
| Correct | 706 |
| Extras | 59 |
| Missing | 59 |
| Recall | 92.3% (706/765) |
| Precision | 92.3% (706/765) |
| Version | v0.19 / `<253aa33>` / 2026-07-20 |

The residual gap sits in two classes that need a future layer, not more mapping rules:

- Operator-discretion extras: PR->SEL fires on some runs but not others (ROK, WOK, ASH, CHERRY, HMW).
- Standing-activation misses: ASH 12/4 FAS Unsel prime (3-for-3, no RSU signal).

---

## Roadmap

1. [x] Stage 1: Rule discovery harness. Parsers, match engine, diff harness,
   fixture scaffolder, corpus of 45 labeled fixtures across 10 species.
   v0.17 shipped 2026-07-06.
2. [x] Stage 2: `translate.py` CLI. Format-preserving augmented `.xlsx` output
   (Comact Products / Instance IDs / Match Count, 0-match rows flagged red).
   Shipped 2026-07-06. First production run confirmed 2026-07-07.
3. [ ] Stage 3: Comact Setup sheet. Second sheet in the output workbook:
   deduped active products, grouped by thickness, ordered to mirror the
   Optimizer screen. Printable operator hand-off.
4. [ ] Stage 4: Excel ribbon button. One-click trigger from the Run Set Up
   workbook itself.
5. [ ] Stage 5: Bin Sorter extension. Translate Run Set Up -> Bin Sorter
   sort assignments.
