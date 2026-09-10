import math

import pytest

from carbon_calc.formulas import FormulaError, compile_formula, evaluate
from carbon_calc.model import (
    INDIA_GRID_MIX,
    METRICS,
    MIX_VARIABLES,
    DEFAULT_TRAIN_SHARE,
    REFERENCE_GRID_FACTOR,
    SCOPES,
    build_variables,
    calculate,
    load_dataset,
    mix_factor,
)
from carbon_calc.optimize import Constraints, InfeasibleError, optimise, optimise_mix
from carbon_calc.route import (
    active_stages,
    build_stages,
    default_route,
    even_mix,
    normalise_mix,
    route_weights,
)


@pytest.fixture(scope="module")
def dataset():
    return load_dataset()


def test_dataset_has_67_processes_and_seven_sources(dataset):
    assert len(dataset.processes) == 67
    assert {src.variable for src in dataset.grid_sources} == set(MIX_VARIABLES)


def test_every_process_has_all_eleven_formulas(dataset):
    for proc in dataset.processes:
        assert set(proc.formulas) == set(METRICS)


def test_formula_evaluator_rejects_non_arithmetic():
    with pytest.raises(FormulaError):
        compile_formula("__import__('os').system('ls')")
    with pytest.raises(FormulaError):
        compile_formula("x + z")


def test_formula_evaluator_matches_hand_calculation():
    tree = compile_formula("(x*2+y*4)*(a*0.95+e*0.011)/1000")
    value = evaluate(tree, build_variables(0.5, {"a": 0.5, "e": 0.5}))
    assert value == pytest.approx((0.5 * 2 + 0.5 * 4) * (0.5 * 0.95 + 0.5 * 0.011) / 1000)


def test_scrap_ratio_defines_virgin_ratio():
    variables = build_variables(0.35, INDIA_GRID_MIX)
    assert variables["x"] + variables["y"] == pytest.approx(1.0)


def test_train_share_defines_road_share():
    variables = build_variables(0.4, INDIA_GRID_MIX, train_share=0.7)
    assert variables["p"] == pytest.approx(0.7)
    assert variables["p"] + variables["q"] == pytest.approx(1.0)


def test_only_the_two_transport_rows_depend_on_the_rail_split(dataset):
    transport = [proc for proc in dataset.processes if proc.transport]
    assert len(transport) == 2
    assert {proc.department for proc in transport} == {"RMHS", "Outbound"}
    all_rail = calculate(0.4, INDIA_GRID_MIX, dataset, train_share=1.0)
    all_road = calculate(0.4, INDIA_GRID_MIX, dataset, train_share=0.0)
    # Rail is the lower-carbon mode in the workbook's coefficients.
    assert all_rail.total_co2e < all_road.total_co2e
    moved = {
        row["Process"]
        for rail, road in zip(all_rail.per_process, all_road.per_process)
        for row in [rail]
        if abs(rail["total_co2e"] - road["total_co2e"]) > 1e-12
    }
    assert moved == {"Unloading / Inbound", "Transport"}


def test_india_reference_mix_is_close_to_workbook_blended_factor():
    # The workbook notes this mix computes to ~0.70 kg CO2e/kWh, just under the
    # 0.77 CEA-midpoint used to back-derive the kWh intensities. The quoted shares
    # are rounded to whole percent, so the reproduced figure lands slightly above.
    assert sum(INDIA_GRID_MIX.values()) == pytest.approx(1.0)
    assert mix_factor(INDIA_GRID_MIX) == pytest.approx(0.70, abs=0.02)
    assert mix_factor(INDIA_GRID_MIX) < REFERENCE_GRID_FACTOR


def test_totals_equal_sum_of_process_rows(dataset):
    result = calculate(0.4, INDIA_GRID_MIX, dataset)
    for metric in METRICS:
        assert result.totals[metric] == pytest.approx(
            sum(row[metric] for row in result.per_process)
        )
    assert result.total_co2e == pytest.approx(sum(result.totals[s] for s in SCOPES))


def test_department_breakdown_reconciles_with_totals(dataset):
    result = calculate(0.6, INDIA_GRID_MIX, dataset)
    for metric in METRICS:
        assert sum(d[metric] for d in result.by_department.values()) == pytest.approx(
            result.totals[metric]
        )


