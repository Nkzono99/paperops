# GitHub Actions Node.js 24 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** paperopsが直接参照するGitHub公式JavaScript ActionをNode.js 24 runtimeのmajor tagへ統一する。

**Architecture:** workflowの公開interfaceやjob構造には触れず、`uses:`参照だけを一括更新する。repository全体を走査する静的回帰テストで旧majorの再混入を防ぎ、PyPI Trusted Publishingのmain到達性guardとpublish Actionを別assertionで保護する。

**Tech Stack:** GitHub Actions YAML、Python 3.11 `unittest`、KUDPC Slurm `tssrun`、GNU Make

## Global Constraints

- 更新先は`actions/checkout@v7`、`actions/setup-python@v6`、`actions/upload-artifact@v7`、`actions/download-artifact@v8`とする。
- `pypa/gh-action-pypi-publish@release/v1`は変更しない。
- workflow trigger、permissions、Python 3.12、artifact名/path、reusable workflow inputを変更しない。
- major tag追従を維持し、commit SHA固定へ変更しない。
- `CHANGELOG.md`の`Unreleased`へ記録し、v0.13.0節は変更しない。
- login nodeでテストを直接実行せず、SysB計算ノードへrouteする。
- userの明示指示なしにpushしない。GitHub-hosted runnerの実確認は次回push後に行う。

---

### Task 1: Direct Action runtime contract and workflow update

**Files:**

- Create: `tests/test_github_actions_runtime.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/publish-pypi.yml`
- Modify: `.github/workflows/reusable-build.yml`
- Modify: `.github/workflows/reusable-mirror-check.yml`
- Modify: `.github/workflows/reusable-release.yml`
- Modify: `CHANGELOG.md`

**Interfaces:**

- Consumes: `.github/workflows/*.yml`内の`uses: owner/action@ref`行。
- Produces: Node.js 24 major tagだけを直接参照するworkflow集合と、そのrepository-wide静的contract。

- [ ] **Step 1: Write the failing runtime contract test**

`tests/test_github_actions_runtime.py`を次の内容で作る。

```python
from __future__ import annotations

import re
import unittest
from pathlib import Path

from tests.helpers import ROOT


EXPECTED = {
    "actions/checkout": "v7",
    "actions/setup-python": "v6",
    "actions/upload-artifact": "v7",
    "actions/download-artifact": "v8",
}
ACTION = re.compile(r"uses:\s+(actions/(?:checkout|setup-python|upload-artifact|download-artifact))@(v\d+)")


class GitHubActionsRuntimeTest(unittest.TestCase):
    def test_direct_official_actions_use_node24_major_tags(self) -> None:
        seen: dict[str, set[str]] = {name: set() for name in EXPECTED}
        for workflow in sorted((ROOT / ".github/workflows").glob("*.yml")):
            for name, version in ACTION.findall(workflow.read_text(encoding="utf-8")):
                seen[name].add(version)

        self.assertEqual(seen, {name: {version} for name, version in EXPECTED.items()})

    def test_publish_boundary_is_unchanged(self) -> None:
        text = (ROOT / ".github/workflows/publish-pypi.yml").read_text(encoding="utf-8")
        self.assertIn("git merge-base --is-ancestor", text)
        self.assertIn("uses: pypa/gh-action-pypi-publish@release/v1", text)
        self.assertIn('python-version: "3.12"', text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run RED on a compute node**

Run:

```sh
tssrun -p gr20001b -t 0:10:0 --rsc p=1:t=4:c=4 \
  bash -lc 'module load SysB/2022 && cd /LARGE1/gr20001/b36291/Github/paperops && python3.11 -m unittest tests.test_github_actions_runtime -v'
```

Expected: `test_direct_official_actions_use_node24_major_tags` fails because the observed sets contain `v4` / `v5` instead of the four expected major tags。`test_publish_boundary_is_unchanged`はpassする。

- [ ] **Step 3: Update only direct Action references**

全workflowで次の置換だけを行う。

```text
actions/checkout@v4          -> actions/checkout@v7
actions/setup-python@v5      -> actions/setup-python@v6
actions/upload-artifact@v4   -> actions/upload-artifact@v7
actions/download-artifact@v4 -> actions/download-artifact@v8
```

`CHANGELOG.md`の`## Unreleased`直下へ次を追加する。

```markdown
- GitHub公式ActionをNode.js 24 runtimeのmajorへ更新した。`checkout@v7`、`setup-python@v6`、`upload-artifact@v7`、`download-artifact@v8`を全workflowで統一し、trigger、permissions、Python 3.12、artifact contract、PyPI Trusted Publishing境界は維持する。
```

- [ ] **Step 4: Run GREEN and workflow reference audit**

Run the focused test with the Step 2 command. Expected: 2 tests pass。

Then run:

```sh
rg -n 'actions/(checkout@v4|setup-python@v5|upload-artifact@v4|download-artifact@v4)' .github/workflows
```

Expected: no output and exit 1 because no deprecated direct reference remains。

- [ ] **Step 5: Run full verification on a compute node**

Run:

```sh
tssrun -p gr20001b -t 0:30:0 --rsc p=1:t=4:c=4 \
  bash -lc 'set -o pipefail; module load SysB/2022 && cd /LARGE1/gr20001/b36291/Github/paperops && make cli-smoke PYTHON=python3.11 && make smoke PYTHON=python3.11'
```

Expected: both Make targets exit 0。`make smoke`が`cli-smoke`を内包する場合も、planの明示gateとして両方のexitを確認する。

- [ ] **Step 6: Commit the implementation**

```sh
git add tests/test_github_actions_runtime.py .github/workflows/ci.yml \
  .github/workflows/publish-pypi.yml .github/workflows/reusable-build.yml \
  .github/workflows/reusable-mirror-check.yml .github/workflows/reusable-release.yml \
  CHANGELOG.md
git commit -m "Node.js廃止前に全workflowを公式Actionの新runtimeへ移す"
```

Expected: one implementation commit after the already committed design and plan documents。pushは行わない。

### Task 2: Final local review and live-check handoff

**Files:**

- Modify: none
- Test: repository status and committed workflow references

**Interfaces:**

- Consumes: Task 1のcommit。
- Produces: push前に確認可能なclean local branchと、次回push後の実環境確認項目。

- [ ] **Step 1: Verify committed state**

Run:

```sh
git diff --check HEAD^ HEAD
git status -sb
git show --stat --oneline HEAD
```

Expected: whitespace errorなし、tracked worktree clean、implementation commitに想定7 filesだけが含まれる。

- [ ] **Step 2: Record the post-push acceptance command**

次回明示的にpushした後、次を実行する。

```sh
run_id=$(gh run list --workflow ci.yml --branch main --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch "$run_id" --exit-status
gh run view "$run_id" --json status,conclusion,url
```

Expected: Smoke workflowが`success`で完了し、run annotationにNode.js 20廃止警告がない。これはlocal implementationをblockせず、push後の公開環境受入条件として残す。
