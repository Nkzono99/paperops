.PHONY: venv smoke cli-smoke scaffold-package-boundary-check build-submission lint-bib citation-check mirror-check mirror-freshness-check public-terms-check concept-term-check argument-focus-check authoring-intent-check storyline-check section-contract-check section-depth-check quantity-integrity-check content-first-check finish-manuscript-check figure-reference-check figure-obligation-check claim-evidence-check paper-layer-card-check workflow-check archive-seal-check submission-drift-check skill-mirror-check links-check research-request-handoff-check external-import-check collect-context template-readiness-check

PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,$(if $(wildcard .venv/Scripts/python.exe),.venv/Scripts/python.exe,python))
PYTHON_BOOTSTRAP ?= python

venv:
	$(PYTHON_BOOTSTRAP) -m venv .venv
	@if [ -x .venv/bin/python ]; then .venv/bin/python -m pip install --upgrade pip; else .venv/Scripts/python.exe -m pip install --upgrade pip; fi

smoke: cli-smoke lint-bib citation-check mirror-check mirror-freshness-check public-terms-check concept-term-check argument-focus-check authoring-intent-check storyline-check section-contract-check section-depth-check quantity-integrity-check content-first-check figure-reference-check figure-obligation-check claim-evidence-check paper-layer-card-check workflow-check archive-seal-check submission-drift-check skill-mirror-check links-check research-request-handoff-check external-import-check collect-context template-readiness-check

cli-smoke:
	$(PYTHON) -m compileall src
	$(PYTHON) scripts/cli-smoke.py

scaffold-package-boundary-check:
	$(PYTHON) scripts/check-scaffold-package-boundary.py

build-submission:
	bash template/scripts/build-submission.sh $(VENUE)

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

authoring-intent-check:
	$(PYTHON) template/scripts/check-authoring-intent.py --root template

storyline-check:
	$(PYTHON) template/scripts/check-storyline.py --root template

section-contract-check:
	$(PYTHON) template/scripts/check-section-contracts.py --root template

section-depth-check:
	$(PYTHON) template/scripts/check-section-depth.py --root template

quantity-integrity-check:
	$(PYTHON) template/scripts/check-quantity-integrity.py --root template

content-first-check:
	$(PYTHON) template/scripts/check-content-first.py --root template --phase start --intent content

finish-manuscript-check: storyline-check section-contract-check public-terms-check authoring-intent-check quantity-integrity-check figure-obligation-check claim-evidence-check workflow-check
	$(PYTHON) template/scripts/check-public-terms.py --root template --strict
	$(PYTHON) template/scripts/check-authoring-intent.py --root template --strict
	$(PYTHON) template/scripts/check-section-contracts.py --root template --strict
	$(PYTHON) template/scripts/check-section-depth.py --root template --strict
	$(PYTHON) template/scripts/check-content-first.py --root template --phase finish --intent content --strict

figure-reference-check:
	$(PYTHON) template/scripts/check-figure-references.py --root template

figure-obligation-check:
	$(PYTHON) template/scripts/check-figure-obligations.py --root template

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
	$(PYTHON) template/scripts/collect-note-context.py --root template --output template/_paperops/notes/session-context.generated.md

template-readiness-check:
	$(PYTHON) template/scripts/readiness-check.py --root template --allow-placeholders
