"""The two-second welcome that plays on the way into the tool."""

from __future__ import annotations

import time

import streamlit as st

from .theme import spark_mark

WELCOME = f"""
<div class="cs-splash-cover"><div class="cs-splash">
  <div class="cs-rise">{spark_mark(64)}</div>
  <h1>Welcome to CarbonSpark</h1>
  <p>Loading the accounting grid and building your plant…</p>
  <div class="cs-loadbar"><i></i></div>
</div></div>"""


def render() -> None:
    placeholder = st.empty()
    placeholder.markdown(WELCOME, unsafe_allow_html=True)
    time.sleep(2.0)
    placeholder.empty()
    # Arrive with the inputs open: people who met the dashboard first read the
    # figures as fixed and never found the controls.
    st.session_state.drawer_open = True
    st.session_state.drawer_panel = st.session_state.pop("pending_panel", None)
    st.session_state.page = "tool"
    st.rerun()
