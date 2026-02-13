# Graduate Visit Scheduler

[![Docs Latest](https://img.shields.io/badge/docs-latest-2E86C1?logo=readthedocs&logoColor=white)](https://grad-visit-scheduler.readthedocs.io/en/latest/)
[![Docs Stable](https://img.shields.io/badge/docs-stable-2EA043?logo=readthedocs&logoColor=white)](https://grad-visit-scheduler.readthedocs.io/en/stable/)
[![CI](https://github.com/dowlinglab/grad-visit-scheduler/actions/workflows/ci.yml/badge.svg)](https://github.com/dowlinglab/grad-visit-scheduler/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/dowlinglab/grad-visit-scheduler/graph/badge.svg)](https://codecov.io/gh/dowlinglab/grad-visit-scheduler)
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

## CI and Coverage

GitHub Actions runs the test suite on pushes to `main` and on pull requests
targeting `main`. Coverage is uploaded to Codecov from the Python 3.11 job.
For this public repository, coverage upload uses GitHub OIDC (no
`CODECOV_TOKEN` secret required).

## Automated PyPI Releases

Releases are tag-driven via GitHub Actions:

- Push a semantic version tag like `v0.2.0`.
- Workflow `.github/workflows/release.yml` runs tests, builds `sdist`/wheel, and checks package metadata.
- Package is published to **TestPyPI** first.
- CI performs a smoke install of that exact tagged version from TestPyPI.
- If smoke install passes, CI publishes the same artifact to **PyPI**.

Publishing uses PyPI Trusted Publishing (OIDC), so no API token secret is required.
Configure both PyPI and TestPyPI trusted publishers to point to this repository
and the `release.yml` workflow file.
Detailed release instructions are in [`docs/releasing.md`](docs/releasing.md).

Manual release workflow runs are also supported (`workflow_dispatch`):

- `target=testpypi`: build, publish to TestPyPI, smoke install, stop.
- `target=pypi`: run the full pipeline (TestPyPI + smoke + PyPI publish).
- Optional `version` input lets smoke install pin a specific version.

## Quickstart

```python
from pathlib import Path
from grad_visit_scheduler import scheduler_from_configs, Solver

root = Path("examples")

s = scheduler_from_configs(
    root / "faculty_formulation.yaml",
    root / "config_two_buildings_close.yaml",
    root / "data_formulation_visitors.csv",
    solver=Solver.HIGHS,
)

sol = s.schedule_visitors(
    group_penalty=0.2,
    min_visitors=2,
    max_visitors=8,
    min_faculty=1,
    max_group=2,
    enforce_breaks=True,
    tee=False,
    run_name="demo",
)

if sol is not None:
    sol.plot_visitor_schedule(save_files=True, show_solution_rank=False)
    sol.plot_faculty_schedule(save_files=True, show_solution_rank=False)
    sol.export_visitor_docx("visitor_schedule.docx")
else:
    print(s.infeasibility_report())
```

Note: the `examples/` folder referenced above is included in the repository,
but it is not packaged on PyPI. If you installed from PyPI, clone the repo
to access the example files.

## Buildings and Movement

Notre Dame CBE is split across two buildings (Nieuwland Science Hall and McCourtney Hall) separated by about a 7-minute walk. A key aspect of the scheduler is to ensure that any visitor who needs to move buildings does so during their break slot. A typical schedule uses six meeting slots, and each visitor and faculty member gets at least one middle-slot break.

The run config now supports one, two, or many buildings. `building_order` controls plotting/export ordering. Movement behavior is configured with the `movement` section:

- `movement.policy: none`: close-proximity buildings; no explicit travel-time constraints.
- `movement.policy: travel_time`: explicit inter-building travel-time lag constraints.
- `movement.phase_slot`: earliest slot allowed by building (for staggered starts like Building A first vs Building B first).

Legacy `Mode.*` options are still available with `FutureWarning`.

See [`docs/movement.md`](docs/movement.md) and `scripts/run_shifted_start_comparison.py` for full examples.
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

To generate multiple ranked schedules, use no-good cuts:

```python
top = s.schedule_visitors_top_n(n_solutions=3, enforce_breaks=True)
report = top.summarize(ranks_to_plot=(1, 2), show_solution_rank=True)
print(report["summary"])
print(report["compact"])
```

## Export DOCX

Preferred modern path:

```python
sol = s.schedule_visitors(...)
if sol is not None:
    sol.export_visitor_docx("visitor_schedule.docx")
```

Legacy helper `grad_visit_scheduler.export_visitor_docx(...)` remains available
for compatibility but emits `FutureWarning`.

## License

This software is released under the BSD-3-Clause license. Please adapt it to your needs and share.
