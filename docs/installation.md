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

## Optional local docs build

From the repository root:

```bash
pip install -e .
pip install -r docs/requirements.txt
sphinx-build -b html docs docs/_build/html
```
