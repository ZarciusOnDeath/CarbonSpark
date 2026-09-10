"""The two-second welcome that plays on the way into the tool."""

from __future__ import annotations

import time

import streamlit as st

from .theme import spark_mark

WELCOME = f"""
<div class="cs-splash">
  <div class="cs-rise">{spark_mark(64)}</div>
  <h1>Welcome to CarbonSpark</h1>
  <p>Loading the accounting grid and building your plant…</p>
  <div class="cs-loadbar"><i></i></div>
</div>"""


def render() -> None:
    placeholder = st.empty()
    placeholder.markdown(WELCOME, unsafe_allow_html=True)
    time.sleep(2.0)
    placeholder.empty()
    st.session_state.page = "tool"
    st.rerun()
