# Carbon & Energy Calculator for Steelmaking

Streamlit application for **Problem Statement 3** of the Jindal Stainless engineering
case study: estimate CO₂e per tonne of stainless steel from the input mix and the
energy mix, show clearly how each input moves the result, and find lower-carbon
combinations that are still practical.

Every number in the app comes from evaluating the formula definitions in
`Stainless Steel Carbon Accounting Grid (3).xlsx` — **71 process steps × 11 metrics** —
at the user's chosen scrap ratio and grid energy mix. No coefficients are re-derived
or hard-coded in the application code.

## Running it

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open http://localhost:8501.

## What the app does

| Tab | Purpose |
| --- | --- |
| **Calculator** | Live Scope 1 / Scope 2 / Scope 3 / total tCO₂e per tonne and GJ per tonne, split by scope and by department, plus a sensitivity curve across the full scrap-ratio range. |
| **Route builder** | Every department, stage and technology variation selectable from dropdowns, with each option priced at the current inputs, per-stage contribution bars, and the saving available at each stage. |
| **Process grid** | All per-process results, filterable and downloadable as CSV, with the exact workbook formula and the row's coefficient notes for any step. |
| **Baseline comparison** | Current scenario against a default or user-captured baseline: per-scope deltas, tonnes avoided, and the annual saving at 1 Mt of output. |
| **Optimiser** | Lowest-carbon path within user constraints — scrap availability, per-source share caps, renewable and non-fossil floors, and stages locked to installed assets. |
| **Methodology** | The model, the seven grid emission factors and their basis, the downstream Scope 3 (Cat. 9-15) framing, and the source workbook's disclaimer. |

## The model

Two families of formula appear in the grid:

* **Input-mix driven** — `x·EF_virgin + y·EF_scrap`, where `y` is the scrap ratio and
  `x = 1 − y`. Covers Scope 1, Scope 3 upstream, the trace gases and specific energy.
* **Grid-mix driven** — Scope 2 is
  `(x·kWh_virgin + y·kWh_scrap) × (a·EF_coal + b·EF_oil + c·EF_gas + d·EF_hydro + e·EF_wind + f·EF_solar + g·EF_nuclear) / 1000`,
  so electricity demand comes from the input mix and its carbon intensity comes from
  the seven source shares `a`–`g`, which sum to 1.

**Total CO₂e/t = Scope 1 + Scope 2 + Scope 3 (upstream, Cat. 1-8).** The gas-by-gas
columns (CO₂, CH₄, N₂O, HFCs, PFCs, SF₆, NF₃) are a disaggregation reported alongside
the scopes, not a fourth scope, so the app displays them separately and never adds
them into the total.

### Route, not a sum of all 71 rows

Several stages in the grid list **mutually exclusive alternatives** — inbound unloading
by train / road / ocean, primary melting by EAF / IF / BF-converter / VIM / VAR / ESR,
decarburisation by AOD / VOD / K-OBM-S / CLU, and so on. Adding all 71 rows would
double-count them, so the app groups the rows into **48 stages** and a route takes
exactly one variation per stage. Stages and whole departments can also be switched
off entirely. The **Route builder** tab exposes all of this: a department picker, a
per-department accordion, and a dropdown at every stage whose options are labelled
with what each technology costs at the current scrap ratio and grid mix — so the
carbon consequence of a choice is visible while making it.

### How the optimiser works

The search is exact rather than heuristic, because the model's structure allows it:

1. Each Scope 2 formula is `kWh × EF_mix / 1000` with `EF_mix` a share-weighted average,
   so the mix minimising Scope 2 is the one minimising `EF_mix` — independent of scrap
   ratio and route. It is solved once as a small linear program (box bounds on each
   source, plus renewable and non-fossil floors, summing to 1).
2. Stages are additive, so at any fixed scrap ratio the best route is the lowest-total
   variation at each unlocked stage, chosen independently.
3. That leaves a one-dimensional sweep over the allowed scrap ratio range.

Infeasible constraint sets (floors that cannot be met within the caps, caps that cannot
reach 100%) are reported as such rather than silently relaxed.

## Layout

```
app.py                        Streamlit UI
carbon_calc/formulas.py       AST-based safe evaluator for the workbook's formula text
carbon_calc/model.py          Dataset loading, per-process evaluation, aggregation
carbon_calc/route.py          Stage grouping and route selection
carbon_calc/optimize.py       Constraint handling and the lowest-carbon search
scripts/extract_workbook.py   Regenerates data/carbon_grid.json from the .xlsx
data/carbon_grid.json         Extracted formulas, grid factors, downstream notes
data/source/                  The source workbook
tests/                        pytest suite (run with `python -m pytest`)
```

The formula strings are parsed to an AST and evaluated against a whitelist of the nine
model variables and the arithmetic operators — `eval` is never used on workbook content.

## Disclaimer

The coefficients in the source workbook are **illustrative** values chosen to demonstrate
a working, formula-linked model. They are not measured or independently verified for any
specific plant or grid connection. Replace them with verified plant data and your
utility's disclosed emission factors before using any output for regulatory disclosure
(BRSR, CBAM, EPD).
