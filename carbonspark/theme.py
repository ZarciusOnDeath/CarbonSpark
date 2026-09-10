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
    "RMHS": "🚚",
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
def hero_art(dark: bool = False) -> str:
    """The hero figure: a tonne of steel, drawn as the carbon it carries.

    Three stacked bands in the scope colours, above the route the tonne takes.
    It is the same reading the tool gives — which is a truer thing to open with
    than an illustration of a furnace.
    """
    t = tokens(dark)
    ink, ink_soft, clay = t["ink"], t["ink_soft"], t["clay"]
    bands = (
        ("Scope 1 \u00b7 direct", t["ember"], 0.166, "1.020", 0),
        ("Scope 2 \u00b7 purchased electricity", t["amber"], 0.560, "3.451", 1),
        ("Scope 3 \u00b7 upstream", t["steel"], 0.274, "1.696", 2),
    )
    marks = "".join(
        f'<g transform="translate(0,{index * 74})">'
        f'<text x="0" y="0" fill="{ink_soft}" font-size="12" font-family="Inter,sans-serif" '
        f'letter-spacing="1.2">{name.upper()}</text>'
        f'<rect x="0" y="12" width="{int(520 * width)}" height="28" rx="4" fill="{colour}"/>'
        f'<text x="{int(520 * width) + 12}" y="32" fill="{ink}" font-size="15" '
        f'font-family="Inter,sans-serif" font-weight="600">{value}</text>'
        f"</g>"
        for name, colour, width, value, index in bands
    )
    stops = ["RMHS", "MELT", "HOT", "ANNEAL", "PICKLE", "COLD", "OUT"]
    step = 540 / (len(stops) - 1)
    route = "".join(
        f'<g transform="translate({index * step:.0f},0)">'
        f'<circle cx="0" cy="0" r="4" fill="{"none" if index else clay}" '
        f'stroke="{clay}" stroke-width="1.6"/>'
        f'<text x="0" y="22" fill="{ink_soft}" font-size="10" text-anchor="middle" '
        f'font-family="Inter,sans-serif" letter-spacing="1">{name}</text></g>'
        for index, name in enumerate(stops)
    )
    return f"""
<svg viewBox="0 0 620 360" class="cs-hero-art" role="img"
     aria-label="One tonne of stainless steel broken into Scope 1, 2 and 3 emissions">
  <g transform="translate(20,34)">{marks}</g>
  <g transform="translate(24,292)">
    <line x1="0" y1="0" x2="540" y2="0" stroke="{ink_soft}" stroke-width="1" opacity="0.3"/>
    {route}
  </g>
  <text x="24" y="348" fill="{ink_soft}" font-size="11" font-family="Inter,sans-serif">
    6.167 tCO2e per tonne \u00b7 default route, 40% scrap, today\u2019s Indian grid
  </text>
</svg>"""


def panel_art(kind: str, dark: bool = False) -> str:
    """Art for the three control panels in the tool's drawer."""
    ground = tokens(dark)["surface_hi"]
    if kind == "scrap":
        return f"""
<svg viewBox="0 0 240 120" class="cs-panel-art" aria-hidden="true">
  <rect width="240" height="120" rx="10" fill="{ground}"/>
  <g opacity="0.9">
    <path d="M28 92 l26-34 22 20 20-30 24 26 22-40 26 34 18-16" fill="none"
          stroke="{STEEL}" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/>
  </g>
  <g fill="{EMBER}" opacity="0.85">
    <rect x="30" y="30" width="16" height="16" rx="3" transform="rotate(18 38 38)"/>
    <rect x="58" y="22" width="12" height="12" rx="3" transform="rotate(-12 64 28)"/>
  </g>
  <g fill="{AMBER}" opacity="0.8">
    <rect x="176" y="26" width="18" height="18" rx="3" transform="rotate(24 185 35)"/>
  </g>
</svg>"""
    if kind == "grid":
        return f"""
<svg viewBox="0 0 240 120" class="cs-panel-art" aria-hidden="true">
  <rect width="240" height="120" rx="10" fill="{ground}"/>
  <g transform="translate(62,60)" stroke="{GREEN}" stroke-width="5" stroke-linecap="round">
    <line x1="0" y1="0" x2="0" y2="-30" class="cs-spin-a"/>
    <line x1="0" y1="0" x2="26" y2="16" class="cs-spin-a"/>
    <line x1="0" y1="0" x2="-26" y2="16" class="cs-spin-a"/>
    <circle r="4" fill="{GREEN}" stroke="none"/>
  </g>
  <line x1="62" y1="60" x2="62" y2="102" stroke="#b3ab99" stroke-width="4"/>
  <g transform="translate(150,44)">
    <circle r="15" fill="{AMBER}" opacity="0.9"/>
    <g stroke="{AMBER}" stroke-width="3" stroke-linecap="round" opacity="0.75">
      <line x1="0" y1="-24" x2="0" y2="-19"/><line x1="0" y1="19" x2="0" y2="24"/>
      <line x1="-24" y1="0" x2="-19" y2="0"/><line x1="19" y1="0" x2="24" y2="0"/>
    </g>
  </g>
  <g fill="#e2ded1" stroke="#b3ab99" stroke-width="2">
    <rect x="176" y="70" width="42" height="30" rx="3"/>
  </g>
  <path d="M186 70 v-16 M198 70 v-22 M210 70 v-12" stroke="#a79f8e" stroke-width="3"
        stroke-linecap="round" fill="none"/>
</svg>"""
    return f"""
<svg viewBox="0 0 240 120" class="cs-panel-art" aria-hidden="true">
  <rect width="240" height="120" rx="10" fill="{ground}"/>
  <g fill="none" stroke="{STEEL}" stroke-width="3">
    <rect x="24" y="42" width="38" height="38" rx="5"/>
    <rect x="96" y="30" width="38" height="38" rx="5"/>
    <rect x="96" y="64" width="38" height="38" rx="5" opacity="0.55"/>
    <rect x="172" y="42" width="42" height="38" rx="5"/>
  </g>
  <g stroke="{AMBER}" stroke-width="3" stroke-linecap="round">
    <path d="M62 61 h34"/><path d="M134 49 h38"/><path d="M134 83 h20 v-22 h18" opacity="0.6"/>
  </g>
  <circle cx="193" cy="61" r="7" fill="{EMBER}"/>
</svg>"""


