"""Route construction: which process steps make up one production path, and in
what proportion.

Several stages in the grid list interchangeable *variations* of the same step —
melting by EAF / IF / BF-converter / VIM / VAR / ESR, decarburisation by
AOD / VOD / K-OBM-S / CLU, and so on. A plant may genuinely run more than one,
so a stage selects one or more variations and splits its tonne between them by
share. Shares within a stage always sum to 1, which keeps every result a true
per-tonne figure rather than a sum that grows with each extra selection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

from .model import Dataset, Process

#: A stage's selection: variation id -> share of that stage's tonne.
StageMix = Dict[int, float]
#: A whole route: stage key -> StageMix. An absent or empty entry means the
#: stage is excluded.
RouteMix = Dict[str, StageMix]


@dataclass(frozen=True)
class Stage:
    """A process stage and the interchangeable variations available for it."""

    key: str
    department: str
    process: str
    options: Tuple[Process, ...]

    @property
    def has_choice(self) -> bool:
        return len(self.options) > 1

    @property
    def default_id(self) -> int:
        """The workbook's first-listed variation, used as the baseline choice."""
        return self.options[0].id

    @property
    def option_ids(self) -> Tuple[int, ...]:
        return tuple(option.id for option in self.options)

    def option_by_id(self, process_id: int) -> Process:
        for option in self.options:
            if option.id == process_id:
                return option
        raise KeyError(process_id)


def build_stages(dataset: Dataset) -> Tuple[Stage, ...]:
    """Group the dataset's processes into ordered stages."""
    grouped: Dict[Tuple[str, str], List[Process]] = {}
    order: List[Tuple[str, str]] = []
    for proc in dataset.processes:
        key = (proc.department, proc.process)
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(proc)
    return tuple(
        Stage(
            key=f"{dept} :: {process}",
            department=dept,
            process=process,
            options=tuple(grouped[(dept, process)]),
        )
        for dept, process in order
    )


def even_mix(option_ids: Iterable[int]) -> StageMix:
    """Split a stage's tonne evenly across the given variations."""
    ids = list(option_ids)
    if not ids:
        return {}
    share = 1.0 / len(ids)
    return {int(pid): share for pid in ids}


def normalise_mix(mix: Mapping[int, float]) -> StageMix:
    """Rescale a stage's shares to sum to 1, dropping non-positive entries."""
    positive = {int(pid): float(share) for pid, share in mix.items() if share > 0}
    total = sum(positive.values())
    if total <= 0:
        return {}
    return {pid: share / total for pid, share in positive.items()}


def default_route(stages: Sequence[Stage]) -> RouteMix:
    """Baseline route: the workbook's first-listed variation at every stage."""
    return {stage.key: {stage.default_id: 1.0} for stage in stages}


def route_weights(route: Mapping[str, Mapping[int, float]]) -> Dict[int, float]:
    """Flatten a route into the process-id -> weight map the model evaluates.

    Each stage is normalised independently, so a stage's shares always sum to 1
    however the user left the sliders.
    """
    weights: Dict[int, float] = {}
    for stage_mix in route.values():
        for process_id, share in normalise_mix(stage_mix).items():
            weights[process_id] = weights.get(process_id, 0.0) + share
    return weights


def active_stages(route: Mapping[str, Mapping[int, float]]) -> int:
    """How many stages the route actually runs through."""
    return sum(1 for stage_mix in route.values() if normalise_mix(stage_mix))


#: Neutral inbound share: both transport legs at the workbook's per-tonne basis.
NEUTRAL_INBOUND_SHARE = 0.5


def transport_ids(dataset: Dataset) -> Tuple[Tuple[int, ...], Tuple[int, ...]]:
    """The inbound and outbound transport row ids.

    The workbook marks exactly two rows as transport-mode dependent: RMHS
    unloading (material arriving) and outbound despatch (product leaving).
    """
    inbound = tuple(
        proc.id for proc in dataset.processes if proc.transport and proc.department == "RMHS"
    )
    outbound = tuple(
        proc.id for proc in dataset.processes if proc.transport and proc.department != "RMHS"
    )
    return inbound, outbound


def rail_shares(
    dataset: Dataset, inbound_rail: float, outbound_rail: float
) -> Dict[int, float]:
    """Per-row rail share ``p`` for the two transport legs.

    The legs are independent: ore, ferroalloy and scrap may arrive by rail while
    finished coil leaves by road, so each row gets its own ``p``.
    """
    inbound, outbound = transport_ids(dataset)
    shares = {process_id: float(inbound_rail) for process_id in inbound}
    shares.update({process_id: float(outbound_rail) for process_id in outbound})
    return shares


def apply_haulage(
    weights: Mapping[int, float],
    dataset: Dataset,
    inbound_share: float = NEUTRAL_INBOUND_SHARE,
) -> Dict[int, float]:
    """Re-split the haulage between the inbound and outbound legs.

    Both transport rows are stated per tonne moved, so the workbook as published
    sits at an even split. Moving the slider shifts tonne-movement from one leg
    to the other while keeping the pair's total movement fixed: at ``0.5`` both
    rows keep weight 1, at ``0.75`` the inbound leg carries one and a half times
    the movement and the outbound leg half.
    """
    share = max(0.0, min(1.0, float(inbound_share)))
    inbound, outbound = transport_ids(dataset)
    scaled = dict(weights)
    for process_id in inbound:
        scaled[process_id] = weights.get(process_id, 0.0) * 2.0 * share
    for process_id in outbound:
        scaled[process_id] = weights.get(process_id, 0.0) * 2.0 * (1.0 - share)
    return scaled
