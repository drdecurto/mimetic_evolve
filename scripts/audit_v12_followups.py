#!/usr/bin/env python3
"""Recompute the v12/v12.1 follow-up audit from immutable run artifacts.

The script keeps mathematical artifacts separate from campaign-level search-policy
claims.  It performs no model calls and does not rerun the numerical search.
"""
from __future__ import annotations

import argparse
import json
import tempfile
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd
from scipy.stats import fisher_exact


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
    return rows


def resolve_results_root(
    path: Path,
    expected_name: str,
    temp_roots: list[tempfile.TemporaryDirectory],
) -> Path:
    """Return an extracted result directory from a directory or ZIP archive."""
    if path.is_dir():
        direct = path / expected_name
        if direct.is_dir():
            return direct
        if path.name == expected_name:
            return path
        matches = [p for p in path.rglob(expected_name) if p.is_dir()]
        if len(matches) == 1:
            return matches[0]
        raise FileNotFoundError(f"Could not locate {expected_name} below {path}")

    if path.suffix.lower() != ".zip":
        raise ValueError(f"Expected a results directory or ZIP, got {path}")
    tmp = tempfile.TemporaryDirectory(prefix=f"audit_{expected_name}_")
    temp_roots.append(tmp)
    with zipfile.ZipFile(path) as archive:
        archive.extractall(tmp.name)
    base = Path(tmp.name)
    candidates = [p for p in base.rglob(expected_name) if p.is_dir()]
    if len(candidates) != 1:
        raise FileNotFoundError(f"Expected one {expected_name} in {path}, found {len(candidates)}")
    return candidates[0]


def normalize_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.map(lambda value: str(value).strip().lower() in {"true", "1", "yes"})


def classify_v12_call(row: dict[str, Any]) -> str:
    """Classify v12 failures by their actual source rather than empty payload shape."""
    if bool(row.get("ok")):
        return "success"

    error = str(row.get("error") or "")
    parsed = row.get("parsed")

    if "503 Service Unavailable" in error:
        return "provider_http_503"
    if "ReadTimeout" in error or "read operation timed out" in error.lower():
        return "provider_read_timeout"
    if isinstance(parsed, dict) and parsed.get("type") == "object" and "properties" in parsed:
        return "schema_echo_selected_by_parser"
    if "KeyError: 'target_order'" in error:
        # In this run every such row contains the echoed request schema in `parsed`.
        return "schema_echo_selected_by_parser"
    if "unterminated JSON object" in error:
        return "unterminated_json"
    return "other_failure"


