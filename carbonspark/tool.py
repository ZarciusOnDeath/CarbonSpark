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
    TRAIN_W,
    apply_grid_preset,
    apply_plant_profile,
    current_mix,
    go,
    inbound_share,
    mix_total,
    mix_widget,
    on_inbound_change,
    on_mix_change,
    on_scrap_change,
    on_train_change,
    rescale_mix,
    scrap_ratio,
    set_stage_mix,
    train_share,
)
from .theme import DEPARTMENT_ICONS, SCOPE_NAMES, panel_art, section_band, spark_mark

PANELS = [
    ("scrap", "Scrap vs virgin", "How much of the charge is recycled steel"),
    ("grid", "Energy grid mix", "Where the electricity comes from"),
    ("plant", "Plant customisation", "Departments, techniques and variations"),
]

#: Slider labels, shared with the live-readout chips that follow them.
SCRAP_LABEL = "Scrap steel ratio  y"
RAIL_LABEL = "Rail share  p"
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
        help="Share of the metallic charge that is recycled scrap. Virgin ratio x = 1 − y.",
    )
    st.markdown(
        live.rendered_chip(SCRAP_LABEL, "virgin x = {inv}%", scrap)
        + " "
        + live.rendered_chip(SCRAP_LABEL, "scrap y = {v}%", scrap, tone="cs-chip-good"),
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown("#### Inbound / outbound haulage")
    train = st.slider(
        RAIL_LABEL,
        min_value=0,
        max_value=100,
        value=st.session_state.train,
        key=TRAIN_W,
        on_change=on_train_change,
        format="%d%%",
        help="Share of material moved by rail. Road share q = 1 − p. Applies to the two "
        "transport rows: RMHS unloading and outbound despatch.",
    )
    st.markdown(
        live.rendered_chip(RAIL_LABEL, "rail p = {v}%", train)
        + " "
        + live.rendered_chip(RAIL_LABEL, "road q = {inv}%", train, tone="cs-chip-warn"),
        unsafe_allow_html=True,
    )
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
        live.rendered_chip(INBOUND_LABEL, "inbound = {v}%", inbound)
        + " "
        + live.rendered_chip(INBOUND_LABEL, "outbound = {inv}%", inbound, tone="cs-chip-warn"),
        unsafe_allow_html=True,
    )
    carbon_share, energy_share = _workbook_haulage_split(dataset)
    st.caption(
        f"At an even split the workbook's two haulage rows put {carbon_share:.0%} of the "
        f"transport carbon and {energy_share:.0%} of the transport energy on the inbound "
        "leg — inbound moves bulk ore, ferroalloy and scrap, outbound moves finished coil."
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
        help="Choosing a preset moves the sliders immediately.",
    )
    note = GRID_PRESET_NOTES.get(st.session_state.grid_preset)
    if note:
        st.caption(note)

    # Normalising is a deliberate action, not something that happens under the
    # user's hand: setting four shares in a row would otherwise have the first
    # three rescaled out from under the fourth. The control sits above the
    # sliders it governs and rewrites their values, so what you see is what the
    # model used.
    total = mix_total()
    off_by = abs(total - 100.0)
    left, right = st.columns([1.6, 1])
    with left:
        if off_by <= 0.05:
            st.markdown(
                f'<span class="cs-chip cs-chip-good">shares total {total:.0f}%</span>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<span class="cs-chip cs-chip-warn">shares total {total:.1f}%</span>',
                unsafe_allow_html=True,
            )
    right.button(
        "Normalise",
        on_click=rescale_mix,
        use_container_width=True,
        disabled=off_by <= 0.05,
        type="primary" if off_by > 0.05 else "secondary",
        help="Rescales every share proportionally so the mix sums to 100%. The sliders "
        "glide to the rescaled values rather than jumping.",
    )
    if off_by > 0.05:
        st.caption(
            "Set as many shares as you like — nothing is rescaled until you press "
            "Normalise. Until then the model uses the shares exactly as they stand."
        )

    for var in MIX_VARIABLES:
        source = dataset.source_by_var[var]
        st.slider(
            f"{source.source}  ·  {source.ef} kg CO\u2082e/kWh",
            min_value=0.0,
            max_value=100.0,
            step=1.0,
            value=float(st.session_state.mix[var]),
            key=mix_widget(var),
            format="%.1f%%",
            on_change=on_mix_change,
            args=(var,),
        )

    mix = current_mix()
    st.plotly_chart(
        charts.mix_donut(mix, dataset.source_by_var),
        use_container_width=True,
        config=charts.PLOT_CONFIG,
    )
    st.metric("Blended grid factor", f"{mix_factor(mix, dataset):.3f} kg CO\u2082e/kWh")
    st.caption(f"Workbook reference (CEA midpoint): {REFERENCE_GRID_FACTOR} kg CO\u2082e/kWh")


