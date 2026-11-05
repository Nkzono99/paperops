"""Light TeX reading: review comments (``%>``) and the paragraph outline.

This is a line-oriented reader, enough for manuscripts written in the scaffold's style
(sections in separate files, one blank line between paragraphs). It does not expand
macros.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

COMMENT_MARK = ">"  # a review comment is a TeX comment that starts with "%>"

_INPUT_RE = re.compile(r"\\(?:input|include|subfile)\{([^}]+)\}")
_HEADING_RE = re.compile(r"\\(section|subsection|subsubsection|paragraph)\*?\s*(?:\[[^\]]*\])?\{")
_BEGIN_RE = re.compile(r"\\begin\{([^}]+)\}")
_LABEL_RE = re.compile(r"\\label\{([^}]+)\}")
_STRUCTURAL_RE = re.compile(
    r"\\(?:label|maketitle|tableofcontents|bibliographystyle|bibliography|appendix|newpage"
    r"|clearpage|vspace\*?|smallskip|medskip|bigskip|noindent|centering|printbibliography)"
    r"(?:\[[^\]]*\])?(?:\{[^{}]*\})?"
)
_FLOAT_ENVS = {"figure", "figure*", "table", "table*"}
_SKIP_ENVS = {
    "equation",
    "equation*",
    "align",
    "align*",
    "gather",
    "gather*",
    "multline",
    "multline*",
    "eqnarray",
    "eqnarray*",
    "tabular",
    "tikzpicture",
    "thebibliography",
    "verbatim",
    "lstlisting",
}
_HEADING_LEVEL = {"section": 1, "subsection": 2, "subsubsection": 3, "paragraph": 4}
_ABBREVIATIONS = ("Fig.", "Figs.", "Eq.", "Eqs.", "Sec.", "Ref.", "Refs.", "e.g.", "i.e.", "al.")
_ABBREVIATIONS += ("vs.", "cf.", "approx.", "resp.", "Tab.")
_EN_SENTENCE_END = re.compile(r"[.!?](?=\s+[A-Z\\]|$)")


@dataclass(frozen=True)
class Line:
    file: Path
    lineno: int
    text: str  # with the TeX comment removed
    comment: str | None  # text after an unescaped %, or None


@dataclass(frozen=True)
class Comment:
    file: str
    line: int
    text: str
    target: str  # the manuscript text the comment is attached to


@dataclass(frozen=True)
class OutlineItem:
    kind: str  # heading | paragraph | float
    file: str
    line: int
    text: str  # heading title, first sentence, or first sentence of the caption
    level: int = 0  # heading level
    size: str = ""  # paragraph length, e.g. "312字" or "85 words"
    label: str = ""  # \label of a float

    def to_dict(self) -> dict:
        return asdict(self)


def split_comment(raw: str) -> tuple[str, str | None]:
    """Split a raw line at the first unescaped ``%``."""
    i = 0
    while True:
        i = raw.find("%", i)
        if i < 0:
            return raw, None
        backslashes = len(raw[:i]) - len(raw[:i].rstrip("\\"))
        if backslashes % 2 == 0:
            return raw[:i], raw[i + 1 :]
        i += 1


def read_lines(path: Path) -> list[Line]:
    lines = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        text, comment = split_comment(raw)
        lines.append(Line(path, number, text, comment))
    return lines


def expand(main: Path, _seen: frozenset[Path] = frozenset()) -> list[Line]:
    """Lines of ``main`` with ``\\input`` files inlined (resolved from the main directory)."""
    return _expand(main, main.parent, _seen)


def _expand(path: Path, base: Path, seen: frozenset[Path]) -> list[Line]:
    if path in seen or not path.is_file():
        return []
    out: list[Line] = []
    for line in read_lines(path):
        match = _INPUT_RE.search(line.text)
        if not match:
            out.append(line)
            continue
        target = base / match.group(1).strip()
        if not target.suffix:
            target = target.with_suffix(".tex")
        out.extend(_expand(target, base, seen | {path}))
    return out


def find_comments(files: list[Path], root: Path) -> list[Comment]:
    """Open review comments: ``%>`` lines (consecutive lines merge) and inline ``%>``."""
    found: list[Comment] = []
    for path in files:
        lines = read_lines(path)
        rel = str(path.relative_to(root))
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.comment is None or not line.comment.startswith(COMMENT_MARK):
                i += 1
                continue
            start = i
            parts = [line.comment[1:].strip()]
            if line.text.strip():  # inline comment: attached to its own line
                target = line.text.strip()
                i += 1
            else:
                i += 1
                while (
                    i < len(lines)
                    and not lines[i].text.strip()
                    and (lines[i].comment or "").startswith(COMMENT_MARK)
                ):
                    parts.append((lines[i].comment or "")[1:].strip())
                    i += 1
                target = next((ln.text.strip() for ln in lines[i:] if ln.text.strip()), "")
            found.append(
                Comment(rel, lines[start].lineno, " ".join(p for p in parts if p), _clip(target))
            )
    return found


def _clip(text: str, limit: int = 60) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _braced(text: str, open_at: int) -> str:
    """Content of the brace group that opens at ``text[open_at]``."""
    depth = 0
    for i in range(open_at, len(text)):
        if text[i] == "{" and (i == 0 or text[i - 1] != "\\"):
            depth += 1
        elif text[i] == "}" and text[i - 1] != "\\":
            depth -= 1
            if depth == 0:
                return text[open_at + 1 : i]
    return text[open_at + 1 :]


def _join(parts: list[str]) -> str:
    """Join source lines; Japanese text continues without a space."""
    out = ""
    for part in (p.strip() for p in parts):
        if not part:
            continue
        if out and (ord(out[-1]) < 128 or ord(part[0]) < 128):
            out += " "
        out += part
    return " ".join(out.split())


def first_sentence(text: str) -> str:
    ends = [i + 1 for i in (text.find("。"), text.find("．")) if i >= 0]
    for match in _EN_SENTENCE_END.finditer(text):
        if not text[: match.end()].endswith(_ABBREVIATIONS):
            ends.append(match.end())
            break
    return text[: min(ends)] if ends else text


def _size(text: str) -> str:
    compact = "".join(text.split())
    if not compact:
        return ""
    ascii_ratio = sum(ord(c) < 128 for c in compact) / len(compact)
    if ascii_ratio > 0.8:
        return f"{len(text.split())} words"
    return f"{len(compact)}字"


def outline(main: Path, root: Path) -> list[OutlineItem]:
    """Headings, the first sentence of each paragraph, and float captions, in order."""
    lines = expand(main)
    starts = [i for i, ln in enumerate(lines) if "\\begin{document}" in ln.text]
    if starts:
        lines = lines[starts[0] + 1 :]

    items: list[OutlineItem] = []
    paragraph: list[Line] = []

    def rel(line: Line) -> str:
        try:
            return str(line.file.relative_to(root))
        except ValueError:
            return str(line.file)

    def flush() -> None:
        if paragraph:
            text = _join([ln.text for ln in paragraph])
            first = paragraph[0]
            items.append(
                OutlineItem(
                    "paragraph", rel(first), first.lineno, first_sentence(text), 0, _size(text)
                )
            )
            paragraph.clear()

    i = 0
    while i < len(lines):
        line = lines[i]
        text = line.text
        if "\\end{document}" in text:
            break
        stripped = text.strip()
        if not stripped:
            if line.comment is None:  # a comment-only line does not end a paragraph
                flush()
            i += 1
            continue

        heading = _HEADING_RE.search(text)
        if heading:
            flush()
            title = _braced(text, heading.end() - 1)
            items.append(
                OutlineItem(
                    "heading", rel(line), line.lineno, title, _HEADING_LEVEL[heading.group(1)]
                )
            )
            i += 1
            continue

        begin = _BEGIN_RE.search(text)
        env = begin.group(1) if begin else ""
        if env == "abstract":
            flush()
            items.append(OutlineItem("heading", rel(line), line.lineno, "Abstract", 1))
            rest = text[begin.end() :] if begin else ""
            if rest.strip():
                paragraph.append(Line(line.file, line.lineno, rest, None))
            i += 1
            continue
        if env in _FLOAT_ENVS or env in _SKIP_ENVS:
            end_token = f"\\end{{{env}}}"
            block = [line]
            while end_token not in lines[i].text and i + 1 < len(lines):
                i += 1
                block.append(lines[i])
            i += 1
            if env in _FLOAT_ENVS:
                flush()
                body = _join([ln.text for ln in block])
                at = body.find("\\caption")
                caption = ""
                if at >= 0 and "{" in body[at:]:
                    caption = _braced(body, body.index("{", at))
                label = _LABEL_RE.search(body)
                items.append(
                    OutlineItem(
                        "float",
                        rel(line),
                        line.lineno,
                        first_sentence(_LABEL_RE.sub("", caption).strip()),
                        label=label.group(1) if label else "",
                    )
                )
            continue
        if "\\end{abstract}" in text:
            before = text.split("\\end{abstract}")[0]
            if before.strip():
                paragraph.append(Line(line.file, line.lineno, before, None))
            flush()
            i += 1
            continue

        content = _STRUCTURAL_RE.sub("", text)
        if content.strip():
            paragraph.append(Line(line.file, line.lineno, content, None))
        i += 1
    flush()
    return items


def render_outline(items: list[OutlineItem]) -> str:
    out: list[str] = []
    for item in items:
        if item.kind == "heading":
            indent = "  " * (item.level - 1)
            out.append(f"{indent}{'#' * item.level} {item.text}")
        elif item.kind == "float":
            label = f" {item.label}" if item.label else ""
            out.append(f"      [float{label}] {item.text}  ({item.file}:{item.line})")
        else:
            out.append(f"    - {item.text}  ({item.size}; {item.file}:{item.line})")
    return "\n".join(out)
