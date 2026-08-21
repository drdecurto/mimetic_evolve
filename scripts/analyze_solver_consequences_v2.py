#!/usr/bin/env python3
"""Recompute linear-solver consequences of the certified weighted structure.

This analysis is downstream of discovery. It makes no model calls and does not
change the search or promotion endpoint. It asks a narrower question: when does
an operator admit the symmetric positive-definite weighted system required by
conjugate gradients, and how large is the error if a nonsymmetric weighted
system is replaced by its symmetric part?

The forced-CG route is deliberately a diagnostic, not a recommended solver.
GMRES and BiCGSTAB are applied to the original nonsymmetric reference systems.
Iteration counts are retained for reproducibility but are not used for
cross-family speed claims because Krylov algorithms have different work and
memory costs and may vary slightly across BLAS/SciPy builds.
"""
from __future__ import annotations

import argparse
import inspect
import io
import json
import math
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.sparse.linalg import bicgstab, cg, gmres

SYMMETRY_TOLERANCE = 1e-10


@dataclass
class Operator:
    name: str
    family: str  # primary_exact | followup_exact | reference
    cells: int
    D: np.ndarray
    G: np.ndarray
    Q: np.ndarray | None
    P: np.ndarray | None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def L(self) -> np.ndarray:
        return self.D @ self.G

    def interior_laplacian(self) -> np.ndarray:
        return self.L[1:-1, 1:-1]

    def interior_norm(self) -> np.ndarray | None:
        return None if self.Q is None else self.Q[1:-1, 1:-1]


def _as_matrix(value: Any) -> np.ndarray | None:
    if value is None:
        return None
    arr = np.asarray(value, dtype=float)
    return np.diag(arr) if arr.ndim == 1 else arr


def _load_npz_bytes(data: bytes, name: str, family: str) -> Operator:
    with np.load(io.BytesIO(data), allow_pickle=True) as bundle:
        keys = set(bundle.files)
        if not {"D", "G", "cells"} <= keys:
            raise ValueError(f"operator archive lacks D/G/cells: {name}")
        metadata: dict[str, Any] = {}
        if "metadata_json" in keys:
            raw = bundle["metadata_json"]
            try:
                metadata = json.loads(str(raw.item() if np.asarray(raw).ndim == 0 else raw))
            except Exception:
                metadata = {}
        q_value = bundle["Q"] if "Q" in keys else (bundle["q"] if "q" in keys else None)
        p_value = bundle["P"] if "P" in keys else (bundle["p"] if "p" in keys else None)
        return Operator(
            name=Path(name).stem,
            family=family,
            cells=int(bundle["cells"]),
            D=np.asarray(bundle["D"], dtype=float),
            G=np.asarray(bundle["G"], dtype=float),
            Q=_as_matrix(q_value),
            P=_as_matrix(p_value),
            metadata=metadata,
        )


def _load_npz_path(path: Path, family: str) -> Operator:
    return _load_npz_bytes(path.read_bytes(), path.name, family)


def load_release_operators(root: Path) -> list[Operator]:
    operators: list[Operator] = []
    for path in sorted((root / "derived" / "operators").glob("*_m200.npz")):
        operators.append(_load_npz_path(path, "primary_exact"))
    for path in sorted((root / "derived" / "followup_operators").glob("*_m200.npz")):
        operators.append(_load_npz_path(path, "followup_exact"))

    archive = root / "runs" / "v11_original_results.zip"
    with zipfile.ZipFile(archive) as zf:
        for order in (2, 4, 6, 8):
            suffix = f"reference_mole_k{order}_m200.npz"
            matches = [name for name in zf.namelist() if name.endswith(suffix)]
            if len(matches) != 1:
                raise RuntimeError(f"expected one {suffix} in {archive}, found {len(matches)}")
            op = _load_npz_bytes(zf.read(matches[0]), suffix, "reference")
            op.metadata["display_family"] = "MOLE/Corbino-Castillo"
            op.metadata["order"] = order
            operators.append(op)

    counts = pd.Series([op.family for op in operators]).value_counts().to_dict()
    expected = {"primary_exact": 4, "followup_exact": 3, "reference": 4}
    if counts != expected:
        raise RuntimeError(f"unexpected operator inventory: {counts}; expected {expected}")
    return operators


