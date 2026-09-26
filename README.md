# CarbonSpark

Carbon and energy calculator for stainless steelmaking — **Problem Statement 3** of the
Jindal Stainless engineering case study. Estimate CO₂e per tonne from the input mix, the
energy mix and the process route; see how each input moves the result; and find
lower-carbon combinations that stay practical.

Every figure comes from evaluating the formula definitions in
`data/source/Stainless_Steel_Carbon_Accounting_Grid_5.xlsx` — **67 process steps × 11 metrics** — at
the chosen scrap ratio (`y`), grid shares (`a`–`g`) and per-leg rail/road split (`p`/`q`).
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

* an **inputs drawer** (45% of the width, opened from the toolbar, with the main content
  scaling to match) holding three panels — *scrap vs virgin*, *energy grid mix*, *plant
  customisation* — each fronted by its own artwork until you pick one. It holds its
  position while the page scrolls and scrolls on its own;
* **staged panels**: the grid mix and the process route are edited as a draft and reach
  the model when Apply is pressed, from a bar docked at the foot of the drawer. Seven
  shares or fifty tick-boxes are one decision, not fifty;
* a **light/dark switch** on every page, each mode's chart palette validated against its
  own surface rather than flipped from the other;
* **full-width charts**, one per screen with a scroll hint between them: where the carbon
  sits, then the department split, then the gas-by-gas table. Both are drawn against a
  fixed axis so a scenario that halves its carbon visibly halves, and the bars tween
  between renders rather than jumping;
* **live slider readouts** — the chips describing a slider follow the thumb as it is
  dragged, while the model's own figures commit when the slider is released;
* **baseline comparison**, **optimiser** and **process grid** views.

**Database** — the accounting grid itself: every formula, every emission factor and its
basis, the downstream Scope 3 categories, the calibration record, and the notation. The
source workbook can be downloaded from there.

## Starting points

`Custom` plus two JSL site profiles. Their **process routes are sourced**; their
**energy-mix percentages, scrap ratios and haulage splits are estimates**, since neither
site publishes a source-wise breakdown of the electricity it consumes. The app labels that
split wherever a profile is shown. The scrap ratios (Jajpur 68%, Hisar 75%, Custom 70%) are
set so the capacity-weighted average matches the 70.12% scrap Jindal Stainless disclosed
company-wide for FY26.

| Profile | Route (sourced) |
| --- | --- |
A site profile switches on only the equipment publicly described for that site — it is
not an inventory of the plant, and anything left unticked is unevidenced rather than known
to be absent.

