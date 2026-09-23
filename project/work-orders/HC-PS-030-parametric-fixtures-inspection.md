---
schema_version: 1
id: HC-PS-030
title: Build the parametric benchmark fixture and inspection corpus
project: kellyjanderson/Herculean-Columns
base: main
branch: feature/HC-PS-030-fixture-corpus
scope:
  owns:
    - src/herculean_columns/fixtures/**
    - src/herculean_columns/inspection/**
    - fixtures/**
    - tests/fixtures/**
    - tests/inspection/**
    - docs/fixtures/**
  may_read:
    - src/herculean_columns/**
    - project/architecture/**
dependencies: [HC-PS-020]
completion:
  delivery: pull_request
  merge: agent
  required_checks: [unit, fixture-regeneration, geometry, visual]
---

# Context

The experiment needs shapes that expose algorithmic failures and support
repeatable physical tests. Opaque hand-authored STLs are insufficient because
their dimensions, purpose, and regeneration provenance cannot be reviewed.

# Outcome

The repository contains a deterministic parametric fixture corpus, expected-
property manifests, source and Herculean outputs, machine-readable geometry
reports, and preview images. Every fixture states which software invariant and
physical endpoint it tests.

# Required work

- Implement named parametric definitions for the convex box, concave L,
  tapered coupon, three-point-bending bar, torsion coupon, and shell-indentation
  coupon described by architecture v0.3.
- Preserve identical exterior dimensions and test interfaces across generated
  variants. Keep labels off load surfaces and other critical geometry.
- Define build orientation, dimensional parameters, expected component count,
  expected graph properties, intended physical setup, and acceptance tolerances
  in versioned manifests.
- Define a small percentage series for canonical density behavior, including at
  least three increasing nonzero Herculean `infill_percent` values on the same
  exterior fixture. Record expected monotonic planning and achieved-volume
  properties without assuming exact equality where printable minima intervene.
- Generate admitted source assets and Herculean materialized assets into a
  reproducible generated-artifact directory without treating those artifacts
  as hand-edited sources.
- Create deterministic inspection reports and views that distinguish required
  shell, structural edges, print-support edges, and junctions.
- Add a corpus-level command that regenerates and validates every fixture in a
  clean temporary directory, then compares expected manifests and hashes where
  byte determinism is part of the contract.

# Boundaries

Do not select winning infill settings, generate production G-code, invent
physical measurements, or optimize fixtures for a favorable Herculean result.
Do not change the measurement interface of one variant independently.

# Validation

Use RED tests for deliberately changed dimensions, illegal labels, unexpected
components, nondeterministic manifests, missing provenance, and mismatched
build orientation. GREEN validation must independently read every exported
asset and verify dimensions, manifold/watertight state, component count,
exterior equivalence, and stable configuration identity. Render all canonical
fixtures and inspect them for occluded, disconnected, or escaped geometry.

# Delivery

Preflight the registered workspace and repository-delivery authority. Create
the exact owned branch from current `main`, commit and push the complete fixture
corpus, open a pull request, wait for required checks and visual review, merge
it, return the registered workspace to updated `main`, and delete only the
owned local and remote feature branch. Delivery failures enter the repair gate.

# Completion report

Return the schema-version-1 structured completion result for `HC-PS-030`, with
the fixture matrix, dimensions and purposes, regeneration commands, hash and
geometry artifacts, visual-review evidence, named checks with commands, and
exact branch/HEAD/PR/merged-HEAD identities.
