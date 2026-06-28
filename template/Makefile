.PHONY: venv build-ja build-en build-submission lint-bib lint-bib-pre-submit citation-check mirror-check mirror-freshness-check mirror-strict-check public-terms-check concept-term-check argument-focus-check storyline-check section-contract-check section-depth-check quantity-integrity-check predicted-results-check content-first-check finish-manuscript-check submission-gate figure-reference-check figure-obligation-check figure-design-check claim-evidence-check paper-layer-card-check card-coverage-check workflow-check archive-seal-check submission-drift-check skill-mirror-check links-check research-request-handoff-check research-request-handoff-live-check external-import-check external-import-live-check collect-context readiness-check export-arxiv ci audit pre-submit

PYTHON_FALLBACK = $(shell bash scripts/resolve-python.sh "$(CURDIR)" 2>/dev/null || echo python3.11)
PYTHON ?= $(PYTHON_FALLBACK)
PYTHON_BOOTSTRAP ?= $(PYTHON_FALLBACK)

CI_CHECKS = \
	lint-bib \
	citation-check \
	mirror-check \
	public-terms-check \
	paper-layer-card-check \
	card-coverage-check \
	workflow-check \
	archive-seal-check \
	skill-mirror-check \
	links-check

AUDIT_CHECKS = \
	mirror-freshness-check \
	concept-term-check \
	argument-focus-check \
	authoring-intent-check \
	storyline-check \
	section-contract-check \
	section-depth-check \
	quantity-integrity-check \
	predicted-results-check \
	content-first-check \
	figure-reference-check \
	figure-obligation-check \
	figure-design-check \
	claim-evidence-check \
	card-coverage-check \
	research-request-handoff-check \
	external-import-check \
	submission-drift-check

FINISH_MANUSCRIPT_CHECKS = \
	storyline-check \
	section-contract-check \
	public-terms-check \
	authoring-intent-check \
	quantity-integrity-check \
	predicted-results-check \
	figure-obligation-check \
	figure-design-check \
	claim-evidence-check \
	workflow-check

SUBMISSION_GATE_CHECKS = \
	public-terms-check \
	authoring-intent-check \
	predicted-results-check \
	research-request-handoff-check \
	submission-drift-check

PRE_SUBMIT_CHECKS = \
	ci \
	audit \
	finish-manuscript-check \
	lint-bib-pre-submit \
	mirror-strict-check \
	submission-gate

venv:
	$(PYTHON_BOOTSTRAP) -m venv .venv
	@if [ -x .venv/bin/python ]; then .venv/bin/python -m pip install --upgrade pip; else .venv/Scripts/python.exe -m pip install --upgrade pip; fi

build-ja:
	bash scripts/build-ja.sh

build-en:
	bash scripts/build-en.sh

build-submission:
	bash scripts/build-submission.sh $(VENUE)

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

authoring-intent-check:
	$(PYTHON) scripts/check-authoring-intent.py --root .

storyline-check:
	$(PYTHON) scripts/check-storyline.py --root .

section-contract-check:
	$(PYTHON) scripts/check-section-contracts.py --root .

section-depth-check:
	$(PYTHON) scripts/check-section-depth.py --root .

quantity-integrity-check:
	$(PYTHON) scripts/check-quantity-integrity.py --root .

predicted-results-check:
	$(PYTHON) scripts/check-predicted-results.py --root .

content-first-check:
	$(PYTHON) scripts/check-content-first.py --root . --phase start --intent content

finish-manuscript-check: $(FINISH_MANUSCRIPT_CHECKS)
	$(PYTHON) scripts/check-public-terms.py --root . --strict
	$(PYTHON) scripts/check-authoring-intent.py --root . --strict
	$(PYTHON) scripts/check-section-contracts.py --root . --strict
	$(PYTHON) scripts/check-section-depth.py --root . --strict
	$(PYTHON) scripts/check-predicted-results.py --root . --scope all --strict
	$(PYTHON) scripts/check-figure-design.py --root . --strict
	$(PYTHON) scripts/check-claim-evidence.py --root . --strict
	$(PYTHON) scripts/check-content-first.py --root . --phase finish --intent content --strict

submission-gate: $(SUBMISSION_GATE_CHECKS)
	$(PYTHON) scripts/check-predicted-results.py --root . --scope all --strict
	$(PYTHON) scripts/check-public-terms.py --root . --strict
	$(PYTHON) scripts/check-authoring-intent.py --root . --strict
	$(PYTHON) scripts/check-research-request-handoff.py --root . --strict
	$(PYTHON) scripts/check-submission-drift.py --root . --strict

figure-reference-check:
	$(PYTHON) scripts/check-figure-references.py --root .

figure-obligation-check:
	$(PYTHON) scripts/check-figure-obligations.py --root .

figure-design-check:
	$(PYTHON) scripts/check-figure-design.py --root .

claim-evidence-check:
	$(PYTHON) scripts/check-claim-evidence.py --root .

paper-layer-card-check:
	$(PYTHON) scripts/check-paper-layer-cards.py --root .

card-coverage-check:
	$(PYTHON) scripts/check-card-coverage.py --root .

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

research-request-handoff-live-check:
	$(PYTHON) scripts/check-research-request-handoff.py --root . --live

external-import-check:
	$(PYTHON) scripts/check-external-imports.py --root .

external-import-live-check:
	$(PYTHON) scripts/check-external-imports.py --root . --live

collect-context:
	$(PYTHON) scripts/collect-note-context.py --root . --output _paperops/notes/session-context.generated.md

readiness-check:
	$(PYTHON) scripts/readiness-check.py --root .

export-arxiv:
	bash scripts/export-arxiv.sh

ci: $(CI_CHECKS) build-ja build-en

audit: $(AUDIT_CHECKS)

pre-submit: $(PRE_SUBMIT_CHECKS)
	$(PYTHON) scripts/check-concept-terms.py --root . --strict
	$(PYTHON) scripts/check-authoring-intent.py --root . --strict
	$(PYTHON) scripts/check-storyline.py --root . --strict
	$(PYTHON) scripts/check-section-depth.py --root . --strict
	$(PYTHON) scripts/check-quantity-integrity.py --root . --strict
	$(PYTHON) scripts/check-figure-references.py --root . --strict
	$(PYTHON) scripts/check-figure-obligations.py --root . --strict
	$(PYTHON) scripts/check-figure-design.py --root . --strict
	$(PYTHON) scripts/check-research-request-handoff.py --root . --strict
	$(PYTHON) scripts/check-external-imports.py --root . --strict
	$(PYTHON) scripts/readiness-check.py --root . --require-submission
	$(PYTHON) scripts/check-submission-drift.py --root . --strict

-include Makefile.project
-include Makefile.local
