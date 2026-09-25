---
schema_version: 1
id: HC-PS-020
title: Materialize valid Herculean graphs as watertight printable solids
project: kellyjanderson/Herculean-Columns
base: main
branch: feature/HC-PS-020-solid-materialization
scope:
  owns:
    - pyproject.toml
    - src/herculean_columns/__init__.py
    - src/herculean_columns/cli.py
    - src/herculean_columns/geometry/**
    - src/herculean_columns/materialize/**
    - src/herculean_columns/export/**
    - src/herculean_columns/config.py
    - tests/geometry/**
    - tests/materialize/**
    - tests/export/**
    - tests/fixtures/basic/**
    - project/decisions/**
  may_read:
    - src/herculean_columns/**
    - tests/unit/**
    - tests/regression/**
    - project/architecture/**
dependencies: [HC-PS-010]
completion:
  delivery: pull_request
  merge: agent
  required_checks: [unit, geometry, export, typecheck]
---

# Context

Architecture v0.3 makes a normal watertight composite model the first slicer
boundary. The exterior must remain equivalent to the admitted source while the
interior contains a clipped, connected, bead-scale realization of the valid
Herculean graph. The source asset must remain immutable.

# Outcome

A Python API and CLI accept a supported watertight source mesh plus Herculean
configuration and produce a separately named, previewable, manifold STL. They
also produce 3MF when the selected maintained package preserves geometry,
units, and provenance reliably. A machine-readable report binds the output to
the source, graph, configuration, tool versions, and validation evidence.

# Required work

- Evaluate maintained mesh IO and robust boolean packages before writing custom
  geometry machinery. Prefer thin adapters around `trimesh`, `manifold3d`, or
  another evidenced package; record accepted and rejected options.
- Admit source units, watertightness, winding, components, bounds, volume, and
  content hash. Never silently repair or overwrite source input.
- Derive an explicit required shell and closed legal infill domain from line
  width, wall count, top/bottom thickness, and tolerance settings.
- Sweep every structural and support edge into a printable strut solid with
  configurable cross-section. Materialize node/junction bodies with real
  overlap rather than coplanar or point contact.
- Intersect graph solids with the legal domain, union them with the required
  shell, and preserve the source exterior within declared tolerance.
- Detect thin features, boolean failures, disconnected struts, multiple bodies,
  self-intersection indicators, nonmanifold output, empty output, and unit or
  orientation ambiguity as structured failures.
- Export deterministic filenames without overwriting source assets. Include a
  sidecar manifest even when STL cannot carry provenance.
- Measure unioned internal structural volume after clipping and booleans.
  Report requested `infill_percent`, achieved percentage, absolute deviation,
  structural-member volume, print-support-member volume, and shell volume.
  Never derive achieved percentage from un-unioned member sums that double
  count junction overlap.
- Provide a preview command or deterministic render artifact that helps an
  operator inspect shell, structural members, support members, and junctions.

# Boundaries

Do not invoke a slicer, generate G-code, tune graph optimization weights, add
native slicer centerlines, or claim mechanical performance. Do not accept
clipping at layer-output time as proof that the solid graph is legal.

# Validation

Add RED tests for non-watertight input, unknown units, boolean failure,
zero-thickness/coplanar junctions, concave-domain escape, disconnected members,
and exterior deviation. Add GREEN tests for a convex box, concave L, and
tapered source. Verify each output with an independent readback path: positive
volume, intended component count, watertight/manifold status, bounds/exterior
tolerance, source immutability, independently recomputed achieved infill
percentage, and stable hashes for deterministic inputs.

Run the complete existing suite, geometry tests, export/readback tests, and
type checker. Render and inspect every canonical generated fixture before
claiming the export is previewable.

The required repository checks and their commands are:

- `unit`: `.venv/bin/python -m pytest -m unit`
- `geometry`: `.venv/bin/python -m pytest tests/geometry tests/materialize`
- `export`: `.venv/bin/python -m pytest tests/export`
- `typecheck`: `.venv/bin/python -m mypy src`

# Delivery

Preflight the registered workspace and repository-delivery authority. Create
the exact owned branch from current `main`, commit and push the materialization
slice, open a pull request, wait for the required checks, merge it, return the
registered workspace to updated `main`, and delete only the owned local and
remote branch. Preserve all unrelated work and generated user assets. Route
missing authority or failed delivery through the repair gate without moving the
implementation to `main` or another checkout.

# Completion report

Return the schema-version-1 structured completion result for `HC-PS-020`, with
package/boolean decisions, supported inputs and outputs, tolerance and failure
contracts, artifact paths and hashes, render/readback evidence, named checks
with commands, and exact branch/HEAD/PR/merged-HEAD identities.
