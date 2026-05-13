---
id: H0001
record_type: hypothesis
created_at: '2026-05-13T18:25:03+09:00'
status: proposed
target_capability: agent-bridge update-harness distribution
source_eval_case: E0001
---

# H0001: E0001-fb0004-packaged-update-harness-skill-lacks-pypi-fallback-guidance の仮説

## 仮説

Packaged Codex and Claude hops-update-harness skill assets include the same PyPI uvx fallback wording used by other HarnessOps agent bridge assets.

## メカニズム

Align the generated hops-update-harness SKILL.md assets with the package-first execution path: when hops is not on PATH, agents are explicitly told to run uvx --from harnessops hops <command>.

## 最小実装

Patch the bundled codex and claude hops-update-harness skill templates to add the PATH/uvx fallback sentence, then run update-harness in a linked target repo and verify no .new diff removes that local guidance.

## 代替案: 削除または統合

Leave downstream repos to keep local-only wording and manually reject .new files, but that preserves repeated update friction and weakens generated asset trust.

## 期待される利点

Downstream target/project repositories can accept update-harness managed skill assets without losing correct PyPI execution guidance.

## 想定される欠点

If a repo intentionally wants no PyPI fallback guidance, the managed asset becomes slightly more prescriptive, but it matches documented package execution behavior.

## 評価計画

Run E0001 against a linked repo whose local hops-update-harness skill contains the uvx fallback line; after the asset patch, update-harness should not generate a .new file that removes the fallback wording.

## 中止基準

Reject or revise if the package runtime guarantees hops is always on PATH, or if update-harness conflict behavior is changed to preserve additive local guidance without changing packaged assets.
