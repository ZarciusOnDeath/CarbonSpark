"""The database view: the accounting workbook itself, nothing hidden."""

from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from carbon_calc.model import METRICS, METRIC_LABELS, MIX_VARIABLES, Dataset

from . import live
from .notes import parse as parse_note
from .state import go, toggle_dark
from .theme import spark_mark


def _variation(variation: str) -> str:
    """Match the tool's naming for the workbook's catch-all variation."""
    return "General estimate" if variation.strip().lower().startswith("general") else variation


def render(dataset: Dataset) -> None:
    live.enable("database")
    bar = st.columns([4.0, 0.8, 1.5, 1.3])
    bar[0].markdown(
        f'<div style="display:flex;align-items:center;gap:10px;font-weight:800;'
        f'font-size:1.1rem">{spark_mark(24, st.session_state.dark)} CarbonSpark '
        f'<span class="cs-chip">database</span></div>',
        unsafe_allow_html=True,
    )
    bar[1].button(
        "☀️" if st.session_state.dark else "☾",
        on_click=toggle_dark,
        use_container_width=True,
        help="Switch to light mode" if st.session_state.dark else "Switch to dark mode",
        key="dark_toggle_db",
    )
    bar[2].button("Use the tool", on_click=go, args=("loading",), use_container_width=True)
    bar[3].button("← Back to site", on_click=go, args=("landing",), use_container_width=True)
    st.divider()

    st.markdown(
        f"""
<div class="cs-eyebrow">Database</div>
<h2 style="margin-top:0">The carbon accounting grid</h2>
<p style="color:var(--ink-soft);max-width:74ch">
  Every figure the tool reports comes from evaluating these formula definitions —
  {len(dataset.processes)} process steps, eleven metrics each — at the chosen scrap
  ratio, grid mix and haulage split. The formulas are stored as text and parsed
  against a whitelist of the eleven model variables and the arithmetic operators.
</p>""",
        unsafe_allow_html=True,
    )

    processes, factors, downstream, notation = st.tabs(
        ["Process formulas", "Grid emission factors", "Downstream Scope 3", "Notation"]
    )

    with processes:
        rows = [
            {
                "#": proc.id,
                "Department": proc.department,
                "Technique / Process": proc.process,
                "Variation": _variation(proc.variation),
                **{METRIC_LABELS[metric]: proc.formulas[metric] for metric in METRICS},
            }
            for proc in dataset.processes
        ]
        frame = pd.DataFrame(rows)
        # Filters start empty: an empty filter means "no department chosen yet",
        # and the grid shows everything until one is.
        picked = st.multiselect(
            "Departments", dataset.departments, default=[], key="db_depts",
            placeholder="All departments",
        )
        search = st.text_input("Search techniques and variations", key="db_search").strip().lower()
        view = frame[frame["Department"].isin(picked)] if picked else frame
        if search:
            haystack = (
                view["Technique / Process"].str.lower() + " " + view["Variation"].str.lower()
            )
            view = view[haystack.str.contains(search, regex=False)]
        st.caption(f"{len(view)} of {len(frame)} rows")
        st.dataframe(view, use_container_width=True, hide_index=True, height=460)
        st.download_button(
            "Download the formula grid as CSV",
            frame.to_csv(index=False).encode("utf-8"),
            file_name="carbonspark_formula_grid.csv",
            mime="text/csv",
        )

        st.markdown("#### Coefficients behind a row")
        chosen = st.selectbox(
            "Process step",
            options=[proc.id for proc in dataset.processes],
            format_func=lambda pid: next(
                p.label for p in dataset.processes if p.id == pid
            ),
            key="db_row",
        )
        proc = next(p for p in dataset.processes if p.id == chosen)
        st.dataframe(
            pd.DataFrame(
                [
                    {"Metric": METRIC_LABELS[metric], "Formula": proc.formulas[metric]}
                    for metric in METRICS
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
        # A row's note mixes prose with a dense run of NAME=value listings.
        # Printed as one block the prose disappeared into the numbers, so the
        # two are separated: coefficients into a table, the rest as notes.
        paragraphs, coefficients = parse_note(proc.notes)
        if coefficients:
            st.markdown("**Coefficients behind these formulas**")
            st.dataframe(
                pd.DataFrame(coefficients),
                use_container_width=True,
                hide_index=True,
                height=min(420, 40 + 36 * len(coefficients)),
            )
        if paragraphs:
            st.markdown("**Basis and caveats**")
            st.markdown(
                '<div class="cs-note">'
                + "".join(f"<p>{html.escape(text)}</p>" for text in paragraphs)
                + "</div>",
                unsafe_allow_html=True,
            )
        if not coefficients and not paragraphs:
            st.caption("No notes recorded for this row.")

    with factors:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Source": dataset.source_by_var[var].source,
                        "Variable": var,
                        "kg CO₂e/kWh": dataset.source_by_var[var].ef,
                        "Basis / notes": dataset.source_by_var[var].basis,
                    }
                    for var in MIX_VARIABLES
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            "Scope 2 for any row is (kWh through that row) × (share-weighted factor) / 1000."
        )

    with downstream:
        st.caption(
            "Product-level categories from the workbook's second sheet. Only Category 9 "
            "varies by process, and it is already carried in the outbound transport row; "
            "the rest are qualitative framing and are not quantified in the tool's total."
        )
        st.dataframe(
            pd.DataFrame(list(dataset.downstream)).rename(
                columns={
                    "category": "Category",
                    "applicability": "Applicability",
                    "notes": "Notes",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    with notation:
        st.markdown(
            """
| Symbol | Meaning |
| --- | --- |
| `x` | Virgin steel ratio |
| `y` | Scrap steel ratio, `y = 1 − x` |
| `a` … `g` | Grid shares: coal, oil, gas, hydro, wind, solar, nuclear — summing to 1 |
| `p` | Rail share of haulage |
| `q` | Road share, `q = 1 − p` |

**Total CO₂e per tonne = Scope 1 + Scope 2 + Scope 3 (upstream, Cat. 1-8).**
The gas-by-gas columns are a disaggregation of the same footprint, so they are
reported separately and never added into that total.

Stages that list interchangeable variations split their tonne between whichever
variations are selected, so a stage always accounts for exactly one tonne of
throughput however many technologies run in parallel.
            """
        )
        st.warning(
            "**Disclaimer.** The coefficients in the source workbook are illustrative values "
            "chosen to demonstrate a working, formula-linked model. They are not measured or "
            "independently verified for any specific plant or grid connection. Replace them "
            "with verified plant data and your utility's disclosed emission factors before "
            "using any output for regulatory disclosure (BRSR, CBAM, EPD)."
        )
