from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT, run_cli, run_python_script
from paperops.cli.links import ALLOWED_ACCESS, ALLOWED_LINK_KINDS


class LinksCheckTest(unittest.TestCase):
    def test_cli_and_template_script_report_unknown_kind(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            code, _out, err = run_cli(["init", str(target)])
            self.assertEqual(code, 0, err)
            self.assertTrue((target / "scripts" / "paperops_links.py").is_file())

            links_path = target / "_paperops" / "refs" / "links.toml"
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

    def test_template_link_helper_keeps_cli_link_schema_constants(self) -> None:
        helper = ROOT / "template" / "scripts" / "paperops_links.py"
        spec = importlib.util.spec_from_file_location("paperops_links_under_test", helper)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(helper.parent))
        try:
            spec.loader.exec_module(module)
        finally:
            sys.path.remove(str(helper.parent))

        self.assertEqual(module.ALLOWED_LINK_KINDS, ALLOWED_LINK_KINDS)
        self.assertEqual(module.ALLOWED_ACCESS, ALLOWED_ACCESS)


if __name__ == "__main__":
    unittest.main()
