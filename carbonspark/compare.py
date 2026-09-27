"""The Compare view: two scenarios, each edited in place, side by side.

Scenario A's inputs slide in from the left and scenario B's from the right; the
comparison sits between them. Either panel can be open, both, or neither, and
the middle narrows and tightens its type when both are open so everything still
fits on one screen. Nothing has to be saved and loaded back: each side holds
its own inputs for as long as the session lasts.

Each side carries every input the calculator has: the starting plant, scrap
share, grid mix, rail share per leg, and the full department -> process route,
with each process switched on or off or set to one of its variations.
"""

from __future__ import annotations

import html
from typing import Dict

import pandas as pd
import streamlit as st

from carbon_calc.advice import Scenario, evaluate
from carbon_calc.model import MIX_VARIABLES, Dataset, Result, mix_factor
import json

from carbon_calc.route import coefficient_model, normalise_mix, route_weights

from . import charts
from .tables import table
from .live import html_escape
from .presets import GRID_PRESETS, PLANT_PROFILES, profile_route
from .theme import DEPARTMENT_ICONS
from .state import current_mix, inbound_rail, inbound_share, outbound_rail, scrap_ratio

SIDES = ("A", "B")
SIDE_NAMES = {"A": "Scenario A", "B": "Scenario B"}



def _k(side: str, name: str) -> str:
    return f"cmp_{side}_{name}"


# --------------------------------------------------------------------------- #
# State
# --------------------------------------------------------------------------- #
def _set_side(side: str, stages, scrap: float, mix: Dict[str, float], rail_in: float,
              rail_out: float, route, profile: str) -> None:
    """Write one side's inputs into its widgets' state."""
    st.session_state[_k(side, "profile")] = profile
    st.session_state[_k(side, "route")] = {key: dict(value) for key, value in route.items()}
    st.session_state[_k(side, "scrap")] = int(round(scrap * 100))
    st.session_state[_k(side, "rail_in")] = int(round(rail_in * 100))
    st.session_state[_k(side, "rail_out")] = int(round(rail_out * 100))
    st.session_state[_k(side, "preset")] = next(
        (name for name, preset in GRID_PRESETS.items()
         if all(abs(preset.get(v, 0) - mix.get(v, 0)) < 0.005 for v in MIX_VARIABLES)),
        "Custom mix",
    )
    for var in MIX_VARIABLES:
        st.session_state[_k(side, f"mix_{var}")] = int(round(mix.get(var, 0.0) * 100))
    _route_widgets(side, stages, route)



def _route_widgets(side: str, stages, route) -> None:
    """Point every process widget of a side at the given route."""
    for stage in stages:
        running = normalise_mix(route.get(stage.key, {}))
        if len(stage.options) == 1:
            st.session_state[_k(side, f"on_{stage.key}")] = bool(running)
            continue
        st.session_state[_k(side, f"ms_{stage.key}")] = [
            stage.option_by_id(pid).variation for pid in running
        ]
        for pid, share in running.items():
            st.session_state[_k(side, f"sh_{stage.key}_{pid}")] = int(round(share * 100))


def _set_on(side: str, stage) -> None:
    route = st.session_state[_k(side, "route")]
    on = st.session_state[_k(side, f"on_{stage.key}")]
    route[stage.key] = {stage.default_id: 1.0} if on else {}


def _set_variations(side: str, stage) -> None:
    """Technologies picked for a stage: an even split to start, kept shares kept."""
    route = st.session_state[_k(side, "route")]
    names = st.session_state[_k(side, f"ms_{stage.key}")]
    ids = [o.id for o in stage.options if o.variation in names]
    if not ids:
        route[stage.key] = {}
        return
    current = normalise_mix(route.get(stage.key, {}))
    kept = {pid: current[pid] for pid in ids if pid in current}
    if len(kept) != len(ids):
        kept = {pid: 1.0 / len(ids) for pid in ids}
    route[stage.key] = normalise_mix(kept)
    for pid, share in route[stage.key].items():
        st.session_state[_k(side, f"sh_{stage.key}_{pid}")] = int(round(share * 100))


