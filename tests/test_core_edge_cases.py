"""Additional branch/edge-case tests for core scheduler logic."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys
import types

import pandas as pd
import pytest

import grad_visit_scheduler.core as core_mod
from grad_visit_scheduler import Mode, Scheduler, Solver
from grad_visit_scheduler.plotting import abbreviate_name
from pyomo.opt import SolverStatus, TerminationCondition


def _write_csv(path: Path, rows):
    pd.DataFrame(rows).to_csv(path, index=False)


def _highs_available() -> bool:
    try:
        return core_mod.pyo.SolverFactory("appsi_highs").available() or core_mod.pyo.SolverFactory("highs").available()
    except Exception:
        return False


def _tiny_scheduler(
    tmp_path: Path,
    *,
    mode: Mode = Mode.BUILDING_A_FIRST,
    solver: Solver = Solver.HIGHS,
    faculty_catalog: dict | None = None,
) -> Scheduler:
    csv_path = tmp_path / "v.csv"
    _write_csv(
        csv_path,
        [{"Name": "Visitor 1", "Prof1": "Faculty A", "Area1": "Area1", "Area2": "Area2"}],
    )
    times_by_building = {
        "BuildingA": ["1:00-1:25", "1:30-1:55"],
        "BuildingB": ["1:00-1:25", "1:30-1:55"],
    }
    if faculty_catalog is None:
        faculty_catalog = {
            "Faculty A": {
                "building": "BuildingA",
                "room": "101",
                "areas": ["Area1"],
                "status": "active",
            }
        }
    return Scheduler(
        times_by_building=times_by_building,
        student_data_filename=str(csv_path),
        mode=mode,
        solver=solver,
        faculty_catalog=faculty_catalog,
    )


def test_abbreviate_name_edge_cases():
    """Cover single/empty/multi-part name formatting branches."""
    assert abbreviate_name(None) == ""
    assert abbreviate_name(" ") == ""
    assert abbreviate_name("Jane") == "Jane"
    assert abbreviate_name("Jane Doe") == "Jane D."
    assert abbreviate_name("Jane Mary Doe") == "Jane M. D."
    assert abbreviate_name("Visitor 01") == "Visitor 01"


def test_default_catalog_path_and_time_validation_errors(tmp_path: Path):
    """Cover default faculty load path and scheduler time validation branches."""
    csv_path = tmp_path / "v.csv"
    _write_csv(csv_path, [{"Name": "Visitor 1", "Prof1": "Faculty A", "Area1": "Area1", "Area2": "Area2"}])

    # Default catalog branch (faculty_catalog=None)
    s = Scheduler(
        times_by_building={"BuildingA": ["1:00-1:25"], "BuildingB": ["1:00-1:25"]},
        student_data_filename=str(csv_path),
        mode=Mode.BUILDING_A_FIRST,
        solver=Solver.HIGHS,
        faculty_catalog=None,
    )
    assert "Faculty A" in s.faculty and "Faculty B" in s.faculty

    with pytest.raises(ValueError, match="exactly two buildings"):
        Scheduler(
            times_by_building={"BuildingA": ["1:00-1:25"]},
            student_data_filename=str(csv_path),
            mode=Mode.BUILDING_A_FIRST,
            solver=Solver.HIGHS,
            faculty_catalog=s.faculty,
        )

    with pytest.raises(ValueError, match="valid break time"):
        Scheduler(
            times_by_building={
                "BuildingA": ["1:00-1:25"],
                "BuildingB": ["1:00-1:25"],
                "breaks": [2],
            },
            student_data_filename=str(csv_path),
            mode=Mode.BUILDING_A_FIRST,
            solver=Solver.HIGHS,
            faculty_catalog=s.faculty,
        )

    with pytest.raises(ValueError, match="same number of timeslots"):
        Scheduler(
            times_by_building={"BuildingA": ["1:00-1:25"], "BuildingB": ["1:00-1:25", "1:30-1:55"]},
            student_data_filename=str(csv_path),
            mode=Mode.BUILDING_A_FIRST,
            solver=Solver.HIGHS,
            faculty_catalog=s.faculty,
        )


def test_solution_set_wrappers_and_filename_helpers(tmp_path: Path):
    """Cover SolutionSet.best wrapper and forwarding plot/export methods."""
    pytest.importorskip("docx")
    s = _tiny_scheduler(tmp_path, mode=Mode.BUILDING_A_FIRST)
    top = s.schedule_visitors_top_n(
        n_solutions=1,
        group_penalty=0.1,
        min_visitors=0,
        max_visitors=2,
        min_faculty=1,
        max_group=1,
        enforce_breaks=False,
        tee=False,
        run_name="edge",
    )
    best = top.best()
    assert best.rank == 1
    assert best._schedule_filename("x", suffix="_y").endswith("_y")

    top.plot_faculty_schedule(rank=1, save_files=False)
    top.plot_visitor_schedule(rank=1, save_files=False)
    out = top.export_visitor_docx(tmp_path / "wrapper.docx", rank=1)
    assert out.exists()


def test_docx_export_without_breaks_and_external_summary(tmp_path: Path):
    """Cover DOCX empty-cell formatting path and external assignment summary."""
    pytest.importorskip("docx")
    csv_path = tmp_path / "v.csv"
    _write_csv(
        csv_path,
        [{"Name": "Visitor 1", "Prof1": "External Z", "Area1": "Area1", "Area2": "Area2"}],
    )
    s = Scheduler(
        times_by_building={"BuildingA": ["1:00-1:25", "1:30-1:55"], "BuildingB": ["1:00-1:25", "1:30-1:55"]},
        student_data_filename=str(csv_path),
        mode=Mode.BUILDING_A_FIRST,
        solver=Solver.HIGHS,
        faculty_catalog={
            "Faculty A": {
                "building": "BuildingA",
                "room": "101",
                "areas": ["Area1"],
                "status": "active",
            }
        },
    )
    s.add_external_faculty("External Z")  # defaults: building=None/areas=None/available=None
    s.faculty_limited_availability("External Z", [1, 2])
    top = s.schedule_visitors_top_n(
        n_solutions=1,
        group_penalty=0.1,
        min_visitors=0,
        max_visitors=1,
        min_faculty=1,
        max_group=1,
        enforce_breaks=False,
        tee=False,
        run_name="external",
    )
    sol = top.get(1)
    row = sol.summary_row(best_objective=sol.objective_value)
    assert row["external_assignments"] >= 1

    # include_breaks=False exercises empty-run fallback formatting for open slots.
    out = sol.export_visitor_docx(tmp_path / "no_breaks.docx", include_breaks=False)
    assert out.exists()


def test_legacy_hasattr_guard_and_validation_branches(tmp_path: Path):
    """Cover hasattr guard and invalid faculty-limited availability name."""
    s = _tiny_scheduler(tmp_path)
    delattr(s, "legacy_faculty")
    s._add_legacy_faculty_from_preferences()
    with pytest.raises(ValueError, match="faculty member"):
        s.faculty_limited_availability("Missing Faculty", [1])


def test_preference_update_unknown_and_nan_paths(tmp_path: Path, capsys):
    """Cover unknown faculty print path and NaN/none preference skips."""
    s = _tiny_scheduler(tmp_path)
    s.student_data.loc["Visitor 1", "Prof1"] = "none"
    s.student_data.loc["Visitor 1", "Area1"] = float("nan")
    s.update_weights()

    s.student_data.loc["Visitor 1", "Prof1"] = "Ghost Person"
    s.update_weights()
    captured = capsys.readouterr()
    assert "Unknown faculty preference" in captured.out


def test_load_preferences_skips_none_like_strings(tmp_path: Path):
    """The loader should skip none-like faculty strings during initial parse."""
    csv_path = tmp_path / "v_none.csv"
    _write_csv(
        csv_path,
        [{"Name": "Visitor 1", "Prof1": "none", "Area1": "Area1", "Area2": "Area2"}],
    )
    s = Scheduler(
        times_by_building={"BuildingA": ["1:00-1:25"], "BuildingB": ["1:00-1:25"]},
        student_data_filename=str(csv_path),
        mode=Mode.BUILDING_A_FIRST,
        solver=Solver.HIGHS,
        faculty_catalog={
            "Faculty A": {
                "building": "BuildingA",
                "room": "101",
                "areas": ["Area1"],
                "status": "active",
            }
        },
    )
    assert s.requests["Visitor 1"] == []


def test_invalid_student_availability_name_raises(tmp_path: Path):
    """Invalid visitor name in limited availability should raise."""
    s = _tiny_scheduler(tmp_path)
    with pytest.raises(ValueError, match="valid student name"):
        s.specify_limited_student_availability({"Ghost Visitor": [1]})


@pytest.mark.skipif(not _highs_available(), reason="HiGHS solver unavailable")
def test_fixed_unavailable_student_slot_in_model(tmp_path: Path):
    """When student slot is unavailable, corresponding y vars are fixed to zero."""
    s = _tiny_scheduler(tmp_path)
    s.specify_limited_student_availability({"Visitor 1": [1]})
    s.schedule_visitors(
        group_penalty=0.1,
        min_visitors=0,
        max_visitors=2,
        min_faculty=1,
        max_group=1,
        enforce_breaks=False,
        tee=False,
        run_name="fixed_slots",
    )
    for f in s.model.faculty:
        assert s.model.y["Visitor 1", f, 2].fixed


@pytest.mark.skipif(not _highs_available(), reason="HiGHS solver unavailable")
def test_infeasibility_report_min_faculty_capacity_message(tmp_path: Path):
    """Report should include min_faculty capacity warning branch."""
    s = _tiny_scheduler(tmp_path)
    s.faculty_limited_availability("Faculty A", [1])
    s.schedule_visitors(
        group_penalty=0.1,
        min_visitors=0,
        max_visitors=2,
        min_faculty=2,
        max_group=1,
        enforce_breaks=False,
        tee=False,
        run_name="min_faculty_infeasible",
    )
    assert not s.has_feasible_solution()
    report = s.infeasibility_report()
    assert "min_faculty requirement exceeds total capacity" in report


def test_solverfactory_highs_unavailable_raises(tmp_path: Path, monkeypatch):
    """Cover RuntimeError when neither appsi_highs nor highs is available."""
    s = _tiny_scheduler(tmp_path)

    class FakeOpt:
        def available(self):
            return False

    monkeypatch.setattr(core_mod.pyo, "SolverFactory", lambda *args, **kwargs: FakeOpt())
    with pytest.raises(RuntimeError, match="No available HiGHS solver found"):
        s.schedule_visitors(
            group_penalty=0.1,
            min_visitors=0,
            max_visitors=2,
            min_faculty=1,
            max_group=1,
            enforce_breaks=False,
            tee=False,
            run_name="no_highs",
        )


def test_solverfactory_highs_runtimeerror_reraises(tmp_path: Path, monkeypatch):
    """Cover generic RuntimeError re-raise path in _solve_model."""
    s = _tiny_scheduler(tmp_path)

    class FakeOpt:
        config = SimpleNamespace(load_solution=True)

        def available(self):
            return True

        def solve(self, *args, **kwargs):
            raise RuntimeError("unexpected solver failure")

    monkeypatch.setattr(core_mod.pyo, "SolverFactory", lambda *args, **kwargs: FakeOpt())
    with pytest.raises(RuntimeError, match="unexpected solver failure"):
        s.schedule_visitors(
            group_penalty=0.1,
            min_visitors=0,
            max_visitors=2,
            min_faculty=1,
            max_group=1,
            enforce_breaks=False,
            tee=False,
            run_name="highs_runtimeerror",
        )


def test_solverfactory_gurobi_iis_unavailable_raises(tmp_path: Path, monkeypatch):
    """Cover GUROBI_IIS available(exception_flag=False)==False path."""
    s = _tiny_scheduler(tmp_path, solver=Solver.GUROBI_IIS)
    fake_exe = tmp_path / "gurobi_ampl"
    fake_exe.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    monkeypatch.setenv("GVS_GUROBI_IIS_EXECUTABLE", str(fake_exe))

    class FakeOpt:
        def available(self, exception_flag=False):
            return False

    monkeypatch.setattr(core_mod.pyo, "SolverFactory", lambda *args, **kwargs: FakeOpt())
    with pytest.raises(RuntimeError, match="GUROBI_IIS solver is not available"):
        s.schedule_visitors(
            group_penalty=0.1,
            min_visitors=0,
            max_visitors=2,
            min_faculty=1,
            max_group=1,
            enforce_breaks=False,
            tee=False,
            run_name="iis_unavailable",
        )


@pytest.mark.skipif(not _highs_available(), reason="HiGHS solver unavailable")
def test_docx_export_cell_run_fallback_branch(tmp_path: Path, monkeypatch):
    """Force the cell add_run fallback path used when a paragraph has no runs."""
    s = _tiny_scheduler(tmp_path)
    top = s.schedule_visitors_top_n(
        n_solutions=1,
        group_penalty=0.1,
        min_visitors=0,
        max_visitors=1,
        min_faculty=1,
        max_group=1,
        enforce_breaks=False,
        tee=False,
        run_name="mock_docx",
    )
    sol = top.get(1)

    class _FakeRun:
        def __init__(self):
            self.font = SimpleNamespace(size=None, name=None)

    class _FakeParagraph:
        cell_add_run_calls = 0

        def __init__(self, is_cell=False):
            self.runs = []
            self._is_cell = is_cell

        def add_run(self, _text):
            if self._is_cell:
                _FakeParagraph.cell_add_run_calls += 1
            run = _FakeRun()
            self.runs.append(run)
            return run

    class _FakeCell:
        def __init__(self):
            self.paragraphs = [_FakeParagraph(is_cell=True)]
            self.text = ""

    class _FakeTable:
        def __init__(self, rows, cols):
            self.rows = [SimpleNamespace(cells=[_FakeCell() for _ in range(cols)]) for _ in range(rows)]

    class _FakeDocument:
        def add_paragraph(self, _text=""):
            return _FakeParagraph(is_cell=False)

        def add_table(self, rows, cols):
            return _FakeTable(rows, cols)

        def save(self, _path):
            return None

    fake_docx = types.ModuleType("docx")
    fake_docx_shared = types.ModuleType("docx.shared")
    fake_docx.Document = _FakeDocument
    fake_docx_shared.Pt = lambda x: x
    monkeypatch.setitem(sys.modules, "docx", fake_docx)
    monkeypatch.setitem(sys.modules, "docx.shared", fake_docx_shared)

    sol.export_visitor_docx(tmp_path / "fake.docx", include_breaks=False)
    assert _FakeParagraph.cell_add_run_calls > 0


def test_scheduler_direct_movement_validation_branches(tmp_path: Path):
    """Exercise direct Scheduler movement validation that bypasses config loader."""
    csv_path = tmp_path / "v.csv"
    _write_csv(csv_path, [{"Name": "Visitor 1", "Prof1": "Faculty A", "Area1": "Area1", "Area2": "Area2"}])
    times = {"BuildingA": ["1:00-1:25", "1:30-1:55"], "BuildingB": ["1:00-1:25", "1:30-1:55"]}
    faculty_catalog = {
        "Faculty A": {"building": "BuildingA", "room": "101", "areas": ["Area1"], "status": "active"},
        "Faculty B": {"building": "BuildingB", "room": "201", "areas": ["Area1"], "status": "active"},
    }

    with pytest.raises(ValueError, match="Unsupported movement policy"):
        Scheduler(
            times_by_building=times,
            student_data_filename=str(csv_path),
            movement={"policy": "teleport"},
            solver=Solver.HIGHS,
            faculty_catalog=faculty_catalog,
        )

    with pytest.raises(ValueError, match="movement.phase_slot"):
        Scheduler(
            times_by_building=times,
            student_data_filename=str(csv_path),
            movement={"policy": "none", "phase_slot": {"BuildingA": 0, "BuildingB": 1}},
            solver=Solver.HIGHS,
            faculty_catalog=faculty_catalog,
        )

    with pytest.raises(ValueError, match="min_buffer_minutes"):
        Scheduler(
            times_by_building=times,
            student_data_filename=str(csv_path),
            movement={"policy": "travel_time", "min_buffer_minutes": -1},
            solver=Solver.HIGHS,
            faculty_catalog=faculty_catalog,
        )

    with pytest.raises(ValueError, match="nonoverlap_time"):
        Scheduler(
            times_by_building=times,
            student_data_filename=str(csv_path),
            movement={
                "policy": "nonoverlap_time",
                "travel_slots": {"BuildingA": {"BuildingA": 0, "BuildingB": 1}},
            },
            solver=Solver.HIGHS,
            faculty_catalog=faculty_catalog,
        )

    with pytest.raises(ValueError, match="dictionary or 'auto'"):
        Scheduler(
            times_by_building=times,
            student_data_filename=str(csv_path),
            movement={"policy": "travel_time", "travel_slots": "manual"},
            solver=Solver.HIGHS,
            faculty_catalog=faculty_catalog,
        )

    with pytest.raises(ValueError, match="missing row"):
        Scheduler(
            times_by_building=times,
            student_data_filename=str(csv_path),
            movement={
                "policy": "travel_time",
                "travel_slots": {"BuildingA": {"BuildingA": 0, "BuildingB": 1}},
            },
            solver=Solver.HIGHS,
            faculty_catalog=faculty_catalog,
        )

    with pytest.raises(ValueError, match="missing destination"):
        Scheduler(
            times_by_building=times,
            student_data_filename=str(csv_path),
            movement={
                "policy": "travel_time",
                "travel_slots": {
                    "BuildingA": {"BuildingA": 0},
                    "BuildingB": {"BuildingA": 1, "BuildingB": 0},
                },
            },
            solver=Solver.HIGHS,
            faculty_catalog=faculty_catalog,
        )

    with pytest.raises(ValueError, match="nonnegative integers"):
        Scheduler(
            times_by_building=times,
            student_data_filename=str(csv_path),
            movement={
                "policy": "travel_time",
                "travel_slots": {
                    "BuildingA": {"BuildingA": 0, "BuildingB": -1},
                    "BuildingB": {"BuildingA": 1, "BuildingB": 0},
                },
            },
            solver=Solver.HIGHS,
            faculty_catalog=faculty_catalog,
        )

    # travel_slots omitted under travel_time should synthesize default lag matrix.
    s_default = Scheduler(
        times_by_building=times,
        student_data_filename=str(csv_path),
        movement={"policy": "travel_time"},
        solver=Solver.HIGHS,
        faculty_catalog=faculty_catalog,
    )
    assert s_default.travel_slots["BuildingA"]["BuildingB"] == 1
    assert s_default.travel_slots["BuildingB"]["BuildingA"] == 1


def test_scheduler_rejects_times_with_no_buildings_key(tmp_path: Path):
    """Times mapping with only breaks should be rejected."""
    csv_path = tmp_path / "v.csv"
    _write_csv(csv_path, [{"Name": "Visitor 1", "Prof1": "Faculty A", "Area1": "Area1", "Area2": "Area2"}])
    with pytest.raises(ValueError, match="at least one building"):
        Scheduler(
            times_by_building={"breaks": [1]},
            student_data_filename=str(csv_path),
            movement={"policy": "none"},
            solver=Solver.HIGHS,
            faculty_catalog={"Faculty A": {"building": "BuildingA", "room": "101", "areas": ["Area1"], "status": "active"}},
        )


def test_none_policy_warning_truncates_many_risky_pairs(tmp_path: Path):
    """Warning message should truncate long risky pair lists with ellipsis."""
    csv_path = tmp_path / "v.csv"
    _write_csv(csv_path, [{"Name": "Visitor 1", "Prof1": "Faculty A", "Area1": "Area1", "Area2": "Area2"}])
    times = {
        "A": ["1:00-1:25", "1:30-1:55"],
        "B": ["1:05-1:30", "1:35-2:00"],
        "C": ["1:10-1:35", "1:40-2:05"],
        "D": ["1:15-1:40", "1:45-2:10"],
        "E": ["1:20-1:45", "1:50-2:15"],
    }
    faculty_catalog = {
        "Faculty A": {"building": "A", "room": "101", "areas": ["Area1"], "status": "active"},
    }
    with pytest.warns(UserWarning) as w:
        Scheduler(
            times_by_building=times,
            student_data_filename=str(csv_path),
            movement={"policy": "none"},
            solver=Solver.HIGHS,
            faculty_catalog=faculty_catalog,
        )
    assert "..." in str(w[0].message)


def test_gurobi_iis_prints_iis_entries_when_available(tmp_path: Path, monkeypatch, capsys):
    """Cover GUROBI_IIS option setup, IIS suffix creation, and IIS print loop."""
    s = _tiny_scheduler(tmp_path, solver=Solver.GUROBI_IIS)
    fake_exe = tmp_path / "gurobi_ampl"
    fake_exe.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    monkeypatch.setenv("GVS_GUROBI_IIS_EXECUTABLE", str(fake_exe))

    class FakeOpt:
        def __init__(self):
            self.options = {}

        def available(self, exception_flag=False):
            return True

        def solve(self, model, tee=False):
            # Insert one IIS-marked component to exercise print loop lines.
            first_y = next(model.y.values())
            model.iis[first_y] = 1
            return SimpleNamespace(
                solver=SimpleNamespace(
                    termination_condition=TerminationCondition.infeasible,
                    status=SolverStatus.warning,
                )
            )

    monkeypatch.setattr(core_mod.pyo, "SolverFactory", lambda *args, **kwargs: FakeOpt())
    s.schedule_visitors(
        group_penalty=0.1,
        min_visitors=0,
        max_visitors=2,
        min_faculty=1,
        max_group=1,
        enforce_breaks=False,
        tee=False,
        run_name="iis_print",
    )
    out = capsys.readouterr().out
    assert "IIS Results" in out
    assert "y[" in out
