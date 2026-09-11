"""The CarbonSpark tool: input drawer, plant flow, and the result views."""

from __future__ import annotations

import math
from typing import Dict, List

import pandas as pd
import streamlit as st

from carbon_calc.model import (
    INDIA_GRID_MIX,
    METRIC_LABELS,
    MIX_VARIABLES,
    REFERENCE_GRID_FACTOR,
    SCOPES,
    TRACE_GASES,
    Dataset,
    Result,
    build_variables,
    calculate,
    mix_factor,
)
from carbon_calc.optimize import Constraints, InfeasibleError, optimise
from carbon_calc.route import (
    Stage,
    apply_haulage,
    coefficient_model,
    rail_shares,
    default_route,
    even_mix,
    normalise_mix,
    route_weights,
    transport_ids,
)

from . import charts, live
from .presets import GRID_PRESET_NOTES, GRID_PRESETS, PLANT_PROFILES
from .state import (
    INBOUND_W,
    PRESET_W,
    PROFILE_W,
    SCRAP_W,
    TRAIN_IN_W,
    TRAIN_OUT_W,
    apply_grid_preset,
    apply_plant_profile,
    apply_mix,
    apply_route,
    current_mix,
    draft_mix,
    go,
    inbound_rail,
    inbound_share,
    mix_dirty,
    mix_total,
    mix_widget,
    on_inbound_change,
    on_mix_change,
    on_scrap_change,
    on_train_in_change,
    on_train_out_change,
    outbound_rail,
    rescale_mix,
    revert_mix,
    forget_route_widgets,
    revert_route,
    route_dirty,
    route_key,
    scrap_ratio,
    set_stage_mix,
    toggle_dark,
    train_share,
)
from .theme import DEPARTMENT_ICONS, SCOPE_NAMES, panel_art, section_band, spark_mark

PANELS = [
    ("scrap", "Scrap vs virgin", "How much of the charge is recycled steel"),
    ("grid", "Energy grid mix", "Where the electricity comes from"),
    ("plant", "Plant customisation", "Departments, techniques and variations"),
]

#: Glyphs used in the drill-down titles, kept out of the f-strings that use them.
ALL_ON, SOME_ON, ALL_OFF = "\u2713", "\u2013", "\u00d7"
BULLET, MIDDOT, DASH = "\u2022", "\u00b7", "\u2014"

#: Slider labels, shared with the live-readout chips that follow them.
SCRAP_LABEL = "Scrap steel ratio"
INBOUND_RAIL_LABEL = "Rail share of the inbound leg"
OUTBOUND_RAIL_LABEL = "Rail share of the outbound leg"
INBOUND_LABEL = "Inbound share of haulage"

#: The tool's result views, shown as a tab strip matching the database page.
VIEWS = ["Dashboard", "Baseline comparison", "Optimiser", "Process grid"]

SCROLL_HINT = """
<div class="cs-scroll-hint" style="margin-top:8px">
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M6 9l6 6 6-6"/></svg>
  <span>{label}</span>
</div>"""


# --------------------------------------------------------------------------- #
# Drawer
# --------------------------------------------------------------------------- #
def _toggle_drawer() -> None:
    st.session_state.drawer_open = not st.session_state.drawer_open


def _open_panel(panel: str | None) -> None:
    st.session_state.drawer_open = True
    st.session_state.drawer_panel = panel


@st.cache_data(show_spinner=False)
def _workbook_haulage_split(_dataset: Dataset) -> tuple:
    """The inbound leg's share of haulage carbon and energy, read off the workbook.

    Evaluated at the workbook's own reference basis — an even virgin/scrap charge,
    an even rail/road split and today's Indian grid — so the figure describes the
    two transport rows themselves rather than the user's current scenario.
    """
    inbound_ids, outbound_ids = transport_ids(_dataset)
    variables = build_variables(0.5, INDIA_GRID_MIX, 0.5)
    by_id = {proc.id: proc for proc in _dataset.processes}

    def leg(ids):
        carbon = energy = 0.0
        for process_id in ids:
            values = by_id[process_id].evaluate(variables)
            carbon += sum(values[scope] for scope in SCOPES)
            energy += values["sec"]
        return carbon, energy

    in_carbon, in_energy = leg(inbound_ids)
    out_carbon, out_energy = leg(outbound_ids)
    carbon_total = in_carbon + out_carbon
    energy_total = in_energy + out_energy
    return (
        in_carbon / carbon_total if carbon_total else 0.0,
        in_energy / energy_total if energy_total else 0.0,
    )


