"""Grid-mix presets and plant profiles.

The two JSL profiles are built from published information about each site. Their
**process routes are sourced** (see ``sources`` on each profile); their
**energy-mix percentages are estimates**, because neither plant publishes a
source-wise breakdown of the electricity it consumes. The UI labels that split
wherever a profile is shown — a demo should never imply verified plant data it
does not have.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Sequence, Tuple

from carbon_calc.model import INDIA_GRID_MIX, MIX_VARIABLES
from carbon_calc.route import RouteMix, Stage, default_route

# --------------------------------------------------------------------------- #
# Grid energy mixes
# --------------------------------------------------------------------------- #
GRID_PRESETS: Dict[str, Dict[str, float]] = {
    "India grid today": dict(INDIA_GRID_MIX),
    "50% renewable": {"a": 0.35, "b": 0.01, "c": 0.09, "d": 0.15, "e": 0.20, "f": 0.15, "g": 0.05},
    "Near-zero carbon": {"a": 0.0, "b": 0.0, "c": 0.0, "d": 0.25, "e": 0.40, "f": 0.25, "g": 0.10},
    "JSL Jajpur (estimated)": {
        "a": 0.78, "b": 0.01, "c": 0.02, "d": 0.06, "e": 0.03, "f": 0.08, "g": 0.02,
    },
    "JSL Hisar (estimated)": {
        "a": 0.82, "b": 0.01, "c": 0.03, "d": 0.05, "e": 0.02, "f": 0.05, "g": 0.02,
    },
}

GRID_PRESET_NOTES: Dict[str, str] = {
    "India grid today": (
        "The mix quoted in the workbook's reference note (~70% coal, 4% gas, 12% hydro, "
        "4% wind, 5% solar, 2% nuclear, 2% oil), which blends to ~0.71 kg CO2e/kWh."
    ),
    "50% renewable": "Half the supply from hydro, wind and solar — a mid-transition PPA position.",
    "Near-zero carbon": "Entirely non-fossil supply: hydro, wind, solar and nuclear only.",
    "JSL Jajpur (estimated)": (
        "Coal-dominated Odisha supply with a captive solar contribution. Jindal Stainless "
        "commissioned Odisha's largest single-campus captive solar plant at Jajpur — over "
        "30 MWp (a 7.324 MW floating array plus 23.02 MWp rooftop) generating ~44.3 million "
        "units a year — and has contracted a 700 million-unit/year wind-solar hybrid with "
        "ReNew. The solar and wind capacity is published; the percentage split below is an "
        "ESTIMATE, since the site's source-wise consumption mix is not disclosed."
    ),
    "JSL Hisar (estimated)": (
        "Haryana grid supply alongside the site's 250 MW captive power plant and rooftop "
        "solar. The captive capacity is published; the percentage split below is an "
        "ESTIMATE, since the site's source-wise consumption mix is not disclosed."
    ),
}


# --------------------------------------------------------------------------- #
# Plant profiles
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class PlantProfile:
    """A plant's process route, transport split and energy mix."""

    name: str
    tagline: str
    summary: str
    grid_preset: str
    scrap_ratio: float
    #: Rail share of the inbound and outbound legs — a site can rail its raw
    #: material in and truck its coil out, so the two are separate.
    inbound_rail: float
    outbound_rail: float
    #: (stage process name, [variation names]) — variations are matched by name,
    #: so an unmatched entry is reported rather than silently ignored.
    route_choices: Tuple[Tuple[str, Tuple[str, ...]], ...] = ()
    #: Departments the site does not run at all.
    excluded_departments: Tuple[str, ...] = ()
    #: Individual techniques the site does not run, by process name.
    excluded_techniques: Tuple[str, ...] = ()
    #: Departments where only the listed techniques run. A department named here
    #: keeps *only* what ``route_choices`` and ``kept_techniques`` mention;
    #: everything else in it is switched off. This is how a site profile comes
    #: out visibly narrower than "run everything".
    restricted_departments: Tuple[str, ...] = ()
    #: Techniques kept in a restricted department beyond those in route_choices.
    kept_techniques: Tuple[str, ...] = ()
    sources: Tuple[Tuple[str, str], ...] = ()
    estimated: Tuple[str, ...] = ()


CUSTOM = PlantProfile(
    name="Custom",
    tagline="Start from the workbook's default route",
    summary=(
        "Every stage runs its first-listed technology at a 40% scrap charge on today's "
        "Indian grid. Change anything you like — this is the blank sheet."
    ),
    grid_preset="India grid today",
    scrap_ratio=0.40,
    inbound_rail=0.50,
    outbound_rail=0.50,
)

