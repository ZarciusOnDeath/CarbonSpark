"""A written review of the user's scenario.

Two writers produce it from the same computed figures (the scenario, the
optimum, the lever-by-lever waterfall and the advisor's findings):

* ``write_review`` — built in, needs nothing. It composes the review from those
  figures: a verdict, what is already good, the biggest gaps and the physical
  reason for each, an ordered action plan with the running total, and the
  limits holding the optimum back. It is deterministic, so the same scenario
  always reads the same.
* ``review`` — Claude, used instead when an Anthropic API key is configured
  (``ANTHROPIC_API_KEY`` in the environment or ``.streamlit/secrets.toml``). It
  is told to use only the figures it is given.
"""

from __future__ import annotations

import json
import os
from typing import Mapping, Sequence

import streamlit as st

MODEL = "claude-opus-5"

SYSTEM = (
    "You review carbon-reduction choices for a stainless steel plant, using the output "
    "of a carbon calculator. You are given the user's current scenario, the calculator's "
    "optimum under a named ambition level, a lever-by-lever breakdown of the saving, and "
    "the calculator's own findings.\n\n"
    "Write a short review for a plant engineer: what they are doing well, the one or two "
    "choices costing the most carbon and why (the physical reason, e.g. virgin alloy units "
    "carry their smelting emissions; Indian grid power is coal-heavy), and what to do first. "
    "Use only the numbers provided; never invent figures. Quote savings in tCO2e per tonne. "
    "Say plainly when a limit (scrap supply, coal floor) rather than a choice is what holds "
    "the answer back. Plain prose with a few short bullet points, under 250 words."
)


def _api_key() -> str | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    try:
        return st.secrets.get("ANTHROPIC_API_KEY")  # type: ignore[no-any-return]
    except Exception:  # no secrets file
        return None


def available() -> bool:
    return bool(_api_key())


def review(payload: Mapping[str, object]) -> str:
    """Ask Claude for a written review of the computed figures."""
    import anthropic

    client = anthropic.Anthropic(api_key=_api_key())
    try:
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=4000,
            system=SYSTEM,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[{
                "role": "user",
                "content": "Calculator output (JSON):\n" + json.dumps(payload, indent=1),
            }],
        )
    except anthropic.AuthenticationError:
        return "The configured Anthropic API key was rejected."
    except anthropic.RateLimitError:
        return "The review service is busy; try again in a minute."
    except anthropic.APIStatusError as error:
        return f"The review could not be generated ({error.status_code})."
    except anthropic.APIConnectionError:
        return "Could not reach the review service."
    if response.stop_reason == "refusal":
        return "The review could not be generated for this scenario."
    return "".join(block.text for block in response.content if block.type == "text").strip()


def payload(current, optimum, steps: Sequence, findings: Sequence, level_name: str,
            current_total: float, grid_now: float) -> dict:
    """The figures the review is allowed to use."""
    return {
        "ambition_level": level_name,
        "current": {
            "total_tco2e_per_t": round(current_total, 3),
            "scrap_share": round(current.scrap, 3),
            "grid_kg_per_kwh": round(grid_now, 3),
            "rail_share_inbound": round(current.rail_in, 3),
            "rail_share_outbound": round(current.rail_out, 3),
        },
        "optimum": {
            "total_tco2e_per_t": round(optimum.result.total_co2e, 3),
            "scrap_share": round(optimum.scrap_ratio, 3),
            "grid_kg_per_kwh": round(optimum.grid_factor, 3),
            "rail_share_inbound": round(optimum.rail_in, 3),
            "rail_share_outbound": round(optimum.rail_out, 3),
            "technology_changes": [
                {"stage": key.replace(" :: ", " - "), "now": before, "optimum": after}
                for key, before, after in optimum.stage_changes
            ],
        },
        "saving_by_lever_tco2e_per_t": {step.lever: round(step.saving, 3) for step in steps},
        "findings": [
            {"lever": f.lever, "saving_alone": round(f.saving, 3), "headline": f.headline,
             "detail": f.detail}
            for f in findings
        ],
    }


