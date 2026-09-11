"""Session state for CarbonSpark.

Two ideas run through this module.

**The truth is not the widget.** A slider whose ``key`` was written in an
earlier run renders at its minimum even though session state holds the right
number, which is why presets appeared to leave the sliders where they were. So
plain state holds the truth, each widget has its own key seeded through
``value=``, and callbacks write back.

**Some panels are staged.** The grid mix and the process route are edited as a
*draft* and only reach the model when Apply is pressed. Seven shares or fifty
tick-boxes are one decision, not fifty; recomputing between each one made the
figures jump around while the user was still halfway through expressing an
intent. The scrap and haulage sliders are not staged — they are single
decisions, and their feedback is the point.
"""

from __future__ import annotations

from typing import Dict, Mapping

import streamlit as st

from carbon_calc.model import MIX_VARIABLES, Dataset
from carbon_calc.route import RouteMix, Stage, build_stages, default_route, normalise_mix

from .presets import GRID_PRESETS, OPENING_PROFILE, PLANT_PROFILES, profile_route

#: Widget keys, kept distinct from the truth keys they mirror.
SCRAP_W = "w_scrap"
TRAIN_IN_W = "w_train_in"
TRAIN_OUT_W = "w_train_out"
INBOUND_W = "w_inbound"
PROFILE_W = "w_plant_profile"
PRESET_W = "w_grid_preset"


def mix_widget(var: str) -> str:
    return f"w_mix_{var}"


# --------------------------------------------------------------------------- #
# Reading the truth
# --------------------------------------------------------------------------- #
def current_mix() -> Dict[str, float]:
    """The applied grid mix, as fractions — this is what the model reads."""
    return {var: st.session_state.mix[var] / 100.0 for var in MIX_VARIABLES}


def draft_mix() -> Dict[str, float]:
    """The mix as the sliders currently stand, applied or not."""
    return {var: st.session_state.mix_draft[var] / 100.0 for var in MIX_VARIABLES}


def mix_total() -> float:
    return sum(st.session_state.mix_draft[var] for var in MIX_VARIABLES)


def mix_dirty() -> bool:
    """True when the sliders hold something the model has not been given yet."""
    return any(
        abs(st.session_state.mix_draft[var] - st.session_state.mix[var]) > 1e-9
        for var in MIX_VARIABLES
    )


def apply_mix() -> None:
    """Hand the drafted mix to the model."""
    st.session_state.mix = dict(st.session_state.mix_draft)


def revert_mix() -> None:
    """Throw the draft away and put the sliders back on the applied mix."""
    write_mix(st.session_state.mix, as_fraction=False)


def route_dirty() -> bool:
    """True when the tick-boxes hold a route the model has not been given yet."""
    return _route_signature(st.session_state.route_draft) != _route_signature(
        st.session_state.route
    )


def _route_signature(route) -> tuple:
    return tuple(
        sorted(
            (key, tuple(sorted(normalise_mix(mix).items())))
            for key, mix in route.items()
            if normalise_mix(mix)
        )
    )


def apply_route() -> None:
    """Hand the drafted route to the model."""
    st.session_state.route = {
        key: dict(value) for key, value in st.session_state.route_draft.items()
    }


def revert_route() -> None:
    """Throw the drafted route away and rebuild the tick-boxes from the applied one."""
    st.session_state.route_draft = {
        key: dict(value) for key, value in st.session_state.route.items()
    }
    forget_route_widgets()


def forget_route_widgets() -> None:
    """Rebuild every route widget from the draft.

    Deleting the widgets' session-state keys looked like the way to do this, and
    it crashed: a checkbox whose key had been removed while the widget was still
    on screen raised ``KeyError`` in its own callback the next time it was
    clicked — which is what happened when switching between the two site
    profiles. Instead the generation counter moves, every route widget key
    changes with it, and Streamlit builds fresh widgets seeded from the draft.
    The old keys are simply never asked for again.
    """
    st.session_state.route_generation = st.session_state.get("route_generation", 0) + 1


