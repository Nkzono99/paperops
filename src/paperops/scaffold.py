"""``pops init`` and ``pops update``."""

from __future__ import annotations

import shutil
import subprocess
from importlib import resources
from pathlib import Path

from paperops.harness import deploy_skills, write_harness
from paperops.project import CONFIG_NAME, DEFAULT_SHARED_STYLE, PaperopsError, load_project

LANGS = ("ja", "en")
# Scaffold files stored under another name: git would read a nested ``.gitignore`` here,
# and the preamble and shared style are chosen or placed by ``pops init``.
_SPECIAL = {"gitignore", "STYLE.shared.md"}


def scaffold_source() -> Path:
    return Path(str(resources.files("paperops") / "_scaffold"))


def _toml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _source_name(path: Path, taken: set[str]) -> str:
    name = path.name.removeprefix("project_") or "source"
    base, n = name, 2
    while name in taken:
        name, n = f"{base}-{n}", n + 1
    taken.add(name)
    return name


def init_project(
    target: Path,
    *,
    title: str = "",
    lang: str = "ja",
    sources: list[Path] | None = None,
    shared_style: str = DEFAULT_SHARED_STYLE,
) -> list[str]:
    """Create a paper project in ``target``; existing files are kept as they are."""
    if lang not in LANGS:
        raise PaperopsError(f"--lang must be one of {', '.join(LANGS)}")
    target = target.resolve()
    if (target / CONFIG_NAME).exists():
        raise PaperopsError(f"{target} is already a paperops project; use `pops update`")
    source_paths = [p.expanduser().resolve() for p in sources or []]
    for path in source_paths:
        if not path.is_dir():
            raise PaperopsError(f"--source is not a directory: {path}")

    target.mkdir(parents=True, exist_ok=True)
    title = title or target.name
    report: list[str] = []
    src = scaffold_source()

    def place(rel: Path, text: str) -> None:
        dest = target / rel
        if dest.exists():
            report.append(f"kept     {rel}")
            return
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
        report.append(f"created  {rel}")

    for path in sorted(p for p in src.rglob("*") if p.is_file()):
        rel = path.relative_to(src)
        if "__pycache__" in rel.parts or rel.name in _SPECIAL:
            continue
        if rel.name.startswith("preamble."):
            if rel.name != f"preamble.{lang}.tex":
                continue
            rel = rel.with_name("preamble.tex")
        text = path.read_text(encoding="utf-8")
        if rel == Path(CONFIG_NAME):
            text = (
                text.replace("{{title}}", _toml_string(title))
                .replace("{{lang}}", _toml_string(lang))
                .replace("{{shared_style}}", _toml_string(shared_style))
            )
            taken: set[str] = set()
            for source in source_paths:
                text += (
                    f"\n[[sources]]\nname = {_toml_string(_source_name(source, taken))}\n"
                    f"path = {_toml_string(str(source))}\n"
                )
        place(rel, text)
    place(Path(".gitignore"), (src / "gitignore").read_text(encoding="utf-8"))

    if shared_style:
        shared = Path(shared_style).expanduser()
        if shared.exists():
            report.append(f"kept     {shared} (shared style)")
        else:
            try:
                shared.parent.mkdir(parents=True, exist_ok=True)
                shared.write_text(
                    (src / "STYLE.shared.md").read_text(encoding="utf-8"), encoding="utf-8"
                )
                report.append(f"created  {shared} (shared style)")
            except OSError as exc:
                report.append(f"warning  could not create shared style {shared}: {exc}")

    report += [f"wrote    {name}" for name in write_harness(target, title)]
    skills = deploy_skills(target)
    report.append(f"deployed {len(skills)} skills: {', '.join(skills)}")
    report.append(_git_init(target))
    return [line for line in report if line]


def _git_init(target: Path) -> str:
    """Start a git repository when there is none: revisions rely on git for history."""
    if not shutil.which("git"):
        return "warning  git not found; the manuscript history will not be recorded"
    inside = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=target,
        capture_output=True,
        text=True,
        check=False,
    )
    if inside.returncode == 0:
        return ""
    done = subprocess.run(["git", "init", "-q"], cwd=target, capture_output=True, check=False)
    return "created  git repository" if done.returncode == 0 else "warning  git init failed"


def update_project(start: Path | None = None) -> list[str]:
    """Refresh the managed AGENTS.md block and the skills; project files are left alone."""
    project = load_project(start)
    report = [f"wrote    {name}" for name in write_harness(project.root, project.title)]
    skills = deploy_skills(project.root)
    report.append(f"deployed {len(skills)} skills: {', '.join(skills)}")
    return report
