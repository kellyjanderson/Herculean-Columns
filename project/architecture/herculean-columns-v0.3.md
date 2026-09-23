# Herculean Columns Architecture Version 0.3

Status: implementation authority for the printable-solid experiment

## Purpose

Herculean Columns is a sparse three-dimensional structural-infill experiment.
It generates a reasoned graph of shell braces and shared struts, repairs that
graph for the selected FDM build direction, materializes the graph as real
solid geometry inside an unchanged source-model envelope, and hands the
resulting watertight model to an existing slicer with ordinary infill disabled.

Version 0.3 changes the first proof target. Per-layer centerline emission is no
longer the first integration milestone. The first milestone is a previewable,
sliceable, and printable solid whose external geometry matches the source model
and whose internal material is the Herculean structure. Direct native-slicer
path integration remains a later optimization after physical utility is shown.

## Main hypothesis

For the same external model and printer process, a materialized Herculean
structure can approach the nozzle time and material use of Lightning infill
while improving one or more of:

- shell-to-shell stiffness;
- bending resistance;
- torsional coupling;
- local shell-collapse resistance;
- compression strength; and
- top-surface support quality.

The experiment is successful only when those claims are supported by slicer
and physical measurements. Concern count, graph length, and CAD volume are
diagnostics, not outcome evidence.

## Architectural principles

1. Structural topology is synthesized before build-direction repair.
2. Every graph member identifies the concern or manufacturing obligation it
   serves.
3. Shared members and nodes are preferred when they satisfy several concerns.
4. Print-support members remain useful permanent structure.
5. The exterior source-model surface is immutable during comparison generation.
6. A generated graph is invalid unless every identity is unique, every member
   lies in legal material volume, and every printable component has a proven
   deposited path to the build plate or already supported shell.
7. The first slicer boundary is a normal watertight solid, not custom G-code.
8. Comparisons hold model, orientation, walls, material, nozzle, layer height,
   temperatures, speed limits, acceleration limits, and slicer version fixed.
9. Optimize actual nozzle time and measured performance, not nominal infill
   percentage or raw CAD volume.
10. Generated artifacts and benchmark results are content-addressed and
    reproducible from a recorded configuration.

## Herculean infill percentage

Herculean has its own required `infill_percent` parameter. This is a planning
input to the Herculean generator and is independent of the downstream slicer's
infill setting.

`infill_percent` expresses the requested fraction of the legal infill domain
that should become materialized Herculean structure, excluding the required
exterior shell:

```text
achieved_infill_percent =
    100 * volume(materialized internal struts and nodes) /
          volume(legal infill domain)
```

The requested percentage drives how densely the engine plans concerns, nodes,
and struts. The prototype may meet the budget through candidate spacing,
concern selection, member sizing, or a documented combination, but the mapping
must be deterministic and monotonic enough that increasing the request does not
silently produce a less dense planned structure for the same model and other
configuration.

Printability-support members count toward the achieved percentage because they
consume real material and nozzle time. If minimum member size, shell attachment,
or printability repair prevents the exact requested percentage, generation may
produce the closest valid structure within a configured tolerance or fail with
a structured diagnostic. It must always report requested percentage, achieved
percentage, absolute deviation, structural volume, and support-member volume.

The slicer setting of 0% infill has no structural meaning for Herculean. It is
only a handoff convention telling the slicer not to add another infill pattern
inside a model whose Herculean structure is already represented as solid
geometry.

## Pipeline

### Stage 0: source-model admission

Input is a watertight, consistently oriented triangle mesh in millimetres. The
admission pass records a content hash, bounds, volume, connected-component
count, watertightness, winding consistency, and repair decisions. Automatic
repair may be offered, but repaired input receives a new identity and never
silently replaces the source.

The admitted model is preserved byte-for-byte. Every generated variant records
the source hash, transform, build orientation, and configuration hash.

### Stage 1: legal structural domain

The engine derives three separate regions:

- **exterior envelope**: the immutable outside shape of the source model;
- **required shell**: material reserved for external walls and top/bottom skin;
- **legal infill domain**: the remaining closed interior volume in which
  Herculean members may exist.

Shell thickness is an explicit geometric experiment parameter. It is derived
from the benchmark line width and requested wall count, then validated after
meshing. Thin features that cannot contain the requested shell are reported,
not silently erased.

### Stage 2: orientation-independent concern synthesis