JAJPUR = PlantProfile(
    name="JSL Jajpur",
    tagline="Integrated melting to hot rolling, Odisha",
    summary=(
        "India's largest stainless plant at ~2.2 MTPA. Ferrochrome from submerged arc "
        "furnaces feeds an EAF, liquid steel is decarburised in an AOD converter, refined "
        "in a ladle furnace, and cast on a single-strand slab caster before hot rolling."
    ),
    grid_preset="JSL Jajpur (estimated)",
    scrap_ratio=0.35,
    inbound_rail=0.70,
    outbound_rail=0.55,
    route_choices=(
        ("Inspection", ("Ferroalloy", "Scrap")),
        ("Primary Melting", ("Electric Arc Furnace (EAF)",)),
        ("Decarburization / Alloying", ("AOD",)),
        ("Secondary Refining / Homogenization", ("Ladle Furnace (LF)",)),
        # One caster, not three: SEN and argon shrouding are practices applied
        # *with* a caster, not alternative casters. Listing them here would send
        # a third of every tonne "through" a nozzle instead of through the mould.
        ("Continuous Casting (CCM)", ("Curved Mold Caster",)),
    ),
    # Jajpur is the integrated melt-to-coil line: the publicly described route is
    # EAF → AOD → LF → single-strand slab caster → hot strip. Its finishing end is
    # narrower than the workbook's full catalogue, so those departments keep only
    # what is evidenced.
    restricted_departments=(
        "Melt Shop", "Hot Rolling", "Annealing", "Descaling", "Pickling", "Cold Rolling",
    ),
    kept_techniques=(
        "Scrap Prep / Charging",
        # The hot strip line as described: reheat, rough, finish, coil.
        "Reheating in Furnace",
        "High Pressure Hydraulic Descaling",
        "Roughing Rolling Mill",
        "Finishing Rolling Train",
        "Controlled Cooling",
        "Coiling or Plate Shearing",
        "Hydraulic High Pressure Spraying",
        "Mechanical Impingement Shot Blasting",
        "Solution Annealing",
        "Continuous Tank Pickling",
        "20-High Cluster Mill (Z-Mill / Sendzimir)",
        "CAPL / AP Line (Continuous Anneal & Pickle Line)",
        "Tension Leveling / Slitting Lines",
    ),
    sources=(
        (
            "Primetals — new AOD converter, ladle furnace and stainless caster at JSL "
            "(150 t AOD, 150 t ladle furnace, single-strand slab caster)",
            "https://www.primetals.com/press-media/news/primetals-technologies-receives-fac-for-new-aod-converter-ladle-furnace-and-stainless-caster-at-jsl",
        ),
        (
            "Jindal Stainless — captive solar at Jajpur (30+ MWp, ~44.3 MU/year)",
            "https://www.jindalstainless.com/press-releases/jindal-stainless-and-ab-energia-set-new-benchmark-with-odishas-largest-captive-industrial-solar-plant/",
        ),
        (
            "Jindal Stainless — 300 MW / 700 MU renewable project with ReNew Power",
            "https://www.jindalstainless.com/press-releases/accelerating-its-esg-goals-jindal-stainless-partners-with-renew-power-to-set-up-300-mw-renewable-energy-project/",
        ),
    ),
    estimated=("energy mix percentages", "scrap ratio", "rail/road splits"),
)

