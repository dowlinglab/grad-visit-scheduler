# Grad Visitor Scheduler

[![Docs (latest)](https://readthedocs.org/projects/grad-visit-scheduler/badge/?version=latest)](https://grad-visit-scheduler.readthedocs.io/en/latest/)
[![Docs (stable)](https://readthedocs.org/projects/grad-visit-scheduler/badge/?version=stable)](https://grad-visit-scheduler.readthedocs.io/en/stable/)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/dowlinglab/grad-visit-scheduler/blob/main/examples/large_example_colab.ipynb)

MILP-based scheduling utilities for graduate visit days. Created by [Alex Dowling](https://engineering.nd.edu/faculty/alexander-dowling/) and [Jeff Kantor](https://engineering.nd.edu/news/in-memoriam-jeffrey-kantor-former-vice-president-associate-provost-and-dean/) at the University of Notre Dame.

## Motivation

Most chemical engineering graduate programs in the U.S. host admitted or prospective students for a visit or open house. A core part of those events is one-on-one or small-group meetings with individual faculty members. Building a fair, feasible schedule is challenging: faculty availability, room locations, and student preferences must all be respected simultaneously.

This package is the meeting scheduler used by [Notre Dame Chemical and Biomolecular Engineering](https://cbe.nd.edu), released as a general-purpose, open-source tool. Under the hood, it formulates a mixed-integer linear program (MILP) in Pyomo, solves it with a standard solver, visualizes the results, and can export customized student schedules to DOCX.

## Data Gathering

Each visitor is asked to rank up to four faculty members for meetings and to choose up to two topic areas within the department. Likewise, faculty are asked to provide any afternoon meeting conflicts. This information is used to generate three key input files:

- A faculty catalog YAML file (names, buildings, rooms, areas, status, and optional aliases).
- A run configuration YAML file (time slots by building, breaks, area weights, and any faculty availability constraints).
- A visitor preferences CSV file.

Research areas are department-specific. In the included example data, they are represented as simple labels such as `Area1` and `Area2`, but you can define any set of areas in your faculty catalog.

## What It Produces

- An optimal assignment of visitors to faculty across time slots.
- Visual summaries (plots) of the resulting schedule.
- Optional DOCX exports with individualized visitor schedules.

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

Notre Dame CBE is split across two buildings (Nieuwland Science Hall and McCourtney Hall) separated by about a 7-minute walk. A key aspect of the scheduler is to ensure that any visitor who needs to move buildings does so during their break slot. A typical schedule uses six meeting slots, and each visitor and faculty member gets at least one middle-slot break.

The run config defines exactly two buildings, and `building_order` declares which one is Building A versus Building B. Mode controls how movement between buildings is constrained:

- `Mode.BUILDING_A_FIRST`: visitor starts in Building A, then may move to B
- `Mode.BUILDING_B_FIRST`: visitor starts in Building B, then may move to A
- `Mode.NO_OFFSET`: visitor may move either direction, but only with an empty slot

## Refine the Schedule

The solver exposes several tunable parameters on `schedule_visitors` to refine the schedule:

- `group_penalty`: penalize group meetings to bias toward one-on-one meetings; higher values discourage multi-visitor meetings.
- `min_visitors`: minimum number of visitors each available faculty member must meet.
- `max_visitors`: maximum number of visitors each faculty member may meet.
- `min_faculty`: minimum number of faculty each visitor must meet.
- `max_group`: maximum size of a meeting group at any time slot.
- `enforce_breaks`: force breaks for visitors and faculty during the configured break window.
- `tee`: print solver output for debugging.
- `run_name`: label used when saving plots/exports.

## Export DOCX

You can optionally export customized visitor schedules to a DOCX file. This facilitates easy copy/paste into individualized agendas for each visitor.

```python
from grad_visit_scheduler import export_visitor_docx

export_visitor_docx(s, "visitor_schedule.docx")
```

## License

This software is released under the BSD-3-Clause license. Please adapt it to your needs and share.