The analysis creates candidate shell-to-shell connections from configurable
directions, adaptive shell samples, or later load hints. Version 0.3 may retain
the prototype ray sampler, but sampled interval ends must be refined to actual
legal-domain boundary intersections.

Every concern has a globally unique stable identity, endpoint anchors, source
method, score components, and required structural role. Top-N selection occurs
before final identity allocation or preserves monotonic identities without
reuse.

Candidate sampling and selection are governed by the requested Herculean
`infill_percent`. The planning pass estimates the material cost of members and
junctions, reserves budget for required printability repair, and selects the
highest-value valid structure that fits the remaining budget. A simple initial
implementation may use a calibrated density-to-pitch/candidate-count mapping,
but it must measure final unioned solid volume rather than claim that the input
percentage was achieved by construction.

Long interior span alone is only a geometric heuristic. It must be identified
as such; no concern may be described as mechanically valuable without a
corresponding score or physical result.

### Stage 3: shared structural graph

Near-intersections across distinct concerns may become shared nodes. Candidate
nodes are projected or rejected so they remain inside the legal infill domain.
Every routed edge is checked as a swept member, not only as a mathematical
centerline. Concave-volume chords and members that intersect forbidden shell or
void regions are invalid.

Node and edge IDs come from monotonic allocators independent of collection
length and survive pruning without reuse. Graph simplification must preserve
concern coverage and provenance.

### Stage 4: build-direction printability repair

The selected build direction is introduced only after the structural graph
exists. The solver operates on deposited bead-scale member geometry and proves
a support path bottom-up.

A node or member is constructively supported only when the generated solid has
sufficient overlap with previously deposited material under the configured
line width, layer height, bridge policy, and maximum unsupported inclination.
Creating a lower anchor does not make it supported; that anchor must itself be
connected to a grounded component.

The solver returns either a graph satisfying all printability invariants or a
structured diagnostic. It must never return a nominally successful graph with
unsupported nodes.

### Stage 5: solid materialization

Each accepted edge is swept into a printable strut solid. Junctions receive
explicit node bodies or blends large enough to survive slicing and provide
bead overlap. The strut assembly is intersected with the legal infill domain
and unioned with the required shell:

```text
materialized body = required shell union
                    (swept printable graph intersection legal infill domain)
```

The output must be a single intended printable body unless the fixture
explicitly tests multiple components. It must be watertight, manifold, have
positive volume, preserve the admitted exterior within tolerance, contain no
self-intersections detectable by the selected validation stack, and have no
strut disconnected from the shell/body component.

Primary output is STL for broad slicer compatibility. A 3MF package is also
produced when the chosen library can preserve units, names, provenance, and
preview metadata without changing geometry. The original model is never
overwritten.

### Stage 6: slicer handoff

The materialized Herculean body is sliced with the slicer's infill setting at
zero solely because its requested Herculean `infill_percent` has already been
realized as solid internal geometry. Conventional controls use the unmodified
source model with their named infill pattern and the same requested percentage.
All variants use the same recorded virtual printer, process, and filament
profiles.

Solid struts are contour geometry rather than native infill strokes. This is an
intentional prototype-stage difference: the experiment measures the real cost
and properties of that representation. Native centerline integration is
considered only after the solid experiment shows value.

## Python benchmark boundary

Python owns the experiment:

- fixture generation and source hashing;
- Herculean configuration and artifact generation;
- virtual printer/process/filament profile selection;
- slicer invocation in an isolated output directory;
- G-code and slicer-report parsing;
- normalized metrics, provenance, and comparison reports; and
- deterministic fake-slicer fixtures for unit tests.

Production benchmark evidence comes from a mature FDM slicer CLI behind a
Python `SlicerBackend` protocol. The preferred backend targets the user's
installed Creality Print CLI so generated models, profiles, previews, and G-code
fit the user's normal printing workflow. The installed OrcaSlicer CLI remains a
fallback and cross-check backend because Creality Print derives from the same
Slic3r/PrusaSlicer/Bambu Studio/Orca family and exposes a closely related CLI.

The preferred-backend decision is evidence gated: Creality Print must prove
isolated profile loading, deterministic slicing, G-code export, and parseable
metrics without mutating user profiles. If one of those capabilities fails,
the experiment uses Orca for automated benchmark evidence while continuing to
export ordinary STL/3MF artifacts that the user can open and slice in Creality
Print. Reimplementing perimeter generation, extrusion planning,
acceleration-aware estimation, or G-code production in Python is out of scope.
Fake or simplified Python backends may test orchestration but must be marked
non-authoritative for performance.