def audit_v12(root: Path, out_dir: Path) -> dict[str, Any]:
    calls = load_jsonl(root / "open_program" / "llm" / "open_program_calls.jsonl")
    classifications = Counter(classify_v12_call(row) for row in calls)

    model_rows: list[dict[str, Any]] = []
    for model_id in sorted({str(row.get("model_id")) for row in calls}):
        subset = [row for row in calls if str(row.get("model_id")) == model_id]
        counts = Counter(classify_v12_call(row) for row in subset)
        model_rows.append({"model_id": model_id, "generations": len(subset), **counts})
    pd.DataFrame(model_rows).fillna(0).to_csv(out_dir / "v12_harness_call_audit.csv", index=False)

    capability = load_json(root / "llm" / "model_capabilities.json")
    capability_rows: list[dict[str, Any]] = []
    for model_id, result in capability.items():
        attempts = result.get("attempts") or []
        schema_echo_attempts = sum(
            "probe JSON was {'type': 'object'" in str(attempt.get("error", ""))
            for attempt in attempts
        )
        capability_rows.append({
            "model_id": model_id,
            "usable": bool(result.get("usable")),
            "mode": result.get("mode"),
            "latency_s": result.get("latency_s"),
            "attempt_count": len(attempts),
            "schema_echo_attempts": schema_echo_attempts,
            "first_error": (attempts[0].get("error") if attempts else ""),
        })
    pd.DataFrame(capability_rows).to_csv(out_dir / "v12_capability_probe_audit.csv", index=False)

    validity = load_json(root / "tables" / "open_llm_archive_ablation_validity.json")
    status = pd.read_csv(root / "tables" / "open_llm_archive_ablation_status.csv")
    status["completed"] = normalize_bool(status["completed"])
    status.to_csv(out_dir / "v12_arm_completion.csv", index=False)

    promoted = pd.read_csv(root / "tables" / "open_promoted_exact_candidates.csv")
    promoted.to_csv(out_dir / "v12_exact_candidates.csv", index=False)
    diagonal = promoted[promoted["norm_class"].eq("diagonal")]

    provider_transport_failures = (
        classifications.get("provider_http_503", 0)
        + classifications.get("provider_read_timeout", 0)
    )
    summary = {
        "run": "v12",
        "comparison_valid": bool(validity.get("comparison_valid")),
        "paired_model_role_schedule": bool(validity.get("paired_model_role_schedule")),
        "total_generations": len(calls),
        "call_classifications": dict(classifications),
        "provider_transport_failures": int(provider_transport_failures),
        "completed_arms": int(status["completed"].sum()),
        "declared_arms": int(len(status)),
        "exact_promoted_candidates": int(len(promoted)),
        "exact_diagonal_candidates": int(len(diagonal)),
        "diagonal_candidate_program_id": (str(diagonal.iloc[0]["program_id"]) if len(diagonal) else None),
        "diagonal_candidate_q_condition": (float(diagonal.iloc[0]["q_condition_bound"]) if len(diagonal) else None),
        "diagonal_candidate_scaled_spectral_radius": (float(diagonal.iloc[0]["scaled_spectral_radius"]) if len(diagonal) else None),
        "diagonal_candidate_asymptotic_rate": (float(diagonal.iloc[0]["mixed_pde_rate_asymptotic"]) if len(diagonal) else None),
    }
    return summary


