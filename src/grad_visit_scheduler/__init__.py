"""Grad visit scheduling package."""
from .core import (
    Scheduler,
    Mode,
    MovementPolicy,
    Solver,
    FacultyStatus,
    SolutionResult,
    SolutionSet,
    compute_min_travel_lags,
)
from .config import (
    load_faculty_catalog,
    load_run_config,
    build_times_by_building,
    scheduler_from_configs,
)
from .export import export_visitor_docx

__all__ = [
    "Scheduler",
    "Mode",
    "MovementPolicy",
    "Solver",
    "FacultyStatus",
    "SolutionResult",
    "SolutionSet",
    "compute_min_travel_lags",
    "load_faculty_catalog",
    "load_run_config",
    "build_times_by_building",
    "scheduler_from_configs",
    "export_visitor_docx",
]
from importlib.metadata import version as _version

__version__ = _version("grad-visitor-scheduler")
