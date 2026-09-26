"""Visual language for CarbonSpark: palette, page CSS and generated SVG art.

All artwork is hand-built inline SVG rather than fetched imagery — no network
requests, nothing to break on a deploy, no licensing question, and the motifs
share the app's palette exactly.
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# Palette
# --------------------------------------------------------------------------- #
# A warm, paper-like scheme: near-black ink on cream, one clay accent, and
# hairline rules instead of panels. The three scope colours are a validated
# categorical set — worst-pair CVD Delta E 17.7, normal-vision 24.1 on this
# surface — so the charts stay readable to colour-blind readers.
INK = "#141413"          # primary text
INK_SOFT = "#6b6a63"     # secondary text
PAPER = "#faf9f5"        # page ground
SURFACE = "#f2f0e9"      # recessed surface (drawer, code, notes)
SURFACE_HI = "#eae7dd"   # hover / selected surface
LINE = "rgba(20,20,19,0.12)"
CLAY = "#c1633f"         # the accent: links, focus, the brand mark
EMBER = "#a8402a"        # furnace / Scope 1
AMBER = "#d2a028"        # electricity / Scope 2
STEEL = "#1f6e9e"        # upstream / Scope 3
GREEN = "#3f7d58"        # savings
SLATE = "#3a3833"

#: The dark-mode steps of the same three hues, chosen for the dark surface
#: rather than flipped from the light ones.
EMBER_DARK = "#d1673c"
AMBER_DARK = "#b3862c"
STEEL_DARK = "#3f92c9"

#: Page tokens per mode. The dark set is selected, not inverted.
LIGHT_TOKENS = {
    "ink": INK, "ink_soft": INK_SOFT, "paper": PAPER,
    "surface": SURFACE, "surface_hi": SURFACE_HI,
    "line": LINE, "clay": CLAY,
    "ember": EMBER, "amber": AMBER, "steel": STEEL, "green": GREEN,
    "nav": "rgba(250,249,245,.86)",
    "scroll": "rgba(20,20,19,.18)",
}
DARK_TOKENS = {
    "ink": "#eceae4", "ink_soft": "#9a978c", "paper": "#1a1a19",
    "surface": "#232320", "surface_hi": "#2c2b28",
    "line": "rgba(236,234,228,0.14)", "clay": "#d1673c",
    "ember": EMBER_DARK, "amber": AMBER_DARK, "steel": STEEL_DARK, "green": "#5aa07a",
    "nav": "rgba(26,26,25,.88)",
    "scroll": "rgba(236,234,228,.20)",
}


def tokens(dark: bool = False) -> dict:
    """The page's colour tokens for the active mode."""
    return DARK_TOKENS if dark else LIGHT_TOKENS


def scope_colours(dark: bool = False) -> dict:
    palette = tokens(dark)
    return {"scope1": palette["ember"], "scope2": palette["amber"], "scope3": palette["steel"]}


SCOPE_COLOURS = {"scope1": EMBER, "scope2": AMBER, "scope3": STEEL}

#: Order the scopes are stacked in. Clay and gold are the one pair that cannot
#: be told apart reliably on a dark surface, so blue is stacked between them —
#: with this order both modes clear every gate the palette validator applies.
STACK_ORDER = ("scope1", "scope3", "scope2")
SCOPE_NAMES = {
    "scope1": "Scope 1 — direct",
    "scope2": "Scope 2 — purchased electricity",
    "scope3": "Scope 3 — upstream (Cat. 1-8)",
}

DEPARTMENT_ICONS = {
    "Inbound": "🚚",
    "Melt Shop": "🔥",
    "Hot Rolling": "🌡️",
    "Annealing": "♨️",
    "Descaling": "💨",
    "Pickling": "🧪",
    "Cold Rolling": "🧊",
    "Outbound": "📦",
}


# --------------------------------------------------------------------------- #
# Generated SVG art
# --------------------------------------------------------------------------- #
def spark_mark(size: int = 34, dark: bool = False) -> str:
    """The CarbonSpark mark: a spark struck off a steel arc."""
    mark_ink, mark_clay = tokens(dark)["ink"], tokens(dark)["clay"]
    return f"""
<svg viewBox="0 0 48 48" width="{size}" height="{size}" class="cs-mark" aria-hidden="true">
  <circle cx="24" cy="24" r="20" fill="none" stroke="{mark_ink}" stroke-width="1.5" opacity="0.35"/>
  <path d="M26 6 L14 26 h9 l-3 16 L36 21 h-10 Z" fill="{mark_clay}"/>
</svg>"""


# --------------------------------------------------------------------------- #
# Photography
# --------------------------------------------------------------------------- #
#: Photo slots used across the site. Each loads ``static/photos/<name>.jpg``
#: (served by Streamlit's static route) and sits on a gradient in the photo's
#: own colours, so a slot still reads as intended while a file is missing or
#: loading.
PHOTOS = {
    "hero": "radial-gradient(120% 90% at 70% 110%, #ff8a2a 0%, #b8410f 22%, #3a1a0e 52%, #0f0d0c 100%)",
    "melt": "radial-gradient(90% 80% at 40% 90%, #ffb347 0%, #d4561a 28%, #3b1a0c 60%, #121010 100%)",
    "scrap": "linear-gradient(135deg, #5b4636 0%, #8a6a4c 35%, #3f3a36 70%, #1f1d1b 100%)",
    "grid": "linear-gradient(160deg, #20364a 0%, #35607e 40%, #c9874a 85%, #e7b073 100%)",
    "mill": "linear-gradient(120deg, #1d2329 0%, #4a545d 45%, #a9b1b8 70%, #2a3036 100%)",
    "coil": "linear-gradient(140deg, #2b3440 0%, #6d7c8a 50%, #c7ced4 75%, #39424c 100%)",
}
_FALLBACK = "linear-gradient(135deg, #2a2f35 0%, #59636d 55%, #1d2126 100%)"

#: One photo per department, shown as the banner of its dropdown.
DEPARTMENT_PHOTOS = {
    "Inbound": "dept_inbound",
    "Melt Shop": "dept_melt",
    "Hot Rolling": "dept_hot",
    "Annealing": "dept_anneal",
    "Descaling": "dept_descale",
    "Pickling": "dept_pickle",
    "Cold Rolling": "dept_cold",
    "Outbound": "dept_outbound",
}

#: Where a slot's photo is served from, relative to the page.
PHOTO_URL = "./app/static/photos/{name}.jpg"


def photo_style(name: str, shade: float = 0.0) -> str:
    """Inline ``background`` for a photo slot, with an optional dark wash.

    ``shade`` lays a black gradient over the photo so type set on it stays
    legible whatever the picture turns out to be.
    """
    layers = []
    if shade:
        layers.append(
            f"linear-gradient(180deg, rgba(10,9,8,{shade * 0.55:.2f}) 0%, "
            f"rgba(10,9,8,{shade:.2f}) 100%)"
        )
    layers.append(f"url('{PHOTO_URL.format(name=name)}')")
    layers.append(PHOTOS.get(name, _FALLBACK))
    return f"background-image:{', '.join(layers)};background-size:cover;background-position:center;"
