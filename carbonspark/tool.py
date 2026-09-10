"""The CarbonSpark tool: input drawer, plant flow, and the result views."""

from __future__ import annotations

import math
from typing import Dict, List

import pandas as pd
import streamlit as st

from carbon_calc.model import (
    METRIC_LABELS,
    MIX_VARIABLES,
    REFERENCE_GRID_FACTOR,
    SCOPES,
    TRACE_GASES,
    Dataset,
    Result,
    calculate,
    mix_factor,
)
from carbon_calc.optimize import Constraints, InfeasibleError, optimise
from carbon_calc.route import Stage, default_route, even_mix, normalise_mix, route_weights

from . import charts
from .presets import GRID_PRESET_NOTES, GRID_PRESETS, PLANT_PROFILES
from .state import (
    NORMALISE_W,
    PRESET_W,
    PROFILE_W,
    SCRAP_W,
    TRAIN_W,
    apply_grid_preset,
    apply_plant_profile,
    current_mix,
    go,
    mix_total,
    mix_widget,
    on_mix_change,
    on_normalise_toggle,
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


def _panel_scrap() -> None:
    st.markdown("#### Scrap vs virgin charge")
    scrap = st.slider(
        "Scrap steel ratio  y",
        min_value=0,
        max_value=100,
        value=st.session_state.scrap,
        key=SCRAP_W,
        on_change=on_scrap_change,
        format="%d%%",
        help="Share of the metallic charge that is recycled scrap. Virgin ratio x = 1 − y.",
    )
    st.markdown(
        f'<span class="cs-chip">virgin x = {100 - scrap}%</span> '
        f'<span class="cs-chip cs-chip-good">scrap y = {scrap}%</span>',
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown("#### Inbound / outbound haulage")
    train = st.slider(
        "Rail share  p",
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
        f'<span class="cs-chip">rail p = {train}%</span> '
        f'<span class="cs-chip cs-chip-warn">road q = {100 - train}%</span>',
        unsafe_allow_html=True,
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

    # The normalise control sits above the sliders it governs, and rescaling
    # rewrites the slider values themselves rather than adjusting silently.
    st.checkbox(
        "Keep shares summing to 100%",
        value=st.session_state.auto_normalise,
        key=NORMALISE_W,
        on_change=on_normalise_toggle,
        help="On: moving one slider rescales the others so the mix always totals 100%.",
    )
    total = mix_total()
    if abs(total - 100.0) > 0.5:
        left, right = st.columns([2, 1])
        left.warning(f"Shares total {total:.0f}%.")
        right.button("Rescale to 100%", on_click=rescale_mix, use_container_width=True)

    for var in MIX_VARIABLES:
        source = dataset.source_by_var[var]
        st.slider(
            f"{source.source}  ·  {source.ef} kg CO₂e/kWh",
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
    st.metric("Blended grid factor", f"{mix_factor(mix, dataset):.3f} kg CO₂e/kWh")
    st.caption(f"Workbook reference (CEA midpoint): {REFERENCE_GRID_FACTOR} kg CO₂e/kWh")


def _panel_plant(dataset: Dataset, stages) -> None:
    st.markdown("#### Plant customisation")
    st.caption(
        "Pick a department, then the techniques it runs, then the variations of each. "
        "Selecting more than one variation splits that stage's tonne between them."
    )
    route = st.session_state.route
    department = st.selectbox("Department", options=dataset.departments, key="dept_pick")
    st.markdown(
        f'{section_band(department)}<div class="cs-band-title">'
        f'{DEPARTMENT_ICONS.get(department, "•")} {department}</div>',
        unsafe_allow_html=True,
    )

    dept_stages = [stage for stage in stages if stage.department == department]
    running = [stage for stage in dept_stages if normalise_mix(route.get(stage.key, {}))]
    chosen = st.multiselect(
        "Techniques / processes in use",
        options=[stage.key for stage in dept_stages],
        default=[stage.key for stage in running],
        format_func=lambda key: next(s.process for s in dept_stages if s.key == key),
        key=f"techniques_{department}",
    )
    for stage in dept_stages:
        if stage.key not in chosen:
            route[stage.key] = {}
        elif not normalise_mix(route.get(stage.key, {})):
            route[stage.key] = {stage.default_id: 1.0}

    for stage in dept_stages:
        if stage.key not in chosen:
            continue
        with st.expander(stage.process, expanded=stage.has_choice):
            current = normalise_mix(route.get(stage.key, {}))
            picked = st.multiselect(
                "Variations",
                options=list(stage.option_ids),
                default=[pid for pid in stage.option_ids if pid in current],
                format_func=lambda pid, s=stage: s.option_by_id(pid).variation,
                key=f"vars_{stage.key}",
            )
            if not picked:
                route[stage.key] = {}
                st.caption("No variation selected — this stage is out of the route.")
                continue
            if len(picked) == 1:
                set_stage_mix(stage, {picked[0]: 1.0})
                continue

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
                    stage.option_by_id(pid).variation,
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
                    f'<span class="cs-chip">{stage.option_by_id(pid).variation} '
                    f"{share:.0%}</span>"
                    for pid, share in normalised.items()
                ),
                unsafe_allow_html=True,
            )


def _drawer(dataset: Dataset, stages) -> None:
    panel = st.session_state.drawer_panel
    if panel is None:
        st.markdown("#### Inputs")
        st.caption("Pick what you want to change.")
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
        _panel_scrap()
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
    st.markdown("### How this route flows")
    st.caption(
        "Material runs left to right; the red branches are the carbon each department "
        "releases on the way."
    )
    st.plotly_chart(
        charts.plant_flow(result, dataset.departments),
        use_container_width=True,
        config=charts.PLOT_CONFIG,
    )
    st.markdown(SCROLL_HINT.format(label="Scroll for the scope breakdown"), unsafe_allow_html=True)

    st.markdown('<div class="cs-stage">', unsafe_allow_html=True)
    st.markdown("### Where the carbon sits")
    st.plotly_chart(
        charts.scope_breakdown(result),
        use_container_width=True,
        config=charts.PLOT_CONFIG,
    )
    st.markdown(SCROLL_HINT.format(label="Scroll for the department split"), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

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
            "label": f"Captured: y={st.session_state.scrap}%, p={st.session_state.train}%",
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
            "label": "Default baseline: y=40%, India grid today, first-listed technologies",
        }
    st.info(saved["label"])

    baseline = calculate(
        saved["scrap"], saved["mix"], dataset, route_weights(saved["route"]), saved["train"]
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
            dataset, stages, constraints, st.session_state.route, optimise_route=optimise_route
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
    st.plotly_chart(
        charts.scrap_sweep(optimum.sweep, optimum.scrap_ratio),
        use_container_width=True,
        config=charts.PLOT_CONFIG,
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
    bar = st.columns([0.6, 3.2, 1.5, 1.3])
    bar[0].button("☰", on_click=_toggle_drawer, use_container_width=True,
                  help="Show or hide the input drawer")
    bar[1].markdown(
        f'<div style="display:flex;align-items:center;gap:10px;font-weight:800;'
        f'font-size:1.1rem">{spark_mark(24)} CarbonSpark <span class="cs-chip">tool</span></div>',
        unsafe_allow_html=True,
    )
    bar[2].button("Database", on_click=go, args=("database",), use_container_width=True)
    bar[3].button("← Back to site", on_click=go, args=("landing",), use_container_width=True)

    if st.session_state.drawer_open:
        drawer, main = st.columns([3, 7], gap="large")
        with drawer:
            st.markdown('<div class="cs-drawer">', unsafe_allow_html=True)
            _drawer(dataset, stages)
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        main = st.container()

    # The drawer mutates the route as it renders, so the result is computed
    # afterwards — otherwise every reading would lag one interaction behind.
    weights = route_weights(st.session_state.route)
    if not weights:
        with main:
            st.error(
                "Every stage is switched off. Open the drawer and add at least one process."
            )
        return
    result = calculate(scrap_ratio(), current_mix(), dataset, weights, train_share())

    with main:
        _headline(result, dataset)
        view = st.radio(
            "View",
            ["Dashboard", "Baseline comparison", "Optimiser", "Process grid"],
            horizontal=True,
            key="tool_view",
            label_visibility="collapsed",
        )
        st.divider()
        if view == "Dashboard":
            _dashboard(result, dataset, stages)
        elif view == "Baseline comparison":
            _baseline(result, dataset, stages)
        elif view == "Optimiser":
            _optimiser(result, dataset, stages)
        else:
            _process_grid(result, dataset)