## Virtual printer profile

The repository owns a versioned, machine-independent profile intended for
repeatable comparisons, not as a promise about a physical printer. The initial
profile fixes at least:

- Cartesian FDM build volume: 220 by 220 by 250 mm;
- nozzle diameter: 0.4 mm;
- nominal line width: 0.45 mm;
- layer height: 0.20 mm;
- filament diameter and density;
- wall count and top/bottom layers;
- maximum volumetric flow;
- print and travel speeds;
- print and travel acceleration;
- retraction policy;
- temperatures and cooling policy;
- support disabled; and
- infill pattern/density as the only control-variant change.

The exact numerical values live in checked-in slicer-loadable profile fixtures.
Every result records profile hashes and the slicer executable/version.

## Benchmark variants

For every admitted source fixture, the minimum matrix is:

- Herculean materialized body generated at the requested Herculean
  `infill_percent`, then handed to the slicer with slicer infill set to 0%;
- original source with Lightning infill;
- original source with rectilinear infill;
- original source with cubic infill; and
- original source with gyroid infill.

The initial comparison applies the same requested percentage to Herculean and
each conventional control, while reporting Herculean's achieved percentage
after solid union. A second matched-budget pass brackets conventional densities
to match Herculean filament mass or estimated print time. This avoids treating
equal requested infill percentage as equal material or equal manufacturing
cost.

## Fixtures

Fixtures are generated parametrically and committed as definitions rather than
opaque meshes:

1. **Convex box coupon** — basic containment, grounding, roof support, and
   compression.
2. **Concave L coupon** — detects illegal chords and clipping discontinuities.
3. **Tapered coupon** — exercises variable cross-sections, ranked concern
   selection, and identity stability.
4. **Bending bar** — supports repeatable three-point bending.
5. **Torsion tube or keyed prism** — measures torsional coupling.
6. **Shell-indentation coupon** — measures local wall-collapse resistance.

Every fixture includes dimensions, expected topology properties, build
orientation, and its intended physical test. Fixture IDs are embossed only on
non-critical geometry when labels cannot influence the measurement.

## Measurement contract

### Geometry and graph

- source and output hashes;
- bounds and exterior deviation;
- watertight/manifold/component status;
- volume and estimated mass;
- requested and achieved Herculean infill percentage and deviation;
- structural-member and print-support-member volume;
- concern, node, structural-edge, and support-edge counts;
- concern coverage and shared-use counts;
- disconnected or unsupported count, required to be zero; and
- minimum member and junction dimensions.

### Slicer and G-code

- slice success and warnings;
- slicer and profile identities;
- estimated print time;
- total extrusion length and deposited volume;
- filament length and mass;
- travel distance;
- retraction and restart counts;
- per-feature time where available;
- short-segment distribution; and
- G-code hash.

### Physical observation

- measured print duration;
- measured part mass;
- print completion and visible defects;
- dimensional deviation;
- peak load and stiffness for the declared fixture test;
- failure mode and location; and
- top-surface quality where applicable.

Physical results are never inferred from slicer estimates. Slicer results are
never described as physical validation.

## Required invariants

Generation fails with structured evidence unless all apply:

- source identity and units are known;
- node, edge, and concern IDs are unique and never reused;
- every swept member is contained in legal material volume;
- every graph component is connected to intended shell/body material;
- every printable component has a grounded deposition path;
- no unsupported nodes remain;
- output is watertight and manifold;
- the source exterior is preserved within declared tolerance;
- generated file units and orientation are explicit; and
- the benchmark does not vary an undeclared process setting between variants.

## Deferred native integration

If the materialized-solid experiments show a useful strength-to-time advantage,
Creality Print is the preferred target for a native Herculean infill option.
Creality Print is open source, based on OrcaSlicer and its upstream slicer
lineage, so a later contribution can investigate adding Herculean beside its
existing sparse-infill implementations rather than creating a separate user
application. That phase may hand the graph to the slicer as bead centerlines
and must preserve the same density, graph, and measurement contracts while
adding native path ordering, junction flow, acceleration, seam, bridge, profile,
preview, and retraction behavior. Orca remains a useful upstream-family
reference and alternate integration target. Native integration is not required
for the printable-solid Body of Work.
