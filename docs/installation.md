# Installation

## Install package

```bash
pip install grad-visitor-scheduler
```

## Solver setup

- HiGHS is installed by default via the `highspy` dependency.
- To use CBC, install the solver binary with conda:

```bash
conda install -c conda-forge coincbc
```

## Optional solver tests

Some tests are solver-optional (`tests/test_solver_optional.py`) and will
automatically skip if a backend is not installed. For example, CBC-specific
checks are skipped unless `coincbc` is available in the active environment.

## Optional local docs build

From the repository root:

```bash
pip install -e .
pip install -r docs/requirements.txt
sphinx-build -b html docs docs/_build/html
```
