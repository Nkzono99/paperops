---
name: review-template-regression
description: Review template changes for regressions in mirror tracking, file protection, session continuity, or downstream compatibility.
allowed-tools: Read, Glob, Grep
---

# review-template-regression

Use this skill when reviewing a pull request or diff that modifies the template.

## Review focus

- regressions in bilingual mirror tracking
- weaker protection around generated files and local paths
- loss of session continuity in `notes/`
- broken starter scripts or reusable workflows
- undocumented interface changes for downstream repositories

## Process

1. Read the changed files in full.
2. Compare them against `docs/architecture.md` and `docs/change-policy.md`.
3. Prioritize concrete breakages and missing migrations.
4. Call out testing gaps if the smoke checks do not exercise the changed path.