def weighted_symmetry_residual(L: np.ndarray, Q: np.ndarray) -> float:
    product = Q @ L
    return float(np.linalg.norm(product - product.T, 2) /
                 max(float(np.linalg.norm(product, 2)), 1e-300))


def symmetric_system(L: np.ndarray, Q: np.ndarray) -> dict[str, Any]:
    Q = 0.5 * (Q + Q.T)
    residual = weighted_symmetry_residual(L, Q)
    weighted = -(Q @ L)
    symmetric_part = 0.5 * (weighted + weighted.T)
    eigenvalues = np.linalg.eigvalsh(symmetric_part)
    return {
        "symmetry_residual": residual,
        "weighted_matrix": weighted,
        "symmetric_part": symmetric_part,
        "min_eigenvalue_symmetric_part": float(eigenvalues[0]),
        "max_eigenvalue_symmetric_part": float(eigenvalues[-1]),
        "symmetric_part_condition_proxy": (
            float(abs(eigenvalues[-1] / eigenvalues[0])) if eigenvalues[0] else float("inf")
        ),
        "symmetric_part_is_spd": bool(eigenvalues[0] > 0),
        "cg_applicable": bool(residual < SYMMETRY_TOLERANCE and eigenvalues[0] > 0),
    }


def manufactured_poisson(cells: int,
                           modes: tuple[tuple[int, float], ...] = ((1, 1.0), (7, 0.25))
                           ) -> tuple[np.ndarray, np.ndarray]:
    x = (np.arange(1, cells + 1) - 0.5) / cells
    u = sum(amplitude * np.sin(mode * math.pi * x) for mode, amplitude in modes)
    f = sum(-amplitude * (mode * math.pi) ** 2 * np.sin(mode * math.pi * x)
            for mode, amplitude in modes)
    return u, f


def _iterate(solver, A: np.ndarray, b: np.ndarray, tolerance: float,
             maxiter: int) -> dict[str, Any]:
    history: list[float] = []
    scale = max(float(np.linalg.norm(b)), 1e-300)

    def callback(value):
        arr = np.asarray(value)
        if arr.ndim == 0:
            history.append(float(arr))
        else:
            history.append(float(np.linalg.norm(b - A @ arr) / scale))

    kwargs: dict[str, Any] = {"maxiter": maxiter, "callback": callback}
    parameters = inspect.signature(solver).parameters
    kwargs["rtol" if "rtol" in parameters else "tol"] = tolerance
    if solver is gmres:
        if "restart" in parameters:
            kwargs["restart"] = 50
        if "callback_type" in parameters:
            kwargs["callback_type"] = "pr_norm"
    x, info = solver(A, b, **kwargs)
    residual = float(np.linalg.norm(b - A @ x) / scale)
    return {
        "x": x,
        "info": int(info),
        "iterations": len(history),
        "final_relative_residual": residual,
        "history": history,
        "converged": bool(residual <= tolerance * 10),
    }


def poisson_experiment(operator: Operator, tolerance: float = 1e-10,
                       maxiter: int = 5000) -> dict[str, Any]:
    L = operator.interior_laplacian()
    Q = operator.interior_norm()
    result: dict[str, Any] = {
        "operator": operator.name,
        "family": operator.family,
        "cells": operator.cells,
        "unknowns": int(L.shape[0]),
        "target_order": operator.metadata.get("target_order", operator.metadata.get("order")),
    }
    if Q is None:
        result["norm_available"] = False
        return result
    result["norm_available"] = True
    Q = 0.5 * (Q + Q.T)
    system = symmetric_system(L, Q)
    for key in (
        "symmetry_residual", "min_eigenvalue_symmetric_part",
        "max_eigenvalue_symmetric_part", "symmetric_part_condition_proxy",
        "symmetric_part_is_spd", "cg_applicable",
    ):
        result[key] = system[key]

    u_exact, f = manufactured_poisson(operator.cells)
    b_weighted = -(Q @ f)

    def solution_error(x: np.ndarray) -> float:
        return float(np.linalg.norm(x - u_exact) / np.linalg.norm(u_exact))

    # Dense direct solve is a deterministic accuracy reference, not a scalable method.
    direct = np.linalg.solve(L, f)
    result["direct_original_solution_error"] = solution_error(direct)
    result["direct_original_relative_residual"] = float(
        np.linalg.norm(f - L @ direct) / max(float(np.linalg.norm(f)), 1e-300)
    )

    runs: dict[str, dict[str, Any]] = {}
    if system["cg_applicable"]:
        runs["cg_certified"] = _iterate(cg, system["weighted_matrix"], b_weighted,
                                         tolerance, maxiter)
    # Diagnostic only: this solves a different system whenever the residual is non-negligible.
    runs["cg_symmetric_part_diagnostic"] = _iterate(
        cg, system["symmetric_part"], b_weighted, tolerance, maxiter
    )
    runs["gmres_original"] = _iterate(gmres, L, f, tolerance, maxiter)
    runs["bicgstab_original"] = _iterate(bicgstab, L, f, tolerance, maxiter)

    for name, run in runs.items():
        result[f"{name}_iterations"] = run["iterations"]
        result[f"{name}_converged"] = run["converged"]
        result[f"{name}_relative_residual"] = run["final_relative_residual"]
        result[f"{name}_solution_error"] = solution_error(run["x"])
    result["_histories"] = {name: run["history"] for name, run in runs.items()}
    return result


