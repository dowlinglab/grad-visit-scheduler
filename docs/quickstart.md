# Quickstart

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/dowlinglab/grad-visit-scheduler/blob/main/examples/large_example_colab.ipynb)

This quickstart uses the larger formulation example:

- `examples/faculty_formulation.yaml` (6 faculty: `Prof. A` to `Prof. F`)
- `examples/config_formulation.yaml` (4 meeting slots across buildings `ABC` and `XYZ`)
- `examples/data_formulation_visitors.csv` (10 visitors)

For a detailed explanation of this same example (model equations, conflicts, preferences, and solver output tables), see [Mathematical Formulation](formulation.md). For movement policy and staggered starts, see [Building Movement and Staggered Starts](movement.md).

## 1) Understand the input files

The scheduler expects three inputs.

### Faculty catalog (`faculty_formulation.yaml`)

TODO: Please show the yaml file contents here. Is there a clever way to embed the file contents without just repeating it? I want to make it easier to keep the docs up to date.

- Defines each faculty member's building, room, research areas, and status.
- Example statuses: `active`, `legacy`, `external`.

### Run config (`config_formulation.yaml`)

TODO: Let's shown the yaml file here. See the comment above.

- Defines slot times for two buildings.
- Uses building names `ABC` and `XYZ`.
- Defines break slots (`breaks: [2, 3]` in this example).
- Defines three topic areas: `Energy`, `Bio`, `Theory`.
- Includes per-faculty availability conflicts.

### Visitor CSV (`data_formulation_visitors.csv`)

TODO: Please show an excerpt of the file. Is there an easy way to do this that keeps the documentation up to date?

- One row per visitor.
- Ranked faculty preferences in `Prof1`, `Prof2`, ...
- Topic areas in `Area1`, `Area2`.

## 2) Build and solve

```python
from pathlib import Path
from grad_visit_scheduler import scheduler_from_configs, Solver

root = Path("examples")

s = scheduler_from_configs(
    root / "faculty_formulation.yaml",
    root / "config_formulation.yaml",
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
    run_name="formulation_demo",
)

if sol is not None:
    sol.plot_faculty_schedule(save_files=True, show_solution_rank=False)
    sol.plot_visitor_schedule(save_files=True, show_solution_rank=False)
    sol.export_visitor_docx("visitor_schedule.docx")
else:
    print(s.infeasibility_report())
```

The Top-N workflow in section 5 uses the preferred modern `SolutionSet` /
`SolutionResult` interface for ranked schedules.

## 3) Key solver options

Common options on `schedule_visitors(...)`:

- `group_penalty`: penalizes multi-visitor meetings.
- `min_visitors` / `max_visitors`: faculty-level load bounds.
- `min_faculty`: minimum meetings required per visitor.
- `max_group`: cap on simultaneous visitors in one faculty meeting.
- `enforce_breaks`: enforce break-window constraints.
- `tee`: print solver output for debugging.

## 4) Inspect and export solutions

Schedule plots from this example:

TODO: Please make sure these are up to date.

![Visitor Schedule Example](_static/visitor_schedule_example.png)

![Faculty Schedule Example](_static/faculty_schedule_example.png)

How to interpret these plots:

- `ABC` and `XYZ` are building abbreviations from `config_formulation.yaml`. The box color (blue versus green) also indicates the building.
- Visitor-view bars are labeled `Faculty (Building)`. Missing blocks indicate breaks/travel slots.
- In the faculty-view y-axis labels, the number in parentheses is each faculty member's total scheduled meetings. Missing blocks indicate faculty conflict. Blocks without a visitor name indicate a break (unused meeting).

Preferred DOCX export path:

```python
if sol is not None:
    sol.export_visitor_docx("visitor_schedule.docx")
```

Legacy helper note: `grad_visit_scheduler.export_visitor_docx(...)` is still
available for compatibility and emits `FutureWarning`.

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

## 5) Generate Top-N Unique Solutions (No-Good Cuts)

Use `schedule_visitors_top_n(...)` to generate multiple ranked schedules.
Each additional solution is forced to differ by at least one assignment.
For the exact no-good-cut equation used in the model, see
[Mathematical Formulation](formulation.md) ("Top-N No-Good Cuts" section).

```python
top = s.schedule_visitors_top_n(
    n_solutions=3,
    group_penalty=0.2,
    min_visitors=2,
    max_visitors=8,
    min_faculty=1,
    max_group=2,
    enforce_breaks=True,
    tee=False,
    run_name="formulation_top_n",
)

report = top.summarize(
    ranks_to_plot=(1, 2),
    save_files=True,
    show_solution_rank=True,  # turn off for external-facing plots
    plot_prefix="formulation_top_n",
)

summary = report["summary"]
compact = report["compact"]
print(summary)
print(compact)

if len(top) > 0:
    top.export_visitor_docx("visitor_schedule_rank1.docx", rank=1)
```

Developer note: if `n_solutions` exceeds the number of unique feasible
schedules, `top` contains all feasible unique schedules found, and the
`Scheduler` object remains at the last feasible loaded solution state.

Repository script for this workflow:

```bash
python scripts/run_top_n_example.py
```

## 6) Staggered Building Starts (A First vs B First)

Use `movement.phase_slot` in run configs to compare staggered starts.
Repository examples:

- `examples/config_shifted_a_first.yaml`
- `examples/config_shifted_b_first.yaml`
- `examples/faculty_formulation.yaml`
- `examples/data_formulation_visitors.csv`

Comparison runner:

```bash
python scripts/run_shifted_start_comparison.py
```

For full movement-policy details (one/two/three-building cases and travel-time
constraints), plus visual example outputs and result tables, see
[Building Movement and Staggered Starts](movement.md).

For shifted-clock schedules where you want automatic overlap protection, see:

- `examples/config_shifted_nonoverlap_auto.yaml`
