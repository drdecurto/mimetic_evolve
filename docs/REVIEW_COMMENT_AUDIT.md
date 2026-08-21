# Audit of independent review comments

This audit checks the six supplied comments and the convergence question against the immutable v11 run and the independently derived summary tables. No new LLM calls or numerical search experiments were required.

## Decision summary

| Comment | Decision | Action |
|---|---|---|
| 1. External endpoint differs from the notebook gate | Correct and important | Revised the verifier and statistical-endpoint text; added containment and per-strategy audit CSVs |
| 2. Expert-prior figure caption | Correct | Corrected the caption and explained the constant seed-level rate and sign-flip floor |
| 3. Full-SPD proposition and block-norm motivation | Correct and mathematically important | Rewrote the abstract, introduction, and proposition discussion to distinguish a fixed closure from a changed closure |
| 4. Refinement and infeasibility results | Substantively correct; two quoted counts were off by one in the supplied package | Added the corrected randomized-refinement analysis and exact infeasibility counts |
| 5. MOLE norm-condition dash | Correct | Renamed the table column and explained why the raw ratio is not a certified norm condition |
| 6. Archive-condition wording and strongest-candidate tension | Correct | Corrected the abstract and explicitly separated best-candidate quality from strategy-level yield |
| MOLE late convergence window | Correct | Marked the reference tail as round-off limited and excluded it from asymptotic interpretation |

## 1. Fixed external endpoint versus the notebook gate

The two endpoints are not identical:

- `hard_pass_all` is the notebook's in-run gate and includes program-selected caps.
- `external_pass` is this release's post-run endpoint with one fixed threshold set for all arms.

The observed containment table is:

| Notebook gate | External fail | External pass |
|---|---:|---:|
| Fail | 809 | 142 |
| Pass | 0 | 249 |

Thus the notebook gate is an empirical subset of the external endpoint in this campaign. The external endpoint is not stricter; it is **threshold-independent across arms**. It expands weak arms more strongly than the full-feedback arm:

| Strategy | Notebook rate | External rate |
|---|---:|---:|
| Uniform random | 2.1% | 13.3% |
| ExtraTrees surrogate | 3.3% | 23.8% |
| LLM structure only | 9.2% | 26.7% |
| LLM full metrics | 50.0% | 55.0% |

Consequently, the full-metrics/random ratio falls from 24.0 under the in-run gate to 4.1 under the common endpoint. This is a more conservative comparative result and is now stated explicitly.

Evidence: `derived/endpoint_containment.csv` and `derived/endpoint_by_strategy.csv`.

## 2. Expert-informed prior

The expert arm does **not** use the same program sequence at every seed. There are ten distinct sequence hashes. What is constant is the outcome: every seed produces exactly 12 external passes from 24 solver calls. This is why the bootstrap interval has zero width.

Because all ten paired rate differences against uniform random are positive, the exact two-sided sign-flip test reaches its discrete ten-pair floor:

\[
2/2^{10}=0.001953125.
\]

The analysis now states that this is a consistent directional comparison but does not provide within-expert-arm rate variation.

Evidence: `derived/expert_prior_seed_audit.csv`.

## 3. Scope of the weighted-similarity proposition

The corrected proposition assumes symmetric positive-definite `Q` and `P` together with Dirichlet-compatible scalar-norm separation and a boundary term satisfying `E^T B G E = 0`. A non-real spectrum rules out an SPD self-adjoint similarity for the fixed Dirichlet block, but it does not contradict the more general Corbino--Castillo extended-Gauss identity whose boundary operator extends over closure rows. A block norm cannot rescue the fixed MOLE/Corbino--Castillo matrices merely by reweighting them; the closure and boundary identity must change.

The search remains meaningful because it changes the boundary closure. Block norms then enlarge the feasible class for those newly compiled closures. The abstract, introduction, and proposition discussion now make this distinction explicit.

## 4. Diagnostic refinement and infeasibility

The qualitative comment is correct, but the current package gives slightly different counts from those quoted.

Among the 97 refinement-eligible full-metric and illumination calls:

| Endpoint | Refined | Fresh | Fisher p |
|---|---:|---:|---:|
| Notebook gate | 16/42 | 20/55 | 1.000 |
| Common external endpoint | 20/42 | 25/55 | 0.840 |

There is no measurable one-step refinement effect under either endpoint.

For infeasibility, 638 LP failures have a diagnosed binding group:

- 637/638 (99.8%) bind on `extended_gauss`;
- 1/638 binds on `gradient_boundary_moments`.

There are 13 further compilation failures without a binding-group diagnosis: twelve singular systems and one residual-only infeasibility. The review comment's `638/639` should therefore be corrected to `637/638` for the supplied package.

Evidence: `derived/refinement_effect_audit.csv` and `derived/infeasibility_structure_audit.csv`.

## 5. MOLE norm condition

The archived same-mesh comparison computes a raw ratio of `1.897312` from the supplied reference weights, but its weighted-similarity residual is `0.481`. The relation required to interpret that ratio as a symmetrizing norm condition therefore fails.

The table now reports `n/a` under **Certified** `kappa_Q` and explains that the quantity was not withheld: it is not a valid norm-conditioning comparison.

## 6. Terminology and best-object versus policy yield

The four exact candidates are one per **archive condition**, not one per feedback condition. The abstract is corrected.

The strongest exact candidate came from structure only, although that arm's aggregate external yield, 32/120 = 26.7%, does not significantly exceed uniform random after Holm correction (`p = 0.3281`). The analysis now names this tension directly. Finding one strong object and repeatedly generating valid objects are different outcomes.

## 7. Reference convergence and round-off

The MOLE order-six mixed-PDE error decreases to approximately `1.44e-12` at `m = 480` and then rises to `1.20e-11` at `m = 640`. The nominal rate `3.375` over `(160, 320, 640)` is therefore round-off contaminated and should not be interpreted.

The revised figure uses a dashed final reference segment and annotates the round-off floor. `derived/extended_convergence_rates.csv` now contains `roundoff_limited` and `rate_interpretable` fields.

## Overall decision

All six comments improve the analysis. Five are exactly correct. The fourth is correct in substance but its two quoted numerators/denominators require the corrections above. The convergence concern is also correct. The revised article incorporates all seven points without changing the underlying mathematical result or rerunning the live campaign.

## Minor-comment and v12/v12.1 update

A subsequent audit adds three analysis clarifications and evaluates the later v12/v12.1 campaigns. The ten-seed sign test is explicitly described as discrete and saturated; the v11 one-step repair contrast is described as randomized within the failed-predecessor eligible stratum; and the fourth-model exclusion is attributed to the schema-echo extraction behavior of the harness rather than to model capability. The v12.1 2x2 is reported as descriptive only because completion, duplicate, pairing, and model-roster checks fail. See `MINOR_COMMENTS_AND_V12_FOLLOWUP_AUDIT.md` for the full decision record.
