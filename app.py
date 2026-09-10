"""Carbon & Energy Calculator for Steelmaking — Streamlit application.

Jindal Stainless engineering case study, Problem Statement 3. Every figure shown
is computed by evaluating the 71 process-step formulas extracted from
"Stainless Steel Carbon Accounting Grid (3).xlsx" at the user's chosen scrap
ratio and grid energy mix.
"""

from __future__ import annotations

import math
from typing import Dict, Mapping

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from carbon_calc.model import (
    INDIA_GRID_MIX,
    METRIC_LABELS,
    METRICS,
    MIX_VARIABLES,
    REFERENCE_GRID_FACTOR,
    SCOPES,
    TRACE_GASES,
    Result,
    calculate,
    load_dataset,
    mix_factor,
)
from carbon_calc.optimize import Constraints, InfeasibleError, optimise
from carbon_calc.route import build_stages, default_selection, selection_to_ids

st.set_page_config(
    page_title="Carbon & Energy Calculator — Steelmaking",
    page_icon="🔥",
    layout="wide",
)

SCOPE_COLOURS = {"scope1": "#c0392b", "scope2": "#e08e0b", "scope3": "#2e86c1"}
SCOPE_NAMES = {
    "scope1": "Scope 1 — direct",
    "scope2": "Scope 2 — purchased electricity",
    "scope3": "Scope 3 — upstream (Cat. 1-8)",
}

#: Ready-made mixes users can drop in before fine-tuning.
MIX_PRESETS: Dict[str, Dict[str, float]] = {
    "India grid today (workbook reference)": INDIA_GRID_MIX,
    "Coal only": {"a": 1.0},
    "Gas-heavy transition": {"a": 0.25, "c": 0.40, "d": 0.10, "e": 0.10, "f": 0.10, "g": 0.05},
    "50% renewable PPA": {"a": 0.35, "c": 0.10, "d": 0.15, "e": 0.20, "f": 0.15, "g": 0.05},
    "Near-zero carbon grid": {"d": 0.25, "e": 0.40, "f": 0.25, "g": 0.10},
}

DATASET = load_dataset()
STAGES = build_stages(DATASET)
STAGE_BY_KEY = {stage.key: stage for stage in STAGES}
SOURCES = DATASET.source_by_var


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def normalise(mix: Mapping[str, float]) -> Dict[str, float]:
    """Rescale shares to sum to 1. An all-zero mix is left alone."""
    total = sum(max(0.0, float(v)) for v in mix.values())
    if total <= 0:
        return {var: 0.0 for var in MIX_VARIABLES}
    return {var: max(0.0, float(mix.get(var, 0.0))) / total for var in MIX_VARIABLES}


def run(scrap_ratio: float, mix: Mapping[str, float], selection, enabled) -> Result:
    return calculate(scrap_ratio, mix, DATASET, selection_to_ids(STAGES, selection, enabled))


def scope_frame(result: Result) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Scope": [SCOPE_NAMES[s] for s in SCOPES],
            "tCO2e/t": [result.totals[s] for s in SCOPES],
            "colour": [SCOPE_COLOURS[s] for s in SCOPES],
        }
    )


def process_frame(result: Result) -> pd.DataFrame:
    frame = pd.DataFrame(list(result.per_process))
    frame = frame.rename(columns={**METRIC_LABELS, "total_co2e": "Total CO2e (tCO2e/t)"})
    return frame.drop(columns=["id"])


def format_mix(mix: Mapping[str, float]) -> str:
    parts = [
        f"{SOURCES[var].source} {mix[var]:.0%}" for var in MIX_VARIABLES if mix.get(var, 0) > 0.0005
    ]
    return ", ".join(parts) if parts else "—"


def init_state() -> None:
    if "initialised" in st.session_state:
        return
    st.session_state.initialised = True
    st.session_state.scrap_ratio = 0.40
    for var in MIX_VARIABLES:
        st.session_state[f"mix_{var}"] = INDIA_GRID_MIX.get(var, 0.0) * 100
    for stage in STAGES:
        st.session_state[f"stage_{stage.key}"] = stage.default_id
        st.session_state[f"on_{stage.key}"] = True
    st.session_state.baseline = None


