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
    frame = requestAnimationFrame(() => { frame = null; paint(); });
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

  doc.__csLiveSliders = { sync: schedule };
  paint();
})();
</script>
"""


def enable() -> None:
    """Install the live-readout script for this page render."""
    components.html(_SCRIPT, height=0, width=0)


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
