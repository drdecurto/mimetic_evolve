# Audit of the Additional Comments and the v12/v12.1 Follow-Ups

## Decision

The additional comments are correct and improve the reporting. The primary v11 results and mathematical conclusions are unchanged. The article now adds four clarifications:

1. a least-favourable missing-as-failure sensitivity for the incomplete v12.1 factorial;
2. an explicit caveat that the two-stage phase contrast is confounded by selective truncation;
3. a corrected partition of v12 failures into provider transport, parser schema echoes, and malformed JSON;
4. simultaneous reporting of v12.1 transport health and unique-program yield.

v11 remains the primary inferential experiment. v12.1 remains a mechanism-generating follow-up because completion, model-role pairing, and model-roster conditions failed.

## 1. Least-favourable attrition sensitivity

The observed v12.1 factorial counts are:

| Condition | Passes / observed calls | Observed rate |
|---|---:|---:|
| Cold | 15/120 | 12.5% |
| Diagnostic only | 16/120 | 13.3% |
| Archive only | 42/107 | 39.3% |
| Full feedback | 38/114 | 33.3% |

Because archive-bearing arms lost solver calls to duplicate collapse, a conservative sensitivity treats every unfilled call as a failure. On the full 120-call denominators:

| Condition | Passes / full budget | Missing-as-failure rate |
|---|---:|---:|
| Cold | 15/120 | 12.5% |
| Diagnostic only | 16/120 | 13.3% |
| Archive only | 42/120 | 35.0% |
| Full feedback | 38/120 | 31.7% |
| Two stage | 33/120 | 27.5% |

Two-sided Fisher exact tests on these conservative tables give:

- archive only versus cold: `p = 6.383029e-05`;
- diagnostic only versus cold: `p = 1.000`;
- full feedback versus archive only: `p = 0.681361`;
- full feedback versus cold: `p = 0.000536837`.

Thus the broad archive/no-archive separation survives the least-favourable completion assumption. This is stronger than an unsigned-bias caveat, but it does not make the factorial confirmatory: the model-role schedule is mismatched and most accepted calls come from one surviving model.

Completion-stratified observed rates also show that incomplete archive-bearing arms are weaker than complete arms:

- archive only: `7/23 = 30.4%` incomplete versus `35/84 = 41.7%` complete;
- full feedback: `1/6 = 16.7%` incomplete versus `37/108 = 34.3%` complete.

These descriptive strata are consistent with duplicate collapse degrading an arm before starvation, but the missing-as-failure analysis remains the cleaner conservative bound.

## 2. Two-stage phase contrast

The aggregate two-stage transition is:

- cold phase: `10/60 = 16.7%`;
- feedback phase: `23/51 = 45.1%`.

Four of ten two-stage arms truncate during the feedback phase. Their overall observed yield is `18/39 = 46.2%`, compared with `15/72 = 20.8%` for complete arms. By phase:

| Completion status | Cold | Feedback |
|---|---:|---:|
| Truncated arms | 6/24 = 25.0% | 12/15 = 80.0% |
| Complete arms | 4/36 = 11.1% | 11/36 = 30.6% |

The phase contrast therefore mixes the intervention with selective completion. It cannot serve as an internal causal estimate of the archive effect and is retained only as descriptive corroboration.

## 3. Correct v12 failure partition

The previous audit incorrectly called provider failures “empty responses.” The raw v12 log contains exactly:

- successful generations: 495;
- HTTP 503 Service Unavailable: 1,602;
- provider read timeouts: 282;
- schema echoes selected by the left-to-right JSON parser: 120;
- unterminated JSON objects: 3.

The first two failure categories are **1,884 provider transport failures**, not model refusals or empty model outputs. The parser-selected schema echoes are a harness defect. The corrected categories sum to all 2,502 raw generations.

The v12 campaign remains invalid for a search-policy comparison, but its exactly certified altered order-six diagonal-norm candidate remains a valid mathematical artifact.

## 4. v12.1 transport health versus diversity

The v12.1 run achieved strong transport and parse health:

- `1036/1051 = 98.6%` of raw generations produced a schema-valid normalized program;
- 12 transport failures and 3 other parse/schema failures remained;
- predictions were supplied for `569/572` solver records.

However, deduplication within each condition--seed arm leaves only:

- `612/1051 = 58.2%` arm-distinct normalized programs;
- 424 successful duplicate generations;
- a duplicate rate of 40.9% among schema-valid generations.

Both figures must be reported together. Transport is no longer the principal bottleneck; proposal diversity is.

## 5. analysis and repository changes

The article now:

- reports observed and missing-as-failure rates in the v12.1 table;
- gives the conservative Fisher comparisons while retaining v11 as primary;
- explicitly states that the two-stage contrast is confounded by selective truncation;
- describes v12 failures as provider transport failures, parser-selected schema echoes, and malformed JSON;
- reports `98.6%` schema-valid transport/parse success alongside `58.2%` arm-distinct program yield.

The repository adds the following recomputed audit outputs:

- `v12_1_generation_health.csv`;
- `v12_1_missing_as_failure_sensitivity.csv`;
- `v12_1_missing_as_failure_fisher.csv`;
- `v12_1_completion_stratified_rates.csv`;
- `v12_1_two_stage_completion_stratified.csv`.

The standalone `audit_v12_followups.py` script now regenerates these files and classifies v12 failures from the recorded error strings rather than from an empty payload heuristic.
