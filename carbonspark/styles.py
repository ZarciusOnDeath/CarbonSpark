"""Page-level CSS.

The scheme is warm paper and near-black ink with a single clay accent, and the
layout is *embedded*: hairlines, spacing and type scale carry the structure, so
almost nothing on the page is a box. The two exceptions earn it — the inputs
drawer, where a recessed surface is the signal that a menu is open, and a long
coefficient note, which needs a bounded scroll area.

Display type is a serif; the interface stays sans. That pairing is what keeps a
dense analytical page from reading like a spreadsheet.
"""

from __future__ import annotations

from .theme import AMBER, CLAY, EMBER, GREEN, INK, INK_SOFT, LINE, PAPER, STEEL, SURFACE, SURFACE_HI

BASE_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&display=swap');

:root {{
  --ink: {INK}; --ink-soft: {INK_SOFT}; --paper: {PAPER};
  --surface: {SURFACE}; --surface-hi: {SURFACE_HI}; --line: {LINE};
  --clay: {CLAY}; --ember: {EMBER}; --amber: {AMBER}; --steel: {STEEL}; --green: {GREEN};
  --serif: Newsreader, Georgia, "Times New Roman", serif;
  --sans: Inter, -apple-system, "Segoe UI", system-ui, sans-serif;
}}
html, body, [class*="css"] {{ font-family: var(--sans); color: var(--ink); }}
.stApp {{ background: var(--paper); }}
#MainMenu, footer {{ visibility: hidden; }}
header[data-testid="stHeader"] {{ display: none; }}
html {{ scroll-behavior: smooth; }}

.block-container {{
  padding-top: .4rem; padding-bottom: 4rem;
  max-width: min(1920px, 94vw);
  padding-left: clamp(14px, 2.4vw, 44px);
  padding-right: clamp(14px, 2.4vw, 44px);
}}

/* ---------- motion ---------- */
@keyframes csRise {{ from {{ opacity:0; transform: translateY(16px); }} to {{ opacity:1; transform:none; }} }}
@keyframes csFade {{ from {{ opacity:0; }} to {{ opacity:1; }} }}
@keyframes csBob {{ 0%,100% {{ transform: translateY(0); }} 50% {{ transform: translateY(8px); }} }}
@keyframes csPulse {{ 0%,100% {{ opacity:.5; }} 50% {{ opacity:.9; }} }}
@keyframes csPour {{ 0%,100% {{ stroke-dashoffset:0; }} 50% {{ stroke-dashoffset:14; }} }}
@keyframes csSpark {{ 0% {{ transform: translateY(0); opacity:1; }} 100% {{ transform: translateY(-34px); opacity:0; }} }}
@keyframes csSpin {{ from {{ transform: rotate(0); }} to {{ transform: rotate(360deg); }} }}
@keyframes csSweep {{ from {{ transform: translateX(-100%); }} to {{ transform: translateX(320%); }} }}
@keyframes csSlideIn {{ from {{ opacity:0; transform: translateX(-10px); }} to {{ opacity:1; transform:none; }} }}

.cs-rise {{ animation: csRise .5s cubic-bezier(.22,.61,.36,1) both; }}
.cs-rise-2 {{ animation: csRise .5s .1s cubic-bezier(.22,.61,.36,1) both; }}
.cs-rise-3 {{ animation: csRise .5s .2s cubic-bezier(.22,.61,.36,1) both; }}
.cs-pulse {{ animation: csPulse 3.4s ease-in-out infinite; }}
.cs-pour {{ stroke-dasharray: 8 6; animation: csPour 1.1s linear infinite; }}
.cs-spark {{ animation: csSpark 1.8s ease-out infinite; }}
.cs-s1 {{ animation-delay: .2s; }} .cs-s2 {{ animation-delay: .9s; }} .cs-s3 {{ animation-delay: 1.4s; }}
.cs-spin-a {{ transform-origin: 0 0; animation: csSpin 7s linear infinite; }}

