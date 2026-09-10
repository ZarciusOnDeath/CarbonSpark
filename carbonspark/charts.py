"""Figures for CarbonSpark.

Every figure is locked against zoom and pan: both axes are ``fixedrange``,
``dragmode`` is off, and ``PLOT_CONFIG`` hides the mode bar and disables scroll
zoom. Hover stays on, so a reader can still interrogate a value — what goes is
the accidental zoom that made the charts confusing.
"""

from __future__ import annotations

from typing import Mapping, Sequence

import plotly.graph_objects as go

from carbon_calc.model import SCOPES, Result

from .theme import AMBER, GREEN, INK, SCOPE_COLOURS, SCOPE_NAMES, STEEL

#: Passed to every ``st.plotly_chart`` call.
PLOT_CONFIG = {
    "displayModeBar": False,
    "scrollZoom": False,
    "doubleClick": False,
    "showTips": False,
    "staticPlot": False,
}

_FONT = dict(family="Inter, Segoe UI, system-ui, sans-serif", color=INK, size=14)


def _lock(figure: go.Figure, height: int) -> go.Figure:
    """Disable zoom/pan and apply the shared chart styling."""
    figure.update_xaxes(fixedrange=True)
    figure.update_yaxes(fixedrange=True)
    figure.update_layout(
        dragmode=False,
        height=height,
        font=_FONT,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=30, b=10),
        hoverlabel=dict(font_size=13),
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
            marker_color=[SCOPE_COLOURS[scope] for scope in SCOPES],
            text=[f"{value:.3f}" for value in values],
            textposition="auto",
            textfont=dict(size=16),
            hovertemplate="%{y}<br><b>%{x:.4f} tCO2e/t</b><extra></extra>",
        )
    )
    figure.update_layout(
        xaxis_title="tCO2e per tonne of steel",
        yaxis_title=None,
        bargap=0.35,
    )
    return _lock(figure, height)


def department_breakdown(result: Result, height: int = 520) -> go.Figure:
    """Every department, stacked by scope, heaviest at the top."""
    departments = sorted(
        result.by_department,
        key=lambda name: result.by_department[name]["total_co2e"],
    )
    figure = go.Figure()
    for scope in SCOPES:
        figure.add_bar(
            x=[result.by_department[name][scope] for name in departments],
            y=departments,
            name=SCOPE_NAMES[scope],
            orientation="h",
            marker_color=SCOPE_COLOURS[scope],
            hovertemplate="%{y} · %{fullData.name}<br><b>%{x:.4f} tCO2e/t</b><extra></extra>",
        )
    figure.update_layout(
        barmode="stack",
        xaxis_title="tCO2e per tonne of steel",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        legend_title_text="",
        margin=dict(l=10, r=10, t=54, b=48),
    )
    return _lock(figure, height)


def comparison_bars(
    labels: Sequence[str],
    results: Sequence[Result],
    height: int = 420,
) -> go.Figure:
    """Two or more scenarios side by side, stacked by scope."""
    figure = go.Figure()
    for scope in SCOPES:
        figure.add_bar(
            x=list(labels),
            y=[result.totals[scope] for result in results],
            name=SCOPE_NAMES[scope],
            marker_color=SCOPE_COLOURS[scope],
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
    palette = {
        "a": "#4a4a4a", "b": "#7a5c3e", "c": AMBER, "d": STEEL,
        "e": GREEN, "f": "#e6c34a", "g": "#8e7cc3",
    }
    figure = go.Figure(
        go.Pie(
            labels=[getattr(sources[var], "source", var) for var in order],
            values=[mix[var] for var in order],
            hole=0.62,
            marker=dict(colors=[palette.get(var, STEEL) for var in order]),
            textinfo="none",
            hovertemplate="%{label}<br><b>%{percent}</b><extra></extra>",
        )
    )
    figure.update_layout(
        height=height,
        font=_FONT,
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=True,
        legend=dict(orientation="v", font=dict(size=11)),
    )
    return figure
