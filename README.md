# mimetic_evolve

Verifier-guided discovery of exact high-order mimetic operators.

This repository studies a narrow role for large language models in numerical analysis. A model
proposes a **typed operator-construction program** — target order, norm class, boundary
architecture, row-dependent supports, and optimisation objective. It never supplies the accepted
coefficient table and never judges correctness. A deterministic compiler, an independent
spectral/PDE verifier, and a coupled exact rational reconstruction decide what survives.

Everything here is recomputable from the archived runs. No API key and no new model calls are
needed to reproduce any reported number.

## Repository scope

This GitHub repository contains the code, notebooks, immutable run archives, derived data, exact
certificates, and reproducibility documentation. The journal manuscript and its submission source
are distributed separately and are intentionally not committed here.

The compact linear-algebra summary used by the article is generated from
`derived/solver_consequences_v2/solver_guarantees_table.csv`.

## What the search found

Four order-six block-norm constructions — one from each archive condition — were independently
recompiled and exactified. The leading construction (order-six interior, order-four boundary) has
a real spectrum, no detected low-frequency pollution through `m = 640`, a scaled spectral radius
of `6.165962`, and a manufactured-PDE RMS error of `8.91e-8` at `m = 160`. Against an earlier
positive-diagonal order-six construction it lowers the spectral-radius constant by 25.4% and the
tested PDE error by a factor of 62.7.

The reference arrays are the MOLE implementation of the Corbino–Castillo construction, verified
against a pinned MOLE v1.2.0 source snapshot. They remain more accurate on that manufactured
problem, but carry four non-real boundary modes in the tested Dirichlet blocks. The
Corbino–Castillo boundary identity itself remains valid: the complex modes show that its
closure-supported boundary term does not yield the endpoint-supported SPD Dirichlet similarity
that the discovery compiler imposes.

### Search-arm yield

The primary campaign contains 1,200 deterministic solver evaluations, 480 of them from accepted
live-model programs. Under a common verifier whose thresholds are fixed independently of
proposer-selected caps:

| Search arm | External passes / calls | Rate |
|---|---:|---:|
| Model with full metric feedback | 66 / 120 | 55.0% |
| Model with illumination archive | 64 / 120 | 53.3% |
| Expert-informed construction prior | 120 / 240 | 50.0% |
| Uniform random programs | 32 / 240 | 13.3% |

Paired sign-flip randomisation comparisons of full metrics and illumination against uniform
random survive Holm correction (`p = 0.0117`). The test enumerates all `2^10` sign assignments of
the seed-level differences while retaining their magnitudes, so raw values lie on a `1/1024` grid
with a two-sided floor of `2/1024`; identical adjusted values therefore do not imply equal
effects, and magnitude must be read from rates and intervals.

The expert-informed prior remains the strongest trajectory-level control. **The supported claim
concerns verified yield, not that model-driven search dominates expert design.**

### Downstream consequences of the certified structure

At `m = 200`, all seven released exact constructions admit the symmetric positive-definite
weighted system `-Q_I L_I`, so conjugate gradients is mathematically applicable. None of the four
reference blocks has that property under its native quadrature; the order-six weighted-symmetry
residual is `0.522` against `1.2e-16` for the certified constructions.

Applying CG to the symmetric *part* of the order-six weighted reference system converges to a
small residual but returns a solution with relative error `0.278`, while a dense direct solve and
GMRES on the original nonsymmetric block both reach approximately `1.0e-9`. That calculation is
**diagnostic only**: it quantifies the weighted-symmetry residual and documents the availability
of SPD guarantees — energy-norm convergence bounds, a three-term fixed-memory recurrence,
symmetric preconditioning. It is not evidence that the reference is hard to solve, and iteration
counts are archived but never used for cross-family speed claims.

The minimum eigenvalue `-26.0005` of the order-six reference symmetric part and the positive
logarithmic energy rate reported by the downstream analysis are two normalisations of the same
quadratic-form obstruction, not independent evidence.

## What this repository does not establish

The exact constructions are certified; their **novelty is not**. The screen is topology-scoped:
among loaded order-six staggered references the smallest normalised corner-block distance is
`0.608`, with no direct or fingerprint match. That closes the Corbino–Castillo item in the
partial library. Parameterised or compact higher-order Castillo–Grone extensions and
generalised/block-norm staggered families remain outstanding, and classical nodal
summation-by-parts families need an explicit topology map before coefficient equivalence is
meaningful. `novelty_claim_supported` is therefore `false`, and stays so by design until the
library is completed.

The archive comparison is also **not fully causal**: model/role schedules were not paired across
archive conditions in the primary run. Within calls eligible because a preceding proposal failed,
one-step refinement was assigned by a coin flip, and that conditional contrast is null (20/42
external passes after refinement against 25/55 for fresh proposals, Fisher `p = 0.840`).

Identification against families outside the current screen is welcome — the exact rational
coefficients and the screening scripts are all here.

## Later engineering follow-ups

Two later campaigns are preserved without replacing the primary inference.

