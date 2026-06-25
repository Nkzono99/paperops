from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


from tests.helpers import copy_template


class TemplateBuildFallbackTest(unittest.TestCase):
    def test_build_log_audit_flags_latex_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "main.log"
            log_path.write_text(
                "\n".join(
                    [
                        "! LaTeX Error: File `missing.sty' not found.",
                        "LaTeX Warning: Citation `missing-ref' undefined.",
                        "Missing character: There is no あ in font cmr10!",
                    ]
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    os.environ.get("PYTHON", sys.executable),
                    str(Path(__file__).resolve().parents[1] / "template" / "scripts" / "audit-build-log.py"),
                    "--log",
                    str(log_path),
                    "--label",
                    "test PDF",
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("build-log-audit", result.stdout)
        self.assertIn("LaTeX error", result.stdout)
        self.assertIn("undefined citation/reference", result.stdout)
        self.assertIn("Missing character", result.stdout)

    def test_ja_build_uses_xelatex_fallback_when_latexmk_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            fake_bin = Path(tmp) / "fake-bin"
            fake_bin.mkdir()
            log = Path(tmp) / "commands.log"
            bash_log = self.to_bash_path(log)
            self.write_fake_engine(fake_bin / "xelatex", bash_log)
            self.write_fake_bibtex(fake_bin / "bibtex", bash_log)

            env = os.environ.copy()
            bash = shutil.which("bash")
            self.assertIsNotNone(bash)
            env["PATH"] = str(fake_bin) + os.pathsep + str(Path(str(bash)).parent)

            result = subprocess.run(
                [
                    str(bash),
                    "-lc",
                    "export PAPER_TEMPLATE_RUN_LATEX=1 PAPEROPS_JA_DIRECT_ENGINE=xelatex; scripts/build-ja.sh",
                ],
                cwd=target,
                env=env,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            commands = log.read_text(encoding="utf-8") if log.exists() else ""
        self.assertGreaterEqual(commands.count("xelatex "), 3)
        self.assertIn("bibtex main", commands)
        self.assertIn("latexmk が見つからないため", result.stdout)
        self.assertIn(f"BIBINPUTS={target / 'manuscript' / 'shared' / 'bib'}//:", commands)
        self.assertIn(f"BSTINPUTS={target / 'manuscript' / 'shared' / 'style'}//:", commands)

    def test_runner_prefix_wraps_direct_engine_build(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            fake_bin = Path(tmp) / "fake-bin"
            fake_bin.mkdir()
            log = Path(tmp) / "commands.log"
            bash_log = self.to_bash_path(log)
            self.write_fake_engine(fake_bin / "xelatex", bash_log)
            self.write_fake_bibtex(fake_bin / "bibtex", bash_log)
            self.write_fake_runner(fake_bin / "runner", bash_log)

            env = os.environ.copy()
            bash = shutil.which("bash")
            self.assertIsNotNone(bash)
            env["PATH"] = str(fake_bin) + os.pathsep + str(Path(str(bash)).parent)

            result = subprocess.run(
                [
                    str(bash),
                    "-lc",
                    (
                        f"export PAPER_TEMPLATE_RUN_LATEX=1 "
                        f"PAPEROPS_JA_DIRECT_ENGINE=xelatex "
                        f"PAPEROPS_RUNNER_PREFIX={self.to_bash_path(fake_bin / 'runner')}; "
                        "scripts/build-ja.sh"
                    ),
                ],
                cwd=target,
                env=env,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            commands = log.read_text(encoding="utf-8") if log.exists() else ""
        self.assertIn("runner xelatex", commands)
        self.assertIn("runner bibtex", commands)

    def test_submission_build_helper_uses_submission_slot_and_runner_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            submission = target / "submission" / "demo-venue"
            submission.mkdir()
            (submission / "main.tex").write_text(
                textwrap.dedent(
                    r"""\
                    \documentclass{article}
                    \begin{document}
                    Submission draft.
                    \end{document}
                    """
                ),
                encoding="utf-8",
            )
            fake_bin = Path(tmp) / "fake-bin"
            fake_bin.mkdir()
            log = Path(tmp) / "commands.log"
            bash_log = self.to_bash_path(log)
            self.write_fake_engine(fake_bin / "lualatex", bash_log)
            self.write_fake_bibtex(fake_bin / "bibtex", bash_log)
            self.write_fake_runner(fake_bin / "runner", bash_log)

            env = os.environ.copy()
            bash = shutil.which("bash")
            self.assertIsNotNone(bash)
            env["PATH"] = str(fake_bin) + os.pathsep + str(Path(str(bash)).parent)

            result = subprocess.run(
                [
                    str(bash),
                    "-lc",
                    (
                        f"export PAPER_TEMPLATE_RUN_LATEX=1 "
                        f"PAPEROPS_SUBMISSION_DIRECT_ENGINE=lualatex "
                        f"PAPEROPS_RUNNER_PREFIX={self.to_bash_path(fake_bin / 'runner')}; "
                        "scripts/build-submission.sh demo-venue"
                    ),
                ],
                cwd=target,
                env=env,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            commands = log.read_text(encoding="utf-8") if log.exists() else ""
            self.assertTrue((submission / "build" / "main.pdf").exists())
        self.assertIn("runner lualatex", commands)
        self.assertIn("submission/demo-venue/build/main.pdf", result.stdout)
        self.assertIn(f"BIBINPUTS={target / 'submission' / 'demo-venue'}//:", commands)
        self.assertIn(f"{target / 'manuscript' / 'shared' / 'bib'}//:", commands)
        self.assertIn(f"BSTINPUTS={target / 'submission' / 'demo-venue'}//:", commands)
        self.assertIn(f"{target / 'manuscript' / 'shared' / 'style'}//:", commands)

    @staticmethod
    def to_bash_path(path: Path) -> str:
        text = path.as_posix()
        if len(text) >= 3 and text[1:3] == ":/":
            return f"/mnt/{text[0].lower()}/{text[3:]}"
        return text

    @staticmethod
    def write_fake_engine(path: Path, log: str) -> None:
        path.write_text(
            textwrap.dedent(
                f"""\
                #!/usr/bin/env bash
                set -euo pipefail
                echo "$(basename "$0") $*" >> "{log}"
                out="."
                for arg in "$@"; do
                  case "$arg" in
                    -output-directory=*) out="${{arg#-output-directory=}}" ;;
                  esac
                done
                mkdir -p "$out"
                touch "$out/main.aux" "$out/main.pdf"
                printf "fake log\\n" > "$out/main.log"
                """
            ),
            encoding="utf-8",
            newline="\n",
        )
        path.chmod(0o755)

    @staticmethod
    def write_fake_runner(path: Path, log: str) -> None:
        path.write_text(
            textwrap.dedent(
                f"""\
                #!/usr/bin/env bash
                set -euo pipefail
                echo "runner $*" >> "{log}"
                "$@"
                """
            ),
            encoding="utf-8",
            newline="\n",
        )
        path.chmod(0o755)

    @staticmethod
    def write_fake_bibtex(path: Path, log: str) -> None:
        path.write_text(
            textwrap.dedent(
                f"""\
                #!/usr/bin/env bash
                set -euo pipefail
                echo "bibtex $*" >> "{log}"
                echo "BIBINPUTS=${{BIBINPUTS:-}}" >> "{log}"
                echo "BSTINPUTS=${{BSTINPUTS:-}}" >> "{log}"
                touch main.bbl
                """
            ),
            encoding="utf-8",
            newline="\n",
        )
        path.chmod(0o755)


if __name__ == "__main__":
    unittest.main()
