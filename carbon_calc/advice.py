"""Explain an optimum, and critique a scenario against it.

Two things a reader needs beside the optimiser's answer:

* **Where the saving comes from.** ``waterfall`` walks from the current scenario
  to the optimum one lever at a time (scrap, then grid, then haulage, then
  technology) and records what each step saves. The steps telescope, so they add
  up exactly to the total saving; the order only decides how the small
  interaction between scrap and grid (Scope 2 is kWh x factor, and kWh moves
  with scrap) is attributed.
* **What is wrong with the current choices.** ``critique`` prices each lever on
  its own — what moving just that one lever to its best allowed value would
  save — and ranks the findings, so the biggest miss is read first. It also
  names the limits the optimum is pressed against, and what relaxing each one
  would be worth.

Everything here is computed from the same model; nothing is a canned message.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Mapping, Sequence, Tuple

from .model import MIX_VARIABLES, SCOPES, Dataset, Result, build_variables, calculate, mix_factor
from .optimize import Constraints, Optimum
from .route import RouteMix, Stage, apply_haulage, normalise_mix, rail_shares, route_weights, substitutes


@dataclass(frozen=True)
class Scenario:
    """The inputs that define one scenario."""

    scrap: float
    mix: Mapping[str, float]
    rail_in: float
    rail_out: float
    route: RouteMix
    inbound_share: float = 0.5


def evaluate(dataset: Dataset, scenario: Scenario) -> Result:
    weights = apply_haulage(route_weights(scenario.route), dataset, scenario.inbound_share)
    return calculate(
        scenario.scrap,
        scenario.mix,
        dataset,
        weights,
        scenario.rail_in,
        rail_shares(dataset, scenario.rail_in, scenario.rail_out),
    )


def _replace(scenario: Scenario, **changes) -> Scenario:
    values = dict(scenario.__dict__)
    values.update(changes)
    return Scenario(**values)


@dataclass(frozen=True)
class Step:
    lever: str
    before: str
    after: str
    saving: float


def waterfall(dataset: Dataset, current: Scenario, optimum: Optimum) -> Tuple[Step, ...]:
    """Current -> optimum, one lever at a time. The savings sum to the total."""
    target = Scenario(
        optimum.scrap_ratio,
        optimum.mix,
        optimum.rail_in,
        optimum.rail_out,
        optimum.route,
        current.inbound_share,
    )
    steps = (
        ("Scrap in the charge", {"scrap": target.scrap},
         f"{current.scrap:.0%}", f"{target.scrap:.0%}"),
        ("Grid electricity", {"mix": target.mix},
         f"{mix_factor(current.mix, dataset):.3f} kg/kWh",
         f"{mix_factor(target.mix, dataset):.3f} kg/kWh"),
        ("Rail vs road", {"rail_in": target.rail_in, "rail_out": target.rail_out},
         f"in {current.rail_in:.0%} / out {current.rail_out:.0%}",
         f"in {target.rail_in:.0%} / out {target.rail_out:.0%}"),
        ("Process technology", {"route": target.route},
         "as selected", f"{len(optimum.stage_changes)} stage(s) changed"),
    )
    result: List[Step] = []
    state = current
    previous = evaluate(dataset, state).total_co2e
    for lever, change, before, after in steps:
        state = _replace(state, **change)
        now = evaluate(dataset, state).total_co2e
        result.append(Step(lever, before, after, previous - now))
        previous = now
    return tuple(result)


@dataclass(frozen=True)
class Finding:
    """One observation about the current scenario."""

    lever: str
    saving: float  # tCO2e/t this lever alone would save; <= 0 means nothing to gain
    headline: str
    detail: str
    tone: str = "info"  # "high" | "medium" | "low" | "good" | "info"


def _tone(saving: float) -> str:
    if saving >= 0.2:
        return "high"
    if saving >= 0.05:
        return "medium"
    if saving > 0.005:
        return "low"
    return "good"


def _stage_value(stage: Stage, option_id: int, variables, weight: float) -> float:
    values = stage.option_by_id(option_id).evaluate(variables)
    return weight * sum(values[scope] for scope in SCOPES)


def critique(
    dataset: Dataset,
    stages: Sequence[Stage],
    current: Scenario,
    optimum: Optimum,
    constraints: Constraints,
    level_name: str,
    technology_step: float = 0.0,
) -> Tuple[Finding, ...]:
    """Rank what the current scenario leaves on the table, lever by lever."""
    base = evaluate(dataset, current).total_co2e
    findings: List[Finding] = []

    def alone(**change) -> float:
        return base - evaluate(dataset, _replace(current, **change)).total_co2e

    # --- scrap -------------------------------------------------------------
    per_point = base - evaluate(dataset, _replace(current, scrap=min(1.0, current.scrap + 0.01))).total_co2e
    gain = alone(scrap=optimum.scrap_ratio)
    if current.scrap > constraints.scrap_max + 1e-9:
        findings.append(Finding(
            "Scrap", 0.0,
            f"Scrap at {current.scrap:.0%} is beyond what {level_name} assumes ({constraints.scrap_max:.0%}).",
            "The optimum is held to the level's limit, so on this lever you are already ahead of it.",
            "good"))
    elif gain > 0.005:
        findings.append(Finding(
            "Scrap", gain,
            f"Scrap is {current.scrap:.0%}; {level_name} allows {optimum.scrap_ratio:.0%}.",
            f"Every extra percentage point of scrap cuts about {per_point * 1000:.0f} kg CO₂e "
            "per tonne, almost all of it Scope 3: virgin ferrochrome, nickel and iron units carry "
            "their smelting emissions with them, scrap does not.",
            _tone(gain)))
    else:
        findings.append(Finding("Scrap", 0.0, f"Scrap at {current.scrap:.0%} is already at the limit.",
                                "Nothing more to gain here within this ambition level.", "good"))

    # --- grid --------------------------------------------------------------
    now_ef, best_ef = mix_factor(current.mix, dataset), mix_factor(optimum.mix, dataset)
    gain = alone(mix=optimum.mix)
    if gain > 0.005:
        dirtiest = max(MIX_VARIABLES, key=lambda v: current.mix.get(v, 0.0) * dataset.factor(v))
        name = dataset.source_by_var[dirtiest].source
        share = current.mix.get(dirtiest, 0.0)
        findings.append(Finding(
            "Grid", gain,
            f"Your grid emits {now_ef:.3f} kg CO₂e/kWh; the best {level_name} mix emits {best_ef:.3f}.",
            f"{name} supplies {share:.0%} of your electricity and most of the Scope 2. The optimum "
            "buys the cheapest-carbon sources up to each one's cap, and only then the rest.",
            _tone(gain)))
    elif now_ef < best_ef - 1e-6:
        findings.append(Finding("Grid", 0.0,
            f"Your grid ({now_ef:.3f}) is cleaner than {level_name} allows ({best_ef:.3f}).",
            "The level's coal floor holds the optimum back; on this lever you are ahead of it.", "good"))
    else:
        findings.append(Finding("Grid", 0.0, "Your grid mix is already the best this level allows.", "", "good"))

    # --- rail --------------------------------------------------------------
    gain = alone(rail_in=optimum.rail_in, rail_out=optimum.rail_out)
    if gain > 0.0005:
        findings.append(Finding(
            "Rail vs road", gain,
            f"Rail is in {current.rail_in:.0%} / out {current.rail_out:.0%}; "
            f"the optimum runs in {optimum.rail_in:.0%} / out {optimum.rail_out:.0%}.",
            "Rail freight emits roughly a third of road per tonne-km, so each leg is best at the "
            "highest rail share the level allows. The effect is real but small next to scrap and grid.",
            _tone(gain)))
    else:
        findings.append(Finding("Rail vs road", 0.0, "Haulage is already at its best split.", "", "good"))

    # --- technology, stage by stage ---------------------------------------
    variables = build_variables(current.scrap, current.mix, current.rail_in)
    tech: List[Tuple[float, str, str, str]] = []
    for stage in stages:
        mix = normalise_mix(current.route.get(stage.key, {}))
        if not mix or stage.options[0].transport:
            continue
        options = [
            o for o in substitutes(stage, mix)
            if o.variation not in constraints.excluded_variations
        ]
        if not options:
            continue
        now = sum(share * _stage_value(stage, pid, variables, 1.0) for pid, share in mix.items())
        best = min(options, key=lambda o: _stage_value(stage, o.id, variables, 1.0))
        gap = now - _stage_value(stage, best.id, variables, 1.0)
        if gap > 0.005:
            current_names = " + ".join(stage.option_by_id(pid).variation for pid in mix)
            tech.append((gap, stage.process, current_names, best.variation))
    tech.sort(reverse=True)
    if tech:
        total_gap = sum(item[0] for item in tech)
        gap, process, before, after = tech[0]
        others = f" {len(tech) - 1} more stage(s) could also switch." if len(tech) > 1 else ""
        findings.append(Finding(
            "Technology", total_gap,
            f"{process}: {before} → {after} would save {gap:.3f} t/t.",
            "At your scrap ratio and grid, this is the lowest-carbon option for that stage. "
            "A stage split between options can only land between their totals, so the best "
            f"single option always wins.{others}",
            _tone(total_gap)))
    elif optimum.stage_changes and technology_step > 0.005:
        # Best at today's grid, not at the optimum's: which technology wins
        # depends on how clean the electricity is.
        key, before, after = optimum.stage_changes[0]
        findings.append(Finding(
            "Technology", 0.0,
            f"On your current grid your technology is already the best. On the optimum's "
            f"cleaner grid, {key.split(' :: ')[1]}: {before.replace(' 100%', '')} \u2192 "
            f"{after.replace(' 100%', '')} saves a further {technology_step:.3f} t/t.",
            "The alternative uses more electricity but burns less on site. On a coal-heavy grid "
            "the extra electricity costs more carbon than it saves; once the grid is clean, it "
            "wins. Fix the grid first, then revisit the technology.",
            "low"))
    else:
        findings.append(Finding("Technology", 0.0,
            "Every stage already runs its lowest-carbon allowed option.", "", "good"))

    # --- limits the optimum is pressed against ----------------------------
    if optimum.scrap_ratio >= constraints.scrap_max - 1e-9 and constraints.scrap_max < 1.0:
        at = Scenario(optimum.scrap_ratio, optimum.mix, optimum.rail_in, optimum.rail_out,
                      optimum.route, current.inbound_share)
        edge = evaluate(dataset, at).total_co2e - evaluate(
            dataset, _replace(at, scrap=min(1.0, at.scrap + 0.05))).total_co2e
        findings.append(Finding(
            "Scrap limit", 0.0,
            f"The optimum stops at the scrap limit ({constraints.scrap_max:.0%}).",
            f"That limit is binding: allowing 5 points more scrap would save a further "
            f"{edge:.3f} t/t. It is a supply and metallurgy limit, not a carbon one.",
            "info"))
    coal_floor = (constraints.mix_bounds or {}).get("a", (0.0, 1.0))[0]
    if coal_floor > 0 and optimum.mix.get("a", 0.0) <= coal_floor + 1e-9:
        findings.append(Finding(
            "Coal floor", 0.0,
            f"The optimum stops at the coal floor ({coal_floor:.0%}).",
            "The grid connection is coal-fired; captive renewables displace part of it, not all. "
            "Each point of coal swapped for wind would lower the grid factor by about "
            f"{(dataset.factor('a') - dataset.factor('e')) / 100:.4f} kg/kWh.",
            "info"))

    order = {"high": 0, "medium": 1, "low": 2, "info": 3, "good": 4}
    return tuple(sorted(findings, key=lambda f: (order[f.tone], -f.saving)))
