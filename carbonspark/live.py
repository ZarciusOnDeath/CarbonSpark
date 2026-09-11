"""Live slider readouts.

Streamlit commits a slider to the server on release, not during the drag, so the
metrics and charts necessarily update when you let go. What *can* follow the
thumb is the text that is pure arithmetic on the slider's own value — "virgin
x = 60%", "road q = 50%" — and that is what makes a slider feel alive.

This module injects a small script into the parent document that mirrors any
slider's value into the chips that describe it while it is being dragged. Each
chip declares which slider it follows and how to render it::

    <span data-cs-live="Scrap steel ratio  y" data-cs-template="scrap y = {v}%">

``{v}`` is the slider value and ``{inv}`` is ``100 − v``, which covers every
complement in the tool (virgin/scrap, rail/road, inbound/outbound).

The script is injected through ``components.html`` — Streamlit strips scripts
from ``st.markdown`` — so it runs in a zero-height iframe and reaches the page
through ``window.parent.document``.
"""

from __future__ import annotations

import json
from typing import Mapping

import streamlit as st
import streamlit.components.v1 as components

_SCRIPT = """
<script>
(function () {
  const doc = window.parent.document;
  if (doc.__csLiveSliders) { doc.__csLiveSliders.sync(); return; }

  const labelOf = (slider) => {
    const label = slider.querySelector('label');
    return label ? label.innerText.trim().replace(/\\s+/g, ' ') : '';
  };

  // Streamlit renders the thumb as a plain div, so the live value is read from
  // the bubble it paints above it — that text tracks the drag. The ARIA path is
  // kept as a fallback in case a future release makes the thumb a real slider.
  const valueOf = (slider) => {
    const bubble = slider.querySelector('[data-testid="stSliderThumbValue"]');
    if (bubble) {
      const parsed = parseFloat(bubble.innerText.replace(/[^0-9.\\-]/g, ''));
      if (!Number.isNaN(parsed)) return parsed;
    }
    const thumb = slider.querySelector('[role="slider"]');
    if (thumb && thumb.getAttribute('aria-valuenow') !== null) {
      return parseFloat(thumb.getAttribute('aria-valuenow'));
    }
    return NaN;
  };

  // --- the figures follow the drag ----------------------------------------
  // The server only learns a slider's value on release, so the readout is
  // recomputed in the page from the coefficient model the route exports. It is
  // the same arithmetic, re-arranged — see route.coefficient_model.
  const readModel = () => {
    const node = doc.querySelector('[data-cs-model]');
    if (!node) return null;
    try { return JSON.parse(node.getAttribute('data-cs-model')); } catch (e) { return null; }
  };

  const sliderValue = (label, fallback) => {
    const sliders = [...doc.querySelectorAll('div[data-testid="stSlider"]')];
    for (const slider of sliders) {
      if (labelOf(slider) === label) {
        const value = valueOf(slider);
        if (!Number.isNaN(value)) return value / 100;
      }
    }
    return fallback;
  };

  const recompute = () => {
    const model = readModel();
    if (!model) return;
    const y = sliderValue(model.labels.scrap, model.values.scrap);
    const x = 1 - y;
    const share = sliderValue(model.labels.inbound, model.values.inbound);
    const railIn = sliderValue(model.labels.railIn, model.values.railIn);
    const railOut = sliderValue(model.labels.railOut, model.values.railOut);
    const wIn = 2 * share;
    const wOut = 2 * (1 - share);

    const leg = (quad, p) => {
      const q = 1 - p;
      return quad[0] * x * p + quad[1] * x * q + quad[2] * y * p + quad[3] * y * q;
    };
    const totalOf = (key) =>
      model.base[key][0] * x +
      model.base[key][1] * y +
      wIn * leg(model.inbound[key], railIn) +
      wOut * leg(model.outbound[key], railOut);

    const scope1 = totalOf('scope1');
    const scope3 = totalOf('scope3');
    const scope2 = totalOf('kwh') * model.gridFactor / 1000;
    const energy = totalOf('sec');
    const figures = {
      total: (scope1 + scope2 + scope3).toFixed(3),
      scope1: scope1.toFixed(3),
      scope2: scope2.toFixed(3),
      scope3: scope3.toFixed(3),
      energy: energy.toFixed(1),
    };
    doc.querySelectorAll('[data-cs-metric]').forEach((node) => {
      const value = figures[node.getAttribute('data-cs-metric')];
      if (value !== undefined && node.textContent !== value) node.textContent = value;
    });
    redrawCharts(model, { x: x, y: y, share: share, railIn: railIn, railOut: railOut });

    const note = doc.querySelector('[data-cs-conditions]');
    if (note) {
      const railBlend = railIn * share + railOut * (1 - share);
      note.textContent =
        'scrap ' + Math.round(y * 100) + '% \u00b7 rail ' + Math.round(railBlend * 100) + '%';
    }
  };

  // --- the charts follow the drag too --------------------------------------
  // Plotly is on the page, and each figure carries a `meta.live` tag saying
  // what it draws, so the bars can be moved to the values just computed. The
  // server still redraws on release; this keeps the picture honest in between.
  const blockValue = (block, key, at) => {
    const leg = (quad, p) => {
      const q = 1 - p;
      return quad[0] * at.x * p + quad[1] * at.x * q + quad[2] * at.y * p + quad[3] * at.y * q;
    };
    return (
      block.base[key][0] * at.x +
      block.base[key][1] * at.y +
      2 * at.share * leg(block.inbound[key], at.railIn) +
      2 * (1 - at.share) * leg(block.outbound[key], at.railOut)
    );
  };

  const scopesOf = (block, model, at) => ({
    scope1: blockValue(block, 'scope1', at),
    scope2: blockValue(block, 'kwh', at) * model.gridFactor / 1000,
    scope3: blockValue(block, 'scope3', at),
  });

  const redrawCharts = (model, at) => {
    const Plotly = window.parent.Plotly;
    if (!Plotly || !model.departments) return;
    doc.querySelectorAll('.js-plotly-plot').forEach((gd) => {
      const meta = gd.layout && gd.layout.meta;
      if (!meta || !meta.live) return;
      try {
        if (meta.live === 'scopes') {
          const values = scopesOf(model, model, at);
          const x = meta.scopes.map((scope) => values[scope]);
          Plotly.restyle(gd, {
            x: [x],
            text: [x.map((value) => value.toFixed(3))],
          }, [0]);
        } else if (meta.live === 'departments') {
          const perDept = meta.departments.map((name) => {
            const block = model.departments[name];
            return block ? scopesOf(block, model, at) : { scope1: 0, scope2: 0, scope3: 0 };
          });
          meta.order.forEach((scope, index) => {
            Plotly.restyle(gd, { x: [perDept.map((row) => row[scope])] }, [index]);
          });
        }
      } catch (error) {
        /* a chart mid-render is not worth interrupting the drag for */
      }
    });
  };

  const paint = () => {
    const sliders = [...doc.querySelectorAll('div[data-testid="stSlider"]')];
    const byLabel = new Map();
    sliders.forEach((s) => byLabel.set(labelOf(s), s));
    doc.querySelectorAll('[data-cs-live]').forEach((chip) => {
      const slider = byLabel.get(chip.getAttribute('data-cs-live').replace(/\\s+/g, ' ').trim());
      if (!slider) return;
      const value = valueOf(slider);
      if (Number.isNaN(value)) return;
      const rounded = Math.round(value * 10) / 10;
      const shown = Number.isInteger(rounded) ? rounded.toFixed(0) : rounded.toFixed(1);
      const inverse = Math.round((100 - value) * 10) / 10;
      const inverseShown = Number.isInteger(inverse) ? inverse.toFixed(0) : inverse.toFixed(1);
      const text = (chip.getAttribute('data-cs-template') || '{v}')
        .replace('{v}', shown)
        .replace('{inv}', inverseShown);
      if (chip.textContent !== text) chip.textContent = text;
    });
  };

  // Pointer events fire continuously through a drag; the observer catches the
  // keyboard case and any re-render Streamlit does underneath us.
  let frame = null;
  const schedule = () => {
    if (frame) return;
    frame = requestAnimationFrame(() => { frame = null; paint(); recompute(); });
  };
  ['pointerdown', 'pointermove', 'pointerup', 'keydown', 'keyup', 'input'].forEach((event) =>
    doc.addEventListener(event, schedule, true)
  );
  // characterData catches the thumb bubble's own text changing, which is what
  // moves during a drag; childList catches Streamlit re-rendering underneath.
  new MutationObserver(schedule).observe(doc.body, {
    subtree: true, childList: true, characterData: true,
    attributes: true, attributeFilter: ['aria-valuenow', 'style'],
  });

  // --- the readout condenses as the page scrolls ---------------------------
  const scroller = () =>
    doc.querySelector('section[data-testid="stMain"]') ||
    doc.querySelector('.main') ||
    doc.scrollingElement;

  const condense = () => {
    const dock = doc.querySelector('.st-key-cs_readout');
    const box = scroller();
    if (!dock || !box) return;
    const past = (box.scrollTop || 0) > 90;
    dock.classList.toggle('cs-condensed', past);
  };

  // --- the drawer keeps its scroll position across reruns ------------------
  // Streamlit rebuilds the column on every interaction, so ticking a box would
  // otherwise throw the user back to the top of a long list.
  const drawerCol = () => {
    const drawer = doc.querySelector('.st-key-cs_drawer');
    return drawer ? drawer.closest('div[data-testid="stColumn"]') : null;
  };
  let savedScroll = 0;
  const rememberScroll = () => {
    const column = drawerCol();
    if (column && column.scrollTop > 0) savedScroll = column.scrollTop;
  };
  const restoreScroll = () => {
    const column = drawerCol();
    if (column && savedScroll > 0 && Math.abs(column.scrollTop - savedScroll) > 4) {
      column.scrollTop = savedScroll;
    }
  };

  const onScroll = () => { rememberScroll(); condense(); };
  doc.addEventListener('scroll', onScroll, true);

  // --- a new page opens at its top -----------------------------------------
  // Streamlit keeps the main container's scroll position across a page change,
  // so arriving from the landing page dropped the reader at the bottom of the
  // tool. The page stamps a token when it changes; each new token scrolls once.
  const openAtTop = () => {
    const stamp = doc.querySelector('[data-cs-page]');
    if (!stamp) return;
    const token = stamp.getAttribute('data-cs-page');
    if (doc.__csPage === token) return;
    doc.__csPage = token;
    savedScroll = 0;
    const box = scroller();
    if (box) box.scrollTo({ top: 0, behavior: 'auto' });
  };

  const tick = () => { openAtTop(); schedule(); restoreScroll(); condense(); };
  new MutationObserver(tick).observe(doc.body, { subtree: true, childList: true });

  doc.__csLiveSliders = { sync: tick };
  openAtTop();
  paint();
  recompute();
  condense();
})();
</script>
"""