def implicit_heat_step(operator: Operator, dt_over_h2: float = 5.0,
                       tolerance: float = 1e-10, maxiter: int = 5000) -> dict[str, Any]:
    L = operator.interior_laplacian()
    Q = operator.interior_norm()
    result: dict[str, Any] = {
        "operator": operator.name,
        "family": operator.family,
        "dt_over_h2": dt_over_h2,
    }
    if Q is None:
        result["norm_available"] = False
        return result
    result["norm_available"] = True
    Q = 0.5 * (Q + Q.T)
    h = 1.0 / operator.cells
    dt = dt_over_h2 * h * h
    A = np.eye(L.shape[0]) - dt * L
    weighted = Q @ A
    residual = float(np.linalg.norm(weighted - weighted.T, 2) /
                     max(float(np.linalg.norm(weighted, 2)), 1e-300))
    symmetric_part = 0.5 * (weighted + weighted.T)
    eigenvalues = np.linalg.eigvalsh(symmetric_part)
    applicable = bool(residual < SYMMETRY_TOLERANCE and eigenvalues[0] > 0)
    result.update({
        "weighted_symmetry_residual": residual,
        "min_eigenvalue_symmetric_part": float(eigenvalues[0]),
        "symmetric_part_is_spd": bool(eigenvalues[0] > 0),
        "cg_applicable": applicable,
    })
    u0, _ = manufactured_poisson(operator.cells)
    if applicable:
        run = _iterate(cg, weighted, Q @ u0, tolerance, maxiter)
        result.update({
            "cg_iterations": run["iterations"],
            "cg_converged": run["converged"],
            "cg_relative_residual": run["final_relative_residual"],
        })
    run = _iterate(gmres, A, u0, tolerance, maxiter)
    result.update({
        "gmres_iterations": run["iterations"],
        "gmres_converged": run["converged"],
        "gmres_relative_residual": run["final_relative_residual"],
    })
    return result


