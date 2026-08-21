# v11 Run Ledger

## Deterministic solver records

| Group | Design | Records |
|---|---:|---:|
| Uniform random | 10 seeds × 24 calls | 240 |
| ExtraTrees surrogate | 10 × 24 | 240 |
| Expert-informed construction prior | 10 × 24 | 240 |
| LLM no archive | 10 × 12 | 120 |
| LLM structure only | 10 × 12 | 120 |
| LLM full metrics | 10 × 12 | 120 |
| LLM illumination | 10 × 12 | 120 |
| **Total** |  | **1,200** |

## Live-generation ledger

| Archive condition | Raw generations | Accepted solver programs | Input tokens | Output tokens | API seconds |
|---|---:|---:|---:|---:|---:|
| Full metrics | 134 | 120 | see CSV | see CSV | 1,220.55 |
| Illumination | 131 | 120 | see CSV | see CSV | 1,480.53 |
| Structure only | 131 | 120 | see CSV | see CSV | 1,233.11 |
| No archive | 133 | 120 | see CSV | see CSV | 1,440.46 |
| **Total** | **529** | **480** |  |  |  |

Canonical cost values are in `derived/actual_llm_costs.csv`.

## Live models retained after capability probing

```text
zai-org/GLM-5.2
MiniMaxAI/MiniMax-M3
nvidia/Cosmos3-Super-Reasoner
```

`Qwen/Qwen3.5-397B-A17B` was not retained by the structured-object probe. Later debugging showed that the left-to-right JSON extractor could select an echoed request schema rather than the terminal answer; this exclusion reflects the harness, not a demonstrated model limitation.

## Endpoint reconciliation

The original notebook gate and this release endpoint are both retained. `derived/endpoint_by_strategy.csv` records each strategy's counts. Across all 1,200 calls, 249 pass both, 142 pass only the common external endpoint, and none pass only the notebook gate.

## Diagnostic audits

- Refinement-eligible calls: 42 refined and 55 fresh; see `derived/refinement_effect_audit.csv`.
- Group-diagnosed LP infeasibilities: 637 endpoint-supported extended-Gauss and 1 gradient-boundary-moment; see `derived/infeasibility_structure_audit.csv`.
- Expert-informed arm: ten distinct sequence hashes, each yielding 12/24 external passes; see `derived/expert_prior_seed_audit.csv`.


## Follow-up run ledger

| Run | Purpose | Raw generations | Solver records | Completed arms | Comparison valid |
|---|---|---:|---:|---:|---|
| v12 | paired-schedule and 2x2 harness attempt | 2,502 | 266 | 11/50 | no |
| v12.1 | transport-repaired 2x2 mechanism follow-up | 1,051 | 572 | 42/50 | no |

For v12, the 2,007 failed generations partition into 1,602 HTTP 503 responses, 282 provider read timeouts, 120 parser-selected schema echoes, and 3 unterminated JSON objects. For v12.1, 1,036 generations reached a schema-valid normalized output, 12 failed in transport, and 3 failed schema/parse validation; only 612 were arm-distinct after within-arm deduplication, leaving 424 successful duplicates. Condition-level solver yields were `15/120`, `16/120`, `42/107`, `38/114`, and `33/111` for cold, diagnostic only, archive only, full feedback, and two-stage. Under missing-as-failure imputation the corresponding full-budget rates are `12.5%`, `13.3%`, `35.0%`, `31.7%`, and `27.5%`. See `derived/followups/` for the full audit.

## Downstream solver-analysis ledger

This is not a search campaign and makes no LLM calls. The analysis contains 11 operator instances at `m = 200`: four primary exact candidates, three exact follow-up artifacts, and four MOLE/Corbino--Castillo references. All seven exact constructions admit an SPD weighted system; none of the four reference systems is CG-applicable in its native quadrature. See `derived/solver_consequences_v2/`.


## Downstream solver-consequence analysis

This deterministic analysis loads 11 released operators at `m = 200`: four primary exact candidates, three exact follow-up candidates, and four MOLE/Corbino--Castillo references. It performs no model calls and no discovery search.

| Inventory/result | Count or value |
|---|---:|
| Operators loaded | 11 |
| Exact constructions CG-compatible in certified weighted form | 7/7 |
| References CG-compatible under native quadrature | 0/4 |
| Order-six diagnostic symmetric-part CG solution error | 0.278366 |
| Order-six GMRES original-system solution error | approximately `1.0e-9` |

Iteration counts are archived but are not treated as cross-family performance measurements because solver work, memory, restart, preconditioning, and BLAS/SciPy details differ.



## Solver-consequence diagnostic

This post hoc deterministic analysis makes no model calls and does not add search-policy observations. It loads 11 operators at `m=200`: four primary exact candidates, three exact follow-up artifacts, and four MOLE/Corbino--Castillo references.

| Group | Operators | Weighted SPD/CG applicable |
|---|---:|---:|
| Primary exact | 4 | 4 |
| Exact follow-up | 3 | 3 |
| MOLE/Corbino--Castillo reference, native quadrature | 4 | 0 |

The canonical outputs are in `derived/solver_consequences_v2/`. The source notebook executed 12 cells without error and is preserved for provenance, but the authoritative script uses stable terminology and deterministic direct-solve checks. Krylov iteration counts may vary slightly with SciPy/BLAS; no reported claim depends on them.
