# Experiment-to-analysis Claim Map

This document identifies the exact source of the main analysis statements.

## Campaign design

| analysis statement | Source |
|---|---|
| 1,200 deterministic solver evaluations | `runs/v11_original_results.zip` → `tables/open_search_all_budgeted_records.csv`; recomputed in `derived/open_search_records_with_external_pass.csv` |
| 720 non-LLM + 480 accepted live-LLM solver records | same table, grouped by `strategy` |
| 529 raw live generations | archive → `open_program/llm/open_program_calls.jsonl`; summarized in `derived/actual_llm_costs.csv` |
| Three usable live models and one failed capability probe | archive → `provenance.json`, `model_capabilities` |

## Primary common-external endpoint

The independent endpoint is implemented by `common_external_pass()` in `scripts/postprocess_v11.py`. It uses one fixed threshold set and ignores proposer-selected caps. It is threshold-independent across arms, not necessarily stricter than the notebook's `hard_pass_all` gate. In the archived campaign, 249 programs pass both endpoints, 142 pass only the external endpoint, and none pass only the notebook gate. The per-arm reconciliation is stored in `derived/endpoint_by_strategy.csv`; the 2×2 containment table is `derived/endpoint_containment.csv`.

| Claim | Evidence |
|---|---|
| Full metrics: 66/120 = 55.0% | `derived/common_external_hit_rates.csv` |
| Illumination: 64/120 = 53.3% | same |
| Uniform random: 32/240 = 13.3% | same |
| Holm-adjusted `p = 0.0117` for full metrics and illumination vs random | same; exact seed-level sign-flip test in postprocessor |
| Only expert-informed AUC survives multiplicity at the 12-call budget | `derived/common_external_auc.csv` |

## Costs

Every raw generation, including malformed, duplicate, preflight-rejected, and repair calls, is counted from `open_program_calls.jsonl`.

| Claim | Evidence |
|---|---|
| Full metrics: 775,493 tokens, 20.3 API minutes, 85.1 passes/Mtok | `derived/actual_llm_costs.csv` |
| Illumination: 797,685 tokens, 24.7 API minutes, 80.2 passes/Mtok | same |

## Exact candidates

| Archive condition | Certificate | Operator array |
|---|---|---|
| No archive | `derived/exact_certificates/no_archive_*.json` | `derived/operators/no_archive_*_m200.npz` |
| Structure only | `derived/exact_certificates/structure_only_*.json` | `derived/operators/structure_only_*_m200.npz` |
| Full metrics | `derived/exact_certificates/full_metrics_*.json` | `derived/operators/full_metrics_*_m200.npz` |
| Illumination | `derived/exact_certificates/illumination_*.json` | `derived/operators/illumination_*_m200.npz` |

The summary table is `derived/exact_top_candidate_per_condition.csv`.

## Leading order-six comparison

The analysis's leading structure-only candidate is:

```text
prog_k6_block_psd_reflection_min_next_moment_973378905933
```

At `m = 160`, its values are read from `derived/extended_exact_candidate_validation.csv`. The MOLE and prior positive-diagonal comparison rows are preserved from the immutable v11 run in `runs_source_open_same_mesh_comparison.csv`.

The reported 25.4% spectral-radius reduction and 62.7-fold PDE-error reduction are direct arithmetic comparisons of these rows.

## Extended refinement

`derived/extended_exact_candidate_validation.csv` contains every exact candidate at:

```text
m = 40, 64, 80, 96, 120, 160, 200, 320, 480, 640.
```

`derived/extended_convergence_rates.csv` reports fitted windows together with `monotone_error_decrease`, `roundoff_limited`, and `rate_interpretable`. Candidate late-window rates are used to avoid presenting the pre-asymptotic `m = 40,80,160` slope as an asymptotic order. The MOLE reference reaches a numerical floor at `m = 480` and rises at `m = 640`; its `160-320-640` rate is marked non-interpretable.

## Perturbations

`derived/perturbation_trials.csv` contains every Monte Carlo trial; `derived/perturbation_summary.csv` contains means and variability. Perturbations are normalized to

```text
||ΔL||₂ = γ ||L||₂
```

for dense and boundary-supported cases.


## Weighted-system and linear-solver consequence

The solver experiment is downstream of discovery and does not enter candidate selection.

| analysis statement | Evidence |
|---|---|
| All seven released exact constructions admit the certified SPD system `-Q_I L_I`; none of the four MOLE/Corbino--Castillo references is CG-compatible in its native quadrature | `derived/solver_consequences_v2/tables/symmetric_system_availability.csv` |
| Order-six reference weighted-symmetry residual `0.522351` and minimum eigenvalue of the weighted symmetric part `-26.000485` | same |
| Diagnostic CG on the order-six reference symmetric part returns relative solution error `0.278366` despite a small surrogate-system residual | `derived/solver_consequences_v2/tables/poisson_solver_comparison.csv` |
| GMRES on the original order-six reference returns relative solution error about `1.0e-9` | same |
| The same SPD-availability distinction occurs for backward Euler with `dt/h^2 = 5` | `derived/solver_consequences_v2/tables/implicit_heat_step.csv` |

The forced-CG calculation solves a different, symmetrized system and is used only to interpret the residual. It is not a recommended solver and is not evidence that the nonsymmetric reference is unsolvable or slower. The negative eigenvalue and the positive logarithmic energy rate reported in the downstream analysis are two views of the same quadratic-form obstruction.

## Validity qualifications

