"""Template for a figure script. Copy this directory to figures/<name>/ and edit.

Run from anywhere:  .venv/bin/python figures/<name>/make.py [--refresh]
Writes <name>.pdf (for the manuscript) and <name>.png (for review) next to this file.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

# True while the result does not exist yet and the figure shows what is expected.
PREDICTED = False

HERE = Path(__file__).resolve().parent
DATA = HERE / "data" / ("predicted.npz" if PREDICTED else "reduced.npz")


def predict() -> None:
    """Write the expected data from a stated basis, so the author can inspect the reasoning.

    Use an estimate, a scaling law, or an extrapolation of existing runs; say which in figure.md.
    """
    x = np.linspace(0.0, 1.0, 50)
    np.savez(DATA, x=x, y=x**2)


def reduce() -> None:
    """Read the source runs once and keep only what the figure needs in data/.

    The figure can then be redrawn quickly, and it survives a purge of the run output.
    Heavy reads belong on a compute node.
    """
    # src = common.source("<source name>")
    # ... read from src / "runs/..." ...
    x = np.linspace(0.0, 1.0, 50)
    np.savez(DATA, x=x, y=x**2)


def draw() -> None:
    data = np.load(DATA)
    common.use_style()
    fig, ax = plt.subplots(figsize=(common.SINGLE, 2.4))
    ax.plot(data["x"], data["y"])
    ax.set_xlabel("x (unit)")
    ax.set_ylabel("y (unit)")
    if PREDICTED:
        common.mark_predicted(fig)
    common.save(fig, __file__)


if __name__ == "__main__":
    if not DATA.is_file() or "--refresh" in sys.argv:
        DATA.parent.mkdir(exist_ok=True)
        (predict if PREDICTED else reduce)()
    draw()
