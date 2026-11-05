"""Shared helpers for figure scripts: source paths, the paper style, and saving.

In ``figures/<name>/make.py``::

    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import common
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import to_hex, to_rgba_array  # noqa: E402
from matplotlib.text import Text  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FIGURES = ROOT / "figures"

# Figure widths in inches. Draw at the printed size so fonts and lines keep their size.
SINGLE = 3.4  # one column
DOUBLE = 7.0  # full width

# Colour of anything predicted in a figure (the same hue as \pred{} in the manuscript).
PRED_COLOR = "#d98200"


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
        color=PRED_COLOR,
        alpha=0.18,
        zorder=100,
    )


def message(figure_dir: Path) -> str:
    """The one-sentence message in ``figure.md``, or ``""`` while it is not written."""
    try:
        text = (figure_dir / "figure.md").read_text(encoding="utf-8")
    except OSError:
        return ""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    section = re.search(r"^## メッセージ[^\n]*\n(.*?)(?=^## |\Z)", text, flags=re.M | re.S)
    lines = section.group(1).splitlines() if section else []
    return next((line.strip() for line in lines if line.strip()), "")


def _hues(artists) -> set[str]:
    """Distinct non-gray colors: each one is something the reader has to tell apart."""
    found = set()
    for artist in artists:
        if hasattr(artist, "get_color"):
            colors = to_rgba_array(artist.get_color())
        else:
            face, edge = artist.get_facecolor(), artist.get_edgecolor()
            colors = [*to_rgba_array(face), *to_rgba_array(edge)]
        for r, g, b, a in colors:
            if a > 0 and max(r, g, b) - min(r, g, b) > 0.1:
                found.add(to_hex((r, g, b)))
    return found


def _is_cap(line) -> bool:
    """Error-bar caps are drawn as extra marker-only lines; they are not series."""
    return line.get_linestyle() == "None" and line.get_marker() in ("_", "|")


def load(fig) -> str:
    """What a reader has to take in, panel by panel. Call after the figure has been drawn.

    The review asks of each counted element whether the message can be read without it.
    """
    marks = [(ax, [*ax.images, *ax.collections]) for ax in fig.axes]
    colorbars = {m.colorbar.ax for _, ms in marks for m in ms if getattr(m, "colorbar", None)}
    panels = [ax for ax in fig.axes if ax not in colorbars and ax.get_visible()]
    texts = [t for t in fig.findobj(Text) if t.get_visible() and t.get_text().strip()]
    head = f"  {len(panels)} panel{'' if len(panels) == 1 else 's'}"
    if texts:
        head += f", smallest text {min(t.get_fontsize() for t in texts):.1f} pt"
    rows = [head]
    for index, ax in enumerate(panels, 1):
        lines = [ln for ln in ax.lines if not _is_cap(ln)]
        plain = [c for c in ax.collections if c.get_array() is None]
        mapped = [m for m in (*ax.images, *ax.collections) if getattr(m.get_array(), "size", 0)]
        legend = ax.get_legend()
        counts = {
            "lines": len(lines),
            "bars or patches": len(ax.patches),
            "point or band sets": len(plain),
            "color maps": len(mapped),
            "hues": len(_hues([*lines, *ax.patches, *plain])),
            "legend entries": len(legend.get_texts()) if legend else 0,
            "notes": sum(1 for t in ax.texts if t.get_text().strip()),
        }
        listed = ", ".join(f"{n} {kind}" for kind, n in counts.items() if n)
        rows.append(f"  panel {index}: {listed or 'empty'}")
    return "\n".join(rows)


def save(fig, script: str, dpi: int = 300) -> Path:
    """Write ``<name>.pdf`` for the manuscript and ``<name>.png`` for review, next to ``script``.

    Prints the message from ``figure.md`` next to what the figure asks the reader to take in,
    so the two can be compared when the PNG is reviewed.
    """
    out = Path(script).resolve().parent
    pdf = out / f"{out.name}.pdf"
    fig.savefig(pdf)
    fig.savefig(out / f"{out.name}.png", dpi=dpi)
    said = message(out) or "(no message in figure.md yet: write the design before drawing)"
    print(f"{out.name}: {said}\n{load(fig)}")
    plt.close(fig)
    return pdf