| Qualification | Evidence |
|---|---|
| Model-role schedules are not paired across archive conditions | `derived/schedule_pairing_audit.csv` |
| Full metrics and illumination bundle metrics with diagnostic refinement | notebook prompt/construction cells and archived raw calls |
| Mechanism prediction is too sparse for a calibration claim | original `open_mechanism_calibration.csv`; only eight accepted rows contain optional prediction fields |
| Novelty library is incomplete | original `open_novelty_library_coverage.json` and partial comparison table |
| Frontier-probe quota declared but unused | notebook configuration and preflight code |
## Reviewer-triggered audits

| Claim | Evidence |
|---|---|
| External endpoint contains the notebook gate in this run: 249 both, 142 external-only, 0 notebook-only | `derived/endpoint_containment.csv` |
| Per-strategy notebook-to-external rate changes | `derived/endpoint_by_strategy.csv` |
| Eligible refinement: external 20/42 refined vs 25/55 fresh (`p = 0.840`); notebook gate 16/42 vs 20/55 (`p = 1.00`) | `derived/refinement_effect_audit.csv` |
| 637/638 diagnosed infeasibilities bind on the endpoint-supported extended-Gauss system | `derived/infeasibility_structure_audit.csv` |
| Ten distinct expert-prior sequences, each with 12/24 external passes | `derived/expert_prior_seed_audit.csv` |
| MOLE raw weight ratio 1.897312 is not a certified norm condition because the similarity residual is 0.481 | `runs_source_open_same_mesh_comparison.csv` |

The point-by-point decision record is `docs/REVIEW_COMMENT_AUDIT.md`.


## Descriptive v12/v12.1 follow-up

These results do not replace the primary v11 campaign.

| analysis statement | Evidence |
|---|---|
| v12 failures: 1,884 provider-transport failures, 120 parser-selected schema echoes, 3 unterminated JSON objects; comparison invalid | `derived/followups/v12_harness_call_audit.csv`, `v12_arm_completion.csv` |
| v12 exact diagonal candidate: `kappa_Q=1.253266`, `rho h^2=6.165951` | `derived/followups/v12_exact_candidates.csv`, exact certificate under `derived/followup_exact_certificates/` |
| v12.1 health: 1036/1051 schema-valid generations, 612/1051 arm-distinct programs, predictions 569/572 | `derived/followups/v12_1_generation_health.csv`, `v12_1_prediction_coverage.csv` |
| Descriptive 2x2, missing-as-failure sensitivity, and two-stage completion caveat | `v12_1_factorial_summary.csv`, `v12_1_missing_as_failure_sensitivity.csv`, `v12_1_missing_as_failure_fisher.csv`, `v12_1_two_stage_completion_stratified.csv` |
| Eight incomplete arms, 424 duplicates, 20 schedule mismatches | `v12_1_completion_summary.csv`, `v12_1_duplicate_summary.csv`, `v12_1_schedule_mismatches.csv` |
| v12.1 exact cold candidate: `kappa_Q=1.199150` | `v12_1_exact_candidates.csv`, exact certificate under `derived/followup_exact_certificates/` |
| Expert-prior self-declared minus common-external gap: 0.6667 (random 0.0553; surrogate 0.0441) | `derived/followups/v12_1_gate_standard_gap.csv` |

Because the follow-up comparison validity flag is false, the article labels these rates descriptive and uses exact certificates only as mathematical evidence about the constructed objects.

## Semidiscrete energy consequence

**analysis claim.** The leading exact candidate is contractive in its certified $Q$ norm and has normalized weighted-symmetry residual `1.23e-16`, whereas the order-six reference has residual `0.522` under its native quadrature and exhibits 1.066 maximum transient $Q$-energy amplification; both have `RK4 dt_max/h^2 = 0.4517`. The transient maximum occurs inside the tested window at `t/h^2 = 0.333` and then decays.

**Evidence.** `derived/downstream_analysis_v3/headline_downstream_metrics.csv`, `headline_energy_transient_history.csv`, and `downstream_report_v3.json`, generated by `scripts/analyze_downstream_v3.py`. The comparison is norm-specific and does not imply that the reference lacks every possible Lyapunov norm.

## Robust partial novelty screen

**Claim boundary.** No match is found among the loaded MOLE/Corbino--Castillo references under direct corner-block and fixed-length fingerprint comparisons. That family is screened directly, but parameterized/compact Castillo--Grone extensions and generalized block-norm staggered families remain incomplete, so literature-level novelty remains unresolved.

**Evidence.** `derived/downstream_analysis_v3/novelty_block_comparisons.csv`, `novelty_fingerprint_distances.csv`, and `partial_novelty_gate.json`, generated by `scripts/analyze_downstream_v3.py`; source amendment preserved in `source_artifacts/mimetic_analysis_v3.zip`.

## Linear-solver consequence

**analysis claim.** All seven released exact constructions admit an SPD weighted Poisson system at `m = 200`; none of the four MOLE/Corbino--Castillo reference systems is CG-applicable in its stored/native quadrature. For the order-six reference, CG on the symmetric part is a diagnostic that converges to a solution with relative error `0.2783656`, whereas GMRES and a dense direct solve on the original nonsymmetric operator give approximately `1.0e-9` error. This is an availability-of-guarantees result, not a speed or solvability claim.

**Evidence.** `derived/solver_consequences_v2/tables/symmetric_system_availability.csv`, `poisson_solver_comparison.csv`, `implicit_heat_step.csv`, and `solver_experiment_report.json`, generated by `scripts/analyze_solver_consequences_v2.py`. The order-six symmetric-part minimum eigenvalue `-26.0005` and the positive downstream energy-growth rate are two normalizations of the same quadratic-form obstruction.