def _panel_scrap(dataset: Dataset) -> None:
    st.markdown("#### Scrap vs virgin charge")
    scrap = st.slider(
        SCRAP_LABEL,
        min_value=0,
        max_value=100,
        value=st.session_state.scrap,
        key=SCRAP_W,
        on_change=on_scrap_change,
        format="%d%%",
        help="Share of the metallic charge that is recycled scrap. The workbook calls this y; the virgin ratio x is the remainder.",
    )
    st.markdown(
        live.rendered_chip(SCRAP_LABEL, "virgin {inv}%", scrap)
        + " "
        + live.rendered_chip(SCRAP_LABEL, "scrap {v}%", scrap, tone="cs-chip-good"),
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown("#### Inbound / outbound haulage")
    inbound = st.slider(
        INBOUND_LABEL,
        min_value=0,
        max_value=100,
        value=st.session_state.inbound,
        key=INBOUND_W,
        on_change=on_inbound_change,
        format="%d%%",
        help="How the material movement splits between the inbound leg (raw material and "
        "scrap arriving at RMHS) and the outbound leg (finished coil despatched). Both "
        "workbook rows are stated per tonne moved, so 50% is the workbook as published; "
        "moving the slider shifts movement from one leg to the other and leaves the total "
        "unchanged.",
    )
    st.markdown(
        live.rendered_chip(INBOUND_LABEL, "inbound {v}%", inbound)
        + " "
        + live.rendered_chip(INBOUND_LABEL, "outbound {inv}%", inbound, tone="cs-chip-warn"),
        unsafe_allow_html=True,
    )
    st.caption(
        "Rail versus road is set on each leg separately, with the transport step itself \u2014 "
        "under Plant customisation, in RMHS and Outbound."
    )
    carbon_share, energy_share = _workbook_haulage_split(dataset)
    st.caption(
        f"At an even split the workbook's two haulage rows put {carbon_share:.0%} of the "
        f"transport carbon and {energy_share:.0%} of the transport energy on the inbound "
        "leg — inbound moves bulk ore, ferroalloy and scrap, outbound moves finished coil."
    )


def _action_bar(dirty: bool, apply_label: str, on_apply, on_revert, dirty_note: str) -> None:
    """The panel's docked Apply / Discard row.

    It sits at the bottom of the drawer and stays there while the panel scrolls,
    so the control that commits a change is never somewhere off screen.
    """
    # A keyed container, not an unclosed <div>: Streamlit strips a dangling tag
    # from markdown, and the wrapper has to actually contain the buttons for the
    # sticky rule to hold them on screen.
    with st.container(key="cs_dock"):
        if dirty:
            st.markdown(f'<p class="cs-dock-note">{dirty_note}</p>', unsafe_allow_html=True)
        columns = st.columns([1.4, 1])
        columns[0].button(
            apply_label,
            on_click=on_apply,
            use_container_width=True,
            type="primary" if dirty else "secondary",
            disabled=not dirty,
            key=f"apply_{apply_label}",
        )
        columns[1].button(
            "Discard",
            on_click=on_revert,
            use_container_width=True,
            disabled=not dirty,
            key=f"revert_{apply_label}",
        )


def _panel_grid(dataset: Dataset) -> None:
    st.markdown("#### Grid energy mix")
    presets = list(GRID_PRESETS)
    st.selectbox(
        "Preset",
        options=presets,
        index=presets.index(st.session_state.grid_preset),
        key=PRESET_W,
        on_change=apply_grid_preset,
        help="A preset is a single decision, so choosing one moves the sliders and "
        "applies straight away.",
    )
    note = GRID_PRESET_NOTES.get(st.session_state.grid_preset)
    if note:
        st.caption(note)

    total = mix_total()
    off_by = abs(total - 100.0)
    tone = "cs-chip-good" if off_by <= 0.05 else "cs-chip-warn"
    st.markdown(
        f'<span class="cs-chip {tone}">shares total {total:.1f}%</span>',
        unsafe_allow_html=True,
    )
    st.button(
        "Normalise to 100%",
        on_click=rescale_mix,
        use_container_width=True,
        disabled=off_by <= 0.05,
        help="Rescales every share proportionally. The sliders glide to the rescaled "
        "values rather than jumping.",
    )

    for var in MIX_VARIABLES:
        source = dataset.source_by_var[var]
        st.slider(
            f"{source.source}  \u00b7  {source.ef} kg CO\u2082e/kWh",
            min_value=0.0,
            max_value=100.0,
            step=1.0,
            value=float(st.session_state.mix_draft[var]),
            key=mix_widget(var),
            format="%.1f%%",
            on_change=on_mix_change,
            args=(var,),
        )

    drafted = draft_mix()
    st.plotly_chart(
        charts.mix_donut(drafted, dataset.source_by_var),
        use_container_width=True,
        config=charts.PLOT_CONFIG,
    )
    st.metric("Blended grid factor", f"{mix_factor(drafted, dataset):.3f} kg CO\u2082e/kWh")
    st.caption(f"Workbook reference (CEA midpoint): {REFERENCE_GRID_FACTOR} kg CO\u2082e/kWh")

    _action_bar(
        mix_dirty(),
        "Apply mix",
        apply_mix,
        revert_mix,
        "Set every share you want, normalise, then apply \u2014 nothing reaches the model "
        "until you do.",
    )


def _variation_label(variation: str) -> str:
    """Display name for a workbook variation."""
    return "General estimate" if _is_general(variation) else variation


def _is_general(variation: str) -> bool:
    """True for the workbook's catch-all "General (all types)" variation.

    A step with only this variation has nothing to choose between, so the tool
    shows it as a single checkbox rather than a menu containing one item.
    """
    return variation.strip().lower().startswith("general")


def _single_option(stage: Stage) -> bool:
    return len(stage.options) == 1


def _stage_on(route, stage: Stage) -> bool:
    return bool(normalise_mix(route.get(stage.key, {})))


def _remember_open(stage: Stage) -> None:
    """Note which rows the user is working in, so a rerun re-opens them.

    Streamlit rebuilds expanders closed on every run unless told otherwise, so
    ticking a box inside one folded it away and threw the user back to the top
    of the list.
    """
    st.session_state.open_department = stage.department
    st.session_state.open_stage = stage.key


def _toggle_stage(stage: Stage) -> None:
    """Checkbox callback for a step with nothing to choose between."""
    route = st.session_state.route_draft
    on = st.session_state.get(route_key("on", stage.key), False)
    route[stage.key] = {stage.default_id: 1.0} if on else {}
    st.session_state.open_department = stage.department


def _toggle_variation(stage: Stage, process_id: int) -> None:
    """Checkbox callback for one variation of a step."""
    _remember_open(stage)
    route = st.session_state.route_draft
    chosen = [
        pid
        for pid in stage.option_ids
        if st.session_state.get(route_key("pick", f"{stage.key}_{pid}"), False)
    ]
    if not chosen:
        route[stage.key] = {}
        return
    kept = normalise_mix({pid: route.get(stage.key, {}).get(pid, 0.0) for pid in chosen})
    route[stage.key] = kept if len(kept) == len(chosen) else even_mix(chosen)


def _transport_controls(stage: Stage) -> None:
    """The rail/road split for a transport step, shown with the step itself.

    The workbook has two transport rows and they are independent choices: a
    plant can rail its raw material in and truck its coil out. Each row's slider
    therefore lives with the row, not in a single global setting.
    """
    inbound = stage.department == "RMHS"
    label = INBOUND_RAIL_LABEL if inbound else OUTBOUND_RAIL_LABEL
    widget, callback, value = (
        (TRAIN_IN_W, on_train_in_change, st.session_state.train_in)
        if inbound
        else (TRAIN_OUT_W, on_train_out_change, st.session_state.train_out)
    )
    leg = "arriving" if inbound else "leaving"
    st.caption(f"How the tonnes {leg} are moved. Road is the remainder.")
    share = st.slider(
        label,
        min_value=0,
        max_value=100,
        value=value,
        key=widget,
        on_change=callback,
        format="%d%%",
    )
    st.markdown(
        live.rendered_chip(label, "rail {v}%", share)
        + " "
        + live.rendered_chip(label, "road {inv}%", share, tone="cs-chip-warn"),
        unsafe_allow_html=True,
    )


def _stage_controls(stage: Stage, route) -> None:
    """The variation picker for one technique, as checkboxes."""
    current = normalise_mix(route.get(stage.key, {}))
    for pid in stage.option_ids:
        st.checkbox(
            _variation_label(stage.option_by_id(pid).variation),
            value=pid in current,
            key=route_key("pick", f"{stage.key}_{pid}"),
            on_change=_toggle_variation,
            args=(stage, pid),
        )
    picked = [pid for pid in stage.option_ids if pid in normalise_mix(route.get(stage.key, {}))]
    if not picked:
        st.caption("Nothing ticked — this technique is out of the route.")
        return
    if len(picked) > 1:
        st.caption("Share of this stage's tonne through each:")
        raw: Dict[int, float] = {}
        for pid in picked:
            previous = current.get(pid, 1.0 / len(picked))
            raw[pid] = st.slider(
                _variation_label(stage.option_by_id(pid).variation),
                min_value=0.0,
                max_value=100.0,
                value=float(round(previous * 100, 1)),
                step=1.0,
                format="%.0f%%",
                key=route_key("share", f"{stage.key}_{pid}"),
            )
        set_stage_mix(stage, normalise_mix(raw) or even_mix(picked))
    if stage.options[0].transport:
        st.divider()
        _transport_controls(stage)


def _panel_plant(dataset: Dataset, stages) -> None:
    """Department → technique → variation, as one drill-down of checkboxes.

    Every level is a tick: a department shows how many of its techniques run, a
    technique with nothing to choose between is a single checkbox, and a
    technique with real alternatives opens into its variations.
    """
    st.markdown("#### Plant customisation")
    st.caption("Tick what the plant runs. Untick to take it out of the route.")
    route = st.session_state.route_draft

    for department in dataset.departments:
        dept_stages = [stage for stage in stages if stage.department == department]
        running = [stage for stage in dept_stages if _stage_on(route, stage)]
        mark = ALL_ON if len(running) == len(dept_stages) else (SOME_ON if running else ALL_OFF)
        icon = DEPARTMENT_ICONS.get(department, BULLET)
        title = f"{mark}  {icon}  {department}  {MIDDOT}  {len(running)}/{len(dept_stages)}"
        with st.expander(
            title, expanded=department == st.session_state.get("open_department")
        ):
            band = section_band(department, st.session_state.dark)
            st.markdown(
                f'{band}<div class="cs-band-title">{icon} {department}</div>',
                unsafe_allow_html=True,
            )
            head = st.columns(2)
            head[0].button(
                "Tick all",
                key=f"all_{department}",
                use_container_width=True,
                on_click=_set_department,
                args=(dept_stages, True),
            )
            head[1].button(
                "Untick all",
                key=f"none_{department}",
                use_container_width=True,
                on_click=_set_department,
                args=(dept_stages, False),
            )
            for stage in dept_stages:
                if _single_option(stage) and _is_general(stage.options[0].variation):
                    # Nothing to choose between, so the technique is the
                    # checkbox — but it still gets the same row treatment as the
                    # ones that open, so the list reads as one list.
                    with st.container(key=f"csrow_{route_key('row', stage.key)}"):
                        st.checkbox(
                            stage.process,
                            value=_stage_on(route, stage),
                            key=route_key("on", stage.key),
                            on_change=_toggle_stage,
                            args=(stage,),
                        )
                    continue
                summary = _stage_summary(stage, route.get(stage.key, {}))
                with st.expander(
                    f"{stage.process}  {DASH}  {summary}",
                    expanded=stage.key == st.session_state.get("open_stage"),
                ):
                    _stage_controls(stage, route)

    _action_bar(
        route_dirty(),
        "Apply route",
        apply_route,
        revert_route,
        "Tick everything the plant runs, then apply \u2014 the model keeps the current "
        "route until you do.",
    )


def _stage_summary(stage: Stage, mix) -> str:
    """One line describing what a stage is currently running."""
    live_mix = normalise_mix(mix)
    if not live_mix:
        return "off"
    return " + ".join(
        _variation_label(stage.option_by_id(pid).variation)
        + (f" {share:.0%}" if len(live_mix) > 1 else "")
        for pid, share in sorted(live_mix.items(), key=lambda item: -item[1])
    )


def _set_department(dept_stages, on: bool) -> None:
    """Turn a whole department on (first-listed variation) or off."""
    if dept_stages:
        st.session_state.open_department = dept_stages[0].department
    route = st.session_state.route_draft
    for stage in dept_stages:
        if on:
            if not normalise_mix(route.get(stage.key, {})):
                route[stage.key] = {stage.default_id: 1.0}
        else:
            route[stage.key] = {}
        _forget_stage_widgets(stage)


def _forget_stage_widgets(stage: Stage) -> None:
    """Rebuild a stage's widgets from the draft on the next run.

    Bumping the generation is heavier than dropping this stage's three keys, but
    dropping keys of widgets that are still on screen is what crashed when a
    profile was switched, so the route never does it.
    """
    forget_route_widgets()


def _drawer(dataset: Dataset, stages) -> None:
    panel = st.session_state.drawer_panel
    head = st.columns([3, 1])
    head[0].markdown(
        '<div class="cs-drawer-title">\u2699\ufe0f Inputs</div>'
        '<p class="cs-drawer-sub">Everything you can change about the scenario.</p>',
        unsafe_allow_html=True,
    )
    head[1].button("Close  \u2715", key="close_drawer", on_click=_toggle_drawer,
                   use_container_width=True)
    if panel is None:
        for key, title, blurb in PANELS:
            st.markdown(panel_art(key, st.session_state.dark), unsafe_allow_html=True)
            st.button(title, key=f"open_{key}", on_click=_open_panel, args=(key,),
                      use_container_width=True)
            st.caption(blurb)
            st.write("")
        return

    columns = st.columns(3)
    for column, (key, title, _) in zip(columns, PANELS):
        column.button(
            title.split()[0],
            key=f"tab_{key}",
            on_click=_open_panel,
            args=(key,),
            use_container_width=True,
            type="primary" if key == panel else "secondary",
            help=title,
        )
    st.divider()
    if panel == "scrap":
        _panel_scrap(dataset)
    elif panel == "grid":
        _panel_grid(dataset)
    else:
        _panel_plant(dataset, stages)


# --------------------------------------------------------------------------- #
# Result views
# --------------------------------------------------------------------------- #
def _metric(label: str, value: str, unit: str, *, key: str, lead: bool = False) -> str:
    """One figure in the readout. The number is the element; the unit recedes.

    ``key`` names the figure for the in-page script that follows a slider drag.
    """
    classes = "cs-metric cs-metric-lead" if lead else "cs-metric"
    return (
        f'<div class="{classes}"><div class="cs-metric-label">{label}</div>'
        f'<div class="cs-metric-value"><span data-cs-metric="{key}">{value}</span>'
        f'<span class="cs-unit">{unit}</span></div></div>'
    )


def _headline(result: Result, dataset: Dataset) -> None:
    """The scenario's figures, sized so they read before anything else does."""
    kwh = result.electricity_kwh
    figures = "".join(
        (
            _metric("Total CO\u2082e", f"{result.total_co2e:.3f}", "t/t", key="total", lead=True),
            _metric("Scope 1", f"{result.totals['scope1']:.3f}", "t/t", key="scope1"),
            _metric("Scope 2", f"{result.totals['scope2']:.3f}", "t/t", key="scope2"),
            _metric("Scope 3 upstream", f"{result.totals['scope3']:.3f}", "t/t", key="scope3"),
            _metric("Specific energy", f"{result.energy_gj:.1f}", "GJ/t", key="energy"),
        )
    )
    # A keyed container, so the sticky rule has a tall parent to travel in: a
    # markdown block is exactly its own height, and a sticky element with no
    # room to move never moves.
    with st.container(key="cs_readout"):
        st.markdown(
            f'<div class="cs-readout">{figures}</div>'
            f'<p class="cs-readout-note"><span data-cs-conditions>scrap '
            f"{result.scrap_ratio:.0%} \u00b7 rail {result.train_share:.0%}</span> "
            f"\u00b7 grid {result.grid_factor:.3f} kg CO\u2082e/kWh "
            f"\u00b7 electricity \u2248 "
            f"{'n/a' if math.isnan(kwh) else f'{kwh:,.0f} kWh/t'}</p>",
            unsafe_allow_html=True,
        )


def _profile_banner(stages) -> None:
    profiles = list(PLANT_PROFILES)
    st.selectbox(
        "Starting point",
        options=profiles,
        index=profiles.index(st.session_state.plant_profile),
        key=PROFILE_W,
        on_change=apply_plant_profile,
        args=(stages,),
    )
    profile = PLANT_PROFILES[st.session_state.plant_profile]
    st.caption(profile.summary)
    if profile.restricted_departments:
        st.caption(
            "This profile switches on only the equipment publicly described for the "
            "site \u2014 it is not an inventory of the plant. Anything left unticked is "
            "unevidenced rather than known to be absent, so tick it back on if you "
            "know the site runs it."
        )
    if profile.sources:
        with st.expander("Where this profile comes from", expanded=False):
            st.markdown(
                f"**Process route — sourced.** {profile.tagline}.\n\n"
                + "\n".join(f"- [{label}]({url})" for label, url in profile.sources)
            )
            st.warning(
                "**Estimated, not published:** "
                + ", ".join(profile.estimated)
                + ". Neither site discloses a source-wise breakdown of the electricity it "
                "consumes, so the mix below is a plausible starting point to adjust — not "
                "verified JSL data."
            )
    for problem in st.session_state.get("profile_problems", []):
        st.error(f"Profile could not be applied fully — {problem}")


def _live_model(dataset: Dataset) -> dict:
    """What the page needs to follow a slider drag without the server.

    The charts still wait for the release — redrawing them is the server's job —
    but the figures a reader steers by follow the thumb.
    """
    model = coefficient_model(dataset, route_weights(st.session_state.route))
    mix = current_mix()
    model["gridFactor"] = sum(model["factors"][var] * mix[var] for var in MIX_VARIABLES)
    model["labels"] = {
        "scrap": SCRAP_LABEL,
        "inbound": INBOUND_LABEL,
        "railIn": INBOUND_RAIL_LABEL,
        "railOut": OUTBOUND_RAIL_LABEL,
    }
    model["values"] = {
        "scrap": scrap_ratio(),
        "inbound": inbound_share(),
        "railIn": inbound_rail(),
        "railOut": outbound_rail(),
    }
    return model


def _chart_key(name: str) -> str:
    """A chart key that is stable while values change, but not across layouts.

    A stable key is what lets Plotly tween the bars between renders instead of
    repainting them. It also makes the component keep its measured width, so the
    key carries the drawer state: opening or closing the drawer changes the
    column width and must remount the chart, while moving a slider must not.
    """
    return f"{name}_{'open' if st.session_state.drawer_open else 'closed'}"


def _dashboard(result: Result, dataset: Dataset, stages) -> None:
    _profile_banner(stages)

    st.markdown('<div class="cs-stage">', unsafe_allow_html=True)
    st.markdown("### Where the carbon sits")
    st.plotly_chart(
        charts.scope_breakdown(result),
        use_container_width=True,
        config=charts.PLOT_CONFIG,
        key=_chart_key("chart_scopes"),
    )
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown(
        SCROLL_HINT.format(label="Scroll for the department split"), unsafe_allow_html=True
    )

    st.markdown('<div class="cs-stage">', unsafe_allow_html=True)
    st.markdown("### By department")
    st.plotly_chart(
        charts.department_breakdown(result),
        use_container_width=True,
        config=charts.PLOT_CONFIG,
        key=_chart_key("chart_departments"),
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### Greenhouse gases")
    st.caption(
        "A gas-by-gas view of the same footprint, reported alongside the scopes in the "
        "workbook — not a fourth scope, so it is never added into the total above."
    )
    gases = pd.DataFrame(
        [{"Gas": METRIC_LABELS[gas], "tCO₂e/t": result.totals[gas]} for gas in TRACE_GASES]
    )
    st.dataframe(
        gases.style.format({"tCO₂e/t": "{:.5f}"}),
        use_container_width=True,
        hide_index=True,
    )


def _baseline(result: Result, dataset: Dataset, stages) -> None:
    st.markdown("### Baseline comparison")
    controls = st.columns([2, 1, 1])
    controls[0].caption(
        "The default baseline is a 40% scrap charge on today's Indian grid with the "
        "workbook's first-listed technology at every stage and a 50/50 rail-road split."
    )
    if controls[1].button("Capture current", use_container_width=True):
        st.session_state.baseline = {
            "scrap": scrap_ratio(),
            "mix": current_mix(),
            "route": {key: dict(value) for key, value in st.session_state.route.items()},
            "train": train_share(),
            "inbound": inbound_share(),
            "rail_in": inbound_rail(),
            "rail_out": outbound_rail(),
            "label": f"Captured: scrap {st.session_state.scrap}%, inbound "
            f"{st.session_state.inbound}%, rail {st.session_state.train_in}% in / "
            f"{st.session_state.train_out}% out",
        }
    if controls[2].button("Reset baseline", use_container_width=True):
        st.session_state.baseline = None

    saved = st.session_state.baseline
    if saved is None:
        saved = {
            "scrap": 0.40,
            "mix": GRID_PRESETS["India grid today"],
            "route": default_route(stages),
            "train": 0.50,
            "inbound": 0.50,
            "label": "Default baseline: scrap 40%, India grid today, first-listed technologies",
        }
    st.info(saved["label"])

    baseline = calculate(
        saved["scrap"],
        saved["mix"],
        dataset,
        apply_haulage(route_weights(saved["route"]), dataset, saved.get("inbound", 0.50)),
        saved["train"],
        rail_shares(
            dataset,
            saved.get("rail_in", saved["train"]),
            saved.get("rail_out", saved["train"]),
        ),
    )

    def delta(current: float, base: float) -> str:
        return "n/a" if base == 0 else f"{(current - base) / base:+.1%}"

    pairs = [
        ("Total CO₂e", result.total_co2e, baseline.total_co2e, "{:.3f} t/t"),
        ("Scope 1", result.totals["scope1"], baseline.totals["scope1"], "{:.3f} t/t"),
        ("Scope 2", result.totals["scope2"], baseline.totals["scope2"], "{:.3f} t/t"),
        ("Scope 3", result.totals["scope3"], baseline.totals["scope3"], "{:.3f} t/t"),
        ("Energy", result.energy_gj, baseline.energy_gj, "{:.1f} GJ/t"),
    ]
    for column, (name, current, base, fmt) in zip(st.columns(5), pairs):
        column.metric(name, fmt.format(current), delta(current, base), delta_color="inverse")

    saving = baseline.total_co2e - result.total_co2e
    if saving > 1e-9:
        st.success(
            f"**{saving:.3f} tCO₂e/t avoided** versus the baseline "
            f"({saving / baseline.total_co2e:.1%} lower) — "
            f"{saving * 1000:,.0f} kt CO₂e a year at 1 Mt of output."
        )
    elif saving < -1e-9:
        st.warning(
            f"**{-saving:.3f} tCO₂e/t higher** than the baseline "
            f"({-saving / baseline.total_co2e:.1%} above it)."
        )
    else:
        st.info("The current scenario matches the baseline.")

    st.plotly_chart(
        charts.comparison_bars(["Baseline", "Current"], [baseline, result]),
        use_container_width=True,
        config=charts.PLOT_CONFIG,
    )

    rows = []
    for department in dataset.departments:
        base_value = baseline.by_department.get(department, {}).get("total_co2e", 0.0)
        current_value = result.by_department.get(department, {}).get("total_co2e", 0.0)
        rows.append(
            {
                "Department": department,
                "Baseline": base_value,
                "Current": current_value,
                "Change": current_value - base_value,
            }
        )
    st.dataframe(
        pd.DataFrame(rows).style.format(
            {"Baseline": "{:.4f}", "Current": "{:.4f}", "Change": "{:+.4f}"}
        ),
        use_container_width=True,
        hide_index=True,
    )


def _optimiser(result: Result, dataset: Dataset, stages) -> None:
    st.markdown("### Lowest-carbon path")
    st.caption(
        "The search covers the scrap ratio, the seven grid shares, the rail/road split and "
        "the technology at every stage. Set the limits that make the answer practical."
    )
    left, right = st.columns(2, gap="large")
    with left:
        scrap_range = st.slider("Allowed scrap ratio (%)", 0, 100, (0, 80), key="opt_scrap")
        rail_range = st.slider("Allowed rail share (%)", 0, 100, (0, 100), key="opt_rail")
        optimise_route = st.checkbox("Let it change technologies", value=True, key="opt_route")
        lockable = [stage.key for stage in stages if stage.has_choice]
        locked = st.multiselect(
            "Keep these stages as they are",
            options=lockable,
            format_func=lambda key: key.replace(" :: ", " — "),
            disabled=not optimise_route,
            key="opt_locked",
        )
    with right:
        max_coal = st.slider("Maximum coal (%)", 0, 100, 40, key="opt_coal") / 100
        min_renewable = st.slider("Minimum renewables (%)", 0, 100, 30, key="opt_ren") / 100
        min_non_fossil = st.slider("Minimum non-fossil (%)", 0, 100, 30, key="opt_nf") / 100
        caps = st.columns(2)
        max_wind = caps[0].slider("Max wind (%)", 0, 100, 40, key="opt_wind") / 100
        max_solar = caps[1].slider("Max solar (%)", 0, 100, 40, key="opt_solar") / 100

    constraints = Constraints(
        scrap_min=scrap_range[0] / 100,
        scrap_max=scrap_range[1] / 100,
        mix_bounds={"a": (0.0, max_coal), "e": (0.0, max_wind), "f": (0.0, max_solar)},
        min_renewable=min_renewable,
        min_non_fossil=min_non_fossil,
        locked_stages=tuple(locked),
        train_min=rail_range[0] / 100,
        train_max=rail_range[1] / 100,
    )
    try:
        optimum = optimise(
            dataset,
            stages,
            constraints,
            st.session_state.route,
            optimise_route=optimise_route,
            inbound_share=inbound_share(),
        )
    except InfeasibleError as error:
        st.error(f"No feasible scenario: {error}")
        return

    saving = result.total_co2e - optimum.result.total_co2e
    headline = st.columns(4)
    headline[0].metric(
        "Optimised total",
        f"{optimum.result.total_co2e:.3f} t/t",
        f"{-saving:+.3f} vs current",
        delta_color="inverse",
    )
    headline[1].metric("Scrap ratio", f"{optimum.scrap_ratio:.0%}")
    headline[2].metric("Rail share", f"{optimum.train_share:.0%}")
    headline[3].metric(
        "Reduction", f"{saving / result.total_co2e:.1%}" if result.total_co2e else "n/a"
    )
    if saving > 1e-9:
        st.success(
            f"Cutting {saving:.3f} tCO₂e/t against your current settings — "
            f"{saving * 1000:,.0f} kt CO₂e a year at 1 Mt of output."
        )
    else:
        st.info("Your current scenario is already optimal for these constraints.")

    st.markdown("**Recommended grid mix**")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Source": dataset.source_by_var[var].source,
                    "Current": current_mix()[var],
                    "Optimised": optimum.mix[var],
                    "kg CO₂e/kWh": dataset.source_by_var[var].ef,
                }
                for var in MIX_VARIABLES
            ]
        ).style.format({"Current": "{:.1%}", "Optimised": "{:.1%}", "kg CO₂e/kWh": "{:.3f}"}),
        use_container_width=True,
        hide_index=True,
    )
    if optimum.stage_changes:
        st.markdown("**Technology changes recommended**")
        st.dataframe(
            pd.DataFrame(
                [
                    {"Stage": key.replace(" :: ", " — "), "Current": before, "Recommended": after}
                    for key, before, after in optimum.stage_changes
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )


def _process_grid(result: Result, dataset: Dataset) -> None:
    st.markdown("### Per-process results")
    frame = pd.DataFrame(list(result.per_process)).rename(
        columns={**METRIC_LABELS, "total_co2e": "Total CO₂e (tCO₂e/t)"}
    ).drop(columns=["id"])
    departments = st.multiselect(
        "Departments", dataset.departments, default=[], key="grid_depts",
        placeholder="All departments",
    )
    view = frame[frame["Department"].isin(departments)] if departments else frame
    numeric = [column for column in view.columns if view[column].dtype.kind == "f"]
    st.dataframe(
        view.style.format({column: "{:.5f}" for column in numeric}),
        use_container_width=True,
        hide_index=True,
        height=480,
    )
    st.download_button(
        "Download as CSV",
        view.to_csv(index=False).encode("utf-8"),
        file_name="carbonspark_route.csv",
        mime="text/csv",
    )


# --------------------------------------------------------------------------- #
# Page
# --------------------------------------------------------------------------- #
def render(dataset: Dataset, stages) -> None:
    live.enable("tool", _live_model(dataset))
    bar = st.columns([2.6, 1.2, 0.7, 1.2, 1.2])
    bar[0].markdown(
        f'<div style="display:flex;align-items:center;gap:10px;font-weight:800;'
        f'font-size:1.1rem">{spark_mark(24, st.session_state.dark)} CarbonSpark <span class="cs-chip">tool</span></div>',
        unsafe_allow_html=True,
    )
    bar[1].button(
        "\u2715 Close inputs" if st.session_state.drawer_open else "\u2699\ufe0f Customise",
        on_click=_toggle_drawer,
        use_container_width=True,
        type="secondary" if st.session_state.drawer_open else "primary",
        help="Scrap ratio, energy grid mix and the plant's process route",
        key="open_inputs",
    )
    bar[2].button(
        "\u2600\ufe0f" if st.session_state.dark else "\u263e",
        on_click=toggle_dark,
        use_container_width=True,
        help="Switch to light mode" if st.session_state.dark else "Switch to dark mode",
        key="dark_toggle_tool",
    )
    bar[3].button("Database", on_click=go, args=("database",), use_container_width=True)
    bar[4].button("\u2190 Back to site", on_click=go, args=("landing",), use_container_width=True)
    st.markdown('<div class="cs-rule"></div>', unsafe_allow_html=True)

    # The drawer mutates the route as it renders, so the result is computed
    # afterwards — otherwise every reading would lag one interaction behind.
    if st.session_state.drawer_open:
        drawer, main = st.columns([4.5, 5.5], gap="large")
        with drawer:
            # A keyed container gets its own CSS class, so the drawer's raised
            # surface wraps its contents instead of an unclosed <div> leaving an
            # empty box floating above them.
            with st.container(border=True, key="cs_drawer"):
                _drawer(dataset, stages)
    else:
        main = st.container()

    weights = apply_haulage(route_weights(st.session_state.route), dataset, inbound_share())
    if not weights:
        with main:
            st.error(
                "Every stage is switched off. Open Inputs and add at least one process."
            )
            st.button("\u2699\ufe0f  Open inputs", on_click=_toggle_drawer, type="primary")
        return
    result = calculate(
        scrap_ratio(),
        current_mix(),
        dataset,
        weights,
        train_share(),
        rail_shares(dataset, inbound_rail(), outbound_rail()),
    )

    with main:
        _headline(result, dataset)
        view = st.segmented_control(
            "View", VIEWS, key="tool_view", label_visibility="collapsed"
        ) or VIEWS[0]
        if view == "Dashboard":
            _dashboard(result, dataset, stages)
        elif view == "Baseline comparison":
            _baseline(result, dataset, stages)
        elif view == "Optimiser":
            _optimiser(result, dataset, stages)
        else:
            _process_grid(result, dataset)