def make_figure(poisson_rows: list[dict[str, Any]], output: Path) -> None:
    primary = next(
        (row for row in poisson_rows
         if row["family"] == "primary_exact"
         and "structure_only" in row["operator"]
         and row.get("cg_applicable")),
        next(row for row in poisson_rows
             if row["family"] == "primary_exact" and row.get("cg_applicable")),
    )
    reference = next(row for row in poisson_rows if "reference_mole_k6" in row["operator"])

    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.1))
    histories = primary["_histories"]
    ref_histories = reference["_histories"]
    series = [
        ("exact candidate: CG on $-Q_I L_I$", histories.get("cg_certified"), "-"),
        ("exact candidate: GMRES on $L_I$", histories.get("gmres_original"), "--"),
        ("MOLE/CC $k=6$: diagnostic CG", ref_histories.get("cg_symmetric_part_diagnostic"), "-"),
        ("MOLE/CC $k=6$: GMRES on $L_I$", ref_histories.get("gmres_original"), "--"),
    ]
    for label, history, linestyle in series:
        if history:
            axes[0].semilogy(np.arange(1, len(history) + 1), history,
                             linestyle=linestyle, linewidth=1.3, label=label)
    axes[0].set_xlabel("iteration")
    axes[0].set_ylabel("relative residual")
    axes[0].set_title("Residual histories")
    axes[0].legend(fontsize=7)

    table = pd.DataFrame([{k: v for k, v in row.items() if not k.startswith("_")}
                          for row in poisson_rows])
    markers = {"reference": "s", "primary_exact": "o", "followup_exact": "^"}
    labels = {"reference": "MOLE/CC reference", "primary_exact": "primary exact",
              "followup_exact": "follow-up exact"}
    for family, marker in markers.items():
        subset = table[table.family == family]
        axes[1].loglog(
            subset.symmetry_residual.clip(lower=1e-17),
            subset.cg_symmetric_part_diagnostic_solution_error,
            marker=marker, linestyle="none", label=labels[family], markersize=6,
        )
    axes[1].set_xlabel("weighted-symmetry residual")
    axes[1].set_ylabel("diagnostic symmetric-part solution error")
    axes[1].set_title("Interpreting departure from symmetry")
    axes[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(output, dpi=200)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    root = args.root.resolve()
    output = (args.output or (root / "derived" / "solver_consequences_v2")).resolve()
    tables = output / "tables"
    figures = output / "figures"
    if output.exists():
        shutil.rmtree(output)
    tables.mkdir(parents=True)
    figures.mkdir(parents=True)

    operators = load_release_operators(root)
    availability_rows: list[dict[str, Any]] = []
    poisson_rows: list[dict[str, Any]] = []
    heat_rows: list[dict[str, Any]] = []

    for op in operators:
        Q = op.interior_norm()
        if Q is None:
            availability_rows.append({"operator": op.name, "family": op.family,
                                      "norm_available": False})
        else:
            system = symmetric_system(op.interior_laplacian(), Q)
            availability_rows.append({
                "operator": op.name,
                "family": op.family,
                "target_order": op.metadata.get("target_order", op.metadata.get("order")),
                "norm_available": True,
                **{key: system[key] for key in (
                    "symmetry_residual", "min_eigenvalue_symmetric_part",
                    "max_eigenvalue_symmetric_part", "symmetric_part_condition_proxy",
                    "symmetric_part_is_spd", "cg_applicable",
                )},
            })
        poisson_rows.append(poisson_experiment(op))
        heat_rows.append(implicit_heat_step(op))

    availability = pd.DataFrame(availability_rows)
    poisson = pd.DataFrame([{k: v for k, v in row.items() if not k.startswith("_")}
                            for row in poisson_rows])
    heat = pd.DataFrame(heat_rows)
    availability.to_csv(tables / "symmetric_system_availability.csv", index=False)
    poisson.to_csv(tables / "poisson_solver_comparison.csv", index=False)
    heat.to_csv(tables / "implicit_heat_step.csv", index=False)
    make_figure(poisson_rows, figures / "solver_consequences.png")

    primary = poisson[poisson.family == "primary_exact"]
    followup = poisson[poisson.family == "followup_exact"]
    released_exact = poisson[poisson.family.isin(["primary_exact", "followup_exact"])]
    references = poisson[poisson.family == "reference"]
    k6 = references[references.operator.str.contains("reference_mole_k6")].iloc[0]
    k8 = references[references.operator.str.contains("reference_mole_k8")].iloc[0]
    heat_primary = heat[heat.family == "primary_exact"]
    heat_refs = heat[heat.family == "reference"]

    report = {
        "analysis": "solver_consequences_v2",
        "operators": int(len(poisson)),
        "primary_exact": int(len(primary)),
        "followup_exact": int(len(followup)),
        "references": int(len(references)),
        "primary_cg_applicable": int(primary.cg_applicable.sum()),
        "followup_cg_applicable": int(followup.cg_applicable.sum()),
        "released_exact": int(len(released_exact)),
        "released_exact_cg_applicable": int(released_exact.cg_applicable.sum()),
        "reference_cg_applicable_native_quadrature": int(references.cg_applicable.sum()),
        "four_primary_symmetry_residual_range": [
            float(primary.symmetry_residual.min()),
            float(primary.symmetry_residual.max()),
        ],
        "all_released_exact_symmetry_residual_range": [
            float(released_exact.symmetry_residual.min()),
            float(released_exact.symmetry_residual.max()),
        ],
        "reference_symmetry_residuals": {
            row.operator: float(row.symmetry_residual) for row in references.itertuples()
        },
        "order6_reference": {
            "symmetry_residual": float(k6.symmetry_residual),
            "min_eigenvalue_symmetric_part": float(k6.min_eigenvalue_symmetric_part),
            "diagnostic_cg_solution_error": float(
                k6.cg_symmetric_part_diagnostic_solution_error
            ),
            "gmres_solution_error": float(k6.gmres_original_solution_error),
            "direct_solution_error": float(k6.direct_original_solution_error),
        },
        "order8_reference": {
            "symmetry_residual": float(k8.symmetry_residual),
            "min_eigenvalue_symmetric_part": float(k8.min_eigenvalue_symmetric_part),
            "diagnostic_cg_solution_error": float(
                k8.cg_symmetric_part_diagnostic_solution_error
            ),
            "gmres_solution_error": float(k8.gmres_original_solution_error),
        },
        "primary_diagnostic_solution_error_max": float(
            primary.cg_symmetric_part_diagnostic_solution_error.max()
        ),
        "primary_backward_euler_cg_applicable": int(heat_primary.cg_applicable.sum()),
        "reference_backward_euler_cg_applicable_native_quadrature": int(
            heat_refs.cg_applicable.sum()
        ),
        "interpretation": (
            "The symmetric-part CG run is a diagnostic that quantifies the consequence of "
            "treating a nonsymmetric weighted operator as symmetric. It is not a recommended "
            "solver and is not evidence that the reference systems are unsolvable. Dense direct "
            "solves, GMRES, and BiCGSTAB reproduce the original nonsymmetric systems; the large "
            "forced-CG error is introduced by symmetrization. Iteration counts are not used "
            "for cross-family speed claims."
        ),
    }
    (output / "solver_experiment_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )
    headline_rows = [
        {"quantity": "released_exact_constructions", "value": int(len(primary) + len(followup)), "units": "operators"},
        {"quantity": "released_exact_cg_applicable", "value": int(primary.cg_applicable.sum() + followup.cg_applicable.sum()), "units": "operators"},
        {"quantity": "reference_cg_applicable_native_quadrature", "value": int(references.cg_applicable.sum()), "units": "operators"},
        {"quantity": "order6_reference_weighted_symmetry_residual", "value": float(k6.symmetry_residual), "units": "relative"},
        {"quantity": "order6_reference_min_symmetric_part_eigenvalue", "value": float(k6.min_eigenvalue_symmetric_part), "units": "matrix units"},
        {"quantity": "order6_reference_diagnostic_cg_solution_error", "value": float(k6.cg_symmetric_part_diagnostic_solution_error), "units": "relative"},
        {"quantity": "order6_reference_direct_solution_error", "value": float(k6.direct_original_solution_error), "units": "relative"},
        {"quantity": "order6_reference_gmres_solution_error", "value": float(k6.gmres_original_solution_error), "units": "relative"},
        {"quantity": "order8_reference_diagnostic_cg_solution_error", "value": float(k8.cg_symmetric_part_diagnostic_solution_error), "units": "relative"},
    ]
    pd.DataFrame(headline_rows).to_csv(output / "headline_solver_consequences.csv", index=False)

    # Compact, manuscript-facing summary.  The exact-construction row aggregates
    # the four primary and three follow-up certificates; reference rows remain
    # individual so that the availability boundary is visible by order.
    guarantee_rows: list[dict[str, Any]] = [{
        "operator_group": "Exact constructions (7)",
        "operators": int(len(released_exact)),
        "symmetry_residual_max": float(released_exact.symmetry_residual.max()),
        "min_eigenvalue_min": float(released_exact.min_eigenvalue_symmetric_part.min()),
        "cg_applicable": bool(released_exact.cg_applicable.all()),
        "original_solution_error_min": float(released_exact.direct_original_solution_error.min()),
        "original_solution_error_max": float(released_exact.direct_original_solution_error.max()),
        "symmetric_part_solution_error_min": float(
            released_exact.cg_symmetric_part_diagnostic_solution_error.min()
        ),
        "symmetric_part_solution_error_max": float(
            released_exact.cg_symmetric_part_diagnostic_solution_error.max()
        ),
    }]
    for row in references.sort_values("target_order").itertuples():
        guarantee_rows.append({
            "operator_group": f"MOLE/CC order {int(row.target_order)}",
            "operators": 1,
            "symmetry_residual_max": float(row.symmetry_residual),
            "min_eigenvalue_min": float(row.min_eigenvalue_symmetric_part),
            "cg_applicable": bool(row.cg_applicable),
            "original_solution_error_min": float(row.direct_original_solution_error),
            "original_solution_error_max": float(row.direct_original_solution_error),
            "symmetric_part_solution_error_min": float(
                row.cg_symmetric_part_diagnostic_solution_error
            ),
            "symmetric_part_solution_error_max": float(
                row.cg_symmetric_part_diagnostic_solution_error
            ),
        })
    pd.DataFrame(guarantee_rows).to_csv(output / "solver_guarantees_table.csv", index=False)

    # Compare claim-bearing values against the immutable user notebook outputs.
    user_archive = root / "runs" / "mimetic_solver_v2_user_results.zip"
    comparison_rows: list[dict[str, Any]] = []
    if user_archive.exists():
        with zipfile.ZipFile(user_archive) as zf:
            def user_table(name: str) -> pd.DataFrame:
                member = next(m for m in zf.namelist() if m.endswith(f"tables/{name}"))
                return pd.read_csv(io.BytesIO(zf.read(member))).set_index("operator")

            def compare(name: str, user_column: str, authoritative: pd.DataFrame,
                        authoritative_column: str, quantity: str) -> None:
                user_df = user_table(name)
                auth_df = authoritative.set_index("operator")
                for operator in sorted(set(user_df.index) & set(auth_df.index)):
                    user_value = user_df.loc[operator, user_column]
                    auth_value = auth_df.loc[operator, authoritative_column]
                    comparison_rows.append({
                        "table": name, "operator": operator, "quantity": quantity,
                        "user_value": user_value, "authoritative_value": auth_value,
                        "absolute_difference": abs(float(user_value) - float(auth_value)),
                    })

            compare("symmetric_system_availability.csv", "symmetry_residual", availability,
                    "symmetry_residual", "weighted_symmetry_residual")
            compare("symmetric_system_availability.csv", "min_eigenvalue", availability,
                    "min_eigenvalue_symmetric_part", "min_eigenvalue_symmetric_part")
            compare("poisson_solver_comparison.csv", "cg_forced_solution_error", poisson,
                    "cg_symmetric_part_diagnostic_solution_error", "diagnostic_cg_solution_error")
            compare("poisson_solver_comparison.csv", "gmres_solution_error", poisson,
                    "gmres_original_solution_error", "gmres_solution_error")
            compare("implicit_heat_step.csv", "weighted_symmetry_residual", heat,
                    "weighted_symmetry_residual", "backward_euler_weighted_symmetry_residual")
    pd.DataFrame(comparison_rows).to_csv(output / "user_authoritative_comparison.csv", index=False)

    readme = """# Solver-consequence analysis (authoritative)

This directory is generated by `scripts/analyze_solver_consequences_v2.py` from the released exact operator arrays and the immutable primary run archive.

The analysis tests availability of a symmetric positive-definite weighted system. The `cg_symmetric_part_diagnostic` route deliberately solves the symmetric part of a nonsymmetric weighted reference system. Its solution error interprets the weighted-symmetry residual; it is not a proposed practical solver and is not evidence that the reference cannot be solved. Dense direct solves, GMRES, and BiCGSTAB are applied to the original reference matrices. The direct and nonsymmetric Krylov solutions remain at the discretization-error level, so the large forced-CG error is attributable to symmetrization. Iteration counts may vary slightly across SciPy/BLAS builds and are not used for cross-family speed claims.

The negative minimum eigenvalues of the symmetric parts for the order-six and order-eight references are the same quadratic-form obstruction measured by the positive logarithmic energy rates in `derived/downstream_analysis_v3`; they are not independent evidence.

Authoritative headline values are collected in `headline_solver_consequences.csv`; `solver_guarantees_table.csv` is the compact source for the manuscript table. The original user-supplied notebook and its outputs are preserved separately under `notebooks/`, `runs/`, and `source_artifacts/` for provenance.
"""
    (output / "README.md").write_text(readme, encoding="utf-8")


    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
