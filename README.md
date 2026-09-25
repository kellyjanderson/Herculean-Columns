# Herculean Columns

Herculean Columns is a typed Python research package for planning sparse,
grounded structural infill. This slice establishes graph correctness; mesh
booleans, watertight solid export, slicing, and physical claims are deliberately
deferred.

The historical `herculean_columns.py` v0.2 prototype remains unchanged for
reference. The supported migration entry point is now:

```bash
.venv/bin/herculean-columns --help
```

## Reproducible local environment

Python 3.12 or newer is required. Dependencies and developer tools are pinned
in `pyproject.toml`; the environment is local and ignored by Git.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
```

Run each required check independently:

```bash
.venv/bin/python -m pytest -m unit
.venv/bin/python -m pytest -m regression
.venv/bin/python -m mypy src
```

Run the complete suite with `.venv/bin/python -m pytest`. Configuration uses
millimetres, cubic millimetres, and percent. `infill_percent` is required and
controls Herculean planning independently of any downstream slicer setting.

## Result contract

`HerculeanGenerator.generate()` returns a `GenerationResult`. On success it
contains a validated graph and deterministic density report. On failure its
graph is absent and structured diagnostics explain which invariant failed.
Callers must not forward a failed result to materialization.

Current authority remains the [v0.3 architecture](project/architecture/herculean-columns-v0.3.md)
and [printable-solid plan](project/planning/printable-solid-implementation-plan.md).
