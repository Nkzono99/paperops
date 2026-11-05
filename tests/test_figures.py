"""The figure helpers shipped in the scaffold. They need matplotlib, which paperops itself does not."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from .conftest import write

pytest.importorskip("matplotlib")
pytest.importorskip("numpy")

BUSY = """\
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common
import matplotlib.pyplot as plt
import numpy as np

common.use_style()
x = np.linspace(0.0, 1.0, 20)
fig, (left, right) = plt.subplots(1, 2, figsize=(common.DOUBLE, 2.4))
left.plot(x, x, color="#0072B2", label="rough")
left.plot(x, x**2, color="#D55E00", label="smooth")
left.plot(x, x**3, color="0.6")
left.axhline(0.5, color="0.8")
left.errorbar([0.2, 0.8], [0.3, 0.6], yerr=0.1, fmt="o", color="#0072B2", capsize=2)
left.legend()
left.text(0.1, 0.9, "(a)")
left.text(0.5, 0.1, "note", fontsize=5)
mesh = right.pcolormesh(np.outer(x, x))
fig.colorbar(mesh, ax=right)
common.save(fig, __file__)
"""


def make(paper: Path, name: str, script: str | None = None) -> str:
    target = paper / "figures" / name
    shutil.copytree(paper / "figures/_template", target)
    if script is not None:
        write(target / "make.py", script)
    done = subprocess.run(
        [sys.executable, str(target / "make.py")], capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, done.stderr
    assert (target / f"{name}.pdf").is_file() and (target / f"{name}.png").is_file()
    return done.stdout


def test_save_asks_for_the_design_when_figure_md_has_no_message(paper: Path) -> None:
    out = make(paper, "demo")
    assert out.startswith("demo: (no message in figure.md yet")
    assert "\n  1 panel, smallest text 7.0 pt\n" in out
    assert "\n  panel 1: 1 lines, 1 hues\n" in out


def test_save_prints_the_message_next_to_what_the_reader_takes_in(paper: Path) -> None:
    template = paper / "figures/_template/figure.md"
    text = template.read_text("utf-8").replace(
        "## 読者にさせる比較", "粗い壁の管は圧力損失が 3 倍大きい。\n\n## 読者にさせる比較"
    )
    template.write_text(text, encoding="utf-8")
    out = make(paper, "busy", BUSY)
    assert out.splitlines() == [
        "busy: 粗い壁の管は圧力損失が 3 倍大きい。",
        "  2 panels, smallest text 5.0 pt",
        # The error bar adds its marker line and one bar set; its caps and the colorbar are not counted.
        "  panel 1: 5 lines, 1 point or band sets, 2 hues, 2 legend entries, 2 notes",
        "  panel 2: 1 color maps",
    ]
