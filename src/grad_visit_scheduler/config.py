"""Config loading and helpers for grad visit scheduling."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

import yaml

from .core import Scheduler, Mode, Solver


def load_yaml(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def load_faculty_catalog(path: str | Path) -> Tuple[Dict[str, Any], Dict[str, str]]:
    data = load_yaml(path)
    faculty = data.get("faculty", {})
    aliases = data.get("aliases", {})
    if not faculty:
        raise ValueError("Faculty catalog is empty or missing 'faculty' section.")
    for alias, target in aliases.items():
        if target not in faculty:
            raise ValueError(f"Alias target '{target}' not found in faculty catalog.")
    return faculty, aliases


def load_run_config(path: str | Path) -> Dict[str, Any]:
    data = load_yaml(path)
    if "buildings" not in data or not data.get("buildings"):
        raise ValueError("Run config missing 'buildings' section.")
    building_order = data.get("building_order")
    if building_order is not None:
        if not isinstance(building_order, list) or len(building_order) != 2:
            raise ValueError("Run config 'building_order' must be a list of exactly two building names.")
        buildings = data.get("buildings", {})
        missing = [b for b in building_order if b not in buildings]
        if missing:
            raise ValueError(f"Run config 'building_order' entries not found in buildings: {missing}")
    return data


def build_times_by_building(run_config: Dict[str, Any]) -> Dict[str, Any]:
    buildings = run_config.get("buildings", {})
    if not buildings:
        raise ValueError("Run config must define at least one building.")
    building_order = run_config.get("building_order")
    if building_order:
        times = {name: buildings[name] for name in building_order}
    else:
        times = dict(buildings)
    breaks = run_config.get("breaks", [])
    if breaks:
        times["breaks"] = breaks
    return times


def scheduler_from_configs(
    faculty_catalog_path: str | Path,
    run_config_path: str | Path,
    student_data_filename: str | Path,
    mode: Mode = Mode.NO_OFFSET,
    solver: Solver = Solver.HIGHS,
    include_legacy_faculty: bool = False,
) -> Scheduler:
    faculty_catalog, aliases = load_faculty_catalog(faculty_catalog_path)
    run_cfg = load_run_config(run_config_path)
    buildings = set(run_cfg.get("buildings", {}).keys())
    invalid_buildings = sorted(
        {info.get("building") for info in faculty_catalog.values()} - buildings
    )
    if invalid_buildings:
        raise ValueError(
            "Faculty catalog contains building(s) not defined in run config: "
            + ", ".join(invalid_buildings)
        )
    times_by_building = build_times_by_building(run_cfg)

    s = Scheduler(
        times_by_building=times_by_building,
        student_data_filename=str(student_data_filename),
        mode=mode,
        solver=solver,
        include_legacy_faculty=include_legacy_faculty,
        faculty_catalog=faculty_catalog,
        faculty_aliases=aliases,
    )

    faculty_availability = run_cfg.get("faculty_availability", {})
    for name, availability in faculty_availability.items():
        s.faculty_limited_availability(name, availability)

    area_weights = run_cfg.get("area_weights")
    if area_weights:
        s.update_weights(area_weight=area_weights)

    return s