def _variation_label(variation: str) -> str:
    """Display name for a workbook variation.

    The workbook writes "General (all types)" wherever a step has no
    interchangeable technologies. That reads like a selectable option among
    others, when it is really the step's single general estimate.
    """
    if variation.strip().lower().startswith("general"):
        return "General estimate"
    return variation


def _stage_summary(stage: Stage, mix) -> str:
    """One line describing what a stage is currently running."""
    live_mix = normalise_mix(mix)
    if not live_mix:
        return "off"
    parts = [
        f"{_variation_label(stage.option_by_id(pid).variation)}"
        + (f" {share:.0%}" if len(live_mix) > 1 else "")
        for pid, share in sorted(live_mix.items(), key=lambda item: -item[1])
    ]
    return " + ".join(parts)


def _stage_controls(stage: Stage, route) -> None:
    """The variation picker for one technique."""
    current = normalise_mix(route.get(stage.key, {}))
    picked = st.multiselect(
        "Variations in use",
        options=list(stage.option_ids),
        default=[pid for pid in stage.option_ids if pid in current],
        format_func=lambda pid, s=stage: _variation_label(s.option_by_id(pid).variation),
        key=f"vars_{stage.key}",
        help="Pick as many as the plant actually runs — the stage's tonne is split "
        "between them.",
    )
    if not picked:
        route[stage.key] = {}
        st.caption("Nothing selected — this technique is out of the route.")
        return
    if len(picked) == 1:
        set_stage_mix(stage, {picked[0]: 1.0})
        return

    # Adding or removing a variation resets the split to even, so a new
    # selection never inherits a lopsided share from the previous set.
    signature = tuple(sorted(picked))
    signature_key = f"sig_{stage.key}"
    if st.session_state.get(signature_key) != signature:
        st.session_state[signature_key] = signature
        current = even_mix(picked)
        for pid in picked:
            st.session_state.pop(f"share_{stage.key}_{pid}", None)

    st.caption("Share of this stage's tonne through each variation:")
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
            key=f"share_{stage.key}_{pid}",
        )
    normalised = normalise_mix(raw) or even_mix(picked)
    set_stage_mix(stage, normalised)
    st.markdown(
        " ".join(
            f'<span class="cs-chip">{_variation_label(stage.option_by_id(pid).variation)} '
            f"{share:.0%}</span>"
            for pid, share in normalised.items()
        ),
        unsafe_allow_html=True,
    )


def _panel_plant(dataset: Dataset, stages) -> None:
    """Department → technique → variation, as one drill-down.

    Every level works the same way: open the level, see what is running, turn
    things on or off. There is no separate "which techniques" list sitting
    beside the department picker — a technique is on when it has a variation
    selected, exactly as a variation is on when it is ticked.
    """
    st.markdown("#### Plant customisation")
    route = st.session_state.route

    for department in dataset.departments:
        dept_stages = [stage for stage in stages if stage.department == department]
        running = [
            stage for stage in dept_stages if normalise_mix(route.get(stage.key, {}))
        ]
        with st.expander(
            f"{DEPARTMENT_ICONS.get(department, '•')}  {department}"
            f"  ·  {len(running)}/{len(dept_stages)} techniques",
            expanded=False,
        ):
            st.markdown(
                f'{section_band(department)}<div class="cs-band-title">'
                f'{DEPARTMENT_ICONS.get(department, "•")} {department}</div>',
                unsafe_allow_html=True,
            )
            head = st.columns([1, 1])
            head[0].button(
                "Run every technique",
                key=f"all_{department}",
                use_container_width=True,
                on_click=_set_department,
                args=(dept_stages, True),
            )
            head[1].button(
                "Skip this department",
                key=f"none_{department}",
                use_container_width=True,
                on_click=_set_department,
                args=(dept_stages, False),
            )
            for stage in dept_stages:
                summary = _stage_summary(stage, route.get(stage.key, {}))
                with st.expander(f"{stage.process}  —  {summary}", expanded=False):
                    _stage_controls(stage, route)