/* ---------- nav ---------- */
.cs-nav {{
  position: sticky; top: 0; z-index: 999;
  display: flex; align-items: center; gap: 28px;
  padding: 14px 18px; margin: 0 -1rem 4px -1rem;
  background: rgba(250,249,245,.86); backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--line);
}}
.cs-nav .cs-brand {{ display:flex; align-items:center; gap:10px; font-weight:600; letter-spacing:-.01em; font-size:1.04rem; }}
.cs-nav a {{ color: var(--ink-soft); text-decoration:none; font-weight:500; font-size:.92rem; transition: color .18s ease; }}
.cs-nav a:hover {{ color: var(--clay); }}
.cs-nav .cs-spacer {{ flex: 1; }}

/* ---------- hero ---------- */
.cs-hero {{ min-height: 70vh; display:flex; flex-direction:column; justify-content:center; padding: 24px 0 8px 0; }}
.cs-hero h1 {{
  font-family: var(--serif); font-size: clamp(3.2rem, 8vw, 6rem); font-weight: 400;
  letter-spacing:-.03em; line-height:.98; margin:.06em 0; color: var(--ink);
}}
.cs-hero h1 em {{ font-style: italic; color: var(--clay); }}
.cs-hero p.cs-lede {{
  font-size: 1.2rem; color: var(--ink-soft); max-width: 46ch; line-height:1.6; margin-top:.6rem;
}}
.cs-hero-art {{ width:100%; border-radius: 4px; }}
.cs-scroll-hint {{
  display:flex; flex-direction:column; align-items:center; gap:6px;
  margin-top: 22px; color: var(--ink-soft); font-size:.78rem; letter-spacing:.16em; text-transform:uppercase;
}}
.cs-scroll-hint svg {{ animation: csBob 1.7s ease-in-out infinite; }}

/* ---------- sections ---------- */
.cs-section {{ padding: 76px 0 10px 0; scroll-margin-top: 78px; }}
.cs-rule {{ height:1px; background: var(--line); margin: 6px 0 0 0; }}
.cs-eyebrow {{
  font-size:.72rem; font-weight:600; letter-spacing:.18em; text-transform:uppercase;
  color: var(--clay); margin-bottom:12px;
}}
.cs-section h2 {{
  font-family: var(--serif); font-size: clamp(1.9rem,3.6vw,2.9rem); font-weight:400;
  letter-spacing:-.02em; margin:0 0 16px 0; color: var(--ink); line-height:1.12;
}}
.cs-section p {{ color: var(--ink-soft); font-size:1.05rem; line-height:1.72; max-width: 68ch; }}

/* A feature is a hairline and space. No panel, no border, no shadow. */
.cs-card {{ padding: 2px 0 18px 0; margin-bottom: 18px; border-top: 1px solid var(--line); }}
.cs-card-icon {{
  display:inline-block; font-size:.7rem; font-weight:600; letter-spacing:.14em;
  text-transform:uppercase; color: var(--accent, var(--clay)); margin: 14px 0 6px 0;
}}
.cs-card h3 {{ margin:0 0 .4rem 0; font-size:1.08rem; font-weight:600; color: var(--ink); }}
.cs-card p {{ font-size:.96rem; margin:0; color: var(--ink-soft); line-height:1.66; }}

.cs-figure {{ padding-top: 6px; }}
.cs-figure-label {{
  font-size:.72rem; letter-spacing:.16em; text-transform:uppercase;
  color:var(--ink-soft); font-weight:600; margin-bottom:16px;
}}
.cs-figure-note {{ font-size:.88rem; color:var(--ink-soft); margin:14px 0 0 0; line-height:1.6; }}

/* Statistics: the number is the element. */
.cs-stat-row {{ border-top:1px solid var(--line); padding-top:16px; }}
.cs-stat {{
  font-family: var(--serif); font-size:3.4rem; font-weight:400; letter-spacing:-.03em;
  line-height:1; color: var(--accent, var(--ink)); margin-bottom:8px;
}}
.cs-stat-label {{ font-size:.92rem; color:var(--ink-soft); margin:0; line-height:1.55; max-width:34ch; }}

