# 0002 — Solid materialization stack

Status: accepted for HC-PS-020

## Decision

Use `trimesh==5.1.0` as the mesh IO, inspection, deterministic STL, and
readback adapter. Use `manifold3d==3.5.3` through trimesh's maintained
`engine="manifold"` boolean adapter for union, intersection, and difference.
Derive the closed legal domain with Manifold's maintained signed-distance
level-set constructor using trimesh proximity queries, then validate every
boolean result as a positive, watertight manifold.

The adapter requires source units to be explicitly declared as millimetres.
It never invokes trimesh's repair operations and never writes to the source
path. The required shell is the larger of wall-count times line width and
top/bottom thickness. A resolution-scaled overlap band prevents coplanar-only
shell attachment. Circular struts and larger spherical junctions are the
initial supported cross-section contract.

## Evidence and rejected options

- Accepted: trimesh reads STL and exposes bounds, signed volume, winding,
  watertightness, and independent STL readback without altering source bytes.
- Accepted: manifold3d provides deterministic robust booleans and an
  independent solid-body decomposition used instead of incorrectly counting
  the inner and outer boundary surfaces of a hollow shell as separate bodies.
- Accepted: `rtree==1.4.1` supplies the maintained spatial index used by
  trimesh signed-distance queries.
- Rejected: hand-written triangle/CSG code; it duplicates mature topology and
  boolean machinery without an evidence advantage.
- Rejected: Blender/OpenSCAD subprocess booleans; they add external executable
  state and weaker deterministic provenance for this package boundary.
- Rejected: voxel erosion through scipy/scikit-image; it adds a second surface
  generator when Manifold already supplies a closed level-set implementation.
- Rejected for now: 3MF output. Trimesh 5.1.0 exposes no maintained 3MF
  exporter, so geometry, millimetre units, and provenance cannot be reliably
  round-tripped. STL plus the JSON sidecar is emitted instead.

The signed-distance level-set approximation is controlled by
`mesh_resolution_mm` and `geometry_tolerance_mm`.
Outputs are rejected when exterior bounds differ by more than
`exterior_tolerance_mm`, and reports bind the exact configuration and source,
graph, STL, preview, and manifest hashes.
The measured unioned internal percentage must fall within
`budget_tolerance_percent`; otherwise materialization fails with
`DENSITY_BUDGET_MISS` instead of presenting a sparse graph as the requested
density.

Maintenance and API evidence was checked against the primary project sources:

- trimesh 5.1.0 (MIT): https://pypi.org/project/trimesh/5.1.0/ and
  https://github.com/mikedh/trimesh/blob/main/trimesh/boolean.py
- manifold3d 3.5.3 (Apache-2.0): https://pypi.org/project/manifold3d/3.5.3/
  and https://github.com/elalish/manifold/wiki/Manifold-Library
- rtree 1.4.1 (MIT): https://pypi.org/project/Rtree/1.4.1/
