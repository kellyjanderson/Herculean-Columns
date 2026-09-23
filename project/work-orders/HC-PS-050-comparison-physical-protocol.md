---
schema_version: 1
id: HC-PS-050
title: Produce the controlled comparison and physical experiment pack
project: kellyjanderson/Herculean-Columns
base: main
branch: feature/HC-PS-050-comparison-protocol
scope:
  owns:
    - experiments/**
    - reports/**
    - docs/physical-testing.md
    - src/herculean_columns/reporting/**
    - tests/reporting/**
  may_read:
    - src/herculean_columns/**
    - fixtures/**
    - profiles/**
    - project/architecture/**
dependencies: [HC-PS-040]
completion:
  delivery: pull_request
  merge: agent
  required_checks: [unit, benchmark-matrix, report-validation]
---

# Context

The printable-solid milestone exists to create measurable evidence that can
direct further development. Nominal infill percentage is not a fair proxy for
material or time, and slicer estimates are not physical validation. Reports
must retain raw endpoints and separate predicted from observed results.

# Outcome

The repository contains a reproducible full-fixture slicer comparison, a
matched-time or matched-mass control analysis, printable model/G-code bundles,
and a manually executable physical test protocol. No unmeasured strength claim
is presented as a result.

# Required work

- Run the declared Herculean, Lightning, rectilinear, cubic, and gyroid matrix
  for every applicable fixture using one admitted source identity, slicer
  version, build transform, complete virtual-profile identity, and common
  requested percentage. Report the Herculean requested and achieved percentages
  separately from its downstream 0% slicer handoff setting.
- Report the fixed nominal-density control pass separately from a bracketed
  pass that selects conventional densities near Herculean estimated print time
  or filament mass. Preserve every attempted density and selection rule.
- Produce inspectable CSV/JSON raw results and a Markdown report with print
  time, filament mass, travel, retractions, short segments, slice warnings, and
  geometry metrics, including requested/achieved Herculean density and support
  overhead. Avoid a composite score that hides raw tradeoffs.
- Package the exact printable solid, control source, G-code, profile, manifest,
  and checksums needed for each selected physical print.
- Define manual procedures for weighing, timing, dimensional inspection,
  three-point bending, torsion, shell indentation, compression, top-surface
  inspection, and failure photography. State apparatus, calibration, sampling,
  units, repeated-trial count, safety limits, and invalid-run criteria.
- Provide blank observation records that distinguish slicer predictions from
  actual print time, mass, peak load, stiffness, defects, and failure mode.
- Define the evidence threshold for proposing optimization changes. At minimum,
  require repeated physical results and report variance before claiming an
  improvement.

# Boundaries

Do not invent physical observations, silently remove failed slices/prints,
change fixture geometry between variants, or present estimated mechanical
properties as measured. Do not tune the virtual profile independently per
infill method.

# Validation

Add RED report-validation tests for mixed profile identities, missing raw
artifacts, mismatched source hashes/transforms, fake-backend evidence, omitted
failed runs, unit inconsistencies, and claims lacking observations. GREEN
validation must regenerate the report from raw manifests, account for every
matrix member, verify checksums, and reproduce all tables. Independently inspect
at least one G-code/model bundle for each variant and confirm it is ready for a
human-controlled print.

# Delivery

Preflight the registered workspace and repository-delivery authority. Create
the exact owned branch from current `main`, commit and push the reproducible
virtual comparison and empty physical protocol, open a pull request, merge
after required checks, return the registered workspace to updated `main`, and
delete only the owned local and remote feature branch. Physical observations
added later must use a new owned Work Order and may not rewrite the baseline
evidence. Any delivery failure enters the repair gate.

# Completion report

Return the schema-version-1 structured completion result for `HC-PS-050`, with
the comparison matrix, selected matched-budget rule, principal slicer endpoints
without mechanical claims, report and bundle paths/hashes, named checks with
commands, unresolved physical-testing prerequisites, and exact
branch/HEAD/PR/merged-HEAD identities.
