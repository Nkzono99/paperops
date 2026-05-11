.PHONY: venv build-ja build-en lint-bib citation-check mirror-check mirror-freshness-check public-terms-check claim-evidence-check submission-drift-check collect-context readiness-check export-arxiv ci pre-submit

PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,$(if $(wildcard .venv/Scripts/python.exe),.venv/Scripts/python.exe,python))
PYTHON_BOOTSTRAP ?= python

venv:
	$(PYTHON_BOOTSTRAP) -m venv .venv
	@if [ -x .venv/bin/python ]; then .venv/bin/python -m pip install --upgrade pip; else .venv/Scripts/python.exe -m pip install --upgrade pip; fi

build-ja:
	bash scripts/build-ja.sh

build-en:
	bash scripts/build-en.sh

lint-bib:
	$(PYTHON) scripts/lint-bib.py --root .

citation-check:
	$(PYTHON) scripts/check-citations.py --root .

mirror-check:
	$(PYTHON) scripts/mirror-check.py --root manuscript --report manuscript/mirror/reports/latest.md

mirror-freshness-check:
	$(PYTHON) scripts/mirror-freshness-check.py --root manuscript

public-terms-check:
	$(PYTHON) scripts/check-public-terms.py --root .

claim-evidence-check:
	$(PYTHON) scripts/check-claim-evidence.py --root .

submission-drift-check:
	$(PYTHON) scripts/check-submission-drift.py --root .

collect-context:
	$(PYTHON) scripts/collect-note-context.py --root . --output notes/session-context.generated.md

readiness-check:
	$(PYTHON) scripts/readiness-check.py --root .

export-arxiv:
	bash scripts/export-arxiv.sh

ci: lint-bib citation-check mirror-check mirror-freshness-check public-terms-check claim-evidence-check build-ja build-en

pre-submit: ci readiness-check submission-drift-check
