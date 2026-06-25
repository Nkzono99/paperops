.PHONY: venv smoke cli-smoke scaffold-package-boundary-check lint-bib citation-check mirror-check mirror-freshness-check public-terms-check concept-term-check argument-focus-check figure-reference-check claim-evidence-check paper-layer-card-check workflow-check archive-seal-check submission-drift-check skill-mirror-check links-check research-request-handoff-check external-import-check collect-context template-readiness-check

PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,$(if $(wildcard .venv/Scripts/python.exe),.venv/Scripts/python.exe,python))
PYTHON_BOOTSTRAP ?= python

venv:
	$(PYTHON_BOOTSTRAP) -m venv .venv
	@if [ -x .venv/bin/python ]; then .venv/bin/python -m pip install --upgrade pip; else .venv/Scripts/python.exe -m pip install --upgrade pip; fi

smoke: cli-smoke lint-bib citation-check mirror-check mirror-freshness-check public-terms-check concept-term-check argument-focus-check figure-reference-check claim-evidence-check paper-layer-card-check workflow-check archive-seal-check submission-drift-check skill-mirror-check links-check research-request-handoff-check external-import-check collect-context template-readiness-check

cli-smoke:
	$(PYTHON) -m compileall src
	$(PYTHON) scripts/cli-smoke.py

scaffold-package-boundary-check:
	$(PYTHON) scripts/check-scaffold-package-boundary.py

lint-bib:
	$(PYTHON) template/scripts/lint-bib.py --root template

citation-check:
	$(PYTHON) template/scripts/check-citations.py --root template

mirror-check:
	$(PYTHON) template/scripts/mirror-check.py --root template/manuscript --report template/manuscript/mirror/reports/smoke-check.md

mirror-freshness-check:
	$(PYTHON) template/scripts/mirror-freshness-check.py --root template/manuscript

public-terms-check:
	$(PYTHON) template/scripts/check-public-terms.py --root template

concept-term-check:
	$(PYTHON) template/scripts/check-concept-terms.py --root template

argument-focus-check:
	$(PYTHON) template/scripts/check-argument-focus.py --root template

figure-reference-check:
	$(PYTHON) template/scripts/check-figure-references.py --root template

claim-evidence-check:
	$(PYTHON) template/scripts/check-claim-evidence.py --root template

paper-layer-card-check:
	$(PYTHON) template/scripts/check-paper-layer-cards.py --root template

workflow-check:
	$(PYTHON) template/scripts/check-workflow-state.py --root template

archive-seal-check:
	$(PYTHON) template/scripts/check-archive-seal.py --root template

submission-drift-check:
	$(PYTHON) template/scripts/check-submission-drift.py --root template

skill-mirror-check:
	$(PYTHON) template/scripts/check-skill-mirror.py --root template

links-check:
	$(PYTHON) template/scripts/check-links.py --root template

research-request-handoff-check:
	$(PYTHON) template/scripts/check-research-request-handoff.py --root template

external-import-check:
	$(PYTHON) template/scripts/check-external-imports.py --root template

collect-context:
	$(PYTHON) template/scripts/collect-note-context.py --root template --output template/notes/session-context.generated.md

template-readiness-check:
	$(PYTHON) template/scripts/readiness-check.py --root template --allow-placeholders