HISAR = PlantProfile(
    name="JSL Hisar",
    tagline="Melting plus the specialty finishing complex, Haryana",
    summary=(
        "The group's original site, ~0.8 MTPA, running a stainless melt shop alongside the "
        "cold-rolling complex: four 20-Hi Sendzimir mills, three continuous anneal-and-pickle "
        "lines (three with electrolytic pickling), a bright annealing line, and slitting and "
        "cut-to-length finishing."
    ),
    grid_preset="JSL Hisar (estimated)",
    scrap_ratio=0.45,
    inbound_rail=0.40,
    outbound_rail=0.25,
    route_choices=(
        ("Inspection", ("Scrap",)),
        # Selecting two variations splits the tonne evenly between them, so
        # listing VIM beside the EAF claimed half of Hisar's output is vacuum
        # remelted. The specialty routes are a small fraction of a stainless
        # plant's tonnage, and the profile is the main line: one melting route,
        # one decarburiser, one refiner, one caster.
        ("Primary Melting", ("Electric Arc Furnace (EAF)",)),
        ("Decarburization / Alloying", ("AOD",)),
        ("Secondary Refining / Homogenization", ("Ladle Furnace (LF)",)),
        ("Continuous Casting (CCM)", ("Curved Mold Caster",)),
    ),
    # Hisar is the specialty end: four 20-Hi Sendzimir mills, three continuous
    # anneal-and-pickle lines, a bright annealing line, slitting and cut-to-length
    # (ANDRITZ / Jindal Stainless, cited below). The tandem cold mill and the
    # 6-High UC mill are not part of that description.
    restricted_departments=(
        "Melt Shop", "Hot Rolling", "Annealing", "Descaling", "Pickling", "Cold Rolling",
    ),
    kept_techniques=(
        "Scrap Prep / Charging",
        "Reheating in Furnace",
        "High Pressure Hydraulic Descaling",
        "Roughing Rolling Mill",
        "Finishing Rolling Train",
        "Coiling or Plate Shearing",
        "Hydraulic High Pressure Spraying",
        "Mechanical Impingement Shot Blasting",
        # The four 20-Hi Sendzimir mills, three anneal-and-pickle lines and the
        # bright annealing line ANDRITZ and Jindal Stainless describe.
        "Bright Annealing",
        "Open Annealing / Pickling",
        "Continuous Tank Pickling",
        "20-High Cluster Mill (Z-Mill / Sendzimir)",
        "CAPL / AP Line (Continuous Anneal & Pickle Line)",
        "Bright Annealing (in-process, Cold Rolling sequence)",
        "Temper Mill (Skin-Pass)",
        "Tension Leveling / Slitting Lines",
    ),
    sources=(
        (
            "ANDRITZ — hot and cold annealing and pickling lines supplied to Jindal",
            "https://www.andritz.com/metals-en/news-media/references-and-success-stories/jindal-india",
        ),
        (
            "Jindal Stainless — Hisar cold rolling complex and melt shop",
            "https://www.jindalstainless.com/50years/",
        ),
        (
            "Jindal Stainless — rooftop solar at the Jajpur and Hisar units",
            "https://www.jindalstainless.com/press-releases/jindal-stainless-invests-over-120-crores-to-install-rooftop-solar-plants-at-its-jajpur-and-hisar-units/",
        ),
    ),
    estimated=("energy mix percentages", "scrap ratio", "rail/road splits"),
)

PLANT_PROFILES: Dict[str, PlantProfile] = {
    profile.name: profile for profile in (CUSTOM, JAJPUR, HISAR)
}

#: The profile the app opens on — the larger of the two sites.
OPENING_PROFILE = JAJPUR.name


def profile_route(profile: PlantProfile, stages: Sequence[Stage]) -> Tuple[RouteMix, List[str]]:
    """Build a route for a profile, reporting any choice that did not match.

    Unmatched names are returned rather than silently dropped, so a typo in a
    profile shows up instead of quietly falling back to the default technology.
    """
    route = default_route(stages)
    wanted = dict(profile.route_choices)
    problems: List[str] = []
    kept = set(profile.kept_techniques) | {name for name, _ in profile.route_choices}

    for stage in stages:
        restricted = stage.department in profile.restricted_departments
        if (
            stage.department in profile.excluded_departments
            or stage.process in profile.excluded_techniques
            or (restricted and stage.process not in kept)
        ):
            route[stage.key] = {}
            continue
        names = wanted.pop(stage.process, None)
        if not names:
            continue
        chosen = [
            option.id for option in stage.options if option.variation in names
        ]
        missing = set(names) - {
            option.variation for option in stage.options if option.variation in names
        }
        if missing:
            problems.append(f"{stage.process}: no variation named {sorted(missing)}")
        if chosen:
            share = 1.0 / len(chosen)
            route[stage.key] = {pid: share for pid in chosen}

    for process in wanted:
        problems.append(f"no stage named {process!r}")
    return route, problems


def preset_matching(mix: Mapping[str, float], tolerance: float = 0.005) -> str | None:
    """Name the preset a mix corresponds to, if any — used to keep the UI honest."""
    for name, preset in GRID_PRESETS.items():
        if all(
            abs(float(mix.get(var, 0.0)) - preset.get(var, 0.0)) <= tolerance
            for var in MIX_VARIABLES
        ):
            return name
    return None