| **JSL Jajpur** | Ferrochrome from submerged arc furnaces into an EAF, 150 t AOD converter, 150 t ladle furnace, single-strand slab caster ([Primetals](https://www.primetals.com/press-media/news/primetals-technologies-receives-fac-for-new-aod-converter-ladle-furnace-and-stainless-caster-at-jsl)); 30+ MWp captive solar, ~44.3 MU/year ([Jindal Stainless](https://www.jindalstainless.com/press-releases/jindal-stainless-and-ab-energia-set-new-benchmark-with-odishas-largest-captive-industrial-solar-plant/)) |
| **JSL Hisar** | Stainless melt shop plus the cold-rolling complex — four 20-Hi Sendzimir mills, three continuous anneal-and-pickle lines, a bright annealing line ([ANDRITZ](https://www.andritz.com/metals-en/news-media/references-and-success-stories/jindal-india), [Jindal Stainless](https://www.jindalstainless.com/50years/)) |

## The model

* **Input-mix driven** — `x·EF_virgin + y·EF_scrap`, with `x = 1 − y`. Covers Scope 1,
  Scope 3 upstream, the trace gases and specific energy.
* **Grid-mix driven** — Scope 2 is
  `(x·kWh_virgin + y·kWh_scrap) × (a·EF_coal + … + g·EF_nuclear) / 1000`.
* **Haulage-driven** — the two transport rows (inbound unloading, outbound despatch) blend
  rail and road as `p` and `q = 1 − p`. Each leg carries its own `p`, set on the transport
  step itself, because a plant can rail its raw material in and truck its coil out. A
  further slider splits the tonne-movement between the two legs: both rows are stated per
  tonne moved, so 50% is the workbook as published, and the panel reports the split the
  workbook's own rows imply (54% of transport carbon, 59% of transport energy inbound).

**Total CO₂e/t = Scope 1 + Scope 2 + Scope 3 (upstream, Cat. 1-8).** The gas-by-gas columns
are a disaggregation of the same footprint, reported separately and never added into the
total.

### Routes split, they never sum

Stages that list interchangeable variations (melting by EAF / IF / BF-converter / VIM /
VAR / ESR, decarburisation by AOD / VOD / K-OBM-S / CLU, eight casting variants) can run
more than one technology at once. Selecting several **splits that stage's tonne between
them by share**, so a stage always accounts for exactly one tonne of throughput. Adding EAF
at 60% and IF at 40% lands exactly on the weighted average of the two — never their sum,
which is what made a naive read of the whole grid produce an impossible 19.4 tCO₂e/t (17.7 on the Grid 5 coefficients).

### The optimiser is exact, not heuristic

1. **Grid mix.** Scope 2 is `kWh × EF_mix / 1000` with `kWh ≥ 0`, so the mix with the
   lowest `EF_mix` inside the limits is best whatever else is chosen. It is found exactly:
   meet each floor, then fill from the cleanest source with headroom.
2. **Technology.** With the mix fixed, stages are additive, so each is minimised on its own.
   Only genuine alternatives are compared (`route.SUBSTITUTE_GROUPS`): melting furnaces,
   decarburisers, casters. A ladle furnace is never "replaced" by argon stirring.
3. **Scrap and rail.** For a fixed route every formula is linear in the scrap share and in
   each leg's rail share, so the minimum over the allowed box is at a corner. The search
   evaluates all 2 × 2 × 2 = 8 corners (scrap min/max × inbound rail min/max × outbound rail
   min/max), each with its best technology, and the page shows all eight as the proof.

The page also breaks the saving down lever by lever (a waterfall that adds up exactly to
the gap), and reviews the current choices (`carbon_calc/advice.py`): each lever priced on
its own, ranked, plus the limits the optimum is pressed against and what relaxing them is
worth. A button writes a review of the current choices (verdict, strengths, biggest gaps
and why, an ordered action plan, binding limits). It works with no setup: the built-in
writer (`carbonspark/ai_review.py`) composes it from the model's own figures. With
`ANTHROPIC_API_KEY` set (environment or `.streamlit/secrets.toml`), Claude writes it instead,
from the same figures.

Infeasible constraint sets are reported rather than silently relaxed.

## Calibration (Grid 5)

The prelim ran on Grid 4, whose coefficients were illustrative. They overstated the footprint:
the Jajpur route came out at ~4.6 tCO₂e/t with Scope 1+2 at ~3.2, against the 1.76–2.15
tCO₂e/tcs Scope 1+2 intensity Jindal Stainless discloses. Nearly all of the excess was
electricity: the route summed to ~3,300 kWh/t and ~34 GJ/t, where stainless melt-to-coil
routes run at roughly 1,000–1,200 kWh/t and 10–15 GJ/t.

Grid 5 (`data/source/Stainless_Steel_Carbon_Accounting_Grid_5.xlsx`) keeps Grid 4's sheets,
headers, 67 rows, departments, variables, formula shapes and grid emission factors, and
recalibrates the per-row coefficients:

* **Electricity** per row, benchmarked stage by stage (EAF 460 kWh/t on scrap and 650 on a
  virgin-heavy charge, AOD ~45–60, LF ~35–55, caster ~30, hot strip mill ~120 in all,
  Sendzimir ~140).
* **Scope 1**, checked against process chemistry: EAF ~0.10 t/t on scrap (electrodes 1.2–3 kg/t,
  charge carbon), AOD/CLU decarburisation 0.05–0.09, reheating ~1.3 GJ/t of gas.
* **Scope 3 of the charge**, raised from 1.1 to 3.2 tCO₂e per tonne of virgin charge,
  because ferrochrome, nickel units and pig iron carry more upstream carbon than Grid 4
  assumed. Scrap enters at 0.2. This matches the worldstainless finding that Scope 3 is
  linear in scrap share, and it is why scrap is the biggest lever in the model.
* **Trace gases** follow Scope 1 (CO₂, CH₄, N₂O) or electricity (HFC, PFC, SF₆, NF₃).
  **Specific energy** is final energy, `0.0036 × kWh + fuel`.
* The two **transport rows** are unchanged.

| | Grid 4 | Grid 5 | Reference |
| --- | --- | --- | --- |
| Jajpur total | 4.60 | **2.89** | — |
| Jajpur Scope 1+2 | 3.19 | **1.28** | JSL 1.76 (FY26), which also covers captive FeCr and captive power |
| Jajpur Scope 1 | 0.69 | **0.44** | worldstainless average ~0.4 |
| Jajpur electricity (kWh/t) | 3,283 | **1,091** | ~1,000–1,200 |
| Jajpur specific energy (GJ/t) | 33.9 | **9.8** | ~10–15 |
| Hisar total | 4.67 | **2.93** | — |
| Default route total | 6.17 | **4.04** | runs every finishing line at once |

Each row's notes carry its Grid 4 → Grid 5 change and the reason for it. The workbook's
**Calibration Basis** sheet holds the benchmarks and a row-by-row comparison, and the
Database page shows both. To change a coefficient, edit the table in
`scripts/calibrate_workbook.py` (or the workbook directly), then regenerate:

```bash
python scripts/calibrate_workbook.py   # Grid 4 -> Grid 5 workbook
python scripts/extract_workbook.py     # Grid 5 workbook -> data/carbon_grid.json
```

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
scripts/calibrate_workbook.py Builds the calibrated Grid 5 workbook from Grid 4
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

The coefficients in the source workbook are calibrated against published industry and
company benchmarks (see Calibration above). They are not measured or independently verified for any
specific plant or grid connection. Replace them with verified plant data and your utility's
disclosed emission factors before using any output for regulatory disclosure (BRSR, CBAM,
EPD).
