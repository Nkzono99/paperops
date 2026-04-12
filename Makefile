.PHONY: smoke lint-bib mirror-check collect-context

smoke: lint-bib mirror-check collect-context

lint-bib:
	python3 template/scripts/lint-bib.py --root template

mirror-check:
	python3 template/scripts/mirror-check.py --root template/manuscript --report template/manuscript/mirror/reports/smoke-check.md

collect-context:
	python3 template/scripts/collect-note-context.py --root template --output template/notes/session-context.generated.md
