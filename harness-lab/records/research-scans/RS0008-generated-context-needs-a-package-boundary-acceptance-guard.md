---
id: RS0008
record_type: research_scan
created_at: '2026-05-18T04:18:48+09:00'
status: captured
scope: paperops release packaging and scaffold generation
existing_dossier: extends RS0001 package-distribution concerns without reopening adopted IMP0001
classification:
  capability: scaffold package boundary hygiene
  failure_class: ignored generated template artifacts can cross release and source-of-truth boundaries
evidence:
  local:
  - summary: make smoke runs collect-context and writes template/notes/session-context.generated.md; .gitignore ignores that path so ordinary status hides the generated source-tree artifact
    ref: Makefile;.gitignore
  codebase:
  - summary: pyproject force-includes template into paperops/_data/scaffold for wheels, while copy_scaffold excludes notes/session-context.generated.md at init/update time
    ref: pyproject.toml;src/paperops/cli/constants.py;src/paperops/cli/scaffold.py
  external: []
  risk:
  - summary: A release built after smoke could package an ignored generated snapshot or leave maintainers unsure whether generated context is source, package data, or disposable working-tree output
    ref: template/scripts/collect-note-context.py
candidates:
- title: Add a built-wheel scaffold acceptance smoke for generated/ignored artifact boundaries
  relation: queued_for_later
  recommendation: verify wheel data and pops init/update behavior from an installed wheel before publish
  next_command: hops lab capture --title "Built wheel scaffold package boundary guard" --summary "..." --expected-change "..."
recommendation: 'queued_for_later: investigate with a temp wheel build before implementation; do not change template or packaging in this lane'
---

# RS0008: Generated context needs a package-boundary acceptance guard

## Scope

- scope: paperops release packaging and scaffold generation
- existing_dossier: extends RS0001 package-distribution concerns without reopening adopted IMP0001
- capability: scaffold package boundary hygiene
- failure_class: ignored generated template artifacts can cross release and source-of-truth boundaries

## Evidence

### Local

- make smoke runs collect-context and writes template/notes/session-context.generated.md; .gitignore ignores that path so ordinary status hides the generated source-tree artifact (ref: Makefile;.gitignore)

### Codebase

- pyproject force-includes template into paperops/_data/scaffold for wheels, while copy_scaffold excludes notes/session-context.generated.md at init/update time (ref: pyproject.toml;src/paperops/cli/constants.py;src/paperops/cli/scaffold.py)

### External

- なし

### Risk And Counterexample

- A release built after smoke could package an ignored generated snapshot or leave maintainers unsure whether generated context is source, package data, or disposable working-tree output (ref: template/scripts/collect-note-context.py)

## Candidates

| candidate | relation | recommendation | next_command |
|---|---|---|---|
| Add a built-wheel scaffold acceptance smoke for generated/ignored artifact boundaries | queued_for_later | verify wheel data and pops init/update behavior from an installed wheel before publish | hops lab capture --title "Built wheel scaffold package boundary guard" --summary "..." --expected-change "..." |

## Recommendation

queued_for_later: investigate with a temp wheel build before implementation; do not change template or packaging in this lane

## Next Commands

- `hops lab capture --title "Built wheel scaffold package boundary guard" --summary "..." --expected-change "..."`
