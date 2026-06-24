from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


from tests.helpers import copy_template


class TemplateBuildFallbackTest(unittest.TestCase):
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
    def write_fake_bibtex(path: Path, log: str) -> None:
        path.write_text(
            textwrap.dedent(
                f"""\
                #!/usr/bin/env bash
                set -euo pipefail
                echo "bibtex $*" >> "{log}"
                touch main.bbl
                """
            ),
            encoding="utf-8",
            newline="\n",
        )
        path.chmod(0o755)


if __name__ == "__main__":
    unittest.main()
