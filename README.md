# Grad Visitor Scheduler

MILP-based scheduling utilities for graduate visit days.

This repository contains only public code and example data. It does not include any Notre Dame-specific data.

## Install

```bash
pip install grad-visitor-scheduler
```

Solver setup:

- HiGHS is installed by default via the `highspy` dependency.
- To use CBC, install the solver binary with conda:

```bash
conda install -c conda-forge coincbc
```

## Quickstart

```python
from pathlib import Path
from grad_visit_scheduler import scheduler_from_configs, Mode, Solver

root = Path("examples")

s = scheduler_from_configs(
    root / "faculty_example.yaml",
    root / "config_basic.yaml",
    root / "data_fake_visitors.csv",
    mode=Mode.NO_OFFSET,
    solver=Solver.HIGHS,
)

s.schedule_visitors(
    group_penalty=0.1,
    min_visitors=0,
    max_visitors=4,
    min_faculty=1,
    max_group=2,
    enforce_breaks=True,
    tee=False,
    run_name="demo",
)

if s.has_feasible_solution():
    s.show_visitor_schedule(save_files=True)
```

Note: the `examples/` folder referenced above is included in the repository,
but it is not packaged on PyPI. If you installed from PyPI, clone the repo
to access the example files.

## Buildings

The run config defines exactly two buildings, and `building_order` declares
which one is Building A vs Building B. Mode controls how movement between
buildings is constrained:

- `Mode.BUILDING_A_FIRST`: visitor starts in Building A, then may move to B
- `Mode.BUILDING_B_FIRST`: visitor starts in Building B, then may move to A
- `Mode.NO_OFFSET`: visitor may move either direction, but only with an empty slot

## Export DOCX

```python
from grad_visit_scheduler import export_visitor_docx

export_visitor_docx(s, "visitor_schedule.docx")
```

## License

BSD-3-Clause