def test_scope2_scales_linearly_with_the_grid_factor(dataset):
    coal = {"a": 1.0}
    solar = {"f": 1.0}
    hot = calculate(0.5, coal, dataset)
    clean = calculate(0.5, solar, dataset)
    ratio = dataset.factor("f") / dataset.factor("a")
    assert clean.totals["scope2"] == pytest.approx(hot.totals["scope2"] * ratio)
    # Scope 1, Scope 3 and energy are not grid-mix dependent.
    for metric in ("scope1", "scope3", "sec"):
        assert clean.totals[metric] == pytest.approx(hot.totals[metric])


def test_electricity_kwh_round_trips_through_scope2(dataset):
    result = calculate(0.5, INDIA_GRID_MIX, dataset)
    assert result.totals["scope2"] == pytest.approx(
        result.electricity_kwh * result.grid_factor / 1000
    )
    assert math.isnan(calculate(0.5, {}, dataset).electricity_kwh)


def test_default_route_runs_one_variation_per_stage(dataset):
    stages = build_stages(dataset)
    route = default_route(stages)
    weights = route_weights(route)
    assert len(stages) == 48
    assert active_stages(route) == 48
    assert len(weights) == 48
    assert all(share == pytest.approx(1.0) for share in weights.values())


def test_stage_shares_are_normalised_per_stage(dataset):
    stages = build_stages(dataset)
    melting = next(stage for stage in stages if stage.process == "Primary Melting")
    route = default_route(stages)
    # Deliberately un-normalised: 3 + 1 should become 75% / 25%.
    route[melting.key] = {melting.options[0].id: 3.0, melting.options[1].id: 1.0}
    weights = route_weights(route)
    assert weights[melting.options[0].id] == pytest.approx(0.75)
    assert weights[melting.options[1].id] == pytest.approx(0.25)


def test_even_mix_and_normalise_mix():
    assert even_mix([1, 2, 3])[1] == pytest.approx(1 / 3)
    assert even_mix([]) == {}
    assert normalise_mix({1: 2.0, 2: 2.0}) == {1: 0.5, 2: 0.5}
    assert normalise_mix({1: 0.0}) == {}


def test_splitting_a_stage_lands_between_its_options(dataset):
    stages = build_stages(dataset)
    melting = next(stage for stage in stages if stage.process == "Primary Melting")
    route = default_route(stages)
    first, second = melting.options[0].id, melting.options[1].id

    def total(stage_mix):
        route[melting.key] = stage_mix
        return calculate(0.4, INDIA_GRID_MIX, dataset, route_weights(route)).total_co2e

    only_first = total({first: 1.0})
    only_second = total({second: 1.0})
    split = total({first: 0.6, second: 0.4})
    assert min(only_first, only_second) < split < max(only_first, only_second)
    # A 60/40 split is exactly the weighted average, never a sum.
    assert split == pytest.approx(0.6 * only_first + 0.4 * only_second)
    assert split < only_first + only_second


def test_route_total_is_below_summing_every_alternative(dataset):
    stages = build_stages(dataset)
    route = calculate(0.4, INDIA_GRID_MIX, dataset, route_weights(default_route(stages)))
    everything = calculate(0.4, INDIA_GRID_MIX, dataset)
    assert route.total_co2e < everything.total_co2e


def test_excluded_stages_drop_out_of_the_route(dataset):
    stages = build_stages(dataset)
    route = default_route(stages)
    full = calculate(0.4, INDIA_GRID_MIX, dataset, route_weights(route))
    for stage in stages:
        if stage.department == "Outbound":
            route[stage.key] = {}
    trimmed = calculate(0.4, INDIA_GRID_MIX, dataset, route_weights(route))
    assert "Outbound" not in trimmed.by_department
    assert trimmed.total_co2e < full.total_co2e
    assert active_stages(route) == len(stages) - 4


def test_optimise_mix_is_all_wind_when_unconstrained(dataset):
    mix = optimise_mix(Constraints(), dataset)
    assert mix["e"] == pytest.approx(1.0)
    assert mix_factor(mix, dataset) == pytest.approx(dataset.factor("e"))


