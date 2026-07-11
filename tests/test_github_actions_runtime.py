from __future__ import annotations

import re
import unittest

from tests.helpers import ROOT


EXPECTED = {
    "actions/checkout": "v7",
    "actions/setup-python": "v6",
    "actions/upload-artifact": "v7",
    "actions/download-artifact": "v8",
}
ACTION = re.compile(r"uses:\s+(actions/[A-Za-z0-9_.-]+)@([^\s#]+)")


class GitHubActionsRuntimeTest(unittest.TestCase):
    def test_direct_official_actions_use_node24_major_tags(self) -> None:
        seen: dict[str, set[str]] = {}
        for workflow in sorted((ROOT / ".github/workflows").glob("*.yml")):
            for name, version in ACTION.findall(workflow.read_text(encoding="utf-8")):
                seen.setdefault(name, set()).add(version)

        self.assertEqual(
            seen,
            {name: {version} for name, version in EXPECTED.items()},
        )

    def test_publish_boundary_is_unchanged(self) -> None:
        text = (ROOT / ".github/workflows/publish-pypi.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("git merge-base --is-ancestor", text)
        self.assertIn("uses: pypa/gh-action-pypi-publish@release/v1", text)
        self.assertIn('python-version: "3.12"', text)


if __name__ == "__main__":
    unittest.main()
