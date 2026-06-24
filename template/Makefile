.PHONY: venv build-ja build-en lint-bib lint-bib-pre-submit citation-check mirror-check mirror-freshness-check mirror-strict-check public-terms-check argument-focus-check figure-reference-check claim-evidence-check paper-layer-card-check submission-drift-check skill-mirror-check links-check external-import-check collect-context readiness-check export-arxiv ci pre-submit

PYTHON_FALLBACK := $(shell command -v python3.11 2>/dev/null || command -v python3 2>/dev/null || command -v python 2>/dev/null)
PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,$(if $(wildcard .venv/Scripts/python.exe),.venv/Scripts/python.exe,$(PYTHON_FALLBACK)))
PYTHON_BOOTSTRAP ?= $(PYTHON_FALLBACK)

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

argument-focus-check:
	$(PYTHON) scripts/check-argument-focus.py --root .

figure-reference-check:
	$(PYTHON) scripts/check-figure-references.py --root .

claim-evidence-check:
	$(PYTHON) scripts/check-claim-evidence.py --root .

paper-layer-card-check:
	$(PYTHON) scripts/check-paper-layer-cards.py --root .

submission-drift-check:
	$(PYTHON) scripts/check-submission-drift.py --root .

skill-mirror-check:
	$(PYTHON) scripts/check-skill-mirror.py --root .

links-check:
	$(PYTHON) scripts/check-links.py --root .

external-import-check:
	$(PYTHON) scripts/check-external-imports.py --root .

collect-context:
	$(PYTHON) scripts/collect-note-context.py --root . --output notes/session-context.generated.md

readiness-check:
	$(PYTHON) scripts/readiness-check.py --root .

export-arxiv:
	bash scripts/export-arxiv.sh

ci: lint-bib citation-check mirror-check mirror-freshness-check public-terms-check argument-focus-check figure-reference-check claim-evidence-check paper-layer-card-check skill-mirror-check links-check external-import-check build-ja build-en

pre-submit: ci lint-bib-pre-submit mirror-strict-check
	$(PYTHON) scripts/readiness-check.py --root . --require-submission
	$(PYTHON) scripts/check-submission-drift.py --root .
