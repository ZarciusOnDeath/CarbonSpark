"""Session state for CarbonSpark.

Streamlit has one sharp edge that shapes this module: a slider whose ``key`` was
written in an *earlier* run renders at its minimum, even though session state
holds the right number. Presets therefore appeared to leave the sliders where
they were. The fix is to keep the truth in plain (non-widget) state — ``mix``,
``scrap``, ``train`` — and give each widget its own key seeded through ``value=``
the first time it renders. Widgets write back to the truth in their callbacks,
and presets update both, so what the sliders show is always what the model used.
"""

from __future__ import annotations

from typing import Dict, Mapping

import streamlit as st

from carbon_calc.model import MIX_VARIABLES, Dataset
from carbon_calc.route import RouteMix, Stage, build_stages, default_route, normalise_mix

from .presets import GRID_PRESETS, PLANT_PROFILES, profile_route

#: Widget keys, kept distinct from the truth keys they mirror.
SCRAP_W = "w_scrap"
TRAIN_W = "w_train"
INBOUND_W = "w_inbound"
PROFILE_W = "w_plant_profile"
PRESET_W = "w_grid_preset"


def mix_widget(var: str) -> str:
    return f"w_mix_{var}"


# --------------------------------------------------------------------------- #
# Reading the truth
# --------------------------------------------------------------------------- #
def current_mix() -> Dict[str, float]:
    """The grid mix as fractions."""
    return {var: st.session_state.mix[var] / 100.0 for var in MIX_VARIABLES}


def mix_total() -> float:
    return sum(st.session_state.mix[var] for var in MIX_VARIABLES)


def scrap_ratio() -> float:
    return st.session_state.scrap / 100.0


def train_share() -> float:
    return st.session_state.train / 100.0


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
        st.session_state.mix[var] = values[var]
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
    write_mix(
        {var: st.session_state.mix[var] / total for var in MIX_VARIABLES},
    )


def on_mix_change(var: str) -> None:
    """Slider callback: adopt the new value and leave the others alone.

    Rescaling here would fight the user: setting four shares in a row would see
    the first three rewritten under their hand before the fourth was entered.
    Normalising is an explicit button in the panel instead.
    """
    st.session_state.mix[var] = st.session_state[mix_widget(var)]


def on_scrap_change() -> None:
    st.session_state.scrap = st.session_state[SCRAP_W]


def on_train_change() -> None:
    st.session_state.train = st.session_state[TRAIN_W]


def on_inbound_change() -> None:
    st.session_state.inbound = st.session_state[INBOUND_W]


def apply_grid_preset() -> None:
    """Preset callback: move the sliders to the chosen preset immediately."""
    st.session_state.grid_preset = st.session_state[PRESET_W]
    preset = GRID_PRESETS.get(st.session_state.grid_preset)
    if preset:
        write_mix(preset)


def apply_plant_profile(stages) -> None:
    """Load a plant profile: route, scrap ratio, haulage split and energy mix."""
    if PROFILE_W in st.session_state:
        st.session_state.plant_profile = st.session_state[PROFILE_W]
    profile = PLANT_PROFILES.get(st.session_state.get("plant_profile"))
    if profile is None:
        return
    route, problems = profile_route(profile, stages)
    st.session_state.route = route
    st.session_state.profile_problems = problems

    st.session_state.scrap = int(round(profile.scrap_ratio * 100))
    st.session_state.train = int(round(profile.train_share * 100))
    if SCRAP_W in st.session_state:
        st.session_state[SCRAP_W] = st.session_state.scrap
    if TRAIN_W in st.session_state:
        st.session_state[TRAIN_W] = st.session_state.train

    st.session_state.grid_preset = profile.grid_preset
    if PRESET_W in st.session_state:
        st.session_state[PRESET_W] = profile.grid_preset
    write_mix(GRID_PRESETS[profile.grid_preset])

    # A profile replaces the route wholesale, so the per-department technique
    # pickers must be rebuilt rather than kept from the previous selection.
    for key in [k for k in st.session_state if k.startswith(("techniques_", "vars_", "share_"))]:
        del st.session_state[key]


def set_stage_mix(stage: Stage, mix: Mapping[int, float]) -> None:
    route: RouteMix = st.session_state.route
    route[stage.key] = {int(pid): float(share) for pid, share in mix.items() if share > 0}


def init_state(dataset: Dataset) -> tuple:
    """Initialise state once per session and return the stage list."""
    stages = build_stages(dataset)
    if st.session_state.get("initialised"):
        return stages

    st.session_state.initialised = True
    st.session_state.page = "landing"
    st.session_state.scrap = 40
    st.session_state.train = 50
    st.session_state.inbound = 50
    st.session_state.mix = {}
    st.session_state.grid_preset = "India grid today"
    write_mix(GRID_PRESETS["India grid today"])
    st.session_state.route = default_route(stages)
    st.session_state.profile_problems = []
    st.session_state.plant_profile = "Custom"
    st.session_state.drawer_open = False
    st.session_state.drawer_panel = None
    st.session_state.baseline = None
    st.session_state.tool_view = "Dashboard"
    return stages


def go(page: str) -> None:
    st.session_state.page = page