def scope_bars() -> str:
    """A small three-scope bar motif, in the same colours the charts use."""
    rows = (
        ("Scope 1", EMBER, 0.30),
        ("Scope 2", AMBER, 0.62),
        ("Scope 3", STEEL, 0.46),
    )
    bars = "".join(
        f'<g transform="translate(0,{index * 46})">'
        f'<text x="0" y="14" fill="{INK_SOFT}" font-size="12" font-family="Inter,sans-serif">'
        f"{name}</text>"
        f'<rect x="0" y="22" width="340" height="12" rx="6" fill="rgba(20,20,19,.07)"/>'
        f'<rect x="0" y="22" width="{int(340 * width)}" height="12" rx="6" fill="{colour}"/>'
        "</g>"
        for index, (name, colour, width) in enumerate(rows)
    )
    return (
        '<svg viewBox="0 0 340 140" width="100%" role="img" '
        'aria-label="Scope 1, 2 and 3 shown as bars">'
        f"{bars}</svg>"
    )


def section_band(kind: str, dark: bool = False) -> str:
    """A slim decorative band used as a department/section header background."""
    motifs = {
        "RMHS": (STEEL, "M10 40 h60 l14-16 h40 M96 40 h120"),
        "Melt Shop": (EMBER, "M20 46 q26-30 52 0 q26-30 52 0 q26-30 52 0"),
        "Hot Rolling": (AMBER, "M14 40 h180"),
        "Annealing": (EMBER, "M24 48 q14-24 28 0 q14-24 28 0"),
        "Descaling": (STEEL, "M18 32 h50 M18 44 h80 M18 56 h36"),
        "Pickling": (GREEN, "M30 26 v28 a14 14 0 0 0 28 0 v-28"),
        "Cold Rolling": (STEEL, "M20 40 h170"),
        "Outbound": (AMBER, "M28 30 h44 v32 h-44 Z M72 46 h40"),
    }
    colour, path = motifs.get(kind, (STEEL, "M20 40 h160"))
    ground = tokens(dark)["surface_hi"]
    return f"""
<svg viewBox="0 0 240 80" preserveAspectRatio="none" class="cs-band" aria-hidden="true">
  <rect width="240" height="80" fill="{ground}"/>
  <path d="{path}" fill="none" stroke="{colour}" stroke-width="4"
        stroke-linecap="round" opacity="0.75"/>
</svg>"""


def spark_mark(size: int = 34, dark: bool = False) -> str:
    """The CarbonSpark mark: a spark struck off a steel arc."""
    mark_ink, mark_clay = tokens(dark)["ink"], tokens(dark)["clay"]
    return f"""
<svg viewBox="0 0 48 48" width="{size}" height="{size}" class="cs-mark" aria-hidden="true">
  <circle cx="24" cy="24" r="20" fill="none" stroke="{mark_ink}" stroke-width="1.5" opacity="0.35"/>
  <path d="M26 6 L14 26 h9 l-3 16 L36 21 h-10 Z" fill="{mark_clay}"/>
</svg>"""
