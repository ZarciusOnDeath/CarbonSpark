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
    DEFAULT_TRAIN_SHARE,
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
from .route import RouteMix, Stage, route_weights


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
    train_min: float = 0.0
    train_max: float = 1.0

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
    locked: Mapping[str, Mapping[int, float]],
    enabled: Mapping[str, bool] | None,
) -> Tuple[RouteMix, float]:
    """Pick the lowest-total-CO2e variation at every unlocked stage.

    Splitting a stage between technologies can only land between their two
    totals, so an unconstrained optimum always puts the whole stage on its
    single best option. Locked stages keep the user's own split.
    """
    route: RouteMix = {}
    total = 0.0
    for stage in stages:
        if enabled is not None and not enabled.get(stage.key, True):
            continue
        if stage.key in locked:
            stage_mix = {int(pid): float(share) for pid, share in locked[stage.key].items()}
            for process_id, share in stage_mix.items():
                values = stage.option_by_id(process_id).evaluate(variables)
                total += share * sum(values[scope] for scope in SCOPES)
            route[stage.key] = stage_mix
            continue
        best_id, best_value = None, float("inf")
        for option in stage.options:
            values = option.evaluate(variables)
            value = sum(values[scope] for scope in SCOPES)
            if value < best_value:
                best_id, best_value = option.id, value
        route[stage.key] = {int(best_id): 1.0}
        total += best_value
    return route, total


@dataclass(frozen=True)
class Optimum:
    """The best scenario found, plus the sweep used to find it."""

    scrap_ratio: float
    mix: Dict[str, float]
    train_share: float
    route: RouteMix
    result: Result
    grid_factor: float
    sweep: Tuple[Tuple[float, float], ...]
    stage_changes: Tuple[Tuple[str, str, str], ...]


def optimise(
    dataset: Dataset,
    stages: Sequence[Stage],
    constraints: Constraints,
    baseline_route: Mapping[str, Mapping[int, float]],
    enabled: Mapping[str, bool] | None = None,
    steps: int = 201,
    optimise_route: bool = True,
) -> Optimum:
    """Find the lowest-carbon scenario allowed by ``constraints``."""
    scrap_min = max(0.0, min(1.0, constraints.scrap_min))
    scrap_max = max(0.0, min(1.0, constraints.scrap_max))
    if scrap_max < scrap_min:
        raise InfeasibleError("The maximum scrap ratio is below the minimum scrap ratio.")
    train_min = max(0.0, min(1.0, constraints.train_min))
    train_max = max(0.0, min(1.0, constraints.train_max))
    if train_max < train_min:
        raise InfeasibleError("The maximum rail share is below the minimum rail share.")

    mix = optimise_mix(constraints, dataset)
    if optimise_route:
        locked = {
            key: baseline_route[key]
            for key in constraints.locked_stages
            if key in baseline_route
        }
    else:
        locked = dict(baseline_route)

    span = scrap_max - scrap_min
    grid = [scrap_min] if span <= 0 else [
        scrap_min + span * i / (steps - 1) for i in range(steps)
    ]
    # Only two rows depend on the rail/road split and both are linear in p, so
    # the best share is always one of the two bounds.
    train_options = sorted({train_min, train_max})

    sweep: List[Tuple[float, float]] = []
    best: Tuple[float, RouteMix, float, float] | None = None
    for scrap in grid:
        scrap_best: Tuple[float, RouteMix, float] | None = None
        for train_share in train_options:
            variables = build_variables(scrap, mix, train_share)
            route, total = _best_route(stages, variables, locked, enabled)
            if scrap_best is None or total < scrap_best[0] - 1e-15:
                scrap_best = (total, route, train_share)
        assert scrap_best is not None
        sweep.append((scrap, scrap_best[0]))
        if best is None or scrap_best[0] < best[0] - 1e-15:
            best = (scrap_best[0], scrap_best[1], scrap, scrap_best[2])

    assert best is not None
    _, route, scrap_ratio, train_share = best
    result = calculate(scrap_ratio, mix, dataset, route_weights(route), train_share)

    changes: List[Tuple[str, str, str]] = []
    by_key = {stage.key: stage for stage in stages}

    def describe(stage: Stage, stage_mix: Mapping[int, float]) -> str:
        parts = [
            f"{stage.option_by_id(int(pid)).variation} {share:.0%}"
            for pid, share in sorted(stage_mix.items(), key=lambda item: -item[1])
            if share > 0
        ]
        return " + ".join(parts) if parts else "excluded"

    for key, stage_mix in route.items():
        stage = by_key[key]
        before = describe(stage, baseline_route.get(key, {}))
        after = describe(stage, stage_mix)
        if before != after:
            changes.append((key, before, after))

    return Optimum(
        scrap_ratio=scrap_ratio,
        mix=mix,
        train_share=train_share,
        route=route,
        result=result,
        grid_factor=mix_factor(mix, dataset),
        sweep=tuple(sweep),
        stage_changes=tuple(changes),
    )