def apply_preset(name: str) -> None:
    preset = MIX_PRESETS[name]
    for var in MIX_VARIABLES:
        st.session_state[f"mix_{var}"] = preset.get(var, 0.0) * 100


init_state()


# --------------------------------------------------------------------------- #
# Sidebar — the two levers plus the route
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("Inputs")

    st.subheader("Input mix")
    scrap_ratio = st.slider(
        "Scrap steel ratio  y  (%)",
        min_value=0,
        max_value=100,
        value=int(round(st.session_state.scrap_ratio * 100)),
        step=1,
        help="Share of scrap in the metallic charge. Virgin ratio x = 1 − y.",
    ) / 100
    st.session_state.scrap_ratio = scrap_ratio
    st.caption(f"x = {1 - scrap_ratio:.0%} virgin  ·  y = {scrap_ratio:.0%} scrap")

    st.subheader("Grid energy mix")
    preset_name = st.selectbox("Preset", list(MIX_PRESETS), index=0)
    st.button("Apply preset", on_click=apply_preset, args=(preset_name,), use_container_width=True)

    raw_mix: Dict[str, float] = {}
    for var in MIX_VARIABLES:
        source = SOURCES[var]
        raw_mix[var] = st.slider(
            f"{source.source}  ({var})  —  {source.ef} kg CO2e/kWh",
            min_value=0.0,
            max_value=100.0,
            step=1.0,
            key=f"mix_{var}",
        ) / 100

    share_sum = sum(raw_mix.values())
    auto_normalise = st.checkbox(
        "Normalise shares to 100%",
        value=True,
        help="a + b + c + d + e + f + g must sum to 1. When off, the shares are used as entered.",
    )
    mix = normalise(raw_mix) if auto_normalise else raw_mix
    if abs(share_sum - 1.0) > 0.005:
        message = f"Shares entered sum to {share_sum:.0%}."
        if auto_normalise:
            st.info(message + " Rescaled to 100% for the calculation.")
        else:
            st.warning(message + " Results will not represent one full tonne of electricity demand.")

    grid_factor = mix_factor(mix, DATASET)
    st.metric("Blended grid factor", f"{grid_factor:.3f} kg CO2e/kWh")
    st.caption(f"Workbook reference (CEA midpoint): {REFERENCE_GRID_FACTOR} kg CO2e/kWh")

    st.subheader("Process route")
    st.caption(
        "Stages that offer interchangeable technologies are selectable. "
        "Deselect a stage to exclude it from the route."
    )
    with st.expander("Technology choices", expanded=False):
        for stage in STAGES:
            if not stage.has_choice:
                continue
            options = [option.id for option in stage.options]
            st.selectbox(
                f"{stage.department} — {stage.process}",
                options=options,
                format_func=lambda pid, s=stage: s.option_by_id(pid).variation,
                key=f"stage_{stage.key}",
            )
    with st.expander("Stages included", expanded=False):
        for stage in STAGES:
            st.checkbox(f"{stage.department} — {stage.process}", key=f"on_{stage.key}")

selection = {stage.key: st.session_state[f"stage_{stage.key}"] for stage in STAGES}
enabled = {stage.key: st.session_state[f"on_{stage.key}"] for stage in STAGES}
active_stages = sum(1 for value in enabled.values() if value)

if active_stages == 0:
    st.error("No process stages are selected. Enable at least one stage in the sidebar.")
    st.stop()

result = run(scrap_ratio, mix, selection, enabled)

st.title("Carbon & Energy Calculator for Steelmaking")
st.caption(
    f"{len(DATASET.processes)} process-step formulas across {len(STAGES)} stages, "
    "evaluated live from the Stainless Steel Carbon Accounting Grid."
)

tab_calc, tab_grid, tab_compare, tab_optimise, tab_method = st.tabs(
    ["Calculator", "Process grid", "Baseline comparison", "Optimiser", "Methodology"]
)


