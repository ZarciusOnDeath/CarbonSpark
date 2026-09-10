"""Page-level CSS. Kept in one place so the two pages share a visual language."""

from __future__ import annotations

from .theme import AMBER, EMBER, GREEN, INK, INK_SOFT, PAPER, SLATE, STEEL

BASE_CSS = f"""
<style>
:root {{
  --ink: {INK}; --ink-soft: {INK_SOFT}; --paper: {PAPER};
  --ember: {EMBER}; --amber: {AMBER}; --steel: {STEEL};
  --green: {GREEN}; --slate: {SLATE};
}}
html, body, [class*="css"] {{
  font-family: Inter, "Segoe UI", system-ui, sans-serif;
}}
#MainMenu, footer {{ visibility: hidden; }}
/* CarbonSpark supplies its own header, so Streamlit's chrome is removed rather
   than left to overlap the sticky nav. */
header[data-testid="stHeader"] {{ display: none; }}
html {{ scroll-behavior: smooth; }}
.block-container {{ padding-top: .6rem; max-width: 1400px; }}

/* ---------- motion ---------- */
@keyframes csRise {{ from {{ opacity:0; transform: translateY(18px); }} to {{ opacity:1; transform:none; }} }}
@keyframes csFade {{ from {{ opacity:0; }} to {{ opacity:1; }} }}
@keyframes csBob {{ 0%,100% {{ transform: translateY(0); }} 50% {{ transform: translateY(9px); }} }}
@keyframes csPulse {{ 0%,100% {{ opacity:.55; }} 50% {{ opacity:1; }} }}
@keyframes csPour {{ 0%,100% {{ stroke-dashoffset:0; }} 50% {{ stroke-dashoffset:14; }} }}
@keyframes csSpark {{ 0% {{ transform: translateY(0); opacity:1; }} 100% {{ transform: translateY(-34px); opacity:0; }} }}
@keyframes csSpin {{ from {{ transform: rotate(0); }} to {{ transform: rotate(360deg); }} }}
@keyframes csSweep {{ from {{ transform: translateX(-100%); }} to {{ transform: translateX(320%); }} }}

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
  padding: 12px 20px; margin: 0 -1rem;
  background: rgba(247,248,250,.88); backdrop-filter: blur(9px);
  border-bottom: 1px solid rgba(15,23,32,.09);
}}
.cs-nav .cs-brand {{ display:flex; align-items:center; gap:10px; font-weight:800; letter-spacing:-.02em; font-size:1.06rem; }}
.cs-nav a {{ color: var(--ink-soft); text-decoration:none; font-weight:600; font-size:.92rem; transition: color .18s ease; }}
.cs-nav a:hover {{ color: var(--ember); }}
.cs-nav .cs-spacer {{ flex: 1; }}

/* ---------- hero ---------- */
.cs-hero {{
  min-height: 78vh; display:flex; flex-direction:column; justify-content:center;
  padding: 30px 0 10px 0;
}}
.cs-hero h1 {{
  font-size: clamp(3rem, 8vw, 5.6rem); font-weight: 850; letter-spacing:-.045em;
  line-height:.95; margin:.1em 0; color: var(--ink);
}}
.cs-hero h1 span {{
  background: linear-gradient(96deg, var(--ember), var(--amber));
  -webkit-background-clip: text; background-clip: text; color: transparent;
}}
.cs-hero p.cs-lede {{ font-size: 1.22rem; color: var(--ink-soft); max-width: 44ch; line-height:1.55; }}
.cs-hero-art {{ width:100%; border-radius: 16px; box-shadow: 0 20px 48px rgba(15,23,32,.20); }}
.cs-scroll-hint {{
  display:flex; flex-direction:column; align-items:center; gap:6px;
  margin-top: 26px; color: var(--ink-soft); font-size:.85rem; letter-spacing:.14em; text-transform:uppercase;
}}
.cs-scroll-hint svg {{ animation: csBob 1.7s ease-in-out infinite; }}

/* ---------- sections ---------- */
.cs-section {{ padding: 58px 0 22px 0; scroll-margin-top: 72px; }}
.cs-eyebrow {{
  font-size:.76rem; font-weight:700; letter-spacing:.18em; text-transform:uppercase;
  color: var(--ember); margin-bottom:8px;
}}
.cs-section h2 {{ font-size: clamp(1.7rem,3.4vw,2.5rem); font-weight:800; letter-spacing:-.03em; margin:0 0 14px 0; }}
.cs-section p {{ color: var(--ink-soft); font-size:1.03rem; line-height:1.68; max-width: 72ch; }}
.cs-card {{
  background:#fff; border:1px solid rgba(15,23,32,.09); border-radius:14px;
  padding:20px 22px; height:100%;
  transition: transform .22s ease, box-shadow .22s ease;
}}
.cs-card:hover {{ transform: translateY(-3px); box-shadow: 0 14px 34px rgba(15,23,32,.10); }}
.cs-card h3 {{ margin:.1rem 0 .45rem 0; font-size:1.06rem; font-weight:750; }}
.cs-card p {{ font-size:.94rem; margin:0; }}
.cs-stat {{ font-size:2.1rem; font-weight:820; letter-spacing:-.03em; color: var(--ember); }}
.cs-shot {{
  border-radius:14px; border:1px solid rgba(15,23,32,.1); overflow:hidden;
  box-shadow: 0 18px 40px rgba(15,23,32,.14); background:#fff;
}}

/* ---------- tool ---------- */
.cs-toolbar {{
  position: sticky; top:0; z-index:998;
  display:flex; align-items:center; gap:14px; padding:10px 4px;
  background: rgba(247,248,250,.92); backdrop-filter: blur(8px);
  border-bottom:1px solid rgba(15,23,32,.08); margin-bottom: 8px;
}}
.cs-panel-art {{ width:100%; border-radius:10px; display:block; }}
.cs-drawer {{
  background:#fff; border:1px solid rgba(15,23,32,.09); border-radius:14px;
  padding:16px; animation: csRise .3s ease both;
}}
.cs-stage {{ min-height: 72vh; display:flex; flex-direction:column; justify-content:center; padding: 8px 0; }}
.cs-metric-row {{ display:flex; gap:14px; flex-wrap:wrap; }}
.cs-chip {{
  display:inline-block; padding:3px 11px; border-radius:999px;
  font-size:.75rem; font-weight:650; background: rgba(47,127,181,.13); color: var(--steel);
}}
.cs-chip-warn {{ background: rgba(232,160,32,.18); color:#8a5c04; }}
.cs-chip-good {{ background: rgba(31,138,95,.15); color: var(--green); }}
.cs-band {{ width:100%; height:52px; border-radius:10px 10px 0 0; display:block; }}
/* Metrics must stay readable when the drawer squeezes the main column. */
div[data-testid="stMetricValue"] {{ font-size: clamp(1.05rem, 1.6vw, 1.75rem); }}
div[data-testid="stMetricLabel"] p {{ font-size: .82rem; }}

.cs-band-title {{
  margin-top:-52px; height:52px; display:flex; align-items:center; gap:10px;
  padding:0 16px; color:#fff; font-weight:750; position:relative; letter-spacing:-.01em;
}}

/* ---------- loading ---------- */
.cs-splash {{ min-height:70vh; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:18px; }}
.cs-splash h1 {{ font-size: clamp(2.2rem,5vw,3.4rem); font-weight:850; letter-spacing:-.04em; animation: csFade .8s ease both; }}
.cs-splash p {{ color: var(--ink-soft); animation: csFade .8s .3s ease both; }}
.cs-loadbar {{ width:min(420px,70vw); height:5px; border-radius:999px; background: rgba(15,23,32,.10); overflow:hidden; }}
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
