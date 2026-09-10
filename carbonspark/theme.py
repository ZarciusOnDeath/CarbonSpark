"""Visual language for CarbonSpark: palette, page CSS and generated SVG art.

All artwork is hand-built inline SVG rather than fetched imagery — no network
requests, nothing to break on a deploy, no licensing question, and the motifs
share the app's palette exactly.
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# Palette
# --------------------------------------------------------------------------- #
# The palette is dark-first: CarbonSpark pins a dark Streamlit theme in
# .streamlit/config.toml, so INK is the colour text is drawn *in* and PAPER is
# the ground it sits on — not the other way round.
INK = "#e8edf3"          # primary text
INK_SOFT = "#93a1b1"     # secondary text
PAPER = "#0b1017"        # page ground
SURFACE = "#121a24"      # raised surface (drawer, panels)
SURFACE_HI = "#1b2634"   # hover / selected surface
LINE = "rgba(255,255,255,0.10)"
EMBER = "#d94f2b"        # furnace / Scope 1
AMBER = "#e8a020"        # electricity / Scope 2
STEEL = "#2f7fb5"        # upstream / Scope 3
GREEN = "#1f8a5f"        # savings
SLATE = "#243447"

SCOPE_COLOURS = {"scope1": EMBER, "scope2": AMBER, "scope3": STEEL}
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
      <stop offset="0%" stop-color="{SLATE}"/><stop offset="100%" stop-color="#0b1119"/>
    </linearGradient>
    <radialGradient id="glow" cx="50%" cy="50%">
      <stop offset="0%" stop-color="{AMBER}" stop-opacity="0.95"/>
      <stop offset="55%" stop-color="{EMBER}" stop-opacity="0.45"/>
      <stop offset="100%" stop-color="{EMBER}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="pour" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#fff2c4"/><stop offset="60%" stop-color="{AMBER}"/>
      <stop offset="100%" stop-color="{EMBER}"/>
    </linearGradient>
  </defs>
  <rect width="720" height="420" fill="url(#sky)"/>
  <path d="M0 300 H720" stroke="#54637a" stroke-width="1.5" opacity="0.35" fill="none"/>
  <!-- mill housings -->
  <g fill="#1b2735" stroke="#33455c" stroke-width="2">
    <rect x="70" y="196" width="86" height="104" rx="4"/>
    <rect x="565" y="214" width="78" height="86" rx="4"/>
  </g>
  <!-- coil -->
  <g transform="translate(604,257)">
    <circle r="27" fill="#22303f" stroke="#4d6480" stroke-width="2"/>
    <circle r="17" fill="none" stroke="#6d8095" stroke-width="2"/>
    <circle r="8" fill="{STEEL}" opacity="0.65"/>
  </g>
  <!-- ladle glow -->
  <circle cx="330" cy="250" r="150" fill="url(#glow)" class="cs-pulse"/>
  <!-- ladle -->
  <g transform="translate(268,120)">
    <path d="M4 0 h116 l-13 74 a52 52 0 0 1 -90 0 Z" fill="#2b3a4d" stroke="#54687f" stroke-width="3"/>
    <rect x="-12" y="-8" width="140" height="14" rx="6" fill="#3c4f66"/>
  </g>
  <!-- pour stream + sparks -->
  <path d="M330 190 q7 46 -3 84 q-8 30 3 26" stroke="url(#pour)" stroke-width="11"
        fill="none" stroke-linecap="round" class="cs-pour"/>
  <ellipse cx="330" cy="302" rx="52" ry="12" fill="url(#pour)" opacity="0.85"/>
  <g fill="{AMBER}">
    <circle cx="300" cy="286" r="2.6" class="cs-spark cs-s1"/>
    <circle cx="356" cy="278" r="2.2" class="cs-spark cs-s2"/>
    <circle cx="341" cy="296" r="1.8" class="cs-spark cs-s3"/>
    <circle cx="313" cy="270" r="2.0" class="cs-spark cs-s2"/>
  </g>
  <rect y="300" width="720" height="120" fill="#080d13"/>
  <g stroke="{STEEL}" stroke-width="2" opacity="0.5" fill="none">
    <path d="M0 334 H720"/><path d="M0 352 H720"/>
  </g>
</svg>"""


def panel_art(kind: str) -> str:
    """Art for the three control panels in the tool's drawer."""
    if kind == "scrap":
        return f"""
<svg viewBox="0 0 240 120" class="cs-panel-art" aria-hidden="true">
  <rect width="240" height="120" rx="10" fill="#111b26"/>
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
  <rect width="240" height="120" rx="10" fill="#111b26"/>
  <g transform="translate(62,60)" stroke="{GREEN}" stroke-width="5" stroke-linecap="round">
    <line x1="0" y1="0" x2="0" y2="-30" class="cs-spin-a"/>
    <line x1="0" y1="0" x2="26" y2="16" class="cs-spin-a"/>
    <line x1="0" y1="0" x2="-26" y2="16" class="cs-spin-a"/>
    <circle r="4" fill="{GREEN}" stroke="none"/>
  </g>
  <line x1="62" y1="60" x2="62" y2="102" stroke="#3d5064" stroke-width="4"/>
  <g transform="translate(150,44)">
    <circle r="15" fill="{AMBER}" opacity="0.9"/>
    <g stroke="{AMBER}" stroke-width="3" stroke-linecap="round" opacity="0.75">
      <line x1="0" y1="-24" x2="0" y2="-19"/><line x1="0" y1="19" x2="0" y2="24"/>
      <line x1="-24" y1="0" x2="-19" y2="0"/><line x1="19" y1="0" x2="24" y2="0"/>
    </g>
  </g>
  <g fill="#1b2735" stroke="#41556c" stroke-width="2">
    <rect x="176" y="70" width="42" height="30" rx="3"/>
  </g>
  <path d="M186 70 v-16 M198 70 v-22 M210 70 v-12" stroke="#5d7086" stroke-width="3"
        stroke-linecap="round" fill="none"/>
</svg>"""
    return f"""
<svg viewBox="0 0 240 120" class="cs-panel-art" aria-hidden="true">
  <rect width="240" height="120" rx="10" fill="#111b26"/>
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
  <rect width="240" height="80" fill="#0e1620"/>
  <path d="{path}" fill="none" stroke="{colour}" stroke-width="4"
        stroke-linecap="round" opacity="0.75"/>
</svg>"""


def spark_mark(size: int = 34) -> str:
    """The CarbonSpark mark: a spark struck off a steel arc."""
    return f"""
<svg viewBox="0 0 48 48" width="{size}" height="{size}" class="cs-mark" aria-hidden="true">
  <circle cx="24" cy="24" r="21" fill="none" stroke="{STEEL}" stroke-width="3" opacity="0.65"/>
  <path d="M26 6 L14 26 h9 l-3 16 L36 21 h-10 Z" fill="{AMBER}"/>
</svg>"""