# --------------------------------------------------------------------------- #
# Calculator
# --------------------------------------------------------------------------- #
with tab_calc:
    columns = st.columns(5)
    columns[0].metric("Total CO2e", f"{result.total_co2e:.3f} t/t")
    columns[1].metric("Scope 1", f"{result.totals['scope1']:.3f} t/t")
    columns[2].metric("Scope 2", f"{result.totals['scope2']:.3f} t/t")
    columns[3].metric("Scope 3 upstream", f"{result.totals['scope3']:.3f} t/t")
    columns[4].metric("Specific energy", f"{result.energy_gj:.1f} GJ/t")

    kwh = result.electricity_kwh
    st.caption(
        f"Route: {active_stages} of {len(STAGES)} stages  ·  "
        f"purchased electricity ≈ {'n/a' if math.isnan(kwh) else f'{kwh:,.0f} kWh/t'}  ·  "
        f"grid mix: {format_mix(mix)}"
    )

    left, right = st.columns([1, 1])
    with left:
        st.subheader("Where the carbon sits")
        frame = scope_frame(result)
        figure = px.bar(
            frame,
            x="tCO2e/t",
            y="Scope",
            orientation="h",
            text=frame["tCO2e/t"].map("{:.3f}".format),
            color="Scope",
            color_discrete_sequence=list(frame["colour"]),
        )
        figure.update_layout(showlegend=False, height=280, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(figure, use_container_width=True)

    with right:
        st.subheader("By department")
        dept = pd.DataFrame(
            [
                {"Department": name, **{SCOPE_NAMES[s]: values[s] for s in SCOPES}}
                for name, values in result.by_department.items()
            ]
        ).sort_values(SCOPE_NAMES["scope2"], ascending=True)
        figure = px.bar(
            dept,
            x=[SCOPE_NAMES[s] for s in SCOPES],
            y="Department",
            orientation="h",
            color_discrete_sequence=[SCOPE_COLOURS[s] for s in SCOPES],
        )
        figure.update_layout(
            height=380,
            barmode="stack",
            xaxis_title="tCO2e/t",
            legend_title="",
            legend=dict(orientation="h", y=-0.2),
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(figure, use_container_width=True)

    st.subheader("Sensitivity to the scrap ratio")
    st.caption("Grid mix and route held at their current settings; only y is swept.")
    sweep_rows = []
    for step in range(0, 101, 2):
        candidate = run(step / 100, mix, selection, enabled)
        sweep_rows.append(
            {
                "Scrap ratio y": step / 100,
                "Total CO2e (t/t)": candidate.total_co2e,
                "Specific energy (GJ/t)": candidate.energy_gj,
            }
        )
    sweep = pd.DataFrame(sweep_rows)
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=sweep["Scrap ratio y"],
            y=sweep["Total CO2e (t/t)"],
            name="Total CO2e (t/t)",
            line=dict(color="#c0392b", width=3),
        )
    )
    figure.add_trace(
        go.Scatter(
            x=sweep["Scrap ratio y"],
            y=sweep["Specific energy (GJ/t)"],
            name="Specific energy (GJ/t)",
            yaxis="y2",
            line=dict(color="#2e86c1", width=2, dash="dot"),
        )
    )
    figure.add_vline(x=scrap_ratio, line_dash="dash", line_color="#555")
    figure.update_layout(
        height=360,
        xaxis=dict(title="Scrap ratio y", tickformat=".0%"),
        yaxis=dict(title="tCO2e/t"),
        yaxis2=dict(title="GJ/t", overlaying="y", side="right"),
        legend=dict(orientation="h", y=-0.25),
        margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(figure, use_container_width=True)

    st.subheader("Greenhouse gases (disaggregation)")
    st.caption(
        "The workbook reports gas-by-gas figures alongside the scope columns as a "
        "separate view of the same footprint — they are not added to the scope total."
    )
    gases = pd.DataFrame(
        [{"Gas": METRIC_LABELS[g], "tCO2e/t": result.totals[g]} for g in TRACE_GASES]
    )
    st.dataframe(
        gases.style.format({"tCO2e/t": "{:.5f}"}), use_container_width=True, hide_index=True
    )


# --------------------------------------------------------------------------- #
# Process grid
# --------------------------------------------------------------------------- #
with tab_grid:
    st.subheader("Per-process results and formula definitions")
    frame = process_frame(result)
    departments = st.multiselect(
        "Filter by department", DATASET.departments, default=DATASET.departments
    )
    view = frame[frame["Department"].isin(departments)]
    numeric = [column for column in view.columns if view[column].dtype.kind == "f"]
    st.dataframe(
        view.style.format({column: "{:.5f}" for column in numeric}),
        use_container_width=True,
        hide_index=True,
        height=420,
    )
    st.download_button(
        "Download these results as CSV",
        view.to_csv(index=False).encode("utf-8"),
        file_name=f"carbon_results_scrap_{scrap_ratio:.2f}.csv",
        mime="text/csv",
    )

    st.subheader("Formula definitions")
    st.caption("The plain-text formula entries from columns M-W, exactly as stored in the workbook.")
    chosen_ids = set(selection_to_ids(STAGES, selection, enabled))
    inspect = st.selectbox(
        "Process step",
        options=[proc.id for proc in DATASET.processes],
        format_func=lambda pid: (
            f"{'●' if pid in chosen_ids else '○'} "
            f"{next(p for p in DATASET.processes if p.id == pid).label}"
        ),
    )
    process = next(p for p in DATASET.processes if p.id == inspect)
    st.markdown(f"**{process.label}**  ·  {'in the current route' if inspect in chosen_ids else 'not in the current route'}")
    values = process.evaluate({"x": 1 - scrap_ratio, "y": scrap_ratio, **mix})
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Metric": METRIC_LABELS[metric],
                    "Formula": process.formulas[metric],
                    "Value at current inputs": values[metric],
                }
                for metric in METRICS
            ]
        ).style.format({"Value at current inputs": "{:.6f}"}),
        use_container_width=True,
        hide_index=True,
    )
    with st.expander("Coefficients and assumptions for this row"):
        st.text(process.notes or "No notes recorded.")


