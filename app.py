"""CarbonSpark — carbon and energy calculator for stainless steelmaking.

Jindal Stainless engineering case study, Problem Statement 3.

Every figure is computed by evaluating the process-step formulas extracted from
the Stainless Steel Carbon Accounting Grid workbook at the user's chosen scrap
ratio, grid energy mix and rail/road haulage split.
"""

from __future__ import annotations

import streamlit as st

from carbon_calc.model import load_dataset
from carbonspark import database, landing, loading, tool
from carbonspark.state import init_state
from carbonspark.styles import base_css

st.set_page_config(
    page_title="CarbonSpark",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)
DATASET = load_dataset()
STAGES = init_state(DATASET)

# The stylesheet is rendered for the active mode, after state exists to say
# which mode that is.
st.markdown(base_css(st.session_state.dark), unsafe_allow_html=True)

page = st.session_state.page
if page == "loading":
    loading.render()
elif page == "tool":
    tool.render(DATASET, STAGES)
elif page == "database":
    database.render(DATASET)
else:
    landing.render(DATASET)
