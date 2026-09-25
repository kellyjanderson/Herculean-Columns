---
schema_version: 1
id: HC-PS-040
title: Implement the Python controlled-slicing and metrics harness
project: kellyjanderson/Herculean-Columns
base: main
branch: feature/HC-PS-040-slicing-benchmark
scope:
  owns:
    - src/herculean_columns/benchmark/**
    - src/herculean_columns/slicers/**
    - profiles/virtual-fdm/**
    - tests/benchmark/**
    - tests/slicers/**
    - docs/benchmarking.md
    - project/decisions/**
  may_read:
    - src/herculean_columns/**
    - fixtures/**
    - project/architecture/**
dependencies: [HC-PS-030]
completion:
  delivery: pull_request
  merge: agent
  required_checks: [unit, integration, benchmark-smoke, typecheck]
  qualification:
    any_of: [printable_solid, creality_matrix, orca_matrix]
---

# Context

Python owns benchmark orchestration, but authoritative FDM time and G-code must
come from a mature slicer rather than a newly invented path planner. Creality
Print is preferred when it qualifies, but is not a mandatory prerequisite. The
currently installed bundle is 7.1.1.4472; its CLI reports engine identity
`Creality-01.09.03.50` and exposes slicing, profile loading, isolated data
directories, and export operations at
`/Applications/Creality Print.app/Contents/MacOS/CrealityPrint`.

OrcaSlicer 2.3.2 is also installed and exposes a closely related CLI at
`/Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer`; it is an accepted
alternative backend, not merely a diagnostic cross-check. Installed state
must always be discovered at runtime.
These paths and versions are current evidence, not portable hard-coded
dependencies.

# Outcome

One Python command generates each Herculean body at a requested Herculean
`infill_percent`, slices that already-materialized body with downstream slicer
infill set to 0%, and slices its unchanged source with Lightning, rectilinear,
cubic, and gyroid controls at the same requested percentage under a single
versioned virtual printer/process/filament profile. It produces normalized,
provenance-complete JSON and tabular results plus retained G-code and logs.

# Required work

- Define a typed `SlicerBackend` protocol for version discovery, capability
  discovery, profile validation, slicing, artifacts, warnings, and normalized
  metrics.
- Implement a deterministic fake backend for unit and failure-path tests. Mark
  every fake result non-authoritative and prevent it from entering comparison
  evidence as a real benchmark.
- Implement a Creality Print CLI backend with explicit executable and dual
  bundle/engine-version discovery, isolated `--datadir`, bounded execution,
  captured stdout/stderr, exact input/output identities, and no dependency on
  interactive GUI state or user defaults.
- Prove Creality Print can load the checked-in machine/process/filament profile,
  slice, export G-code, and expose the required metrics without mutating global
  or user profiles. Do not infer this from `--help` alone.
- Implement an OrcaSlicer CLI backend with explicit executable discovery,
  isolated `--datadir`, bounded execution, captured stdout/stderr, exact input
  and output identities, and no dependency on interactive GUI/user defaults.
- Create checked-in virtual printer, process, and filament profiles fixing the
  architecture v0.3 settings. Verify through slicer output or exported settings
  that the intended profile was applied.
- Use the unchanged source for conventional variants and the materialized model
  for Herculean. Supply the same requested percentage to conventional slicer
  infill and Herculean planning. Set downstream slicer infill to 0% only for the
  already-materialized Herculean body, and record that as a handoff convention,
  not as Herculean density. Set support off.
- Parse slicer metadata and G-code into normalized metrics: estimated time,
  filament length/mass, deposited volume where available, extrusion/travel
  distance, retractions/restarts, feature time, short-segment distribution,
  warnings, and artifact hash. Preserve unavailable fields explicitly rather
  than fabricating zeroes.
- Store each run in a new content-addressed output directory with a run manifest
  containing source, generated model, slicer, profile, configuration, and code
  identities.
- Include requested and achieved Herculean percentage, density-planning
  configuration, structural volume, and print-support volume in normalized
  metrics and comparison identities.
- Detect profile drift, fallback to user defaults, changed source transforms,
  stale outputs, partial runs, timeouts, unsupported patterns, and parse errors
  as structured failures.
- Qualification is explicitly disjunctive: the Work Order passes when at least
  one of these evidence paths succeeds: (a) an independently read-back,
  printable, watertight single-body solid; (b) the complete real Creality Print
  benchmark; or (c) the complete real OrcaSlicer benchmark. Do not require all
  alternatives to pass.
- Prefer Creality Print when its qualification gate passes. If it fails, retain
  the failure evidence and run the full matrix in OrcaSlicer. A passing Orca
  matrix satisfies the backend gate without a Creality GUI import/Preview
  receipt. Record Creality compatibility as unverified when its importer also
  crashes; never claim the Orca result proves Creality compatibility.
- Preserve valid solid readback as an independent acceptance path. If no real
  slicer succeeds but the solid path does, report slicer metrics as unavailable
  and make no slicer comparison claims; do not turn missing optional backend
  evidence into an error-gate stop.

# Boundaries

Do not implement an FDM slicer in Python, drive the GUI, mutate global slicer
profiles, claim slicer estimates are physical time, or compare results from
different slicer/profile identities. Do not discard logs or failed-run evidence.

# Validation

Use RED tests for missing executable, unsupported backend version, fake backend
mislabeling, profile fallback, timeout, partial G-code, stale artifact reuse,
metric omission, and cross-variant process drift. Use the fake backend for fast
unit coverage. Run the Creality Print qualification and integration smoke test
first on the convex fixture. If it passes, run the required five-variant matrix with
Creality Print in a temporary isolated data directory and cross-check at least
one variant in Orca. If Creality fails, run and reproduce the full matrix in
Orca. Preserve the Creality crash as a known backend limitation; manual GUI
confirmation is not a completion prerequisite when another accepted path passes.
Add a guard proving that `slicer_infill_percent=0` cannot overwrite or be
reported as the Herculean requested percentage.
Re-run at least one variant to prove normalized configuration and metric
reproducibility within declared tolerances. Validate that original source and
global slicer state remain unchanged.

# Delivery

Preflight the registered workspace and repository-delivery authority. For a
fresh implementation, create the exact owned branch from current `main`; when
continuing this HC-PS-040 run, continue its already-owned branch and PR rather
than creating a duplicate. Commit and push the slicing harness and virtual
profile, open or update the pull request, merge only after one accepted
qualification path and the named checks pass, return the registered workspace
to updated `main`, and delete only the owned local and remote feature branch.
A failed optional backend is retained as evidence and must route to an accepted
alternative before error-gate exhaustion is considered.

# Completion report

Return the schema-version-1 structured completion result for `HC-PS-040`, with
backend/package decisions, discovered Creality Print bundle and engine
identities, Orca identity, the Creality qualification result, any explicit
fallback decision and the successful qualification path (`solid`, `creality`,
or `orca`), exact virtual profile and hashes, five-variant metric
artifacts, determinism/import evidence, named checks with commands, warnings,
and exact branch/HEAD/PR/merged-HEAD identities. State explicitly when Creality
GUI compatibility remains unverified because its CLI/importer crashes.
