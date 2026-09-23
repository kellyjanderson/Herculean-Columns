# Printable Solid Implementation Plan

Status: definition-ready; execution requires registered-repository admission

## Objective

Produce reproducible watertight Herculean test bodies at a requested Herculean
infill percentage, slice those already-materialized bodies with downstream
slicer infill set to 0%, and compare them against conventional infills at the
same requested percentage on the unchanged source model using one versioned
virtual printer profile. The result is an evidence pipeline that can direct
later structural and print-time optimization.

## Delivery strategy

Implementation is split into five dependency-ordered vertical slices. Each
slice must be independently qualified and merged before its dependent begins.

### Slice 1: project foundation and graph correctness

Turn the single-file research prototype into a tested Python package. Establish
units, typed configuration, monotonic identities, structured diagnostics, and
hard graph invariants. Reproduce and repair the known tapered-ID, pruned-node,
concave-volume, and unresolved-support failures.

Define the independent Herculean `infill_percent` contract and a deterministic
planning budget. Prove that requested density changes strut planning and that
the generator reports achieved unioned internal volume rather than confusing it
with the slicer's later 0% handoff setting.

Exit evidence: all regression fixtures pass; invalid graphs cannot reach
materialization.

### Slice 2: source admission and solid materialization

Admit a watertight source mesh, derive shell and legal infill volumes, sweep
graph members into bead-scale solids, union junctions, clip the structure, and
export a distinct watertight STL plus optional 3MF. Prefer maintained mesh and
boolean packages; record package choice and adversarial geometry results.

Exit evidence: the convex, concave, and tapered fixtures export as manifold
single-body models with preserved exteriors and connected internal structures.

### Slice 3: parametric fixtures and artifact inspection

Create the complete coupon set, expected-property manifests, deterministic
previews, and automated geometry reports. Keep physical-test surfaces stable
across variants and put labels only on non-critical material.

Exit evidence: every fixture is reproducibly regenerated and previewed, with
hashes and machine-readable validation reports.

### Slice 4: Python slicing and benchmark harness

Implement the Python `SlicerBackend` boundary, a fake backend for unit tests,
a preferred Creality Print CLI backend, and an OrcaSlicer fallback/cross-check
backend. Add checked-in printer/process/filament profiles and normalized
G-code/slicer metrics. Controls slice the original source at the requested
comparison percentage; Herculean slices the materialized body with slicer
infill at 0% because its requested percentage is already solid geometry.

Exit evidence: one command produces isolated, provenance-complete results for
all required variants and refuses profile drift or incomplete metrics.

### Slice 5: controlled comparison and physical experiment pack

Run the full virtual matrix, add matched-time or matched-mass conventional
controls, produce comparison tables, and create a physical-print worksheet.
Do not claim mechanical superiority without measured tests.

Exit evidence: reproducible slicer report, printable artifacts, G-code, and a
physical test protocol that clearly separates predicted from observed results.

## Dependency graph

```text
HC-PS-010 graph foundation
    -> HC-PS-020 solid materialization
        -> HC-PS-030 fixtures and inspection
            -> HC-PS-040 slicing benchmark
                -> HC-PS-050 comparison and physical protocol
```

## Package-selection checkpoints

The implementation agents must evaluate maintained packages before adding
custom infrastructure:

- `trimesh` for mesh IO, inspection, sections, and mass properties;
- `manifold3d` or another robust supported backend for boolean operations;
- `build123d` only where parametric B-rep construction materially improves
  fixture or junction generation;
- `pydantic` or an equivalent maintained package for versioned configuration
  and result validation; and
- Creality Print CLI as the preferred production-faithful slicing backend and
  future native integration target;
- OrcaSlicer CLI as the automated fallback and cross-check backend.

Package decisions belong in a short project decision record with versions,
license, maintenance evidence, rejected alternatives, and failure behavior.

## Benchmark fairness gates

- Same admitted source mesh and build transform for every variant.
- Same slicer executable and complete profile hashes.
- Same walls, skins, temperatures, cooling, speed, acceleration, retraction,
  support, and material settings.
- The same requested percentage is supplied to Herculean planning and each
  conventional control. Only the infill method or substitution of the
  materialized Herculean body may differ.
- Repeat runs must produce identical normalized configuration and equivalent
  metrics within declared deterministic tolerances.
- Nominal-density results and matched-budget results are reported separately.

## Initial virtual-profile target

Use a generic 220 by 220 by 250 mm Cartesian printer with a 0.4 mm nozzle,
0.45 mm line width, 0.20 mm layers, generic PLA, two walls, four top and bottom
layers, supports disabled, fixed acceleration and volumetric-flow limits, and
one fixed retraction/cooling policy. HC-PS-040 owns the exact slicer-loadable
values and first verifies that Creality Print applies them rather than silently
falling back to user defaults. Equivalent Orca fixtures are maintained only as
the fallback/cross-check path.

## Measurable development endpoints

The optimizer may later target:

- zero invalid, disconnected, or unsupported members;
- requested versus achieved Herculean infill percentage and budget deviation;
- monotonic density response across the declared percentage fixture set;
- minimum slice-success rate across fixture corpus;
- estimated and actual print time;
- filament mass;
- travel and retraction counts;
- short-segment and start/stop penalties;
- bending stiffness and peak load per minute;
- torsional stiffness per minute;
- shell-indentation load per minute;
- compression load per minute; and
- top-surface quality at matched time or material.

No single score should hide the underlying measurements during the research
phase.

## Admission prerequisites

Auto-Atumnus 0.1.0 starts only against a context-registered canonical Git
worktree. This folder is now a standalone Git repository whose `main` branch is
published to the public `kellyjanderson/Herculean-Columns` GitHub repository.
Before starting the Body:

1. register this exact project/workspace/repository with the installed
   Auto-Atumnus context using adapter `codex-native` and its admitted sandbox;
2. verify Git refs/index/objects/worktree writes plus GitHub authentication,
   push, PR/check observation, merge, integration restoration, and owned-branch
   deletion; and
3. validate the workspace-relative Body path through the installed service.

The intended installed-service sequence is:

```bash
auto-atumnus project register kellyjanderson/Herculean-Columns \
  --workspace "/Users/k/Documents/Projects/Herculean Columns" \
  --github-repository kellyjanderson/Herculean-Columns
auto-atumnus validate kellyjanderson/Herculean-Columns \
  project/bodies/HC-PRINTABLE-SOLID-001.yaml
auto-atumnus start kellyjanderson/Herculean-Columns \
  project/bodies/HC-PRINTABLE-SOLID-001.yaml --detach
```

These commands are documentation, not evidence that Auto-Atumnus registration
already exists.

Local strict-schema validation proves definition consistency only. It does not
substitute for registered-project admission, installed-service validation, or
remote repository-delivery authority.
