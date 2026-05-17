---
id: RS0007
record_type: research_scan
created_at: '2026-05-17T10:46:02+09:00'
status: captured
scope: paperops link registry validation
existing_dossier:
classification:
  capability: link registry validation consistency
  failure_class: CLI and template script link checks can drift
evidence:
  local:
  - summary: Open scan noted pops links check and template/scripts/check-links.py duplicate validation logic to keep downstream scripts independent.
    ref: src/paperops/cli/links.py; template/scripts/check-links.py
  codebase:
  - summary: Added a regression test that mutates a scaffold link kind and asserts both the CLI and copied template script report the unknown kind.
    ref: tests/test_links_check.py
  external: []
  risk:
  - summary: Refactoring the template script to import the CLI would make downstream make links-check depend on the package, so this keeps implementations separate and guards parity by behavior.
    ref: tests/test_links_check.py
candidates:
- title: Add behavioral parity test for CLI and template link checks
  relation: record_only
  recommendation: implemented as test-only guard; no runtime change
  next_command: python -m unittest tests.test_links_check
recommendation: 'record_only: parity test is enough for now; defer shared implementation until schema drift repeats or link schema grows'
---

# RS0007: link registry duplicate implementations get a parity guard

## Scope

- scope: paperops link registry validation
- existing_dossier: 未設定
- capability: link registry validation consistency
- failure_class: CLI and template script link checks can drift

## Evidence

### Local

- Open scan noted pops links check and template/scripts/check-links.py duplicate validation logic to keep downstream scripts independent. (ref: src/paperops/cli/links.py; template/scripts/check-links.py)

### Codebase

- Added a regression test that mutates a scaffold link kind and asserts both the CLI and copied template script report the unknown kind. (ref: tests/test_links_check.py)

### External

- なし

### Risk And Counterexample

- Refactoring the template script to import the CLI would make downstream make links-check depend on the package, so this keeps implementations separate and guards parity by behavior. (ref: tests/test_links_check.py)

## Candidates

| candidate | relation | recommendation | next_command |
|---|---|---|---|
| Add behavioral parity test for CLI and template link checks | record_only | implemented as test-only guard; no runtime change | python -m unittest tests.test_links_check |

## Recommendation

record_only: parity test is enough for now; defer shared implementation until schema drift repeats or link schema grows

## Next Commands

- `python -m unittest tests.test_links_check`
