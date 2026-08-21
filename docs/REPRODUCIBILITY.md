# Reproducibility Protocol

## 1. What can be reproduced without network access

The analysis can be regenerated from the immutable archived run without issuing any new LLM request. The offline path recomputes:

1. the common externally fixed verifier endpoint and its containment relation with the notebook gate;
2. seed-level hit rates and exact paired sign-flip randomization tests over all `2^10` sign assignments;
3. Holm multiplicity correction;
4. best-so-far utility curves and AUC;
5. complete LLM cost accounting from every raw generation;
6. the model/role schedule and expert-prior sequence audits;
7. endpoint containment, randomized-refinement, and infeasibility-structure audits;
8. a model/role-adjusted post-hoc logistic sensitivity analysis;
9. the highest-utility hard-pass candidate from every archive condition;
10. coupled rational reconstruction and exact block-positive-definiteness checks;
11. extended mesh transfer through `m = 640`;
12. normalized dense and boundary-supported perturbation experiments;
13. all summary tables and figures.

## 2. Environment

The original run reports:

```text
Python              3.12.13
NumPy               2.0.2
SciPy               1.16.3
pandas              2.2.3
Matplotlib          3.10.0
SymPy               1.14.0
scikit-learn        1.6.1
HTTPX               0.28.1
```

The independent postprocessor additionally requires statsmodels 0.14 or newer. `environment.yml` records a portable environment; `requirements.txt` records pip constraints.

## 3. Immutable source artifacts

| Artifact | SHA-256 |
|---|---|
| Original v11 notebook | `b0a55b91ab8841b87c564dd461265502b7da0b7c54620a835f977e5b41b03d4b` |
| Original v11 result archive | `6f83b469b452121628447954c57efea51d36ed15e3c37caf2d290ec2dbcf66ec` |

The nested result archive contains its own `MANIFEST.sha256`; `scripts/verify_release.py` verifies it after temporary extraction.

## 4. Offline reconstruction

```bash
make extract
make postprocess DERIVED=derived_reproduced
make compare-derived DERIVED=derived_reproduced
```

The postprocessor dynamically loads the exact operator/compiler definitions from the archived notebook. It never calls a hosted model. Its output is a separate directory so that the supplied authoritative derivation remains untouched.

Expected top-level counts:

```text
all deterministic solver records     1,200
non-LLM solver records                  720
accepted live-LLM solver records        480
raw live LLM generations                529
LLM archive conditions                    4
LLM seeds per condition                  10
unique solver calls per condition/seed   12
```

Expected common-external pass counts:

```text
full metrics          66 / 120
illumination          64 / 120
structure only        32 / 120
no archive            20 / 120
expert-informed      120 / 240
ExtraTrees surrogate  57 / 240
uniform random        32 / 240
```

## 5. Exact reconstruction

`postprocess_v11.py` recompiles the leading hard-pass program from each archive condition. It rebuilds the complete affine system in rational arithmetic, computes an exact reduced-row-echelon parameterization, places only free variables on a dyadic grid, solves the pivot variables exactly, and checks all original constraints. Positive norm blocks are certified through exact leading principal minors.

Exact certificates are JSON files under `derived/exact_certificates/`; numerical arrays instantiated at `m = 200` are stored under `derived/operators/`.

## 6. Floating-point variation

The LP and dense eigensolvers can show last-digit variation across BLAS/LAPACK implementations. The analysis does not rely on last-digit equality. Claim-level tolerances and exact certificates are much wider than ordinary floating-point variation. Exact rational identities are backend independent once reconstruction succeeds.

## 7. Live reruns

A live rerun requires a Nebius Token Factory key and will not reproduce the same served catalogue indefinitely. Archive the following for every new campaign:

- exact notebook hash and schema version;
- endpoint and resolved model IDs;
- capability-probe responses;
- decoding settings;
- all raw and repaired generations;
- prompt hashes and archive condition;
- deterministic solver evaluations;
- environment versions;
- a new immutable run manifest.

Never overwrite the supplied v11 archive.

## 8. Reviewer-revision audit outputs

The following files are regenerated from the same immutable solver table and require no new model or LP calls:

```text
derived/endpoint_containment.csv
derived/endpoint_by_strategy.csv
derived/refinement_effect_audit.csv
derived/infeasibility_structure_audit.csv
derived/expert_prior_seed_audit.csv
```

Expected checks:

```text
endpoint containment: false/false 809, false/true 142, true/false 0, true/true 249
refinement external: refined 20/42, fresh 25/55, Fisher p 0.8404378429863986
refinement notebook: refined 16/42, fresh 20/55, Fisher p 1.0
endpoint-supported extended-Gauss diagnoses: 637 of 638
expert sequence hashes: 10 unique; external passes: 12/24 for every seed
```


## 9. Recompute the v12/v12.1 follow-up audit

No model calls or LP solves are required.

```bash
python scripts/audit_v12_followups.py \
  --v12-results runs/v12_failed_results.zip \
  --v12-1-results runs/v12_1_followup_results.zip \
  --output-dir derived/followups_recomputed
```

The authoritative precomputed outputs are in `derived/followups/`. Expected checks include:

```text
v12: comparison_valid false; 495/2502 successful generations; 120 schema echoes selected by parser
v12.1: comparison_valid false; 1036/1051 successful generations; 569/572 predictions
v12.1: 42/50 completed arms; 424 duplicates; 20 schedule mismatches
2x2 hard-pass rates: cold 15/120, diagnostic 16/120, archive 42/107, full 38/114
two-stage: cold 10/60, feedback 23/51
```

The script also exports the exactly certified v12 diagonal and v12.1 block-norm candidate summaries. It does not interpret either invalid campaign as a policy comparison.

## 11. Linear-solver consequence

Recompute the weighted-system and Krylov diagnostics with:

```bash
python scripts/analyze_solver_consequences_v2.py
```

The script loads the four primary exact operators, three follow-up exact mathematical artifacts, and the four MOLE/Corbino--Castillo references at `m = 200`. It writes authoritative tables, a diagnostic figure, and a JSON report to `derived/solver_consequences_v2/`.

`cg_symmetric_part_diagnostic` is intentionally not a practical solver: for a nonsymmetric weighted reference it solves a different matrix. GMRES and BiCGSTAB are applied to the original matrix, and a dense direct solve is retained as an accuracy check. Iteration counts can vary across BLAS/SciPy builds and are not used for cross-family speed claims.


## 10. Recompute the solver-consequence analysis

No model calls, LP solves, or exact reconstructions are required; the script uses the released operator arrays.

```bash
python scripts/analyze_solver_consequences_v2.py --root .
# equivalently
make solver-analysis
```

Authoritative output is written to `derived/solver_consequences_v2/`. Expected checks are:

```text
operators analysed                                  11
released exact constructions CG-compatible          7/7
MOLE/Corbino--Castillo references CG-compatible     0/4
order-six weighted-symmetry residual                0.5223512407
order-six diagnostic symmetric-part CG error        0.278365562
order-six GMRES original-system error               about 1.0e-9
```

The preserved user notebook and result archive are provenance artifacts. Small Krylov iteration-count differences across environments are expected and do not affect any reported claim.