**v12 is a failed harness run.** Its comparison is invalid: the JSON extractor selected an echoed
request schema in 120 GLM-5.2 generations and in the excluded Qwen3.5 capability probe. It still
produced an exactly certified order-six diagonal-norm closure with `kappa_Q = 1.253266`, a
mathematical artifact showing the obstruction is specific to the fixed Corbino–Castillo closure
rather than to every order-six diagonal norm.

**v12.1 is a descriptive mechanism follow-up.** Transport/parse success reached
`1036/1051 = 98.6%`, of which `612/1036 = 59.1%` were arm-distinct; the remaining 424 repeated an
already used program. The observed 2×2 rates were cold `15/120`, diagnostic-only `16/120`,
archive-only `42/107`, full-feedback `38/114`. Treating every unfilled call as a failure yields
`12.5%`, `13.3%`, `35.0%` and `31.7%`; archive-only still exceeds cold (`p = 6.38e-5`),
diagnostic-only remains null (`p = 1.00`), and adding diagnostics to the archive stays
non-significant (`p = 0.681`). These are **not confirmatory**: 8 of 50 arms starved, 20 model/role
schedule mismatches followed circuit-breaker substitution, and most accepted calls came from one
model. It also produced an exactly certified cold order-six block-norm candidate with
`kappa_Q = 1.199150`, the smallest certified bound in the series — a usable certificate from a run
that is not valid evidence about search policy.

## Layout

```text
.
├── notebooks/     Immutable discovery notebook, follow-ups, and analysis notebooks
├── runs/          Immutable run archives (v11 primary, v12 failed, v12.1 follow-up)
├── derived/       Recomputed analysis outputs
│   ├── exact_certificates/            Coupled exact rational/positivity certificates
│   ├── operators/                     Promoted exact operator arrays at m=200
│   ├── followups/                     v12/v12.1 transport, 2x2, duplicate, schedule audits
│   ├── followup_exact_certificates/   Later exact artifacts (not search-policy evidence)
│   ├── downstream_analysis_v3/        Energy, time-stepping, and novelty diagnostics
│   ├── solver_consequences_v2/        Weighted-system and Krylov diagnostics
│   ├── reference_attribution_audit/   Pinned MOLE source matching
│   └── figures/                       Regenerated figures
├── scripts/
│   ├── postprocess_v11.py                   Recomputes primary endpoints from the v11 archive
│   ├── audit_v12_followups.py               Recomputes descriptive v12/v12.1 audits
│   ├── audit_mole_reference_attribution.py  Audits MOLE provenance and boundary identity
│   ├── analyze_downstream_v3.py             Energy, time-stepping, novelty diagnostics
│   ├── analyze_solver_consequences_v2.py    Weighted-system and solver diagnostics
│   ├── compare_derived.py                   Diffs a recomputation against the shipped outputs
│   └── verify_release.py                    Integrity, claim-count, provenance, and secret audit
├── docs/          Provenance, limitations, run ledger, and audit notes
├── source_artifacts/  Superseded exploratory bundles, preserved for provenance
└── Makefile
```

## Reproduce the analysis

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

make extract                                   # unpack the immutable v11 archive
make postprocess DERIVED=derived_reproduced    # recompute the primary endpoints
make compare-derived DERIVED=derived_reproduced
make downstream-analysis
make solver-analysis
make verify
```

Full postprocessing performs exact symbolic reconstruction and takes several minutes;
`make postprocess-quick DERIVED=derived_quick` is a faster engineering check. Recomputed results
are written to the directory named by `DERIVED=` and never modify the raw archives.

Start here to understand what was measured:

1. `docs/RESULT_PROVENANCE.md` — where every reported number comes from.
2. `derived/exact_certificates/` and `derived/operators/` — the exact constructions themselves.
3. `docs/MOLE_REFERENCE_ATTRIBUTION_AND_BOUNDARY_OPERATOR_CORRECTION.md` — read before
   interpreting any historical reference label inside the archives.
4. `docs/LIMITATIONS.md` and `docs/V12_V12_1_FOLLOWUP_AUDIT.md` — read before using any
   later-run number.
5. `docs/REPRODUCIBILITY.md` — complete offline reconstruction protocol.

## Re-run the live campaign

Open `notebooks/mimetic_operator_discovery_v11.ipynb` in Jupyter or Colab and supply the
credential from outside the notebook:

```bash
export NEBIUS_API_KEY="..."
```

In Colab use the Secrets panel with the name `NEBIUS_API_KEY`. The notebook discovers and
capability-probes served model IDs; do not assume the August 2026 catalogue is still current. A
live re-run is a **new experiment** and should be archived under a new version rather than
overwriting the supplied archives.

## Environment

The live run used Python 3.12.13 with NumPy 2.0.2, SciPy 1.16.3, pandas 2.2.3, Matplotlib 3.10.0,
SymPy 1.14.0, scikit-learn 1.6.1 and HTTPX 0.28.1. Postprocessing additionally uses statsmodels.
Pinned versions are in `requirements.txt` and `environment.yml`.

## Licence

The notebooks and numerical code contain Python translations of MOLE operator-generation
routines, and are distributed under **GPL-3.0-or-later**. Documentation, derived tables, and independently generated figures are distributed under
**CC BY 4.0**. See `NOTICE.md` for the boundary between code, data, and documentation.

## Citation

See `CITATION.cff`.
