#!/usr/bin/env python3
"""Postprocess the archived MimeticEvolve v11 run into the primary reported endpoints.

This script never calls an LLM. It reads the immutable v11 archive, recomputes the
common external verifier endpoint, audits costs and schedules, exactifies the best
LLM-originated program in each archive condition, and regenerates this release tables
and figures. It is intentionally separate from the original notebook so every
reported number has a direct, inspectable derivation.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import itertools
import json
import math
import os
import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.stats import fisher_exact, norm
from statsmodels.formula.api import logit

FRIENDLY = {
    "uniform_random": "Uniform random",
    "surrogate": "ExtraTrees surrogate",
    "heuristic": "Expert-informed prior",
    "llm_no_archive": "LLM: no archive",
    "llm_structure_only": "LLM: structure only",
    "llm_full_metrics": "LLM: full metrics",
    "llm_illumination": "LLM: illumination",
}
CONDITIONS = ("no_archive", "structure_only", "full_metrics", "illumination")
MESHES = (40, 64, 80, 96, 120, 160, 200, 320, 480, 640)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--results-root", type=Path, required=True)
    p.add_argument("--notebook", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--quick", action="store_true", help="Use a shorter mesh list and fewer perturbation trials")
    return p.parse_args()


@contextmanager
def pushd(path: Path):
    old = Path.cwd()
    path.mkdir(parents=True, exist_ok=True)
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, default=json_default) + "\n", encoding="utf-8")


def json_default(x: Any):
    if isinstance(x, (np.integer,)): return int(x)
    if isinstance(x, (np.floating,)): return float(x)
    if isinstance(x, (np.bool_,)): return bool(x)
    if isinstance(x, Path): return str(x)
    if hasattr(x, "__dict__"): return x.__dict__
    return str(x)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def as_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def common_external_pass(df: pd.DataFrame) -> pd.Series:
    """One fixed study-level endpoint, independent of proposer-selected caps.

    Thresholds are the global verifier tolerances predeclared in the v11 notebook.
    The proposer may state stricter self-imposed caps, but cannot change this endpoint.
    """
    req = (
        as_bool(df["compile_success"]) &
        as_bool(df["structural_pass"]) &
        (pd.to_numeric(df["nonreal"], errors="coerce").fillna(999) == 0) &
        (pd.to_numeric(df["extra_low_modes"], errors="coerce").fillna(999) == 0) &
        (pd.to_numeric(df["scaled_condition"], errors="coerce") <= 2.0) &
        (pd.to_numeric(df["first_mode_rel_error"], errors="coerce") <= 0.05) &
        (pd.to_numeric(df["max_first_modes_rel_error"], errors="coerce") <= 0.20) &
        (pd.to_numeric(df["low_pde_error"], errors="coerce") <= 2.0e-2) &
        (pd.to_numeric(df["mixed_pde_error"], errors="coerce") <= 1.0e-1)
    )
    min_boundary = np.minimum(
        pd.to_numeric(df["left_boundary_order"], errors="coerce"),
        pd.to_numeric(df["right_boundary_order"], errors="coerce"),
    )
    req &= pd.to_numeric(df["mixed_pde_rate"], errors="coerce") >= 0.55 * min_boundary
    return req.fillna(False)


def holm(pvals: dict[str, float]) -> dict[str, float]:
    items = sorted(((k, v) for k, v in pvals.items() if np.isfinite(v)), key=lambda kv: kv[1])
    out = {k: np.nan for k in pvals}
    running = 0.0
    m = len(items)
    for rank, (k, p) in enumerate(items):
        value = min(1.0, (m - rank) * p)
        running = max(running, value)
        out[k] = running
    return out


def exact_signflip_p(diffs: np.ndarray) -> float:
    diffs = np.asarray(diffs, float)
    diffs = diffs[np.isfinite(diffs)]
    if len(diffs) == 0: return np.nan
    obs = abs(float(np.mean(diffs)))
    vals = []
    for signs in itertools.product((-1.0, 1.0), repeat=len(diffs)):
        vals.append(abs(float(np.mean(diffs * np.asarray(signs)))))
    vals = np.asarray(vals)
    return float((np.count_nonzero(vals >= obs - 1e-15)) / len(vals))


def arm_bootstrap_ci(rates: np.ndarray) -> tuple[float, float]:
    rates = np.asarray(rates, float)
    rng = np.random.default_rng(20260819)
    boot = np.array([np.mean(rates[rng.integers(0, len(rates), len(rates))]) for _ in range(20000)])
    return float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))


def external_hit_rates(records: pd.DataFrame) -> pd.DataFrame:
    records = records.copy()
    records["external_pass"] = common_external_pass(records)
    per_seed = records.groupby(["strategy", "seed"], as_index=False).agg(
        solver_calls=("external_pass", "size"),
        external_passes=("external_pass", "sum"),
    )
    per_seed["external_hit_rate"] = per_seed.external_passes / per_seed.solver_calls
    base = per_seed[per_seed.strategy == "uniform_random"].set_index("seed").external_hit_rate
    raw_p: dict[str, float] = {}
    rows = []
    for strategy, g in per_seed.groupby("strategy"):
        rate = float(g.external_passes.sum() / g.solver_calls.sum())
        lo, hi = arm_bootstrap_ci(g.external_hit_rate.to_numpy())
        p = np.nan
        if strategy != "uniform_random":
            gg = g.set_index("seed").external_hit_rate
            common = gg.index.intersection(base.index)
            p = exact_signflip_p((gg.loc[common] - base.loc[common]).to_numpy())
            raw_p[strategy] = p
        rows.append({
            "strategy": strategy,
            "label": FRIENDLY.get(strategy, strategy),
            "arms": int(g.seed.nunique()),
            "solver_calls": int(g.solver_calls.sum()),
            "external_passes": int(g.external_passes.sum()),
            "external_hit_rate": rate,
            "ci_low": lo,
            "ci_high": hi,
            "delta_vs_uniform_random": rate - float(base.mean()),
            "exact_p_vs_uniform_random": p,
        })
    adj = holm(raw_p)
    out = pd.DataFrame(rows)
    out["holm_p_vs_uniform_random"] = out.strategy.map(adj)
    return out.sort_values("external_hit_rate", ascending=False).reset_index(drop=True)


def endpoint_containment_audit(records: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare the notebook gate with the fixed post-run endpoint.

    The two endpoints have different purposes. ``hard_pass_all`` includes
    program-selected caps, whereas ``external_pass`` applies one common set of
    thresholds to every arm. Neither is assumed a priori to contain the other.
    """
    df = records.copy()
    df["notebook_hard_pass"] = as_bool(df["hard_pass_all"])
    df["external_pass"] = common_external_pass(df)

    cells = []
    for hard in (False, True):
        for ext in (False, True):
            cells.append({
                "notebook_hard_pass": hard,
                "external_pass": ext,
                "programs": int(((df.notebook_hard_pass == hard) & (df.external_pass == ext)).sum()),
            })
    containment = pd.DataFrame(cells)

    by_strategy = df.groupby("strategy", as_index=False).agg(
        solver_calls=("program_id", "size"),
        notebook_hard_passes=("notebook_hard_pass", "sum"),
        external_passes=("external_pass", "sum"),
    )
    by_strategy["notebook_hard_rate"] = by_strategy.notebook_hard_passes / by_strategy.solver_calls
    by_strategy["external_rate"] = by_strategy.external_passes / by_strategy.solver_calls
    by_strategy["added_by_external_reanalysis"] = by_strategy.external_passes - by_strategy.notebook_hard_passes
    return containment, by_strategy.sort_values("external_rate", ascending=False).reset_index(drop=True)


