# Release Validation

The final release was subjected to the following checks:

- the original v11 results ZIP passed CRC validation;
- all 1,162 files listed in the original run's internal SHA-256 manifest were verified;
- the original run's secret scan reports no findings;
- the independent postprocessor completed successfully in quick audit mode from a fresh extraction;
- all Python scripts compile with `py_compile` and the shell build script passes `bash -n`;
- the common-external claim counts reproduce 1,200 total solver calls and the seven strategy-level pass counts used in the analysis;
- all four promoted exact certificates report `certificate_pass = true`;
- the current release compiled with BibTeX to clean and line-numbered twelve-page PDFs;
- all eleven PDF pages were rasterized and visually inspected, including equations, tables, the workflow diagram, and result figures;
- reviewer-triggered endpoint-containment, refinement, infeasibility, expert-sequence, and round-off audits reproduce the counts stated in the revised analysis;
- the reference convergence plot marks the `m = 480` round-off floor and uses a dashed final segment;
- the reviewer, mechanism-update, and attrition-sensitivity diffs are retained in `docs/REVIEWER_REVISION_MAIN_TEX.diff`, `docs/MECHANISM_UPDATE_MAIN_TEX.diff`, and `docs/ATTRITION_SENSITIVITY_MAIN_TEX.diff`;
- no credential-shaped secret was detected in the release;
- the final package SHA-256 manifest is checked by `scripts/verify_release.py`.

- the v12 and v12.1 nested result ZIPs passed CRC and their internal SHA-256 manifests;
- `scripts/audit_v12_followups.py` reproduces the corrected v12 transport/parser partition, v12.1 transport and arm-distinct-program health, arm completion, duplicates, schedules, observed and missing-as-failure 2x2 rates, completion-stratified two-stage results, prediction coverage, and exact-candidate counts;
- the three released follow-up exact certificates report `certificate_pass = true`;
- v12/v12.1 are explicitly excluded from primary policy inference because their archived comparison-validity flags are false.

- the v12.1 expert-prior gate-gap audit reproduces the 0.6667 self-declared-minus-external difference;

- the downstream audit verifies the normalized weighted-symmetry residual contrast (`1.23e-16` for the leading candidate versus `0.522351` for the order-six reference under its native quadrature);
- the the current release text reports the interior transient maximum and the weighted-symmetry contrast;
- the pinned MOLE attribution audit matches the embedded order-2, 4, 6, and 8 arrays to the Corbino--Castillo implementation and verifies the support conditions used by Proposition 1;
- exploratory Euclidean energy-growth outputs are explicitly marked superseded in both the derived-notebook and source-artifact directories.

- the authoritative solver-consequence script loads 11 operators, reproduces weighted-symmetry residuals to floating-point tolerance, and verifies CG applicability for all 7 exact constructions and none of the 4 references under native quadrature;
- the order-six diagnostic symmetric-part solve reproduces relative solution error `0.278366`, while GMRES on the original reference system reproduces approximately `1.0e-9` error;
- the preserved user solver notebook/results and authoritative output agree on all claim-bearing values; environment-dependent Krylov iteration counts are explicitly excluded from analysis performance claims.
