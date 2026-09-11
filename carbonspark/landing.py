"""The CarbonSpark landing page: hero, what it does, why it matters, and the
two doors into the tool and the database."""

from __future__ import annotations

import streamlit as st

from carbon_calc.model import Dataset

from . import live
from .state import go, toggle_dark
from .theme import AMBER, DEPARTMENT_ICONS, EMBER, STEEL, hero_art, scope_bars, spark_mark

CHEVRON = """
<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor"
     stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M6 9l6 6 6-6"/>
</svg>"""


def _nav() -> None:
    st.markdown(
        f"""
<div class="cs-nav">
  <span class="cs-brand">{spark_mark(26, st.session_state.dark)} CarbonSpark</span>
  <span class="cs-spacer"></span>
  <a href="#info">Info</a>
  <a href="#usetool">Use Tool</a>
  <a href="#database">Database</a>
</div>""",
        unsafe_allow_html=True,
    )


def _mode_toggle() -> None:
    """A light/dark switch, parked at the top right under the nav."""
    spacer, button = st.columns([9, 1])
    button.button(
        "\u2600\ufe0f Light" if st.session_state.dark else "\u263e Dark",
        on_click=toggle_dark,
        use_container_width=True,
        key="dark_toggle_landing",
    )


def _hero() -> None:
    left, right = st.columns([1.05, 1], gap="large")
    with left:
        st.markdown(
            f"""
<div class="cs-hero">
  <div class="cs-rise cs-eyebrow">Carbon &amp; energy intelligence for steelmaking</div>
  <h1 class="cs-rise">Carbon<em>Spark</em></h1>
  <p class="cs-lede cs-rise-2">
    See what a tonne of stainless steel really costs in carbon — and find the
    combination of scrap, energy and process route that costs less.
  </p>
</div>""",
            unsafe_allow_html=True,
        )
        # The calculator is the point of the page, so the way in sits in the
        # hero rather than five sections below it.
        with st.container(key="cs_hero_cta"):
            action, _ = st.columns([1.05, 1.4])
            action.button(
                "Open the calculator  \u2192",
                on_click=go,
                args=("loading",),
                type="primary",
                use_container_width=True,
                key="hero_launch",
            )
        st.markdown(
            f'<div class="cs-hero-foot">'
            f'<div class="cs-scroll-hint cs-rise-3">{CHEVRON}'
            f"<span>or read what it does</span></div></div>",
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(f'<div class="cs-hero" style="min-height:auto">{hero_art(st.session_state.dark)}</div>',
                    unsafe_allow_html=True)


def _info(dataset: Dataset) -> None:
    st.markdown(
        f"""
<div class="cs-section" id="info">
  <div class="cs-eyebrow">Info</div>
  <h2>What CarbonSpark does</h2>
  <p>
    It turns a carbon accounting spreadsheet into something you can steer. Set the scrap
    ratio, the electricity mix and the process route; {len(dataset.processes)} process steps
    recompute live from the plant's own formulas.
  </p>
</div>""",
        unsafe_allow_html=True,
    )
    cards = [
        (EMBER, "Accounting", "Scope 1, 2 and 3",
         "Direct, purchased electricity and upstream Cat. 1-8 \u2014 per department and per step."),
        (AMBER, "Control", "Every lever, live",
         "Scrap ratio, seven energy sources, rail vs road per leg, technology at 48 stages."),
        (STEEL, "Search", "A lower-carbon answer",
         "An optimiser that searches the whole space under practical limits."),
    ]
    left, right = st.columns([1.25, 1], gap="large")
    with left:
        for colour, icon, title, body in cards:
            st.markdown(
                f'<div class="cs-card cs-rise" style="--accent:{colour}">'
                f'<div class="cs-card-icon">{icon}</div>'
                f"<h3>{title}</h3><p>{body}</p></div>",
                unsafe_allow_html=True,
            )
    with right:
        st.markdown(
            '<div class="cs-figure cs-rise-2">'
            '<div class="cs-figure-label">A default route, by scope</div>'
            f"{scope_bars()}"
            '<p class="cs-figure-note">Scope 2 dominates on today\u2019s Indian grid \u2014 '
            "the electricity mix is the biggest lever.</p>"
            "</div>",
            unsafe_allow_html=True,
        )


def _route_strip(dataset: Dataset) -> None:
    """The plant as a line of departments — the shape of what the tool models."""
    steps = "".join(
        f'<span class="cs-step">{DEPARTMENT_ICONS.get(name, "•")} <b>{name}</b></span>'
        for name in dataset.departments
    )
    st.markdown(
        f"""
<div class="cs-section" style="padding-top:26px">
  <div class="cs-eyebrow">The route</div>
  <h2>Raw material in, finished coil out</h2>
  <p>
    Eight departments, {len(dataset.processes)} process steps, and every interchangeable
    technology the workbook records between them — all of it yours to switch.
  </p>
  <div class="cs-strip">{steps}</div>
</div>""",
        unsafe_allow_html=True,
    )


def _how() -> None:
    """Three steps, so a first-time visitor knows what using it involves."""
    st.markdown(
        """
<div class="cs-section">
  <div class="cs-eyebrow">How it works</div>
  <h2>Three moves from spreadsheet to answer</h2>
</div>""",
        unsafe_allow_html=True,
    )
    steps = [
        ("01", "Set the charge",
         "Choose how much of the melt is recycled scrap and how the inbound and outbound "
         "tonnes travel — rail or road, arriving or leaving."),
        ("02", "Set the supply",
         "Move the seven grid shares, or start from the Indian grid, a half-renewable "
         "position or near-zero supply."),
        ("03", "Read the consequence",
         "Scope 1, 2 and 3 per tonne, split by department and by gas, against a baseline "
         "you captured — and the lowest-carbon route the optimiser can find."),
    ]
    for column, (number, title, body) in zip(st.columns(3, gap="large"), steps):
        column.markdown(
            f'<div class="cs-card cs-rise"><div class="cs-stat" style="font-size:1.5rem">'
            f"{number}</div><h3>{title}</h3><p>{body}</p></div>",
            unsafe_allow_html=True,
        )


def _why() -> None:
    st.markdown(
        """
<div class="cs-section">
  <div class="cs-eyebrow">Why it matters</div>
  <h2>Carbon intensity is decided long before it is measured</h2>
  <p>
    A tonne's intensity is set upstream of the meter — by the scrap charged, the
    electricity bought and the route the metal takes. Those choices are usually made
    without anyone seeing their carbon consequence.
  </p>
  <p>
    The gap is not measurement; it is visibility while the decision is still open.
    Every option here is priced in tCO<sub>2</sub>e per tonne before you pick it.
  </p>
</div>""",
        unsafe_allow_html=True,
    )
    stats = [
        (EMBER, 0.56, "~6.1", "tCO\u2082e per tonne on the default route"),
        (AMBER, 0.72, "72%", "lower under the optimiser\u2019s practical limits"),
        (STEEL, 1.00, "48", "process stages you can reconfigure"),
    ]
    for column, (colour, _, figure, label) in zip(st.columns(3, gap="large"), stats):
        column.markdown(
            f'<div class="cs-stat-row cs-rise" style="--accent:{colour}">'
            f'<div class="cs-stat">{figure}</div>'
            f'<p class="cs-stat-label">{label}</p></div>',
            unsafe_allow_html=True,
        )


def _tool_door() -> None:
    st.markdown(
        """
<div class="cs-section" id="usetool">
  <div class="cs-eyebrow">Use Tool</div>
  <h2>Open the calculator</h2>
  <p>
    Pick a starting point — a custom route or a built-in site profile — then move the
    levers and watch every breakdown respond.
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
        st.caption("Opens the full calculator: inputs, scope and department charts, baseline and optimiser.")
    with right:
        st.markdown(f'<div class="cs-shot">{_tool_preview()}</div>', unsafe_allow_html=True)


def _tool_preview() -> str:
    """A miniature rendering of the tool's own layout."""
    return """
<svg viewBox="0 0 640 330" aria-label="Preview of the CarbonSpark tool">
  <rect width="640" height="330" fill="#0b1017"/>
  <rect x="0" y="0" width="640" height="34" fill="#060a0f"/>
  <circle cx="22" cy="17" r="6" fill="#e8a020"/>
  <rect x="38" y="11" width="86" height="11" rx="5" fill="#42525f"/>
  <rect x="14" y="48" width="176" height="266" rx="10" fill="#141d28" stroke="#2a3644"/>
  <rect x="28" y="62" width="148" height="52" rx="8" fill="#111b26"/>
  <rect x="28" y="124" width="148" height="52" rx="8" fill="#1b2735"/>
  <rect x="28" y="186" width="148" height="52" rx="8" fill="#1b2735"/>
  <rect x="206" y="48" width="420" height="120" rx="10" fill="#111a24" stroke="#2a3644"/>
  <g opacity="0.9">
    <rect x="226" y="70" width="54" height="76" rx="5" fill="#2f7fb5"/>
    <rect x="316" y="70" width="54" height="76" rx="5" fill="#2f7fb5" opacity=".8"/>
    <rect x="406" y="70" width="54" height="76" rx="5" fill="#2f7fb5" opacity=".6"/>
    <rect x="496" y="70" width="54" height="76" rx="5" fill="#1f8a5f"/>
    <path d="M280 108 h36 M370 108 h36 M460 108 h36" stroke="#d94f2b" stroke-width="3"/>
  </g>
  <rect x="206" y="180" width="420" height="134" rx="10" fill="#111a24" stroke="#2a3644"/>
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
    No black box. All {len(dataset.processes)} process rows with their formulas and
    coefficient notes, the seven grid factors and the Scope 3 categories — as the
    workbook has them.
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
  <rect width="640" height="260" fill="#0e1620"/>
  <rect x="0" y="0" width="640" height="34" fill="#243447"/>
  <g fill="#8ea3b8">
    <rect x="20" y="12" width="70" height="10" rx="5"/><rect x="150" y="12" width="90" height="10" rx="5"/>
    <rect x="300" y="12" width="70" height="10" rx="5"/><rect x="430" y="12" width="110" height="10" rx="5"/>
  </g>
  <g fill="#141d28">
    <rect x="0" y="44" width="640" height="26"/><rect x="0" y="96" width="640" height="26"/>
    <rect x="0" y="148" width="640" height="26"/><rect x="0" y="200" width="640" height="26"/>
  </g>
  <g fill="#3d4c5d">
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
    live.enable("landing")
    _nav()
    _mode_toggle()
    _hero()
    _info(dataset)
    _route_strip(dataset)
    _how()
    _why()
    _tool_door()
    _database_door(dataset)
    st.markdown(
        """
<div class="cs-section" style="padding-bottom:40px">
  <p style="font-size:.86rem;opacity:.75">
    <b>Disclaimer.</b> The workbook's coefficients are illustrative, not measured or
    verified for any specific plant. Replace them with verified plant data before using
    any output for regulatory disclosure (BRSR, CBAM, EPD).
  </p>
</div>""",
        unsafe_allow_html=True,
    )
