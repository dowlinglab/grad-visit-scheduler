# Building Movement and Staggered Starts

This page documents the movement interface in run configs (`movement:`) and shows
one standardized comparison across all examples.

All scenarios here use:

- `examples/data_formulation_visitors.csv`
- A faculty catalog matching the number of buildings in the scenario

## Movement Configuration

```yaml
movement:
  policy: none          # or travel_time / nonoverlap_time
  phase_slot:
    BuildingA: 1
    BuildingB: 1
  travel_slots:         # used for policy: travel_time (or "auto")
    BuildingA:
      BuildingA: 0
      BuildingB: 1
    BuildingB:
      BuildingA: 1
      BuildingB: 0
```

- `policy: none`: no explicit inter-building travel-time constraints.
- `policy: travel_time`: explicit pairwise slot lag constraints from `travel_slots`.
- `policy: nonoverlap_time`: auto-derive lag constraints from absolute slot timestamps.
- `phase_slot`: earliest slot allowed for each building (supports staggered starts).
- `travel_slots: auto`: allowed with `policy: travel_time`.
- `min_buffer_minutes`: optional nonnegative buffer for auto-derived lags.

## Examples for Different Building Configurations

Run every scenario and regenerate all movement figures:

```bash
python scripts/run_building_configuration_examples.py
```

This command prints one unified comparison table and writes scenario plots to
`docs/_static/movement_<slug>_{visitor,faculty}.png`.

| Category | Scenario | Policy | Feasible | Objective | Assignments | Requested Assignments | Group Slots |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| Baseline | One building (no movement) | `none` | True | 110.9 | 30 | 30 | 13 |
| Baseline | Two buildings (close, policy=none) | `none` | True | 110.9 | 30 | 30 | 13 |
| Baseline | Three buildings (close, policy=none) | `none` | True | 110.9 | 30 | 30 | 13 |
| Travel lag | Two buildings (+1 slot travel lag) | `travel_time` | True | 110.9 | 30 | 30 | 13 |
| Travel lag | Three buildings (+1 slot travel lag) | `travel_time` | True | 103.7 | 28 | 25 | 12 |
| Shifted clocks | Shifted clocks (ABC starts 15 min earlier) | `nonoverlap_time` | True | 110.9 | 30 | 30 | 13 |
| Shifted clocks | Shifted clocks (XYZ starts 15 min earlier) | `nonoverlap_time` | True | 110.9 | 30 | 30 | 13 |
| Phase slot | Staggered start (ABC first) | `none` | True | 101.8 | 26 | 26 | 11 |
| Phase slot | Staggered start (XYZ first) | `none` | True | 94.9 | 24 | 23 | 9 |

Interpretation of the close-building equivalence:

- In this dataset, one-building, two-close-building, three-close-building, and two-building `travel_time` (+1 lag) all attain the same optimum.
- Practically, that means the added movement constraints are non-binding for this particular demand/availability profile.
- The three-building +1 lag case is stricter (more inter-building transition edges), so objective and assignments decrease.

Here are the files used in these examples.

| Slug | Config | Faculty Catalog |
| --- | --- | --- |
| `one_building` | `examples/config_one_building.yaml` | `examples/faculty_one_building.yaml` |
| `two_close_none` | `examples/config_two_buildings_close.yaml` | `examples/faculty_formulation.yaml` |
| `three_close_none` | `examples/config_three_buildings_close.yaml` | `examples/faculty_three_buildings.yaml` |
| `two_travel_lag1` | `examples/config_two_buildings_travel_delay.yaml` | `examples/faculty_formulation.yaml` |
| `three_travel_lag1` | `examples/config_three_buildings_travel_delay.yaml` | `examples/faculty_three_buildings.yaml` |
| `shifted_abc_earlier_nonoverlap` | `examples/config_shifted_abc_earlier_nonoverlap.yaml` | `examples/faculty_formulation.yaml` |
| `shifted_xyz_earlier_nonoverlap` | `examples/config_shifted_xyz_earlier_nonoverlap.yaml` | `examples/faculty_formulation.yaml` |
| `staggered_a_first` | `examples/config_shifted_a_first.yaml` | `examples/faculty_formulation.yaml` |
| `staggered_b_first` | `examples/config_shifted_b_first.yaml` | `examples/faculty_formulation.yaml` |


### Example 1: One building (no movement)

TODO: Add a sentence summarizing this example.

Configuration:

- `examples/config_one_building.yaml`
- `examples/faculty_one_building.yaml`

Result summary: feasible, objective `110.9`, assignments `30`, requested assignments `30`, group slots `13`.

![One Building Visitor View](_static/movement_one_building_visitor.png)
![One Building Faculty View](_static/movement_one_building_faculty.png)



### Example 2: Two nearby buildings

TODO: Add a sentence summarizing this example.

Configuration:

- `examples/config_two_buildings_close.yaml`
- `examples/faculty_formulation.yaml`

Result summary: feasible, objective `110.9`, assignments `30`, requested assignments `30`, group slots `13`.

![Two Close Buildings Visitor View](_static/movement_two_close_none_visitor.png)
![Two Close Buildings Faculty View](_static/movement_two_close_none_faculty.png)

