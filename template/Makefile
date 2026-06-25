.PHONY: venv build-ja build-en lint-bib lint-bib-pre-submit citation-check mirror-check mirror-freshness-check mirror-strict-check public-terms-check concept-term-check argument-focus-check figure-reference-check claim-evidence-check paper-layer-card-check workflow-check archive-seal-check submission-drift-check skill-mirror-check links-check research-request-handoff-check external-import-check collect-context readiness-check export-arxiv ci audit pre-submit

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

lint-bib-pre-submit:
	$(PYTHON) scripts/lint-bib.py --root . --mode pre-submit

citation-check:
	$(PYTHON) scripts/check-citations.py --root .

mirror-check:
	$(PYTHON) scripts/mirror-check.py --root manuscript --report manuscript/mirror/reports/latest.md

mirror-freshness-check:
	$(PYTHON) scripts/mirror-freshness-check.py --root manuscript

mirror-strict-check:
	$(PYTHON) scripts/mirror-freshness-check.py --root manuscript --strict

public-terms-check:
	$(PYTHON) scripts/check-public-terms.py --root .

concept-term-check:
	$(PYTHON) scripts/check-concept-terms.py --root .

argument-focus-check:
	$(PYTHON) scripts/check-argument-focus.py --root .

figure-reference-check:
	$(PYTHON) scripts/check-figure-references.py --root .

claim-evidence-check:
	$(PYTHON) scripts/check-claim-evidence.py --root .

paper-layer-card-check:
	$(PYTHON) scripts/check-paper-layer-cards.py --root .

workflow-check:
	$(PYTHON) scripts/check-workflow-state.py --root .

archive-seal-check:
	$(PYTHON) scripts/check-archive-seal.py --root .

submission-drift-check:
	$(PYTHON) scripts/check-submission-drift.py --root .

skill-mirror-check:
	$(PYTHON) scripts/check-skill-mirror.py --root .

links-check:
	$(PYTHON) scripts/check-links.py --root .

research-request-handoff-check:
	$(PYTHON) scripts/check-research-request-handoff.py --root .

external-import-check:
	$(PYTHON) scripts/check-external-imports.py --root .

collect-context:
	$(PYTHON) scripts/collect-note-context.py --root . --output notes/session-context.generated.md

readiness-check:
	$(PYTHON) scripts/readiness-check.py --root .

export-arxiv:
	bash scripts/export-arxiv.sh

ci: lint-bib citation-check mirror-check public-terms-check paper-layer-card-check workflow-check archive-seal-check skill-mirror-check links-check build-ja build-en

audit: mirror-freshness-check concept-term-check argument-focus-check figure-reference-check claim-evidence-check research-request-handoff-check external-import-check submission-drift-check

pre-submit: ci audit lint-bib-pre-submit mirror-strict-check
	$(PYTHON) scripts/check-concept-terms.py --root . --strict
	$(PYTHON) scripts/check-figure-references.py --root . --strict
	$(PYTHON) scripts/check-research-request-handoff.py --root . --strict
	$(PYTHON) scripts/check-external-imports.py --root . --strict
	$(PYTHON) scripts/readiness-check.py --root . --require-submission
	$(PYTHON) scripts/check-submission-drift.py --root .
