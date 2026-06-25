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
    "dist",
    "dist/*",
    "_archives/*",
    "harness-feedback",
    "harness-feedback/*",
    "harness-lab",
    "harness-lab/*",
    ".claude/settings.local.json",
    "_handoff/*",
    "notes/session-context.generated.md",
    "manuscript/mirror/reports/latest.md",
    "manuscript/mirror/reports/smoke-check.md",
    "manuscript/shared/build/en",
    "manuscript/shared/build/en/*",
    "manuscript/shared/build/ja",
    "manuscript/shared/build/ja/*",
    "refs/local/locations.toml",
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
)

MANAGED_UPDATE_PATTERNS = (
    "AGENTS.md",
    "CLAUDE.md",
    "Makefile",
    "TROUBLESHOOTING.md",
    "contracts/*",
    "workflow/*",
    "scripts/*",
    ".agents/*",
    ".claude/*",
    ".github/ISSUE_TEMPLATE/*",
    ".github/PULL_REQUEST_TEMPLATE.md",
)

PROJECT_MARKERS = (
    "manuscript",
    "notes",
    "scripts",
    "Makefile",
)
