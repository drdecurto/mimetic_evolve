#!/usr/bin/env python3
"""Audit MOLE reference provenance and the boundary identity used in this release.

The immutable campaign notebook historically labels its embedded MOLE arrays as
Castillo--Grone.  MOLE's pinned source and upstream documentation identify the
implemented high-order construction with Corbino--Castillo.  This audit verifies
that the archived coefficient blocks match that source and distinguishes the
general Corbino--Castillo boundary operator from the sparse endpoint selector
imposed by the discovery compiler.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import zipfile
from fractions import Fraction
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import linalg as la

UPSTREAM_TAG = "v1.2.0"
UPSTREAM_COMMIT = "15de866"
ARCHIVE_PREFIX = "mimetic_operator_discovery_results_v11/operators/"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def parse_fraction(token: str) -> Fraction:
    token = token.strip()
    if not token:
        raise ValueError("empty coefficient token")
    return Fraction(token)


def parse_matlab_A(path: Path, order: int) -> np.ndarray:
    text = path.read_text(encoding="utf-8")
    case_match = re.search(rf"\bcase\s+{order}\b", text)
    if not case_match:
        raise KeyError(f"case {order} not found in {path.name}")
    tail = text[case_match.end():]
    next_case = re.search(r"\n\s*case\s+\d+", tail)
    block = tail[: next_case.start()] if next_case else tail
    a_match = re.search(r"A\s*=\s*\[(.*?)\];", block, flags=re.S)
    if not a_match:
        raise KeyError(f"A matrix for case {order} not found in {path.name}")
    body = a_match.group(1).replace("...", " ")
    rows = []
    for row in body.split(";"):
        tokens = row.split()
        if tokens:
            rows.append([float(parse_fraction(tok)) for tok in tokens])
    widths = {len(row) for row in rows}
    if len(widths) != 1:
        raise ValueError(f"ragged A matrix in {path.name}, case {order}: {widths}")
    return np.asarray(rows, dtype=float)


def load_npz_from_zip(zf: zipfile.ZipFile, name: str) -> dict[str, np.ndarray]:
    with np.load(io.BytesIO(zf.read(name)), allow_pickle=False) as z:
        return {key: np.asarray(z[key]) for key in z.files}


def source_blocks(source_dir: Path, order: int) -> tuple[np.ndarray, np.ndarray]:
    div_path = source_dir / "divNonPeriodic.m"
    grad_path = source_dir / "gradNonPeriodic.m"
    D = np.asarray([[-1.0, 1.0]], float) if order == 2 else parse_matlab_A(div_path, order)
    G = parse_matlab_A(grad_path, order)
    return D, G


def endpoint_selector(rows: int, cols: int) -> np.ndarray:
    B0 = np.zeros((rows, cols), dtype=float)
    B0[0, 0] = -1.0
    B0[-1, -1] = 1.0
    return B0


def interior_injection(cells: int) -> np.ndarray:
    E = np.zeros((cells + 2, cells), dtype=float)
    E[1:-1, :] = np.eye(cells)
    return E


def relnorm(A: np.ndarray, scale: np.ndarray | float) -> float:
    den = float(scale) if np.ndim(scale) == 0 else float(la.norm(scale, 2))
    return float(la.norm(A, 2) / max(den, 1e-300))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--output", type=Path, default=None)
    args = ap.parse_args()
    root = args.repo_root.resolve()
    out = (args.output or root / "derived" / "reference_attribution_audit").resolve()
    out.mkdir(parents=True, exist_ok=True)

    source_dir = root / "source_artifacts" / "mole_v1.2.0_matlab_octave"
    run_zip = root / "runs" / "v11_original_results.zip"
    if not run_zip.exists():
        raise FileNotFoundError(run_zip)

    source_rows: list[dict] = []
    diagnostic_rows: list[dict] = []
    with zipfile.ZipFile(run_zip) as zf:
        for order in (2, 4, 6, 8):
            name = f"reference_mole_k{order}_m200.npz"
            data = load_npz_from_zip(zf, ARCHIVE_PREFIX + name)
            D = np.asarray(data["D"], float)
            G = np.asarray(data["G"], float)
            q = np.asarray(data["q"], float)
            p = np.asarray(data["p"], float)
            cells = int(np.asarray(data["cells"]).reshape(-1)[0])
            h = 1.0 / cells
            Dbar, Gbar = h * D, h * G
            src_D, src_G = source_blocks(source_dir, order)
            notebook_D = Dbar[1:2, 0:2] if order == 2 else Dbar[1:1 + src_D.shape[0], :src_D.shape[1]]
            notebook_G = Gbar[:src_G.shape[0], :src_G.shape[1]]
            d_err = float(np.max(np.abs(notebook_D - src_D)))
            g_err = float(np.max(np.abs(notebook_G - src_G)))
            source_rows.append({
                "order": order,
                "reference_file": name,
                "upstream_family": "Corbino-Castillo",
                "upstream_implementation": "MOLE v1.2.0",
                "upstream_commit": UPSTREAM_COMMIT,
                "D_left_block_max_abs_error": d_err,
                "G_left_block_max_abs_error": g_err,
                "source_match_pass": bool(max(d_err, g_err) < 1e-14),
            })

            Q, P = np.diag(q), np.diag(p)
            E = interior_injection(cells)
            QI = E.T @ Q @ E
            LI = E.T @ D @ G @ E
            B_native = Q @ D + G.T @ P
            B0 = endpoint_selector(*B_native.shape)
            boundary_term = E.T @ B_native @ G @ E
            eig = la.eigvals(LI)
            eig_scale = max(1.0, float(np.max(np.abs(eig))))
            rows = np.where(np.linalg.norm(B_native, axis=1) > 1e-10)[0]
            cols = np.where(np.linalg.norm(B_native, axis=0) > 1e-10)[0]
            sep_resid = relnorm(E.T @ Q - QI @ E.T, E.T @ Q)
            diagnostic_rows.append({
                "order": order,
                "cells": cells,
                "min_q": float(q.min()),
                "min_p": float(p.min()),
                "q_positive": bool(q.min() > 0),
                "p_positive": bool(p.min() > 0),
                "nonreal_eigenvalues": int(np.sum(np.abs(eig.imag) > 1e-8 * eig_scale)),
                "scalar_norm_dirichlet_separation_residual": sep_resid,
                "weighted_symmetry_residual": relnorm(QI @ LI - LI.T @ QI, QI @ LI),
                "native_B_minus_endpoint_B0_relative_norm": relnorm(B_native - B0, B_native),
                "interior_boundary_term_relative_norm": relnorm(boundary_term, QI @ LI),
                "native_B_nonzero_row_count": int(len(rows)),
                "native_B_nonzero_col_count": int(len(cols)),
                "native_B_leftmost_rows": ",".join(map(str, rows[: min(20, len(rows))])),
                "native_B_rightmost_rows": ",".join(map(str, rows[max(0, len(rows)-20):])),
                "endpoint_supported_identity_holds": bool(la.norm(B_native - B0, 2) <= 1e-10),
            })

    src_df = pd.DataFrame(source_rows)
    diag_df = pd.DataFrame(diagnostic_rows)
    src_df.to_csv(out / "mole_reference_source_match.csv", index=False)
    diag_df.to_csv(out / "mole_boundary_operator_diagnostics.csv", index=False)

    # Verify that the promoted candidates satisfy the two sufficient conditions
    # used by the corrected Dirichlet-symmetry proposition.
    candidate_rows: list[dict] = []
    for path in sorted((root / "derived" / "operators").glob("*.npz")):
        with np.load(path, allow_pickle=False) as z:
            D = np.asarray(z["D"], float)
            G = np.asarray(z["G"], float)
            Q = np.asarray(z["Q"], float)
            P = np.asarray(z["P"], float)
            cells = int(np.asarray(z["cells"]).reshape(-1)[0])
        E = interior_injection(cells)
        QI = E.T @ Q @ E
        LI = E.T @ D @ G @ E
        B0 = endpoint_selector(D.shape[0], D.shape[1])
        identity_resid = relnorm(Q @ D + G.T @ P - B0, B0)
        separation_resid = relnorm(E.T @ Q - QI @ E.T, E.T @ Q)
        interior_B_resid = relnorm(E.T @ B0 @ G @ E, QI @ LI)
        symmetry_resid = relnorm(QI @ LI - LI.T @ QI, QI @ LI)
        candidate_rows.append({
            "operator_file": path.name,
            "cells": cells,
            "endpoint_identity_relative_residual": identity_resid,
            "scalar_norm_dirichlet_separation_residual": separation_resid,
            "interior_boundary_term_relative_residual": interior_B_resid,
            "weighted_symmetry_residual": symmetry_resid,
            "proposition_conditions_pass": bool(max(identity_resid, separation_resid, interior_B_resid) < 1e-10),
        })
    cand_df = pd.DataFrame(candidate_rows)
    cand_df.to_csv(out / "compiled_candidate_identity_diagnostics.csv", index=False)

    provenance = {
        "audit_version": "mole_reference_attribution_v2",
        "upstream_project": "MOLE: Mimetic Operators Library Enhanced",
        "upstream_tag": UPSTREAM_TAG,
        "upstream_commit": UPSTREAM_COMMIT,
        "upstream_statement": (
            "MOLE states that its mathematics is based on Corbino and Castillo (2020); "
            "Castillo and Grone (2003) are cited as earlier similar matrix-analysis operators."
        ),
        "source_snapshots": {p.name: sha256(p) for p in sorted(source_dir.iterdir()) if p.is_file()},
        "all_reference_blocks_match_upstream_source": bool(src_df["source_match_pass"].all()),
        "all_compiled_candidates_satisfy_proposition_conditions": bool(cand_df["proposition_conditions_pass"].all()),
        "corrected_reference_label": "MOLE/Corbino-Castillo",
        "boundary_identity_distinction": {
            "reference": (
                "The MOLE/Corbino-Castillo arrays satisfy a general mimetic identity "
                "B_CC = QD + G^T P whose boundary operator extends over closure rows."
            ),
            "compiler": (
                "The discovery compiler imposes B0 = -e_1 e_1^T + e_{m+2} e_{m+1}^T, "
                "together with E^T Q = Q_I E^T; consequently E^T B0 G E = 0."
            ),
            "consequence": (
                "Non-real reference eigenvalues do not contradict the general Corbino-Castillo "
                "extended-Gauss identity. They preclude an SPD self-adjoint similarity of the "
                "Dirichlet block and show that the stricter endpoint-supported identity is absent."
            ),
        },
        "immutable_run_note": (
            "The archived notebook and raw result metadata retain the historical Castillo-Grone label "
            "for provenance. Authoritative analysis and derived analyses use the corrected attribution."
        ),
    }
    (out / "mole_reference_attribution.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "README.md").write_text(
        """# MOLE reference attribution and boundary-operator audit