def _set_department(dept_stages, on: bool) -> None:
    """Turn a whole department on (first-listed variation) or off."""
    route = st.session_state.route
    for stage in dept_stages:
        if on:
            if not normalise_mix(route.get(stage.key, {})):
                route[stage.key] = {stage.default_id: 1.0}
        else:
            route[stage.key] = {}
        st.session_state.pop(f"vars_{stage.key}", None)


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
            st.markdown(panel_art(key), unsafe_allow_html=True)
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
def _headline(result: Result, dataset: Dataset) -> None:
    columns = st.columns(5)
    columns[0].metric("Total CO₂e", f"{result.total_co2e:.3f} t/t")
    columns[1].metric("Scope 1", f"{result.totals['scope1']:.3f} t/t")
    columns[2].metric("Scope 2", f"{result.totals['scope2']:.3f} t/t")
    columns[3].metric("Scope 3 upstream", f"{result.totals['scope3']:.3f} t/t")
    columns[4].metric("Specific energy", f"{result.energy_gj:.1f} GJ/t")
    kwh = result.electricity_kwh
    st.caption(
        f"Scrap y = {result.scrap_ratio:.0%} · rail p = {result.train_share:.0%} · "
        f"grid {result.grid_factor:.3f} kg CO₂e/kWh · "
        f"electricity ≈ {'n/a' if math.isnan(kwh) else f'{kwh:,.0f} kWh/t'}"
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


def _dashboard(result: Result, dataset: Dataset, stages) -> None:
    _profile_banner(stages)

    st.markdown('<div class="cs-stage">', unsafe_allow_html=True)
    st.markdown("### Where the carbon sits")
    st.plotly_chart(
        charts.scope_breakdown(result),
        use_container_width=True,
        config=charts.PLOT_CONFIG,
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
            "label": f"Captured: y={st.session_state.scrap}%, p={st.session_state.train}%, "
            f"inbound={st.session_state.inbound}%",
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
            "label": "Default baseline: y=40%, India grid today, first-listed technologies",
        }
    st.info(saved["label"])

    baseline = calculate(
        saved["scrap"],
        saved["mix"],
        dataset,
        apply_haulage(route_weights(saved["route"]), dataset, saved.get("inbound", 0.50)),
        saved["train"],
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
        "Departments", dataset.departments, default=dataset.departments, key="grid_depts"
    )
    view = frame[frame["Department"].isin(departments)]
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
    live.enable()
    bar = st.columns([4.0, 1.3, 1.3])
    bar[0].markdown(
        f'<div style="display:flex;align-items:center;gap:10px;font-weight:800;'
        f'font-size:1.1rem">{spark_mark(24)} CarbonSpark <span class="cs-chip">tool</span></div>',
        unsafe_allow_html=True,
    )
    bar[1].button("Database", on_click=go, args=("database",), use_container_width=True)
    bar[2].button("\u2190 Back to site", on_click=go, args=("landing",), use_container_width=True)
    st.markdown('<div class="cs-rule"></div>', unsafe_allow_html=True)

    # The drawer mutates the route as it renders, so the result is computed
    # afterwards — otherwise every reading would lag one interaction behind.
    if st.session_state.drawer_open:
        drawer, main = st.columns([3, 7], gap="large")
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
    result = calculate(scrap_ratio(), current_mix(), dataset, weights, train_share())

    with main:
        # The inputs button sits with the readings it changes, not in a far
        # corner of the page.
        opener, headline = st.columns([1.15, 6], gap="medium")
        opener.button(
            "\u2715  Close inputs" if st.session_state.drawer_open else "\u2699\ufe0f  Customise inputs",
            on_click=_toggle_drawer,
            use_container_width=True,
            type="secondary" if st.session_state.drawer_open else "primary",
            help="Scrap ratio, energy grid mix and the plant's process route",
            key="open_inputs",
        )
        with headline:
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