### Example 3: Three nearby buildings

TODO: Add a sentence summarizing this example.


Configuration:

- `examples/config_three_buildings_close.yaml`
- `examples/faculty_three_buildings.yaml`

Result summary: feasible, objective `110.9`, assignments `30`, requested assignments `30`, group slots `13`.

![Three Close Buildings Visitor View](_static/movement_three_close_none_visitor.png)
![Three Close Buildings Faculty View](_static/movement_three_close_none_faculty.png)

### Example 4: Two buildings with one-slot travel delays

TODO: Add a sentence summarizing this example.


Configuration:

- `examples/config_two_buildings_travel_delay.yaml`
- `examples/faculty_formulation.yaml`

Result summary: feasible, objective `110.9`, assignments `30`, requested assignments `30`, group slots `13`.

![Two Buildings Travel Lag Visitor View](_static/movement_two_travel_lag1_visitor.png)
![Two Buildings Travel Lag Faculty View](_static/movement_two_travel_lag1_faculty.png)

### Example 5: Three buildings with one-slot travel delays

TODO: Add a sentence summarizing this example.


Configuration:

- `examples/config_three_buildings_travel_delay.yaml`
- `examples/faculty_three_buildings.yaml`

Result summary: feasible, objective `103.7`, assignments `28`, requested assignments `25`, group slots `12`.

![Three Buildings Travel Lag Visitor View](_static/movement_three_travel_lag1_visitor.png)
![Three Buildings Travel Lag Faculty View](_static/movement_three_travel_lag1_faculty.png)

### Example 6: Shifted clocks, building ABC starts 15 minutes earlier

TODO: Add a sentence summarizing this example.


Configuration:

- `examples/config_shifted_abc_earlier_nonoverlap.yaml`
- `examples/faculty_formulation.yaml`

Result summary: feasible, objective `110.9`, assignments `30`, requested assignments `30`, group slots `13`.

Why this addresses cross-building movement without explicit break slots:

- `nonoverlap_time` derives travel lags from absolute timestamps.
- Adjacent-slot transitions are allowed when the destination slot starts after the source slot ends.
- That lets the model permit valid moves directly from one meeting to the next when timing permits.

![ABC Earlier Shifted Visitor View](_static/movement_shifted_abc_earlier_nonoverlap_visitor.png)
![ABC Earlier Shifted Faculty View](_static/movement_shifted_abc_earlier_nonoverlap_faculty.png)

### Example 7: Shifted clocks, building XYZ starts 15 minutes earlier

TODO: Add a sentence summarizing this example.


Configuration:

- `examples/config_shifted_xyz_earlier_nonoverlap.yaml`
- `examples/faculty_formulation.yaml`

Result summary: feasible, objective `110.9`, assignments `30`, requested assignments `30`, group slots `13`.

![XYZ Earlier Shifted Visitor View](_static/movement_shifted_xyz_earlier_nonoverlap_visitor.png)
![XYZ Earlier Shifted Faculty View](_static/movement_shifted_xyz_earlier_nonoverlap_faculty.png)

### Example 8: Synced clocks, building ABC starts first

TODO: Add a sentence summarizing this example and why it would be used, e.g., visitors are already in building ABC.

Configuration:

- `examples/config_shifted_a_first.yaml`
- `examples/faculty_formulation.yaml`

Result summary: feasible, objective `101.8`, assignments `26`, requested assignments `26`, group slots `11`.

![Staggered ABC First Visitor View](_static/movement_staggered_a_first_visitor.png)
![Staggered ABC First Faculty View](_static/movement_staggered_a_first_faculty.png)

###  Example 9: Synced clocks, building XYZ starts first

TODO: Add a sentence summarizing this example.


Configuration:

- `examples/config_shifted_b_first.yaml`
- `examples/faculty_formulation.yaml`

Result summary: feasible, objective `94.9`, assignments `24`, requested assignments `23`, group slots `9`.

![Staggered XYZ First Visitor View](_static/movement_staggered_b_first_visitor.png)
![Staggered XYZ First Faculty View](_static/movement_staggered_b_first_faculty.png)

###  Example 10: Three buildings with shifted clocks

TODO: Need to create a new example. Let's assume meetings are 25 minutes with a 5 minute travel break. The three buildings are approximately 6 minutes apart, thus the 5 minute travel window is not sufficient. Instead, the building time grids will be offset by 10 minutes. For example, build ABC could start at 1:00pm, IJK starts at 1:10pm, and XYZ starts at 1:20pm.


## Legacy Mode Mappings

Legacy modes are still available with `FutureWarning` and map to movement configs:

- `Mode.BUILDING_A_FIRST` maps to `policy: none` with `phase_slot` offset (`ABC:1`, `XYZ:2`).
- `Mode.BUILDING_B_FIRST` maps to `policy: none` with `phase_slot` offset (`ABC:2`, `XYZ:1`).
- `Mode.NO_OFFSET` maps to `policy: travel_time` with a +1 inter-building lag matrix.

Break nuance:

- Legacy `Mode.NO_OFFSET` implicitly enforces break constraints by default.
- Movement-only configs do not imply breaks; set `enforce_breaks=True` if needed.
