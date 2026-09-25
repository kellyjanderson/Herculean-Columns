# Decision 0001: package foundation

Status: accepted for HC-PS-010 (2026-09-24)

The project uses a `src/` package and Python 3.12+. Runtime and qualification
dependencies are exactly pinned in `pyproject.toml` so a fresh repository-local
`.venv` reproduces the toolchain.

| Concern | Choice | Version | License | Reason and failure posture |
|---|---|---:|---|---|
| geometry predicates | Shapely | 2.1.2 | BSD-3-Clause | Maintained GEOS binding with robust 2-D predicates. This slice uses it for layer-domain containment only; failed containment rejects a graph. Mesh booleans are deferred. |
| validation and serialization | Pydantic | 2.12.5 | MIT | Maintained typed validation, range constraints, and deterministic JSON. Invalid units/ranges fail at configuration admission. |
| property testing | Hypothesis | 6.151.9 | MPL-2.0 | Maintained generative testing for identity, determinism, density, containment, and connectivity invariants. |
| type checking | mypy | 1.19.1 | MIT | Strict static checking with a stable Python CLI. Type failures block delivery. |
| test runner | pytest | 9.0.2 | MIT | Mature test discovery and separate unit/regression gates. |
| build backend | Hatchling | 1.27.0 | MIT | Minimal PEP 517 `src/` packaging without project-specific build infrastructure. |
| geometry type stubs | types-Shapely | 2.1.0.20260728 | Apache-2.0 | Strict third-party annotations for the pinned Shapely API; qualification fails on missing or inconsistent types. |

Rejected for this slice: custom validation/serialization (unnecessary risk),
mesh boolean packages such as `manifold3d` (HC-PS-020 responsibility), and
`build123d` (no B-rep construction is needed for graph correctness).

The density report is explicitly a deterministic planning estimate based on
member lengths and configured circular area. It accounts for support overhead
but is not mislabeled as unioned materialized volume. HC-PS-020 must replace
the estimate with measured unioned solid volume before physical or slicer use.
