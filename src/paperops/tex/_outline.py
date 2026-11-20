"""Extract the manuscript outline with a line-oriented TeX reader."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

from ._source import Line, expand

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
