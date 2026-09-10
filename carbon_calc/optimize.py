"""Lowest-carbon-path search over scrap ratio, grid mix and process variations.

The search is exact rather than heuristic, because the model's structure allows
it. Every formula is linear in ``x``/``y``, and each Scope 2 formula has the form
``kWh(x, y) * EF_mix(a..g) / 1000`` where ``EF_mix`` is a share-weighted average
of the seven source factors. Two consequences:

* the mix that minimises Scope 2 is the mix that minimises ``EF_mix``, whatever
  the scrap ratio or the route — so the mix is solved once, as a small linear
  program with box bounds plus share-group floors;
* stages are additive, so at any fixed scrap ratio the best route is simply the
  lowest-total variation at each stage, chosen independently.

That leaves a one-dimensional search over the scrap ratio, which is swept on a
fine grid (the route choice can switch between steps, so the objective is only
piecewise linear in ``y``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Sequence, Tuple

from .model import (
    FOSSIL_VARS,
    MIX_VARIABLES,
    RENEWABLE_VARS,
    SCOPES,
    Dataset,
    Result,
    build_variables,
    calculate,
    mix_factor,
)
from .route import Stage, selection_to_ids


class InfeasibleError(ValueError):
    """Raised when the supplied constraints admit no valid grid mix."""


@dataclass(frozen=True)
class Constraints:
    """User-set limits on what counts as a practical scenario."""

    scrap_min: float = 0.0
    scrap_max: float = 1.0
    mix_bounds: Dict[str, Tuple[float, float]] = None  # type: ignore[assignment]
    min_renewable: float = 0.0
    min_non_fossil: float = 0.0
    locked_stages: Tuple[str, ...] = ()

    def bounds_for(self, var: str) -> Tuple[float, float]:
        if not self.mix_bounds:
            return (0.0, 1.0)
        return self.mix_bounds.get(var, (0.0, 1.0))


def optimise_mix(constraints: Constraints, dataset: Dataset) -> Dict[str, float]:
    """Minimise the blended grid factor subject to bounds, floors and sum-to-one.

    Greedy allocation is optimal here: with a single linear objective, box
    bounds and nested share floors, filling each floor from its cheapest
    eligible member and then spending what remains on the cheapest source with
    headroom cannot be improved by any reallocation.
    """
    lower = {var: max(0.0, constraints.bounds_for(var)[0]) for var in MIX_VARIABLES}
    upper = {var: min(1.0, constraints.bounds_for(var)[1]) for var in MIX_VARIABLES}
    for var in MIX_VARIABLES:
        if upper[var] < lower[var]:
            raise InfeasibleError(
                f"{dataset.source_by_var[var].source}: maximum share is below its minimum share."
            )
    if sum(lower.values()) > 1.0 + 1e-9:
        raise InfeasibleError("The minimum source shares add up to more than 100%.")
    if sum(upper.values()) < 1.0 - 1e-9:
        raise InfeasibleError("The maximum source shares add up to less than 100%.")

    shares = dict(lower)

    def headroom(var: str) -> float:
        return max(0.0, upper[var] - shares[var])

    def allocate(candidates: Sequence[str], amount: float) -> float:
        """Spend ``amount`` on the cheapest candidates that still have headroom."""
        for var in sorted(candidates, key=lambda v: dataset.factor(v)):
            if amount <= 1e-12:
                break
            take = min(headroom(var), amount, 1.0 - sum(shares.values()))
            if take > 0:
                shares[var] += take
                amount -= take
        return amount

    # Nested share floors, most restrictive first.
    groups: List[Tuple[str, Tuple[str, ...], float]] = [
        ("renewable (hydro + wind + solar)", RENEWABLE_VARS, constraints.min_renewable),
        (
            "non-fossil (hydro + wind + solar + nuclear)",
            RENEWABLE_VARS + ("g",),
            constraints.min_non_fossil,
        ),
    ]
    for name, members, floor in groups:
        deficit = floor - sum(shares[var] for var in members)
        if deficit > 1e-12:
            remaining = allocate(members, deficit)
            if remaining > 1e-9:
                raise InfeasibleError(
                    f"Cannot reach the required {name} share of {floor:.0%} "
                    "within the per-source maximums."
                )

    remaining = 1.0 - sum(shares.values())
    if remaining > 1e-12:
        leftover = allocate(MIX_VARIABLES, remaining)
        if leftover > 1e-9:  # pragma: no cover - guarded by the sum(upper) check
            raise InfeasibleError("The per-source maximums cannot add up to 100%.")
    return {var: round(shares[var], 12) for var in MIX_VARIABLES}


def _best_route(
    stages: Sequence[Stage],
    variables: Mapping[str, float],
    locked: Mapping[str, int],
    enabled: Mapping[str, bool] | None,
) -> Tuple[Dict[str, int], float]:
    """Pick the lowest-total-CO2e variation at every stage (locked stages kept)."""
    selection: Dict[str, int] = {}
    total = 0.0
    for stage in stages:
        if enabled is not None and not enabled.get(stage.key, True):
            continue
        if stage.key in locked:
            chosen = stage.option_by_id(locked[stage.key])
            values = chosen.evaluate(variables)
            selection[stage.key] = chosen.id
            total += sum(values[scope] for scope in SCOPES)
            continue
        best_id, best_value = None, float("inf")
        for option in stage.options:
            values = option.evaluate(variables)
            value = sum(values[scope] for scope in SCOPES)
            if value < best_value:
                best_id, best_value = option.id, value
        selection[stage.key] = int(best_id)
        total += best_value
    return selection, total


@dataclass(frozen=True)
class Optimum:
    """The best scenario found, plus the sweep used to find it."""

    scrap_ratio: float
    mix: Dict[str, float]
    selection: Dict[str, int]
    result: Result
    grid_factor: float
    sweep: Tuple[Tuple[float, float], ...]
    stage_changes: Tuple[Tuple[str, str, str], ...]


def optimise(
    dataset: Dataset,
    stages: Sequence[Stage],
    constraints: Constraints,
    baseline_selection: Mapping[str, int],
    enabled: Mapping[str, bool] | None = None,
    steps: int = 201,
    optimise_route: bool = True,
) -> Optimum:
    """Find the lowest-carbon scenario allowed by ``constraints``."""
    scrap_min = max(0.0, min(1.0, constraints.scrap_min))
    scrap_max = max(0.0, min(1.0, constraints.scrap_max))
    if scrap_max < scrap_min:
        raise InfeasibleError("The maximum scrap ratio is below the minimum scrap ratio.")

    mix = optimise_mix(constraints, dataset)
    locked: Dict[str, int] = {}
    if optimise_route:
        locked = {key: int(baseline_selection[key]) for key in constraints.locked_stages if key in baseline_selection}
    else:
        locked = {stage.key: int(baseline_selection.get(stage.key, stage.default_id)) for stage in stages}

    span = scrap_max - scrap_min
    grid = [scrap_min] if span <= 0 else [
        scrap_min + span * i / (steps - 1) for i in range(steps)
    ]

    sweep: List[Tuple[float, float]] = []
    best: Tuple[float, Dict[str, int], float] | None = None
    for scrap in grid:
        variables = build_variables(scrap, mix)
        selection, total = _best_route(stages, variables, locked, enabled)
        sweep.append((scrap, total))
        if best is None or total < best[0] - 1e-15:
            best = (total, selection, scrap)

    assert best is not None
    _, selection, scrap_ratio = best
    result = calculate(scrap_ratio, mix, dataset, selection_to_ids(stages, selection, enabled))

    changes: List[Tuple[str, str, str]] = []
    by_key = {stage.key: stage for stage in stages}
    for key, chosen_id in selection.items():
        base_id = int(baseline_selection.get(key, by_key[key].default_id))
        if base_id != chosen_id:
            changes.append(
                (
                    key,
                    by_key[key].option_by_id(base_id).variation,
                    by_key[key].option_by_id(chosen_id).variation,
                )
            )

    return Optimum(
        scrap_ratio=scrap_ratio,
        mix=mix,
        selection=selection,
        result=result,
        grid_factor=mix_factor(mix, dataset),
        sweep=tuple(sweep),
        stage_changes=tuple(changes),
    )
