"""Route construction: which of the 71 process steps make up one production path.

Several stages in the grid list mutually exclusive *variations* of the same
step — inbound unloading by train / road / ocean, primary melting by EAF / IF /
BF-converter / VIM / VAR / ESR, and so on. Summing all 71 rows would
double-count those alternatives, so a route selects exactly one variation per
stage. Stages with a single "General (all types)" row have nothing to choose.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Sequence, Tuple

from .model import Dataset, Process


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


def default_selection(stages: Sequence[Stage]) -> Dict[str, int]:
    """Baseline route: the workbook's first-listed variation at every stage."""
    return {stage.key: stage.default_id for stage in stages}


def selection_to_ids(
    stages: Sequence[Stage],
    selection: Mapping[str, int],
    enabled: Mapping[str, bool] | None = None,
) -> List[int]:
    """Resolve a stage selection into the list of process ids to evaluate."""
    ids: List[int] = []
    for stage in stages:
        if enabled is not None and not enabled.get(stage.key, True):
            continue
        ids.append(int(selection.get(stage.key, stage.default_id)))
    return ids
