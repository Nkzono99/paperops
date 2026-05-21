---
id: RS0012
record_type: research_scan
created_at: '2026-05-22T04:19:15+09:00'
status: captured
scope: paperops external link registry and runops handoff
existing_dossier: RS0007
classification:
  capability: external link privacy and handoff visibility
  failure_class: schema-valid links can hide read/write and local-only sharing boundaries
evidence:
  local:
  - summary: Open-meta scan selected privacy boundary preview over operator/release ideas; docs split shared link intent from ignored local paths and MCP-first read/plan flow.
    ref: .harnessops/cache/steward-runs/20260522-040226-cdc9cf8.json;docs/architecture.md;docs/cli.md
  codebase:
  - summary: pops links validates schema/kind/access/location_ref and list prints MCP/request metadata, but it does not render a pre-handoff boundary summary for shared intent, local-only fields, MCP read scope, and writeback request path.
    ref: src/paperops/cli/links.py;src/paperops/cli/main.py;template/refs/links.toml;template/notes/research-requests.md
  external: []
  risk:
  - summary: A blocking warning layer would slow normal runops use and could expose local path details; keep any preview nonblocking and derived from tracked intent unless the user explicitly resolves local paths.
    ref: template/refs/links.md;template/refs/local/README.md
candidates:
- title: Add nonblocking link boundary preview for runops handoff
  relation: queued_for_later
  recommendation: investigate UX and tests before implementation; keep RS0007 parity guard separate
  next_command: hops lab investigate --from RS0012 --kind codebase --summary Map link boundary fields to a nonblocking preview contract --evidence-ref src/paperops/cli/main.py;template/refs/links.md
recommendation: 'queued_for_later: create one privacy-boundary research candidate connected to RS0007; do not implement in invention lane'
---

# RS0012: Runops link handoff needs a privacy boundary preview

## Scope

- scope: paperops external link registry and runops handoff
- existing_dossier: RS0007
- capability: external link privacy and handoff visibility
- failure_class: schema-valid links can hide read/write and local-only sharing boundaries

## Evidence

### Local

- Open-meta scan selected privacy boundary preview over operator/release ideas; docs split shared link intent from ignored local paths and MCP-first read/plan flow. (ref: .harnessops/cache/steward-runs/20260522-040226-cdc9cf8.json;docs/architecture.md;docs/cli.md)

### Codebase

- pops links validates schema/kind/access/location_ref and list prints MCP/request metadata, but it does not render a pre-handoff boundary summary for shared intent, local-only fields, MCP read scope, and writeback request path. (ref: src/paperops/cli/links.py;src/paperops/cli/main.py;template/refs/links.toml;template/notes/research-requests.md)

### External

- なし

### Risk And Counterexample

- A blocking warning layer would slow normal runops use and could expose local path details; keep any preview nonblocking and derived from tracked intent unless the user explicitly resolves local paths. (ref: template/refs/links.md;template/refs/local/README.md)

## Candidates

| candidate | relation | recommendation | next_command |
|---|---|---|---|
| Add nonblocking link boundary preview for runops handoff | queued_for_later | investigate UX and tests before implementation; keep RS0007 parity guard separate | hops lab investigate --from RS0012 --kind codebase --summary Map link boundary fields to a nonblocking preview contract --evidence-ref src/paperops/cli/main.py;template/refs/links.md |

## Recommendation

queued_for_later: create one privacy-boundary research candidate connected to RS0007; do not implement in invention lane

## Next Commands

- `hops lab investigate --from RS0012 --kind codebase --summary Map link boundary fields to a nonblocking preview contract --evidence-ref src/paperops/cli/main.py;template/refs/links.md`
