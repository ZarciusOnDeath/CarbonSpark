"""Figures for CarbonSpark.

Three decisions shape every figure here.

*No zoom.* Both axes are ``fixedrange``, ``dragmode`` is off and ``PLOT_CONFIG``
hides the mode bar, so the accidental zoom that made the charts confusing is
gone. Hover stays, so a value can still be interrogated.

*A fixed scale.* The x-axis is pinned to a reference span rather than rescaled
to whatever the current bars happen to be. An axis that follows its own data
makes every scenario look the same size; a fixed one lets a route that halves
its carbon visibly halve.

*Motion.* ``layout.transition`` plus a stable chart key means Plotly tweens the
bars from their old values to their new ones, instead of repainting them.
"""

from __future__ import annotations

from typing import Mapping, Sequence

import plotly.graph_objects as go
import streamlit as st

from carbon_calc.model import SCOPES, Result

from .theme import STACK_ORDER, SCOPE_NAMES, scope_colours, tokens


def _mode() -> bool:
    return bool(st.session_state.get("dark", False))


def _ink() -> str:
    return tokens(_mode())["ink"]


def _grid() -> str:
    return tokens(_mode())["line"]

#: Passed to every ``st.plotly_chart`` call.
PLOT_CONFIG = {
    "displayModeBar": False,
    "scrollZoom": False,
    "doubleClick": False,
    "showTips": False,
    "staticPlot": False,
}

_FONT_FAMILY = "Inter, Segoe UI, system-ui, sans-serif"


def _font(size: int = 14) -> dict:
    return dict(family=_FONT_FAMILY, color=_ink(), size=size)

#: Bars tween to their new values rather than jumping there.
_TRANSITION = dict(duration=520, easing="cubic-in-out")

#: The x-axis span, in tCO2e/t, that the scope and department charts are drawn
#: against. It is a little above the default route's own total so a heavier
#: scenario still fits, and it never moves — that is the point of it.
SCOPE_AXIS_MAX = 4.2
DEPARTMENT_AXIS_MAX = 4.2


def _lock(figure: go.Figure, height: int) -> go.Figure:
    """Disable zoom/pan and apply the shared chart styling."""
    # Plotly falls back to its own dark greys for ticks, titles, legends and
    # hover labels unless each is told otherwise, which is why the charts were
    # unreadable on a dark ground even with layout.font set.
    ink, soft = _ink(), tokens(_mode())["ink_soft"]
    axis = dict(
        fixedrange=True,
        gridcolor=_grid(),
        zerolinecolor=_grid(),
        linecolor=_grid(),
        tickfont=dict(color=soft, size=13, family=_FONT_FAMILY),
        title_font=dict(color=soft, size=13, family=_FONT_FAMILY),
    )
    figure.update_xaxes(**axis)
    figure.update_yaxes(**axis)
    figure.update_layout(
        dragmode=False,
        height=height,
        font=_font(),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(font=dict(color=ink, size=13, family=_FONT_FAMILY)),
        hoverlabel=dict(
            font=dict(color=tokens(_mode())["paper"], size=13, family=_FONT_FAMILY),
            bgcolor=ink,
            bordercolor=ink,
        ),
        transition=_TRANSITION,
    )
    return figure


def scope_breakdown(result: Result, height: int = 520) -> go.Figure:
    """Where the carbon sits: the three scopes, largest bar first."""
    values = [result.totals[scope] for scope in SCOPES]
    figure = go.Figure(
        go.Bar(
            x=values,
            y=[SCOPE_NAMES[scope] for scope in SCOPES],
            orientation="h",
            marker_color=[scope_colours(_mode())[scope] for scope in SCOPES],
            text=[f"{value:.3f}" for value in values],
            textposition="auto",
            textfont=dict(size=16, color=tokens(_mode())["paper"], family=_FONT_FAMILY),
            insidetextanchor="end",
            cliponaxis=False,
            hovertemplate="%{y}<br><b>%{x:.4f} tCO2e/t</b><extra></extra>",
        )
    )
    figure.update_layout(
        xaxis=dict(title="tCO2e per tonne of steel", range=[0, SCOPE_AXIS_MAX]),
        yaxis_title=None,
        bargap=0.42,
    )
    return _lock(figure, height)


