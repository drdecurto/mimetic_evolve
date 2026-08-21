# the current release solver-consequence update audit

## Decision

The attached solver experiment is worth adding, but only as a compact downstream consequence of the exact weighted structure. It does not warrant a new main figure, a solver-performance table, or any claim that the reference operators are unsolvable or slower. The analysis therefore adds one Results paragraph and one bounded Methods paragraph. The article grows from 11 to 12 pages.

## Source audit

The supplied archive `mimetic_solver_v2.zip` contains an executed notebook and a nested result archive. The preserved notebook contains 11 code cells with execution counts 2 through 12 and no stored error output. The experiment loads 18 arrays, selects 11 for analysis, and distinguishes four primary exact operators, three exact follow-up artifacts, and four MOLE/Corbino--Castillo references.

The release preserves:

- `source_artifacts/mimetic_solver_v2.zip`;
- `notebooks/mimetic_solver_consequences_v2_user.ipynb`;
- `runs/mimetic_solver_v2_user_results.zip`.

The authoritative reproduction is `scripts/analyze_solver_consequences_v2.py`; its outputs are under `derived/solver_consequences_v2/`.

## Reproduced headline values

At `m=200`:

- weighted-symmetry residuals for the seven exact constructions lie between `7.86e-17` and `1.23e-16`;
- the MOLE/Corbino--Castillo reference residuals are `0.07195`, `0.14851`, `0.52235`, and `0.89005` at orders 2, 4, 6, and 8;
- `-Q_I L_I` is SPD and CG-applicable for all seven exact constructions and for none of the references under their native quadratures;
- the symmetric part of the order-six reference has minimum eigenvalue `-26.0005`; the order-eight value is `-844.8657`;
- intentionally applying CG to the symmetric part of the order-six weighted reference system produces relative solution error `0.2783656`;
- GMRES on the original nonsymmetric order-six operator produces error `1.0147e-9`, and a dense direct solve produces `1.0025e-9`;
- the maximum symmetric-part diagnostic error among the four primary exact candidates is `5.8717e-6`, at their discretization-error level;
- at `dt/h^2=5`, the weighted backward-Euler system is CG-applicable for all four primary exact candidates and for none of the four references under their native quadratures.

The authoritative/user comparison table shows agreement on claim-bearing values to floating-point precision. Krylov iteration counts vary modestly across numerical-library builds and are not used as release evidence.

## Interpretation

The forced-CG result is a diagnostic, not a practical failure mode. It quantifies the consequence of replacing a nonsymmetric weighted system by its symmetric part. The original reference system is solved accurately by GMRES and BiCGSTAB. The contribution is availability of SPD-specific guarantees: energy-norm convergence bounds, a fixed-memory three-term recurrence, and symmetric preconditioning. No speed advantage is claimed.

The negative minimum eigenvalue of the symmetric part and the positive logarithmic Q-energy rate in the semidiscrete experiment are two normalizations of the same quadratic-form obstruction, not independent evidence.

## analysis changes

1. The long fixed-closure sentence was split into shorter statements, eliminating the previously reported collapsed-space rendering risk.
2. Results now report the weighted-system availability contrast, the `0.278` diagnostic error, the accurate GMRES solution, and the precise no-speed-overclaim boundary.
3. Methods specify the manufactured field, the SPD applicability rule, the diagnostic symmetric-part solve, the original-system Krylov solves, and the backward-Euler test.
4. No new display item was added. The detailed solver figure and tables remain in the repository.

## Validation

- Clean the current release PDF: 12 pages.
- Line-numbered the current release PDF: 12 pages.
- Four figures and two tables remain cited inline.
- No undefined citations, unresolved references, overfull boxes, clipping, or broken glyphs were observed.
- The full release verifier checks the source archive, notebook, nested result archive, authoritative tables, key numerical values, analysis wording, exact certificates, nested manifests, ZIP CRCs, and credential scan.
## Final diagnostic clarification

The analysis now quotes the dense direct solve (`1.0025e-9`) alongside GMRES (`1.0147e-9`) for the original order-six reference system. This makes explicit that the `0.278` forced-CG error is created by replacing the original system with its symmetric part, not by the reference discretization or by a particular nonsymmetric iterative solver. The authoritative JSON report also separates the four-primary and all-seven released-exact weighted-symmetry residual ranges.
