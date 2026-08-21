# Solver-guarantees table update

The manuscript source itself is distributed separately and is intentionally not stored in this GitHub repository.

The Scientific Reports manuscript now includes an inline table that separates two quantities which were previously described only in prose:

1. the solution error obtained from the **original discrete operator** (dense direct solve, used as a deterministic accuracy reference); and
2. the solution error obtained when CG is deliberately applied to the **symmetric part** of the weighted system.

For all seven released exact constructions, the certified weighted matrix is symmetric positive definite to numerical precision, so the two problems coincide and their errors agree at the displayed precision. For the MOLE/Corbino--Castillo references, the symmetric-part calculation is a different operator and is retained only as a diagnostic interpretation of the weighted-symmetry residual.

The compact source for the table is `derived/solver_consequences_v2/solver_guarantees_table.csv`. The underlying unaggregated records remain in `tables/poisson_solver_comparison.csv` and `tables/symmetric_system_availability.csv`.

The table does not compare solver speed. GMRES and BiCGSTAB results are archived for the original reference matrices; iteration counts are not compared across solver families because memory, restart, preconditioning, work per iteration, tolerances, and numerical-library details differ.
