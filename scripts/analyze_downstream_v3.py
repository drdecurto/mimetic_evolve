#!/usr/bin/env python3
"""Corrected downstream consequences for the exact mimetic operators.

This script supersedes the exploratory energy-growth calculation in
``source_artifacts/mimetic_analysis_v2.zip``.  It evaluates the Q-energy rate as
a generalized eigenvalue, excludes indefinite reference weights from energy
claims, and reports finite-time Q-energy amplification, RK stability limits,
and solver structure without turning those diagnostics into search objectives.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import re
import tempfile
import zipfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import linalg as la


def load_npz(path_or_bytes):
    if isinstance(path_or_bytes, (bytes, bytearray)):
        z = np.load(io.BytesIO(path_or_bytes), allow_pickle=False)
    else:
        z = np.load(path_or_bytes, allow_pickle=False)
    D, G = np.asarray(z['D'], float), np.asarray(z['G'], float)
    if 'Q' in z.files:
        Q = np.asarray(z['Q'], float)
    else:
        q = np.asarray(z['q'], float); Q = np.diag(q) if q.ndim == 1 else q
    if 'P' in z.files:
        P = np.asarray(z['P'], float)
    else:
        p = np.asarray(z['p'], float); P = np.diag(p) if p.ndim == 1 else p
    cells = int(np.asarray(z['cells']).reshape(-1)[0]) if 'cells' in z.files else D.shape[0] - 2
    metadata = {}
    if 'metadata_json' in z.files:
        try:
            metadata = json.loads(str(np.asarray(z['metadata_json']).reshape(-1)[0]))
        except Exception:
            metadata = {}
    return {'D': D, 'G': G, 'Q': Q, 'P': P, 'cells': cells, 'metadata': metadata}


def interior(op):
    L = op['D'] @ op['G']
    return L[1:-1, 1:-1], op['Q'][1:-1, 1:-1]



REQUIRED_NOVELTY_FAMILIES = (
    'corbino_castillo', 'castillo_grone_extensions', 'strand',
    'mattsson_nordstrom', 'generalized_sbp_block_norm'
)
FINGERPRINT_LENGTH = 6


def _as_int_list(value, fallback):
    """Parse integer metadata stored as numbers, sequences, or archive strings."""
    if value is None:
        return list(fallback)
    if isinstance(value, str):
        found = [int(x) for x in re.findall(r'\d+', value)]
        return found or list(fallback)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return [int(value)]
    try:
        out = [int(x) for x in value]
        return out or list(fallback)
    except Exception:
        return list(fallback)


def _target_order(name, op):
    meta = op.get('metadata', {})
    for key in ('target_order', 'interior_order', 'order'):
        try:
            if key in meta:
                return int(meta[key])
        except Exception:
            pass
    m = re.search(r'(?:^|_)k(\d+)(?:_|$)', name)
    return int(m.group(1)) if m else None


def boundary_blocks(name, op, rows=None, support=None):
    """Return comparable left-corner blocks with type-stable metadata parsing."""
    meta = op.get('metadata', {})
    row_values = _as_int_list(meta.get('left_rows') or meta.get('boundary_rows'), [6])
    support_values = _as_int_list(meta.get('left_support_profile') or meta.get('support_width'), [12])
    rows = int(rows if rows is not None else row_values[0])
    support = int(support if support is not None else max(support_values))
    rows = max(1, min(rows + 1, op['D'].shape[0] // 3))
    support = max(2, min(support + 2, op['D'].shape[1] // 3))
    return {'D_corner': op['D'][:rows, :support].copy(),
            'G_corner': op['G'][:rows, :support].copy()}


def _canonical_block(block):
    block = np.asarray(block, float)
    scale = float(np.max(np.abs(block))) if block.size else 0.0
    if scale == 0:
        return block.copy()
    out = block / scale
    for value in out.ravel():
        if abs(value) > 1e-12:
            if value < 0:
                out = -out
            break
    return out


def _block_distance(a, b):
    """Distance on the largest common corner, with shape agreement reported separately."""
    rows, cols = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1])
    if rows == 0 or cols == 0:
        return float('inf'), False
    same_shape = a.shape == b.shape
    ca = _canonical_block(a[:rows, :cols])
    view = b[:rows, :cols]
    candidates = [_canonical_block(view), _canonical_block(view[::-1, ::-1]),
                  _canonical_block(-view), _canonical_block(-view[::-1, ::-1])]
    return float(min(np.max(np.abs(ca-c)) for c in candidates)), bool(same_shape)


def _padded_singular_values(block, length=FINGERPRINT_LENGTH):
    values = la.svdvals(np.asarray(block, float))
    values = values / max(float(np.max(np.abs(block))), 1e-300)
    out = np.zeros(length)
    out[:min(length, values.size)] = values[:length]
    return out


def _fingerprint(name, op):
    L, _ = interior(op)
    h = 1.0 / op['cells']
    eig = la.eigvals(L)
    blocks = boundary_blocks(name, op)
    return {
        'scaled_spectral_radius': float(np.max(np.abs(eig))*h*h),
        'nonreal_modes': int(np.sum(np.abs(eig.imag) > 1e-8*max(1.0, np.max(np.abs(eig))))),
        'leading_eigenvalues': np.sort(eig.real)[-FINGERPRINT_LENGTH:]*h*h,
        'D_corner_singular_values': _padded_singular_values(blocks['D_corner']),
        'G_corner_singular_values': _padded_singular_values(blocks['G_corner']),
    }


def _fingerprint_distance(a, b):
    """Symmetrically normalized distance; fixed padding avoids undefined shape comparisons."""
    distances = []
    for key in ('leading_eigenvalues', 'D_corner_singular_values', 'G_corner_singular_values'):
        u, v = np.asarray(a[key], float), np.asarray(b[key], float)
        if u.shape != v.shape:
            return float('inf')
        scale = max(float(np.max(np.abs(u))), float(np.max(np.abs(v))), 1e-12)
        distances.append(float(np.max(np.abs(u-v))/scale))
    sr_scale = max(abs(float(a['scaled_spectral_radius'])), abs(float(b['scaled_spectral_radius'])), 1e-12)
    distances.append(abs(float(a['scaled_spectral_radius'])-float(b['scaled_spectral_radius']))/sr_scale)
    distances.append(0.0 if int(a['nonreal_modes']) == int(b['nonreal_modes']) else 1.0)
    return float(max(distances))


def novelty_screen(operators, out):
    """Run a conservative partial screen; non-comparability declarations do not close the gate."""
    library = []
    for name, (provenance, op) in operators.items():
        if provenance != 'reference':
            continue
        blocks = boundary_blocks(name, op, rows=8, support=12)
        order = _target_order(name, op)
        library.append({'family': f'corbino_castillo_k{order}', 'target_order': order,
                        'D_corner': blocks['D_corner'], 'G_corner': blocks['G_corner'],
                        'source': 'pinned MOLE v1.2.0 Corbino-Castillo implementation'})

    # Optional external entries and documentary declarations.
    external_dir = out.parent/'novelty_library'
    declarations = {}
    if external_dir.exists():
        for path in sorted(external_dir.glob('*.json')):
            try:
                entry = json.loads(path.read_text())
            except Exception:
                continue
            if 'D_corner' in entry and 'G_corner' in entry:
                entry['D_corner'] = np.asarray(entry['D_corner'], float)
                entry['G_corner'] = np.asarray(entry['G_corner'], float)
                entry.setdefault('family', path.stem)
                entry['source'] = str(path)
                library.append(entry)
            elif 'family' in entry and 'applicable' in entry:
                declarations[str(entry['family']).lower()] = entry

    screened = [(name, op) for name, (prov, op) in operators.items()
                if prov in ('promoted', 'followup')]
    block_rows, fp_rows = [], []
    fingerprints = {name: _fingerprint(name, op) for name, (_, op) in operators.items()}
    for name, op in screened:
        blocks = boundary_blocks(name, op)
        for entry in library:
            dd, ds = _block_distance(blocks['D_corner'], entry['D_corner'])
            gd, gs = _block_distance(blocks['G_corner'], entry['G_corner'])
            distance = max(dd, gd)
            same_shape = bool(ds and gs)
            block_rows.append({'operator': name, 'library_family': entry['family'],
                               'target_order': _target_order(name, op),
                               'library_target_order': entry.get('target_order'),
                               'block_distance': distance, 'same_block_shape': same_shape,
                               'match': bool(same_shape and distance < 1e-6)})
        for other_name, (other_prov, other_op) in operators.items():
            if other_name == name:
                continue
            fp_rows.append({'operator': name, 'compared_with': other_name,
                            'provenance': other_prov,
                            'same_target_order': _target_order(name, op) == _target_order(other_name, other_op),
                            'fingerprint_distance': _fingerprint_distance(fingerprints[name], fingerprints[other_name])})

    block_df = pd.DataFrame(block_rows)
    fp_df = pd.DataFrame(fp_rows)
    block_df.to_csv(out/'novelty_block_comparisons.csv', index=False)
    fp_df.to_csv(out/'novelty_fingerprint_distances.csv', index=False)

    loaded_names = {str(e.get('family','')).lower() for e in library}
    status = {}
    for family in REQUIRED_NOVELTY_FAMILIES:
        if any(family in name for name in loaded_names):
            status[family] = 'compared'
        elif family in declarations and declarations[family].get('applicable') is False:
            status[family] = 'documented_not_directly_comparable'
        else:
            status[family] = 'outstanding'
    # Conservative rule: a documentary non-comparability statement is useful metadata,
    # but does not by itself establish literature-level non-equivalence.
    outstanding = [f for f, state in status.items() if state != 'compared']
    any_direct_match = bool(len(block_df) and block_df['match'].any())
    same_order_fp = fp_df[fp_df['same_target_order']] if len(fp_df) else fp_df
    any_fp_near_match = bool(len(same_order_fp) and (same_order_fp['fingerprint_distance'] < 1e-6).any())
    gate = {
        'screen_version': 'v3.2_topology_scoped_partial',
        'screening_methods': ['corner_blocks_scale_sign_reflection', 'fixed_length_singular_value_fingerprint'],
        'family_status': status,
        'library_families_loaded': sorted(loaded_names),
        'documented_not_directly_comparable': {k: v.get('justification','') for k,v in declarations.items()
                                               if v.get('applicable') is False},
        'required_families_outstanding': outstanding,
        'direct_comparison_scope': 'same target order and common staggered degree-of-freedom placement',
        'required_same_topology_families_outstanding': [
            f for f in ('castillo_grone_extensions', 'generalized_sbp_block_norm') if status.get(f) != 'compared'
        ],
        'cross_topology_families_requiring_mapping': [
            f for f in ('strand', 'mattsson_nordstrom') if status.get(f) != 'compared'
        ],
        'library_complete': not outstanding,
        'all_fingerprint_distances_finite': bool(len(fp_df) and np.isfinite(fp_df['fingerprint_distance']).all()),
        'any_direct_match': any_direct_match,
        'any_same_order_fingerprint_near_match': any_fp_near_match,
        'novelty_claim_supported': bool(len(block_df)) and not outstanding and not any_direct_match and not any_fp_near_match,
        'interpretation': ('No match is found among the loaded same-topology MOLE/Corbino-Castillo references. '
                           'Parameterized or compact higher-order Castillo-Grone extensions and generalized/block-norm '
                           'staggered comparisons remain outstanding. Classical nodal SBP families require an explicit '
                           'topology map before coefficient equivalence is meaningful; literature-level novelty is therefore not established.')
    }
    (out/'partial_novelty_gate.json').write_text(json.dumps(gate, indent=2)+'\n')
    (out/'novelty_library_coefficient_template.json').write_text(json.dumps({
        'family':'castillo_grone_extension_k6', 'reference':'full citation and table/equation',
        'target_order':6, 'topology':'staggered', 'D_corner':[[0.0]], 'G_corner':[[0.0]]}, indent=2)+'\n')
    (out/'novelty_library_declaration_template.json').write_text(json.dumps({
        'family':'strand', 'applicable':False, 'reference':'full citation',
        'justification':'Explain why no faithful staggered-grid coefficient mapping is defined. '
                        'This records scope but does not close the novelty gate.'}, indent=2)+'\n')
    return gate


def q_spd(Q, tol=1e-13):
    e = la.eigvalsh((Q + Q.T) / 2)
    return bool(e[0] > tol), float(e[0]), float(e[-1])


def weighted_symmetry_residual(L, Q):
    return float(la.norm(Q @ L - L.T @ Q, 2) / max(la.norm(Q @ L, 2), 1e-300))


def relative_energy_rate(L, Q):
    # If E_Q = 1/2 u^T Q u, then max_u (dE_Q/dt)/E_Q is the
    # largest generalized eigenvalue of (L^T Q + Q L, Q).
    return float(la.eigh(L.T @ Q + Q @ L, Q, eigvals_only=True)[-1])


def rk_limit_scaled_from_eig(eig, h, order):
    if order == 2:
        def R(z): return 1 + z + z*z/2
    elif order == 4:
        def R(z): return 1 + z + z*z/2 + z*z*z/6 + z*z*z*z/24
    else:
        raise ValueError(order)
    def stable(dt): return float(np.max(np.abs(R(dt * eig)))) <= 1 + 1e-12
    lo, hi = 0.0, h*h
    while stable(hi) and hi < 100*h*h: hi *= 2
    for _ in range(80):
        mid = (lo + hi) / 2
        if stable(mid): lo = mid
        else: hi = mid
    return float(lo / (h*h))


def q_factors(Q):
    w, V = la.eigh((Q + Q.T) / 2)
    if w[0] <= 0: raise ValueError('Q is not SPD')
    S = (V * np.sqrt(w)) @ V.T
    Si = (V * (1 / np.sqrt(w))) @ V.T
    return S, Si


def transient_history(L, Q, taus, h):
    # Dimensionless generator A = h^2 L; tau = t/h^2.
    S, Si = q_factors(Q)
    A = L * h*h
    vals, V = la.eig(A)
    Vi = la.inv(V)
    out = []
    for tau in taus:
        expA = V @ np.diag(np.exp(vals * tau)) @ Vi
        M = S @ expA @ Si
        amp = float(la.svdvals(M)[0] ** 2)
        out.append(amp)
    return np.asarray(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument('--output', type=Path, default=None)
    args = ap.parse_args()
    root = args.repo_root.resolve()
    out = (args.output or root/'derived'/'downstream_analysis_v3').resolve()
    (out/'figures').mkdir(parents=True, exist_ok=True)

    operators = {}
    for p in sorted((root/'derived'/'operators').glob('*.npz')):
        operators[p.stem] = ('promoted', load_npz(p))
    for p in sorted((root/'derived'/'followup_operators').glob('*.npz')):
        operators[p.stem] = ('followup', load_npz(p))

    run = root/'runs'/'v11_original_results.zip'
    prefix = 'mimetic_operator_discovery_results_v11/operators/'
    with zipfile.ZipFile(run) as z:
        for k in (2, 4, 6, 8):
            name = f'reference_mole_k{k}_m200.npz'
            operators[name[:-4]] = ('reference', load_npz(z.read(prefix + name)))

    rows = []
    for name, (provenance, op) in sorted(operators.items()):
        L, Q = interior(op); h = 1.0 / op['cells']
        spd, qmin, qmax = q_spd(Q)
        eig = la.eigvals(L)
        row = {
            'operator': name,
            'provenance': provenance,
            'cells': op['cells'],
            'q_spd': spd,
            'q_min_eigenvalue': qmin,
            'q_condition': (qmax/qmin if spd else np.nan),
            'nonreal_eigenvalues': int(np.sum(np.abs(eig.imag) > 1e-8 * max(1.0, np.max(np.abs(eig))))),
            'operator_condition_2': float(np.linalg.cond(L)),
            'rk2_dt_over_h2': rk_limit_scaled_from_eig(eig, h, 2),
            'rk4_dt_over_h2': rk_limit_scaled_from_eig(eig, h, 4),
        }
        if spd:
            mu = relative_energy_rate(L, Q)
            residual = weighted_symmetry_residual(L, Q)
            row.update({
                'weighted_symmetry_residual': residual,
                'max_relative_q_energy_rate': mu,
                'h2_max_relative_q_energy_rate': h*h*mu,
                'certified_q_contractive_numerically': bool(mu <= 1e-8 and residual <= 1e-9),
                'weighted_spd_form_available': bool(residual <= 1e-9 and la.eigvalsh(-(Q@L + L.T@Q)/2)[0] > 0),
            })
        else:
            row.update({
                'weighted_symmetry_residual': np.nan,
                'max_relative_q_energy_rate': np.nan,
                'h2_max_relative_q_energy_rate': np.nan,
                'certified_q_contractive_numerically': False,
                'weighted_spd_form_available': False,
            })
        rows.append(row)
    all_df = pd.DataFrame(rows)
    all_df.to_csv(out/'all_operator_energy_timestep_solver.csv', index=False)

    candidate_name = 'structure_only_prog_k6_block_psd_reflection_min_next_moment_973378905933_m200'
    reference_name = 'reference_mole_k6_m200'
    candidate = operators[candidate_name][1]
    reference = operators[reference_name][1]
    Lc, Qc = interior(candidate); Lr, Qr = interior(reference)
    h = 1 / 200
    # A compact grid contains the observed peak and keeps clean-room reproduction fast.
    taus = np.asarray([0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30,
                       0.32, 0.33, 0.333, 0.34, 0.35, 0.40, 0.50, 0.60])
    ac = transient_history(Lc, Qc, taus, h)
    ar = transient_history(Lr, Qr, taus, h)
    jf = int(np.argmax(ar)); tau_max = float(taus[jf]); amp_max = float(ar[jf])
    # Validate the eigendecomposition evaluation with a direct matrix exponential at the maximum.
    Sr, Sri = q_factors(Qr)
    direct = Sr @ la.expm((Lr*h*h)*tau_max) @ Sri
    direct_amp = float(la.svdvals(direct)[0]**2)

    history = pd.DataFrame({'tau_t_over_h2': taus,
                            'leading_exact_candidate_q_energy_amplification': ac,
                            'mole_order6_native_q_energy_amplification': ar})
    history.to_csv(out/'headline_energy_transient_history.csv', index=False)

    plt.figure(figsize=(6.4, 3.7))
    plt.plot(taus, ac, label='Exact candidate (certified Q)')
    plt.plot(taus, ar, label='MOLE/Corbino-Castillo order 6 (native Q)')
    plt.axhline(1.0, linewidth=0.8)
    plt.xlabel(r'Dimensionless time $t/h^2$')
    plt.ylabel(r'Maximum $Q$-energy amplification')
    plt.legend(frameon=False)
    plt.tight_layout()
    plt.savefig(out/'figures'/'energy_transient_order6.png', dpi=220)
    plt.close()

    idx = all_df.set_index('operator')
    headline = pd.DataFrame([
        {
            'operator': candidate_name,
            'role': 'leading_exact_candidate',
            'h2_max_relative_q_energy_rate': idx.loc[candidate_name,'h2_max_relative_q_energy_rate'],
            'max_q_energy_amplification_tau_0_to_0p6': float(ac.max()),
            'tau_of_max_amplification': float(taus[int(np.argmax(ac))]),
            'rk4_dt_over_h2': idx.loc[candidate_name,'rk4_dt_over_h2'],
            'weighted_symmetry_residual': idx.loc[candidate_name,'weighted_symmetry_residual'],
            'nonreal_eigenvalues': idx.loc[candidate_name,'nonreal_eigenvalues'],
        },
        {
            'operator': reference_name,
            'role': 'order6_reference_native_quadrature',
            'h2_max_relative_q_energy_rate': idx.loc[reference_name,'h2_max_relative_q_energy_rate'],
            'max_q_energy_amplification_tau_0_to_0p6': amp_max,
            'tau_of_max_amplification': tau_max,
            'rk4_dt_over_h2': idx.loc[reference_name,'rk4_dt_over_h2'],
            'weighted_symmetry_residual': idx.loc[reference_name,'weighted_symmetry_residual'],
            'nonreal_eigenvalues': idx.loc[reference_name,'nonreal_eigenvalues'],
        },
    ])
    headline.to_csv(out/'headline_downstream_metrics.csv', index=False)

    novelty = novelty_screen(operators, out)

    report = {
        'analysis_version': 'v3.2_topology_scoped_partial_novelty_screen',
        'supersedes': 'the exploratory energy-growth interpretation in source_artifacts/mimetic_analysis_v2.zip; incorporates safe novelty-screen fixes from source_artifacts/mimetic_analysis_v3.zip',
        'operators_analysed': len(operators),
        'headline_candidate': candidate_name,
        'headline_reference': reference_name,
        'candidate_h2_max_relative_q_energy_rate': float(idx.loc[candidate_name,'h2_max_relative_q_energy_rate']),
        'reference_h2_max_relative_q_energy_rate_native_q': float(idx.loc[reference_name,'h2_max_relative_q_energy_rate']),
        'reference_max_transient_q_energy_amplification': amp_max,
        'reference_tau_of_max_amplification': tau_max,
        'direct_expm_validation_amplification': direct_amp,
        'candidate_rk4_dt_over_h2': float(idx.loc[candidate_name,'rk4_dt_over_h2']),
        'reference_rk4_dt_over_h2': float(idx.loc[reference_name,'rk4_dt_over_h2']),
        'caveat': 'The reference result is specific to its native positive quadrature and does not exclude another Lyapunov norm. Indefinite weights are excluded from Q-energy claims.',
        'novelty': novelty,
    }
    (out/'downstream_report_v3.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
