#!/usr/bin/env python3

import argparse
import re
from pathlib import Path


CONCRETE_CLAUDE_SKILL_REF_RE = re.compile(r"\.claude/skills/[A-Za-z0-9_.-]+/")


def skill_names(root: Path, rel_dir: str) -> set[str]:
    base = root / rel_dir
    if not base.exists():
        return set()
    return {
        path.name
        for path in base.iterdir()
        if path.is_dir() and (path / "SKILL.md").exists()
    }


def frontmatter_fields(path: Path) -> tuple[dict[str, str], str | None]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, "frontmatter がありません"
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, "frontmatter が閉じていません"
    fields: dict[str, str] = {}
    for line in parts[1].splitlines():
        if not line or line.startswith(" ") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"')
    return fields, None


def validate_skill_frontmatter(root: Path, rel_dir: str, names: set[str]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    for name in sorted(names):
        skill_path = root / rel_dir / name / "SKILL.md"
        rel_path = skill_path.relative_to(root)
        fields, parse_error = frontmatter_fields(skill_path)
        if parse_error is not None:
            errors.append(f"`{rel_path}` の {parse_error}")
            continue
        actual_name = fields.get("name", "")
        if actual_name != name:
            errors.append(
                f"`{rel_path}` の frontmatter name `{actual_name}` が directory name `{name}` と一致しません"
            )
        if not fields.get("description"):
            warnings.append(f"`{rel_path}` の frontmatter description が未記入です")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(
        description=".claude/skills が .agents/skills の Claude Code 互換入口として揃っているか検査する。"
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()

    root = args.root.resolve()
    claude_skills = skill_names(root, ".claude/skills")
    agent_skills = skill_names(root, ".agents/skills")

    errors: list[str] = []
    warnings: list[str] = []

    missing_claude = sorted(agent_skills - claude_skills)
    extra_claude = sorted(claude_skills - agent_skills)

    for name in missing_claude:
        errors.append(f"`.claude/skills/{name}/SKILL.md` がありません")
    for name in extra_claude:
        warnings.append(f"`.claude/skills/{name}/SKILL.md` は `.agents/skills/` に対応 skill がありません")

    for rel_dir, names in [
        (".agents/skills", agent_skills),
        (".claude/skills", claude_skills),
    ]:
        frontmatter_errors, frontmatter_warnings = validate_skill_frontmatter(root, rel_dir, names)
        errors.extend(frontmatter_errors)
        warnings.extend(frontmatter_warnings)

    for name in sorted(claude_skills & agent_skills):
        agent_path = root / ".agents" / "skills" / name / "SKILL.md"
        skill_path = root / ".claude" / "skills" / name / "SKILL.md"
        agent_fields, agent_parse_error = frontmatter_fields(agent_path)
        wrapper_fields, wrapper_parse_error = frontmatter_fields(skill_path)
        if agent_parse_error is None and wrapper_parse_error is None:
            for field in ["name", "description"]:
                if agent_fields.get(field, "") != wrapper_fields.get(field, ""):
                    errors.append(
                        f"`.claude/skills/{name}/SKILL.md` の frontmatter {field} が "
                        f"`.agents/skills/{name}/SKILL.md` と一致しません"
                    )

        text = skill_path.read_text(encoding="utf-8")
        expected = f"@${{CLAUDE_SKILL_DIR}}/../../../.agents/skills/{name}/SKILL.md"
        if expected not in text:
            errors.append(
                f"`.claude/skills/{name}/SKILL.md` が source of truth `{expected}` を参照していません"
            )
        cwd_relative = f"@.agents/skills/{name}/SKILL.md"
        if cwd_relative in text:
            errors.append(
                f"`.claude/skills/{name}/SKILL.md` が cwd 依存の参照 `{cwd_relative}` を使っています"
            )

    for name in sorted(agent_skills):
        agent_path = root / ".agents" / "skills" / name / "SKILL.md"
        text = agent_path.read_text(encoding="utf-8")
        if CONCRETE_CLAUDE_SKILL_REF_RE.search(text):
            errors.append(
                f"`.agents/skills/{name}/SKILL.md` が `.claude/skills/` 配下を参照しています。"
                "helper は `.agents` 側か scripts/ を source of truth にしてください"
            )

    print("# skill-mirror-check")
    print("")
    if errors:
        print("## Errors")
        for error in errors:
            print(f"- {error}")
        print("")
    if warnings:
        print("## Warnings")
        for warning in warnings:
            print(f"- {warning}")
        print("")
    if not errors and not warnings:
        print(".agents source と .claude 互換入口の対応に問題は見つかりませんでした。")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
