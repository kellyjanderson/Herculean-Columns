# HC-PS-040 backend and evidence policy

Creality Print is preferred only after an isolated convex-fixture slice proves profile loading, G-code export, applied-settings export, and normalized metric parsing. Its bundle and engine identities are recorded independently. A failed gate is retained as evidence; OrcaSlicer may become the benchmark backend only through an explicit recorded fallback decision and must pass the same gate.

The bounded subprocess is single-owner and synchronous: one request owns one process, isolated data directory, output directory, logs, and artifacts. Timeout is a hard process termination performed by the standard library; incomplete evidence remains in the `.partial` run. Content-addressed final directories are immutable and stale reuse is refused. Running matrices concurrently is safe only when output roots differ.

## Attempt 4cc322b7 fallback decision

Creality Print 7.1.1.4472 / `Creality-01.09.03.50` failed the isolated convex-fixture gate on 2026-09-25. After profile compatibility was repaired, the CLI exited by `SIGSEGV` following `calc_exclude_triangles:Unable to create exclude triangles`. A control invocation using the installed vendor Ender-3 V3 KE machine, process, and filament profiles failed identically, so the failure is not accepted as virtual-profile evidence. Logs and partial outputs were retained under the run's external qualification directory.

OrcaSlicer 2.3.2 is therefore the explicitly selected fallback for this attempt, contingent on passing the identical isolated real-backend gate. Creality remains required for non-slicing ordinary-model import validation; no Creality timing result from this attempt is authoritative.
