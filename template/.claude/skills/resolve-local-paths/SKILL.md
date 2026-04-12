# resolve-local-paths

Use this skill when the writing session needs to access simulation outputs, figure sources, or external knowledge stored outside the repository.

## Read

- `refs/local/locations.toml` if present
- otherwise `refs/local/locations.example.toml`
- `refs/local/aliases.md`

## Responsibilities

1. Resolve the alias to a concrete path and explain what lives there.
2. State whether the path is machine-specific or portable.
3. Suggest which notes or refs file should record the usage.

Never commit absolute personal paths into tracked files.
