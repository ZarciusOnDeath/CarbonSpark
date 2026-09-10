"""The CarbonSpark landing page: hero, what it does, why it matters, and the
two doors into the tool and the database."""

from __future__ import annotations

import streamlit as st

from carbon_calc.model import Dataset

from .state import go
from .theme import hero_art, spark_mark

CHEVRON = """
<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor"
     stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M6 9l6 6 6-6"/>
</svg>"""


def _nav() -> None:
    st.markdown(
        f"""
<div class="cs-nav">
  <span class="cs-brand">{spark_mark(26)} CarbonSpark</span>
  <span class="cs-spacer"></span>
  <a href="#info">Info</a>
  <a href="#usetool">Use Tool</a>
  <a href="#database">Database</a>
</div>""",
        unsafe_allow_html=True,
    )


def _hero() -> None:
    left, right = st.columns([1.05, 1], gap="large")
    with left:
        st.markdown(
            f"""
<div class="cs-hero">
  <div class="cs-rise cs-eyebrow">Carbon &amp; energy intelligence for steelmaking</div>
  <h1 class="cs-rise">Carbon<span>Spark</span></h1>
  <p class="cs-lede cs-rise-2">
    See what a tonne of stainless steel really costs in carbon — and find the
    combination of scrap, energy and process route that costs less.
  </p>
  <div class="cs-scroll-hint cs-rise-3">{CHEVRON}<span>Scroll to explore</span></div>
</div>""",
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(f'<div class="cs-hero" style="min-height:auto">{hero_art()}</div>',
                    unsafe_allow_html=True)


def _info(dataset: Dataset) -> None:
    st.markdown(
        f"""
<div class="cs-section" id="info">
  <div class="cs-eyebrow">Info</div>
  <h2>What CarbonSpark does</h2>
  <p>
    It turns a carbon accounting spreadsheet into something you can actually steer.
    Set the scrap-to-virgin ratio, the electricity mix and the process route, and every
    number on screen recomputes from the plant's own formulas — {len(dataset.processes)}
    process steps, eleven metrics each, evaluated live.
  </p>
</div>""",
        unsafe_allow_html=True,
    )
    cards = [
        ("Scope 1, 2 and 3", "Direct combustion, purchased electricity and upstream Cat. 1-8, "
                             "split out per department and per process step."),
        ("Every lever, live", "Scrap ratio, seven electricity sources, rail-versus-road haulage "
                              "and the technology at each of 48 stages."),
        ("A lower-carbon answer", "An optimiser that searches the whole space under your own "
                                  "practical constraints and returns the route that costs least."),
    ]
    columns = st.columns(3, gap="medium")
    for column, (title, body) in zip(columns, cards):
        column.markdown(
            f'<div class="cs-card cs-rise"><h3>{title}</h3><p>{body}</p></div>',
            unsafe_allow_html=True,
        )


def _why() -> None:
    st.markdown(
        """
<div class="cs-section">
  <div class="cs-eyebrow">Why it matters</div>
  <h2>Carbon intensity is decided long before it is measured</h2>
  <p>
    Stainless steelmaking is energy- and emissions-intensive, and the intensity of any
    given tonne is set by choices made upstream of the meter: how much scrap goes into
    the charge, where the electricity comes from, which furnace and casting route the
    metal takes. Those decisions are usually made without anyone seeing their carbon
    consequence at the moment of choosing.
  </p>
  <p>
    With a net-zero-by-2050 commitment on the table, the gap that matters is not
    measurement — it is visibility while the decision is still open. CarbonSpark closes
    that gap: every option is priced in tCO<sub>2</sub>e per tonne before you pick it.
  </p>
</div>""",
        unsafe_allow_html=True,
    )
    stats = [
        ("~6.1", "tCO₂e per tonne on a default route at 40% scrap, today's Indian grid"),
        ("Up to 72%", "lower under a practical constraint set the optimiser finds"),
        ("48", "process stages you can reconfigure, from raw material handling to despatch"),
    ]
    columns = st.columns(3, gap="medium")
    for column, (figure, label) in zip(columns, stats):
        column.markdown(
            f'<div class="cs-card"><div class="cs-stat">{figure}</div><p>{label}</p></div>',
            unsafe_allow_html=True,
        )


def _tool_door() -> None:
    st.markdown(
        """
<div class="cs-section" id="usetool">
  <div class="cs-eyebrow">Use Tool</div>
  <h2>Open the calculator</h2>
  <p>
    A live model of the plant: pick a starting point — a custom route or one of the two
    JSL site profiles — then move the levers and watch the flow diagram, the scope
    breakdown and the department split respond.
  </p>
</div>""",
        unsafe_allow_html=True,
    )
    left, right = st.columns([1, 1.25], gap="large")
    with left:
        st.button(
            "Launch the tool  →",
            on_click=go,
            args=("loading",),
            type="primary",
            use_container_width=True,
            key="launch_tool",
        )
        st.caption("Opens the full calculator with the input drawer, flow diagram and optimiser.")
    with right:
        st.markdown(f'<div class="cs-shot">{_tool_preview()}</div>', unsafe_allow_html=True)


def _tool_preview() -> str:
    """A miniature rendering of the tool's own layout."""
    return """
<svg viewBox="0 0 640 330" aria-label="Preview of the CarbonSpark tool">
  <rect width="640" height="330" fill="#f7f8fa"/>
  <rect x="0" y="0" width="640" height="34" fill="#0f1720"/>
  <circle cx="22" cy="17" r="6" fill="#e8a020"/>
  <rect x="38" y="11" width="86" height="11" rx="5" fill="#42525f"/>
  <rect x="14" y="48" width="176" height="266" rx="10" fill="#fff" stroke="#e2e6ea"/>
  <rect x="28" y="62" width="148" height="52" rx="8" fill="#111b26"/>
  <rect x="28" y="124" width="148" height="52" rx="8" fill="#1b2735"/>
  <rect x="28" y="186" width="148" height="52" rx="8" fill="#1b2735"/>
  <rect x="206" y="48" width="420" height="120" rx="10" fill="#fff" stroke="#e2e6ea"/>
  <g opacity="0.9">
    <rect x="226" y="70" width="54" height="76" rx="5" fill="#2f7fb5"/>
    <rect x="316" y="70" width="54" height="76" rx="5" fill="#2f7fb5" opacity=".8"/>
    <rect x="406" y="70" width="54" height="76" rx="5" fill="#2f7fb5" opacity=".6"/>
    <rect x="496" y="70" width="54" height="76" rx="5" fill="#1f8a5f"/>
    <path d="M280 108 h36 M370 108 h36 M460 108 h36" stroke="#d94f2b" stroke-width="3"/>
  </g>
  <rect x="206" y="180" width="420" height="134" rx="10" fill="#fff" stroke="#e2e6ea"/>
  <rect x="226" y="204" width="300" height="22" rx="5" fill="#d94f2b"/>
  <rect x="226" y="236" width="366" height="22" rx="5" fill="#e8a020"/>
  <rect x="226" y="268" width="188" height="22" rx="5" fill="#2f7fb5"/>
</svg>"""


def _database_door(dataset: Dataset) -> None:
    st.markdown(
        f"""
<div class="cs-section" id="database">
  <div class="cs-eyebrow">Database</div>
  <h2>Look at the data behind it</h2>
  <p>
    Nothing here is a black box. The database view is the accounting grid itself —
    all {len(dataset.processes)} process rows with their formula definitions and
    coefficient notes, the seven grid emission factors and their basis, and the
    downstream Scope 3 categories — exactly as they appear in the workbook.
  </p>
</div>""",
        unsafe_allow_html=True,
    )
    left, right = st.columns([1, 1.25], gap="large")
    with left:
        st.button(
            "Open the database  →",
            on_click=go,
            args=("database",),
            use_container_width=True,
            key="open_db",
        )
        st.caption("Browse and download every formula, factor and assumption.")
    with right:
        st.markdown(
            """
<div class="cs-shot"><svg viewBox="0 0 640 260" aria-label="Preview of the database view">
  <rect width="640" height="260" fill="#fff"/>
  <rect x="0" y="0" width="640" height="34" fill="#243447"/>
  <g fill="#8ea3b8">
    <rect x="20" y="12" width="70" height="10" rx="5"/><rect x="150" y="12" width="90" height="10" rx="5"/>
    <rect x="300" y="12" width="70" height="10" rx="5"/><rect x="430" y="12" width="110" height="10" rx="5"/>
  </g>
  <g fill="#eef1f4">
    <rect x="0" y="44" width="640" height="26"/><rect x="0" y="96" width="640" height="26"/>
    <rect x="0" y="148" width="640" height="26"/><rect x="0" y="200" width="640" height="26"/>
  </g>
  <g fill="#c3ccd6">
    <rect x="20" y="52" width="86" height="10" rx="5"/><rect x="150" y="52" width="150" height="10" rx="5"/>
    <rect x="330" y="52" width="120" height="10" rx="5"/><rect x="480" y="52" width="60" height="10" rx="5"/>
    <rect x="20" y="78" width="70" height="10" rx="5"/><rect x="150" y="78" width="190" height="10" rx="5"/>
    <rect x="360" y="78" width="90" height="10" rx="5"/><rect x="480" y="78" width="80" height="10" rx="5"/>
    <rect x="20" y="104" width="96" height="10" rx="5"/><rect x="150" y="104" width="130" height="10" rx="5"/>
    <rect x="320" y="104" width="150" height="10" rx="5"/><rect x="490" y="104" width="60" height="10" rx="5"/>
    <rect x="20" y="130" width="80" height="10" rx="5"/><rect x="150" y="130" width="170" height="10" rx="5"/>
    <rect x="340" y="130" width="110" height="10" rx="5"/><rect x="470" y="130" width="90" height="10" rx="5"/>
    <rect x="20" y="156" width="90" height="10" rx="5"/><rect x="150" y="156" width="140" height="10" rx="5"/>
    <rect x="310" y="156" width="140" height="10" rx="5"/><rect x="480" y="156" width="70" height="10" rx="5"/>
    <rect x="20" y="182" width="74" height="10" rx="5"/><rect x="150" y="182" width="160" height="10" rx="5"/>
    <rect x="330" y="182" width="120" height="10" rx="5"/><rect x="475" y="182" width="85" height="10" rx="5"/>
    <rect x="20" y="208" width="88" height="10" rx="5"/><rect x="150" y="208" width="120" height="10" rx="5"/>
    <rect x="300" y="208" width="160" height="10" rx="5"/><rect x="486" y="208" width="64" height="10" rx="5"/>
  </g>
</svg></div>""",
            unsafe_allow_html=True,
        )


def render(dataset: Dataset) -> None:
    _nav()
    _hero()
    _info(dataset)
    _why()
    _tool_door()
    _database_door(dataset)
    st.markdown(
        """
<div class="cs-section" style="padding-bottom:40px">
  <p style="font-size:.86rem;opacity:.75">
    <b>Disclaimer.</b> The coefficients in the source workbook are illustrative values
    chosen to demonstrate a working, formula-linked model. They are not measured or
    independently verified for any specific plant or grid connection. Replace them with
    verified plant data and your utility's disclosed emission factors before using any
    output for regulatory disclosure (BRSR, CBAM, EPD).
  </p>
</div>""",
        unsafe_allow_html=True,
    )
