# ADR 0003: Revision・state・hash

- Status: Accepted
- Decision ID: ADR-0003
- Parent: [RFC 0001: PaperOps 2](../rfcs/0001-paperops-2.md)

## Context

単一の進捗 state に編集、review、submission の状態を詰め込むと、一つの変更が無関係な対象を stale にし、UI 表示と machine validation が競合する。ファイル全体の更新時刻や生成文を hash に含める方法も、semantic change でない差分を revision と誤認する。逆に依存関係を hash へ含めなければ、参照先の claim や evidence が変わっても downstream packet を有効と判断してしまう。

## Decision

macro state、object revision、section state、review round、submission axis を直交状態として定義する。一つの axis の遷移は、規則で明示されない限り他 axis を暗黙変更しない。

| Axis | 意味 | 例 | 更新主体 |
|---|---|---|---|
| macro state | workflow 全体を要約する UI / orchestration 状態 | setup、researching、drafting、reviewing | deterministic projection または明示 workflow command |
| object revision | stable ID を持つ typed object の semantic version | story `S-01` revision 3 | authority record の単一 writer |
| section state | manuscript section/block の editorial lifecycle | planned、drafted、verified、stale | section transition command / checker |
| review round | reviewer feedback と response の反復単位 | internal-1、reviewer-2 | review workflow |
| submission axis | living manuscript から immutable submission への履歴 | target、submitted、revised、accepted | publication workflow |

macro state は他の axis を要約表示できるが、それらの authority にはならない。object revision の増加だけで review round や submission axis を進めない。submission snapshot は参照した object revision と section state を固定する。

## Canonical hash boundary

canonical hash の対象は、schema により型付けされ正規化済みの semantic field とする。具体的には安定 ID、schema version、意味を持つ scalar、順序が意味を持つ list、キー順を正規化した mapping、明示された参照を含む。空白、表現形式、mapping の記述順の違いは正規化後に同じ意味なら同一入力とする。

canonical hash からは timestamp、local path、generated text、cache metadata、実行 host、credential、表示専用 field を除外する。除外 field の変更だけでは object revision や selective stale を更新しない。除外は private/raw 情報を hash material へ混入させない境界でもある。

hash algorithm、serialization、normalization profile はこの ADR では選ばない。P1 で algorithm と canonicalization version を version 付き識別子として固定し、hash 値とともに保存する。algorithm 更新は同じ semantic revision の再計算と意味変更を区別できなければならない。

## Dependency hash

dependency hash は、対象 object が意味上参照する各 dependency の参照 ID と参照 object revision または canonical hash から構成する。集合の順序が意味を持たない場合は参照 ID で正規化し、意味を持つ場合は schema が順序を宣言する。

dependency の追加、削除、参照 revision/hash の変化は downstream object、Writer packet、または manuscript block の selective stale 判定に使う。timestamp や local path の変化だけでは dependency hash を変えない。dependency hash 自体の algorithm/version も P1 で canonical hash と整合する形に固定する。

## Transition rules

- semantic field の承認済み変更は object revision を進め、新しい canonical hash を記録する。
- dependency hash の変化は影響を受ける section/block だけを stale 候補とし、macro state 全体を無条件に巻き戻さない。
- review round は feedback set ごとに独立し、原稿変更だけで新 round を暗黙作成しない。
- submission axis の遷移は immutable snapshot 作成を伴い、living manuscript の section state を凍結しない。
- migration は旧 revision/hash と新 revision/hash の対応を検証し、不一致時には部分更新しない。

## Consequences

- UI の進捗、object の変更、section の stale、review 履歴、submission 履歴を個別に説明できる。
- claim・move・block 単位の selective stale を dependency に基づいて判断できる。
- canonicalization と dependency graph の versioned implementation が P1 で必要になる。
- timestamp による簡易 invalidation は authority 判定に使えなくなる。

## Revisit conditions

- 直交 axis の一つが別 axis の状態を重複して authority として保持する場合。
- semantic field でない変更が revision や stale を恒常的に発生させる場合。
- dependency 変更が関連 block を stale にできない、または無関係な全 block を stale にする場合。
- hash algorithm/version を見ずに hash 値を比較する実装が導入された場合。
