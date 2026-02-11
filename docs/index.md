# Graduate Visitor Scheduler

Mixed integer optimization-based scheduler for visitor-faculty meetings at department recruitment events.

## Motivation

Many graduate programs host recruitment visits where prospective students meet faculty one-on-one or in small groups. Building schedules by hand is difficult because preferences, availability, group limits, room/building constraints, and break/travel windows all interact.

This project packages the scheduling workflow used for graduate recruitment at Notre Dame CBE as an open-source Python tool. Under the hood, it builds and solves a mixed-integer linear program (MILP) in Pyomo.

## Workflow

The scheduler takes three input files:

- Faculty catalog YAML (faculty metadata, areas, status, building/room).
- Run configuration YAML (building slots, break slots, availability constraints, weights).
- Visitor preferences CSV (ranked faculty choices and research area interests).

Outputs include:

- Optimized visitor-faculty assignments.
- Faculty-view and visitor-view schedule plots.
- Optional DOCX exports of individualized visitor schedules.

## Large Example Results

The documentation includes a realistic worked example with 10 visitors, 6 faculty, two buildings (`ABC` and `XYZ`), topic areas (`Energy`, `Bio`, `Theory`), and faculty scheduling conflicts.

Visitor-centered schedule:

![Visitor Schedule Example](_static/visitor_schedule_example.png)

Faculty-centered schedule:

![Faculty Schedule Example](_static/faculty_schedule_example.png)

Full setup, model details, and solver outputs are documented in [Quickstart](quickstart.md) and [Mathematical Formulation](formulation.md).

```{toctree}
:maxdepth: 2
:caption: Contents

installation
quickstart
api
formulation
```
