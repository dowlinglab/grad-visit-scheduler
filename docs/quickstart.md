# Quickstart

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/dowlinglab/grad-visit-scheduler/blob/main/examples/large_example_colab.ipynb)

This quickstart uses the larger formulation example:

- `examples/faculty_formulation.yaml` (6 faculty: `Prof. A` to `Prof. F`)
- `examples/config_formulation.yaml` (4 meeting slots across buildings `ABC` and `XYZ`)
- `examples/data_formulation_visitors.csv` (10 visitors)

For a detailed explanation of this same example (model equations, conflicts, preferences, and solver output tables), see [Mathematical Formulation](formulation.md).

## 1) Understand the input files

The scheduler expects three inputs.

### Faculty catalog (`faculty_formulation.yaml`)

- Defines each faculty member's building, room, research areas, and status.
- Example statuses: `active`, `legacy`, `external`.

### Run config (`config_formulation.yaml`)

- Defines slot times for two buildings.
- Uses building names `ABC` and `XYZ`.
- Defines break slots (`breaks: [2, 3]` in this example).
- Defines three topic areas: `Energy`, `Bio`, `Theory`.
- Includes per-faculty availability conflicts.

### Visitor CSV (`data_formulation_visitors.csv`)

- One row per visitor.
- Ranked faculty preferences in `Prof1`, `Prof2`, ...
- Topic areas in `Area1`, `Area2`.

## 2) Build and solve

```python
from pathlib import Path
from grad_visit_scheduler import scheduler_from_configs, Mode, Solver

root = Path("examples")

s = scheduler_from_configs(
    root / "faculty_formulation.yaml",
    root / "config_formulation.yaml",
    root / "data_formulation_visitors.csv",
    mode=Mode.NO_OFFSET,
    solver=Solver.HIGHS,
)

s.schedule_visitors(
    group_penalty=0.2,
    min_visitors=2,
    max_visitors=8,
    min_faculty=1,
    max_group=2,
    enforce_breaks=True,
    tee=False,
    run_name="formulation_demo",
)

if s.has_feasible_solution():
    s.show_faculty_schedule(save_files=True)
    s.show_visitor_schedule(save_files=True)
else:
    print(s.infeasibility_report())
```

## 3) Key solver options

Common options on `schedule_visitors(...)`:

- `group_penalty`: penalizes multi-visitor meetings.
- `min_visitors` / `max_visitors`: faculty-level load bounds.
- `min_faculty`: minimum meetings required per visitor.
- `max_group`: cap on simultaneous visitors in one faculty meeting.
- `enforce_breaks`: enforce break-window constraints.
- `tee`: print solver output for debugging.

## 4) Inspect and export solutions

Generate a DOCX schedule:

```python
from grad_visit_scheduler import export_visitor_docx

export_visitor_docx(s, "visitor_schedule.docx")
```

Optional diagnostics:

```python
if s.has_feasible_solution():
    s.check_requests()
else:
    print(s.infeasibility_report())
```

Repository script for this same workflow:

```bash
python scripts/run_formulation_example.py
```