/* the department strip */
.cs-strip {{ display:flex; flex-wrap:wrap; gap:0; margin-top:18px; border-top:1px solid var(--line); }}
.cs-step {{
  display:flex; align-items:center; gap:8px; padding:14px 22px 14px 0;
  margin-right:22px; color:var(--ink-soft); font-size:.92rem; font-weight:500;
  border-bottom:1px solid transparent; transition: color .2s ease, border-color .2s ease;
}}
.cs-step:hover {{ color: var(--ink); border-bottom-color: var(--clay); }}
.cs-step b {{ color: var(--ink); font-weight:600; }}

/* ---------- the tool's headline figures ---------- */
.cs-readout {{ display:flex; flex-wrap:wrap; gap:0 clamp(24px,3.2vw,60px); align-items:flex-end; }}
.cs-metric {{ padding: 4px 0 10px 0; }}
.cs-metric-label {{
  font-size:.7rem; letter-spacing:.14em; text-transform:uppercase;
  color:var(--ink-soft); font-weight:600; margin-bottom:6px;
}}
.cs-metric-value {{
  font-family: var(--serif); font-weight:400; letter-spacing:-.03em; line-height:1;
  font-size: clamp(1.8rem, 2.4vw, 2.6rem); color: var(--ink);
}}
.cs-metric-value .cs-unit {{ font-size:.4em; color:var(--ink-soft); margin-left:.3em; letter-spacing:0; }}
.cs-metric-lead .cs-metric-value {{ font-size: clamp(2.9rem, 4.6vw, 4.8rem); color: var(--clay); }}
.cs-metric-lead .cs-metric-label {{ color: var(--clay); }}
.cs-readout-note {{ color:var(--ink-soft); font-size:.85rem; margin:4px 0 0 0; }}

/* ---------- inputs drawer ---------- */
/* Sticky has to sit on the column itself: Streamlit's scroll container is the
   main block, and a sticky element inside the bordered wrapper would scroll
   away with it. `align-self:flex-start` stops the column stretching to the row
   height, which would otherwise leave nothing to stick to. */
div[data-testid="stColumn"]:has(.st-key-cs_drawer) {{
  position: sticky; top: 8px; align-self: flex-start;
  max-height: calc(100vh - 20px);
  overflow-y: auto; overscroll-behavior: contain;
  scrollbar-width: thin; scrollbar-color: rgba(20,20,19,.2) transparent;
}}
div[data-testid="stColumn"]:has(.st-key-cs_drawer)::-webkit-scrollbar {{ width: 8px; }}
div[data-testid="stColumn"]:has(.st-key-cs_drawer)::-webkit-scrollbar-thumb {{
  background: rgba(20,20,19,.18); border-radius: 999px;
}}
.st-key-cs_drawer {{
  background: var(--surface);
  border: none !important; border-right: 1px solid var(--line) !important;
  border-radius: 0; padding: 20px 22px 26px 20px;
  animation: csSlideIn .26s cubic-bezier(.22,.61,.36,1) both;
}}
.st-key-cs_drawer div[data-testid="stVerticalBlockBorderWrapper"] {{ border:none !important; }}
.cs-drawer-title {{
  font-family: var(--serif); font-size:1.35rem; font-weight:400; letter-spacing:-.02em;
  color:var(--ink); margin-bottom:2px;
}}
.cs-drawer-sub {{ color:var(--ink-soft); font-size:.86rem; margin:2px 0 16px 0; }}
.cs-panel-art {{ width:100%; border-radius:4px; display:block; }}

.cs-stage {{ padding: 4px 0 8px 0; }}
.cs-stage h3 {{ font-family: var(--serif); font-weight:400; letter-spacing:-.02em; margin-bottom:2px; }}

