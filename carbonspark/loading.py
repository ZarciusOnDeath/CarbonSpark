"""The two-second welcome that plays on the way into the tool."""

from __future__ import annotations

import time

import streamlit as st

from .theme import wordmark

WELCOME = f"""
<div class="cs-splash-cover"><div class="cs-splash">
  <h1>Welcome to</h1>
  <div class="cs-rise">{wordmark(4.6)}</div>
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
    # The calculator opens on its figures. A lever card on the landing page
    # ("Try it") names a panel, and only then does it arrive with inputs open.
    panel = st.session_state.pop("pending_panel", None)
    st.session_state.drawer_open = panel is not None
    st.session_state.drawer_panel = panel
    st.session_state.page = "tool"
    st.rerun()
