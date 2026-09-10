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
def hero_art() -> str:
    """The landing hero: a furnace pour against a rolling-mill horizon."""
    return f"""
<svg viewBox="0 0 720 420" class="cs-hero-art" role="img" aria-label="Stainless steel plant illustration">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#efece3"/><stop offset="100%" stop-color="#e2ded1"/>
    </linearGradient>
    <radialGradient id="glow" cx="50%" cy="50%">
      <stop offset="0%" stop-color="{AMBER}" stop-opacity="0.85"/>
      <stop offset="55%" stop-color="{EMBER}" stop-opacity="0.30"/>
      <stop offset="100%" stop-color="{EMBER}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="pour" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#f6dfa6"/><stop offset="60%" stop-color="{AMBER}"/>
      <stop offset="100%" stop-color="{EMBER}"/>
    </linearGradient>
  </defs>
  <rect width="720" height="420" fill="url(#sky)"/>
  <path d="M0 300 H720" stroke="{SLATE}" stroke-width="1.5" opacity="0.25" fill="none"/>
  <!-- mill housings -->
  <g fill="#ded8c7" stroke="#a89f8b" stroke-width="2">
    <rect x="70" y="196" width="86" height="104" rx="4"/>
    <rect x="565" y="214" width="78" height="86" rx="4"/>
  </g>
  <!-- coil -->
  <g transform="translate(604,257)">
    <circle r="27" fill="#ddd8c9" stroke="#b9b1a0" stroke-width="2"/>
    <circle r="17" fill="none" stroke="#a79f8e" stroke-width="2"/>
    <circle r="8" fill="{STEEL}" opacity="0.65"/>
  </g>
  <!-- ladle glow -->
  <circle cx="330" cy="250" r="150" fill="url(#glow)" class="cs-pulse"/>
  <!-- ladle -->
  <g transform="translate(268,120)">
    <path d="M4 0 h116 l-13 74 a52 52 0 0 1 -90 0 Z" fill="#c8c0ad" stroke="{SLATE}" stroke-width="2.5"/>
    <rect x="-12" y="-8" width="140" height="14" rx="6" fill="#b6ad99"/>
  </g>
  <!-- pour stream + sparks -->
  <path d="M330 190 q7 46 -3 84 q-8 30 3 26" stroke="url(#pour)" stroke-width="11"
        fill="none" stroke-linecap="round" class="cs-pour"/>
  <ellipse cx="330" cy="302" rx="52" ry="12" fill="url(#pour)" opacity="0.95"/>
  <g fill="{AMBER}">
    <circle cx="300" cy="286" r="2.6" class="cs-spark cs-s1"/>
    <circle cx="356" cy="278" r="2.2" class="cs-spark cs-s2"/>
    <circle cx="341" cy="296" r="1.8" class="cs-spark cs-s3"/>
    <circle cx="313" cy="270" r="2.0" class="cs-spark cs-s2"/>
  </g>
  <rect y="300" width="720" height="120" fill="#e0dbcb"/>
  <g stroke="{STEEL}" stroke-width="2" opacity="0.5" fill="none">
    <path d="M0 334 H720"/><path d="M0 352 H720"/>
  </g>
</svg>"""


def panel_art(kind: str) -> str:
    """Art for the three control panels in the tool's drawer."""
    if kind == "scrap":
        return f"""
<svg viewBox="0 0 240 120" class="cs-panel-art" aria-hidden="true">
  <rect width="240" height="120" rx="10" fill="#efece3"/>
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
  <rect width="240" height="120" rx="10" fill="#efece3"/>
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
  <rect width="240" height="120" rx="10" fill="#efece3"/>
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


def section_band(kind: str) -> str:
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
    return f"""
<svg viewBox="0 0 240 80" preserveAspectRatio="none" class="cs-band" aria-hidden="true">
  <rect width="240" height="80" fill="#efece3"/>
  <path d="{path}" fill="none" stroke="{colour}" stroke-width="4"
        stroke-linecap="round" opacity="0.75"/>
</svg>"""


def spark_mark(size: int = 34) -> str:
    """The CarbonSpark mark: a spark struck off a steel arc."""
    return f"""
<svg viewBox="0 0 48 48" width="{size}" height="{size}" class="cs-mark" aria-hidden="true">
  <circle cx="24" cy="24" r="20" fill="none" stroke="{INK}" stroke-width="1.5" opacity="0.35"/>
  <path d="M26 6 L14 26 h9 l-3 16 L36 21 h-10 Z" fill="{CLAY}"/>
</svg>"""
