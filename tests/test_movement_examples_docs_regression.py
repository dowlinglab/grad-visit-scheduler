"""Regression checks tying documented movement examples to computed results.

If this test fails after changing configs, solver settings, or movement logic,
update the unified comparison table in:
`docs/movement.md` ("Examples for Different Building Configurations").
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
DOCS_MOVEMENT = ROOT / "docs" / "movement.md"
RUNNER_PATH = ROOT / "scripts" / "run_building_configuration_examples.py"


def _load_runner_module():
    spec = importlib.util.spec_from_file_location("run_building_configuration_examples", RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _parse_documented_unified_table(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    header = "| Category | Scenario | Policy | Feasible | Objective | Assignments | Requested Assignments | Group Slots |"
    header_idx = next(i for i, line in enumerate(lines) if line.strip() == header)

    rows = []
    for line in lines[header_idx + 2 :]:
        stripped = line.strip()
        if not stripped.startswith("|"):
            break
        cols = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cols) != 8:
            continue
        rows.append(
            {
                "category": cols[0],
                "scenario": cols[1],
                "policy": cols[2].strip("`"),
                "feasible": cols[3] == "True",
                "objective": float(cols[4]),
                "assignments": int(cols[5]),
                "requested_assignments": int(cols[6]),
                "group_slots": int(cols[7]),
            }
        )
    return rows


def test_movement_examples_match_documented_results():
    """All documented movement examples must match computed scenario results.

    Breadcrumb for maintainers:
    If results drift, adjust either:
    1) The scenario configs / solver behavior, or
    2) The docs table in docs/movement.md.
    Keep both in sync.
    """
    docs_rows = _parse_documented_unified_table(DOCS_MOVEMENT)
    assert len(docs_rows) == 10

    runner = _load_runner_module()
    computed_df = runner.run(plot_dir=None)
    computed_rows = computed_df.to_dict(orient="records")
    assert len(computed_rows) == 10

    computed_by_scenario = {row["scenario"]: row for row in computed_rows}
    assert set(computed_by_scenario.keys()) == {row["scenario"] for row in docs_rows}

    for documented in docs_rows:
        scenario = documented["scenario"]
        computed = computed_by_scenario[scenario]
        assert computed["category"] == documented["category"]
        assert computed["policy"] == documented["policy"]
        assert computed["feasible"] == documented["feasible"]
        assert computed["objective"] == documented["objective"]
        assert computed["assignments"] == documented["assignments"]
        assert computed["requested_assignments"] == documented["requested_assignments"]
        assert computed["group_slots"] == documented["group_slots"]
