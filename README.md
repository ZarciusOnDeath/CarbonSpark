# CarbonSpark

Carbon and energy calculator for stainless steelmaking — **Problem Statement 3** of the
Jindal Stainless engineering case study. Estimate CO₂e per tonne from the input mix, the
energy mix and the process route; see how each input moves the result; and find
lower-carbon combinations that stay practical.

Every figure comes from evaluating the formula definitions in
`Stainless Steel Carbon Accounting Grid (4).xlsx` — **67 process steps × 11 metrics** — at
the chosen scrap ratio (`y`), grid shares (`a`–`g`) and rail/road haulage split (`p`/`q`).
No coefficients are re-derived or hard-coded in application code.

## Running it

```bash
pip install -r requirements.txt
streamlit run app.py
```

Opens at http://localhost:8501 (Python 3.9+).

## The three screens

**Landing** — a CarbonSpark hero with generated industrial artwork, a sticky nav that keeps
the brand top-left, and scroll-through sections: what the tool does, why it matters, and
doors into the tool and the database.

**Tool** — entered through a two-second welcome, then:

* an **inputs drawer** (30% of the width, opened by the button beside the readings it
  changes, with the main content scaling to match) holding three panels — *scrap vs
  virgin*, *energy grid mix*, *plant customisation* — each fronted by its own artwork
  until you pick one;
* **full-width charts**, one per screen with a scroll hint between them: where the carbon
  sits, then the department split, then the gas-by-gas table;
* **live slider readouts** — the chips describing a slider follow the thumb as it is
  dragged, while the model's own figures commit when the slider is released;
* **baseline comparison**, **optimiser** and **process grid** views.

**Database** — the accounting grid itself: every formula, every emission factor and its
basis, the downstream Scope 3 categories, and the notation.

## Starting points

`Custom` plus two JSL site profiles. Their **process routes are sourced**; their
**energy-mix percentages, scrap ratios and haulage splits are estimates**, since neither
site publishes a source-wise breakdown of the electricity it consumes. The app labels that
split wherever a profile is shown.

| Profile | Route (sourced) |
| --- | --- |
| **JSL Jajpur** | Ferrochrome from submerged arc furnaces into an EAF, 150 t AOD converter, 150 t ladle furnace, single-strand slab caster ([Primetals](https://www.primetals.com/press-media/news/primetals-technologies-receives-fac-for-new-aod-converter-ladle-furnace-and-stainless-caster-at-jsl)); 30+ MWp captive solar, ~44.3 MU/year ([Jindal Stainless](https://www.jindalstainless.com/press-releases/jindal-stainless-and-ab-energia-set-new-benchmark-with-odishas-largest-captive-industrial-solar-plant/)) |
| **JSL Hisar** | Stainless melt shop plus the cold-rolling complex — four 20-Hi Sendzimir mills, three continuous anneal-and-pickle lines, a bright annealing line ([ANDRITZ](https://www.andritz.com/metals-en/news-media/references-and-success-stories/jindal-india), [Jindal Stainless](https://www.jindalstainless.com/50years/)) |

## The model

* **Input-mix driven** — `x·EF_virgin + y·EF_scrap`, with `x = 1 − y`. Covers Scope 1,
  Scope 3 upstream, the trace gases and specific energy.
* **Grid-mix driven** — Scope 2 is
  `(x·kWh_virgin + y·kWh_scrap) × (a·EF_coal + … + g·EF_nuclear) / 1000`.
* **Haulage-driven** — the two transport rows (RMHS unloading, outbound despatch) blend
  rail and road as `p` and `q = 1 − p`, and a second slider splits the tonne-movement
  between the inbound and outbound legs. Both rows are stated per tonne moved, so 50%
  is the workbook as published; the panel reports the split the workbook's own rows
  imply (54% of transport carbon, 59% of transport energy on the inbound leg).

**Total CO₂e/t = Scope 1 + Scope 2 + Scope 3 (upstream, Cat. 1-8).** The gas-by-gas columns
are a disaggregation of the same footprint, reported separately and never added into the
total.

### Routes split, they never sum

Stages that list interchangeable variations (melting by EAF / IF / BF-converter / VIM /
VAR / ESR, decarburisation by AOD / VOD / K-OBM-S / CLU, eight casting variants) can run
more than one technology at once. Selecting several **splits that stage's tonne between
them by share**, so a stage always accounts for exactly one tonne of throughput. Adding EAF
at 60% and IF at 40% lands exactly on the weighted average of the two — never their sum,
which is what made a naive read of the whole grid produce an impossible 19.4 tCO₂e/t.

### The optimiser is exact, not heuristic

1. Scope 2 is `kWh × EF_mix / 1000` with `EF_mix` a share-weighted average, so the best mix
   is independent of scrap ratio and route → solved once as a bounded linear program.
2. Stages are additive → the best variation at each unlocked stage is chosen independently.
3. Both transport rows are linear in `p`, so the best rail share is always at a bound.
4. That leaves a one-dimensional sweep over the allowed scrap-ratio range.

Infeasible constraint sets are reported rather than silently relaxed.

## Layout

```
app.py                        Router
carbon_calc/formulas.py       AST-based safe evaluator for the workbook's formula text
carbon_calc/model.py          Dataset loading, per-process evaluation, aggregation
carbon_calc/route.py          Stage grouping and share-weighted route mixes
carbon_calc/optimize.py       Constraint handling and the lowest-carbon search
carbonspark/landing.py        Landing page
carbonspark/loading.py        Welcome and loading screen
carbonspark/tool.py           Drawer, dashboard, baseline, optimiser, process grid
carbonspark/database.py       Formula and factor browser
carbonspark/charts.py         Figures — zoom and pan disabled on every one
carbonspark/theme.py          Palette and generated SVG artwork
carbonspark/presets.py        Grid mixes and the JSL plant profiles
carbonspark/state.py          Session state
scripts/extract_workbook.py   Regenerates data/carbon_grid.json from the .xlsx
tests/                        pytest suite (run with `python -m pytest`)
```

Formula strings are parsed to an AST and evaluated against a whitelist of the eleven model
variables and the arithmetic operators — `eval` is never used on workbook content.

### Two Streamlit behaviours worth knowing

* **Charts** have `fixedrange` on both axes, `dragmode` off and the mode bar hidden, so
  nothing zooms by accident. Hover stays on.
* **Widget state** is held in plain session keys (`mix`, `scrap`, `train`) rather than in
  widget keys, because a widget key written in an *earlier* run renders at its minimum even
  though session state holds the right value. That quirk is why presets used to appear to
  leave the sliders untouched.

## Disclaimer

The coefficients in the source workbook are illustrative values chosen to demonstrate a
working, formula-linked model. They are not measured or independently verified for any
specific plant or grid connection. Replace them with verified plant data and your utility's
disclosed emission factors before using any output for regulatory disclosure (BRSR, CBAM,
EPD).
