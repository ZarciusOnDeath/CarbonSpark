"""Tables drawn in the page's own colours.

``st.dataframe`` paints on a canvas with Streamlit's theme, and the theme is
pinned light (``.streamlit/config.toml``), so every table stayed light in dark
mode whatever the page's CSS said. These tables are plain HTML styled by the
page's colour tokens (``.cs-table`` in the stylesheet), so they follow the
mode. A long table keeps a bounded, scrolling box with a sticky header.

``table`` takes the same arguments as ``st.dataframe`` so a call can switch
over unchanged; the canvas-only ones (column config and so on) are ignored.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st


def table(data, use_container_width: bool = True, hide_index: bool = True,
          height: int | None = None, **_ignored) -> None:
    if isinstance(data, pd.io.formats.style.Styler):
        styler = data.hide(axis="index") if hide_index else data
        body = styler.to_html(table_attributes='class="cs-table"')
    else:
        frame = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
        body = frame.to_html(index=not hide_index, classes="cs-table", border=0,
                             escape=True, na_rep="")
    limit = f"max-height:{int(height)}px;" if height else ""
    st.markdown(f'<div class="cs-table-wrap" style="{limit}">{body}</div>',
                unsafe_allow_html=True)
