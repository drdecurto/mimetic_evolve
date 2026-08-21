PYTHON ?= python3
DERIVED ?= derived
FOLLOWUP_DERIVED ?= derived/followups_recomputed
WORK ?= work
RESULTS_ROOT := $(WORK)/mimetic_operator_discovery_results_v11
NOTEBOOK := notebooks/mimetic_operator_discovery_v11.ipynb

.PHONY: all extract postprocess postprocess-quick compare-derived audit-followups \
        reference-audit downstream-analysis solver-analysis verify clean

all: postprocess verify

extract:
	rm -rf "$(WORK)"
	mkdir -p "$(WORK)"
	unzip -q runs/v11_original_results.zip -d "$(WORK)"

postprocess: extract
	$(PYTHON) scripts/postprocess_v11.py --results-root "$(RESULTS_ROOT)" --notebook "$(NOTEBOOK)" --output "$(DERIVED)"

postprocess-quick: extract
	$(PYTHON) scripts/postprocess_v11.py --results-root "$(RESULTS_ROOT)" --notebook "$(NOTEBOOK)" --output "$(DERIVED)" --quick

compare-derived:
	$(PYTHON) scripts/compare_derived.py "$(DERIVED)" --reference derived

audit-followups:
	rm -rf "$(FOLLOWUP_DERIVED)"
	$(PYTHON) scripts/audit_v12_followups.py --v12-results runs/v12_failed_results.zip --v12-1-results runs/v12_1_followup_results.zip --output-dir "$(FOLLOWUP_DERIVED)"

reference-audit:
	$(PYTHON) scripts/audit_mole_reference_attribution.py --repo-root .

downstream-analysis:
	$(PYTHON) scripts/analyze_downstream_v3.py

solver-analysis:
	$(PYTHON) scripts/analyze_solver_consequences_v2.py --root .

verify:
	$(PYTHON) scripts/verify_release.py

clean:
	rm -rf "$(WORK)" derived_reproduced derived_quick derived/followups_recomputed
