.PHONY: venv build-ja build-en lint-bib citation-check mirror-check collect-context readiness-check export-arxiv ci pre-submit

PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,$(if $(wildcard .venv/Scripts/python.exe),.venv/Scripts/python.exe,python))
PYTHON_BOOTSTRAP ?= python

venv:
	$(PYTHON_BOOTSTRAP) -m venv .venv
	@if [ -x .venv/bin/python ]; then .venv/bin/python -m pip install --upgrade pip; else .venv/Scripts/python.exe -m pip install --upgrade pip; fi

build-ja:
	./scripts/build-ja.sh

build-en:
	./scripts/build-en.sh

lint-bib:
	$(PYTHON) scripts/lint-bib.py --root .

citation-check:
	$(PYTHON) scripts/check-citations.py --root .

mirror-check:
	$(PYTHON) scripts/mirror-check.py --root manuscript --report manuscript/mirror/reports/latest.md

collect-context:
	$(PYTHON) scripts/collect-note-context.py --root . --output notes/session-context.generated.md

readiness-check:
	$(PYTHON) scripts/readiness-check.py --root .

export-arxiv:
	./scripts/export-arxiv.sh

ci: lint-bib citation-check mirror-check build-ja build-en

pre-submit: ci readiness-check
