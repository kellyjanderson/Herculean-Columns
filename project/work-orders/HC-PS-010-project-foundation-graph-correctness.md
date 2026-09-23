---
schema_version: 1
id: HC-PS-010
title: Establish the package and enforce structural graph correctness
project: kellyjanderson/Herculean-Columns
base: main
branch: feature/HC-PS-010-graph-foundation
scope:
  owns:
    - pyproject.toml
    - README.md
    - AGENTS.md
    - src/herculean_columns/**
    - tests/unit/**
    - tests/regression/**
    - project/decisions/**
  may_read:
    - herculean_columns.py
    - Herculean Columns — Architecture v0.2.docx
    - project/architecture/**
    - project/planning/**
dependencies: []
completion:
  delivery: pull_request
  merge: agent
  required_checks: [unit, regression, typecheck]
---

# Context

Architecture v0.3 requires hard identity, containment, connectivity, and
grounding invariants before geometry can be materialized. The v0.2 prototype is
a reference implementation, not a compatibility contract. Review findings
already demonstrated duplicate concern IDs on tapered geometry, node-ID reuse
after pruning, structural chords outside concave volumes, unresolved nodes, and
an environment that cannot reproduce dependencies from the folder alone.

# Outcome

The project is a reproducible typed Python package with a corrected structural
graph pipeline. Invalid graphs produce structured diagnostics and cannot be
reported as successful or passed to downstream materialization.

# Required work

- Establish a repository-local `.venv` workflow, pinned project dependencies,
  documented commands, and a test/typecheck toolchain without committing the
  environment itself.
- Follow the package-first directive. Record the package choices for geometry,
  validation/serialization, property testing, and type checking in a concise
  decision document.
- Split the monolithic prototype into cohesive package modules while preserving
  an intentional migration entry point or documenting the replacement command.
- Replace collection-length IDs with monotonic, non-reused typed identities for
  concerns, nodes, and edges.
- Allocate or normalize retained concern IDs after ranking so top-N selection
  cannot collide across orientations.
- Refine sampled interval endpoints to legal-domain boundary intersections or
  classify approximate endpoints explicitly until the refinement is available.
- Require structural centerlines and their configured member radius to remain
  within the legal domain. Reject illegal concave-volume chords.
- Require every node to reach a grounded printable component. A newly created
  lower anchor must prove its own grounded path.
- Return a structured generation result that distinguishes valid graph output
  from diagnostics; never leave unsupported nodes in a successful result.
- Validate configuration ranges, units, deterministic ordering, and stable
  serialization.
- Add an independent required Herculean `infill_percent` configuration value.
  Define it as requested materialized internal-structure volume divided by
  legal infill-domain volume, excluding required shell material.
- Implement a deterministic initial density-planning budget that changes
  candidate, concern, or strut density without reference to the downstream
  slicer's infill setting. Reserve or account for print-support material and
  report when constraints prevent the exact requested percentage.

# Boundaries

Do not implement mesh booleans, solid export, slicer invocation, optimization,
FEA, a GUI, or physical-strength claims. Do not mutate or delete the historical
v0.2 document or source file. Do not weaken an invariant to make a fixture pass.

# Validation

First add RED regression tests that reproduce:

- duplicate retained concern IDs in a tapered volume;
- node overwrites after shared-node pruning and support insertion;
- an out-of-domain structural edge in a concave L volume;
- an ungrounded fallback anchor in a disconnected/upper region; and
- unresolved nodes returned without a failing result.

Then implement GREEN behavior. Add property tests for unique stable IDs,
deterministic generation, containment, connectivity, and zero unsupported nodes
for successful outputs. Add percentage boundary, monotonic-response, budget,
support-overhead, and requested-versus-achieved reporting tests across several
fixed percentages on the same fixture. Run the complete suite and type checker
from the documented `.venv`. Report exact commands, versions, counts, and
evidence bound to the delivered commit.

# Delivery

Preflight the registered workspace, writable Git control plane, `origin`
agreement with `kellyjanderson/Herculean-Columns`, GitHub authentication, and
pull-request/merge/cleanup capability before source mutation. Create the exact
owned branch from current `main`, commit and push only the coherent project
foundation and graph-correctness slice, open a pull request, wait for required
checks, merge it, return the registered workspace to updated `main`, and delete
only the owned local and remote feature branch. Any missing authority or
capability enters the Auto-Atumnus repair gate; do not implement on `main` or
substitute an unregistered workspace.

# Completion report

Return the schema-version-1 structured completion result for `HC-PS-010`,
including summary, exact branch/HEAD/PR/merged-HEAD identities, named validation
checks with commands and evidence bound to the delivered commit, artifact
paths, deferred work, and any error or downstream migration obligation.
