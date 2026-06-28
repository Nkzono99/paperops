"""Shared constants for the ``pops`` CLI."""

PACKAGE_NAME = "paper-harness-cli"
UPSTREAM_REPO = "Nkzono99/paperops"
CHANGELOG_URL = f"https://github.com/{UPSTREAM_REPO}/blob/main/CHANGELOG.md"
PYPI_JSON_URL = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"
UPDATE_CHECK_INTERVAL_SECONDS = 24 * 60 * 60
LAYOUT_VERSION = "0.1"
UPGRADE_CHAIN_SUPPORTED_SINCE = "0.1.0"

EXCLUDED_SCAFFOLD_PATTERNS = (
    ".git",
    ".git/*",
    ".harness",
    ".harness/*",
    ".harnessops",
    ".harnessops/*",
    ".venv",
    ".venv/*",
    ".paperops",
    ".paperops/*",
    ".tools",
    ".tools/*",
    "dist",
    "dist/*",
    "__pycache__",
    "__pycache__/*",
    "*/__pycache__",
    "*/__pycache__/*",
    "**/__pycache__",
    "**/__pycache__/*",
    "*.pyc",
    "_archives/*",
    "harness-feedback",
    "harness-feedback/*",
    "harness-lab",
    "harness-lab/*",
    ".claude/settings.local.json",
    "_handoff/*",
    "_paperops/notes/session-context.generated.md",
    "notes/session-context.generated.md",
    "manuscript/mirror/reports/latest.md",
    "manuscript/mirror/reports/smoke-check.md",
    "manuscript/shared/build/en",
    "manuscript/shared/build/en/*",
    "manuscript/shared/build/ja",
    "manuscript/shared/build/ja/*",
    "submission/*/build",
    "submission/*/build/*",
    "submission/*/.tools",
    "submission/*/.tools/*",
    "submission/**/build",
    "submission/**/build/**",
    "submission/**/.tools",
    "submission/**/.tools/**",
    "tex-env.toml",
    "_paperops/refs/local/locations.toml",
    "refs/local/locations.toml",
    "_paperops/refs/papers",
    "_paperops/refs/papers/**",
    "refs/papers",
    "refs/papers/**",
    "_paperops/refs/research/**/results",
    "_paperops/refs/research/**/results/**",
    "_paperops/refs/research/**/report.generated.md",
    "_paperops/refs/research/**/raw-findings.*",
    "refs/research/**/results",
    "refs/research/**/results/**",
    "refs/research/**/report.generated.md",
    "refs/research/**/raw-findings.*",
    "_paperops/refs/source-reach/**/raw",
    "_paperops/refs/source-reach/**/raw/**",
    "_paperops/refs/source-reach/**/doctor.generated.*",
    "_paperops/refs/source-reach/**/capture.generated.*",
    "refs/source-reach/**/raw",
    "refs/source-reach/**/raw/**",
    "refs/source-reach/**/doctor.generated.*",
    "refs/source-reach/**/capture.generated.*",
)

SCAFFOLD_INCLUDE_EXCEPTIONS = (
    "_handoff/.gitkeep",
    "_handoff/README.md",
    "_archives/AGENTS.md",
    "_archives/README.md",
    "_paperops/refs/papers/.gitkeep",
    "refs/papers/.gitkeep",
)

MANAGED_UPDATE_PATTERNS = (
    "AGENTS.md",
    "CLAUDE.md",
    "Makefile",
    "TROUBLESHOOTING.md",
    "_paperops/defaults/contracts/*",
    "_paperops/defaults/workflow/*",
    "contracts/*",
    "workflow/*",
    "scripts/*",
    ".agents/*",
    ".claude/*",
    ".github/ISSUE_TEMPLATE/*",
    ".github/PULL_REQUEST_TEMPLATE.md",
)

PROJECT_EXTENSION_PATTERNS = (
    "AGENTS.project.md",
    "CLAUDE.project.md",
    "Makefile.project",
    "Makefile.local",
    ".agents/skills/project-*",
    ".agents/skills/project-*/*",
    ".claude/skills/project-*",
    ".claude/skills/project-*/*",
)

PROJECT_MARKERS = (
    "manuscript",
    "_paperops",
    "scripts",
    "Makefile",
)
