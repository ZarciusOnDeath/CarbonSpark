"""Carbon and energy model for the 71-step stainless steelmaking route.

The model is a thin, faithful evaluator of the workbook: every number the app
shows is produced by evaluating a formula that came out of
``Stainless_Steel_Carbon_Accounting_Grid (3).xlsx`` at the user's chosen input
mix (``x``/``y``) and grid energy mix (``a``-``g``). No coefficients are
re-derived or hard-coded here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Mapping, Sequence, Tuple

from .formulas import VARIABLES, compile_formula, evaluate

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "carbon_grid.json"

#: Metric keys in the order they appear in the workbook's columns M-W.
METRICS: Tuple[str, ...] = (
    "scope1",
    "scope2",
    "scope3",
    "co2",
    "ch4",
    "n2o",
    "hfc",
    "pfc",
    "sf6",
    "nf3",
    "sec",
)

SCOPES: Tuple[str, ...] = ("scope1", "scope2", "scope3")

#: Trace-gas columns. These are a gas-by-gas *disaggregation* published alongside
#: the scope columns, not a fourth scope, so they are reported separately and are
#: never added into the scope total.
TRACE_GASES: Tuple[str, ...] = ("co2", "ch4", "n2o", "hfc", "pfc", "sf6", "nf3")

METRIC_LABELS: Dict[str, str] = {
    "scope1": "Scope 1 (tCO2e/t)",
    "scope2": "Scope 2 (tCO2e/t)",
    "scope3": "Scope 3 upstream (tCO2e/t)",
    "co2": "CO2 (tCO2e/t)",
    "ch4": "CH4 (tCO2e/t)",
    "n2o": "N2O (tCO2e/t)",
    "hfc": "HFCs (tCO2e/t)",
    "pfc": "PFCs (tCO2e/t)",
    "sf6": "SF6 (tCO2e/t)",
    "nf3": "NF3 (tCO2e/t)",
    "sec": "Specific energy (GJ/t)",
}

#: Grid share variables in workbook order, with display names.
MIX_VARIABLES: Tuple[str, ...] = ("a", "b", "c", "d", "e", "f", "g")

RENEWABLE_VARS: Tuple[str, ...] = ("d", "e", "f")
FOSSIL_VARS: Tuple[str, ...] = ("a", "b", "c")

#: India's approximate current generation mix, quoted in the workbook's
#: "REFERENCE CONVERSION BASIS" note (~70% coal, 4% gas, 12% hydro, 4% wind,
#: 5% solar, 2% nuclear, 2% oil/other). The quoted shares are rounded and add to
#: 99%, so coal carries the remaining point to make the vector sum to exactly 1.
#: Used as the default / baseline mix.
INDIA_GRID_MIX: Dict[str, float] = {
    "a": 0.71,
    "b": 0.02,
    "c": 0.04,
    "d": 0.12,
    "e": 0.04,
    "f": 0.05,
    "g": 0.02,
}

#: Blended factor the workbook used to back-derive each row's kWh intensity.
REFERENCE_GRID_FACTOR = 0.77

#: Default split of material movement between rail and road (p, with q = 1 - p).
DEFAULT_TRAIN_SHARE = 0.5


@dataclass(frozen=True)
class Process:
    """One of the 71 process steps in the grid."""

    id: int
    department: str
    process: str
    variation: str
    notes: str
    transport: bool = False
    _compiled: Dict[str, object] = field(repr=False, compare=False, default_factory=dict)
    formulas: Dict[str, str] = field(default_factory=dict)

    @property
    def label(self) -> str:
        return f"{self.department} · {self.process} · {self.variation}"

    def evaluate(self, variables: Mapping[str, float]) -> Dict[str, float]:
        return {key: evaluate(tree, variables) for key, tree in self._compiled.items()}


@dataclass(frozen=True)
class GridSource:
    """One electricity source and its emission factor (kg CO2e/kWh)."""

    variable: str
    source: str
    ef: float
    basis: str


@dataclass(frozen=True)
class Dataset:
    processes: Tuple[Process, ...]
    grid_sources: Tuple[GridSource, ...]
    downstream: Tuple[Dict[str, str], ...]

    @property
    def departments(self) -> List[str]:
        seen: List[str] = []
        for proc in self.processes:
            if proc.department not in seen:
                seen.append(proc.department)
        return seen

    def factor(self, variable: str) -> float:
        return self.source_by_var[variable].ef

    @property
    def source_by_var(self) -> Dict[str, GridSource]:
        return {src.variable: src for src in self.grid_sources}


@lru_cache(maxsize=1)
def load_dataset(path: str | Path = DATA_PATH) -> Dataset:
    """Load and compile the extracted workbook data (cached)."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    processes = tuple(
        Process(
            id=item["id"],
            department=item["department"],
            process=item["process"],
            variation=item["variation"],
            notes=item.get("notes", ""),
            transport=bool(item.get("transport", False)),
            formulas={k: item["formulas"][k] for k in METRICS},
            _compiled={k: compile_formula(item["formulas"][k]) for k in METRICS},
        )
        for item in raw["processes"]
    )
    grid_sources = tuple(
        GridSource(variable=var, source=info["source"], ef=float(info["ef"]), basis=info["basis"])
        for var, info in raw["grid_factors"].items()
    )
    return Dataset(processes, grid_sources, tuple(raw.get("downstream", ())))