def route_key(prefix: str, name: str) -> str:
    """A widget key that changes whenever the route is replaced wholesale."""
    return f"{prefix}_{name}_g{st.session_state.get('route_generation', 0)}"


def scrap_ratio() -> float:
    return st.session_state.scrap / 100.0


def train_share() -> float:
    """The tonne-weighted rail share, for headline reporting only."""
    inbound = st.session_state.inbound / 100.0
    return (
        st.session_state.train_in / 100.0 * inbound
        + st.session_state.train_out / 100.0 * (1.0 - inbound)
    )


def inbound_rail() -> float:
    return st.session_state.train_in / 100.0


def outbound_rail() -> float:
    return st.session_state.train_out / 100.0


def inbound_share() -> float:
    """How the haulage tonne-movement splits between the inbound and outbound legs."""
    return st.session_state.inbound / 100.0


# --------------------------------------------------------------------------- #
# Writing the truth (and the widgets that mirror it)
# --------------------------------------------------------------------------- #
def write_mix(mix: Mapping[str, float], *, as_fraction: bool = True) -> None:
    """Set the mix, moving any slider that is already on screen.

    Values are shown to one decimal place, so the rounding residual is given to
    the largest share — otherwise a rescaled mix displays as 99.9% or 100.1%.
    """
    scale = 100.0 if as_fraction else 1.0
    values = {var: round(float(mix.get(var, 0.0)) * scale, 1) for var in MIX_VARIABLES}
    total = sum(values.values())
    if values and abs(total - 100.0) < 0.5 and total != 100.0:
        largest = max(values, key=lambda var: values[var])
        values[largest] = round(values[largest] + (100.0 - total), 1)
    for var in MIX_VARIABLES:
        st.session_state.mix_draft[var] = values[var]
        if mix_widget(var) in st.session_state:
            st.session_state[mix_widget(var)] = values[var]


def rescale_mix() -> None:
    """Rescale the mix so the shares sum to exactly 100%.

    This rewrites the slider values themselves rather than normalising silently
    behind the scenes, so the sliders always show the mix the model used.
    """
    total = mix_total()
    if total <= 0:
        return
    write_mix({var: st.session_state.mix_draft[var] / total for var in MIX_VARIABLES})


def on_mix_change(var: str) -> None:
    """Slider callback: adopt the new value and leave the others alone.

    Rescaling here would fight the user: setting four shares in a row would see
    the first three rewritten under their hand before the fourth was entered.
    Normalising is an explicit button in the panel instead.
    """
    st.session_state.mix_draft[var] = st.session_state[mix_widget(var)]


def on_scrap_change() -> None:
    st.session_state.scrap = st.session_state[SCRAP_W]


def on_train_in_change() -> None:
    st.session_state.train_in = st.session_state[TRAIN_IN_W]


def on_train_out_change() -> None:
    st.session_state.train_out = st.session_state[TRAIN_OUT_W]


def on_inbound_change() -> None:
    st.session_state.inbound = st.session_state[INBOUND_W]


def apply_grid_preset() -> None:
    """Preset callback: move the sliders and apply, since a preset is one decision."""
    st.session_state.grid_preset = st.session_state[PRESET_W]
    preset = GRID_PRESETS.get(st.session_state.grid_preset)
    if preset:
        write_mix(preset)
        apply_mix()


