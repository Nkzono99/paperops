"""Read TeX source, review comments, and manuscript outlines."""

from ._outline import OutlineItem, first_sentence, outline, render_outline
from ._source import COMMENT_MARK, Comment, Line, expand, find_comments, read_lines, split_comment

__all__ = [
    "COMMENT_MARK",
    "Comment",
    "Line",
    "OutlineItem",
    "expand",
    "find_comments",
    "first_sentence",
    "outline",
    "read_lines",
    "render_outline",
    "split_comment",
]
