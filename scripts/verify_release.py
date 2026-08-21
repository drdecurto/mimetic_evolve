#!/usr/bin/env python3
"""Fail-closed integrity and claim audit for the release package."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''): h.update(block)
    return h.hexdigest()


def check(cond: bool, message: str) -> None:
    if not cond:
        raise AssertionError(message)
    print('PASS', message)


def verify_package_manifest() -> None:
    manifest=ROOT/'MANIFEST.sha256'
    if not manifest.exists():
        print('SKIP package manifest not created yet')
        return
    count=0
    for line in manifest.read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        expected, rel=line.split('  ',1)
        path=ROOT/rel
        if not path.exists(): raise AssertionError(f'manifest path missing: {rel}')
        if digest(path)!=expected: raise AssertionError(f'manifest hash mismatch: {rel}')
        count += 1
    check(count > 0, f'package manifest hashes verified ({count} files)')


def verify_nested_run() -> None:
    archive=ROOT/'runs'/'v11_original_results.zip'
    check(archive.exists(), 'immutable v11 run archive present')
    with zipfile.ZipFile(archive) as z:
        check(z.testzip() is None, 'v11 ZIP CRC integrity')
        prefix='mimetic_operator_discovery_results_v11/'
        lines=z.read(prefix+'MANIFEST.sha256').decode().splitlines()
        count=0
        names=set(z.namelist())
        for line in lines:
            if not line.strip(): continue
            expected, rel=line.split('  ',1)
            # The archived manifest uses paths relative to its root.
            name=prefix+rel
            if name not in names: raise AssertionError(f'v11 manifest member missing: {rel}')
            if hashlib.sha256(z.read(name)).hexdigest()!=expected:
                raise AssertionError(f'v11 manifest hash mismatch: {rel}')
            count += 1
        check(count > 0, f'v11 internal manifest hashes verified ({count} files)')
        scan=json.loads(z.read(prefix+'secret_scan.json'))
        check((scan.get('status')=='pass' or scan.get('passed') is True) and not scan.get('findings'), 'archived secret scan')


def verify_followup_runs() -> None:
    specs = [
        ('v12_failed_results.zip', 'mimetic_operator_discovery_results_v12/'),
        ('v12_1_followup_results.zip', 'mimetic_operator_discovery_results_v12_1/'),
    ]
    for archive_name, prefix in specs:
        archive = ROOT/'runs'/archive_name
        check(archive.exists(), f'{archive_name} present')
        with zipfile.ZipFile(archive) as z:
            check(z.testzip() is None, f'{archive_name} ZIP CRC integrity')
            lines = z.read(prefix+'MANIFEST.sha256').decode().splitlines()
            names = set(z.namelist())
            count = 0
            for line in lines:
                if not line.strip():
                    continue
                expected, rel = line.split('  ', 1)
                name = prefix + rel
                if name not in names:
                    raise AssertionError(f'{archive_name} manifest member missing: {rel}')
                if hashlib.sha256(z.read(name)).hexdigest() != expected:
                    raise AssertionError(f'{archive_name} manifest hash mismatch: {rel}')
                count += 1
            check(count > 0, f'{archive_name} internal manifest hashes verified ({count} files)')
            scan = json.loads(z.read(prefix+'secret_scan.json'))
            check((scan.get('status') == 'pass' or scan.get('passed') is True) and not scan.get('findings'),
                  f'{archive_name} archived secret scan')


def verify_followup_audits() -> None:
    d = ROOT/'derived'/'followups'
    summary = json.loads((d/'v12_v12_1_followup_summary.json').read_text())
    v12 = summary['v12']; v121 = summary['v12_1']
    check(v12['comparison_valid'] is False and v12['total_generations'] == 2502 and
          v12['call_classifications']['success'] == 495 and
          v12['call_classifications']['provider_http_503'] == 1602 and
          v12['call_classifications']['provider_read_timeout'] == 282 and
          v12['call_classifications']['schema_echo_selected_by_parser'] == 120 and
          v12['call_classifications']['unterminated_json'] == 3 and
          v12['provider_transport_failures'] == 1884,
          'v12 provider-transport and parser-failure audit')
    check(v12['completed_arms'] == 11 and v12['declared_arms'] == 50,
          'v12 incomplete-arm audit')
    check(abs(v12['diagonal_candidate_q_condition'] - 1.253265804605223) < 1e-12,
          'v12 exact diagonal candidate audit')
    check(v121['comparison_valid'] is False and v121['successful_generations'] == 1036 and
          v121['total_generations'] == 1051 and v121['transport_failures'] == 12 and
          v121['schema_or_parse_failures'] == 3,
          'v12.1 transport audit')
    check(v121['predictions_supplied'] == 569 and v121['solver_records'] == 572,
          'v12.1 prediction coverage')
    check(v121['completed_arms'] == 42 and v121['declared_arms'] == 50 and
          v121['arm_distinct_normalized_programs'] == 612 and
          abs(v121['unique_normalized_program_rate_per_raw_generation'] - 612/1051) < 1e-15 and
          v121['duplicates'] == 424 and v121['schedule_mismatches'] == 20,
          'v12.1 completion, diversity, duplicate, and schedule audit')
    fac = pd.read_csv(d/'v12_1_factorial_summary.csv').set_index('archive_condition')
    expected = {'cold': (120,15), 'diagnostic_only': (120,16),
                'archive_only': (107,42), 'full_feedback': (114,38)}
    for condition,(calls,passes) in expected.items():
        check(int(fac.loc[condition,'solver_calls']) == calls and int(fac.loc[condition,'hard_passes']) == passes,
              f'v12.1 2x2 count: {condition}')
    sensitivity = pd.read_csv(d/'v12_1_missing_as_failure_sensitivity.csv').set_index('archive_condition')
    sensitivity_expected = {
        'cold': (15, 120, 0.125),
        'diagnostic_only': (16, 120, 16/120),
        'archive_only': (42, 120, 0.35),
        'full_feedback': (38, 120, 38/120),
        'two_stage': (33, 120, 0.275),
    }
    for condition, (passes, budget, rate) in sensitivity_expected.items():
        check(int(sensitivity.loc[condition,'hard_passes']) == passes and
              int(sensitivity.loc[condition,'full_budget']) == budget and
              abs(float(sensitivity.loc[condition,'missing_as_failure_rate']) - rate) < 1e-15,
              f'v12.1 missing-as-failure sensitivity: {condition}')
    fisher = pd.read_csv(d/'v12_1_missing_as_failure_fisher.csv').set_index('comparison')
    check(abs(float(fisher.loc['archive_only_vs_cold','two_sided_fisher_p']) - 6.383029099324621e-05) < 1e-15 and
          abs(float(fisher.loc['diagnostic_only_vs_cold','two_sided_fisher_p']) - 1.0) < 1e-15 and
          abs(float(fisher.loc['full_feedback_vs_archive_only','two_sided_fisher_p']) - 0.6813606274604465) < 1e-15,
          'v12.1 least-favourable Fisher sensitivity')
    health = pd.read_csv(d/'v12_1_generation_health.csv').iloc[0]
    check(int(health['raw_generations']) == 1051 and int(health['schema_valid_generations']) == 1036 and
          int(health['arm_distinct_normalized_programs']) == 612 and
          int(health['duplicate_successful_generations']) == 424,
          'v12.1 transport-versus-diversity health audit')
    stages = pd.read_csv(d/'v12_1_two_stage_summary.csv').set_index('stage_in_force')
    check(int(stages.loc['cold','solver_calls']) == 60 and int(stages.loc['cold','hard_passes']) == 10 and
          int(stages.loc['full_feedback','solver_calls']) == 51 and int(stages.loc['full_feedback','hard_passes']) == 23,
          'v12.1 two-stage transition')
    strat = pd.read_csv(d/'v12_1_completion_stratified_rates.csv')
    def _strat(condition: str, completed: bool) -> pd.Series:
        row = strat[(strat.archive_condition == condition) & (strat.completed.astype(str).str.lower() == str(completed).lower())]
        check(len(row) == 1, f'v12.1 completion stratum present: {condition}/{completed}')
        return row.iloc[0]
    ar_incomplete = _strat('archive_only', False); ar_complete = _strat('archive_only', True)
    ff_incomplete = _strat('full_feedback', False); ff_complete = _strat('full_feedback', True)
    ts_incomplete = _strat('two_stage', False); ts_complete = _strat('two_stage', True)
    check((int(ar_incomplete.hard_passes), int(ar_incomplete.solver_calls), int(ar_complete.hard_passes), int(ar_complete.solver_calls)) == (7,23,35,84) and
          (int(ff_incomplete.hard_passes), int(ff_incomplete.solver_calls), int(ff_complete.hard_passes), int(ff_complete.solver_calls)) == (1,6,37,108) and
          (int(ts_incomplete.hard_passes), int(ts_incomplete.solver_calls), int(ts_complete.hard_passes), int(ts_complete.solver_calls)) == (18,39,15,72),
          'v12.1 completion-stratified outcome audit')
    ts_strat = pd.read_csv(d/'v12_1_two_stage_completion_stratified.csv')
    lookup_ts = {(str(r.completed).lower() == 'true', r.stage_in_force): (int(r.hard_passes), int(r.solver_calls)) for _, r in ts_strat.iterrows()}
    check(lookup_ts == {(False,'cold'):(6,24), (False,'full_feedback'):(12,15),
                        (True,'cold'):(4,36), (True,'full_feedback'):(11,36)},
          'v12.1 two-stage selective-completion audit')
    check(abs(v121['cold_exact_q_condition'] - 1.1991499046784042) < 1e-12,
          'v12.1 exact cold candidate audit')
    gap = pd.read_csv(d/'v12_1_gate_standard_gap.csv').set_index('strategy')
    check(abs(float(gap.loc['expert_prior','self_declared_minus_external']) - 2/3) < 1e-12 and
          abs(float(gap.loc['uniform_random','self_declared_minus_external']) - 0.0552631578947368) < 1e-12 and
          abs(float(gap.loc['surrogate','self_declared_minus_external']) - 0.0441326530612244) < 1e-12,
          'v12.1 self-declared versus external gate-gap audit')
    for cert in (ROOT/'derived'/'followup_exact_certificates').glob('*.json'):
        check(json.loads(cert.read_text()).get('certificate_pass') is True,
              f'follow-up exact certificate pass: {cert.name}')


def verify_claim_counts() -> None:
    rates=pd.read_csv(ROOT/'derived'/'common_external_hit_rates.csv').set_index('strategy')
    expected={
        'llm_full_metrics':(120,66),
        'llm_illumination':(120,64),
        'heuristic':(240,120),
        'llm_structure_only':(120,32),
        'surrogate':(240,57),
        'llm_no_archive':(120,20),
        'uniform_random':(240,32),
    }
    for key,(calls,passes) in expected.items():
        check(int(rates.loc[key,'solver_calls'])==calls, f'{key} solver calls')
        check(int(rates.loc[key,'external_passes'])==passes, f'{key} external passes')
    check(int(rates.solver_calls.sum())==1200, '1,200 total solver calls')

    exact=pd.read_csv(ROOT/'derived'/'exact_top_candidate_per_condition.csv')
    check(set(exact.archive_condition)=={'no_archive','structure_only','full_metrics','illumination'}, 'one exact candidate per LLM condition')
    for p in (ROOT/'derived'/'exact_certificates').glob('*.json'):
        check(json.loads(p.read_text()).get('certificate_pass') is True, f'exact certificate pass: {p.name}')


def verify_reviewer_audits() -> None:
    containment = pd.read_csv(ROOT/'derived'/'endpoint_containment.csv')
    lookup = {(bool(r.notebook_hard_pass), bool(r.external_pass)): int(r.programs) for _, r in containment.iterrows()}
    check(lookup == {(False, False): 809, (False, True): 142, (True, False): 0, (True, True): 249},
          'endpoint containment audit')

    by = pd.read_csv(ROOT/'derived'/'endpoint_by_strategy.csv').set_index('strategy')
    check(int(by.loc['uniform_random','notebook_hard_passes']) == 5 and int(by.loc['uniform_random','external_passes']) == 32,
          'uniform-random endpoint reconciliation')
    check(int(by.loc['llm_full_metrics','notebook_hard_passes']) == 60 and int(by.loc['llm_full_metrics','external_passes']) == 66,
          'full-metrics endpoint reconciliation')

    ref = pd.read_csv(ROOT/'derived'/'refinement_effect_audit.csv')
    ext = ref[ref.endpoint == 'external_pass'].set_index('refined')
    hard = ref[ref.endpoint == 'notebook_hard_pass'].set_index('refined')
    check(int(ext.loc[True,'passes']) == 20 and int(ext.loc[True,'eligible_calls']) == 42 and
          int(ext.loc[False,'passes']) == 25 and int(ext.loc[False,'eligible_calls']) == 55,
          'external refinement audit counts')
    check(abs(float(ext.loc[True,'two_sided_fisher_p']) - 0.8404378429863986) < 1e-12,
          'external refinement Fisher p')
    check(int(hard.loc[True,'passes']) == 16 and int(hard.loc[False,'passes']) == 20 and
          abs(float(hard.loc[True,'two_sided_fisher_p']) - 1.0) < 1e-12,
          'notebook-gate refinement audit')

    inf = pd.read_csv(ROOT/'derived'/'infeasibility_structure_audit.csv').set_index('binding_group')
    check(int(inf.loc['extended_gauss','programs']) == 637 and
          int(inf.loc['gradient_boundary_moments','programs']) == 1 and
          int(inf.loc['__group_diagnosed_total__','programs']) == 638,
          'infeasibility binding-group audit')

    expert = pd.read_csv(ROOT/'derived'/'expert_prior_seed_audit.csv')
    check(expert.sequence_sha256.nunique() == 10, 'ten distinct expert-prior sequences')
    check((expert.external_passes == 12).all() and (expert.solver_calls == 24).all(),
          'constant 12/24 expert-prior external yield')

    rates = pd.read_csv(ROOT/'derived'/'extended_convergence_rates.csv')
    tail = rates[(rates.archive_condition == 'reference') & (rates.mesh_window == '160-320-640')]
    check(len(tail) == 1 and bool(tail.iloc[0].roundoff_limited) and not bool(tail.iloc[0].rate_interpretable),
          'reference late convergence marked round-off limited')



def verify_downstream_analysis() -> None:
    d = ROOT/'derived'/'downstream_analysis_v3'
    headline = pd.read_csv(d/'headline_downstream_metrics.csv').set_index('role')
    cand = headline.loc['leading_exact_candidate']
    ref = headline.loc['order6_reference_native_quadrature']
    check(float(cand['h2_max_relative_q_energy_rate']) < 0, 'exact candidate is Q-contractive')
    check(abs(float(ref['h2_max_relative_q_energy_rate']) - 0.32800963478116085) < 1e-10,
          'order-six native-Q relative energy rate')
    check(abs(float(ref['max_q_energy_amplification_tau_0_to_0p6']) - 1.065559) < 2e-5 and
          abs(float(ref['tau_of_max_amplification']) - 0.333) < 0.003,
          'order-six transient Q-energy amplification')
    check(abs(float(cand['weighted_symmetry_residual'])) < 1e-12 and
          abs(float(ref['weighted_symmetry_residual']) - 0.522351240707882) < 1e-10,
          'weighted-symmetry residual contrast')
    check(abs(float(cand['rk4_dt_over_h2']) - float(ref['rk4_dt_over_h2'])) < 1e-5 and
          abs(float(cand['rk4_dt_over_h2']) - 0.451694) < 1e-5,
          'common RK4 stability limit')
    check((ROOT/'derived'/'downstream_analysis_v3_notebook'/'README.md').exists() and
          'superseded and must not be cited' in (ROOT/'derived'/'downstream_analysis_v3_notebook'/'README.md').read_text().lower() and
          (ROOT/'source_artifacts'/'SUPERSEDED_ENERGY_INTERPRETATION.md').exists(),
          'exploratory energy outputs are explicitly marked superseded')
    novelty = json.loads((d/'partial_novelty_gate.json').read_text())
    check(novelty['library_complete'] is False and novelty['novelty_claim_supported'] is False,
          'partial novelty screen does not overclaim')
    check(novelty.get('screen_version') == 'v3.2_topology_scoped_partial' and
          novelty.get('all_fingerprint_distances_finite') is True and
          novelty.get('family_status', {}).get('corbino_castillo') == 'compared' and
          novelty.get('required_same_topology_families_outstanding') == ['castillo_grone_extensions', 'generalized_sbp_block_norm'] and
          novelty.get('cross_topology_families_requiring_mapping') == ['strand', 'mattsson_nordstrom'],
          'topology-scoped novelty screen is finite and remains claim-blocking')
    fp = pd.read_csv(d/'novelty_fingerprint_distances.csv')
    blocks = pd.read_csv(d/'novelty_block_comparisons.csv')
    check(len(fp) > 0 and np.isfinite(fp['fingerprint_distance']).all(),
          'all novelty fingerprint distances are finite')
    check(len(blocks) > 0 and not blocks['match'].astype(bool).any(),
          'no direct match among loaded novelty references')
    same_order_blocks = blocks[blocks['target_order'] == blocks['library_target_order']]
    check(len(same_order_blocks) > 0 and
          abs(float(same_order_blocks['block_distance'].min()) - 0.6079964839325207) < 1e-12 and
          not bool(same_order_blocks.loc[same_order_blocks['block_distance'].idxmin(), 'same_block_shape']),
          'quantified same-order loaded-library separation')
    source = ROOT/'source_artifacts'/'mimetic_analysis_v3.zip'
    check(source.exists() and hashlib.sha256(source.read_bytes()).hexdigest() == '1bbde0f78ec4c7bb9c7c5b5f46a971d2644dd25981dc63bf1ac2e2031f0a05ed',
          'amended downstream analysis source artifact preserved')





def verify_solver_consequences() -> None:
    d = ROOT/'derived'/'solver_consequences_v2'
    report = json.loads((d/'solver_experiment_report.json').read_text())
    check(report.get('analysis') == 'solver_consequences_v2' and
          report.get('operators') == 11 and report.get('primary_exact') == 4 and
          report.get('followup_exact') == 3 and report.get('references') == 4,
          'solver-consequence operator inventory')
    check(report.get('primary_cg_applicable') == 4 and
          report.get('followup_cg_applicable') == 3 and
          report.get('released_exact') == 7 and
          report.get('released_exact_cg_applicable') == 7 and
          report.get('reference_cg_applicable_native_quadrature') == 0,
          'CG availability follows certified weighted symmetry')
    p_lo, p_hi = report['four_primary_symmetry_residual_range']
    a_lo, a_hi = report['all_released_exact_symmetry_residual_range']
    check(float(p_lo) < 2e-16 and float(p_hi) < 2e-16 and
          float(a_lo) < 2e-16 and float(a_hi) < 2e-16,
          'explicitly scoped exact-operator weighted-symmetry residuals')
    k6 = report['order6_reference']
    check(abs(float(k6['symmetry_residual']) - 0.522351240707882) < 1e-12 and
          abs(float(k6['min_eigenvalue_symmetric_part']) + 26.000484784797088) < 1e-9,
          'order-six reference weighted-symmetry obstruction')
    check(abs(float(k6['diagnostic_cg_solution_error']) - 0.27836556195491635) < 1e-10 and
          abs(float(k6['gmres_solution_error']) - 1.0147343054966979e-09) < 2e-11 and
          abs(float(k6['direct_solution_error']) - 1.002510282683709e-09) < 2e-11,
          'order-six diagnostic CG and original-system accuracy')
    check(float(report['primary_diagnostic_solution_error_max']) < 6e-6,
          'exact-candidate symmetric-part diagnostic remains at discretization level')
    check(report.get('primary_backward_euler_cg_applicable') == 4 and
          report.get('reference_backward_euler_cg_applicable_native_quadrature') == 0,
          'backward-Euler weighted-system availability')
    tables = d/'tables'
    check(all((tables/name).exists() for name in [
        'symmetric_system_availability.csv', 'poisson_solver_comparison.csv',
        'implicit_heat_step.csv']), 'authoritative solver tables present')
    availability = pd.read_csv(tables/'symmetric_system_availability.csv')
    refs = availability[availability.family == 'reference']
    exact = availability[availability.family.isin(['primary_exact','followup_exact'])]
    check(len(refs) == 4 and not refs.cg_applicable.astype(bool).any() and
          len(exact) == 7 and exact.cg_applicable.astype(bool).all(),
          'solver availability table reconciles with report')
    heat = pd.read_csv(tables/'implicit_heat_step.csv')
    k8_heat = heat[heat.operator.str.contains('reference_mole_k8')].iloc[0]
    check(not bool(k8_heat['symmetric_part_is_spd']) and not bool(k8_heat['cg_applicable']),
          'order-eight reference backward-Euler symmetric part is not SPD')
    check((d/'figures'/'solver_consequences.png').exists() and
          (ROOT/'docs'/'SOLVER_CONSEQUENCES_ANALYSIS.md').exists(),
          'solver figure and interpretation document present')
    source = ROOT/'source_artifacts'/'mimetic_solver_v2.zip'
    notebook = ROOT/'notebooks'/'mimetic_solver_consequences_v2_user.ipynb'
    archive = ROOT/'runs'/'mimetic_solver_v2_user_results.zip'
    check(source.exists() and digest(source) == '191c2d3342c12ed0edd992067adf5e2ed7a13d88db96f8c90b6a717bd71c39d8',
          'user-supplied solver analysis source artifact preserved')
    check(notebook.exists() and digest(notebook) == '821de30a829d2844005d1aaef825b59f3164d67321b860ebdc847df7a4e2c80f',
          'user solver notebook preserved')
    check(archive.exists() and digest(archive) == 'd2c22374dcacfde7b5d0a826ad23373137034f82efcf7219477fc7f2c8b97cc9',
          'user solver result archive preserved')
    with zipfile.ZipFile(source) as zf:
        check(zf.testzip() is None, 'user solver source ZIP CRC integrity')
    with zipfile.ZipFile(archive) as zf:
        check(zf.testzip() is None, 'user solver result ZIP CRC integrity')

    comparison = pd.read_csv(d/'user_authoritative_comparison.csv')
    check(np.isfinite(comparison['absolute_difference']).all() and
          float(comparison[comparison.quantity == 'weighted_symmetry_residual']['absolute_difference'].max()) < 2e-15 and
          float(comparison[comparison.quantity == 'diagnostic_cg_solution_error']['absolute_difference'].max()) < 1e-9,
          'user and authoritative solver outputs agree on claim-bearing values')



def verify_reference_attribution() -> None:
    d = ROOT/'derived'/'reference_attribution_audit'
    provenance = json.loads((d/'mole_reference_attribution.json').read_text())
    check(provenance.get('audit_version') == 'mole_reference_attribution_v2' and
          provenance.get('corrected_reference_label') == 'MOLE/Corbino-Castillo' and
          provenance.get('all_reference_blocks_match_upstream_source') is True and
          provenance.get('all_compiled_candidates_satisfy_proposition_conditions') is True,
          'MOLE source attribution and candidate proposition-condition audit')
    src = pd.read_csv(d/'mole_reference_source_match.csv')
    check(set(src['order']) == {2,4,6,8} and src['source_match_pass'].astype(bool).all() and
          float(src[['D_left_block_max_abs_error','G_left_block_max_abs_error']].to_numpy().max()) < 1e-14,
          'archived reference blocks match pinned MOLE v1.2.0 source')
    diag = pd.read_csv(d/'mole_boundary_operator_diagnostics.csv').set_index('order')
    check(int(diag.loc[6,'nonreal_eigenvalues']) == 4 and int(diag.loc[8,'nonreal_eigenvalues']) == 4 and
          not bool(diag.loc[6,'endpoint_supported_identity_holds']) and
          not bool(diag.loc[8,'endpoint_supported_identity_holds']) and
          float(diag.loc[6,'interior_boundary_term_relative_norm']) > 1.0,
          'Corbino-Castillo complex modes coexist with a non-vanishing closure boundary term')
    cand = pd.read_csv(d/'compiled_candidate_identity_diagnostics.csv')
    check(len(cand) == 4 and cand['proposition_conditions_pass'].astype(bool).all() and
          float(cand['endpoint_identity_relative_residual'].max()) < 1e-12 and
          float(cand['scalar_norm_dirichlet_separation_residual'].max()) < 1e-12 and
          float(cand['interior_boundary_term_relative_residual'].max()) < 1e-12,
          'promoted candidates satisfy corrected Dirichlet-symmetry proposition conditions')
    source_dir = ROOT/'source_artifacts'/'mole_v1.2.0_matlab_octave'
    check(all((source_dir/name).exists() for name in ['divNonPeriodic.m','gradNonPeriodic.m','weightsP.m','weightsQ.m','README_upstream.md','UPSTREAM.md']),
          'pinned MOLE source snapshot present')
    check((ROOT/'docs'/'MOLE_REFERENCE_ATTRIBUTION_AND_BOUNDARY_OPERATOR_CORRECTION.md').exists() and
          (ROOT/'notebooks'/'REFERENCE_ATTRIBUTION_NOTE.md').exists(),
          'reference-attribution correction documented')
    current_tables = [
        ROOT/'derived'/'extended_exact_candidate_validation.csv',
        ROOT/'derived'/'extended_convergence_rates.csv',
        ROOT/'derived'/'perturbation_trials.csv',
        ROOT/'derived'/'perturbation_summary.csv',
    ]
    check(all('MOLE-CG' not in q.read_text(encoding='utf-8') and 'MOLE-CC' in q.read_text(encoding='utf-8')
              for q in current_tables),
          'regenerated derived tables use corrected MOLE/Corbino-Castillo labels')


def secret_scan() -> None:
    patterns=[
        re.compile(rb'(?i)(?:api[_-]?key|access[_-]?token|secret)\s*[:=]\s*["\'][A-Za-z0-9_\-]{20,}["\']'),
        re.compile(rb'Bearer\s+[A-Za-z0-9_\-\.]{25,}'),
        re.compile(rb'\bsk-[A-Za-z0-9]{20,}\b'),
    ]
    findings=[]
    allowed={'.pdf','.png','.npz','.zip','.ipynb'}
    for p in ROOT.rglob('*'):
        if not p.is_file() or p.name=='MANIFEST.sha256' or p.suffix.lower() in allowed: continue
        data=p.read_bytes()
        for pat in patterns:
            if pat.search(data): findings.append(str(p.relative_to(ROOT)))
    check(not findings, f'no credential-shaped secrets ({findings})')


def main() -> None:
    verify_nested_run()
    verify_followup_runs()
    verify_claim_counts()
    verify_reviewer_audits()
    verify_followup_audits()
    verify_downstream_analysis()
    verify_solver_consequences()
    verify_reference_attribution()
    secret_scan()
    verify_package_manifest()
    print('\nRELEASE AUDIT: PASS')

if __name__=='__main__':
    main()
