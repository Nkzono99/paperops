#!/usr/bin/env python3

import argparse
from pathlib import Path


def skill_names(root: Path, rel_dir: str) -> set[str]:
    base = root / rel_dir
    if not base.exists():
        return set()
    return {
        path.name
        for path in base.iterdir()
        if path.is_dir() and (path / "SKILL.md").exists()
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=".agents/skills が .claude/skills の互換入口として揃っているか検査する。"
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()

    root = args.root.resolve()
    claude_skills = skill_names(root, ".claude/skills")
    agent_skills = skill_names(root, ".agents/skills")

    errors: list[str] = []
    warnings: list[str] = []

    missing_agents = sorted(claude_skills - agent_skills)
    extra_agents = sorted(agent_skills - claude_skills)

    for name in missing_agents:
        errors.append(f"`.agents/skills/{name}/SKILL.md` がありません")
    for name in extra_agents:
        warnings.append(f"`.agents/skills/{name}/SKILL.md` は `.claude/skills/` に対応 skill がありません")

    for name in sorted(claude_skills & agent_skills):
        skill_path = root / ".agents" / "skills" / name / "SKILL.md"
        text = skill_path.read_text(encoding="utf-8")
        expected = f".claude/skills/{name}/SKILL.md"
        if expected not in text:
            errors.append(
                f"`.agents/skills/{name}/SKILL.md` が source of truth `{expected}` を参照していません"
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
        print(".agents と .claude の skill 対応に問題は見つかりませんでした。")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
