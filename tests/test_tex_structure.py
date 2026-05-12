from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "template" / "scripts" / "check-tex-structure.py"


class TexStructureTest(unittest.TestCase):
    def test_section_graphics_resolve_from_main_language_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lang = root / "manuscript" / "ja"
            section_dir = lang / "sections"
            figures = root / "manuscript" / "shared" / "figures"
            bib = root / "manuscript" / "shared" / "bib"
            style = root / "manuscript" / "shared" / "style" / "elsarticle"
            section_dir.mkdir(parents=True)
            figures.mkdir(parents=True)
            bib.mkdir(parents=True)
            style.mkdir(parents=True)

            (lang / "main.tex").write_text(
                "\n".join(
                    [
                        r"\documentclass{article}",
                        r"\begin{document}",
                        r"\input{sections/body}",
                        r"\bibliographystyle{elsarticle-num}",
                        r"\bibliography{references}",
                        r"\end{document}",
                    ]
                ),
                encoding="utf-8",
            )
            (section_dir / "body.tex").write_text(
                r"\includegraphics{../shared/figures/schematic}",
                encoding="utf-8",
            )
            (figures / "schematic.png").write_bytes(b"")
            (bib / "references.bib").write_text("", encoding="utf-8")
            (style / "elsarticle-num.bst").write_text("", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--root",
                    str(root),
                    "--main",
                    str(lang / "main.tex"),
                    "--label",
                    "test",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
