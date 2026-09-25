# Controlled slicing benchmark

HC-PS-040 uses a mature slicer for every authoritative estimate. Python owns orchestration, provenance, parsing, and comparison; it does not implement toolpaths. Results are estimates from the named slicer/profile, not physical print times.

The versioned `HC-VIRTUAL-FDM-V1` profile fixes a 220 × 220 × 250 mm Cartesian machine, 0.4 mm nozzle, 0.45 mm line width, 0.20 mm layers, PLA properties, speeds, accelerations, retraction, temperatures, and disabled support. Runtime profile hashes are recorded and isolated `--datadir` directories prevent user-profile mutation.

Run the matrix with the repository virtual environment:

```sh
PYTHONPATH=src .venv/bin/python -P -m herculean_columns.benchmark.cli \
  --source fixtures/generated/convex-box/source.stl \
  --herculean fixtures/generated/convex-box/source-herculean-81a8a1ba1356f1ff.stl \
  --materialization-manifest fixtures/generated/convex-box/source-herculean-81a8a1ba1356f1ff.manifest.json \
  --infill-percent 5 --output benchmark-results
```

The Herculean body is already materialized. Its downstream `slicer_infill_percent` is therefore 0%; this is a handoff convention and never overwrites or describes the requested or achieved Herculean density. The four controls use the unchanged source and the requested percentage.

Each run is placed in a content-addressed directory and retains its manifest, normalized JSON/CSV metrics, G-code, applied settings, stdout, stderr, and per-variant profile. Existing or partial destinations are rejected. Fake results are permanently non-authoritative and the comparison runner refuses them.

## Creality CLI crash fallback

Creality Print 7.1.1.4472 / `Creality-01.09.03.50` currently exits via
`SIGSEGV` after `calc_exclude_triangles:Unable to create exclude triangles`,
including with vendor profiles and during CLI import. Do not reinterpret that
crash as import compatibility evidence and do not automate the GUI.

HC-PS-040's qualification is disjunctive: a verified printable solid, a
complete real Creality matrix, or a complete real Orca matrix is sufficient.
When Creality's CLI/importer crashes, retain its logs and select Orca with
`--fallback-from-creality-failure`; do not require a manual GUI receipt to use
a passing Orca result. The manifest must record Creality GUI compatibility as
unverified. A solid-only pass must state that slicer metrics are unavailable
and must not claim a comparison result.

The optional human receipt helper remains available for a later, explicitly
requested Creality GUI compatibility study. It is not part of the release gate
and must not block a successful solid, Creality, or Orca evidence path.
