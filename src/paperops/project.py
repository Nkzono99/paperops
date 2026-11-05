"""Paper project discovery and ``paper.toml`` loading."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_NAME = "paper.toml"
DEFAULT_SHARED_STYLE = "~/.config/paperops/STYLE.md"


class PaperopsError(Exception):
    """An error the user can act on; the CLI prints it without a traceback."""


@dataclass(frozen=True)
class Source:
    """A directory the paper draws results from, usually a runops project."""

    name: str
    path: Path
    note: str = ""

    @property
    def is_runops(self) -> bool:
        return (self.path / "runops.toml").is_file()


@dataclass(frozen=True)
class Project:
    root: Path
    title: str = ""
    lang: str = "ja"
    main: Path = Path("manuscript/main.tex")
    engine: str = "xelatex"
    bib: str = "bibtex"
    tex_bin: str = ""
    shared_style: Path | None = None
    sources: tuple[Source, ...] = field(default_factory=tuple)

    @property
    def manuscript_dir(self) -> Path:
        return self.root / "manuscript"

    @property
    def main_path(self) -> Path:
        return self.root / self.main


def find_root(start: Path | None = None) -> Path:
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / CONFIG_NAME).is_file():
            return candidate
    raise PaperopsError(
        f"no {CONFIG_NAME} found in {here} or its parents; run `pops init` to start a paper"
    )


def _table(data: dict, key: str) -> dict:
    value = data.get(key, {})
    if not isinstance(value, dict):
        raise PaperopsError(f"{CONFIG_NAME}: [{key}] must be a table")
    return value


def load_project(start: Path | None = None) -> Project:
    root = find_root(start)
    path = root / CONFIG_NAME
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise PaperopsError(f"{path}: {exc}") from exc

    paper = _table(data, "paper")
    build = _table(data, "build")
    style = _table(data, "style")

    sources = []
    for entry in data.get("sources", []):
        if not isinstance(entry, dict) or "path" not in entry:
            raise PaperopsError(f"{CONFIG_NAME}: each [[sources]] needs a path")
        src_path = Path(str(entry["path"])).expanduser()
        if not src_path.is_absolute():
            src_path = root / src_path
        sources.append(
            Source(
                name=str(entry.get("name") or src_path.name),
                path=src_path,
                note=str(entry.get("note", "")),
            )
        )

    shared = str(style.get("shared", DEFAULT_SHARED_STYLE)).strip()
    return Project(
        root=root,
        title=str(paper.get("title", "")),
        lang=str(paper.get("lang", "ja")),
        main=Path(str(paper.get("main", "manuscript/main.tex"))),
        engine=str(build.get("engine", "xelatex")),
        bib=str(build.get("bib", "bibtex")),
        tex_bin=str(build.get("tex_bin", "")),
        shared_style=Path(shared).expanduser() if shared else None,
        sources=tuple(sources),
    )
