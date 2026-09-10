import math

import pytest

from carbon_calc.formulas import FormulaError, compile_formula, evaluate
from carbon_calc.model import (
    INDIA_GRID_MIX,
    METRICS,
    MIX_VARIABLES,
    REFERENCE_GRID_FACTOR,
    SCOPES,
    build_variables,
    calculate,
    load_dataset,
    mix_factor,
)
from carbon_calc.optimize import Constraints, InfeasibleError, optimise, optimise_mix
from carbon_calc.route import build_stages, default_selection, selection_to_ids


@pytest.fixture(scope="module")
def dataset():
    return load_dataset()


def test_dataset_has_71_processes_and_seven_sources(dataset):
    assert len(dataset.processes) == 71
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


def test_route_selects_one_variation_per_stage(dataset):
    stages = build_stages(dataset)
    ids = selection_to_ids(stages, default_selection(stages))
    assert len(stages) == 48
    assert len(ids) == len(stages) == len(set(ids))


def test_route_total_is_below_summing_every_alternative(dataset):
    stages = build_stages(dataset)
    route = calculate(0.4, INDIA_GRID_MIX, dataset, selection_to_ids(stages, default_selection(stages)))
    everything = calculate(0.4, INDIA_GRID_MIX, dataset)
    assert route.total_co2e < everything.total_co2e


def test_disabled_stages_are_excluded(dataset):
    stages = build_stages(dataset)
    selection = default_selection(stages)
    enabled = {stage.key: stage.department != "Outbound" for stage in stages}
    full = calculate(0.4, INDIA_GRID_MIX, dataset, selection_to_ids(stages, selection))
    trimmed = calculate(
        0.4, INDIA_GRID_MIX, dataset, selection_to_ids(stages, selection, enabled)
    )
    assert "Outbound" not in trimmed.by_department
    assert trimmed.total_co2e < full.total_co2e


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
    baseline_selection = default_selection(stages)
    baseline = calculate(
        0.4, INDIA_GRID_MIX, dataset, selection_to_ids(stages, baseline_selection)
    )
    optimum = optimise(dataset, stages, Constraints(), baseline_selection)
    assert optimum.result.total_co2e < baseline.total_co2e
    assert sum(optimum.mix.values()) == pytest.approx(1.0)


def test_optimum_honours_locked_stages_and_scrap_bounds(dataset):
    stages = build_stages(dataset)
    baseline_selection = default_selection(stages)
    melting = "Melt Shop :: Primary Melting"
    constraints = Constraints(scrap_min=0.25, scrap_max=0.55, locked_stages=(melting,))
    optimum = optimise(dataset, stages, constraints, baseline_selection)
    assert 0.25 - 1e-9 <= optimum.scrap_ratio <= 0.55 + 1e-9
    assert optimum.selection[melting] == baseline_selection[melting]
    assert melting not in {change[0] for change in optimum.stage_changes}


def test_route_optimisation_can_be_switched_off(dataset):
    stages = build_stages(dataset)
    baseline_selection = default_selection(stages)
    optimum = optimise(dataset, stages, Constraints(), baseline_selection, optimise_route=False)
    assert optimum.selection == baseline_selection
    assert optimum.stage_changes == ()
