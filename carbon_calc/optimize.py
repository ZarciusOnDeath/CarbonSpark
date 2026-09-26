"""Lowest-carbon-path search over scrap ratio, grid mix, haulage and technology.

The search is exact, and the model's structure is what makes it so:

1. **Grid mix.** Every Scope 2 formula is ``kWh(route, y) * EF_mix / 1000`` with
   ``kWh >= 0`` and ``EF_mix`` a share-weighted average of the seven source
   factors. Lowering ``EF_mix`` lowers Scope 2 whatever else is chosen, so the
   best mix is the one with the lowest ``EF_mix`` — a small linear program
   (box bounds, share floors, shares summing to one) solved exactly by filling
   floors and remaining demand from the cheapest source with headroom.
2. **Technology.** With the mix fixed, the total is a sum over stages, and each
   stage's contribution depends only on the technology chosen for it. So each
   stage is minimised on its own; splitting a stage between two options can only
   land between their two totals, never below the better one.
3. **Scrap and rail.** For a fixed route, every formula is linear in the scrap
   share ``y`` and in each leg's rail share ``p`` (the transport rows are
   bilinear: linear in each with the others fixed). A function that is linear in
   each variable separately takes its minimum over a box at a corner of the box.
   Minimising over routes first and corners second gives the same answer as the
   other way round, so the optimum is at one of the corners
   ``y in {min, max}`` x ``p_in in {min, max}`` x ``p_out in {min, max}``.

The search therefore evaluates those eight corners, each with its per-stage best
technology, and keeps the lowest. Every corner is returned, so the page can show
the whole comparison: that table is the proof the answer is the minimum.
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
from .route import (
    NEUTRAL_INBOUND_SHARE,
    RouteMix,
    Stage,
    apply_haulage,
    normalise_mix,
    rail_shares,
    route_weights,
    substitutes,
    transport_ids,
)


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
    #: Variation names the search may not pick. A route the world barely runs is
    #: not an answer to "what should this plant do", however little carbon it
    #: would emit on paper.
    excluded_variations: Tuple[str, ...] = ()

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
    variables_for,
    locked: Mapping[str, Mapping[int, float]],
    enabled: Mapping[str, bool] | None,
    excluded: Tuple[str, ...] = (),
    stage_weight=None,
    current: Mapping[str, Mapping[int, float]] | None = None,
) -> Tuple[RouteMix, float]:
    """Pick the lowest-total-CO2e variation at every unlocked stage.

    ``variables_for(stage)`` gives the variable binding for a stage (the two
    transport legs each carry their own rail share). ``stage_weight(stage)`` is
    the stage's tonne weight (the haulage split re-weights the transport legs).
    Locked stages keep the user's own split.
    """
    route: RouteMix = {}
    total = 0.0
    for stage in stages:
        if enabled is not None and not enabled.get(stage.key, True):
            continue
        variables = variables_for(stage)
        weight = stage_weight(stage) if stage_weight else 1.0

        def value_of(option) -> float:
            values = option.evaluate(variables)
            return weight * sum(values[scope] for scope in SCOPES)

        # Only genuine alternatives are candidates; a stage running something
        # with no substitute keeps it (see route.SUBSTITUTE_GROUPS).
        allowed = substitutes(stage, (current or {}).get(stage.key, {stage.default_id: 1.0}))
        if stage.key in locked or not allowed:
            source = locked.get(stage.key) or (current or {}).get(stage.key) or {stage.default_id: 1.0}
            stage_mix = normalise_mix({int(pid): float(share) for pid, share in source.items()})
            for process_id, share in stage_mix.items():
                total += share * value_of(stage.option_by_id(process_id))
            route[stage.key] = stage_mix
            continue
        # A technology the constraints exclude is not an option, but a stage
        # whose every option is excluded keeps what it is running rather than
        # vanishing from the route.
        options = [
            option for option in allowed if option.variation not in excluded
        ] or list(allowed)
        best = min(options, key=value_of)
        route[stage.key] = {int(best.id): 1.0}
        total += value_of(best)
    return route, total


@dataclass(frozen=True)
class Corner:
    """One corner of the scrap x rail box, with its best route's total."""

    scrap_ratio: float
    rail_in: float
    rail_out: float
    total: float


@dataclass(frozen=True)
class Optimum:
    """The best scenario found under the constraints."""

    scrap_ratio: float
    mix: Dict[str, float]
    rail_in: float
    rail_out: float
    route: RouteMix
    result: Result
    grid_factor: float
    stage_changes: Tuple[Tuple[str, str, str], ...]
    corners: Tuple[Corner, ...] = ()

    @property
    def train_share(self) -> float:
        """Rail share of the inbound leg (kept for the single-share callers)."""
        return self.rail_in


def optimise(
    dataset: Dataset,
    stages: Sequence[Stage],
    constraints: Constraints,
    baseline_route: Mapping[str, Mapping[int, float]],
    enabled: Mapping[str, bool] | None = None,
    optimise_route: bool = True,
    inbound_share: float = NEUTRAL_INBOUND_SHARE,
    steps: int | None = None,
) -> Optimum:
    """Find the lowest-carbon scenario allowed by ``constraints``.

    ``enabled`` defaults to the stages the baseline route actually runs, so the
    answer describes the same plant as the one it is compared with. ``steps`` is
    accepted for compatibility and ignored: the search is exact, not a sweep.
    """
    if enabled is None:
        enabled = {
            key: bool(normalise_mix(mix)) for key, mix in baseline_route.items()
        }
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

    inbound_ids, outbound_ids = transport_ids(dataset)
    share = max(0.0, min(1.0, float(inbound_share)))

    def leg(stage: Stage) -> str | None:
        ids = set(stage.option_ids)
        if ids & set(inbound_ids):
            return "in"
        if ids & set(outbound_ids):
            return "out"
        return None

    def stage_weight(stage: Stage) -> float:
        side = leg(stage)
        if side == "in":
            return 2.0 * share
        if side == "out":
            return 2.0 * (1.0 - share)
        return 1.0

    corners: List[Corner] = []
    best: Tuple[float, RouteMix, float, float, float] | None = None
    for scrap in sorted({scrap_min, scrap_max}):
        for rail_in in sorted({train_min, train_max}):
            for rail_out in sorted({train_min, train_max}):
                bindings = {
                    None: build_variables(scrap, mix, rail_in),
                    "in": build_variables(scrap, mix, rail_in),
                    "out": build_variables(scrap, mix, rail_out),
                }
                route, total = _best_route(
                    stages,
                    lambda stage: bindings[leg(stage)],
                    locked,
                    enabled,
                    constraints.excluded_variations,
                    stage_weight,
                    baseline_route,
                )
                corners.append(Corner(scrap, rail_in, rail_out, total))
                if best is None or total < best[0] - 1e-15:
                    best = (total, route, scrap, rail_in, rail_out)

    assert best is not None
    _, route, scrap_ratio, rail_in, rail_out = best
    result = calculate(
        scrap_ratio,
        mix,
        dataset,
        apply_haulage(route_weights(route), dataset, share),
        rail_in,
        rail_shares(dataset, rail_in, rail_out),
    )

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
        rail_in=rail_in,
        rail_out=rail_out,
        route=route,
        result=result,
        grid_factor=mix_factor(mix, dataset),
        stage_changes=tuple(changes),
        corners=tuple(sorted(corners, key=lambda corner: corner.total)),
    )
