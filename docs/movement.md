# Building Movement and Staggered Starts

This page documents the new movement interface in the run config (`movement:`),
which generalizes scheduling across one, two, or many buildings.

All examples on this page use the larger formulation visitor dataset:

- `examples/data_formulation_visitors.csv`
- `examples/faculty_formulation.yaml` (or building-variant catalogs derived from it)

## Movement Configuration

Add a `movement` block to your run config:

```yaml
movement:
  policy: none          # or travel_time
  phase_slot:
    BuildingA: 1
    BuildingB: 1
  travel_slots:         # only used for policy: travel_time
    BuildingA:
      BuildingA: 0
      BuildingB: 1
    BuildingB:
      BuildingA: 1
      BuildingB: 0
```

- `policy: none`: buildings are treated as close-proximity; no explicit travel-time constraints.
- `policy: travel_time`: enforces pairwise building-to-building lag constraints using `travel_slots`.
- `phase_slot`: earliest slot each building is allowed to host meetings. This enables staggered starts.

## Supported Patterns

### 1) One building

Use a single building in `buildings:` with `policy: none`.

- Example config: `examples/config_one_building.yaml`
- Example faculty catalog: `examples/faculty_one_building.yaml`
- Visitor data: `examples/data_formulation_visitors.csv`

### 2) Two close buildings (no travel-time constraints)

Use two buildings with `policy: none` and both phase slots set to `1`.

- Example config: `examples/config_two_buildings_close.yaml`
- Faculty catalog: `examples/faculty_formulation.yaml`
- Visitor data: `examples/data_formulation_visitors.csv`

### 3) Three or more close buildings (no travel-time constraints)

Use `policy: none` with one `phase_slot` entry per building.

- Example config: `examples/config_three_buildings_close.yaml`
- Example faculty catalog: `examples/faculty_three_buildings.yaml`
- Visitor data: `examples/data_formulation_visitors.csv`

## Staggered Starts (A First vs B First)

Staggered starts are now represented through `phase_slot`.

- Building A first:

```yaml
movement:
  policy: none
  phase_slot:
    BuildingA: 1
    BuildingB: 2
```

- Building B first:

```yaml
movement:
  policy: none
  phase_slot:
    BuildingA: 2
    BuildingB: 1
```

Repository configs:

- `examples/config_shifted_a_first.yaml`
- `examples/config_shifted_b_first.yaml`

Comparison runner:

```bash
python scripts/run_shifted_start_comparison.py
```

This script solves both scenarios and prints a side-by-side table of objective
value and key schedule metrics, then writes both visitor and faculty plots.

The script uses:

- `examples/faculty_formulation.yaml`
- `examples/data_formulation_visitors.csv`
- `examples/config_shifted_a_first.yaml`
- `examples/config_shifted_b_first.yaml`

## Executable Comparison Across 1/2/3 Buildings

Run all close-proximity building-configuration examples (one, two, and three buildings)
on the large formulation dataset:

```bash
python scripts/run_building_configuration_examples.py
```

This prints a side-by-side summary table with objective and assignment metrics.

## Visualization

Example schedule visualizations (visitor and faculty perspectives):

![Visitor Schedule Example](_static/visitor_schedule_example.png)

![Faculty Schedule Example](_static/faculty_schedule_example.png)

Use `show_solution_rank=False` when generating external-facing schedules.

## Legacy Mode Compatibility

`mode=Mode.BUILDING_A_FIRST`, `mode=Mode.BUILDING_B_FIRST`, and
`mode=Mode.NO_OFFSET` remain available with `FutureWarning`, but `movement` is
the preferred interface for new code.
