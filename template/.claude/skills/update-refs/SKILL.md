---
name: update-refs
description: Validate bibliography and reference knowledge alignment. Use when adding citations or after editing bib files.
allowed-tools: Read, Edit, Write, Glob, Grep
---

# update-refs

Use this skill when bibliography and reference knowledge need to be brought back in sync with the manuscript.

## Tasks

1. Review `manuscript/shared/bib/*.bib` and `refs/bib/curated/`.
2. Check whether high-value cited papers have summaries in `refs/summaries/`.
3. Flag manuscript citations that lack curated metadata or a usable summary.
4. Suggest the next reference curation tasks in priority order.

## Principles

- Prefer curated summaries over raw PDF accumulation.
- Keep citation keys stable once they appear in the manuscript.
- Log unresolved citation questions in `notes/open-questions.md` if they affect writing.
