.PHONY: venv smoke lint-bib mirror-check collect-context publish-scaffold-dry-run

PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3.11)

venv:
	python3.11 -m venv .venv
	./.venv/bin/python -m pip install --upgrade pip

smoke: lint-bib mirror-check collect-context

lint-bib:
	$(PYTHON) template/scripts/lint-bib.py --root template

mirror-check:
	$(PYTHON) template/scripts/mirror-check.py --root template/manuscript --report template/manuscript/mirror/reports/smoke-check.md

collect-context:
	$(PYTHON) template/scripts/collect-note-context.py --root template --output template/notes/session-context.generated.md

publish-scaffold-dry-run:
	chmod +x scripts/publish-scaffold.sh
	./scripts/publish-scaffold.sh --source-dir template --target-dir /tmp/paper-harness-scaffold-preview --dry-run