def audit_v121(root: Path, out_dir: Path) -> dict[str, Any]:
    calls = load_jsonl(root / "open_program" / "llm" / "open_program_calls.jsonl")
    results = pd.read_csv(root / "tables" / "open_llm_archive_ablation_results.csv")
    status = pd.read_csv(root / "tables" / "open_llm_archive_ablation_status.csv")
    status["completed"] = normalize_bool(status["completed"])
    validity = load_json(root / "tables" / "open_llm_archive_ablation_validity.json")

    transport_rows: list[dict[str, Any]] = []
    by_model: dict[str, Counter] = defaultdict(Counter)
    for row in calls:
        model_id = str(row.get("model_id"))
        if bool(row.get("ok")):
            outcome = "success"
        elif bool(row.get("transport_failure")):
            outcome = "transport_failure"
        else:
            outcome = "schema_or_parse_failure"
        by_model[model_id][outcome] += 1
    for model_id, counts in sorted(by_model.items()):
        total = sum(counts.values())
        transport_rows.append({
            "model_id": model_id,
            "generations": total,
            "successful_generations": counts["success"],
            "transport_failures": counts["transport_failure"],
            "schema_or_parse_failures": counts["schema_or_parse_failure"],
            "success_rate": counts["success"] / total if total else float("nan"),
        })
    pd.DataFrame(transport_rows).to_csv(out_dir / "v12_1_transport_model_audit.csv", index=False)

    condition_summary = results.groupby("archive_condition", sort=False).agg(
        solver_calls=("program_id", "size"),
        hard_passes=("hard_pass_all", "sum"),
        pass_rate=("hard_pass_all", "mean"),
        predictions_supplied=("predicted_hard_pass", lambda series: int(series.notna().sum())),
        best_utility=("utility", "max"),
    ).reset_index()
    condition_summary.to_csv(out_dir / "v12_1_factorial_summary.csv", index=False)

    two_stage = results[results["archive_condition"].eq("two_stage")].groupby(
        "stage_in_force", sort=False
    ).agg(
        solver_calls=("program_id", "size"),
        hard_passes=("hard_pass_all", "sum"),
        pass_rate=("hard_pass_all", "mean"),
    ).reset_index()
    two_stage.to_csv(out_dir / "v12_1_two_stage_summary.csv", index=False)

    status.to_csv(out_dir / "v12_1_arm_completion.csv", index=False)
    completion = status.groupby("condition", sort=False).agg(
        completed_arms=("completed", "sum"),
        declared_arms=("completed", "size"),
        solver_calls=("solver_calls", "sum"),
        generations=("generations", "sum"),
        budget=("budget", "first"),
    ).reset_index()
    completion["full_budget"] = completion["declared_arms"] * completion["budget"]
    completion["missing_solver_calls"] = completion["full_budget"] - completion["solver_calls"]
    completion.to_csv(out_dir / "v12_1_completion_summary.csv", index=False)

    # Duplicate counts are based on every schema-valid normalized generation, not only solver records.
    valid_rows = [row for row in calls if bool(row.get("ok")) and row.get("normalized_program_id")]
    valid_df = pd.DataFrame({
        "condition": [row.get("archive_condition") for row in valid_rows],
        "seed": [row.get("seed") for row in valid_rows],
        "program_id": [row.get("normalized_program_id") for row in valid_rows],
        "model_id": [row.get("model_id") for row in valid_rows],
        "role": [row.get("role") for row in valid_rows],
    })
    duplicate_groups = valid_df.groupby(
        ["condition", "seed", "program_id"], dropna=False
    ).size().reset_index(name="generation_count")
    duplicate_groups.sort_values("generation_count", ascending=False).to_csv(
        out_dir / "v12_1_duplicate_groups.csv", index=False
    )
    duplicate_summary = valid_df.groupby("condition", sort=False).size().rename(
        "valid_generations"
    ).to_frame()
    duplicate_summary = duplicate_summary.join(
        duplicate_groups.groupby("condition").size().rename("unique_programs")
    )
    duplicate_summary["duplicates"] = (
        duplicate_summary["valid_generations"] - duplicate_summary["unique_programs"]
    )
    duplicate_summary["duplicate_rate"] = (
        duplicate_summary["duplicates"] / duplicate_summary["valid_generations"]
    )
    duplicate_summary.reset_index().to_csv(out_dir / "v12_1_duplicate_summary.csv", index=False)

    total_success = sum(bool(row.get("ok")) for row in calls)
    transport_failures = sum(bool(row.get("transport_failure")) for row in calls)
    other_failures = len(calls) - total_success - transport_failures
    arm_distinct_programs = int(len(duplicate_groups))
    generation_health = pd.DataFrame([{
        "raw_generations": len(calls),
        "schema_valid_generations": total_success,
        "schema_valid_rate": total_success / len(calls),
        "arm_distinct_normalized_programs": arm_distinct_programs,
        "arm_distinct_rate_per_raw_generation": arm_distinct_programs / len(calls),
        "duplicate_successful_generations": len(valid_df) - arm_distinct_programs,
        "duplicate_rate_among_successful": (len(valid_df) - arm_distinct_programs) / len(valid_df),
        "transport_failures": transport_failures,
        "schema_or_parse_failures": other_failures,
    }])
    generation_health.to_csv(out_dir / "v12_1_generation_health.csv", index=False)

    # Least-favourable completion sensitivity: every unfilled solver call is a failure.
    full_budget = completion[["condition", "full_budget", "missing_solver_calls"]].rename(
        columns={"condition": "archive_condition"}
    )
    worst_case = condition_summary.merge(full_budget, on="archive_condition", how="left")
    worst_case["missing_as_failure_rate"] = worst_case["hard_passes"] / worst_case["full_budget"]
    worst_case.to_csv(out_dir / "v12_1_missing_as_failure_sensitivity.csv", index=False)

    wc = worst_case.set_index("archive_condition")
    fisher_specs = [
        ("archive_only_vs_cold", "archive_only", "cold"),
        ("diagnostic_only_vs_cold", "diagnostic_only", "cold"),
        ("full_feedback_vs_archive_only", "full_feedback", "archive_only"),
        ("full_feedback_vs_cold", "full_feedback", "cold"),
        ("two_stage_vs_cold", "two_stage", "cold"),
    ]
    fisher_rows: list[dict[str, Any]] = []
    for label, arm_a, arm_b in fisher_specs:
        pa = int(wc.loc[arm_a, "hard_passes"])
        na = int(wc.loc[arm_a, "full_budget"])
        pb = int(wc.loc[arm_b, "hard_passes"])
        nb = int(wc.loc[arm_b, "full_budget"])
        result = fisher_exact([[pa, na - pa], [pb, nb - pb]], alternative="two-sided")
        fisher_rows.append({
            "comparison": label,
            "arm_a": arm_a,
            "arm_b": arm_b,
            "arm_a_passes": pa,
            "arm_a_full_budget": na,
            "arm_b_passes": pb,
            "arm_b_full_budget": nb,
            "odds_ratio": float(result.statistic),
            "two_sided_fisher_p": float(result.pvalue),
        })
    pd.DataFrame(fisher_rows).to_csv(out_dir / "v12_1_missing_as_failure_fisher.csv", index=False)

    # Completion-stratified outcomes, including the two-stage phase composition.
    merged = results.merge(
        status[["condition", "seed", "completed"]],
        left_on=["archive_condition", "seed"],
        right_on=["condition", "seed"],
        how="left",
        validate="many_to_one",
    )
    completion_stratified = merged.groupby(
        ["archive_condition", "completed"], sort=False
    ).agg(
        solver_calls=("program_id", "size"),
        hard_passes=("hard_pass_all", "sum"),
        pass_rate=("hard_pass_all", "mean"),
    ).reset_index()
    completion_stratified.to_csv(
        out_dir / "v12_1_completion_stratified_rates.csv", index=False
    )
    two_stage_stratified = merged[merged["archive_condition"].eq("two_stage")].groupby(
        ["completed", "stage_in_force"], sort=False
    ).agg(
        solver_calls=("program_id", "size"),
        hard_passes=("hard_pass_all", "sum"),
        pass_rate=("hard_pass_all", "mean"),
    ).reset_index()
    two_stage_stratified.to_csv(
        out_dir / "v12_1_two_stage_completion_stratified.csv", index=False
    )

    schedule_mismatches = validity.get("schedule_mismatches") or []
    schedule_rows = []
    for mismatch in schedule_mismatches:
        assignments = mismatch.get("assignments") or {}
        schedule_rows.append({
            "seed": mismatch.get("seed"),
            "solver_step": mismatch.get("solver_step"),
            "distinct_assignments": len({tuple(value) for value in assignments.values()}),
            "assignments_json": json.dumps(assignments, sort_keys=True),
        })
    pd.DataFrame(schedule_rows).to_csv(out_dir / "v12_1_schedule_mismatches.csv", index=False)

    prediction_summary = condition_summary[[
        "archive_condition", "solver_calls", "predictions_supplied"
    ]].copy()
    prediction_summary["prediction_coverage"] = (
        prediction_summary["predictions_supplied"] / prediction_summary["solver_calls"]
    )
    prediction_summary.to_csv(out_dir / "v12_1_prediction_coverage.csv", index=False)

    promoted = pd.read_csv(root / "tables" / "open_promoted_exact_candidates.csv")
    promoted.to_csv(out_dir / "v12_1_exact_candidates.csv", index=False)
    cold_exact = promoted[promoted["source_strategy"].eq("llm_cold")]

    gate_gap = pd.read_csv(root / "tables" / "open_gate_standard_gap.csv")
    gate_gap.to_csv(out_dir / "v12_1_gate_standard_gap.csv", index=False)

    summary = {
        "run": "v12.1",
        "comparison_valid": bool(validity.get("comparison_valid")),
        "paired_model_role_schedule": bool(validity.get("paired_model_role_schedule")),
        "schedule_mismatches": len(schedule_mismatches),
        "total_generations": len(calls),
        "successful_generations": total_success,
        "generation_success_rate": total_success / len(calls),
        "transport_failures": transport_failures,
        "schema_or_parse_failures": other_failures,
        "solver_records": int(len(results)),
        "predictions_supplied": int(results["predicted_hard_pass"].notna().sum()),
        "prediction_coverage": float(results["predicted_hard_pass"].notna().mean()),
        "completed_arms": int(status["completed"].sum()),
        "declared_arms": int(len(status)),
        "incomplete_arms": int((~status["completed"]).sum()),
        "valid_normalized_generations": int(len(valid_df)),
        "arm_distinct_normalized_programs": arm_distinct_programs,
        "unique_normalized_program_rate_per_raw_generation": arm_distinct_programs / len(calls),
        "duplicates": int(len(valid_df) - arm_distinct_programs),
        "cold_exact_program_id": (str(cold_exact.iloc[0]["program_id"]) if len(cold_exact) else None),
        "cold_exact_q_condition": (float(cold_exact.iloc[0]["q_condition_bound"]) if len(cold_exact) else None),
        "cold_exact_scaled_spectral_radius": (float(cold_exact.iloc[0]["scaled_spectral_radius"]) if len(cold_exact) else None),
        "cold_exact_asymptotic_rate": (float(cold_exact.iloc[0]["mixed_pde_rate_asymptotic"]) if len(cold_exact) else None),
        "missing_as_failure_rates": {
            row["archive_condition"]: float(row["missing_as_failure_rate"])
            for _, row in worst_case.iterrows()
        },
        "missing_as_failure_fisher": {
            row["comparison"]: float(row["two_sided_fisher_p"])
            for row in fisher_rows
        },
    }
    return summary