def build_variables(
    scrap_ratio: float,
    mix: Mapping[str, float],
    train_share: float = DEFAULT_TRAIN_SHARE,
) -> Dict[str, float]:
    """Assemble the eleven-variable binding the workbook formulas expect.

    ``train_share`` is ``p``; road is the remainder ``q = 1 - p``, the same
    convention the workbook uses for ``y = 1 - x``.
    """
    variables = {"y": float(scrap_ratio), "x": 1.0 - float(scrap_ratio)}
    variables.update({var: float(mix.get(var, 0.0)) for var in MIX_VARIABLES})
    variables["p"] = float(train_share)
    variables["q"] = 1.0 - float(train_share)
    missing = set(VARIABLES) - set(variables)
    if missing:
        raise ValueError(f"missing model variables: {sorted(missing)}")
    return variables


def mix_factor(mix: Mapping[str, float], dataset: Dataset | None = None) -> float:
    """Blended grid emission factor in kg CO2e/kWh for a given share vector."""
    dataset = dataset or load_dataset()
    return sum(dataset.factor(var) * float(mix.get(var, 0.0)) for var in MIX_VARIABLES)


@dataclass(frozen=True)
class Result:
    """Model output for one (scrap ratio, grid mix) scenario."""

    scrap_ratio: float
    mix: Dict[str, float]
    train_share: float
    per_process: Tuple[Dict[str, float], ...]
    totals: Dict[str, float]
    by_department: Dict[str, Dict[str, float]]
    grid_factor: float

    @property
    def total_co2e(self) -> float:
        """Total emissions per tonne = Scope 1 + Scope 2 + Scope 3 (upstream)."""
        return sum(self.totals[scope] for scope in SCOPES)

    @property
    def energy_gj(self) -> float:
        return self.totals["sec"]

    @property
    def electricity_kwh(self) -> float:
        """Purchased electricity per tonne, back-derived from Scope 2 and the mix factor.

        Every Scope 2 formula is ``kWh * grid_factor / 1000``, so dividing the
        Scope 2 total by the blended factor recovers the kWh. Undefined for a
        zero-emission mix, where it is reported as ``nan``.
        """
        if self.grid_factor <= 0:
            return float("nan")
        return self.totals["scope2"] * 1000.0 / self.grid_factor


def calculate(
    scrap_ratio: float,
    mix: Mapping[str, float],
    dataset: Dataset | None = None,
    weights: Mapping[int, float] | None = None,
    train_share: float = DEFAULT_TRAIN_SHARE,
    train_shares: Mapping[int, float] | None = None,
) -> Result:
    """Evaluate the selected process steps and aggregate the results.

    ``weights`` maps a process id to the share of the tonne routed through it.
    A stage where two technologies are both selected splits its tonne between
    them (0.6 EAF + 0.4 IF), so the result stays a true per-tonne figure instead
    of double-counting the stage. ``None`` runs every row at full weight.

    ``train_shares`` overrides ``p`` for individual rows. The inbound and
    outbound legs are independent choices — a plant can rail its ore in and
    truck its coil out — so each transport row can carry its own rail share.
    Rows without an override use ``train_share``.
    """
    dataset = dataset or load_dataset()
    variables = build_variables(scrap_ratio, mix, train_share)
    overrides = {int(pid): float(share) for pid, share in (train_shares or {}).items()}
    # One binding per distinct rail share, rather than one per row.
    by_share: Dict[float, Dict[str, float]] = {}
    for share in set(overrides.values()):
        by_share[share] = build_variables(scrap_ratio, mix, share)
    if weights is None:
        weights = {proc.id: 1.0 for proc in dataset.processes}

    per_process: List[Dict[str, float]] = []
    totals = {metric: 0.0 for metric in METRICS}
    by_department: Dict[str, Dict[str, float]] = {}

    for proc in dataset.processes:
        weight = float(weights.get(proc.id, 0.0))
        if weight <= 0:
            continue
        binding = by_share.get(overrides.get(proc.id), variables)
        values = {key: value * weight for key, value in proc.evaluate(binding).items()}
        row = {
            "id": proc.id,
            "Department": proc.department,
            "Process": proc.process,
            "Variation": proc.variation,
            "Share": weight,
            **values,
        }
        row["total_co2e"] = sum(values[scope] for scope in SCOPES)
        per_process.append(row)
        dept = by_department.setdefault(
            proc.department, {metric: 0.0 for metric in METRICS} | {"total_co2e": 0.0}
        )
        for metric in METRICS:
            totals[metric] += values[metric]
            dept[metric] += values[metric]
        dept["total_co2e"] += row["total_co2e"]

    return Result(
        scrap_ratio=float(scrap_ratio),
        mix={var: float(mix.get(var, 0.0)) for var in MIX_VARIABLES},
        train_share=float(train_share),
        per_process=tuple(per_process),
        totals=totals,
        by_department=by_department,
        grid_factor=mix_factor(mix, dataset),
    )
