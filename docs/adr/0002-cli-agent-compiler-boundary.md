# ADR 0002: CLI・Agent・compiler 境界

- Status: Accepted
- Decision ID: ADR-0002
- Parent: [RFC 0001: PaperOps 2](../rfcs/0001-paperops-2.md)

## Context

PaperOps 2 では、schema 検証や stale 判定のように同じ入力から同じ結果を得る処理と、story 選択や文章判断のように文脈依存の editorial work が連携する。これらを一つの `pops` command に隠すと、network、model、API key の有無で結果が変わり、承認されていない claim や story が原稿へ入る恐れがある。

compiler と Writer の境界も必要である。compiler が自由文を生成したり、Writer が packet 外の authority を読み替えたりすれば、typed state から原稿変更までの追跡可能性が失われる。

## Decision

CLI と checker は deterministic な機械処理を担当する。Agent/skill は代替案比較と editorial choice を担当する。compiler は承認済み typed input だけから限定された Writer packet を作る。Writer はその packet が許可した対象と操作だけを実行する。

CLI は Agent の判断を内部で暗黙実行しない。通常 command は network、model、API key を暗黙利用せず、外部サービスが必要な別 workflow は明示起動、入力・出力境界、失敗時の非更新を備える。

## Responsibility table

| Component | 責務 | 許可されないこと | Output |
|---|---|---|---|
| `pops` CLI | deterministic な validate、migrate、materialize、status 表示、atomic write の調停 | network/model/API key の暗黙利用、editorial choice の代行、Agent の暗黙実行 | 検証結果、明示 migration、状態表示、再生成可能 view |
| Agent / skill | story candidate の比較、選択・棄却理由、claim role、argument move、文章上の代替案を提案する | 承認なしに authority や manuscript を変更する、deterministic check を裁量で無効化する | human-reviewable proposal / approval request |
| compiler | 承認済み typed input と対象 revision を検証し、限定された Writer packet を deterministic に構成する | 新しい story/claim を創作する、未承認 input や local confidential data を packet に混ぜる | scoped Writer packet |
| Writer | Writer packet の対象 section、block ID、許可操作、claim scope に従って manuscript patch を作る | packet 外の story/claim scope を変更する、対象外 section を編集する、packet を authority として永続化する | reviewable manuscript patch |
| checker | schema、参照、mirror、quantity、figure、citation、authoring intent、hash/revision 整合性を deterministic に検査する | editorial quality を合否へ偽装する、失敗を legacy fallback で隠す | strict / advisory / diagnostic result |

## Writer packet contract

Writer packet は少なくとも入力 record ID と revision、dependency hash、対象 manuscript/section/block ID、許可操作、承認済み story/claim/move、引用可能な evidence reference、禁止範囲を持つ。packet は generated cache であり authority ではない。

compiler は input の承認状態、revision、dependency を検査し、不整合時には packet を部分生成しない。Writer は packet 外の story/claim scope を変更しない。追加判断が必要なら patch を拡張せず Agent/human へ差し戻す。

## Execution rules

1. Agent/skill が editorial proposal を作る。
2. human または将来定義される明示 approval record が typed state の変更を承認する。
3. CLI/checker が承認済み state と dependency を検証する。
4. compiler が限定 Writer packet を生成する。
5. 明示起動された Writer が reviewable patch を作る。
6. checker が patch と invariant を検証し、human が採否を決める。

いずれの段階も次段階を暗黙実行しない。特に validation command は Agent、compiler、Writer を連鎖起動しない。

## Consequences

- offline 環境でも CLI と checker の再現性を維持できる。
- editorial proposal、承認済み state、compiled packet、manuscript patch の provenance を分離できる。
- Agent の提案から原稿反映までに明示 checkpoint が増える。
- packet contract と scope checker の実装が必要になる。

## Revisit conditions

- 同一入力の CLI/checker 結果が network や model により変化する場合。
- compiler が未承認情報から story、claim、move を生成する必要が生じた場合。
- Writer が packet 外を変更しなければ主要 workflow を実行できない場合。
- packet から manuscript patch までの provenance を再現できない場合。
