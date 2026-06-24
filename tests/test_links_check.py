from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.helpers import run_cli, run_python_script


class LinksCheckTest(unittest.TestCase):
    def test_cli_and_template_script_report_unknown_kind(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            code, _out, err = run_cli(["init", str(target)])
            self.assertEqual(code, 0, err)

            links_path = target / "refs" / "links.toml"
            links_path.write_text(
                links_path.read_text(encoding="utf-8").replace(
                    'kind = "runops_project"',
                    'kind = "mystery"',
                    1,
                ),
                encoding="utf-8",
            )

            cli_code, cli_out, _cli_err = run_cli(["links", "check", str(target)])
            script_result = run_python_script(
                target / "scripts" / "check-links.py",
                "--root",
                target,
            )

        self.assertEqual(cli_code, 1)
        self.assertEqual(script_result.returncode, 1)
        for output in [cli_out, script_result.stdout]:
            self.assertIn("kind `mystery` は未知です", output)


if __name__ == "__main__":
    unittest.main()
