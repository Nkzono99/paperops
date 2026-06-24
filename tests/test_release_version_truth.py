from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check-release-version-truth.py"
SPEC = importlib.util.spec_from_file_location("check_release_version_truth", SCRIPT)
release_truth = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = release_truth
SPEC.loader.exec_module(release_truth)


def write_repo(root: Path, *, pyproject_version: str, src_version: str, changelog: str) -> None:
    (root / "src" / "paperops").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "paper-harness-cli"',
                f'version = "{pyproject_version}"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (root / "src" / "paperops" / "__init__.py").write_text(
        f'__version__ = "{src_version}"\n',
        encoding="utf-8",
    )
    (root / "CHANGELOG.md").write_text(changelog, encoding="utf-8")


class ReleaseVersionTruthTest(unittest.TestCase):
    def run_check(
        self,
        *,
        changelog: str,
        pyproject_version: str = "0.2.0",
        src_version: str | None = None,
        **kwargs: object,
    ) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_repo(
                root,
                pyproject_version=pyproject_version,
                src_version=src_version or pyproject_version,
                changelog=changelog,
            )
            return release_truth.check_release_version_truth(root, **kwargs)

    def assert_check_failure(self, expected: str, **kwargs: object) -> str:
        with self.assertRaises(release_truth.CheckFailure) as raised:
            self.run_check(**kwargs)
        message = str(raised.exception)
        self.assertIn(expected, message)
        return message

    def test_default_check_accepts_current_released_version_with_unreleased_notes(self) -> None:
        facts = self.run_check(
            changelog="""# Change Log

## Unreleased

- Next change.

## 0.2.0 - 2026-05-14

- Released package.

## Template archive 0.3.0 - 2026-04-14

- Legacy template-only note.

## 0.1.0 - 2026-04-13

- First package release.
""",
        )

        self.assertIn("pyproject/src version: 0.2.0", facts)

    def test_default_check_rejects_duplicate_package_release_heading(self) -> None:
        self.assert_check_failure(
            "duplicate package release heading",
            changelog="""# Change Log

## Unreleased

## 0.2.0 - 2026-05-14

## 0.2.0 - 2026-04-14
""",
        )

    def test_default_check_rejects_metadata_mismatch(self) -> None:
        self.assert_check_failure(
            "must match",
            src_version="0.3.0",
            changelog="""# Change Log

## Unreleased

## 0.2.0 - 2026-05-14
""",
        )

    def test_release_mode_rejects_existing_target_tag(self) -> None:
        self.assert_check_failure(
            "already exists",
            pyproject_version="0.3.0",
            release_version="0.3.0",
            existing_tags={"v0.3.0"},
            changelog="""# Change Log

## Unreleased

## 0.3.0 - 2026-05-20

- Release notes.

## 0.2.0 - 2026-05-14

- Previous release.
""",
        )

    def test_release_mode_requires_target_metadata_and_empty_unreleased(self) -> None:
        message = self.assert_check_failure(
            "[project].version must be '0.3.0'",
            release_version="0.3.0",
            existing_tags=set(),
            changelog="""# Change Log

## Unreleased

- Not moved yet.

## 0.3.0 - 2026-05-20

- Release notes.

## 0.2.0 - 2026-05-14

- Previous release.
""",
        )
        self.assertIn("'## Unreleased' must be empty", message)


if __name__ == "__main__":
    unittest.main()
