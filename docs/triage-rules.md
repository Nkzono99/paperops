# Triage Rules

Use these rules when processing incoming template feedback.

## Scope test

- If the problem can affect multiple paper repositories, treat it as a template issue.
- If the problem depends on a specific venue, manuscript topic, or local machine path, keep it project-local unless a reusable abstraction is obvious.

## Change type

- `type:bug`: broken script, invalid workflow, incorrect file layout, missing protection
- `type:enhancement`: smoother authoring flow or clearer documentation
- `area:structure`: directories, naming, starter files
- `area:skills`: skill coverage, skill prompts, handoff flow
- `area:hooks`: protections or session hooks
- `area:mirror`: bilingual sync and drift reporting
- `area:refs`: bibliography or summary knowledge layer

## Acceptance bar

- The problem is reproducible.
- The proposed change has a plausible downstream benefit.
- The maintenance cost is lower than the expected repeated friction.

## Backwards compatibility

When a change touches an existing file path in `template/`, explicitly document:

- what downstream repos must update
- whether the old path still works
- whether a migration helper is needed
