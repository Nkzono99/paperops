#!/usr/bin/env python3
"""Detect suspiciously thin Results and Discussion sections."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_SECTION_DEPTH = {
    "length_is_floor_not_target": True,
    "profile": "full_article",
    "soft_floor": {
        "full_article": {
            "results": {"ja_chars": 2400, "en_words": 900, "min_paragraphs": 6},
            "discussion": {"ja_chars": 2000, "en_words": 750, "min_paragraphs": 5},
        },
        "short_article": {
            "results": {"ja_chars": 1200, "en_words": 450, "min_paragraphs": 3},
            "discussion": {"ja_chars": 1000, "en_words": 350, "min_paragraphs": 3},
        },
    },
    "subsection_policy": {
        "min_paragraphs_per_subsection": 2,
    },
}

SECTION_FILES = {
    "results": "30_results.tex",
    "discussion": "40_discussion.tex",
}
LANGUAGE_LABELS = {
    "ja": ("日本語文字数", "ja_chars"),
    "en": ("English word count", "en_words"),
}
WORD_RE = re.compile(r"[A-Za-z]+(?:[-'][A-Za-z]+)*|\d+(?:\.\d+)?")
DROP_COMMAND_WITH_ARG_RE = re.compile(
    r"\\(?:section|subsection|subsubsection|paragraph|caption|label|ref|eqref|cite|citep|citet|citealp|includegraphics|input|include|bibliography)\*?(?:\[[^\]]*\])?\{[^{}]*\}",
    re.DOTALL,
)


@dataclass
class Finding:
    severity: str
    message: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def load_profile(root: Path) -> dict[str, Any]:
    path = root / "manuscript" / "writing-profile.yml"
    if not path.exists():
        return {}
    try:
        import yaml  # type: ignore[import-not-found]

        data = yaml.safe_load(read_text(path))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def section_depth_config(root: Path) -> dict[str, Any]:
    profile = load_profile(root)
    configured = profile.get("section_depth")
    if not isinstance(configured, dict):
        return DEFAULT_SECTION_DEPTH
    merged = {
        "length_is_floor_not_target": configured.get(
            "length_is_floor_not_target", DEFAULT_SECTION_DEPTH["length_is_floor_not_target"]
        ),
        "profile": configured.get("profile", DEFAULT_SECTION_DEPTH["profile"]),
        "soft_floor": deep_merge_dicts(DEFAULT_SECTION_DEPTH["soft_floor"], configured.get("soft_floor", {})),
        "subsection_policy": dict(DEFAULT_SECTION_DEPTH["subsection_policy"]),
    }
    subsection_policy = configured.get("subsection_policy")
    if isinstance(subsection_policy, dict):
        merged["subsection_policy"].update(subsection_policy)
    return merged


def deep_merge_dicts(base: Any, override: Any) -> Any:
    if not isinstance(base, dict):
        return override if isinstance(override, dict) else base
    merged = dict(base)
    if not isinstance(override, dict):
        return merged
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def strip_tex_comments(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        chars: list[str] = []
        escaped = False
        for char in line:
            if char == "%" and not escaped:
                break
            chars.append(char)
            escaped = char == "\\" and not escaped
            if char != "\\":
                escaped = False
        lines.append("".join(chars))
    return "\n".join(lines)


def strip_tex_noise(text: str) -> str:
    text = strip_tex_comments(text)
    text = re.sub(r"\\\[(.*?)\\\]|\\\((.*?)\\\)|\$(.*?)\$", " ", text, flags=re.DOTALL)
    text = DROP_COMMAND_WITH_ARG_RE.sub(" ", text)
    text = re.sub(r"\\(?:begin|end)\{[^{}]*\}", " ", text)
    text = re.sub(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?", " ", text)
    text = re.sub(r"[{}_^~&$#]", " ", text)
    return text


def count_japanese_units(text: str) -> int:
    cleaned = strip_tex_noise(text)
    return sum(1 for char in cleaned if char.isalnum())


def count_english_words(text: str) -> int:
    cleaned = strip_tex_noise(text)
    return len(WORD_RE.findall(cleaned))


def paragraph_count(text: str) -> int:
    cleaned = strip_tex_noise(text)
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", cleaned) if part.strip()]
    return len(paragraphs)


def subsection_paragraph_counts(text: str) -> list[int]:
    parts = re.split(r"\\sub(?:sub)?section\*?(?:\[[^\]]*\])?\{[^{}]*\}", text)
    if len(parts) <= 1:
        return []
    return [paragraph_count(part) for part in parts[1:] if strip_tex_noise(part).strip()]


def floor_for(config: dict[str, Any], section: str) -> dict[str, int]:
    profile_name = str(config.get("profile", "full_article"))
    floor_profiles = config.get("soft_floor", {})
    if not isinstance(floor_profiles, dict):
        return {}
    floor = floor_profiles.get(profile_name) or floor_profiles.get("full_article") or {}
    if not isinstance(floor, dict):
        return {}
    section_floor = floor.get(section, {})
    if not isinstance(section_floor, dict):
        return {}
    return {
        str(key): int(value)
        for key, value in section_floor.items()
        if isinstance(value, int) and not isinstance(value, bool)
    }


def check(root: Path, strict: bool) -> list[Finding]:
    findings: list[Finding] = []
    config = section_depth_config(root)
    subsection_policy = config.get("subsection_policy", {})
    min_paragraphs_per_subsection = 2
    if isinstance(subsection_policy, dict) and isinstance(subsection_policy.get("min_paragraphs_per_subsection"), int):
        min_paragraphs_per_subsection = int(subsection_policy["min_paragraphs_per_subsection"])

    for section, filename in SECTION_FILES.items():
        section_floor = floor_for(config, section)
        for language, (label, floor_key) in LANGUAGE_LABELS.items():
            path = root / "manuscript" / language / "sections" / filename
            if not path.exists():
                continue
            rel_path = path.relative_to(root).as_posix()
            text = read_text(path)
            actual = count_japanese_units(text) if language == "ja" else count_english_words(text)
            expected = section_floor.get(floor_key, 0)
            severity = "error" if strict else "warning"
            if expected and actual < expected:
                findings.append(
                    Finding(
                        severity,
                        f"`{rel_path}` の {label} {actual} が soft floor {expected} を下回っています。"
                        " Results / Discussion の薄さは section-depth blocker として、"
                        "missing evidence, interpretation, comparison, boundary, or reader-facing explanation を補ってください。",
                    )
                )
            min_paragraphs = section_floor.get("min_paragraphs", 0)
            actual_paragraphs = paragraph_count(text)
            if min_paragraphs and actual_paragraphs < min_paragraphs:
                findings.append(
                    Finding(
                        severity,
                        f"`{rel_path}` の paragraph count {actual_paragraphs} が soft floor {min_paragraphs} を下回っています。",
                    )
                )
            for index, count in enumerate(subsection_paragraph_counts(text), start=1):
                if count < min_paragraphs_per_subsection:
                    findings.append(
                        Finding(
                            severity,
                            f"`{rel_path}` の subsection {index} が {count} paragraph だけです。短い subsection は統合するか、reader question を展開してください。",
                        )
                    )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Results / Discussion の section-depth floor を確認する。")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    findings = check(root, strict=args.strict)
    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]

    print("# section-depth-check")
    print("")
    if errors:
        print("## Errors")
        for finding in errors:
            print(f"- {finding.message}")
        print("")
    if warnings:
        print("## Warnings")
        for finding in warnings:
            print(f"- {finding.message}")
        print("")
    if not findings:
        print("Results / Discussion section depth の suspiciously thin floor は満たしています。")
    if findings:
        print("Length is a floor, not a target. Do not pad; expand only by adding missing scientific content.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
