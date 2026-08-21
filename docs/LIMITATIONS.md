# Limitations and Required Next Experiments

## 1. Archive-condition schedules are not paired

The archived generator seeds model/role selection with a condition-dependent Python `hash()`. Thus, the same numerical seed does not produce the same model-role sequence under the four archive conditions, and the built-in hash can vary across Python processes. The current experiment establishes an association between the complete feedback package and higher verified yield, not a clean causal archive ablation.

**Required controlled rerun:** predeclare one `(seed, solver_step, model_id, role)` schedule using SHA-256 or `numpy.random.SeedSequence` and reuse it under every archive condition. Retries and duplicates must not advance the solver-step schedule.

## 2. Feedback components are bundled

Full metrics and illumination receive both archive information and an explicit diagnostic refinement of a failed preceding program. A partial randomized check among 97 refinement-eligible calls finds no direct one-step repair effect: under the fixed external endpoint, 20/42 refined and 25/55 fresh proposals pass (Fisher `p = 0.840`); under the notebook gate, the counts are 16/42 and 20/55 (`p = 1.00`). Because repair was assigned by a coin flip within calls whose preceding proposal failed, this is a causal null for one-step repair conditional on the failed-predecessor stratum. It does not isolate archive metrics, because archive assignment, prompts, and model-role schedules remain condition-specific.

**Required controlled rerun:** a 2×2 factorial design crossing archive metrics with diagnostic refinement:

| Metrics | Diagnostic | Interpretation |
|---|---|---|
| no | no | cold baseline |
| yes | no | archive-only effect |
| no | yes | repair-only effect |
| yes | yes | complete feedback package |

## 3. Search controls are unequal in strength

The expert-informed prior encodes substantial domain knowledge and should be treated as an expert oracle control. The ExtraTrees surrogate uses one utility regressor in a sparse-feasibility problem and is not a strong general Bayesian-optimization baseline.

**Required improvement:** separate feasibility classification from conditional utility prediction and use a balanced initial design or constrained Bayesian optimization.

## 4. Frontier probes were not consumed

Programs above the empirical boundary-order ceiling are removed by preflight even though a probe quota is declared.

**Required improvement:** reserve a fixed, equal fraction of every arm's solver budget for programs that bypass the empirical frontier filter.

## 5. Literature novelty is unresolved

Current equality checks cover the loaded MOLE/Corbino--Castillo arrays and prior candidates, but not every parameterized or compact Castillo--Grone extension or generalized/block-norm staggered construction. Classical Strand and Mattsson--Nordstroem operators are nodal cross-topology comparators and require an explicit degree-of-freedom map.

**Required improvement:** build a topology-aware coefficient library and compare exact candidates up to scaling, sign, reflection, coordinate convention, and admissible basis transformations before using “new family.”

## 6. Scope is one-dimensional and uniform-grid

The compiler and proof objects concern one-dimensional staggered grids. Mapped grids, multidimensional compatible complexes, nonlinear PDEs, and production solvers are not established.

## 7. The block-positive cone is sufficient, not complete

The LP-compatible representation is an inner approximation to the banded SPD cone. A semidefinite formulation can access valid norms excluded by the current grammar.

## 8. Robustness evidence is diagnostic

Boundary-supported perturbations reduce average spectral drift modestly in the tested setting. This is not a general stability theorem. The solver audit establishes availability of a certified SPD weighted formulation, not a speed advantage: GMRES and BiCGSTAB solve the nonsymmetric references accurately, and iteration counts are not comparable without matched preconditioners, work units, tolerances, and mesh scaling. A stronger study should include interface-low-rank perturbations, preconditioned mesh-scaling experiments, and PDE-level uncertainty propagation.
## 9. Endpoint interpretation

The common external endpoint is a fixed-threshold re-analysis, not a stricter version of the notebook gate. It accepts 142 programs rejected by `hard_pass_all` and rejects none accepted by it. This is appropriate for arm-comparable inference and reduces the full-metrics/random ratio from 24.0 to 4.1, but the two pass rates must not be treated as interchangeable.

## 10. Reference round-off floor

The MOLE order-six manufactured-PDE error reaches approximately `1.44e-12` at `m = 480` and rises at `m = 640`. Reference convergence windows containing the final point are round-off contaminated and are retained only as audited raw slopes, with `rate_interpretable = false`.


## 11. v12 and v12.1 are follow-ups, not replacements for v11

The v12 comparison failed completion despite a paired schedule; 1,884 provider-transport failures and 120 parser-selected schema echoes dominated the campaign. v12.1 repaired transport (`1036/1051` schema-valid generations) but not diversity (`612/1051` arm-distinct programs): 8/50 arms did not exhaust the unique-program budget, 424 successful duplicates depleted generation budgets, circuit-breaker substitution caused 20 schedule mismatches, and most solver records came from one model. A least-favourable missing-as-failure sensitivity preserves the archive/no-archive separation, but it cannot repair the pairing and roster defects. The two-stage phase contrast is additionally confounded because four arms truncate during the feedback phase. The follow-up remains mechanism-generating rather than causal.

Exact coefficient certificates from these runs remain mathematical artifacts. Their validity is assessed independently of the search-policy comparison.

## Downstream and novelty limitations

The energy comparison is made in each operator's stored/native quadrature. Positive transient growth for the reference in that norm does not exclude a different positive Lyapunov norm. The explicit RK4 limit is unchanged, so the current evidence supports a certified energy estimate and symmetric formulation rather than a larger CFL step. The coefficient novelty screen is topology-scoped. It finds no match to the loaded same-order MOLE/Corbino--Castillo reference, closing that item in the partial library, but parameterized/compact Castillo--Grone extensions and generalized/block-norm staggered families remain outstanding. Classical nodal SBP families require an explicit topology map before coefficient equivalence is meaningful. No literature-level novelty claim is made.

## 12. Solver analysis establishes guarantees, not speed

The linear-solver experiment is performed at one mesh (`m = 200`) without a mesh-scaling or matched-preconditioner study. CG on the symmetric part of a nonsymmetric reference is a diagnostic that quantifies the consequence of replacing the true system; it is not a method a competent practitioner would choose. GMRES and BiCGSTAB solve the original reference systems. The evidence supports availability of SPD guarantees for the certified candidates, not lower runtime or iteration count. A solver-performance study would require multiple meshes and matched preconditioners such as IC-CG versus ILU-GMRES.


## Linear-solver diagnostic

The solver analysis establishes availability of a certified SPD weighted formulation, not superiority in wall-clock time or iteration count. The forced-CG calculation on a reference operator solves its symmetric part rather than the original nonsymmetric system and is used only to interpret the weighted-symmetry residual. GMRES and BiCGSTAB remain appropriate for the original reference systems. Iteration counts depend on tolerance, restart, preconditioner, right-hand side, BLAS/LAPACK implementation, and stopping conventions; they are archived but not compared as a performance endpoint. A dedicated solver study would require mesh scaling and matched preconditioners, such as IC-CG versus ILU-GMRES, across several problem classes.