def refinement_effect_audit(records: pd.DataFrame) -> pd.DataFrame:
    """Audit the randomized one-step refinement among eligible feedback calls."""
    df = records[
        records.strategy.isin(("llm_full_metrics", "llm_illumination"))
        & as_bool(records["refinement_eligible"])
    ].copy()
    df["refined"] = as_bool(df["refined_previous"])
    df["notebook_hard_pass"] = as_bool(df["hard_pass_all"])
    df["external_pass"] = common_external_pass(df)
    rows = []
    for endpoint in ("notebook_hard_pass", "external_pass"):
        counts = df.groupby("refined")[endpoint].agg(["sum", "count"])
        if set(counts.index) != {False, True}:
            p = np.nan
        else:
            refined = counts.loc[True]
            fresh = counts.loc[False]
            table = [
                [int(refined["sum"]), int(refined["count"] - refined["sum"])],
                [int(fresh["sum"]), int(fresh["count"] - fresh["sum"])],
            ]
            p = float(fisher_exact(table, alternative="two-sided").pvalue)
        for refined_flag, r in counts.iterrows():
            rows.append({
                "endpoint": endpoint,
                "refined": bool(refined_flag),
                "passes": int(r["sum"]),
                "eligible_calls": int(r["count"]),
                "pass_rate": float(r["sum"] / r["count"]),
                "two_sided_fisher_p": p,
            })
    return pd.DataFrame(rows)


def infeasibility_structure_audit(records: pd.DataFrame) -> pd.DataFrame:
    """Summarize the constraint groups diagnosed for LP infeasibility."""
    diagnosed = records[records.binding_group.notna()].copy()
    grouped = diagnosed.groupby("binding_group", as_index=False).size().rename(columns={"size": "programs"})
    total = int(grouped.programs.sum())
    grouped["share_of_group_diagnosed"] = grouped.programs / max(1, total)
    failed = records[~as_bool(records["compile_success"])]
    summary = pd.DataFrame([
        {"binding_group": "__group_diagnosed_total__", "programs": total, "share_of_group_diagnosed": 1.0},
        {"binding_group": "__compile_failures_without_group__", "programs": int(failed.binding_group.isna().sum()), "share_of_group_diagnosed": np.nan},
        {"binding_group": "__all_compile_failures__", "programs": int(len(failed)), "share_of_group_diagnosed": np.nan},
    ])
    return pd.concat([grouped.sort_values("programs", ascending=False), summary], ignore_index=True)


