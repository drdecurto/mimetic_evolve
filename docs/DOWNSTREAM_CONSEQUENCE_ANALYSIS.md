# Downstream consequence and novelty analysis

## Why this analysis was added

The exact weighted identity is more than a spectral certificate. For the semidiscrete heat equation

\[
\dot u=L_Iu,\qquad E_Q(u)=\tfrac12u^TQ_Iu,
\]

it gives an energy estimate when the compiled closure and norm satisfy the endpoint-supported extended-Gauss relation. The analysis also checks whether the non-real reference modes affect the explicit Runge--Kutta stability limit and records the status of the partial novelty screen.

## Corrected energy quantity

The authoritative relative energy rate is the largest generalized eigenvalue of

\[
(L_I^TQ_I+Q_IL_I)v=\mu Q_Iv.
\]

The exploratory input archive `source_artifacts/mimetic_analysis_v2.zip` evaluated an unnormalised Euclidean symmetric part and is retained only for provenance. Its quoted high-order growth magnitudes are not used in the analysis. Indefinite reference weights are excluded from energy claims.

## Headline result

At `m=200`, the leading exact candidate is contractive in its certified norm. Its normalized weighted-symmetry residual, `||Q L - L^T Q||_2 / ||Q L||_2`, is `1.23e-16`, compared with `0.522` for the order-six MOLE/Corbino--Castillo reference under its native positive quadrature. Consistent with the reference's non-real spectrum, the fixed reference closure admits no positive-definite self-adjoint similarity; the candidate does.

In the reference quadrature, the dimensionless maximal relative energy rate is `h^2 mu_max = 0.3280`, and the finite-time energy amplification reaches approximately `1.0656` at `t/h^2 = 0.333`. The maximum is interior to the tested interval `t/h^2 in [0, 0.6]`, after which the amplification decays. The candidate remains below one for positive time. This comparison is norm-specific and does not exclude a different Lyapunov norm for the reference.

Both operators have essentially the same classical RK4 stability limit, `dt_max/h^2 = 0.4517`. The recovered weighted structure therefore supplies a certified energy estimate and an SPD similarity; it does not enlarge the explicit CFL limit in this test.

## Novelty status

The amended exploratory analysis corrected two implementation defects in the partial novelty screen: support profiles may be stored as strings or sequences, and unequal closure widths require fixed-length fingerprints rather than undefined vector comparisons. The authoritative screen now canonicalizes boundary blocks under scale, sign, and reflection and supplements them with symmetrically normalized, fixed-length singular-value fingerprints. It finds no match among the loaded MOLE/Corbino--Castillo references. The loaded Corbino--Castillo item is closed. Parameterized or compact higher-order Castillo--Grone extensions and generalized/block-norm staggered constructions remain outstanding; Strand and Mattsson--Nordstroem are cross-topology comparators requiring an explicit map. A documentary statement that a family is not directly comparable records scope but does not close the novelty gate. The repository therefore continues to use **exact LLM-originated candidate**, not **new operator family**.

## Reproduction

```bash
python scripts/analyze_downstream_v3.py
jupyter nbconvert --to notebook --execute \
  notebooks/mimetic_downstream_consequences_v3.ipynb \
  --output mimetic_downstream_consequences_v3_executed.ipynb \
  --output-dir notebooks
```

Authoritative outputs are in `derived/downstream_analysis_v3/`.


## Provenance warning

The original exploratory notebook outputs remain inside `runs/mimetic_analysis_v3_user_results.zip` and the source archives. They include an order-eight Euclidean growth value near `844.9`; that value is superseded and must not be used as an energy-norm claim. The corrected notebook-output directory contains a README that points to the authoritative tables.
