Examples live here. Suggested workflow:

- Copy and adjust a run config from this folder.
- Point to a visitor CSV (recommended: `examples/data_formulation_visitors.csv`).
- Build a `Scheduler` with `scheduler_from_configs` and run.

Minimal example:

```python
from grad_visit_scheduler import scheduler_from_configs, Solver

s = scheduler_from_configs(
    "examples/faculty_formulation.yaml",
    "examples/config_two_buildings_close.yaml",
    "examples/data_formulation_visitors.csv",
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
    run_name="demo",
)

if s.has_feasible_solution():
    s.show_visitor_schedule(save_files=True)
```

Notes:
- `movement.policy: none` disables explicit travel-time constraints.
- `movement.policy: travel_time` enables pairwise lag constraints via `movement.travel_slots`.
- Use `movement.phase_slot` to configure staggered starts (for example, Building A first).

Movement/staggered example configs:

- `config_one_building.yaml`: one-building schedule on the large formulation visitor set.
- `config_two_buildings_close.yaml`: two close buildings, no travel-time constraints.
- `config_three_buildings_close.yaml`: three close buildings, no travel-time constraints.
- `config_shifted_a_first.yaml`: staggered starts with Building A first.
- `config_shifted_b_first.yaml`: staggered starts with Building B first.

Companion faculty catalogs for generalized building demos:

- `faculty_one_building.yaml`: same six formulation faculty in one building.
- `faculty_three_buildings.yaml`: same six formulation faculty distributed across three buildings.

Movement/staggered example scripts:

- `../scripts/run_example.py`: two-building close-proximity solve.
- `../scripts/run_building_configuration_examples.py`: one/two/three-building close-proximity comparison on the large dataset.
- `../scripts/run_shifted_start_comparison.py`: A-first vs B-first performance comparison and plots.

Formulation-focused base dataset:
- `faculty_formulation.yaml`: six-faculty catalog (`Prof. A` to `Prof. F`).
- `data_formulation_visitors.csv`: ten visitors with ranked faculty preferences plus topic interests (`Energy`, `Bio`, `Theory`).
- `config_formulation.yaml`: baseline travel-time run config for the same dataset.

Top-N example script:
- `../scripts/run_top_n_example.py`: solves for the best three unique schedules using no-good cuts and writes rank-specific outputs.
- Uses `SolutionSet.summarize(...)` to build summary tables and standardized rank-plot outputs.