def test_optimise_mix_respects_bounds_and_floors(dataset):
    constraints = Constraints(
        mix_bounds={"a": (0.20, 0.40), "e": (0.0, 0.25)}, min_renewable=0.50
    )
    mix = optimise_mix(constraints, dataset)
    assert sum(mix.values()) == pytest.approx(1.0)
    assert 0.20 - 1e-9 <= mix["a"] <= 0.40 + 1e-9
    assert mix["e"] <= 0.25 + 1e-9
    assert sum(mix[v] for v in ("d", "e", "f")) >= 0.50 - 1e-9


def test_optimise_mix_beats_random_alternatives(dataset):
    import random

    constraints = Constraints(mix_bounds={"a": (0.10, 0.5), "g": (0.0, 0.10)}, min_renewable=0.30)
    best = mix_factor(optimise_mix(constraints, dataset), dataset)
    rng = random.Random(7)
    for _ in range(2000):
        raw = {v: rng.random() for v in MIX_VARIABLES}
        total = sum(raw.values())
        candidate = {v: raw[v] / total for v in MIX_VARIABLES}
        ok = (
            0.10 - 1e-9 <= candidate["a"] <= 0.5 + 1e-9
            and candidate["g"] <= 0.10 + 1e-9
            and sum(candidate[v] for v in ("d", "e", "f")) >= 0.30 - 1e-9
        )
        if ok:
            assert best <= mix_factor(candidate, dataset) + 1e-12


def test_infeasible_constraints_are_reported(dataset):
    with pytest.raises(InfeasibleError):
        optimise_mix(Constraints(mix_bounds={v: (0.0, 0.05) for v in MIX_VARIABLES}), dataset)
    with pytest.raises(InfeasibleError):
        optimise_mix(Constraints(mix_bounds={v: (0.2, 1.0) for v in MIX_VARIABLES}), dataset)
    with pytest.raises(InfeasibleError):
        optimise_mix(
            Constraints(mix_bounds={v: (0.0, 0.0) for v in ("d", "e", "f")}, min_renewable=0.2),
            dataset,
        )


def test_optimum_never_exceeds_the_baseline(dataset):
    stages = build_stages(dataset)
    baseline_route = default_route(stages)
    baseline = calculate(0.4, INDIA_GRID_MIX, dataset, route_weights(baseline_route))
    optimum = optimise(dataset, stages, Constraints(), baseline_route)
    assert optimum.result.total_co2e < baseline.total_co2e
    assert sum(optimum.mix.values()) == pytest.approx(1.0)
    # Every stage still routes a whole tonne.
    assert all(
        sum(stage_mix.values()) == pytest.approx(1.0) for stage_mix in optimum.route.values()
    )


def test_optimum_prefers_rail_and_respects_its_bounds(dataset):
    stages = build_stages(dataset)
    baseline_route = default_route(stages)
    assert optimise(dataset, stages, Constraints(), baseline_route).train_share == 1.0
    capped = optimise(
        dataset, stages, Constraints(train_max=0.25), baseline_route
    )
    assert capped.train_share == pytest.approx(0.25)


def test_optimum_honours_locked_stages_and_scrap_bounds(dataset):
    stages = build_stages(dataset)
    baseline_route = default_route(stages)
    melting = "Melt Shop :: Primary Melting"
    constraints = Constraints(scrap_min=0.25, scrap_max=0.55, locked_stages=(melting,))
    optimum = optimise(dataset, stages, constraints, baseline_route)
    assert 0.25 - 1e-9 <= optimum.scrap_ratio <= 0.55 + 1e-9
    assert optimum.route[melting] == baseline_route[melting]
    assert melting not in {change[0] for change in optimum.stage_changes}


def test_optimum_keeps_a_locked_stage_split(dataset):
    stages = build_stages(dataset)
    melting = next(stage for stage in stages if stage.process == "Primary Melting")
    baseline_route = default_route(stages)
    baseline_route[melting.key] = {melting.options[0].id: 0.6, melting.options[1].id: 0.4}
    optimum = optimise(
        dataset, stages, Constraints(locked_stages=(melting.key,)), baseline_route
    )
    assert optimum.route[melting.key] == baseline_route[melting.key]


def test_route_optimisation_can_be_switched_off(dataset):
    stages = build_stages(dataset)
    baseline_route = default_route(stages)
    optimum = optimise(dataset, stages, Constraints(), baseline_route, optimise_route=False)
    assert optimum.route == baseline_route
    assert optimum.stage_changes == ()