.cs-chip {{
  display:inline-block; padding:2px 0; margin-right:16px;
  font-size:.8rem; font-weight:600; color: var(--steel); background:none;
}}
.cs-chip-warn {{ color:#9a6f12; }}
.cs-chip-good {{ color: var(--green); }}
.cs-band {{ width:100%; height:44px; border-radius:0; display:block; }}
.cs-band-title {{
  margin-top:-44px; height:44px; display:flex; align-items:center; gap:9px;
  padding:0 14px; color:var(--ink); font-weight:600; position:relative; letter-spacing:-.01em;
}}

/* ---------- Streamlit widget polish ---------- */
h1, h2, h3, h4 {{ font-family: var(--serif); font-weight: 400; letter-spacing:-.02em; }}
/* Streamlit's per-heading anchor link is noise on a page with no deep links. */
.stMarkdown a[href^="#"] svg, [data-testid="stHeaderActionElements"] {{ display:none !important; }}
.stButton button {{
  border-radius: 6px; border:1px solid var(--line); font-weight:550;
  transition: border-color .18s ease, color .18s ease;
}}
.stButton button:hover {{ border-color: var(--clay); color: var(--clay); }}
div[data-testid="stSlider"] [data-testid="stSliderThumbValue"] {{ color: var(--clay); font-weight:600; }}
div[data-testid="stSlider"] [data-baseweb="slider"] > div > div {{
  transition: left .36s cubic-bezier(.22,.61,.36,1);
}}

/* The view switcher, as a tab strip. */
div[data-testid="stButtonGroup"] button {{
  border:none !important; background:transparent !important; border-radius:0 !important;
  color: var(--ink-soft) !important; font-weight:550 !important;
  padding: 9px 2px !important; margin-right: 30px !important;
  border-bottom: 1px solid transparent !important;
}}
div[data-testid="stButtonGroup"] button:hover {{ color: var(--ink) !important; }}
div[data-testid="stButtonGroup"] button[aria-checked="true"],
div[data-testid="stButtonGroup"] button[aria-pressed="true"] {{
  color: var(--ink) !important; border-bottom-color: var(--clay) !important;
  background: transparent !important;
}}
div[data-testid="stButtonGroup"] {{
  border-bottom: 1px solid var(--line); margin-bottom: 14px; gap: 0 !important;
}}
button[data-baseweb="tab"] {{ font-weight:550; }}
div[data-baseweb="tab-highlight"] {{ background-color: var(--clay) !important; }}

/* Expanders read as rows in a list, not stacked boxes. */
details[data-testid="stExpander"] {{
  border:none !important; border-bottom:1px solid var(--line) !important;
  border-radius:0 !important; background:transparent !important;
}}
details[data-testid="stExpander"] summary {{ padding-left:0 !important; font-weight:550; }}

.cs-note {{
  max-height: 320px; overflow-y: auto; padding: 16px 18px; border-radius: 6px;
  background: var(--surface); border:1px solid var(--line);
  color: var(--ink-soft); font-size:.86rem; line-height:1.64;
  white-space: pre-wrap; overflow-wrap: anywhere;
}}

/* ---------- loading ---------- */
.cs-splash {{ min-height:70vh; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:18px; }}
.cs-splash h1 {{
  font-family: var(--serif); font-size: clamp(2.4rem,5vw,3.6rem); font-weight:400;
  letter-spacing:-.03em; animation: csFade .8s ease both; color: var(--ink);
}}
.cs-splash p {{ color: var(--ink-soft); animation: csFade .8s .3s ease both; }}
.cs-loadbar {{ width:min(420px,70vw); height:3px; border-radius:999px; background: rgba(20,20,19,.10); overflow:hidden; }}
.cs-loadbar i {{
  display:block; width:34%; height:100%; border-radius:999px; background: var(--clay);
  animation: csSweep 1s ease-in-out infinite;
}}

@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ animation: none !important; transition: none !important; }}
}}
</style>
"""
