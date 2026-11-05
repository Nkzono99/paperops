"""Shared helpers for figure scripts: source paths, the paper style, and saving.

In ``figures/<name>/make.py``::

    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import common
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FIGURES = ROOT / "figures"

# Figure widths in inches. Draw at the printed size so fonts and lines keep their size.
SINGLE = 3.4  # one column
DOUBLE = 7.0  # full width


def source(name: str) -> Path:
    """Root directory of a source named in paper.toml."""
    config = tomllib.loads((ROOT / "paper.toml").read_text(encoding="utf-8"))
    for entry in config.get("sources", []):
        path = Path(str(entry["path"])).expanduser()
        if entry.get("name", path.name) == name:
            return path if path.is_absolute() else ROOT / path
    raise KeyError(f"no source named {name!r} in paper.toml")


def use_style() -> None:
    plt.style.use(FIGURES / "paper.mplstyle")


def mark_predicted(fig) -> None:
    """Stamp a figure that is drawn from an expectation, not from results."""
    fig.text(
        0.5,
        0.5,
        "PREDICTED",
        ha="center",
        va="center",
        rotation=30,
        fontsize=22,
        fontweight="bold",
        color="#d98200",
        alpha=0.18,
        zorder=100,
    )


def save(fig, script: str, dpi: int = 300) -> Path:
    """Write ``<name>.pdf`` for the manuscript and ``<name>.png`` for review, next to ``script``."""
    out = Path(script).resolve().parent
    pdf = out / f"{out.name}.pdf"
    fig.savefig(pdf)
    fig.savefig(out / f"{out.name}.png", dpi=dpi)
    plt.close(fig)
    return pdf