def _set_shares(side: str, stage) -> None:
    route = st.session_state[_k(side, "route")]
    ids = list(normalise_mix(route.get(stage.key, {})))
    raw = {pid: float(st.session_state.get(_k(side, f"sh_{stage.key}_{pid}"), 0)) for pid in ids}
    route[stage.key] = normalise_mix(raw) or {pid: 1.0 / len(ids) for pid in ids}


def _init(stages) -> None:
    """Both sides start as the calculator's current scenario."""
    if st.session_state.get("cmp_ready"):
        return
    for side in SIDES:
        _set_side(side, stages, scrap_ratio(), current_mix(), inbound_rail(),
                  outbound_rail(), st.session_state.route, st.session_state.plant_profile)
    st.session_state.cmp_open = {"A": True, "B": True}
    st.session_state.cmp_ready = True


def _load_profile(side: str, stages) -> None:
    profile = PLANT_PROFILES[st.session_state[_k(side, "profile")]]
    route, _ = profile_route(profile, stages)
    _set_side(side, stages, profile.scrap_ratio, GRID_PRESETS[profile.grid_preset],
              profile.inbound_rail, profile.outbound_rail, route, profile.name)


def _apply_preset(side: str) -> None:
    preset = GRID_PRESETS.get(st.session_state[_k(side, "preset")])
    if preset:
        for var in MIX_VARIABLES:
            st.session_state[_k(side, f"mix_{var}")] = int(round(preset[var] * 100))


def _mark_custom(side: str) -> None:
    st.session_state[_k(side, "preset")] = "Custom mix"


def _copy(source: str, target: str) -> None:
    """Make one side a copy of the other, to change a single lever from there."""
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith(f"cmp_{source}_"):
            value = st.session_state[key]
            st.session_state[f"cmp_{target}_" + key[len(f"cmp_{source}_"):]] = (
                {k: dict(v) for k, v in value.items()} if isinstance(value, dict) else value
            )


def _toggle(side: str) -> None:
    st.session_state.cmp_open[side] = not st.session_state.cmp_open[side]


def scenario(side: str, stages) -> Scenario:
    """The side's inputs as a model scenario."""
    raw = {var: float(st.session_state[_k(side, f"mix_{var}")]) for var in MIX_VARIABLES}
    total = sum(raw.values()) or 1.0
    mix = {var: value / total for var, value in raw.items()}
    route = {key: dict(value) for key, value in st.session_state[_k(side, "route")].items()}
    return Scenario(
        st.session_state[_k(side, "scrap")] / 100.0,
        mix,
        st.session_state[_k(side, "rail_in")] / 100.0,
        st.session_state[_k(side, "rail_out")] / 100.0,
        route,
        inbound_share(),
    )


