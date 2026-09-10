"""Page-level CSS. Kept in one place so the pages share a visual language.

The design is dark-first and *embedded*: sections are separated by hairlines,
spacing and type scale rather than by cards floating on the page. The one place
a raised surface survives is the input drawer, where the contrast is the signal
that a menu is open.
"""

from __future__ import annotations

from .theme import AMBER, EMBER, GREEN, INK, INK_SOFT, LINE, PAPER, STEEL, SURFACE, SURFACE_HI

BASE_CSS = f"""
<style>
:root {{
  --ink: {INK}; --ink-soft: {INK_SOFT}; --paper: {PAPER};
  --surface: {SURFACE}; --surface-hi: {SURFACE_HI}; --line: {LINE};
  --ember: {EMBER}; --amber: {AMBER}; --steel: {STEEL}; --green: {GREEN};
}}
html, body, [class*="css"] {{
  font-family: Inter, "Segoe UI", system-ui, sans-serif;
}}
.stApp {{ background: var(--paper); }}
#MainMenu, footer {{ visibility: hidden; }}
header[data-testid="stHeader"] {{ display: none; }}
html {{ scroll-behavior: smooth; }}

/* Wide by default — the old 1400px cap left deep gutters on a desktop screen. */
.block-container {{
  padding-top: .4rem; padding-bottom: 3rem;
  max-width: min(1920px, 95vw);
  padding-left: clamp(12px, 2.2vw, 40px);
  padding-right: clamp(12px, 2.2vw, 40px);
}}

/* ---------- motion ---------- */
@keyframes csRise {{ from {{ opacity:0; transform: translateY(18px); }} to {{ opacity:1; transform:none; }} }}
@keyframes csFade {{ from {{ opacity:0; }} to {{ opacity:1; }} }}
@keyframes csBob {{ 0%,100% {{ transform: translateY(0); }} 50% {{ transform: translateY(9px); }} }}
@keyframes csPulse {{ 0%,100% {{ opacity:.55; }} 50% {{ opacity:1; }} }}
@keyframes csPour {{ 0%,100% {{ stroke-dashoffset:0; }} 50% {{ stroke-dashoffset:14; }} }}
@keyframes csSpark {{ 0% {{ transform: translateY(0); opacity:1; }} 100% {{ transform: translateY(-34px); opacity:0; }} }}
@keyframes csSpin {{ from {{ transform: rotate(0); }} to {{ transform: rotate(360deg); }} }}
@keyframes csSweep {{ from {{ transform: translateX(-100%); }} to {{ transform: translateX(320%); }} }}
@keyframes csSlideIn {{ from {{ opacity:0; transform: translateX(-14px); }} to {{ opacity:1; transform:none; }} }}

.cs-rise {{ animation: csRise .55s cubic-bezier(.22,.61,.36,1) both; }}
.cs-rise-2 {{ animation: csRise .55s .12s cubic-bezier(.22,.61,.36,1) both; }}
.cs-rise-3 {{ animation: csRise .55s .24s cubic-bezier(.22,.61,.36,1) both; }}
.cs-pulse {{ animation: csPulse 3.4s ease-in-out infinite; }}
.cs-pour {{ stroke-dasharray: 8 6; animation: csPour 1.1s linear infinite; }}
.cs-spark {{ animation: csSpark 1.8s ease-out infinite; }}
.cs-s1 {{ animation-delay: .2s; }} .cs-s2 {{ animation-delay: .9s; }} .cs-s3 {{ animation-delay: 1.4s; }}
.cs-spin-a {{ transform-origin: 0 0; animation: csSpin 7s linear infinite; }}

/* ---------- sticky nav ---------- */
.cs-nav {{
  position: sticky; top: 0; z-index: 999;
  display: flex; align-items: center; gap: 26px;
  padding: 13px 18px; margin: 0 -1rem 6px -1rem;
  background: rgba(11,16,23,.82); backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--line);
}}
.cs-nav .cs-brand {{ display:flex; align-items:center; gap:10px; font-weight:800; letter-spacing:-.02em; font-size:1.06rem; color: var(--ink); }}
.cs-nav a {{ color: var(--ink-soft); text-decoration:none; font-weight:600; font-size:.92rem; transition: color .18s ease; }}
.cs-nav a:hover {{ color: var(--amber); }}
.cs-nav .cs-spacer {{ flex: 1; }}

/* ---------- hero ---------- */
.cs-hero {{ min-height: 72vh; display:flex; flex-direction:column; justify-content:center; padding: 24px 0 8px 0; }}
.cs-hero h1 {{
  font-size: clamp(3rem, 8vw, 5.8rem); font-weight: 850; letter-spacing:-.045em;
  line-height:.95; margin:.1em 0; color: var(--ink);
}}
.cs-hero h1 span {{
  background: linear-gradient(96deg, var(--ember), var(--amber));
  -webkit-background-clip: text; background-clip: text; color: transparent;
}}
.cs-hero p.cs-lede {{ font-size: 1.24rem; color: var(--ink-soft); max-width: 46ch; line-height:1.55; }}
.cs-hero-art {{ width:100%; border-radius: 18px; }}
.cs-scroll-hint {{
  display:flex; flex-direction:column; align-items:center; gap:6px;
  margin-top: 22px; color: var(--ink-soft); font-size:.82rem; letter-spacing:.16em; text-transform:uppercase;
}}
.cs-scroll-hint svg {{ animation: csBob 1.7s ease-in-out infinite; }}

/* ---------- sections: hairlines, not boxes ---------- */
.cs-section {{ padding: 64px 0 12px 0; scroll-margin-top: 76px; }}
.cs-rule {{ height:1px; background: linear-gradient(90deg, var(--line), transparent); margin: 8px 0 0 0; }}
.cs-eyebrow {{
  font-size:.74rem; font-weight:700; letter-spacing:.2em; text-transform:uppercase;
  color: var(--ember); margin-bottom:10px;
}}
.cs-section h2 {{ font-size: clamp(1.8rem,3.6vw,2.7rem); font-weight:800; letter-spacing:-.03em; margin:0 0 14px 0; color: var(--ink); }}
.cs-section p {{ color: var(--ink-soft); font-size:1.04rem; line-height:1.7; max-width: 74ch; }}

/* A "card" is now just a left accent rule and space — no floating panel. */
.cs-card {{
  border-left: 2px solid var(--line); padding: 4px 0 4px 18px; height:100%;
  transition: border-color .22s ease;
}}
.cs-card:hover {{ border-left-color: var(--ember); }}
.cs-card h3 {{ margin:.1rem 0 .45rem 0; font-size:1.04rem; font-weight:720; color: var(--ink); }}
.cs-card p {{ font-size:.94rem; margin:0; color: var(--ink-soft); line-height:1.62; }}
.cs-stat {{
  font-size:2.6rem; font-weight:840; letter-spacing:-.035em; line-height:1;
  background: linear-gradient(96deg, var(--ember), var(--amber));
  -webkit-background-clip:text; background-clip:text; color:transparent; margin-bottom:6px;
}}
.cs-shot {{ border-radius:16px; overflow:hidden; border:1px solid var(--line); }}

/* the department strip on the landing page */
.cs-strip {{ display:flex; flex-wrap:wrap; gap:10px; margin-top:10px; }}
.cs-step {{
  display:flex; align-items:center; gap:9px; padding:9px 15px; border-radius:999px;
  border:1px solid var(--line); color:var(--ink-soft); font-size:.88rem; font-weight:600;
  transition: border-color .2s ease, color .2s ease, transform .2s ease;
}}
.cs-step:hover {{ border-color: var(--amber); color: var(--ink); transform: translateY(-2px); }}
.cs-step b {{ color: var(--ink); font-weight:750; }}

/* ---------- tool ---------- */
.cs-toolbar {{
  display:flex; align-items:center; gap:14px; padding:8px 2px 12px 2px;
  border-bottom:1px solid var(--line); margin-bottom: 10px;
}}

/* The drawer is the one deliberately raised surface: opening it should feel
   like a menu came forward over the page. */
.st-key-cs_drawer {{
  background: linear-gradient(180deg, var(--surface-hi), var(--surface));
  border:1px solid rgba(255,255,255,.16) !important; border-radius:16px;
  padding:18px 18px 22px 18px;
  box-shadow: 0 24px 64px rgba(0,0,0,.6), 0 0 0 1px rgba(0,0,0,.45);
  animation: csSlideIn .28s cubic-bezier(.22,.61,.36,1) both;
}}
/* Nothing inside the drawer should draw its own second border. */
.st-key-cs_drawer div[data-testid="stVerticalBlockBorderWrapper"] {{ border:none !important; }}
.cs-drawer-title {{
  display:flex; align-items:center; gap:9px; font-weight:780; font-size:1.02rem;
  letter-spacing:-.01em; color:var(--ink); margin-bottom:2px;
}}
.cs-drawer-sub {{ color:var(--ink-soft); font-size:.85rem; margin:2px 0 14px 0; }}
.cs-panel-art {{ width:100%; border-radius:12px; display:block; }}

/* Graphs: full-width, one per screen, but without the dead air the old
   72vh centred stage produced between them. */
.cs-stage {{ padding: 2px 0 6px 0; }}
.cs-stage h3 {{ margin-bottom:2px; }}

.cs-chip {{
  display:inline-block; padding:3px 11px; border-radius:999px;
  font-size:.75rem; font-weight:650; background: rgba(47,127,181,.20); color: #7fc0ec;
}}
.cs-chip-warn {{ background: rgba(232,160,32,.20); color:#f0bd5e; }}
.cs-chip-good {{ background: rgba(31,138,95,.22); color:#5fd3a2; }}
.cs-band {{ width:100%; height:56px; border-radius:12px 12px 0 0; display:block; }}
.cs-band-title {{
  margin-top:-56px; height:56px; display:flex; align-items:center; gap:10px;
  padding:0 18px; color:#fff; font-weight:760; position:relative; letter-spacing:-.01em;
}}
div[data-testid="stMetricValue"] {{ font-size: clamp(1.05rem, 1.6vw, 1.8rem); }}
div[data-testid="stMetricLabel"] p {{ font-size: .82rem; color: var(--ink-soft); }}

/* ---------- Streamlit widget polish ---------- */
/* Sliders glide to a new value instead of snapping, which matters when
   normalising moves seven of them at once. */
div[data-testid="stSlider"] [role="slider"],
div[data-testid="stSlider"] [data-baseweb="slider"] > div > div {{
  transition: left .38s cubic-bezier(.22,.61,.36,1), transform .18s ease;
}}
div[data-testid="stSlider"] [data-testid="stSliderThumbValue"] {{ color: var(--amber); font-weight:700; }}

/* The view switcher, styled to read like the database page's tab strip. */
div[data-testid="stButtonGroup"] button {{
  border:none !important; background:transparent !important; border-radius:0 !important;
  color: var(--ink-soft) !important; font-weight:650 !important;
  padding: 8px 2px !important; margin-right: 26px !important;
  border-bottom: 2px solid transparent !important;
}}
div[data-testid="stButtonGroup"] button:hover {{ color: var(--ink) !important; }}
div[data-testid="stButtonGroup"] button[aria-checked="true"],
div[data-testid="stButtonGroup"] button[aria-pressed="true"],
div[data-testid="stButtonGroup"] button[kind="segmented_controlActive"] {{
  color: var(--ink) !important; border-bottom-color: var(--ember) !important;
  background: transparent !important;
}}
div[data-testid="stButtonGroup"] {{
  border-bottom: 1px solid var(--line); margin-bottom: 12px; gap: 0 !important;
}}

/* Tabs, so the database page and the tool agree. */
button[data-baseweb="tab"] {{ font-weight:650; }}
div[data-baseweb="tab-highlight"] {{ background-color: var(--ember) !important; }}

/* Expanders read as sections, not as boxes stacked on boxes. */
details[data-testid="stExpander"] {{
  border:none !important; border-top:1px solid var(--line) !important;
  border-radius:0 !important; background:transparent !important;
}}
details[data-testid="stExpander"] summary {{ padding-left:0 !important; }}

/* A long coefficient note is a scrollable block, not a page-wide text dump. */
.cs-note {{
  max-height: 320px; overflow-y: auto; padding: 14px 16px; border-radius: 12px;
  background: rgba(255,255,255,.03); border:1px solid var(--line);
  color: var(--ink-soft); font-size:.86rem; line-height:1.62;
  white-space: pre-wrap; overflow-wrap: anywhere;
}}

/* ---------- loading ---------- */
.cs-splash {{ min-height:70vh; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:18px; }}
.cs-splash h1 {{ font-size: clamp(2.2rem,5vw,3.4rem); font-weight:850; letter-spacing:-.04em; animation: csFade .8s ease both; color: var(--ink); }}
.cs-splash p {{ color: var(--ink-soft); animation: csFade .8s .3s ease both; }}
.cs-loadbar {{ width:min(420px,70vw); height:5px; border-radius:999px; background: rgba(255,255,255,.10); overflow:hidden; }}
.cs-loadbar i {{
  display:block; width:34%; height:100%; border-radius:999px;
  background: linear-gradient(90deg, var(--ember), var(--amber));
  animation: csSweep 1s ease-in-out infinite;
}}

@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ animation: none !important; transition: none !important; }}
}}
</style>
"""
