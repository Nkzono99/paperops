.PHONY: venv smoke cli-smoke lint-bib citation-check mirror-check mirror-freshness-check public-terms-check claim-evidence-check submission-drift-check skill-mirror-check collect-context template-readiness-check

PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,$(if $(wildcard .venv/Scripts/python.exe),.venv/Scripts/python.exe,python))
PYTHON_BOOTSTRAP ?= python

venv:
	$(PYTHON_BOOTSTRAP) -m venv .venv
	@if [ -x .venv/bin/python ]; then .venv/bin/python -m pip install --upgrade pip; else .venv/Scripts/python.exe -m pip install --upgrade pip; fi

smoke: cli-smoke lint-bib citation-check mirror-check mirror-freshness-check public-terms-check claim-evidence-check submission-drift-check skill-mirror-check collect-context template-readiness-check

cli-smoke:
	$(PYTHON) -m compileall src
	$(PYTHON) scripts/cli-smoke.py

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

claim-evidence-check:
	$(PYTHON) template/scripts/check-claim-evidence.py --root template

submission-drift-check:
	$(PYTHON) template/scripts/check-submission-drift.py --root template

skill-mirror-check:
	$(PYTHON) template/scripts/check-skill-mirror.py --root template

collect-context:
	$(PYTHON) template/scripts/collect-note-context.py --root template --output template/notes/session-context.generated.md

template-readiness-check:
	$(PYTHON) template/scripts/readiness-check.py --root template --allow-placeholders