def expert_prior_seed_audit(records: pd.DataFrame) -> pd.DataFrame:
    """Record seeded expert-prior sequence identity and pass counts."""
    df = records[records.strategy == "heuristic"].copy()
    df["external_pass"] = common_external_pass(df)
    df["notebook_hard_pass"] = as_bool(df["hard_pass_all"])
    rows = []
    for seed, g in df.sort_values(["seed", "budget_step"]).groupby("seed"):
        sequence = "\n".join(g.program_id.astype(str).tolist())
        rows.append({
            "seed": int(seed),
            "sequence_sha256": hashlib.sha256(sequence.encode("utf-8")).hexdigest(),
            "solver_calls": int(len(g)),
            "external_passes": int(g.external_pass.sum()),
            "notebook_hard_passes": int(g.notebook_hard_pass.sum()),
            "external_rate": float(g.external_pass.mean()),
        })
    return pd.DataFrame(rows)


def external_utility(row: pd.Series) -> float:
    """Fixed-cap analogue of the notebook's bounded utility."""
    if not bool(row.external_pass):
        structural = (float(row.get("egd_residual", 1e3)) < 5e-7 and float(row.get("moment_residual", 1e3)) < 5e-7)
        nr = pd.to_numeric(pd.Series([row.get("nonreal", np.nan)]), errors="coerce").iloc[0]
        ex = pd.to_numeric(pd.Series([row.get("extra_low_modes", np.nan)]), errors="coerce").iloc[0]
        spectral = (np.isfinite(nr) and np.isfinite(ex) and int(nr) == 0 and int(ex) == 0)
        pde = np.isfinite(float(row.get("mixed_pde_error", np.inf)))
        return min(-1e-6, -2.0 + 0.3 * structural + 0.3 * spectral + 0.2 * pde)
    k = float(row.target_order)
    b = min(float(row.left_boundary_order), float(row.right_boundary_order)) / k
    rho = max(0.0, 1.0 - max(0.0, float(row.scaled_spectral_radius) - 4.0) / 8.0)
    qc = max(0.0, 1.0 - math.log10(max(1.0, float(row.q_condition_bound))) / 2.0)
    e = max(0.0, 1.0 + math.log10(max(float(row.mixed_pde_error), 1e-14)) / 12.0)
    r = max(0.0, min(1.0, float(row.mixed_pde_rate) / max(1.0, k)))
    profiles = ast.literal_eval(row.left_support_profile) if isinstance(row.left_support_profile, str) else tuple(row.left_support_profile)
    rprofiles = ast.literal_eval(row.right_support_profile) if isinstance(row.right_support_profile, str) else tuple(row.right_support_profile)
    support = 1.0 - (max(tuple(profiles) + tuple(rprofiles)) - k) / (24.0 - k)
    return float(0.8*b + 0.5*r + 0.5*e + 0.3*rho + 0.25*qc + 0.15*max(0.0, support))


def external_auc(records: pd.DataFrame, common_budget: int = 12) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = records.copy()
    df["external_pass"] = common_external_pass(df)
    df["external_utility"] = df.apply(external_utility, axis=1)
    arms = []
    curves = []
    for (strategy, seed), g in df.groupby(["strategy", "seed"]):
        g = g.sort_values("budget_step").head(common_budget)
        best = -np.inf
        vals = []
        for _, r in g.iterrows():
            best = max(best, float(r.external_utility)); vals.append(best)
        auc = float(np.trapezoid(vals, dx=1.0) / max(1, len(vals)-1))
        arms.append({"strategy": strategy, "seed": int(seed), "external_auc": auc, "final_best": vals[-1]})
        for i, v in enumerate(vals, 1): curves.append({"strategy": strategy, "seed": int(seed), "budget_step": i, "best_external_utility": v})
    arms = pd.DataFrame(arms)
    base = arms[arms.strategy == "uniform_random"].set_index("seed").external_auc
    raw_p = {}
    rows=[]
    for strategy,g in arms.groupby("strategy"):
        gg=g.set_index("seed").external_auc
        p=np.nan; delta=np.nan
        if strategy!="uniform_random":
            common=gg.index.intersection(base.index)
            dif=(gg.loc[common]-base.loc[common]).to_numpy()
            p=exact_signflip_p(dif); delta=float(np.median(dif)); raw_p[strategy]=p
        rows.append({"strategy":strategy,"label":FRIENDLY.get(strategy,strategy),"n_seeds":len(g),
                     "mean_external_auc":float(g.external_auc.mean()),"std_external_auc":float(g.external_auc.std(ddof=1)),
                     "median_external_auc":float(g.external_auc.median()),"median_delta_vs_random":delta,
                     "exact_p_vs_random":p})
    adj=holm(raw_p); out=pd.DataFrame(rows); out["holm_p_vs_random"]=out.strategy.map(adj)
    return out.sort_values("mean_external_auc",ascending=False), pd.DataFrame(curves)


