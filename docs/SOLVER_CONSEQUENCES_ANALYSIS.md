# Linear-solver consequences of the certified weighted structure

## Purpose

This analysis is downstream of operator discovery. It makes no model calls, does not alter the search objective, and does not provide an additional promotion gate. It asks what linear-algebra guarantees become available once an exact candidate satisfies the weighted Dirichlet identity.

For the Dirichlet block, define

```text
A_Q = -Q_I L_I.
```

Conjugate gradients (CG) is mathematically applicable only when `A_Q` is symmetric positive definite. The normalized symmetry residual is

```text
||Q_I L_I - L_I^T Q_I||_2 / ||Q_I L_I||_2.
```

## Operator inventory

The authoritative script loads 11 released arrays at `m = 200`:

- four primary exact LLM-originated constructions;
- three exact mathematical artifacts from later follow-up runs;
- four MOLE/Corbino--Castillo references of orders 2, 4, 6, and 8.

The seven exact constructions have weighted-symmetry residuals between approximately `7.9e-17` and `1.23e-16` and positive minimum eigenvalues of `sym(-Q_I L_I)`. In the machine-readable report, the four primary candidates and all seven released exact constructions are now reported under separate, explicitly scoped residual-range keys. CG is therefore applicable to all seven. None of the four reference systems is symmetric in its stored/native quadrature; their residuals are approximately `0.072`, `0.149`, `0.522`, and `0.890`.

## Manufactured Poisson diagnostic

The test field is

```text
u(x) = sin(pi x) + 0.25 sin(7 pi x),
```

with its exact second derivative used as the right-hand side. Four routes are retained:

1. `cg_certified`: CG on the true weighted matrix `-Q_I L_I`, used only when that matrix is SPD.
2. `cg_symmetric_part_diagnostic`: CG on `sym(-Q_I L_I)`. For a nonsymmetric reference, this deliberately solves a different problem.
3. `gmres_original`: GMRES on the original `L_I` system.
4. `bicgstab_original`: BiCGSTAB on the original `L_I` system.

A dense direct solve is also retained as a deterministic accuracy check, not as a scalable method.

For the order-six reference, the diagnostic symmetric-part solve converges in residual but returns a solution with relative error

```text
0.27836556195491635.
```

GMRES on the original nonsymmetric matrix gives approximately

```text
1.0147e-9
```

relative solution error, and the dense direct solve gives approximately

```text
1.0025e-9.
```

The forced-CG result is therefore **not** evidence that the reference is unsolvable and is not a proposed practical method. It is a quantitative interpretation of the weighted-symmetry residual: replacing the true system by the nearest symmetric part changes the solution materially. For the released exact constructions, the same diagnostic remains at the discretization-error level (`<= 5.9e-6`).

## Backward-Euler heat step

The same distinction recurs for

```text
(I - dt L_I) u^{n+1} = u^n,
```

at `dt/h^2 = 5`. The weighted backward-Euler system is SPD for all four primary exact candidates and is not CG-applicable for any reference in its native quadrature. GMRES remains applicable to the original reference systems.

## Interpretation and claim boundary

The analysis makes an **availability-of-guarantees** claim, not a speed claim:

- an SPD system admits energy-norm convergence bounds;
- CG uses a three-term recurrence with fixed memory;
- symmetric positive-definite preconditioning is available;
- monotonicity can be stated in the associated energy norm.

No cross-family timing or iteration-count superiority is claimed. GMRES solves the order-six reference accurately. Iteration counts vary slightly across BLAS/SciPy builds and have different work, memory, restart, and preconditioning costs.

The order-six reference has minimum eigenvalue approximately `-26.0005` in the symmetric part of `-Q_I L_I`. This and the positive logarithmic energy rate in `derived/downstream_analysis_v3/` are two normalizations of the same quadratic-form obstruction, not independent evidence.

## Reproduction

```bash
python scripts/analyze_solver_consequences_v2.py
```

Authoritative outputs are written to:

```text
derived/solver_consequences_v2/
```

The immutable user-supplied notebook and its original result archive are preserved at:

```text
notebooks/mimetic_solver_consequences_v2_user.ipynb
runs/mimetic_solver_v2_user_results.zip
source_artifacts/mimetic_solver_v2.zip
```
