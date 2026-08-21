# MOLE reference attribution and boundary-operator correction

## Scope

The immutable discovery notebooks and raw run archives historically call the embedded order-2, 4, 6, and 8 reference arrays “Castillo--Grone” operators. That label is not authoritative for the arrays actually instantiated. The pinned MOLE source and the upstream project documentation identify the implemented high-order mathematics with the **Corbino--Castillo** construction, while citing Castillo--Grone as the earlier matrix-analysis family.

The numerical arrays, spectra, manufactured-PDE results, and search outcomes are unchanged. The correction affects:

1. the family attribution of the reference arrays;
2. the interpretation of the boundary matrix in the extended-Gauss identity; and
3. the scope of the novelty screen.

## Source-level verification

The release pins the MATLAB/Octave source from MOLE v1.2.0, commit `15de866`, under:

```text
source_artifacts/mole_v1.2.0_matlab_octave/
```

The independent audit

```bash
python scripts/audit_mole_reference_attribution.py
```

compares the left boundary blocks of `D` and `G` embedded in the archived notebook against `divNonPeriodic.m` and `gradNonPeriodic.m`. For orders 2, 4, 6, and 8, the maximum absolute discrepancy is at most `8.9e-16`. The authoritative outputs are:

```text
derived/reference_attribution_audit/mole_reference_source_match.csv
derived/reference_attribution_audit/mole_boundary_operator_diagnostics.csv
derived/reference_attribution_audit/mole_reference_attribution.json
```

## Why the complex modes do not contradict Corbino--Castillo

Corbino--Castillo constructs a general discrete extended-Gauss identity

```text
Q D + G^T P = B_CC,
```

where the mimetic boundary operator `B_CC` extends over closure rows. The discovery compiler imposes the stronger endpoint-supported identity

```text
Q D + G^T P = B0,
B0 = -e_1 e_1^T + e_{m+2} e_{m+1}^T.
```

Let `E` inject the retained Dirichlet unknowns. A sufficient condition for the principal Dirichlet block to be self-adjoint in the retained scalar norm is

```text
E^T Q = Q_I E^T,
E^T B G E = 0.
```

The compiled candidates satisfy both conditions. The MOLE/Corbino--Castillo boundary operator does not: `E^T B_CC G E` is nonzero. Therefore, the four non-real modes at orders 6 and 8 do **not** contradict the general Corbino--Castillo identity. They show that the fixed Dirichlet blocks admit no SPD self-adjoint similarity and that the stricter endpoint-supported identity cannot hold with positive-definite weights and a scalar norm respecting Dirichlet elimination.

This support condition also corrects an over-broad statement inherited from the earlier working note. The note’s numerical observations remain valid, but its historical family label and its implication from a general boundary identity to Dirichlet self-adjointness are superseded by the present audit.

## Novelty implication

The loaded same-topology references already screen the Corbino--Castillo family. That item is therefore marked `compared`, not `outstanding`, in the partial novelty gate.

The gate remains open because other same-topology comparators are incomplete, including:

- parameterized or compact higher-order Castillo--Grone extensions; and
- generalized/block-norm staggered constructions.

Classical nodal SBP families remain cross-topology comparators until a mathematically specified map to the staggered scalar/face degrees of freedom is available.

The supported claim remains:

> exact LLM-originated candidates, with no match among the loaded Corbino--Castillo references;

not:

> previously unknown operator families.

## Provenance policy

Historical labels inside immutable notebooks and run archives are retained exactly. The regenerated non-immutable derived tables use `MOLE-CC-k*`; current analysis text, generated figures, authoritative derived tables, and repository documentation use the corrected attribution. Readers should use this document and `derived/reference_attribution_audit/` when interpreting any legacy label.
