# トラブルシューティング

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
