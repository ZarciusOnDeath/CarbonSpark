"""Reading the workbook's coefficient notes.

Each row of the grid carries a note that mixes two different things: prose about
what the step is and where its numbers came from, and a dense run of
``NAME=value | NAME=value`` coefficient listings. Printed as-is it is a wall of
text — the prose disappears into the coefficients, and the coefficients cannot be
compared with one another.

This module splits the two apart so the page can show prose as prose and
coefficients as a table. The rule for telling them apart is deliberately strict:
a coefficient's value must be a *number*. Without that, a sentence like "using
p = train share, q = road share" parses as two coefficients and the prose is
shredded into table rows.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

#: A coefficient name never contains a space in this workbook (EF_S1_v, CO2_s,
#: SEC_virgin), which is what lets a name be told from the prose around it.
#: A bare "_s=10.38961" is the scrap half of the coefficient named just before
#: it, so a leading underscore has to be a valid name here.
_NAME = r"[A-Za-z_][A-Za-z0-9_()/.\-]*"
_NUMBER = r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"

#: NAME = number, with anything after the number kept as its unit or GWP note.
#: Anchored to a whole chunk, so the name may hold spaces and parentheses —
#: "EF_S2(kWh/t at 0.77kg/kWh ref)_v" is one coefficient. Dropping such a name
#: silently re-attaches the "_s=" that follows it to the coefficient *before*
#: it, which reports one row's number under another row's name.
_TOKEN = re.compile(
    rf"^\s*(?P<name>[A-Za-z_][A-Za-z0-9_()/.\- ]*)\s*=\s*"
    rf"(?P<value>{_NUMBER})\s*(?P<unit>.*?)\s*$"
)

#: The same pair, found anywhere in a line — used to locate where the leading
#: label ends and the coefficients begin.
_FIRST_TOKEN = re.compile(rf"{_NAME}\s*=\s*{_NUMBER}")

#: How the workbook suffixes the virgin and scrap variants of a number.
_VIRGIN = ("_virgin", "_v")
_SCRAP = ("_scrap", "_s")

#: Where a coefficient line opens with a label — "Train:", or the longer
#: "Underlying per-mode coefficients … — Train:" — that label groups the numbers
#: that follow. Getting this wrong is not cosmetic: without the group, the Train
#: and Road coefficients of a transport row merge into one another and the table
#: reports numbers that belong to the other mode.
_GROUP_TAIL = re.compile(r"(?:[—:-]\s*)?([A-Za-z][A-Za-z0-9()/ ]{0,24})\s*$")

Row = Dict[str, str]


def _strip_variant(name: str) -> Tuple[str, str | None]:
    """Split "EF_S1_virgin" into ("EF_S1", "virgin"), or report no variant."""
    for suffix in _VIRGIN:
        if name.endswith(suffix):
            return name[: -len(suffix)].rstrip("_"), "virgin"
    for suffix in _SCRAP:
        if name.endswith(suffix):
            return name[: -len(suffix)].rstrip("_"), "scrap"
    return name, None


def _tokens(line: str) -> List[Tuple[str, str, str]]:
    """Every NAME=number pair in a line, as (name, value, unit)."""
    found = []
    for chunk in re.split(r"[|,]", line):
        match = _TOKEN.match(chunk)
        if match:
            found.append(
                (match.group("name").strip(), match.group("value"), match.group("unit").strip())
            )
    return found


def _split_label(line: str) -> Tuple[str, str]:
    """Separate a coefficient line's leading label from its coefficients.

    The label is whatever precedes the first NAME=number pair; only its tail is
    kept, so "Underlying per-mode coefficients (tCO2e/t unless noted) — Train"
    becomes "Train".
    """
    match = _FIRST_TOKEN.search(line)
    if match is None:
        return "", line
    head = line[: match.start()].strip().rstrip(":—-").strip()
    if not head:
        return "", line
    tail = _GROUP_TAIL.search(head)
    label = (tail.group(1).strip() if tail else head)[:26]
    return label, line[match.start():]


def parse(note: str) -> Tuple[List[str], List[Row]]:
    """Split a note into prose paragraphs and coefficient rows.

    A line becomes coefficients only when it holds at least two NAME=number
    pairs; anything else is prose. Returns ``(paragraphs, rows)`` where each row
    has ``Coefficient``, ``Virgin``, ``Scrap`` and ``Unit``.
    """
    paragraphs: List[str] = []
    merged: Dict[str, Row] = {}
    order: List[str] = []

    for raw_line in (note or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        prefix, line = _split_label(line)
        found = _tokens(line)
        if len(found) < 2:
            paragraphs.append(raw_line.strip())
            continue

        previous_key = ""
        for name, value, unit in found:
            base, variant = _strip_variant(name)
            if not base:
                # "_s=10.38961" continues the coefficient before it.
                key = previous_key
                if not key:
                    continue
            else:
                key = f"{prefix} · {base}" if prefix else base
            previous_key = key
            row = merged.get(key)
            if row is None:
                row = {"Coefficient": key, "Virgin": "", "Scrap": "", "Unit": ""}
                merged[key] = row
                order.append(key)
            if variant == "virgin":
                row["Virgin"] = value
            elif variant == "scrap":
                row["Scrap"] = value
            else:
                row["Virgin"] = row["Scrap"] = value
            if unit and not row["Unit"]:
                row["Unit"] = unit

    rows = [merged[key] for key in order]
    if not rows:
        return [line.strip() for line in (note or "").splitlines() if line.strip()], []
    return paragraphs, rows
