# Audit of the amended downstream and novelty analysis

## Source

- `source_artifacts/mimetic_analysis_v3.zip`
- SHA-256: `1bbde0f78ec4c7bb9c7c5b5f46a971d2644dd25981dc63bf1ac2e2031f0a05ed`
- 20 notebook cells, 12 code cells, no stored execution errors.

## What changed relative to the supplied v2 analysis

1. Boundary-row and support-profile metadata are parsed consistently whether stored as numbers, sequences, or strings such as `(10, 10, 10, 10)`.
2. Corner singular-value fingerprints are padded to a fixed length, eliminating undefined comparisons when closure widths differ.
3. Family coverage is recorded explicitly, with templates for coefficient entries and documentary non-comparability statements.

## What is usable

The metadata and fixed-length fingerprint corrections are valid and are incorporated into the authoritative downstream script. They make all 119 exploratory fingerprint comparisons finite and remove a silent `7 x 3` corner-window error affecting two paper candidates. In the supplied exploratory table, componentwise division by padded zeros makes some finite distances as large as `9.34e11`; the authoritative implementation instead uses symmetric block-level normalization, yielding finite distances on a bounded `[0,1]` scale. The supplied `energy_growth_bounds.csv`, `energy_histories.csv`, `time_step_limits.csv`, and `solver_conditioning.csv` are byte-identical to the preceding exploratory package, so the amendment adds no new downstream numerical result. The original exploratory energy tables are preserved only for provenance and are explicitly marked as superseded; the corrected authoritative outputs are under `derived/downstream_analysis_v3/`.

## What is not promoted to a analysis result

The amended analysis loads the MOLE reference arrays, now correctly attributed to Corbino--Castillo. The authoritative interpretation is topology-scoped: parameterized or compact higher-order Castillo--Grone extensions and generalized/block-norm staggered families remain direct-comparison targets, whereas classical Strand and Mattsson--Nordstroem nodal SBP families require an explicit degree-of-freedom map before coefficient equivalence is meaningful. The screen therefore does not establish literature-level novelty or add a new numerical headline.

The supplied notebook allowed a free-form `not applicable` declaration to close a required-family gate. The authoritative repository uses a more conservative rule: such a declaration records scope but the family remains outstanding unless a topology-aware comparison or a mathematically justified exclusion is supplied.

## analysis consequence

Only the description of the partial novelty screen is sharpened. The energy, time-step, exact-certificate, search-yield, and candidate-comparison claims are unchanged.
