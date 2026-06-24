# トラブルシューティング

## Skill context budget warning

Codex が次の warning を出すことがある:

```text
Skill descriptions were shortened to fit the 2% skills context budget.
```

これは skill 本体が読めないという意味ではなく、一覧に表示される description が短縮されたという通知である。通常執筆では、paperops の project-local skill を優先し、GitHub / Slack / Gmail / HPC / 解析系 plugin は必要になった時だけ有効化する。

目安:

- 通常執筆: paperops の原稿、引用、査読、同期 skill を優先する。
- GitHub issue / release 作業: GitHub plugin を有効にする。
- HPC / 解析作業: 解析 project 側で必要な plugin だけを有効にする。

warning が出ても作業は継続できる。入口選択が曖昧になった場合は、`AGENTS.md` の主要 skill 一覧を読み、必要な skill の `SKILL.md` を直接開いてから進める。

## nested private paper repo

解析リポジトリや working リポジトリの配下に、この paper repo を private repo として nested clone する運用では、親 repo と paper repo の `.git` が混ざりやすい。

git 操作の前に、必ず対象 repo を確認する:

```sh
git rev-parse --show-toplevel
git remote -v
git status --short
```

親 repo 側から操作する必要がある場合は、対象を明示する:

```sh
git -C path/to/paper-repo status --short
git -C path/to/paper-repo diff
```

親 repo、working repo、paper repo の変更を同じ commit に混ぜない。特に論文本文、解析コード、生成 output は、それぞれの repo の責務に合わせて分ける。

## Windows の dubious ownership

Windows や removable drive では、`git status` が dubious ownership で止まることがある。この場合、まず per-command の `safe.directory` を使い、対象 repo だけを明示する:

```powershell
git -c safe.directory="C:/path/to/paper-repo" -C "C:/path/to/paper-repo" status --short
```

`git config --global --add safe.directory ...` は共有設定を変えるため、必要性を確認してから使う。広すぎる `safe.directory=*` は避ける。
