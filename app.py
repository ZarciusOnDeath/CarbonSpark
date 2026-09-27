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

# The landing nav's mode switch is a link (?mode=dark / ?mode=light). It must
# be read before the stylesheet is drawn: read after, the page came up with the
# light stylesheet over the dark backdrop, and its text went dark-on-dark.
if st.query_params.get("mode") in ("dark", "light"):
    st.session_state.dark = st.query_params.get("mode") == "dark"
    st.query_params.clear()

# The stylesheet is rendered for the active mode, after state exists to say
# which mode that is.
st.markdown(base_css(st.session_state.dark), unsafe_allow_html=True)

# The landing nav's "Open the calculator" is a plain link (?go=tool), so it
# works from anywhere on the page; it lands on the welcome screen like the
# buttons do.
if st.query_params.get("go") == "tool":
    st.query_params.clear()
    st.session_state.page = "loading"

page = st.session_state.page
if page == "loading":
    loading.render()
elif page == "tool":
    tool.render(DATASET, STAGES)
elif page == "database":
    database.render(DATASET)
else:
    landing.render(DATASET)
