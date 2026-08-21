# Independent Assessment of the v11 Experiments

## What improved materially

v11 addresses the largest interpretive weakness of the earlier campaigns: proposer-selected caps no longer determine this release's main pass rate. The independent postprocessor recomputes one common external endpoint for every strategy. Under that endpoint, full metrics and illumination retain high verified yield (55.0% and 53.3%), while uniform random search reaches 13.3%. The endpoint is threshold-independent, not uniformly stricter: it accepts 142 programs rejected by the notebook gate and rejects none accepted there. This expands random search from 2.1% to 13.3% but full metrics only from 50.0% to 55.0%, reducing the relative headline from 24.0× to 4.1×. The comparative claim is therefore more conservative and is not an artifact of models choosing permissive constraints.

The run is also sufficiently replicated for a first paper-level comparison: ten seeds per search condition, fixed solver-call budgets, complete raw-call cost accounting, and exact paired seed-level tests. The campaign produces exact promoted candidates from every LLM archive condition, not just one anecdotal hit.

## Strongest mathematical result

The most attractive exact trade-off is the structure-only GLM-5.2 order-6/interior, order-4/boundary block-norm construction. It restores a real weighted spectrum and nearly the reference spectral-radius constant, without detected spectral pollution through `m = 640`. Compared with the earlier positive-diagonal candidate, it lowers the spectral-radius constant by 25.4% and the tested mixed-frequency PDE error by 62.7×.

This is a serious numerical-analysis result. It is not yet a proof that the coefficient family is absent from the complete SBP literature, and it does not dominate the MOLE/Corbino--Castillo reference in absolute PDE error.

The fact that this strongest exact candidate comes from structure only should not be confused with strategy-level superiority. Structure only reaches 26.7% verified yield and does not significantly exceed uniform random after Holm correction (`p = 0.3281`). Best-object quality and repeated-seed proposal yield are distinct endpoints.

## Strongest AI-method result

The language model is useful at the level of structural representation. The full-feedback packages move the deterministic compiler toward a much denser region of valid programs than uniform random sampling. Cost-normalized yield is also strongest for full metrics.

The expert-informed construction prior remains stronger on the best-so-far trajectory endpoint. The correct claim is therefore that verifier feedback improves LLM proposal yield—not that LLMs replace expert numerical analysts.

## Remaining threats to validity

1. Model/role schedules differ across archive conditions because the notebook uses a condition-dependent, process-randomized Python hash.
2. Full metrics and illumination bundle archive metrics with diagnostic repair. A randomized eligible-call audit finds no direct repair effect (external `20/42` refined versus `25/55` fresh, Fisher `p = 0.840`), but the archive mechanism is still not causally isolated.
3. The expert prior is highly informed; the ExtraTrees control is comparatively weak.
4. Above-frontier programs are still removed by preflight despite a declared probe quota.
5. The novelty library is incomplete.
6. The study remains one-dimensional and uses an inner approximation to the full banded-SPD cone.

These limitations are stated explicitly in the analysis. They motivate a controlled follow-up, but they do not invalidate the exact operator constructions or the recorded yield comparison against uniform random search.