This directory is authoritative for naming the reference arrays used by the study. The translated MOLE coefficient blocks match the pinned v1.2.0 MATLAB/Octave source to machine precision and are attributed to the Corbino--Castillo construction.

The audit distinguishes the general MOLE/Corbino--Castillo boundary operator `B_CC = QD + G^T P` from the sparse endpoint selector `B0` imposed by the discovery compiler. The corrected Dirichlet-symmetry proposition also requires scalar-norm separation under elimination, `E^T Q = Q_I E^T`. The compiled candidates satisfy both this condition and `E^T B0 G E = 0`; the MOLE boundary operator does not satisfy the latter.

Historical labels inside immutable raw notebooks and run archives are preserved but superseded. See `docs/MOLE_REFERENCE_ATTRIBUTION_AND_BOUNDARY_OPERATOR_CORRECTION.md`.
""",
        encoding="utf-8",
    )

    if not src_df["source_match_pass"].all():
        raise AssertionError("one or more notebook reference blocks do not match pinned MOLE source")
    if not (diag_df.loc[diag_df.order.isin([6, 8]), "endpoint_supported_identity_holds"] == False).all():
        raise AssertionError("high-order references unexpectedly satisfy endpoint-supported B0")
    if not cand_df["proposition_conditions_pass"].all():
        raise AssertionError("one or more promoted candidates fail the corrected proposition conditions")
    print(src_df.to_string(index=False))
    print(diag_df[["order", "nonreal_eigenvalues", "weighted_symmetry_residual",
                   "native_B_minus_endpoint_B0_relative_norm", "interior_boundary_term_relative_norm"]].to_string(index=False))
    print(cand_df.to_string(index=False))
    print("MOLE reference attribution audit: PASS")


if __name__ == "__main__":
    main()
