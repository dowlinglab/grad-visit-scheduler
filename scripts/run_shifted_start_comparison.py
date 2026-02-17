"""Compatibility wrapper for staggered-start scenarios."""

from __future__ import annotations

from run_building_configuration_examples import run


def main():
    df = run(selected_slugs=["staggered_a_first", "staggered_b_first"])
    columns = [
        "category",
        "scenario",
        "policy",
        "feasible",
        "objective",
        "assignments",
        "requested_assignments",
        "group_slots",
    ]
    print(df[columns].to_string(index=False))


if __name__ == "__main__":
    main()