# --------------------------------------------------------------------------- #
# The two input panels
# --------------------------------------------------------------------------- #
def _panel(side: str, dataset: Dataset, stages) -> None:
    other = "B" if side == "A" else "A"
    with st.container(border=True, key=f"cs_cmp_panel_{side}"):
        head = st.columns([3, 1])
        head[0].markdown(f'<div class="cs-cmp-title cs-cmp-{side}">{SIDE_NAMES[side]}</div>',
                         unsafe_allow_html=True)
        head[1].button(":material/close:", key=f"cmp_close_{side}", on_click=_toggle,
                       args=(side,), use_container_width=True)
        st.button(f"Copy {SIDE_NAMES[other]} here", key=f"cmp_copy_{side}", on_click=_copy,
                  args=(other, side), use_container_width=True)

        st.selectbox("Starting plant", list(PLANT_PROFILES), key=_k(side, "profile"),
                     on_change=_load_profile, args=(side, stages))
        st.slider("Scrap in the charge", 0, 100, key=_k(side, "scrap"), format="%d%%")

        presets = list(GRID_PRESETS) + ["Custom mix"]
        st.selectbox("Grid electricity", presets, key=_k(side, "preset"),
                     on_change=_apply_preset, args=(side,))
        with st.expander("Fine-tune the grid mix"):
            for var in MIX_VARIABLES:
                source = dataset.source_by_var[var]
                st.slider(source.source, 0, 100, key=_k(side, f"mix_{var}"), format="%d%%",
                          on_change=_mark_custom, args=(side,))
            total = sum(st.session_state[_k(side, f"mix_{v}")] for v in MIX_VARIABLES)
            if total != 100:
                st.caption(f"Shares add to {total}%; they are scaled to 100% in the result.")

        st.slider("Rail share, inbound", 0, 100, key=_k(side, "rail_in"), format="%d%%")
        st.slider("Rail share, outbound", 0, 100, key=_k(side, "rail_out"), format="%d%%")

        st.markdown("**Plant route**")
        route = st.session_state[_k(side, "route")]
        for department in dataset.departments:
            dept_stages = [stage for stage in stages if stage.department == department]
            running = sum(1 for stage in dept_stages if normalise_mix(route.get(stage.key, {})))
            with st.expander(f"{department} \u00b7 {running} of {len(dept_stages)}",
                             icon=DEPARTMENT_ICONS.get(department)):
                for stage in dept_stages:
                    if len(stage.options) == 1:
                        st.checkbox(stage.process, key=_k(side, f"on_{stage.key}"),
                                    on_change=_set_on, args=(side, stage))
                    else:
                        st.multiselect(
                            stage.process, [o.variation for o in stage.options],
                            key=_k(side, f"ms_{stage.key}"), placeholder="Off",
                            on_change=_set_variations, args=(side, stage),
                        )
                        picked = normalise_mix(route.get(stage.key, {}))
                        # Two or more technologies split the stage's tonne.
                        if len(picked) > 1:
                            for pid in picked:
                                st.slider(
                                    f"{stage.option_by_id(pid).variation} share", 0, 100,
                                    key=_k(side, f"sh_{stage.key}_{pid}"), format="%d%%",
                                    on_change=_set_shares, args=(side, stage),
                                )


# --------------------------------------------------------------------------- #
# The comparison in the middle
# --------------------------------------------------------------------------- #
def _delta(new: float, old: float) -> str:
    diff = new - old
    pct = f" ({diff / old:+.1%})" if old else ""
    return f"{diff:+.3f}{pct}"


def _middle(results: Dict[str, Result], scenarios: Dict[str, Scenario], dataset: Dataset,
            compact: bool) -> None:
    a, b = results["A"], results["B"]
    with st.container(key="cs_cmp_mid_compact" if compact else "cs_cmp_mid"):
        cards = st.columns(3)
        for column, side in zip((cards[0], cards[2]), SIDES):
            result = results[side]
            column.markdown(
                f'<div class="cs-cmp-card cs-cmp-{side}"><span>{SIDE_NAMES[side]}</span>'
                f"<b>{result.total_co2e:.3f}</b><small>tCO₂e per tonne</small></div>",
                unsafe_allow_html=True,
            )
        diff = b.total_co2e - a.total_co2e
        verdict = "lower" if diff < 0 else "higher" if diff > 0 else "the same"
        cards[1].markdown(
            f'<div class="cs-cmp-card cs-cmp-diff"><span>B vs A</span>'
            f"<b>{diff:+.3f}</b><small>{abs(diff) / a.total_co2e:.1%} {verdict}</small></div>"
            if a.total_co2e else "",
            unsafe_allow_html=True,
        )

        st.plotly_chart(
            charts.comparison_bars(["Scenario A", "Scenario B"], [a, b],
                                   height=300 if compact else 380),
            use_container_width=True, config=charts.PLOT_CONFIG,
        )

        rows = [
            ("Total CO₂e", a.total_co2e, b.total_co2e),
            ("Scope 1", a.totals["scope1"], b.totals["scope1"]),
            ("Scope 2", a.totals["scope2"], b.totals["scope2"]),
            ("Scope 3", a.totals["scope3"], b.totals["scope3"]),
            ("Energy (GJ/t)", a.energy_gj, b.energy_gj),
        ]
        table(
            pd.DataFrame(
                [{"": label, "A": f"{va:.3f}", "B": f"{vb:.3f}", "B − A": _delta(vb, va)}
                 for label, va, vb in rows]
            ),
            use_container_width=True, hide_index=True,
        )

        # What differs between the two, so the gap has a reason next to it.
        sa, sb = scenarios["A"], scenarios["B"]
        levers = [
            ("Scrap", f"{sa.scrap:.0%}", f"{sb.scrap:.0%}"),
            ("Grid factor", f"{mix_factor(sa.mix, dataset):.3f}", f"{mix_factor(sb.mix, dataset):.3f}"),
            ("Rail in / out", f"{sa.rail_in:.0%} / {sa.rail_out:.0%}", f"{sb.rail_in:.0%} / {sb.rail_out:.0%}"),
        ]
        changed = [row for row in levers if row[1] != row[2]]
        if changed:
            st.markdown(
                "**What differs:** "
                + " · ".join(f"{name} {html.escape(x)} → {html.escape(y)}"
                                  for name, x, y in changed)
            )
        departments = sorted(set(a.by_department) | set(b.by_department),
                             key=lambda d: -max(a.by_department.get(d, {}).get("total_co2e", 0),
                                                b.by_department.get(d, {}).get("total_co2e", 0)))
        with st.expander("By department", expanded=not compact):
            table(
                pd.DataFrame([
                    {
                        "Department": d,
                        "A": round(a.by_department.get(d, {}).get("total_co2e", 0.0), 3),
                        "B": round(b.by_department.get(d, {}).get("total_co2e", 0.0), 3),
                        "B − A": round(b.by_department.get(d, {}).get("total_co2e", 0.0)
                                            - a.by_department.get(d, {}).get("total_co2e", 0.0), 3),
                    }
                    for d in departments
                ]),
                use_container_width=True, hide_index=True,
            )


