# MOLE reference attribution update: independent audit

## Decision

The attribution concern was correct. The order-2, 4, 6, and 8 reference arrays instantiated by the discovery notebook are the implementations shipped by MOLE and should be described as **MOLE/Corbino--Castillo**, not as the distinct parameterized Castillo--Grone coefficient family.

This update does not alter the reference arrays or any numerical result. It changes the family label, corrects the interpretation of the discrete boundary operator, and narrows the novelty boundary.

## Source-level evidence

The release pins the MOLE v1.2.0 MATLAB/Octave implementation at commit `15de866`. The script

```bash
python scripts/audit_mole_reference_attribution.py
```

compares the embedded left boundary blocks of `D` and `G` with `divNonPeriodic.m` and `gradNonPeriodic.m`. The maximum absolute discrepancy is:

| Order | D block | G block | Match |
|---:|---:|---:|:---:|
| 2 | 0 | 0 | yes |
| 4 | 1.11e-16 | 2.22e-16 | yes |
| 6 | 0 | 5.55e-17 | yes |
| 8 | 1.11e-16 | 8.88e-16 | yes |

The current MOLE project description states that its mathematics is based on Corbino and Castillo, while citing Castillo and Grone as an earlier similar matrix-analysis construction. The Corbino--Castillo article describes staggered-grid operators with uniform interior/boundary order, no free parameters, optimal bandwidth, and a diagonal norm. The Castillo--Grone article constructs the earlier one-dimensional matrix-analysis family, with explicit second- and fourth-order cases.

## Boundary-operator correction

A general identity

```text
Q D + G^T P = B
```

does not, by itself, imply that the principal Dirichlet block is self-adjoint in the retained scalar norm. With `E` denoting Dirichlet injection, the sufficient conditions used in the analysis are

```text
E^T Q = Q_I E^T,
E^T B G E = 0.
```

The discovery compiler enforces the endpoint selector

```text
B0 = -e_1 e_1^T + e_{m+2} e_{m+1}^T,
```

and all four promoted candidates satisfy both support conditions to numerical precision. The MOLE/Corbino--Castillo reference has a closure-supported boundary operator `B_CC = QD + G^T P`, for which the restricted boundary term does not vanish. At orders 6 and 8 the Dirichlet blocks still have four non-real eigenvalues. These facts coexist without contradiction: the general Corbino--Castillo identity is not the endpoint-supported identity required for the candidate self-adjointness proposition.

## Novelty consequence

The loaded references already compare the promoted candidates against the Corbino--Castillo family at orders 2, 4, 6, and 8. The `corbino_castillo` item is therefore closed in the partial novelty gate.

The novelty claim remains open because the current library does not exhaust:

- parameterized or compact higher-order Castillo--Grone extensions;
- generalized or block-norm staggered constructions; and
- nodal SBP families after an explicit topology map to the staggered scalar/face degrees of freedom.

The supported language is therefore:

> exact LLM-originated candidates with no match among the loaded MOLE/Corbino--Castillo references;

not:

> previously unknown operator families.

## Files added or regenerated

- `source_artifacts/mole_v1.2.0_matlab_octave/`
- `scripts/audit_mole_reference_attribution.py`
- `derived/reference_attribution_audit/`
- `notebooks/REFERENCE_ATTRIBUTION_NOTE.md`
- `docs/MOLE_REFERENCE_ATTRIBUTION_AND_BOUNDARY_OPERATOR_CORRECTION.md`
- corrected the reference labels used throughout the analysis
- corrected figure and non-immutable derived-table labels

Historical labels inside immutable notebooks and raw archives remain unchanged for provenance.
