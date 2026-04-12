.PHONY: venv build-ja build-en lint-bib mirror-check collect-context export-arxiv ci

PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3.11)

venv:
	python3.11 -m venv .venv
	./.venv/bin/python -m pip install --upgrade pip

build-ja:
	./scripts/build-ja.sh

build-en:
	./scripts/build-en.sh

lint-bib:
	$(PYTHON) scripts/lint-bib.py --root .

mirror-check:
	$(PYTHON) scripts/mirror-check.py --root manuscript --report manuscript/mirror/reports/latest.md

collect-context:
	$(PYTHON) scripts/collect-note-context.py --root . --output notes/session-context.generated.md

export-arxiv:
	./scripts/export-arxiv.sh

ci: lint-bib mirror-check build-ja build-en