def render(dataset: Dataset, stages) -> None:
    _init(stages)
    opened = st.session_state.cmp_open

    # Open buttons for closed panels sit on their own side.
    if not (opened["A"] and opened["B"]):
        ends = st.columns([1, 2, 1])
        if not opened["A"]:
            ends[0].button(":material/tune:  Edit Scenario A", key="cmp_open_A",
                           on_click=_toggle, args=("A",), use_container_width=True, type="primary")
        if not opened["B"]:
            ends[2].button("Edit Scenario B  :material/tune:", key="cmp_open_B",
                           on_click=_toggle, args=("B",), use_container_width=True, type="primary")

    if opened["A"] and opened["B"]:
        left, mid, right = st.columns([1, 1.5, 1], gap="medium")
    elif opened["A"]:
        left, mid = st.columns([1, 2.2], gap="medium")
        right = None
    elif opened["B"]:
        mid, right = st.columns([2.2, 1], gap="medium")
        left = None
    else:
        mid, left, right = st.container(), None, None

    # Panels first: their widgets update state before the results are read.
    if left is not None:
        with left:
            _panel("A", dataset, stages)
    if right is not None:
        with right:
            _panel("B", dataset, stages)

    scenarios = {side: scenario(side, stages) for side in SIDES}
    # Each side's coefficient model, so the page can follow a slider drag for
    # that side (see the Compare block in live.py).
    for side in SIDES:
        sc = scenarios[side]
        model = coefficient_model(dataset, route_weights(sc.route))
        model.pop("departments", None)
        model["sourceLabels"] = {var: dataset.source_by_var[var].source for var in MIX_VARIABLES}
        model["values"] = {
            "scrap": sc.scrap, "railIn": sc.rail_in, "railOut": sc.rail_out,
            "share": sc.inbound_share,
            "mix": {var: st.session_state[_k(side, f"mix_{var}")] / 100.0 for var in MIX_VARIABLES},
        }
        st.markdown(
            f'<div data-cs-cmp="{side}" data-model="{html_escape(json.dumps(model))}" '
            'style="display:none"></div>',
            unsafe_allow_html=True,
        )
    results: Dict[str, Result] = {}
    for side in SIDES:
        try:
            results[side] = evaluate(dataset, scenarios[side])
        except Exception as error:  # an empty route, for instance
            with mid:
                st.error(f"{SIDE_NAMES[side]} cannot be evaluated: {error}")
            return
    with mid:
        _middle(results, scenarios, dataset, compact=opened["A"] and opened["B"])