def enable(page: str = "", model: Mapping[str, object] | None = None) -> None:
    """Install the live-readout script for this page render.

    ``page`` tells the script a navigation happened, so it scrolls the new page
    to its top exactly once. ``model`` is the route's coefficient model, which
    lets the readout follow a drag instead of waiting for the release.
    """
    payload = html_escape(json.dumps(model)) if model else ""
    st.markdown(
        f'<div data-cs-page="{page}" data-cs-model="{payload}" style="display:none"></div>',
        unsafe_allow_html=True,
    )
    components.html(_SCRIPT, height=0, width=0)


def html_escape(text: str) -> str:
    """Escape a JSON payload for an HTML attribute."""
    return (
        text.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
    )


def rendered_chip(label: str, template: str, value: float, *, tone: str = "") -> str:
    """A chip that follows ``label``'s slider while that slider is dragged.

    ``template`` is rendered with ``{v}`` (the slider value) and ``{inv}``
    (100 − value), which covers every complement in the tool. The text is also
    filled in server-side from ``value``, so the chip is correct before the
    script runs and if scripting is unavailable.
    """
    shown = f"{value:g}"
    inverse = f"{100 - value:g}"
    text = template.replace("{v}", shown).replace("{inv}", inverse)
    classes = f"cs-chip {tone}".strip()
    return (
        f'<span class="{classes}" data-cs-live="{label}" '
        f'data-cs-template="{template}">{text}</span>'
    )
