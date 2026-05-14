# External Link Registry

`refs/links.toml` is the tracked registry for external projects and directories used by this paper. It stores portable metadata only. Machine-specific absolute paths stay in the untracked `refs/local/locations.toml`.

## Schema

Each `[[links]]` entry should include:

- `alias`: stable name used from notes, skills, and manuscript planning.
- `kind`: `runops_project` for a RunOps project, or `directory` for a general external directory.
- `local_path_alias`: key under `[paths.<alias>]` in `refs/local/locations.toml`.
- `title` and `description`: short human-readable context.
- `expected_contents`: what the external location should contain.
- `share_status`: whether the source is `local-only`, `private-source`, or otherwise safe to describe.

Do not put local absolute paths, private dataset names, secrets, or unpublished project-specific details in `refs/links.toml`. Put local paths in `refs/local/locations.toml`, and put shareable claims or literature knowledge in `refs/summaries/` or `notes/`.

## Workflow

1. Add or update a `[[links]]` entry in `refs/links.toml`.
2. Add the matching `[paths.<local_path_alias>]` entry to your local `refs/local/locations.toml`.
3. Use `/resolve-local-paths` to resolve an alias during a session.
4. Run `uvx --from paper-harness-cli pops doctor` to catch malformed TOML or missing local aliases.