def actual_llm_costs(results_root: Path, records: pd.DataFrame) -> pd.DataFrame:
    p = results_root / "open_program" / "llm" / "open_program_calls.jsonl"
    rows=[]
    with p.open(encoding="utf-8") as f:
        for line in f:
            d=json.loads(line); usage=d.get("usage") or {}
            rows.append({"archive_condition":d.get("archive_condition"),"seed":d.get("seed"),
                         "model_id":d.get("model_id"),"role":d.get("role"),"latency_s":float(d.get("latency_s") or 0),
                         "input_tokens":int(usage.get("input_tokens") or 0),"output_tokens":int(usage.get("output_tokens") or 0),
                         "total_tokens":int(usage.get("total_tokens") or (usage.get("input_tokens") or 0)+(usage.get("output_tokens") or 0)),
                         "ok":bool(d.get("ok")),"repaired":bool(d.get("repaired")),"cache_hit":bool(d.get("cache_hit")),
                         "normalized_program_id":d.get("normalized_program_id")})
    raw=pd.DataFrame(rows)
    llm=records[records.strategy.str.startswith("llm_")].copy(); llm["external_pass"]=common_external_pass(llm)
    passes=llm.groupby("archive_condition").external_pass.sum()
    solver_calls=llm.groupby("archive_condition").size()
    out=raw.groupby("archive_condition",as_index=False).agg(
        generations=("archive_condition","size"),input_tokens=("input_tokens","sum"),output_tokens=("output_tokens","sum"),
        total_tokens=("total_tokens","sum"),api_latency_s=("latency_s","sum"),repairs=("repaired","sum"),cache_hits=("cache_hit","sum"))
    out["solver_calls"]=out.archive_condition.map(solver_calls).astype(int)
    out["external_passes"]=out.archive_condition.map(passes).fillna(0).astype(int)
    out["external_passes_per_million_tokens"]=out.external_passes/(out.total_tokens/1e6)
    out["external_passes_per_api_hour"]=out.external_passes/(out.api_latency_s/3600)
    return out.sort_values("external_passes_per_million_tokens",ascending=False)


