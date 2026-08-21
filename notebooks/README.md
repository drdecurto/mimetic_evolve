# Notebook status

- `mimetic_operator_discovery_v11.ipynb` is the immutable primary campaign notebook.
- `mimetic_operator_discovery_v12_failed.ipynb` and `mimetic_operator_discovery_v12_1_followup.ipynb` are preserved follow-up notebooks and are not the source of the primary inferential claims.
- `mimetic_downstream_and_novelty_v3_user.ipynb` is the user-supplied exploratory downstream/novelty notebook. Its source and outputs are retained for provenance, but its original energy-growth convention is superseded.
- `mimetic_downstream_consequences_v3.ipynb` and the executed copy reproduce the corrected authoritative downstream analysis.
- `mimetic_solver_consequences_v2_user.ipynb` is the immutable user-supplied solver-consequence notebook. Its result archive is preserved separately under `runs/`.

For energy, time-stepping, and novelty-screen claims, use `scripts/analyze_downstream_v3.py` and `derived/downstream_analysis_v3/`. See `derived/downstream_analysis_v3_notebook/README.md` and `source_artifacts/SUPERSEDED_ENERGY_INTERPRETATION.md`.

- `mimetic_solver_consequences_v2_user.ipynb` is the user-supplied executed solver-analysis notebook. It is preserved for provenance and reproduces the claim-bearing values, but it hardcodes an earlier repository directory name. Use `scripts/analyze_solver_consequences_v2.py` and `derived/solver_consequences_v2/` as the authoritative portable analysis.
- `mimetic_solver_consequences_v2_reproduction.ipynb` and its executed copy are portable front ends to that authoritative script.

## Historical reference label

The immutable discovery notebooks call the embedded MOLE order-2, 4, 6, and 8 references `Castillo-Grone`. The pinned upstream source identifies the implemented mathematics with **Corbino--Castillo**; Castillo--Grone is the earlier, distinct matrix-analysis family. The raw notebooks are not rewritten, but their label is superseded for interpretation.

See `REFERENCE_ATTRIBUTION_NOTE.md`, `docs/MOLE_REFERENCE_ATTRIBUTION_AND_BOUNDARY_OPERATOR_CORRECTION.md`, and `derived/reference_attribution_audit/`.

For linear-solver claims, use `scripts/analyze_solver_consequences_v2.py` and `derived/solver_consequences_v2/`. The forced-CG route in that analysis is a diagnostic that solves the symmetric part of a nonsymmetric reference system; it is not a recommended solver or a speed comparison.