def apply_plant_profile(stages) -> None:
    """Load a plant profile: route, scrap ratio, haulage split and energy mix."""
    if PROFILE_W in st.session_state:
        st.session_state.plant_profile = st.session_state[PROFILE_W]
    profile = PLANT_PROFILES.get(st.session_state.get("plant_profile"))
    if profile is None:
        return
    route, problems = profile_route(profile, stages)
    st.session_state.route = route
    st.session_state.route_draft = {key: dict(value) for key, value in route.items()}
    st.session_state.profile_problems = problems

    st.session_state.scrap = int(round(profile.scrap_ratio * 100))
    st.session_state.train_in = int(round(profile.inbound_rail * 100))
    st.session_state.train_out = int(round(profile.outbound_rail * 100))
    if SCRAP_W in st.session_state:
        st.session_state[SCRAP_W] = st.session_state.scrap
    for widget, value in (
        (TRAIN_IN_W, st.session_state.train_in),
        (TRAIN_OUT_W, st.session_state.train_out),
    ):
        if widget in st.session_state:
            st.session_state[widget] = value

    st.session_state.grid_preset = profile.grid_preset
    if PRESET_W in st.session_state:
        st.session_state[PRESET_W] = profile.grid_preset
    write_mix(GRID_PRESETS[profile.grid_preset])
    apply_mix()

    # A profile replaces the route wholesale, so every route widget is dropped
    # and rebuilt from the new route. Without this the tick-boxes would keep
    # showing the previous plant's selections while the model used the new one.
    forget_route_widgets()


def set_stage_mix(stage: Stage, mix: Mapping[int, float]) -> None:
    route: RouteMix = st.session_state.route_draft
    route[stage.key] = {int(pid): float(share) for pid, share in mix.items() if share > 0}


def snapshot(label: str) -> Dict[str, object]:
    """Freeze the scenario now on screen, so it can be compared with later."""
    return {
        "label": label,
        "scrap": scrap_ratio(),
        "mix": current_mix(),
        "route": {key: dict(value) for key, value in st.session_state.route.items()},
        "train": train_share(),
        "inbound": inbound_share(),
        "rail_in": inbound_rail(),
        "rail_out": outbound_rail(),
    }


#: Widget keys the comparison view owns.
SAVE_NAME_W = "cmp_save_name"
COMPARE_RIGHT_W = "cmp_right"


def save_scenario() -> None:
    """Keep the current scenario under the name typed beside the button.

    The name is read from session state rather than passed in: a callback's
    arguments are bound when the button is *drawn*, which is before the user has
    typed anything, so passing the text box's value saved the previous one.
    """
    typed = str(st.session_state.get(SAVE_NAME_W, "")).strip()
    name = typed or f"Scenario {len(st.session_state.scenarios) + 1}"
    st.session_state.scenarios[name] = snapshot(name)
    st.session_state[SAVE_NAME_W] = ""


def delete_scenario(name: str) -> None:
    """Forget a saved scenario."""
    st.session_state.scenarios.pop(name, None)


def toggle_dark() -> None:
    st.session_state.dark = not st.session_state.dark


def init_state(dataset: Dataset) -> tuple:
    """Initialise state once per session and return the stage list."""
    stages = build_stages(dataset)
    if st.session_state.get("initialised"):
        return stages

    st.session_state.initialised = True
    st.session_state.page = "landing"
    st.session_state.scrap = 40
    st.session_state.train_in = 50
    st.session_state.train_out = 50
    st.session_state.inbound = 50
    st.session_state.mix = {}
    st.session_state.mix_draft = {}
    st.session_state.grid_preset = "India grid today"
    write_mix(GRID_PRESETS["India grid today"])
    apply_mix()
    st.session_state.route = default_route(stages)
    st.session_state.route_draft = {
        key: dict(value) for key, value in st.session_state.route.items()
    }
    # Which drill-down rows were open when the last rerun happened, so ticking a
    # box does not fold the list up under the user's hand.
    st.session_state.route_generation = 0
    st.session_state.open_department = None
    st.session_state.open_stage = None
    st.session_state.dark = False
    st.session_state.profile_problems = []
    # The app opens on the larger of the two sites rather than on "everything
    # the workbook lists", so the first thing on screen is a real plant.
    st.session_state.plant_profile = OPENING_PROFILE
    st.session_state.drawer_open = False
    st.session_state.drawer_panel = None
    # Saved scenarios, by name, for the comparison view. A scenario is a frozen
    # copy of every input, so comparing two of them is comparing two plants
    # rather than a plant against a fixed reference.
    st.session_state.scenarios = {}
    st.session_state.tool_view = "Dashboard"
    apply_plant_profile(stages)
    return stages


def go(page: str) -> None:
    st.session_state.page = page
