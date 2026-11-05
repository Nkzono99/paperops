"""``pops``: init, update, context, outline, build."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from paperops import __version__
from paperops.project import DEFAULT_SHARED_STYLE, PaperopsError, load_project


def _init(args: argparse.Namespace) -> int:
    from paperops.scaffold import init_project

    target = Path(args.dir)
    report = init_project(
        target,
        title=args.title,
        lang=args.lang,
        sources=[Path(p) for p in args.source],
        shared_style=args.style,
    )
    print("\n".join(report))
    print(
        f"\nNext: start Codex or Claude Code in {target.resolve()} and say what the paper "
        "should show."
    )
    return 0


def _update(args: argparse.Namespace) -> int:
    from paperops.scaffold import update_project

    print("\n".join(update_project()))
    return 0


def _context(args: argparse.Namespace) -> int:
    from paperops.context import gather, render

    state = gather(load_project())
    print(json.dumps(state, ensure_ascii=False, indent=2) if args.json else render(state))
    return 0


def _outline(args: argparse.Namespace) -> int:
    from paperops.tex import outline, render_outline

    project = load_project()
    main = project.root / args.main if args.main else project.main_path
    if not main.is_file():
        raise PaperopsError(f"main file not found: {main}")
    items = outline(main, project.root)
    if args.json:
        print(json.dumps([item.to_dict() for item in items], ensure_ascii=False, indent=2))
    else:
        print(render_outline(items))
    return 0


def _build(args: argparse.Namespace) -> int:
    from paperops.build import build

    project = load_project()
    result = build(project, Path(args.main) if args.main else None)
    print(result.render(project.root))
    return 0 if result.ok else 1


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pops", description="Minimal harness for writing a paper with AI agents."
    )
    parser.add_argument("--version", action="version", version=f"paperops {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="create a paper project")
    init.add_argument("dir", nargs="?", default=".")
    init.add_argument("--title", default="", help="working title (default: directory name)")
    init.add_argument("--lang", default="ja", help="language the draft is written in: ja or en")
    init.add_argument(
        "--source",
        action="append",
        default=[],
        metavar="DIR",
        help="a runops project or other directory with the results; repeatable",
    )
    init.add_argument(
        "--style",
        default=DEFAULT_SHARED_STYLE,
        metavar="FILE",
        help=f"style file shared across papers (default: {DEFAULT_SHARED_STYLE})",
    )
    init.set_defaults(func=_init)

    update = sub.add_parser("update", help="refresh the AGENTS.md block and the skills")
    update.set_defaults(func=_update)

    context = sub.add_parser("context", help="show where the paper stands")
    context.add_argument("--json", action="store_true")
    context.set_defaults(func=_context)

    outline = sub.add_parser("outline", help="headings and the first sentence of each paragraph")
    outline.add_argument("--main", default="", metavar="PATH", help="another main file")
    outline.add_argument("--json", action="store_true")
    outline.set_defaults(func=_outline)

    build = sub.add_parser("build", help="build the PDF and summarize the log")
    build.add_argument("--main", default="", metavar="PATH", help="another main file")
    build.set_defaults(func=_build)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except PaperopsError as exc:
        print(f"pops: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
