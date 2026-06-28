# Migration Guides

`paperops` の更新は二つに分けて扱う。

- `pops update-paperops --apply-chain`: 管理対象ハーネスファイルを checkpoint release ごとに更新する。
- `pops migrate list/show/apply`: 下流 project state を破壊的レイアウト変更へ合わせる。

最新 `pops` は古い project state をすべて直接理解し続けない。たとえば `v1.1 -> v1.4` へ更新する場合は、`v1.2.x`、`v1.3.x`、`v1.4.x` の checkpoint を順に踏み、`v1.1 -> v1.2` の migration は `v1.2.x` が提供する。`v1.3.x` 以降へ同じ migration handler を無期限に持ち越さない。

## Commands

```sh
uvx --from paper-harness-cli pops update-paperops --plan
uvx --from paper-harness-cli pops update-paperops --apply-chain

uvx --from paper-harness-cli pops migrate list
uvx --from paper-harness-cli pops migrate show M0-0001
uvx --from paper-harness-cli pops migrate apply M0-0001 --dry-run
uvx --from paper-harness-cli pops migrate apply M0-0001
uvx --from paper-harness-cli pops migrate show M0-0002
```

`--dry-run` で移動対象と conflict を確認してから apply する。CLI-backed migration は同じ project に複数回実行しても壊れないことを前提にする。判断が必要な migration は destructive handler にせず、`show` で手順を確認できる guide-backed item として扱う。

## Migration Item Format

各 item は `M<major>-<number>` の ID を持つ。

- `ID`: `M0-0001` のような一意 ID
- `Applies to`: 対象 checkpoint
- `Problem`: 旧状態の問題
- `Migration`: CLI で確認・適用する手順
- `Safety`: 上書き、削除、conflict、human gate の扱い
- `After migration`: update chain、確認コマンド、互換 layer の扱い

## Compatibility Horizon

- breaking layout change は migration item にする。
- 最新実装に legacy fallback を長く残さない。
- migration item がある release では、関連する fallback に deprecation note を付ける。
- 次 checkpoint 以降では、前 checkpoint の migration を chain 経由で踏むことを前提にし、最新 code から古い fallback を削る。
- migration guide にない破壊的変更を推測で実行しない。

## Planned Migration Candidates

- 現時点で確定した planned migration candidate はない。
- managed file を project fork として扱う detached fork manifest は `pops detach` / `pops reattach` として実装済みであり、既存 project は必要時に opt-in する。現時点では破壊的 state migration item として扱わない。

現在の migration item は [v0.md](v0.md) に置く。
