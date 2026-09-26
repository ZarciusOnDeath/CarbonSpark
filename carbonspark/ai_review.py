"""An optional written review of the user's scenario, by Claude.

The optimiser page always shows the rule-based advisor (``carbon_calc.advice``),
which needs nothing but the model. When an Anthropic API key is configured —
``ANTHROPIC_API_KEY`` in the environment or in ``.streamlit/secrets.toml`` — the
page also offers a written review: Claude is given the same computed figures
(the scenario, the optimum, the lever-by-lever waterfall and the findings) and
asked to explain them in plain language. It is told to use only those numbers,
so the review cannot invent figures the model did not produce.
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
