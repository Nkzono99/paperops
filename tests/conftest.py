from __future__ import annotations

from pathlib import Path

import pytest

from paperops.cli import main


@pytest.fixture
def paper(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A fresh paper project; the working directory is its root."""
    root = tmp_path / "paper-test"
    code = main(["init", str(root), "--style", str(tmp_path / "shared" / "STYLE.md")])
    assert code == 0
    monkeypatch.chdir(root)
    return root


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