def department_breakdown(result: Result, height: int = 520) -> go.Figure:
    """Every department, stacked by scope, heaviest at the top."""
    departments = sorted(
        result.by_department,
        key=lambda name: result.by_department[name]["total_co2e"],
    )
    figure = go.Figure()
    for scope in STACK_ORDER:
        figure.add_bar(
            x=[result.by_department[name][scope] for name in departments],
            y=departments,
            name=SCOPE_NAMES[scope],
            # The stack order is a legibility choice; the legend still reads
            # Scope 1, 2, 3.
            legendrank=SCOPES.index(scope),
            orientation="h",
            marker_color=scope_colours(_mode())[scope],
            hovertemplate="%{y} · %{fullData.name}<br><b>%{x:.4f} tCO2e/t</b><extra></extra>",
        )
    figure.update_layout(
        barmode="stack",
        bargap=0.34,
        xaxis=dict(title="tCO2e per tonne of steel", range=[0, DEPARTMENT_AXIS_MAX]),
        # Below the plot, anchored to the top of its own band: an overlay legend
        # sat on the widest bar and hid the very numbers it was labelling.
        legend=dict(orientation="h", yanchor="top", y=-0.14, x=0),
        legend_title_text="",
        margin=dict(l=10, r=10, t=18, b=96),
    )
    return _lock(figure, height)


def comparison_bars(
    labels: Sequence[str],
    results: Sequence[Result],
    height: int = 420,
) -> go.Figure:
    """Two or more scenarios side by side, stacked by scope."""
    figure = go.Figure()
    for scope in STACK_ORDER:
        figure.add_bar(
            x=list(labels),
            y=[result.totals[scope] for result in results],
            name=SCOPE_NAMES[scope],
            legendrank=SCOPES.index(scope),
            marker_color=scope_colours(_mode())[scope],
            hovertemplate="%{x} · %{fullData.name}<br><b>%{y:.4f} tCO2e/t</b><extra></extra>",
        )
    figure.update_layout(
        barmode="stack",
        yaxis_title="tCO2e per tonne",
        legend=dict(orientation="h", yanchor="bottom", y=-0.22, x=0),
        legend_title_text="",
    )
    return _lock(figure, height)


def mix_donut(mix: Mapping[str, float], sources: Mapping[str, object], height: int = 300) -> go.Figure:
    """The grid mix as a donut, so the sliders have a visual counterpart."""
    order = [var for var in mix if mix.get(var, 0) > 0.0005]
    active = tokens(_mode())
    # Seven generation sources is past the three a categorical set can carry, so
    # the donut leans on its labels: fossil sources are neutral greys stepped by
    # weight, and only the renewables and nuclear take a hue.
    palette = {
        "a": "#5a564e" if not _mode() else "#8d887d",
        "b": "#7b6a56" if not _mode() else "#a3927c",
        "c": "#9d9384" if not _mode() else "#bdb3a2",
        "d": active["steel"],
        "e": active["green"],
        "f": active["amber"],
        "g": "#7a6f9c" if not _mode() else "#9b8fc0",
    }
    figure = go.Figure(
        go.Pie(
            labels=[getattr(sources[var], "source", var) for var in order],
            values=[mix[var] for var in order],
            hole=0.62,
            marker=dict(colors=[palette.get(var, active["steel"]) for var in order]),
            textinfo="none",
            hovertemplate="%{label}<br><b>%{percent}</b><extra></extra>",
        )
    )
    figure.update_layout(
        height=height,
        font=_font(),
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=True,
        legend=dict(orientation="v", font=dict(size=11, color=_ink(), family=_FONT_FAMILY)),
    )
    return figure
