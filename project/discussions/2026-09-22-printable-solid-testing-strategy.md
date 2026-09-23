# Discussion Notes: Printable Solid Testing Strategy

Date: 2026-09-22

## Context

- The v0.2 prototype emits graph centerlines and layer strokes, but this makes
  meaningful preview, slicing, physical printing, and controlled comparison
  harder than necessary for the first research cycle.
- The user proposed generating a new copy of an input model with the Herculean
  structure physically embedded, then slicing that copy with infill disabled.

## Decisions And Leanings

- Materialized watertight geometry is the first integration target.
- The original source model remains immutable and supplies every conventional
  control.
- Herculean has its own requested `infill_percent` that controls how densely it
  plans internal struts. The generator records both requested and achieved
  structural volume fractions.
- Herculean variants are handed to the downstream slicer with slicer infill at
  0% only because their requested Herculean infill is already solid geometry;
  conventional variants use the source model and named slicer infills at the
  same requested percentage.
- Python owns the experiment harness and metrics. A mature slicer CLI owns
  production-faithful FDM slicing; a fake backend is only for unit tests.
- Creality Print is the preferred benchmark and eventual native-infill target
  because it is the user's normal printing workflow. Its installed CLI is
  qualified first without mutating user profiles.
- OrcaSlicer remains an automated fallback and cross-check if Creality Print's
  CLI/profile behavior cannot provide deterministic evidence. Generated STL/3MF
  artifacts remain directly openable in Creality Print either way.
- Comparisons use actual slicer time and material estimates, followed by
  measured physical time and performance. CAD volume is not a proxy for time.
- Nominal-density and matched-time or matched-mass comparisons remain distinct.
- Native slicer centerline integration is deferred until solid prototypes show
  useful physical results.

## Open Questions

- Intended Git repository name, remote owner, and integration branch.
- Final virtual-profile numerical limits and whether a second slow/reference
  profile is useful.
- Which physical test equipment and load ranges are available.
- Whether 3MF provenance is required in the first export or may follow STL.

## Follow-Up

- Execute `project/bodies/HC-PRINTABLE-SOLID-001.yaml` after repository
  admission.
- Record physical results without overwriting the slicer-only benchmark.
- Auto-Atumnus 0.1.0 requires a context-registered canonical Git worktree. The
  rewritten Body and Work Orders target `kellyjanderson/Herculean-Columns`,
  strict schema version 1, `codex-native`, and pull-request delivery. The GitHub
  repository and registration must exist before the Body can be admitted.