# --------------------------------------------------------------------------- #
# Baseline comparison
# --------------------------------------------------------------------------- #
with tab_compare:
    st.subheader("Compare the current scenario against a baseline")
    controls = st.columns([2, 1, 1])
    with controls[0]:
        st.caption(
            "The default baseline is a 40% scrap charge on today's Indian grid mix "
            "with the workbook's first-listed technology at every stage."
        )
    if controls[1].button("Capture current as baseline", use_container_width=True):
        st.session_state.baseline = {
            "scrap_ratio": scrap_ratio,
            "mix": dict(mix),
            "selection": dict(selection),
            "enabled": dict(enabled),
            "label": f"Captured: y={scrap_ratio:.0%}, {format_mix(mix)}",
        }
    if controls[2].button("Reset to default baseline", use_container_width=True):
        st.session_state.baseline = None

    if st.session_state.baseline is None:
        base_settings = {
            "scrap_ratio": 0.40,
            "mix": dict(INDIA_GRID_MIX),
            "selection": default_selection(STAGES),
            "enabled": {stage.key: True for stage in STAGES},
            "label": "Default baseline: y=40%, India grid today, first-listed technologies",
        }
    else:
        base_settings = st.session_state.baseline

    baseline = run(
        base_settings["scrap_ratio"],
        base_settings["mix"],
        base_settings["selection"],
        base_settings["enabled"],
    )
    st.info(base_settings["label"])

    def delta(current: float, base: float) -> str:
        if base == 0:
            return "n/a"
        return f"{(current - base) / base:+.1%}"

    metrics = st.columns(5)
    pairs = [
        ("Total CO2e", result.total_co2e, baseline.total_co2e, "{:.3f} t/t"),
        ("Scope 1", result.totals["scope1"], baseline.totals["scope1"], "{:.3f} t/t"),
        ("Scope 2", result.totals["scope2"], baseline.totals["scope2"], "{:.3f} t/t"),
        ("Scope 3 upstream", result.totals["scope3"], baseline.totals["scope3"], "{:.3f} t/t"),
        ("Specific energy", result.energy_gj, baseline.energy_gj, "{:.1f} GJ/t"),
    ]
    for column, (name, current, base, fmt) in zip(metrics, pairs):
        column.metric(name, fmt.format(current), delta(current, base), delta_color="inverse")

    saving = baseline.total_co2e - result.total_co2e
    if saving > 0:
        st.success(
            f"**{saving:.3f} tCO2e/t avoided** versus the baseline "
            f"({saving / baseline.total_co2e:.1%} lower). At 1 Mt/year of output that is "
            f"{saving * 1e6 / 1e3:,.0f} kt CO2e per year."
        )
    elif saving < 0:
        st.warning(
            f"**{-saving:.3f} tCO2e/t higher** than the baseline "
            f"({-saving / baseline.total_co2e:.1%} above it)."
        )
    else:
        st.info("The current scenario matches the baseline.")

    comparison = pd.DataFrame(
        [
            {"Scenario": "Baseline", "Scope": SCOPE_NAMES[s], "tCO2e/t": baseline.totals[s]}
            for s in SCOPES
        ]
        + [
            {"Scenario": "Current", "Scope": SCOPE_NAMES[s], "tCO2e/t": result.totals[s]}
            for s in SCOPES
        ]
    )
    figure = px.bar(
        comparison,
        x="Scenario",
        y="tCO2e/t",
        color="Scope",
        barmode="stack",
        color_discrete_map={SCOPE_NAMES[s]: SCOPE_COLOURS[s] for s in SCOPES},
    )
    figure.update_layout(height=380, legend=dict(orientation="h", y=-0.2), margin=dict(t=10))
    st.plotly_chart(figure, use_container_width=True)

    st.subheader("Department-level movement")
    rows = []
    for department in DATASET.departments:
        base_value = baseline.by_department.get(department, {}).get("total_co2e", 0.0)
        current_value = result.by_department.get(department, {}).get("total_co2e", 0.0)
        rows.append(
            {
                "Department": department,
                "Baseline (tCO2e/t)": base_value,
                "Current (tCO2e/t)": current_value,
                "Change (tCO2e/t)": current_value - base_value,
            }
        )
    movement = pd.DataFrame(rows)
    st.dataframe(
        movement.style.format(
            {
                "Baseline (tCO2e/t)": "{:.4f}",
                "Current (tCO2e/t)": "{:.4f}",
                "Change (tCO2e/t)": "{:+.4f}",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )


# --------------------------------------------------------------------------- #
# Optimiser
# --------------------------------------------------------------------------- #
with tab_optimise:
    st.subheader("Find the lowest-carbon path within your constraints")
    st.caption(
        "The search covers the scrap ratio, the seven grid shares and the technology "
        "choice at every stage. Set the limits that make the answer practical for your plant."
    )

    left, right = st.columns(2)
    with left:
        st.markdown("**Input mix**")
        scrap_range = st.slider(
            "Allowed scrap ratio range (%)",
            0,
            100,
            (0, 80),
            help="Scrap availability, grade requirements and residual-element limits cap "
            "how much scrap a real charge can take.",
        )
        st.markdown("**Route**")
        optimise_route = st.checkbox("Let the optimiser change technology choices", value=True)
        lockable = [stage.key for stage in STAGES if stage.has_choice]
        locked = st.multiselect(
            "Keep these stages as currently selected",
            options=lockable,
            format_func=lambda key: f"{STAGE_BY_KEY[key].department} — {STAGE_BY_KEY[key].process}",
            disabled=not optimise_route,
            help="Installed assets you are not going to replace.",
        )

    with right:
        st.markdown("**Grid energy mix limits**")
        max_coal = st.slider("Maximum coal share (%)", 0, 100, 40) / 100
        min_renewable = st.slider("Minimum renewable share — hydro + wind + solar (%)", 0, 100, 30) / 100
        min_non_fossil = st.slider(
            "Minimum non-fossil share — renewables + nuclear (%)", 0, 100, 30
        ) / 100
        cap_columns = st.columns(2)
        max_wind = cap_columns[0].slider("Maximum wind share (%)", 0, 100, 40) / 100
        max_solar = cap_columns[1].slider("Maximum solar share (%)", 0, 100, 40) / 100
        st.caption(
            "Caps on a single source keep the answer contractable — a plant rarely "
            "procures 100% of its power from one resource."
        )

    constraints = Constraints(
        scrap_min=scrap_range[0] / 100,
        scrap_max=scrap_range[1] / 100,
        mix_bounds={"a": (0.0, max_coal), "e": (0.0, max_wind), "f": (0.0, max_solar)},
        min_renewable=min_renewable,
        min_non_fossil=min_non_fossil,
        locked_stages=tuple(locked),
    )

    try:
        optimum = optimise(
            DATASET,
            STAGES,
            constraints,
            selection,
            enabled=enabled,
            optimise_route=optimise_route,
        )
    except InfeasibleError as error:
        st.error(f"No feasible scenario: {error}")
    else:
        saving = result.total_co2e - optimum.result.total_co2e
        headline = st.columns(4)
        headline[0].metric(
            "Optimised total CO2e",
            f"{optimum.result.total_co2e:.3f} t/t",
            f"{-saving:+.3f} vs current",
            delta_color="inverse",
        )
        headline[1].metric("Scrap ratio y", f"{optimum.scrap_ratio:.0%}")
        headline[2].metric("Blended grid factor", f"{optimum.grid_factor:.3f} kg CO2e/kWh")
        headline[3].metric(
            "Reduction",
            f"{saving / result.total_co2e:.1%}" if result.total_co2e else "n/a",
        )

        if saving > 1e-9:
            st.success(
                f"Cutting {saving:.3f} tCO2e/t against your current settings — "
                f"{saving * 1e6 / 1e3:,.0f} kt CO2e per year at 1 Mt of output."
            )
        else:
            st.info("Your current scenario is already at the optimum for these constraints.")

        st.markdown("**Recommended grid mix**")
        recommended = pd.DataFrame(
            [
                {
                    "Source": SOURCES[var].source,
                    "Variable": var,
                    "Current share": mix.get(var, 0.0),
                    "Optimised share": optimum.mix[var],
                    "kg CO2e/kWh": SOURCES[var].ef,
                }
                for var in MIX_VARIABLES
            ]
        )
        st.dataframe(
            recommended.style.format(
                {"Current share": "{:.1%}", "Optimised share": "{:.1%}", "kg CO2e/kWh": "{:.3f}"}
            ),
            use_container_width=True,
            hide_index=True,
        )

        if optimum.stage_changes:
            st.markdown("**Technology changes recommended**")
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Stage": f"{STAGE_BY_KEY[key].department} — {STAGE_BY_KEY[key].process}",
                            "Current": current,
                            "Recommended": proposed,
                        }
                        for key, current, proposed in optimum.stage_changes
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )
        elif optimise_route:
            st.caption("No technology change improves on your current route.")

        st.markdown("**Carbon against the scrap ratio at the optimised mix**")
        sweep = pd.DataFrame(optimum.sweep, columns=["Scrap ratio y", "Total CO2e (t/t)"])
        figure = px.line(sweep, x="Scrap ratio y", y="Total CO2e (t/t)")
        figure.update_traces(line=dict(color="#1e8449", width=3))
        figure.add_vline(x=optimum.scrap_ratio, line_dash="dash", line_color="#555")
        figure.update_layout(
            height=340, xaxis=dict(tickformat=".0%"), margin=dict(l=0, r=0, t=10, b=0)
        )
        st.plotly_chart(figure, use_container_width=True)

        st.markdown("**Scenario summary**")
        summary = pd.DataFrame(
            [
                {
                    "Scenario": "Current",
                    "Scrap ratio": scrap_ratio,
                    "Grid factor (kg CO2e/kWh)": result.grid_factor,
                    "Scope 1": result.totals["scope1"],
                    "Scope 2": result.totals["scope2"],
                    "Scope 3": result.totals["scope3"],
                    "Total CO2e (t/t)": result.total_co2e,
                    "Energy (GJ/t)": result.energy_gj,
                },
                {
                    "Scenario": "Optimised",
                    "Scrap ratio": optimum.scrap_ratio,
                    "Grid factor (kg CO2e/kWh)": optimum.grid_factor,
                    "Scope 1": optimum.result.totals["scope1"],
                    "Scope 2": optimum.result.totals["scope2"],
                    "Scope 3": optimum.result.totals["scope3"],
                    "Total CO2e (t/t)": optimum.result.total_co2e,
                    "Energy (GJ/t)": optimum.result.energy_gj,
                },
            ]
        )
        st.dataframe(
            summary.style.format(
                {
                    "Scrap ratio": "{:.0%}",
                    "Grid factor (kg CO2e/kWh)": "{:.3f}",
                    "Scope 1": "{:.3f}",
                    "Scope 2": "{:.3f}",
                    "Scope 3": "{:.3f}",
                    "Total CO2e (t/t)": "{:.3f}",
                    "Energy (GJ/t)": "{:.1f}",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )


# --------------------------------------------------------------------------- #
# Methodology
# --------------------------------------------------------------------------- #
with tab_method:
    st.subheader("How the numbers are produced")
    st.markdown(
        """
The calculator evaluates the formula entries held in **columns M-W** of the
*Carbon Accounting Grid* sheet — 71 process steps, 11 metrics each. Nothing is
re-derived: the workbook's coefficients are the model.

Two families of formula appear:

* **Input-mix driven** — `x * EF_virgin + y * EF_scrap`, where `y` is the scrap
  ratio and `x = 1 − y`. This covers Scope 1, Scope 3 upstream, the trace gases
  and specific energy consumption.
* **Grid-mix driven** — Scope 2 is
  `(x·kWh_virgin + y·kWh_scrap) × (a·EF_coal + b·EF_oil + c·EF_gas + d·EF_hydro +
  e·EF_wind + f·EF_solar + g·EF_nuclear) / 1000`, so the electricity demand comes
  from the input mix and the carbon intensity of that electricity comes from the
  source shares `a`-`g`, which sum to 1.

**Total CO2e per tonne = Scope 1 + Scope 2 + Scope 3 (upstream).** The gas-by-gas
columns are a disaggregation published alongside the scopes, not a fourth scope,
so they are shown separately and never added into the total.

**Route, not a sum of all 71 rows.** Several stages list mutually exclusive
alternatives — inbound by train, road or ocean; melting by EAF, IF, BF/converter,
VIM, VAR or ESR; and so on. A route takes exactly one variation per stage, which
is why the calculator groups the 71 rows into 48 stages. Adding every row would
double-count those alternatives.
        """
    )

    st.subheader("Grid source emission factors")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Source": SOURCES[var].source,
                    "Variable": var,
                    "kg CO2e/kWh": SOURCES[var].ef,
                    "Basis / notes": SOURCES[var].basis,
                }
                for var in MIX_VARIABLES
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Downstream Scope 3 (Categories 9-15)")
    st.caption(
        "Product-level categories from the workbook's second sheet. Only Category 9 "
        "varies by process and is already carried in the grid's Outbound transport rows; "
        "the rest are qualitative framing and are not quantified in the total above."
    )
    st.dataframe(
        pd.DataFrame(list(DATASET.downstream)).rename(
            columns={"category": "Category", "applicability": "Applicability", "notes": "Notes"}
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.warning(
        "**Disclaimer** — the coefficients in the source workbook are illustrative "
        "values chosen to demonstrate a working, formula-linked model. They are not "
        "measured or independently verified for any specific plant or grid connection. "
        "Replace them with verified plant data and your utility's disclosed emission "
        "factors before using any output for regulatory disclosure (BRSR, CBAM, EPD)."
    )
