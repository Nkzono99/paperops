# Upgrade policy

`paperops` は `uvx --from paper-harness-cli pops ...` を標準実行経路にする。
これにより、最新の `pops` が過去すべての scaffold を直接理解し続けるのではなく、checkpoint release ごとの `pops` を exact version で呼び替える。

## 基本方針

- `.pops/manifest.toml` の `scaffold.version` を、最後に適用した scaffold artifact version として扱う。
- `pops update-paperops --plan` は、現在の scaffold version から target version までの upgrade chain を表示する。
- `pops update-paperops --apply-chain` は、各 checkpoint の `pops` を `uvx --from paper-harness-cli==<version>` で順に実行する。
- 下流 project state の破壊的変更は `pops migrate list/show/apply` の migration item として扱う。
- patch version は原則として踏まず、minor ごとの最新 patch を checkpoint とする。
- major version を跨ぐ chain は `--allow-major` が指定された場合だけ実行する。
- `apply-chain` の途中で changed managed files が見つかった場合、その step は停止し、`.pops/manifest.toml` の `scaffold.version` は進めない。意図的な project fork は `pops detach` で登録し、上書きしてよい変更だけ review 後に `--force` で進める。

## コマンド

```sh
uvx --from paper-harness-cli pops update-paperops --plan
uvx --from paper-harness-cli pops update-paperops --apply-chain
uvx --from paper-harness-cli pops update-paperops --target 0.3
uvx --from paper-harness-cli pops update-paperops --target latest --allow-major --apply-chain
```

内部的には、chain runner が次のような exact version step を呼ぶ:

```sh
uvx --from paper-harness-cli==0.2.5 pops update-paperops --upgrade-step --from-version 0.1.0 --to-version 0.2.5 --apply
uvx --from paper-harness-cli==0.3.4 pops update-paperops --upgrade-step --from-version 0.2.5 --to-version 0.3.4 --apply
```

`--upgrade-step` は内部用の実行入口であり、人間向けの通常導線では使わない。
この step は atomic に扱う。`--force` なしで changed managed files が残る場合、missing files だけを入れて version を進めるのではなく、適用前に失敗する。

## Manifest fields

`.pops/manifest.toml` は既存 key を保持しつつ、以下を記録する:

```toml
[scaffold]
package = "paper-harness-cli"
version = "0.4.2"
layout_version = "0.1"

[upgrade]
last_applied = "0.4.2"
last_checkpoint = "0.4"
chain_supported_since = "0.1.0"
```

`version` は配布 package の version、`layout_version` は scaffold layout の互換単位である。
将来、CLI だけの patch release と scaffold layout 変更を分ける必要が出た場合は、`layout_version` を migration 判断の主軸にする。

## Migration horizon

- 最新 `pops` に古い migration を無限に積み続けない。
- 各 checkpoint release は、直前 checkpoint から自分へ移行する migration を持つ。たとえば `v1.1 -> v1.2` の migration は `v1.2.x` が提供し、`v1.3.x` 以降へ同じ handler を引き継がない。
- chain 導入前の version からの移行だけは、最新側の bootstrap shim で一定期間救済する。
- checkpoint release は PyPI から削除しない。yank が必要な場合も、chain が切れない代替 release を先に用意する。

この方針により、後方互換性は「最新コードがすべての過去構造を理解すること」ではなく、「記録された version chain を順に適用できること」として扱う。

project-state migration の正本は [migrations/README.md](migrations/README.md) と各 major の guide に置く。CLI で定型化できるものだけ `pops migrate apply <id>` に実装し、判断が必要な migration は guide と skill で扱う。
