.PHONY: build-ja build-en lint-bib mirror-check collect-context export-arxiv ci

build-ja:
	./scripts/build-ja.sh

build-en:
	./scripts/build-en.sh

lint-bib:
	python3 scripts/lint-bib.py --root .

mirror-check:
	python3 scripts/mirror-check.py --root manuscript --report manuscript/mirror/reports/latest.md

collect-context:
	python3 scripts/collect-note-context.py --root . --output notes/session-context.generated.md

export-arxiv:
	./scripts/export-arxiv.sh

ci: lint-bib mirror-check build-ja build-en
