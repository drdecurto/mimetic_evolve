#!/usr/bin/env python3
"""Compare a regenerated postprocessing directory with the archived derivation."""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

KEY_CSVS = [
    "common_external_hit_rates.csv",
    "common_external_auc.csv",
    "actual_llm_costs.csv",
    "exact_top_candidate_per_condition.csv",
    "extended_convergence_rates.csv",
    "perturbation_summary.csv",
    "schedule_pairing_audit.csv",
    "endpoint_containment.csv",
    "endpoint_by_strategy.csv",
    "refinement_effect_audit.csv",
    "infeasibility_structure_audit.csv",
    "expert_prior_seed_audit.csv",
]


def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("candidate", type=Path)
    p.add_argument("--reference", type=Path, default=Path(__file__).resolve().parents[1]/"derived")
    p.add_argument("--rtol", type=float, default=5e-7)
    p.add_argument("--atol", type=float, default=5e-10)
    return p.parse_args()


def compare_frame(a: pd.DataFrame, b: pd.DataFrame, rtol: float, atol: float) -> list[str]:
    issues=[]
    if list(a.columns)!=list(b.columns):
        return [f"column mismatch: {list(a.columns)} != {list(b.columns)}"]
    if len(a)!=len(b): issues.append(f"row count {len(a)} != {len(b)}")
    n=min(len(a),len(b))
    for c in a.columns:
        sa=a[c].iloc[:n]; sb=b[c].iloc[:n]
        na=pd.to_numeric(sa,errors='coerce'); nb=pd.to_numeric(sb,errors='coerce')
        numeric=(na.notna()|nb.notna()).all()
        if numeric:
            mask=~(na.isna()&nb.isna())
            if not np.allclose(na[mask],nb[mask],rtol=rtol,atol=atol,equal_nan=True):
                issues.append(f"numeric mismatch in {c}; max abs={np.nanmax(np.abs(na[mask]-nb[mask]))}")
        else:
            xa=sa.fillna('<NA>').astype(str).tolist(); xb=sb.fillna('<NA>').astype(str).tolist()
            if xa!=xb: issues.append(f"text mismatch in {c}")
    return issues


def main():
    args=parse_args(); failed=False
    for name in KEY_CSVS:
        p=args.candidate/name; q=args.reference/name
        if not p.exists() or not q.exists():
            print(f"MISSING {name}: candidate={p.exists()} reference={q.exists()}"); failed=True; continue
        issues=compare_frame(pd.read_csv(p),pd.read_csv(q),args.rtol,args.atol)
        if issues:
            print(f"FAIL {name}: " + "; ".join(issues)); failed=True
        else:
            print(f"PASS {name}")
    raise SystemExit(1 if failed else 0)

if __name__=='__main__': main()
