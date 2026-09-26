"""The CarbonSpark landing page: hero, what it does, why it matters, and the
two doors into the tool and the database."""

from __future__ import annotations

import streamlit as st

from carbon_calc.model import Dataset

from . import live
from .state import go, toggle_dark
from .theme import AMBER, DEPARTMENT_ICONS, EMBER, STEEL, page_backdrop, photo_style, wordmark

def _nav() -> None:
    # The mode switch lives in the nav as a link, so it sits with the rest.
    mode = "light" if st.session_state.dark else "dark"
    mode_label = "\u2600\ufe0f Light" if st.session_state.dark else "\u263e Dark"
    st.markdown(
        f"""
<div class="cs-nav">
  <span class="cs-brand">{wordmark(1.9)}</span>
  <span class="cs-spacer"></span>
  <a href="#levers">How it works</a>
  <a href="#database">Database</a>
  <a class="cs-nav-mode" href="?mode={mode}" target="_self">{mode_label}</a>
  <a class="cs-nav-cta" href="?go=tool" target="_self">Open the calculator \u2192</a>
</div>""",
        unsafe_allow_html=True,
    )


def _launch(panel: str | None = None) -> None:
    """Go to the calculator, optionally straight into one input panel."""
    st.session_state.pending_panel = panel
    go("loading")


def _photo_block(key: str, photo: str, shade: float) -> None:
    """Give a keyed container a photo background (set in CSS by its key)."""
    st.markdown(
        f"<style>.st-key-{key} {{ {photo_style(photo, shade)} }}</style>",
        unsafe_allow_html=True,
    )


def _hero() -> None:
    _photo_block("cs_hero_photo", "hero", 0.72)
    with st.container(key="cs_hero_photo"):
        left, right = st.columns([1.25, 1], gap="large")
        with left:
            st.markdown(
                """
<div class="cs-hero cs-on-photo">
  <div class="cs-rise cs-eyebrow">Carbon calculator for stainless steel</div>
  <h1 class="cs-rise">Carbon<em>Spark</em></h1>
  <p class="cs-lede cs-rise-2">
    What does a tonne of stainless steel cost in carbon? Change the scrap, the
    electricity and the route, and see it move.
  </p>
</div>""",
                unsafe_allow_html=True,
            )
            with st.container(key="cs_hero_cta"):
                action, _ = st.columns([1.2, 1.6])
                action.button(
                    "Calculate your footprint  \u2192",
                    on_click=_launch,
                    type="primary",
                    use_container_width=True,
                    key="hero_launch",
                )
        with right:
            st.markdown(_hero_card(), unsafe_allow_html=True)


def _hero_card() -> str:
    """A glass card with one real reading, so the hero shows the output."""
    bars = (
        ("Scope 1 \u00b7 direct", 0.443, EMBER),
        ("Scope 2 \u00b7 electricity", 0.832, AMBER),
        ("Scope 3 \u00b7 upstream", 1.612, STEEL),
    )
    rows = "".join(
        f'<div class="cs-glass-row"><span>{name}</span>'
        f'<i style="width:{value / 1.7 * 100:.0f}%;background:{colour}"></i>'
        f"<b>{value:.2f}</b></div>"
        for name, value, colour in bars
    )
    return f"""
<div class="cs-glass cs-rise-3">
  <div class="cs-glass-label">Example \u00b7 electric-arc route, 68% scrap</div>
  <div class="cs-glass-total">2.89<small> tCO\u2082e per tonne</small></div>
  {rows}
  <div class="cs-glass-foot">Your numbers will differ \u2014 that is the point.</div>
</div>"""


BULLET = "\u2022"

LEVERS = (
    ("scrap", "scrap", "Scrap in the charge",
     "Recycled scrap is the single biggest lever. Slide it and watch Scope 3 fall."),
    ("grid", "grid", "Where the power comes from",
     "Seven sources, from coal to solar. The electricity mix drives Scope 2."),
    ("plant", "mill", "Process route & transport",
     "Tick the furnaces and mills the plant runs, and rail vs road in and out."),
)


