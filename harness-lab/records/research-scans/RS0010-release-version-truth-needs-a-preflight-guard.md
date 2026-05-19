---
id: RS0010
record_type: research_scan
created_at: '2026-05-20T04:18:18+09:00'
status: captured
scope: paperops release preparation and PyPI publish governance
existing_dossier:
classification:
  capability: release/version source-of-truth governance
  failure_class: duplicate or stale version/changelog state can mislead release automation
evidence:
  local:
  - summary: CHANGELOG has Unreleased plus released 0.2.0 - 2026-05-14, then older 0.3.0 - 2026-04-14 and another 0.2.0 - 2026-04-14 heading; chronology and uniqueness are not machine-guarded before release.
    ref: CHANGELOG.md
  - summary: pyproject.toml and src/paperops/__init__.py both still report 0.2.0 while the GitHub latest release and local tag are already v0.2.0; future release prep must choose a new version before tagging.
    ref: pyproject.toml;src/paperops/__init__.py;git tag --sort=v:refname;gh release list --repo Nkzono99/paperops --limit 10
  codebase:
  - summary: release skill requires updating pyproject version and moving Unreleased into a versioned changelog section, but does not currently name a deterministic preflight for duplicate changelog headings, next-version uniqueness, or pyproject/src/tag/GitHub release alignment.
    ref: .agents/skills/release/SKILL.md;docs/change-policy.md
  - summary: publish-pypi workflow validates that a release tag is reachable from origin/main, but that is a publish-time ancestry guard rather than a release-prep source-of-truth guard.
    ref: .github/workflows/publish-pypi.yml
  external: []
  risk:
  - summary: If an automation run has release authority, stale 0.2.0 package metadata or duplicate changelog headings can turn a valid PR/merge into a blocked tag, confusing notes, or a PyPI publish attempt that lacks a clear next version.
    ref: CHANGELOG.md;pyproject.toml;src/paperops/__init__.py
candidates:
- title: Add a release-preflight version truth check
  relation: selected_for_execution
  recommendation: verify CHANGELOG heading uniqueness/order, pyproject/src version agreement, next tag absence, and GitHub latest-release alignment before any release branch/tag work
  next_command: python scripts/check-release-version-truth.py
- title: Fold non-mutating smoke concerns into adopted scaffold package boundary guard
  relation: record_only
  recommendation: RS0008/IMP0003/D0005 already cover generated context package boundary; do not create a separate smoke side-effect record unless a new failure appears
  next_command: hops lab investigate --from IMP0003 --kind codebase --summary "..." --evidence-ref "..."
- title: Park structured update-paperops manifest output
  relation: park
  recommendation: RS0003 already covered plan explainability and there is no new downstream friction proving agent-readable JSON is needed
  next_command: none
recommendation: record selected release-preflight guard for priority lane; fold smoke side-effect into IMP0003 and park lower-evidence ideas
---

# RS0010: Release version truth needs a preflight guard

## Scope

- scope: paperops release preparation and PyPI publish governance
- existing_dossier: 未設定
- capability: release/version source-of-truth governance
- failure_class: duplicate or stale version/changelog state can mislead release automation

## Evidence

### Local

- CHANGELOG has Unreleased plus released 0.2.0 - 2026-05-14, then older 0.3.0 - 2026-04-14 and another 0.2.0 - 2026-04-14 heading; chronology and uniqueness are not machine-guarded before release. (ref: CHANGELOG.md)
- pyproject.toml and src/paperops/__init__.py both still report 0.2.0 while the GitHub latest release and local tag are already v0.2.0; future release prep must choose a new version before tagging. (ref: pyproject.toml;src/paperops/__init__.py;git tag --sort=v:refname;gh release list --repo Nkzono99/paperops --limit 10)

### Codebase

- release skill requires updating pyproject version and moving Unreleased into a versioned changelog section, but does not currently name a deterministic preflight for duplicate changelog headings, next-version uniqueness, or pyproject/src/tag/GitHub release alignment. (ref: .agents/skills/release/SKILL.md;docs/change-policy.md)
- publish-pypi workflow validates that a release tag is reachable from origin/main, but that is a publish-time ancestry guard rather than a release-prep source-of-truth guard. (ref: .github/workflows/publish-pypi.yml)

### External

- なし

### Risk And Counterexample

- If an automation run has release authority, stale 0.2.0 package metadata or duplicate changelog headings can turn a valid PR/merge into a blocked tag, confusing notes, or a PyPI publish attempt that lacks a clear next version. (ref: CHANGELOG.md;pyproject.toml;src/paperops/__init__.py)

## Candidates

| candidate | relation | recommendation | next_command |
|---|---|---|---|
| Add a release-preflight version truth check | selected_for_execution | verify CHANGELOG heading uniqueness/order, pyproject/src version agreement, next tag absence, and GitHub latest-release alignment before any release branch/tag work | python scripts/check-release-version-truth.py |
| Fold non-mutating smoke concerns into adopted scaffold package boundary guard | record_only | RS0008/IMP0003/D0005 already cover generated context package boundary; do not create a separate smoke side-effect record unless a new failure appears | hops lab investigate --from IMP0003 --kind codebase --summary "..." --evidence-ref "..." |
| Park structured update-paperops manifest output | park | RS0003 already covered plan explainability and there is no new downstream friction proving agent-readable JSON is needed | none |

## Recommendation

record selected release-preflight guard for priority lane; fold smoke side-effect into IMP0003 and park lower-evidence ideas

## Next Commands

- `python scripts/check-release-version-truth.py`
- `hops lab investigate --from IMP0003 --kind codebase --summary "..." --evidence-ref "..."`
- `none`