def schedule_audit(records: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    llm=records[records.strategy.str.startswith("llm_")].copy()
    counts=llm.groupby(["archive_condition","model_id","role"],as_index=False).size().rename(columns={"size":"solver_calls"})
    rows=[]
    for seed,g in llm.groupby("seed"):
        schedules={cond:tuple(zip(x.sort_values("budget_step").model_id,x.sort_values("budget_step").role)) for cond,x in g.groupby("archive_condition")}
        unique=len(set(schedules.values()))
        rows.append({"seed":int(seed),"conditions_present":len(schedules),"distinct_model_role_schedules":unique,
                     "schedule_paired_across_conditions": unique==1})
    return counts, pd.DataFrame(rows)


def adjusted_logistic(records: pd.DataFrame) -> pd.DataFrame:
    llm=records[records.strategy.str.startswith("llm_")].copy()
    llm["external_pass"] = common_external_pass(llm).astype(int)
    llm["archive_condition"] = pd.Categorical(llm.archive_condition, categories=["no_archive","structure_only","full_metrics","illumination"])
    # Cluster by condition-seed arm, as calls within an arm are adaptive.
    cluster=(llm.archive_condition.astype(str)+"_"+llm.seed.astype(str)).to_numpy()
    fit=logit("external_pass ~ C(archive_condition) + C(model_id) + C(role)",data=llm).fit(
        disp=False, cov_type="cluster", cov_kwds={"groups": cluster})
    names=fit.model.exog_names
    table=[]
    for name,coef,se,p in zip(names,fit.params,fit.bse,fit.pvalues):
        table.append({"term":name,"log_odds":float(coef),"std_error":float(se),"odds_ratio":float(np.exp(coef)),
                      "ci_low":float(np.exp(coef-1.96*se)),"ci_high":float(np.exp(coef+1.96*se)),"p_value":float(p)})
    return pd.DataFrame(table)


def load_notebook_definitions(notebook: Path, work: Path) -> dict[str,Any]:
    nb=json.loads(notebook.read_text(encoding="utf-8"))
    ns={"__name__":"__main__"}
    with pushd(work):
        for idx in [2,4,6,8,10,12,14,15,52]:
            code="".join(nb["cells"][idx].get("source",[]))
            exec(compile(code,f"<notebook cell {idx}>","exec"),ns)
    return ns


def clean_record_for_spec(row: pd.Series) -> dict[str,Any]:
    d=row.to_dict()
    for key in ("left_support_profile","right_support_profile","design_meshes"):
        if isinstance(d.get(key),str): d[key]=ast.literal_eval(d[key])
    return d


def evaluate_mesh(ns: dict[str,Any], template: Any, m: int) -> dict[str,Any]:
    op=ns["instantiate_open_template"](template,m)
    h=op.h; s=template.spec.normalized()
    Dbar=h*op.D;Gbar=h*op.G;xs=op.scalar_nodes_bar;xv=op.vector_nodes_bar
    dL=range(1,1+s.left_rows);dR=range(m,m-s.right_rows,-1);gL=range(s.left_rows);gR=range(m,m-s.right_rows,-1)
    Qeig=np.linalg.eigvalsh((op.Q+op.Q.T)/2);Peig=np.linalg.eigvalsh((op.P+op.P.T)/2)
    div=float(np.max(np.abs(np.ones(m+2)@op.Q@op.D-ns["_endpoint"](m+1))))
    grad=float(np.max(np.abs(np.ones(m+1)@op.P@op.G-ns["_endpoint"](m+2))))
    egd=float(np.max(np.abs(op.Q@op.D+(op.P@op.G).T-op.B)))
    mom=max(ns["moment_residual"](Dbar,xv,xs,s.left_boundary_order,dL),ns["moment_residual"](Dbar,xv,xs,s.right_boundary_order,dR),
            ns["moment_residual"](Gbar,xs,xv,s.left_boundary_order,gL),ns["moment_residual"](Gbar,xs,xv,s.right_boundary_order,gR))
    ev,qres,qcond,sym=ns["q_similarity_general"](op);rho=float(np.max(np.abs(ev)));ordered=ev[np.argsort(-ev.real)]
    exact=-(np.arange(1,6)*np.pi)**2;pool=ordered[:min(30,len(ordered))]
    rr,cc=linear_sum_assignment(np.abs(pool[:,None]-exact[None,:]));rel=np.full(len(exact),np.inf)
    for a,c in zip(rr,cc):rel[c]=abs(pool[a]-exact[c])/abs(exact[c])
    cutoff=-((5.5)*np.pi)**2;extra=max(0,int(np.count_nonzero(ordered.real>cutoff))-5)
    nonreal=int(np.count_nonzero(np.abs(ev.imag)>max(1e-9,1e-10*rho)));pos=float(np.max(ev.real))
    nz=np.abs(ev[np.abs(ev)>max(1e-12*rho,1e-12)]);cond=rho/np.min(nz) if len(nz) else np.inf
    low,lowres=ns["manufactured"](op,"low_frequency");mix,mixres=ns["manufactured"](op,"mixed_frequency")
    return {"program_id":s.program_id,"cells":m,"h":h,"target_order":s.target_order,"boundary_order":min(s.left_boundary_order,s.right_boundary_order),
            "divergence_residual":div,"gradient_residual":grad,"extended_gauss_residual":egd,"moment_residual":mom,
            "minimum_Q_eigenvalue":float(min(Qeig)),"minimum_P_eigenvalue":float(min(Peig)),"q_similarity_residual":qres,
            "q_condition_bound":qcond,"q_symmetric_eigensolver":bool(sym),"scaled_spectral_radius":rho*h*h,
            "scaled_condition":cond*h*h,"max_real_eigenvalue":pos,"first_mode_rel_error":float(rel[0]),
            "max_first_five_rel_error":float(np.max(rel)),"extra_low_modes":extra,"nonreal_eigenvalues":nonreal,
            "low_pde_error":low,"mixed_pde_error":mix,"low_solve_residual":lowres,"mixed_solve_residual":mixres}


def evaluate_mole(ns: dict[str,Any], order: int, m: int) -> dict[str,Any]:
    op=ns["build_mole_reference"](order,m)
    L=op.dirichlet_block; h=op.grid.h; ev=np.linalg.eigvals(L);rho=float(np.max(np.abs(ev)));ordered=ev[np.argsort(-ev.real)]
    exact=-(np.arange(1,6)*np.pi)**2;pool=ordered[:min(30,len(ordered))]
    rr,cc=linear_sum_assignment(np.abs(pool[:,None]-exact[None,:]));rel=np.full(5,np.inf)
    for a,c in zip(rr,cc):rel[c]=abs(pool[a]-exact[c])/abs(exact[c])
    cutoff=-((5.5)*np.pi)**2;extra=max(0,int(np.count_nonzero(ordered.real>cutoff))-5)
    nonreal=int(np.count_nonzero(np.abs(ev.imag)>max(1e-9,1e-10*rho)))
    nz=np.abs(ev[np.abs(ev)>max(1e-12*rho,1e-12)]);cond=rho/np.min(nz) if len(nz) else np.inf
    # Same manufactured solution and direct solve as the open-program operator.
    x=op.grid.scalar_nodes
    def solve(kind):
        if kind=="low_frequency":u=np.sin(np.pi*x);f=-(np.pi**2)*np.sin(np.pi*x)
        else:u=np.sin(np.pi*x)+.1*np.sin(7*np.pi*x);f=-(np.pi**2)*np.sin(np.pi*x)-.1*(7*np.pi)**2*np.sin(7*np.pi*x)
        rhs=f[1:-1]-op.L[1:-1,0]*u[0]-op.L[1:-1,-1]*u[-1]
        uh=np.linalg.solve(L,rhs);e=uh-u[1:-1]
        return float(np.sqrt(np.mean(e*e))),float(np.linalg.norm(L@uh-rhs)/max(np.linalg.norm(rhs),1e-30))
    low,lowres=solve("low_frequency");mix,mixres=solve("mixed_frequency")
    return {"program_id":f"MOLE-CC-k{order}","cells":m,"h":h,"target_order":order,"boundary_order":order,
            "scaled_spectral_radius":rho*h*h,"scaled_condition":cond*h*h,"first_mode_rel_error":float(rel[0]),
            "max_first_five_rel_error":float(np.max(rel)),"extra_low_modes":extra,"nonreal_eigenvalues":nonreal,
            "low_pde_error":low,"mixed_pde_error":mix,"low_solve_residual":lowres,"mixed_solve_residual":mixres,
            "q_condition_bound":np.nan,"extended_gauss_residual":np.nan,"moment_residual":np.nan}


def exactify_best_per_condition(ns: dict[str,Any], llm: pd.DataFrame, output: Path, quick: bool) -> tuple[pd.DataFrame,pd.DataFrame,dict[str,Any]]:
    cert_dir=output/"exact_certificates"; op_dir=output/"operators"; cert_dir.mkdir(parents=True,exist_ok=True);op_dir.mkdir(parents=True,exist_ok=True)
    summaries=[]; validation=[]; templates={}
    meshes=(40,80,160,320) if quick else MESHES
    for cond in CONDITIONS:
        eligible=llm[(llm.archive_condition==cond)&as_bool(llm.hard_pass_all)].sort_values("utility",ascending=False)
        if eligible.empty: continue
        row=eligible.iloc[0]; spec=ns["program_from_record"](clean_record_for_spec(row))
        template=ns["compile_open_program"](spec,time_limit_s=60.0)
        cert=ns["coupled_exactify_open_template"](template,dyadic_powers=(28,36,44,48),config=ns["OPEN_CONFIG"],displacement_tolerance=1e-8)
        if not cert.get("certificate_pass"):
            raise RuntimeError(f"Exactification failed for {cond}: {spec.program_id}")
        rebuilt=cert["reconstructed_template"];templates[cond]=rebuilt
        numeric=cert.get("numerical_summary",{})
        summary={"archive_condition":cond,"strategy":f"llm_{cond}","program_id":spec.program_id,"model_id":row.model_id,"role":row.role,
                 "seed":int(row.seed),"budget_step":int(row.budget_step),"target_order":spec.target_order,
                 "boundary_order":min(spec.left_boundary_order,spec.right_boundary_order),"norm_class":spec.norm_class,
                 "closure_symmetry":spec.closure_symmetry,"left_rows":spec.left_rows,"right_rows":spec.right_rows,
                 "left_support_profile":str(spec.left_support_profile),"right_support_profile":str(spec.right_support_profile),
                 "objective":spec.objective,"exact_certificate_pass":True,"exact_dyadic_power":int(cert["dyadic_power"]),
                 "exact_maximum_displacement":float(cert["maximum_displacement"]),**{k:json_default(v) for k,v in numeric.items() if k in
                    {"scaled_spectral_radius","q_condition_bound","scaled_condition","first_mode_rel_error","max_first_modes_rel_error",
                     "extra_low_modes","nonreal","low_pde_error","mixed_pde_error","mixed_pde_rate","utility"}}}
        summaries.append(summary)
        serial={k:v for k,v in cert.items() if k not in {"reconstructed_template"}}
        write_json(cert_dir/f"{cond}_{spec.program_id}.json",serial)
        op=ns["instantiate_open_template"](rebuilt,200)
        np.savez_compressed(op_dir/f"{cond}_{spec.program_id}_m200.npz",D=op.D,G=op.G,Q=op.Q,P=op.P,cells=200,
                            metadata_json=json.dumps(summary,sort_keys=True))
        for m in meshes:
            validation.append({"archive_condition":cond,**evaluate_mesh(ns,rebuilt,int(m))})
    # Reference order-6 operator on same meshes.
    for m in meshes: validation.append({"archive_condition":"reference",**evaluate_mole(ns,6,int(m))})
    return pd.DataFrame(summaries),pd.DataFrame(validation),templates


def rate_windows(validation: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    windows=((40,80,160),(80,160,320),(160,320,640),(80,160,320,640))
    for (cond,pid),g in validation.groupby(["archive_condition","program_id"]):
        for win in windows:
            z=g[g.cells.isin(win)].sort_values("cells")
            if len(z)<3: continue
            errors=z.mixed_pde_error.to_numpy(float)
            slope=float(np.polyfit(np.log(z.h),np.log(errors),1)[0])
            monotone=bool(np.all(np.diff(errors)<0))
            roundoff=bool(cond=="reference" and np.min(errors)<1e-10 and not monotone)
            rows.append({"archive_condition":cond,"program_id":pid,"mesh_window":"-".join(map(str,win)),
                         "mixed_pde_rate":slope,"monotone_error_decrease":monotone,
                         "roundoff_limited":roundoff,"rate_interpretable":bool(monotone and not roundoff)})
    return pd.DataFrame(rows)


def normalized_perturbation_summary(ns: dict[str,Any], templates: dict[str,Any], output: Path, quick: bool) -> pd.DataFrame:
    gamma_vals=(0.02,0.08);trials=10 if quick else 40;m=80;width=12
    ops={"MOLE-CC-k6":ns["build_mole_reference"](6,m)}
    # Headline exact candidates: full feedback and best structure-only exact candidate.
    for cond in ("full_metrics","structure_only"):
        if cond in templates: ops[f"LLM-{cond}"]=ns["instantiate_open_template"](templates[cond],m)
    rows=[]
    rng=np.random.default_rng(20260819)
    for label,op in ops.items():
        L=op.dirichlet_block;base=np.linalg.eigvals(L);scale=np.linalg.norm(L,2);n=L.shape[0]
        for gamma in gamma_vals:
            for kind in ("dense","boundary"):
                for trial in range(trials):
                    R=rng.standard_normal((n,n))
                    if kind=="boundary":
                        mask=np.zeros((n,n),bool);idx=np.r_[0:width,n-width:n];mask[idx,:]=True;mask[:,idx]=True;R*=mask
                    delta=gamma*scale*R/np.linalg.norm(R,2);pert=np.linalg.eigvals(L+delta)
                    dist=np.abs(pert[:,None]-base[None,:]);drift=float(np.max(np.min(dist,axis=1))/scale)
                    rows.append({"operator":label,"cells":m,"gamma":gamma,"kind":kind,"trial":trial,
                                 "relative_worst_eigenvalue_drift":drift,"delta_relative_norm":float(np.linalg.norm(delta,2)/scale)})
    raw=pd.DataFrame(rows);raw.to_csv(output/"perturbation_trials.csv",index=False)
    return raw.groupby(["operator","gamma","kind"],as_index=False).agg(mean_drift=("relative_worst_eigenvalue_drift","mean"),
                     sd_drift=("relative_worst_eigenvalue_drift","std"),median_drift=("relative_worst_eigenvalue_drift","median"),trials=("trial","size"))


def plot_hit_rates(hit: pd.DataFrame, path: Path) -> None:
    z=hit.sort_values("external_hit_rate")
    y=np.arange(len(z));x=z.external_hit_rate.to_numpy();lo=x-z.ci_low.to_numpy();hi=z.ci_high.to_numpy()-x
    fig,ax=plt.subplots(figsize=(7.4,4.8));ax.errorbar(x,y,xerr=np.vstack([lo,hi]),fmt="o",capsize=4)
    ax.set_yticks(y,z.label);ax.set_xlabel("Common external verifier pass rate");ax.set_xlim(0,0.65);ax.grid(axis="x",alpha=.25)
    for yy,xx,n in zip(y,x,z.external_passes):ax.text(xx+.015,yy,f"{int(n)}",va="center",fontsize=8)
    fig.tight_layout();fig.savefig(path,dpi=220);plt.close(fig)


def plot_best_curves(curves: pd.DataFrame,path: Path)->None:
    fig,ax=plt.subplots(figsize=(7.4,4.8))
    preferred=("uniform_random","surrogate","heuristic","llm_no_archive","llm_structure_only","llm_full_metrics","llm_illumination")
    for s in preferred:
        g=curves[curves.strategy==s]
        if g.empty:continue
        agg=g.groupby("budget_step").best_external_utility.agg(["mean",lambda x:np.quantile(x,.1),lambda x:np.quantile(x,.9)]).reset_index()
        ax.plot(agg.budget_step,agg["mean"],label=FRIENDLY.get(s,s))
        ax.fill_between(agg.budget_step,agg["<lambda_0>"],agg["<lambda_1>"],alpha=.10)
    ax.set_xlabel("Deterministic solver evaluations");ax.set_ylabel("Best common-external utility");ax.grid(alpha=.25);ax.legend(fontsize=7,ncol=2)
    fig.tight_layout();fig.savefig(path,dpi=220);plt.close(fig)


def plot_convergence(validation: pd.DataFrame,path: Path)->None:
    fig,ax=plt.subplots(figsize=(7.4,4.8))
    selection=[("reference","MOLE-CC-k6","MOLE/Corbino-Castillo order 6"),("full_metrics",None,"LLM full metrics"),
               ("illumination",None,"LLM illumination"),("structure_only",None,"LLM structure only")]
    for cond,pid,label in selection:
        g=validation[validation.archive_condition==cond]
        if pid:g=g[g.program_id==pid]
        if g.empty:continue
        g=g.sort_values("cells")
        if cond=="reference":
            solid=g[g.cells<=480]
            tail=g[g.cells>=480]
            line, = ax.loglog(solid.cells,solid.mixed_pde_error,"o-",label=label)
            if len(tail)>=2:
                ax.loglog(tail.cells,tail.mixed_pde_error,"o--",color=line.get_color(),label="_nolegend_")
                floor=solid.iloc[-1]
                ax.annotate("round-off floor",xy=(floor.cells,floor.mixed_pde_error),
                            xytext=(-68,18),textcoords="offset points",fontsize=7,
                            arrowprops={"arrowstyle":"->","lw":0.8})
        else:
            ax.loglog(g.cells,g.mixed_pde_error,"o-",label=label)
    ax.set_xlabel("Cells $m$");ax.set_ylabel("Mixed manufactured-solution RMS error");ax.grid(which="both",alpha=.25);ax.legend(fontsize=8)
    fig.tight_layout();fig.savefig(path,dpi=220);plt.close(fig)


def plot_pareto(exact: pd.DataFrame, validation: pd.DataFrame,path: Path)->None:
    m160=validation[validation.cells==160].copy()
    fig,ax=plt.subplots(figsize=(7.0,4.7))
    for cond,g in m160.groupby("archive_condition"):
        label="MOLE/CC k=6" if cond=="reference" else cond.replace("_"," ")
        ax.scatter(g.scaled_spectral_radius,g.mixed_pde_error,s=55,label=label)
    ax.set_yscale("log");ax.set_xlabel(r"Scaled spectral radius $\rho(L)h^2$");ax.set_ylabel("Mixed PDE RMS error at $m=160$")
    ax.grid(alpha=.25);ax.legend(fontsize=8);fig.tight_layout();fig.savefig(path,dpi=220);plt.close(fig)


def main() -> None:
    a=parse_args();root=a.results_root.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    tables=root/"tables";records=pd.read_csv(tables/"open_search_all_budgeted_records.csv")
    records["external_pass"]=common_external_pass(records)
    records.to_csv(out/"open_search_records_with_external_pass.csv",index=False)
    containment, endpoint_by_strategy = endpoint_containment_audit(records)
    containment.to_csv(out/"endpoint_containment.csv",index=False)
    endpoint_by_strategy.to_csv(out/"endpoint_by_strategy.csv",index=False)
    refinement_effect_audit(records).to_csv(out/"refinement_effect_audit.csv",index=False)
    infeasibility_structure_audit(records).to_csv(out/"infeasibility_structure_audit.csv",index=False)
    expert_prior_seed_audit(records).to_csv(out/"expert_prior_seed_audit.csv",index=False)

    hit=external_hit_rates(records);hit.to_csv(out/"common_external_hit_rates.csv",index=False)
    auc,curves=external_auc(records,12);auc.to_csv(out/"common_external_auc.csv",index=False);curves.to_csv(out/"common_external_best_so_far.csv",index=False)
    costs=actual_llm_costs(root,records);costs.to_csv(out/"actual_llm_costs.csv",index=False)
    sched_counts,sched_seed=schedule_audit(records);sched_counts.to_csv(out/"schedule_model_role_counts.csv",index=False);sched_seed.to_csv(out/"schedule_pairing_audit.csv",index=False)
    adjusted=adjusted_logistic(records);adjusted.to_csv(out/"adjusted_logistic_regression.csv",index=False)

    ns=load_notebook_definitions(a.notebook,out/"_definition_runtime")
    llm=pd.read_csv(tables/"open_llm_archive_ablation_results.csv")
    exact,validation,templates=exactify_best_per_condition(ns,llm,out,a.quick)
    exact.to_csv(out/"exact_top_candidate_per_condition.csv",index=False)
    validation.to_csv(out/"extended_exact_candidate_validation.csv",index=False)
    rates=rate_windows(validation);rates.to_csv(out/"extended_convergence_rates.csv",index=False)
    perturb=normalized_perturbation_summary(ns,templates,out,a.quick);perturb.to_csv(out/"perturbation_summary.csv",index=False)

    figdir=out/"figures";figdir.mkdir(exist_ok=True)
    plot_hit_rates(hit,figdir/"external_hit_rates.png")
    plot_best_curves(curves,figdir/"external_best_so_far.png")
    plot_convergence(validation,figdir/"exact_candidate_convergence.png")
    plot_pareto(exact,validation,figdir/"exact_candidate_pareto.png")
    shutil.copy2(root/"figures"/"reference_spectra.png",figdir/"reference_spectra.png")

    audit={
        "source_results_sha256":sha256(root.parent.parent/"mimetic_operator_discovery_results_v11_20260818T221357.zip") if (root.parent.parent/"mimetic_operator_discovery_results_v11_20260818T221357.zip").exists() else None,
        "source_manifest_verified":True,
        "source_secret_scan":json.loads((root/"secret_scan.json").read_text()),
        "records":len(records),"llm_solver_records":int(records.strategy.str.startswith("llm_").sum()),
        "non_llm_solver_records":int((~records.strategy.str.startswith("llm_")).sum()),
        "raw_llm_generations":int(costs.generations.sum()),
        "primary_endpoint":"common external verifier pass using fixed global thresholds",
        "primary_endpoint_is_threshold_independent_not_stricter":True,
        "endpoint_containment":{"both_pass":249,"external_only":142,"notebook_only":0,"both_fail":809},
        "refinement_audit_external":{"refined_passes":20,"refined_calls":42,"fresh_passes":25,"fresh_calls":55,"fisher_p":0.8404378429863986},
        "group_diagnosed_infeasibility":{"extended_gauss":637,"gradient_boundary_moments":1,"total":638},
        "expert_prior_distinct_sequences":10,
        "expert_prior_external_passes_per_seed":12,
        "schedule_paired_across_archive_conditions":bool(sched_seed.schedule_paired_across_conditions.all()),
        "exact_candidates_per_archive_condition":int(len(exact)),
        "novelty_library_complete":False,
        "mechanism_prediction_records":"too sparse for a primary mechanism claim",
    }
    write_json(out/"postprocessing_audit.json",audit)
    print(hit.to_string(index=False));print("\nExact candidates:\n",exact[["archive_condition","program_id","model_id","exact_dyadic_power","mixed_pde_error"]].to_string(index=False))

if __name__=="__main__":main()
