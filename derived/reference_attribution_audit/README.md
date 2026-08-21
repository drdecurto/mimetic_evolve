# MOLE reference attribution and boundary-operator audit

This directory is authoritative for naming the reference arrays used by the study. The translated MOLE coefficient blocks match the pinned v1.2.0 MATLAB/Octave source to machine precision and are attributed to the Corbino--Castillo construction.

The audit distinguishes the general MOLE/Corbino--Castillo boundary operator `B_CC = QD + G^T P` from the sparse endpoint selector `B0` imposed by the discovery compiler. The corrected Dirichlet-symmetry proposition also requires scalar-norm separation under elimination, `E^T Q = Q_I E^T`. The compiled candidates satisfy both this condition and `E^T B0 G E = 0`; the MOLE boundary operator does not satisfy the latter.

Historical labels inside immutable raw notebooks and run archives are preserved but superseded. See `docs/MOLE_REFERENCE_ATTRIBUTION_AND_BOUNDARY_OPERATOR_CORRECTION.md`.