# --------------------------------------------------------------------------- #
# Built-in writer — no API key needed
# --------------------------------------------------------------------------- #
#: Why each lever moves carbon, in one sentence, for the action plan.
_WHY = {
    "Scrap": "virgin ferrochrome, nickel and iron units carry their smelting emissions with "
             "them; scrap arrives without them",
    "Grid": "Indian grid power is coal-heavy, and electricity drives melting, rolling and "
            "every motor in the plant",
    "Rail vs road": "rail moves a tonne-kilometre for roughly a third of road's carbon",
    "Technology": "the alternative technology does the same job with less direct fuel or "
                  "less electricity",
}

_ACTION = {
    "Scrap": "Raise scrap in the charge to {target}",
    "Grid": "Contract cleaner electricity, down to about {target}",
    "Rail vs road": "Move more haulage to rail ({target})",
    "Technology": "Switch technology where it pays ({target})",
}


def write_review(data: Mapping[str, object]) -> str:
    """Compose the written review from the calculator's figures alone."""
    level = data["ambition_level"]
    now = data["current"]
    best = data["optimum"]
    total, target = now["total_tco2e_per_t"], best["total_tco2e_per_t"]
    gap = total - target
    findings = list(data["findings"])
    lines = []

    # Verdict
    if gap <= 0.0005:
        lines.append(
            f"**Verdict.** At {total:.3f} tCO\u2082e per tonne you are already at the best "
            f"*{level}* allows. The remaining carbon is set by the level's limits, not by your "
            "choices; see the last section for what relaxing them would be worth."
        )
    else:
        pct = gap / total if total else 0.0
        size = "a large" if pct >= 0.25 else "a meaningful" if pct >= 0.10 else "a small"
        lines.append(
            f"**Verdict.** Your scenario emits **{total:.3f} tCO\u2082e/t**. Within *{level}* "
            f"the best achievable is **{target:.3f}**, so there is {size} gap of **{gap:.3f} t/t "
            f"({pct:.0%})**, about {gap * 1000:,.0f} kt CO\u2082e a year for every million "
            "tonnes you make."
        )

    # Strengths
    good = [
        f for f in findings
        if f["saving_alone"] <= 0.0005 and f["lever"] in _WHY
        and "cleaner grid" not in f["headline"]  # reported under "revisit later"
    ]
    if good:
        lines.append("**What you are doing well.**")
        lines += [f"- {f['headline']}" for f in good]

    # Biggest gaps
    gaps = sorted(
        (f for f in findings if f["saving_alone"] > 0.0005 and f["lever"] in _WHY),
        key=lambda f: -f["saving_alone"],
    )
    if gaps:
        lines.append("**Where the carbon is going.**")
        for f in gaps[:2]:
            lines.append(
                f"- **{f['lever']}** \u2014 {f['headline']} On its own this is worth "
                f"**{f['saving_alone']:.3f} t/t**, because {_WHY[f['lever']]}."
            )

        # Action plan, biggest first, with the running total from the waterfall.
        by_lever = {
            "Scrap": f"{best['scrap_share']:.0%}",
            "Grid": f"{best['grid_kg_per_kwh']:.3f} kg/kWh",
            "Rail vs road": f"in {best['rail_share_inbound']:.0%} / out {best['rail_share_outbound']:.0%}",
            "Technology": ", ".join(
                f"{c['stage']}: {c['optimum'].replace(' 100%', '')}"
                for c in best["technology_changes"]
            ) or "no change",
        }
        lines.append("**Do this, in this order.**")
        running = total
        for index, f in enumerate(gaps, start=1):
            running -= f["saving_alone"]
            lines.append(
                f"{index}. {_ACTION[f['lever']].format(target=by_lever[f['lever']])} "
                f"\u2014 about {f['saving_alone']:.3f} t/t."
            )
        lines.append(
            "The savings overlap a little (a cleaner grid makes extra scrap worth slightly "
            f"less, and vice versa), so together they land on the optimum of {target:.3f} "
            "rather than on the simple sum."
        )

    # Technology that depends on the grid
    for f in findings:
        if f["lever"] == "Technology" and f["saving_alone"] <= 0.0005 and "cleaner grid" in f["headline"]:
            lines.append(f"**One to revisit later.** {f['headline']} {f['detail']}")

    # Limits
    limits = [f for f in findings if f["lever"] in ("Scrap limit", "Coal floor")]
    if limits:
        lines.append("**What holds the optimum back.**")
        lines += [f"- {f['headline']} {f['detail']}" for f in limits]

    return "\n\n".join(lines)
