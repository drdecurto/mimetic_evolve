# v12 and v12.1 Follow-up Audit

## Scope

The v11 campaign remains the primary inferential experiment. This audit asks which parts of the later v12 and v12.1 runs remain usable. Mathematical artifacts are assessed separately from search-policy comparisons: an exact coefficient certificate can remain valid even when a campaign-level ablation fails its completion or pairing gate.

## v12

- The run-level LLM comparison is **not valid** (`comparison_valid = false`): only 11 of 50 arms exhausted the unique-program budget.
- Of 2502 raw generations, 495 succeeded. The failures comprise 1602 HTTP 503 responses and 282 provider read timeouts (1884 provider-transport failures in total), 120 schema echoes selected by the left-to-right parser, and 3 unterminated JSON objects. These counts should not be described as empty model responses.
- The capability probe excluded a model under the same schema-echo signature. This is a parser/harness limitation, not evidence of a model capability limitation.
- The run nevertheless produced an exactly certified altered order-six **diagonal-norm** closure (`prog_k6_diagonal_asymmetric_hybrid_5e80ffe4c774`) with certified $\kappa_Q=1.253266$ and $\rho(L)h^2=6.165951$. Because its closure differs from the fixed Castillo--Grone closure, it computationally reinforces that the high-order obstruction is closure-specific rather than a prohibition on all order-six diagonal norms. It is not used as search-policy evidence.

## v12.1

- Transport and parsing were largely repaired: 1036/1051 raw generations reached a schema-valid normalized output (98.6%). After deduplication within each condition--seed arm, however, only 612/1051 raw generations represented distinct programs (58.2%); 424 successful generations repeated an already used program.
- Prediction fields were supplied for 569/572 solver records (99.5%).
- The nominal $2\times2$ archive/diagnostic follow-up is descriptively useful, but its comparison is **not valid**: 8 of 50 arms starved, the paired schedule check found 20 mismatches, and a circuit breaker left most accepted calls to one model.
- A least-favourable completion sensitivity treats every unfilled solver call as a failure. It yields archive-only 35.0%, full feedback 31.7%, diagnostic only 13.3%, and cold 12.5%. Archive only still exceeds cold (two-sided Fisher $p=6.4e-05$), diagnostic only is indistinguishable from cold ($p=1.00$), and adding diagnostics to the archive is not significant ($p=0.68$). This sensitivity preserves the qualitative archive/no-archive separation, but it does not repair schedule mismatches or single-model dominance.
- The two-stage phase contrast is especially vulnerable to selective completion: four of ten arms truncate during the feedback phase, and the truncated arms have higher observed yield than the complete arms. The apparent cold-to-feedback increase is therefore descriptive and cannot serve as an internal causal estimate.
- The follow-up produced an exactly certified cold-LLM order-six block-norm candidate (`prog_k6_block_psd_asymmetric_min_next_moment_8a3f6d67a915`) with the series-low certified $\kappa_Q=1.199150$, $\rho(L)h^2=6.266968$, and a reported late-window mixed-PDE rate of 5.372. Its mathematics is usable; its run of origin is not valid evidence that one search condition is superior.

## Consequence for the analysis

The primary v11 hit-rate, AUC, and exact-candidate claims are unchanged. The v12.1 $2\times2$ remains a mechanism-generating follow-up. The article may report the conservative missing-as-failure sensitivity because it preserves the archive/no-archive pattern under the least favourable completion assumption; it must also state that the two-stage phase comparison is confounded by selective truncation. The v12/v12.1 rates do not replace the primary v11 statistics.