def write_markdown(v12_summary: dict[str, Any], v121_summary: dict[str, Any], out_path: Path) -> None:
    classifications = v12_summary["call_classifications"]
    wc = v121_summary["missing_as_failure_rates"]
    fp = v121_summary["missing_as_failure_fisher"]
    text = f"""# v12 and v12.1 Follow-up Audit

## Scope

The v11 campaign remains the primary inferential experiment. This audit asks which parts of the later v12 and v12.1 runs remain usable. Mathematical artifacts are assessed separately from search-policy comparisons: an exact coefficient certificate can remain valid even when a campaign-level ablation fails its completion or pairing gate.

## v12

- The run-level LLM comparison is **not valid** (`comparison_valid = {str(v12_summary['comparison_valid']).lower()}`): only {v12_summary['completed_arms']} of {v12_summary['declared_arms']} arms exhausted the unique-program budget.
- Of {v12_summary['total_generations']} raw generations, {classifications.get('success', 0)} succeeded. The failures comprise {classifications.get('provider_http_503', 0)} HTTP 503 responses and {classifications.get('provider_read_timeout', 0)} provider read timeouts ({v12_summary['provider_transport_failures']} provider-transport failures in total), {classifications.get('schema_echo_selected_by_parser', 0)} schema echoes selected by the left-to-right parser, and {classifications.get('unterminated_json', 0)} unterminated JSON objects. These counts should not be described as empty model responses.
- The capability probe excluded a model under the same schema-echo signature. This is a parser/harness limitation, not evidence of a model capability limitation.
- The run nevertheless produced an exactly certified altered order-six **diagonal-norm** closure (`{v12_summary['diagonal_candidate_program_id']}`) with certified $\\kappa_Q={v12_summary['diagonal_candidate_q_condition']:.6f}$ and $\\rho(L)h^2={v12_summary['diagonal_candidate_scaled_spectral_radius']:.6f}$. Because its closure differs from the fixed Castillo--Grone closure, it computationally reinforces that the high-order obstruction is closure-specific rather than a prohibition on all order-six diagonal norms. It is not used as search-policy evidence.

## v12.1

- Transport and parsing were largely repaired: {v121_summary['successful_generations']}/{v121_summary['total_generations']} raw generations reached a schema-valid normalized output ({100*v121_summary['generation_success_rate']:.1f}%). After deduplication within each condition--seed arm, however, only {v121_summary['arm_distinct_normalized_programs']}/{v121_summary['total_generations']} raw generations represented distinct programs ({100*v121_summary['unique_normalized_program_rate_per_raw_generation']:.1f}%); {v121_summary['duplicates']} successful generations repeated an already used program.
- Prediction fields were supplied for {v121_summary['predictions_supplied']}/{v121_summary['solver_records']} solver records ({100*v121_summary['prediction_coverage']:.1f}%).
- The nominal $2\\times2$ archive/diagnostic follow-up is descriptively useful, but its comparison is **not valid**: {v121_summary['incomplete_arms']} of {v121_summary['declared_arms']} arms starved, the paired schedule check found {v121_summary['schedule_mismatches']} mismatches, and a circuit breaker left most accepted calls to one model.
- A least-favourable completion sensitivity treats every unfilled solver call as a failure. It yields archive-only {100*wc['archive_only']:.1f}%, full feedback {100*wc['full_feedback']:.1f}%, diagnostic only {100*wc['diagnostic_only']:.1f}%, and cold {100*wc['cold']:.1f}%. Archive only still exceeds cold (two-sided Fisher $p={fp['archive_only_vs_cold']:.2g}$), diagnostic only is indistinguishable from cold ($p={fp['diagnostic_only_vs_cold']:.2f}$), and adding diagnostics to the archive is not significant ($p={fp['full_feedback_vs_archive_only']:.2f}$). This sensitivity preserves the qualitative archive/no-archive separation, but it does not repair schedule mismatches or single-model dominance.
- The two-stage phase contrast is especially vulnerable to selective completion: four of ten arms truncate during the feedback phase, and the truncated arms have higher observed yield than the complete arms. The apparent cold-to-feedback increase is therefore descriptive and cannot serve as an internal causal estimate.
- The follow-up produced an exactly certified cold-LLM order-six block-norm candidate (`{v121_summary['cold_exact_program_id']}`) with the series-low certified $\\kappa_Q={v121_summary['cold_exact_q_condition']:.6f}$, $\\rho(L)h^2={v121_summary['cold_exact_scaled_spectral_radius']:.6f}$, and a reported late-window mixed-PDE rate of {v121_summary['cold_exact_asymptotic_rate']:.3f}. Its mathematics is usable; its run of origin is not valid evidence that one search condition is superior.

## Consequence for the analysis

The primary v11 hit-rate, AUC, and exact-candidate claims are unchanged. The v12.1 $2\\times2$ remains a mechanism-generating follow-up. The article may report the conservative missing-as-failure sensitivity because it preserves the archive/no-archive pattern under the least favourable completion assumption; it must also state that the two-stage phase comparison is confounded by selective truncation. The v12/v12.1 rates do not replace the primary v11 statistics.
"""
    out_path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v12-results", type=Path, required=True)
    parser.add_argument("--v12-1-results", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    temp_roots: list[tempfile.TemporaryDirectory] = []
    try:
        root12 = resolve_results_root(args.v12_results, "mimetic_operator_discovery_results_v12", temp_roots)
        root121 = resolve_results_root(args.v12_1_results, "mimetic_operator_discovery_results_v12_1", temp_roots)
        summary12 = audit_v12(root12, args.output_dir)
        summary121 = audit_v121(root121, args.output_dir)
        payload = {"v12": summary12, "v12_1": summary121}
        (args.output_dir / "v12_v12_1_followup_summary.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
        )
        write_markdown(summary12, summary121, args.output_dir / "V12_V12_1_FOLLOWUP_AUDIT.md")
        print(json.dumps(payload, indent=2, sort_keys=True))
    finally:
        for tmp in temp_roots:
            tmp.cleanup()


if __name__ == "__main__":
    main()
