# HC-PS-030 parametric fixture corpus

The source of truth is the named parameter set in `herculean_columns.fixtures.definitions`.
Files under `fixtures/generated/` are generated review artifacts, never hand-edited inputs.
All dimensions are millimetres and +Z is the build direction.

| Fixture | Exterior dimensions | Purpose | Physical interface |
|---|---:|---|---|
| convex-box | 20 x 20 x 20 | containment, grounding, roof support, compression | parallel Z platens |
| concave-l | 24 x 24 x 20 | illegal chord and clipping detection | Z faces and re-entrant corner |
| tapered-coupon | 20 x 20 x 24 | variable section and identity stability | parallel end faces |
| three-point-bending-bar | 80 x 12 x 10 | bending | supports at X +/-30, center top load |
| torsion-keyed-prism | 50 x 16 x 19 | torsional coupling | keyed X end interfaces |
| shell-indentation-coupon | 36 x 36 x 12 | local shell collapse | top center load, supported perimeter |

Labels are intentionally absent: every exterior face listed as critical in the
manifest participates in loading, support, clamping, dimensional inspection, or
the re-entrant geometry test.

Regenerate the committed corpus:

```sh
PYTHONPATH=src .venv/bin/python -P -m herculean_columns.fixtures.corpus generate fixtures/generated
```

Validate it in a clean temporary directory and compare all byte-contract hashes:

```sh
PYTHONPATH=src .venv/bin/python -P -m herculean_columns.fixtures.corpus validate fixtures/generated
```

Each fixture directory contains the source STL, one or more materialized STL
variants, component-colored SVG views, HC-PS-020 materialization manifests, and
the fixture contract. `geometry-report.json` aggregates independent STL
readback. `hashes.json` covers byte-deterministic artifacts. The 5/10/15 percent
convex-box series records requested planning density, achieved unioned internal
volume density, and stable configuration identity. Achieved values are required
to be nondecreasing, not exactly equal, because printable member minima can
flatten the response.

SVG colors are shell charcoal, structural blue, print-support orange, and
junction purple. Visual review checks for escaped, occluded, or disconnected
geometry; it does not substitute for watertight/component readback.