def _levers() -> None:
    st.markdown(
        """
<div class="cs-section" id="levers">
  <div class="cs-eyebrow">Three levers</div>
  <h2>Pick one and try it</h2>
</div>""",
        unsafe_allow_html=True,
    )
    for column, (panel, photo, title, body) in zip(st.columns(3, gap="large"), LEVERS):
        with column:
            st.markdown(
                f'<div class="cs-photo-card cs-rise" style="{photo_style(photo, 0.55)}">'
                f"<h3>{title}</h3></div>"
                f'<p class="cs-photo-card-body">{body}</p>',
                unsafe_allow_html=True,
            )
            st.button(
                "Try it  \u2192",
                on_click=_launch,
                args=(panel,),
                use_container_width=True,
                key=f"lever_{panel}",
            )


def _why(dataset: Dataset) -> None:
    st.markdown(
        """
<div class="cs-section">
  <div class="cs-eyebrow">Why it matters</div>
  <h2>Carbon is decided before it is measured</h2>
  <p>The scrap charged, the power bought and the route taken set a tonne\u2019s footprint.
  Here you see the consequence while the choice is still open.</p>
</div>""",
        unsafe_allow_html=True,
    )
    stats = [
        (EMBER, "~4.0", "tCO\u2082e per tonne on the default route"),
        (AMBER, "24%", "lower under the optimiser\u2019s practical limits"),
        (STEEL, str(len(dataset.processes)), "process steps, from raw material to coil"),
    ]
    for column, (colour, figure, label) in zip(st.columns(3, gap="large"), stats):
        column.markdown(
            f'<div class="cs-stat-row cs-rise" style="--accent:{colour}">'
            f'<div class="cs-stat">{figure}</div>'
            f'<p class="cs-stat-label">{label}</p></div>',
            unsafe_allow_html=True,
        )


def _route_strip(dataset: Dataset) -> None:
    steps = "".join(
        f'<span class="cs-step"><i>{index:02d}</i> <b>{name}</b></span>'
        for index, name in enumerate(dataset.departments, start=1)
    )
    st.markdown(
        f"""
<div class="cs-section" style="padding-top:40px">
  <div class="cs-eyebrow">The route</div>
  <h2>Raw material in, finished coil out</h2>
  <div class="cs-strip">{steps}</div>
</div>""",
        unsafe_allow_html=True,
    )


def _cta_band() -> None:
    _photo_block("cs_cta_band", "melt", 0.7)
    with st.container(key="cs_cta_band"):
        st.markdown(
            """
<div class="cs-on-photo">
  <div class="cs-eyebrow">Your turn</div>
  <h2>See your plant\u2019s number in 30 seconds</h2>
  <p>Start from an example plant, then move one slider.</p>
</div>""",
            unsafe_allow_html=True,
        )
        left, _ = st.columns([1, 2.4])
        left.button(
            "Open the calculator  \u2192",
            on_click=_launch,
            type="primary",
            use_container_width=True,
            key="launch_tool",
        )


def _database_door(dataset: Dataset) -> None:
    """The database as one photo panel: the words and the way in sit on the image."""
    _photo_block("cs_db_band", "database", 0.72)
    with st.container(key="cs_db_band"):
        st.markdown(
            f"""
<div class="cs-on-photo" id="database">
  <div class="cs-eyebrow">Database</div>
  <h2>No black box</h2>
  <p>All {len(dataset.processes)} process formulas, the seven grid factors and every source
  behind the numbers, open to read and download.</p>
</div>""",
            unsafe_allow_html=True,
        )
        left, _ = st.columns([1, 2.4])
        left.button(
            "Open the database  \u2192",
            on_click=go,
            args=("database",),
            type="primary",
            use_container_width=True,
            key="open_db",
        )


def render(dataset: Dataset) -> None:
    live.enable("landing")
    st.markdown(page_backdrop("dept_hot", st.session_state.dark), unsafe_allow_html=True)
    _nav()
    _hero()
    _levers()
    _why(dataset)
    _route_strip(dataset)
    _cta_band()
    _database_door(dataset)
    st.markdown(
        """
<div class="cs-section" style="padding-bottom:40px">
  <p style="font-size:.86rem;opacity:.75">
    <b>Disclaimer.</b> Coefficients are calibrated against published benchmarks, not
    measured at any specific plant. Use verified plant data for regulatory disclosure.
  </p>
</div>""",
        unsafe_allow_html=True,
    )
