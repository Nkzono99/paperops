"""Build the PDF and summarize the LaTeX log."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from paperops.project import PaperopsError, Project

DVI_ENGINES = {"uplatex", "platex"}
MAX_PASSES = 4
_RERUN_RE = re.compile(r"Rerun to get|Label\(s\) may have changed|rerun LaTeX", re.IGNORECASE)
_REF_RE = re.compile(r"Reference `([^']+)' on page")
_CITE_RE = re.compile(r"Citation `([^']+)' on page")
_ERROR_RE = re.compile(r"^(?:\./)?([^\s:]+\.\w+):(\d+): (.+)$")
_PAGES_RE = re.compile(r"Output written on .*\((\d+) pages?")


@dataclass
class BuildResult:
    ok: bool
    pdf: Path | None = None
    log: Path | None = None
    pages: int | None = None
    errors: list[str] = field(default_factory=list)
    undefined_refs: list[str] = field(default_factory=list)
    undefined_cites: list[str] = field(default_factory=list)
    overfull: int = 0
    bib_messages: list[str] = field(default_factory=list)

    def render(self, root: Path) -> str:
        def rel(path: Path | None) -> str:
            return str(path.relative_to(root)) if path else "-"

        out = []
        if self.ok:
            pages = f" ({self.pages} pages)" if self.pages else ""
            out.append(f"built {rel(self.pdf)}{pages}")
        else:
            out.append(f"build failed; full log: {rel(self.log)}")
        out += [f"  error: {e}" for e in self.errors]
        if self.undefined_refs:
            out.append(f"  undefined references: {', '.join(self.undefined_refs)}")
        if self.undefined_cites:
            out.append(f"  undefined citations: {', '.join(self.undefined_cites)}")
        out += [f"  bib: {m}" for m in self.bib_messages]
        if self.overfull:
            out.append(f"  overfull hboxes: {self.overfull}")
        return "\n".join(out)


def _unwrap(log_text: str) -> list[str]:
    """Undo TeX's 79-column wrapping so warnings can be matched on one line."""
    lines: list[str] = []
    carry = ""
    for raw in log_text.splitlines():
        carry += raw
        if len(raw) == 79:
            continue
        lines.append(carry)
        carry = ""
    if carry:
        lines.append(carry)
    return lines


def parse_log(log_text: str) -> BuildResult:
    result = BuildResult(ok=True)
    lines = _unwrap(log_text)
    for i, line in enumerate(lines):
        error = _ERROR_RE.match(line)
        if error:
            result.errors.append(f"{error.group(1)}:{error.group(2)}: {error.group(3)}")
        elif line.startswith("! "):
            context = next((ln for ln in lines[i + 1 : i + 6] if ln.startswith("l.")), "")
            result.errors.append(f"{line[2:]} {context}".strip())
        elif line.startswith("Overfull \\hbox"):
            result.overfull += 1
        for regex, bucket in ((_REF_RE, result.undefined_refs), (_CITE_RE, result.undefined_cites)):
            match = regex.search(line)
            if match and "undefined" in line and match.group(1) not in bucket:
                bucket.append(match.group(1))
        pages = _PAGES_RE.search(line)
        if pages:
            result.pages = int(pages.group(1))
    return result


def _run(cmd: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )


def build(project: Project, main: Path | None = None) -> BuildResult:
    main_path = (project.root / main) if main else project.main_path
    if not main_path.is_file():
        raise PaperopsError(f"main file not found: {main_path}")
    workdir = main_path.parent
    job = main_path.stem
    try:
        sub = workdir.relative_to(project.manuscript_dir)
    except ValueError:
        sub = Path()
    outdir = project.root / "build" / sub
    outdir.mkdir(parents=True, exist_ok=True)
    for directory in workdir.rglob("*"):  # \include writes aux files into subdirectories
        if directory.is_dir():
            (outdir / directory.relative_to(workdir)).mkdir(parents=True, exist_ok=True)

    env = dict(os.environ)
    if project.tex_bin:
        env["PATH"] = f"{Path(project.tex_bin).expanduser()}{os.pathsep}{env.get('PATH', '')}"
    inputs = os.pathsep.join([str(workdir), str(project.manuscript_dir), ""])
    env["BIBINPUTS"] = inputs + env.get("BIBINPUTS", "")
    env["BSTINPUTS"] = inputs + env.get("BSTINPUTS", "")

    engine = project.engine
    if not shutil.which(engine, path=env["PATH"]):
        raise PaperopsError(
            f"TeX engine {engine!r} not found; set [build] engine or tex_bin in paper.toml"
        )
    tex_cmd = [
        engine,
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        f"-output-directory={outdir}",
        main_path.name,
    ]
    log_path = outdir / f"{job}.log"

    def tex_pass() -> BuildResult:
        proc = _run(tex_cmd, workdir, env)
        text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.is_file() else ""
        result = parse_log(text)
        result.log = log_path
        result.ok = proc.returncode == 0
        if not result.ok and not result.errors:
            tail = (proc.stdout or proc.stderr).strip().splitlines()[-1:]
            result.errors.append(tail[0] if tail else f"{engine} exited with {proc.returncode}")
        return result

    result = tex_pass()
    if not result.ok:
        return result

    bib_messages: list[str] = []
    aux = outdir / f"{job}.aux"
    aux_text = aux.read_text(encoding="utf-8", errors="replace") if aux.is_file() else ""
    bib_ran = False
    if project.bib == "biber" and (outdir / f"{job}.bcf").is_file():
        biber = ["biber", f"--input-directory={outdir}", f"--output-directory={outdir}", job]
        proc = _run(biber, workdir, env)
        bib_messages = [ln for ln in proc.stdout.splitlines() if ln.startswith(("WARN", "ERROR"))]
        bib_ran = True
    elif project.bib == "bibtex" and "\\bibdata" in aux_text and "\\citation{" in aux_text:
        proc = _run(["bibtex", job], outdir, env)
        bib_messages = [
            ln for ln in proc.stdout.splitlines() if ln.startswith(("Warning--", "I couldn't"))
        ]
        bib_ran = True

    # After a bibliography run LaTeX needs two more passes; otherwise rerun only on request.
    minimum = 2 if bib_ran else 0
    passes = 0
    while passes < MAX_PASSES:
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        if passes >= minimum and not _RERUN_RE.search(log_text):
            break
        result = tex_pass()
        passes += 1
        if not result.ok:
            return result

    if engine in DVI_ENGINES:
        proc = _run(["dvipdfmx", "-o", f"{job}.pdf", f"{job}.dvi"], outdir, env)
        if proc.returncode != 0:
            result.ok = False
            result.errors.append(f"dvipdfmx failed: {proc.stderr.strip().splitlines()[-1:]}")
            return result

    result.pdf = outdir / f"{job}.pdf"
    result.bib_messages = bib_messages
    if not result.pdf.is_file():
        result.ok = False
        result.errors.append("the engine finished without writing a PDF")
    return result
