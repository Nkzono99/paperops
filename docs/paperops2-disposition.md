# PaperOps 2 現行資産 disposition matrix

この文書は [RFC 0001](rfcs/0001-paperops-2.md)、[ADR 0001](adr/0001-authority-ownership-layout.md)、[ADR 0002](adr/0002-cli-agent-compiler-boundary.md)、[ADR 0003](adr/0003-revision-state-hash.md) の authority class、単一 writer、CLI / Agent / compiler 境界、revision / hash 境界を現行資産へ適用する。各行は P1–P7 の実装計画で再確認する移行判断であり、この表だけで authority を切り替えない。

disposition の語彙は次のとおりである。`retain` は責務と入口を維持、`adapt` は入口を保って新 contract へ適合、`redirect` は互換入口を新正本へ転送、`deprecate` は利用観測と移行期間を設けて新規利用を止める、`remove` は検証済みの削除条件を満たした別変更だけで実行、`investigate` は責務または移行先が未確定で理由付き調査を要求する。本サイクルに `remove` の実行対象はない。

P1 は schema・canonical hash・migration 基盤、P2–P3 は story / claim / evidence の typed authority、P4–P5 は compiler / Writer packet と manuscript patch、P6 は review / submission snapshot、P7 は既定化と legacy removal 判定を指す。段階導入中は legacy-authoritative → shadow → opt-in v2-authoritative → default v2-authoritative の gate を順守する。

checker inventory は、名前が `check-` で始まるかにかかわらず、deterministic gate として Makefile から起動される Python entrypoint を個別 asset として含める。release/package gate も含める一方、test runner、collector、migration utility、build helper は、それ自体が deterministic gate でない限り checker に分類しない。

## 受信フィードバックの統合判断

2026-07-11 時点の open feedback は、独立した leaf skill / checker を増やすのではなく、次の既存実装または PaperOps 2 の責務へ統合する。`absorbed` は機能の放棄ではなく、Issue を閉じてこの設計とローカル実装計画を追跡正本にすることを意味する。

| Issue | 判断 | 統合先 | 完了条件 |
|---|---|---|---|
| #72 Methods の local tool 語 | absorbed | P3 Writer packet の public-language contract と P5 public terminology gate。既存 `public-terminology-pass` / `public-terms-check` を適合する | 公開 software 名の allowlist を保ちつつ、local tool / option / provenance 語を advisory で検出する |
| #73 authoring note 漏出 | implemented | `check-authoring-intent.py`、`authoring-intent-check`、finish gate（`7d65d17`） | strict / advisory、TeX comment、明示 suppression の回帰テストを維持する |
| #74 図中 public label | absorbed | P3 Figure record / compiler contract と figure audit | main figure に public-label audit、label source、replacement または waiver を要求し、OCR は必須にしない |
| #75 derived quantity contract | implemented | legacy `quantity-integrity-check` と P1-B Research Result の typed quantity contract | value、denominator、unit of analysis、estimand、aggregation、independence、source、manuscript refs を保存する |
| #76 Python fallback | implemented | `resolve-python.sh` と root/downstream Makefile（`c5765b9`） | `.venv` → `python3.11` → `python3` → `python` の順で Python 3.11+ のみ選ぶ |
| #77 claim/gate 語の公開本文漏出 | absorbed | #72 と同じ P3/P5 public-language contract | workflow 語は internal-only とし、読者向け scope / next-test 語への mapping を managed default に持つ |
| #78 main-figure role budget | absorbed | P3 typed figure-story compile と Editorial visual obligation | project contract が要求した場合だけ、primary role の順序と secondary-before-primary を advisory 診断する |
| #79 narrative weight pass | absorbed | P3 section/figure compile と P6 semantic fixture | central proof path、mechanism/scope、secondary extension を明示し、defensive negation、secondary salience、同順位 next-test を advisory 評価する |

#78 は #79 の figure-order 特化 acceptance case として扱う。#72 と #77 は一つの public-language contract として実装し、用語ごとの checker を増やさない。

## Root governance layer

| asset | current responsibility | target model/gate | disposition | writer before | writer after | compatibility/migration | removal condition |
|---|---|---|---|---|---|---|---|
| `src/paperops/cli/` | scaffold、upgrade、migration、workflow の deterministic CLI | P1–P7 CLI / migration / atomic-write gate | adapt | PaperOps maintainer | PaperOps maintainer; runtime write は CLI | network/model を暗黙利用せず既存 command を互換維持 | v2 command で代替し利用ゼロを確認した個別 command のみ |
| `.agents/skills/` | root governance skill の正本 | P1–P7 Agent proposal / governance gate | adapt | PaperOps maintainer | PaperOps maintainer | Agent は提案に限定し deterministic 更新を CLI へ渡す | 対応する互換入口と利用がなくなった個別 skill のみ |
| `.claude/skills/` | root skill の Claude 互換 mirror | P1–P7 read-only compatibility entry | retain | mirror maintenance workflow | mirror maintenance workflow | `.agents/skills/` を正本として同期を検査 | 対応環境の利用ゼロと代替導線確認後のみ |
| `scripts/` | root smoke、release truth、package boundary の deterministic helper | P1–P7 checker / release gate | adapt | PaperOps maintainer | PaperOps maintainer | CLI に移す場合も既存 script は明示 redirect を経る | CLI 代替、全 caller 移行、release note 後のみ |
| `Makefile` | root の保守・template smoke 入口 | P1–P7 orchestration gate | retain | PaperOps maintainer | PaperOps maintainer | target 名を保ち deterministic CLI/checker を呼ぶ | 全下流 caller の代替確認後に個別 target を判断 |
| `.github/workflows/` | CI、再利用 build / mirror / release / publish | P1–P7 CI と release gate | adapt | PaperOps maintainer | PaperOps maintainer | main 到達性と既存 reusable interface を維持 | caller と release policy の移行完了後のみ |
| `docs/` | architecture、policy、migration、decision authority | P1–P7 design / migration authority | retain | PaperOps maintainer | PaperOps maintainer | ADR と migration note を実装より先に更新 | superseding decision と参照更新が揃った文書のみ |
| `.agents/skills/apply-template-improvement/SKILL.md` | 承認済み template 改善の実装手順 | P1–P7 managed/project ownership gate | adapt | maintainer via skill | Agent proposal; maintainer approval | migration note と smoke 条件を PaperOps 2 に適合 | 後継 skill への redirect と利用ゼロ確認後のみ |
| `.agents/skills/release/SKILL.md` | root release 手順 | P7 default / publish gate | adapt | maintainer via skill | maintainer; CI publish | v2-authoritative を実装済みと誤認しない release check を追加 | 後継 release automation の監査完了後のみ |
| `.agents/skills/review-template-regression/SKILL.md` | template 互換性 review | P1–P7 compatibility gate | adapt | reviewer via skill | Agent diagnostic; reviewer decision | authority 二重化、fallback、snapshot 分離を review 観点へ追加 | 後継 gate が同じ観点を保証後のみ |
| `.agents/skills/triage-template-feedback/SKILL.md` | feedback の scope / label / 実装先判断 | P1–P7 governance intake gate | retain | triager via skill | Agent proposal; human decision | root と downstream の分類を維持 | intake workflow の完全な代替後のみ |

### Root deterministic checkers

| asset | current responsibility | target model/gate | disposition | writer before | writer after | compatibility/migration | removal condition |
|---|---|---|---|---|---|---|---|
| `scripts/check-release-version-truth.py` | tag、package、CHANGELOG の release version truth 検査 | P7 release gate | retain | checker is read-only | checker is read-only | P1+ 未提供を release 済みと誤認しない | 置換 release gate の同等性確認後のみ |
| `scripts/check-scaffold-package-boundary.py` | scaffold と package の所有境界検査 | P1 managed/project ownership gate | adapt | checker is read-only | checker is read-only | managed path が project-owned state を包含しないことを検査 | 同等 CLI checker へ全 caller 移行後のみ |

### Root Make targets

| asset | current responsibility | target model/gate | disposition | writer before | writer after | compatibility/migration | removal condition |
|---|---|---|---|---|---|---|---|
| `Makefile::.PHONY` | root target の非ファイル宣言 | P1–P7 orchestration hygiene | retain | PaperOps maintainer | PaperOps maintainer | 全公開 target を列挙し続ける | Make を廃止する別変更後のみ |
| `Makefile::venv` | 開発 Python 環境作成 | P1 tool bootstrap gate | retain | Make / Python | Make / Python | Python 3.11+ を維持 | package runner への全移行後のみ |
| `Makefile::smoke` | root と template の総合 smoke | P1–P7 compatibility gate | adapt | Make | Make → deterministic checks | 新しい v2 check は shadow から追加 | 全 gate の別 orchestrator 移行後のみ |
| `Makefile::cli-smoke` | CLI compile と最小動作確認 | P1 CLI gate | adapt | Make / CLI | Make / CLI | legacy command と v2 command を段階比較 | CI の同等 gate が唯一の入口になった後のみ |
| `Makefile::scaffold-package-boundary-check` | scaffold と package 境界検査 | P1 ownership gate | adapt | Make / checker | Make / checker | managed path が project state を包含しない検査へ拡張 | 同等 CLI check へ全 caller 移行後のみ |
| `Makefile::build-submission` | template submission build の root proxy | P6 snapshot build gate | adapt | Make / shell | Make → deterministic builder | living manuscript と snapshot を分離 | template target への直接移行と利用ゼロ後のみ |
| `Makefile::lint-bib` | template bibliography lint | P3/P6 citation gate | retain | Make / checker | Make / checker | strict 意味を変えない | 置換 checker の同等性確認後のみ |
| `Makefile::citation-check` | template citation 整合性 | P3/P6 citation gate | retain | Make / checker | Make / checker | citation invariant を維持 | 置換 checker の同等性確認後のみ |
| `Makefile::mirror-check` | JA/EN mirror 対応検査 | P4/P6 mirror gate | retain | Make / checker | Make / checker | block ID と mirror invariant を維持 | 置換 checker の同等性確認後のみ |
| `Makefile::mirror-freshness-check` | mirror freshness 検査 | P4/P6 mirror gate | retain | Make / checker | Make / checker | selective stale と整合 | 置換 checker の同等性確認後のみ |
| `Makefile::public-terms-check` | 公開語検査 | P4/P5 authoring gate | retain | Make / checker | Make / checker | diagnostic/strict を維持 | 置換 checker の同等性確認後のみ |
| `Makefile::concept-term-check` | concept terminology 検査 | P4/P5 authoring gate | retain | Make / checker | Make / checker | legacy manuscript にも適用 | 置換 checker の同等性確認後のみ |
| `Makefile::argument-focus-check` | 論旨焦点検査 | P2–P5 editorial diagnostic | adapt | Make / checker | Make / checker over approved typed input | editorial 判断を deterministic 合否へ偽装しない | fixture 同等性と利用ゼロ後のみ |
| `Makefile::authoring-intent-check` | authoring intent 検査 | P4/P5 authoring gate | retain | Make / checker | Make / checker | invariant を維持 | 置換 checker の同等性確認後のみ |
| `Makefile::storyline-check` | storyline 整合性 | P2 typed story gate | adapt | Make / checker | Make / checker over story records | malformed v2 を legacy fallback で隠さない | v2 checker への全 caller 移行後のみ |
| `Makefile::schema-check` | template の schema kernel を advisory 検査 | P1-A schema / reference / semantics / hash gate | retain | Make / checker | Make / checker | project-owned state を書かず shadow check に留める | 全 model gate の同等入口へ移行後のみ |
| `Makefile::section-contract-check` | section contract / hierarchy 検査 | P2–P5 typed section gate | adapt | Make / checker | Make / checker over typed records | legacy-authoritative 中は比較し opt-in 後に v2 を正本化 | legacy reader 利用ゼロ確認後のみ |
| `Makefile::section-depth-check` | section depth 検査 | P4/P5 editorial diagnostic | adapt | Make / checker | Make / checker | advisory と strict を区別 | 後継 diagnostic の評価同等性確認後のみ |
| `Makefile::quantity-integrity-check` | 数量整合性 | P3–P6 quantity gate | retain | Make / checker | Make / checker | quantity invariant を維持 | 置換 checker の同等性確認後のみ |
| `Makefile::predicted-results-check` | predicted result lifecycle 検査 | P3–P5 claim/evidence gate | adapt | Make / checker | Make / checker over typed lifecycle | analysis request との追跡を保持 | typed checker への全 caller 移行後のみ |
| `Makefile::content-first-check` | content-first phase 検査 | P2–P5 editorial gate | adapt | Make / checker | Make / checker | submission hygiene と本文 blocker を分離 | 後継 workflow gate の評価後のみ |
| `Makefile::finish-manuscript-check` | manuscript 完了 strict 集約 | P4–P6 acceptance gate | adapt | Make | Make → deterministic check set | Agent/Writer を暗黙起動しない | 同等集約 gate への移行後のみ |
| `Makefile::block-flow-review-check` | block flow review 検査 | P4/P5 block gate | adapt | Make / checker | Make / checker over block revision | block ID と selective stale を維持 | typed replacement の同等性確認後のみ |
| `Makefile::figure-reference-check` | figure 参照検査 | P3–P6 figure gate | retain | Make / checker | Make / checker | figure invariant を維持 | 置換 checker の同等性確認後のみ |
| `Makefile::figure-obligation-check` | claim の figure obligation 検査 | P3–P5 figure gate | adapt | Make / checker | Make / checker over claim records | claim ID と evidence reference を保持 | typed replacement の同等性確認後のみ |
| `Makefile::figure-design-check` | figure design contract 検査 | P3–P5 figure gate | adapt | Make / checker | Make / checker | editorial quality は diagnostic に限定 | 後継 diagnostic の評価後のみ |
| `Makefile::claim-evidence-check` | claim/evidence 対応検査 | P3 typed reference gate | adapt | Make / checker | Make / checker over per-ID records | stable ID と revision を検証 | legacy reader 利用ゼロ確認後のみ |
| `Makefile::paper-layer-card-check` | paper layer card schema 検査 | P2–P3 migration gate | adapt | Make / checker | Make / migration preflight | card を per-ID typed record へ atomic 移行 | rollback と全 project migration 後のみ |
| `Makefile::card-coverage-check` | card coverage 検査 | P2–P3 coverage gate | adapt | Make / checker | Make / checker | decision density を評価 fixture で比較 | typed replacement の同等性確認後のみ |
| `Makefile::workflow-check` | workflow state 整合性 | P1–P6 orthogonal-state gate | adapt | Make / checker | Make / checker over axis records | macro state を read-only projection にする | legacy writable state 利用ゼロ後のみ |
| `Makefile::archive-seal-check` | archive 不変性検査 | P6 snapshot / archive gate | retain | Make / checker | Make / checker | immutable snapshot と living source を分離 | 後継 snapshot seal の同等性確認後のみ |
| `Makefile::submission-drift-check` | submission と living source の drift 検査 | P6 snapshot gate | adapt | Make / checker | Make / checker over referenced revisions | snapshot の revision/hash を固定 | 後継 snapshot checker の同等性確認後のみ |
| `Makefile::skill-mirror-check` | Agent / Claude skill mirror 検査 | P1–P7 compatibility gate | retain | Make / checker | Make / checker | root/template 正本境界を維持 | mirror interface 廃止の別判断後のみ |
| `Makefile::links-check` | local/external link 安全性 | P1/P3 confidentiality gate | adapt | Make / checker | Make / checker | absolute path と confidential state を tracked model から除外 | 後継 link checker の同等性確認後のみ |
| `Makefile::research-request-handoff-check` | research request handoff 検査 | P3 request lifecycle gate | adapt | Make / checker | Make / checker over request records | local/raw content を packet に混ぜない | typed replacement の同等性確認後のみ |
| `Makefile::research-request-handoff-live-check` | live research handoff 診断 | P3 explicit external workflow | retain | Make / checker | explicit Make / checker | network 利用は明示起動のまま | live workflow 廃止判断後のみ |
| `Makefile::external-import-check` | external import 整合性 | P3 provenance gate | adapt | Make / checker | Make / checker over import records | tracked summary と local/raw source を分離 | typed replacement の同等性確認後のみ |
| `Makefile::external-import-live-check` | live external import 診断 | P3 explicit external workflow | retain | Make / checker | explicit Make / checker | network 利用は明示起動のまま | live workflow 廃止判断後のみ |
| `Makefile::collect-context` | template context view 生成 | P2–P5 generated cache gate | redirect | Make / collector | deterministic materializer | 出力を未追跡 cache と明示し authority として読まない | 新 materialize command への全 caller 移行後のみ |
| `Makefile::template-readiness-check` | template starter readiness | P1–P7 starter gate | adapt | Make / checker | Make / checker | starter と strict の意味を分離 | 同等 CLI readiness への移行後のみ |

## Downstream template layer

| asset | current responsibility | target model/gate | disposition | writer before | writer after | compatibility/migration | removal condition |
|---|---|---|---|---|---|---|---|
| `template/_paperops/defaults/schemas/` | managed schema defaults | P1 paperops-managed schema authority | adapt | PaperOps release | PaperOps release | project-owned state を managed update で上書きしない | versioned replacement と migration 完了後のみ |
| `template/_paperops/defaults/contracts/` | managed section / figure contracts | P1–P5 managed contract authority | adapt | PaperOps release | PaperOps release | schema version と compatibility reader を用意 | versioned replacement と利用ゼロ後のみ |
| `template/_paperops/defaults/workflow/` | state machine、focus policy、subagent roster の managed default | paperops-managed workflow default | adapt | PaperOps release | PaperOps release | project-owned workflow fact や overlay を managed update で上書きしない | versioned replacement と migration 完了後のみ |
| `template/_paperops/contracts/` | 論文固有の section / figure contract 差分 | project-owned contract overlay | adapt | human / Agent の明示更新 | project workflow ごとの承認済み単一 writer | defaults と同名でも managed update の対象にせず compatibility reader を維持 | typed overlay migration と利用ゼロ確認後のみ |
| `template/_paperops/model/` | project-owned Editorial / Research / Manuscript / Issue typed state | P1 schema-checked opt-in state、P2以降のmodel別authority | investigate | legacy cards / human-edited TeX | P1-Bではwriterなし。P2/P4でmodel別単一writerを決定 | 理由: modelごとに単一writerをP1で決定する必要がある。managed updateはindex/recordを生成・上書きせず、Issueはpublic summaryとopaque local refのみ。legacy authorityからの切替は未提供 | writer決定、atomic migration、strict検証、全project復元確認後のみ |
| `template/_paperops/claims/` | claim / argument / gate cards | P3 claim typed authority | adapt | human / skills | claim workflow の単一 writer | stable ID、revision、legacy read-only view を保持 | v2-authoritative と利用ゼロ確認後のみ |
| `template/_paperops/evidence/` | result / figure / source evidence cards | P3 evidence typed authority | adapt | human / import skills | evidence workflow の単一 writer | provenance と confidential boundary を保持 | v2-authoritative と利用ゼロ確認後のみ |
| `template/_paperops/evidence/figures/` | figure evidence records | P3 figure evidence authority | adapt | human / figure skills | evidence workflow の単一 writer | figure ID と参照を migration | legacy reader 利用ゼロ後のみ |
| `template/_paperops/evidence/results/` | result evidence records | P3 result evidence authority | adapt | human / analysis import | evidence workflow の単一 writer | predicted と observed を混同しない | legacy reader 利用ゼロ後のみ |
| `template/_paperops/evidence/sources/` | source evidence records | P3 source provenance authority | adapt | human / research skill | evidence workflow の単一 writer | raw/private source は local state に残す | legacy reader 利用ゼロ後のみ |
| `template/_paperops/refs/` | 文献summary、research map、external source link、import provenance | project-owned research/provenance state | adapt | human / research skills | provenance workflow の単一 writer | raw/private/local artifact は追跡外に置き、sanitized summary と参照だけを保持 | typed provenance migration と legacy reader 利用ゼロ後のみ |
| `template/_paperops/notes/views/ (pure overview views)` | card / typed authority の俯瞰 | generated read-only projection | redirect | skill または human による集約 | deterministic materializer only | compatibility readers は migration と strict validation 完了まで維持 | 全 reader が typed authority を参照し strict validation 済みになった後のみ |
| `template/_paperops/notes/views/ (controlled authoring views)` | story spine、概念語、条件名など本文判断の統制 | project-owned editable decision | adapt | project-owned / human-written | P1 で各判断の typed authority と単一 writer を決定 | compatibility readers は migration と strict validation 完了まで維持し、それ以前は redirect しない | P1 の authority 決定、migration、strict validation 後に個別 view ごとに判断 |
| `template/_paperops/review/` | review rounds、feedback、responses | P6 review-round authority | adapt | human / review skills（P1-Bでもauthority） | P2/P4未提供のため未切替。将来review workflowの単一writer | Task 5 Issue schemaはopt-in shadow表現のみ。raw reviewer textをlocal/confidential stateと分離し自動dual-writeしない | migrated rounds、strict検証、復元確認後のみ |
| `template/_paperops/requests/` | analysis / writing request lifecycle | P3–P5 request typed authority | adapt | human / skills（P1-Bでもauthority） | P2/P4未提供のため未切替。将来request workflowの単一writer | Task 5 Issue schemaはlifecycleを保持するがlegacy requestを生成・上書き・削除しない | migrated requests、strict検証、利用ゼロ確認後のみ |
| `template/_paperops/workflow/` | writable workflow state | P1–P6 axis facts + read-only macro projection | adapt | setup / workflow tools | axis ごとの単一 CLI writer | macro state 直接更新を停止し atomic migration | legacy writable macro state 利用ゼロ後のみ |
| `template/story/` | 人間が読む研究質問、仮説、evidence path、negative route | project-owned human story concept | adapt | human / Agent の明示更新 | human-approved story workflow | typed Editorial decision と同一の writable authority にせず、seed / compatibility reader の関係を明示 | P2 authority 決定と migration 検証後に個別判断 |
| `template/manuscript/` | JA/EN human-edited authoring source | P4–P6 human manuscript authority | retain | human / existing editing workflows | human or future deterministic applicator | Writer は patch のみ、block ID と mirror を維持 | living manuscript のため削除対象外 |
| `template/submission/ (mutable candidate)` | 投稿先向けにbuildした差し替え可能な candidate | derived replaceable artifact | adapt | Make / submission workflow | deterministic candidate builder | living manuscript と分離し、submitted round snapshot の authority にしない | v2 candidate builder 全移行後のみ |
| `template/submission/ (submitted round snapshots)` | 実際に提出したroundの原稿、manifest、参照revision | immutable publication evidence | adapt | publication snapshot command | publication snapshot command | candidate と authority を混同しない。新しい提出は既存snapshot更新でなく新roundを作る | immutable evidence のため削除対象外 |
| `template/.agents/skills/` | downstream Agent skill 正本 | P2–P6 proposal / approval workflow | adapt | PaperOps release | PaperOps release; runtime は Agent proposal | authority 直接書込みを CLI / human approval へ分離 | 個別後継と利用ゼロ確認後のみ |
| `template/.claude/skills/` | downstream skill の Claude mirror | P2–P6 read-only compatibility entry | retain | mirror workflow | mirror workflow | `.agents/skills/` を正本として同期 | 対応環境利用ゼロ後のみ |
| `template/scripts/check-*.py` | downstream deterministic checker 群 | P1–P7 checker gates | adapt | PaperOps release | PaperOps release | malformed typed state を legacy fallback で隠さない | 個別 replacement の同等性確認後のみ |
| `template/Makefile` | downstream build / check orchestration | P1–P7 explicit command surface | retain | PaperOps release + project overlay | PaperOps release + project overlay | target 名を維持し Agent/Writer を暗黙起動しない | 全 target の別 orchestrator 移行後のみ |

### Downstream skills

| asset | current responsibility | target model/gate | disposition | writer before | writer after | compatibility/migration | removal condition |
|---|---|---|---|---|---|---|---|
| `template/.agents/skills/ai-disclosure-check/SKILL.md` | AI 利用開示点検 | P6 submission diagnostic | retain | Agent diagnostic | Agent diagnostic; human decision | tracked disclosure と local/private input を分離 | 投稿 workflow で不要と確認後のみ |
| `template/.agents/skills/archive-scratch/SKILL.md` | scratch archive 封印・復元 | P6 immutable archive gate | adapt | skill / CLI | Agent proposal; CLI atomic archive | living source と archive を分離 | snapshot workflow が復元も代替後のみ |
| `template/.agents/skills/audit-ai-draft/SKILL.md` | AI draft の editorial 診断 | P2–P5 proposal | retain | Agent | Agent proposal only | typed authority へ直接書かない | 後継 editorial route 利用定着後のみ |
| `template/.agents/skills/calibrate-claims/SKILL.md` | claim 強度調整提案 | P3 claim proposal | adapt | Agent / human edit | Agent proposal; claim writer after approval | claim revision と evidence hash を記録 | 後継 claim workflow 利用定着後のみ |
| `template/.agents/skills/collect-manuscript-review/SKILL.md` | review diff 回収 | P6 review import | adapt | skill | deterministic collector; review writer | raw comment の confidential boundary を追加 | typed review import の利用定着後のみ |
| `template/.agents/skills/compile-discussion-section/SKILL.md` | Discussion plan compiler | P4 compiler gate | adapt | Agent skill | deterministic compiler from approved input | generated plan を cache とする | P4 compiler へ redirect 完了後のみ |
| `template/.agents/skills/compile-methods-section/SKILL.md` | Methods plan compiler | P4 compiler gate | adapt | Agent skill | deterministic compiler from approved input | generated plan を cache とする | P4 compiler へ redirect 完了後のみ |
| `template/.agents/skills/compile-results-section/SKILL.md` | Results plan compiler | P4 compiler gate | adapt | Agent skill | deterministic compiler from approved input | approved claim/evidence scope に限定 | P4 compiler へ redirect 完了後のみ |
| `template/.agents/skills/content-first-gate/SKILL.md` | content-first route 判定 | P2–P5 editorial gate | retain | Agent | Agent proposal; human route decision | submission axis を暗黙変更しない | 後継 route 利用定着後のみ |
| `template/.agents/skills/contextualize-conditions/SKILL.md` | condition の claim scope 化 | P3 claim proposal | adapt | Agent | Agent proposal; claim writer after approval | evidence reference と revision を明示 | 後継 claim workflow 利用定着後のみ |
| `template/.agents/skills/design-manuscript-claims/SKILL.md` | claim hierarchy 設計 | P3 claim proposal | adapt | Agent / human | Agent proposal; approved claim writer | candidate/selection/rejection を typed 化 | 後継 claim workflow 利用定着後のみ |
| `template/.agents/skills/design-paper-figure/SKILL.md` | figure / panel 設計 | P3 figure proposal | adapt | Agent / human | Agent proposal; figure writer after approval | figure ID と claim scope を保持 | 後継 figure workflow 利用定着後のみ |
| `template/.agents/skills/design-paper-storyline/SKILL.md` | story spine 設計 | P2 story proposal | adapt | Agent / human | Agent proposal; story writer after approval | candidate と棄却理由を保存 | 後継 story workflow 利用定着後のみ |
| `template/.agents/skills/develop-manuscript-content/SKILL.md` | manuscript content route | P2–P5 Agent / Writer boundary | adapt | Agent may edit | Agent proposes; Writer patches packet scope only | manuscript 直接書込みを human approval へ分離 | 新 route への redirect 完了後のみ |
| `template/.agents/skills/draft-predicted-results/SKILL.md` | predicted result scaffold | P3 predicted lifecycle | adapt | Agent / human | Agent proposal; typed request writer after approval | evidence として扱わず analysis request を連結 | 後継 lifecycle 利用定着後のみ |
| `template/.agents/skills/feedback-paper-harness/SKILL.md` | upstream feedback route | P1–P7 governance intake | retain | Agent / human | Agent proposal; human submit | project local と root scope を分離 | upstream intake 代替後のみ |
| `template/.agents/skills/figure-story-audit/SKILL.md` | figure と claim の監査 | P3–P5 diagnostic | adapt | Agent diagnostic | Agent diagnostic | deterministic gate を裁量で無効化しない | 後継 diagnostic 利用定着後のみ |
| `template/.agents/skills/finalize-manuscript/SKILL.md` | completion 前統合確認 | P4–P6 acceptance route | adapt | Agent | Agent proposal; human decision | submission snapshot を別軸にする | 後継 finish route 利用定着後のみ |
| `template/.agents/skills/finish-manuscript/SKILL.md` | manuscript 完了 orchestration | P2–P6 orchestration | adapt | Agent orchestrator | Agent proposals; CLI checks; human approval | 次段階を暗黙起動しない | 後継 orchestrator 利用定着後のみ |
| `template/.agents/skills/import-manuscript/SKILL.md` | 外部 manuscript import | P1/P4 migration | adapt | skill / shell | CLI atomic importer; human approval | preflight、rollback、block ID migration | v2 importer 利用定着後のみ |
| `template/.agents/skills/improve-writing-harness/SKILL.md` | project-local harness 改善 | P1–P7 local governance | adapt | Agent / human | Agent proposal; human implementation | managed path と project path を分離 | 後継 local workflow 利用定着後のみ |
| `template/.agents/skills/integrate-writing-feedback/SKILL.md` | feedback を card へ反映 | P3/P6 typed feedback route | adapt | Agent / human | Agent proposal; review/claim writer after approval | raw feedback と tracked summary を分離 | typed workflow 利用定着後のみ |
| `template/.agents/skills/map-result-patterns/SKILL.md` | raw result を evidence pattern 化 | P3 evidence proposal | adapt | Agent / human | Agent proposal; evidence writer after approval | raw data は authority 外に保持 | typed evidence workflow 利用定着後のみ |
| `template/.agents/skills/note-writing-session/SKILL.md` | session handoff 記録 | P1–P6 operational note | investigate | Agent / human | 未確定: P1 で session note と authority fact の境界を調査 | 理由: session note が authority fact と誤認されない境界が未確定 | 調査後の後継導線と利用ゼロ確認後のみ |
| `template/.agents/skills/open-paper-scan/SKILL.md` | broad editorial scan | P2–P5 proposal | retain | Agent | Agent proposal only | authority を更新しない | 後継 ideation route 利用定着後のみ |
| `template/.agents/skills/orchestrate-manuscript-subagents/SKILL.md` | subagent 分担 | P2–P6 orchestration | adapt | Agent orchestrator | Agent reports only; main integrates proposals | report を authority / manuscript に直接混ぜない | 後継 orchestrator 利用定着後のみ |
| `template/.agents/skills/paragraph-surgery/SKILL.md` | paragraph edit 提案 | P5 Writer patch | adapt | Agent / human edit | Writer packet scoped patch; human apply | claim scope 外変更を禁止 | Writer workflow 利用定着後のみ |
| `template/.agents/skills/peer-review-manuscript/SKILL.md` | strict peer review | P6 review proposal | adapt | Agent | Agent review proposal; human records decision | raw/private review と tracked summary を分離 | 後継 review route 利用定着後のみ |
| `template/.agents/skills/plan-figure-story/SKILL.md` | required figure 計画 | P3 figure proposal | adapt | Agent / human | Agent proposal; figure writer after approval | claim visual obligation を stable ID で参照 | typed figure workflow 利用定着後のみ |
| `template/.agents/skills/polish-ai-draft/SKILL.md` | claim 不変の prose polish | P5 Writer patch | adapt | Agent / human edit | Writer packet scoped patch; human apply | canonical claim/evidence を変更しない | Writer workflow 利用定着後のみ |
| `template/.agents/skills/public-terminology-pass/SKILL.md` | 公開語への修正 | P5 Writer patch / checker | adapt | Agent / human edit | Writer patch; checker; human apply | terminology authority と block ID を保持 | Writer workflow 利用定着後のみ |
| `template/.agents/skills/pull-template-updates/SKILL.md` | update-paperops の旧名入口 | P7 compatibility alias | deprecate | compatibility skill | read-only redirect to update-paperops | 新規利用を止め既存 invocation を観測 | 利用ゼロ、release note、alias migration 後のみ |
| `template/.agents/skills/research-related-work/SKILL.md` | related-work 収集と要約 | P3 source proposal | adapt | Agent / human | Agent proposal; source writer after approval | raw findings と tracked summaries を分離 | typed source workflow 利用定着後のみ |
| `template/.agents/skills/resolve-local-paths/SKILL.md` | external/local path 解決 | P1/P3 local-state boundary | adapt | skill / human | explicit resolver; no tracked absolute path write | credential、絶対 path を local state に限定 | 後継 resolver 利用定着後のみ |
| `template/.agents/skills/respond-to-peer-review/SKILL.md` | reviewer response 設計 | P6 review proposal | adapt | Agent / human | Agent proposal; review writer after approval | raw reviewer text と tracked response を分離 | typed review workflow 利用定着後のみ |
| `template/.agents/skills/resume-session/SKILL.md` | session state 復元 | P1–P6 read-only status | adapt | Agent reads notes | CLI status projection; Agent recommends | macro state を直接書かない | v2 status route 利用定着後のみ |
| `template/.agents/skills/review-block-flow/SKILL.md` | block architecture review | P4/P5 block proposal | adapt | Agent / human | Agent proposal; section writer after approval | block ID、revision、selective stale を保持 | typed section workflow 利用定着後のみ |
| `template/.agents/skills/review-public-manuscript/SKILL.md` | public manuscript reader review | P5/P6 review proposal | retain | Agent | Agent proposal; human decision | repo private context を読まない境界を維持 | 後継 review route 利用定着後のみ |
| `template/.agents/skills/route-manuscript-feedback/SKILL.md` | feedback の上流 route | P3–P6 issue routing | adapt | Agent / human | Agent proposal; model-specific writer after approval | prose 直接編集前に typed state へ戻す | typed router 利用定着後のみ |
| `template/.agents/skills/scientific-gate/SKILL.md` | claim readiness 判断 | P3 approval gate | adapt | Agent / human | Agent proposal; human approval record | editorial 判断と deterministic check を分離 | typed approval gate 利用定着後のみ |
| `template/.agents/skills/setup/SKILL.md` | downstream 初期設定 | P1 init / managed ownership gate | adapt | skill / CLI | CLI deterministic init; Agent guidance | `pops init` に統一し project state を上書きしない | v2 setup route 利用定着後のみ |
| `template/.agents/skills/source-reach-scan/SKILL.md` | source collection route 設計 | P3 source provenance | adapt | Agent | Agent proposal; explicit external workflow | raw storage、promotion、tracked summary を分離 | typed source route 利用定着後のみ |
| `template/.agents/skills/start-manuscript-review/SKILL.md` | human review session 開始 | P6 review-round transition | adapt | skill / human | CLI round start; human review | review round を明示作成し他 axis を動かさない | typed review command 利用定着後のみ |
| `template/.agents/skills/submission-gate/SKILL.md` | submission candidate 化 | P6 immutable snapshot gate | adapt | skill / human | CLI snapshot; human approval | living manuscript と immutable snapshot を分離 | typed snapshot workflow 利用定着後のみ |
| `template/.agents/skills/sync-ja-en/SKILL.md` | JA/EN block mirror 同期 | P4/P5 mirror patch | adapt | Agent / human edit | Writer packet scoped patch; human apply | block ID と mirror map を維持 | v2 mirror workflow 利用定着後のみ |
| `template/.agents/skills/update-paperops/SKILL.md` | managed scaffold update | P1/P7 managed update gate | adapt | pops / skill | CLI atomic managed updater | project-owned typed state を包含しない | 後継 updater 利用定着後のみ |
| `template/.agents/skills/update-refs/SKILL.md` | references 整合性更新 | P3 citation/source workflow | adapt | Agent / human | Agent proposal; refs writer after approval | bib、summary、citation provenance を保持 | typed refs workflow 利用定着後のみ |
| `template/.agents/skills/venue-fit-review/SKILL.md` | venue fit 診断 | P2/P6 editorial proposal | retain | Agent | Agent proposal; human decision | submission metadata authority を直接変更しない | 後継 venue route 利用定着後のみ |

### Downstream deterministic checkers

| asset | current responsibility | target model/gate | disposition | writer before | writer after | compatibility/migration | removal condition |
|---|---|---|---|---|---|---|---|
| `template/scripts/check-archive-seal.py` | archive seal 検査 | P6 immutable snapshot gate | adapt | checker is read-only | checker is read-only | revision/hash を検査 | v2 snapshot checker 同等性確認後のみ |
| `template/scripts/check-argument-focus.py` | argument focus 診断 | P2–P5 editorial diagnostic | adapt | checker is read-only | checker is read-only | editorial choice を合否へ偽装しない | fixture 比較完了後のみ |
| `template/scripts/check-authoring-intent.py` | authoring intent 検査 | P4/P5 authoring gate | retain | checker is read-only | checker is read-only | authoring invariant を維持 | 置換 checker 同等性確認後のみ |
| `template/scripts/check-block-flow-review.py` | block review 検査 | P4/P5 block revision gate | adapt | checker is read-only | checker is read-only | block ID と selective stale を検査 | typed replacement 同等性確認後のみ |
| `template/scripts/check-card-coverage.py` | card coverage 検査 | P2/P3 decision-density gate | adapt | checker is read-only | checker is read-only | legacy/v2 fixture を同一入力で比較 | typed replacement 同等性確認後のみ |
| `template/scripts/check-citations.py` | citation 整合性 | P3/P6 citation gate | retain | checker is read-only | checker is read-only | citation invariant を維持 | 置換 checker 同等性確認後のみ |
| `template/scripts/check-claim-evidence.py` | claim/evidence 対応 | P3 typed reference gate | adapt | checker is read-only | checker is read-only | ID、revision、dependency hash を検査 | legacy reader 利用ゼロ後のみ |
| `template/scripts/check-concept-terms.py` | concept terminology | P4/P5 authoring gate | retain | checker is read-only | checker is read-only | legacy manuscript にも適用 | 置換 checker 同等性確認後のみ |
| `template/scripts/check-content-first.py` | content-first phase | P2–P5 workflow gate | adapt | checker is read-only | checker is read-only | orthogonal state 軸を暗黙変更しない | v2 workflow checker 同等性確認後のみ |
| `template/scripts/check-external-imports.py` | external import | P3 provenance gate | adapt | checker is read-only | checker is read-only | raw/private と tracked record を分離 | typed replacement 同等性確認後のみ |
| `template/scripts/check-figure-design.py` | figure design contract | P3–P5 diagnostic | adapt | checker is read-only | checker is read-only | strict/advisory を区別 | typed replacement 同等性確認後のみ |
| `template/scripts/check-figure-obligations.py` | figure obligation | P3 claim/figure gate | adapt | checker is read-only | checker is read-only | stable claim / figure ID を検査 | typed replacement 同等性確認後のみ |
| `template/scripts/check-figure-references.py` | figure reference | P3–P6 figure gate | retain | checker is read-only | checker is read-only | figure invariant を維持 | 置換 checker 同等性確認後のみ |
| `template/scripts/check-links.py` | link 安全性 | P1/P3 confidentiality gate | adapt | checker is read-only | checker is read-only | tracked absolute path を拒否 | 置換 checker 同等性確認後のみ |
| `template/scripts/check-paper-layer-cards.py` | card schema | P1–P3 migration preflight | adapt | checker is read-only | checker is read-only | malformed v2 は legacy fallback しない | typed replacement 同等性確認後のみ |
| `template/scripts/check-predicted-results.py` | predicted lifecycle | P3–P5 lifecycle gate | adapt | checker is read-only | checker is read-only | request/evidence の区別を維持 | typed replacement 同等性確認後のみ |
| `template/scripts/check-public-terms.py` | public terminology | P4/P5 authoring gate | retain | checker is read-only | checker is read-only | public term invariant を維持 | 置換 checker 同等性確認後のみ |
| `template/scripts/check-quantity-integrity.py` | quantity integrity | P3–P6 quantity gate | retain | checker is read-only | checker is read-only | quantity invariant を維持 | 置換 checker 同等性確認後のみ |
| `template/scripts/check-research-request-handoff.py` | research handoff | P3 request gate | adapt | checker is read-only | checker is read-only | request revision と local boundary を検査 | typed replacement 同等性確認後のみ |
| `template/scripts/check-section-contracts.py` | section contract / hierarchy | P2–P5 typed section gate | adapt | checker is read-only | checker is read-only | malformed typed state の no-fallback を維持 | legacy reader 利用ゼロ後のみ |
| `template/scripts/check-section-depth.py` | section depth | P4/P5 editorial diagnostic | adapt | checker is read-only | checker is read-only | diagnostic と strict を区別 | fixture 比較完了後のみ |
| `template/scripts/check-skill-mirror.py` | skill mirror | P1–P7 compatibility gate | retain | checker is read-only | checker is read-only | `.agents` 正本を維持 | mirror interface 廃止後のみ |
| `template/scripts/check-storyline.py` | storyline | P2 typed story gate | adapt | checker is read-only | checker is read-only | candidate、selection、rejection を検査 | legacy reader 利用ゼロ後のみ |
| `template/scripts/check-submission-drift.py` | submission drift | P6 snapshot gate | adapt | checker is read-only | checker is read-only | referenced revision/hash で比較 | v2 snapshot checker 同等性確認後のみ |
| `template/scripts/check-tex-structure.py` | TeX structure | P4/P5 manuscript gate | retain | checker is read-only | checker is read-only | block/mirror structureを維持 | 置換 checker 同等性確認後のみ |
| `template/scripts/check-workflow-state.py` | workflow state | P1–P6 orthogonal-state gate | adapt | checker is read-only | checker is read-only | macro state を projection として検査 | legacy writable macro state 利用ゼロ後のみ |
| `template/scripts/lint-bib.py` | bibliography 構造と submission mode の lint | P3/P6 citation gate | retain | checker is read-only | checker is read-only | 通常 / pre-submit の exit semantics を維持 | 置換 checker 同等性確認後のみ |
| `template/scripts/mirror-check.py` | JA/EN block 対応検査 | P4/P6 mirror gate | retain | checker is read-only | checker is read-only | block ID と mirror invariant を維持 | 置換 checker 同等性確認後のみ |
| `template/scripts/mirror-freshness-check.py` | JA/EN mirror freshness 検査 | P4/P6 mirror stale gate | retain | checker is read-only | checker is read-only | advisory / strict と selective stale を維持 | 置換 checker 同等性確認後のみ |
| `template/scripts/readiness-check.py` | starter / project / submission readiness 検査 | P1–P7 readiness gate | adapt | checker is read-only | checker is read-only | starter と strict submission profile を区別 | v2 readiness checker 同等性確認後のみ |
| `template/scripts/check-paperops-models.py` | schema registry に従う phase 別 model 検査 | P1-A schema / reference / semantics / hash gate | retain | checker is read-only | checker is read-only | managed schema と project-owned model の境界を維持 | 全 model checker の同等性確認後のみ |

### Downstream Make targets

| asset | current responsibility | target model/gate | disposition | writer before | writer after | compatibility/migration | removal condition |
|---|---|---|---|---|---|---|---|
| `template/Makefile::.PHONY` | downstream target の非ファイル宣言 | P1–P7 orchestration hygiene | retain | PaperOps release | PaperOps release | 公開 target を列挙し続ける | Make 廃止の別変更後のみ |
| `template/Makefile::venv` | Python 環境作成 | P1 bootstrap | retain | Make / Python | Make / Python | Python 3.11+ を維持 | runner 全移行後のみ |
| `template/Makefile::build-ja` | JA manuscript build | P4/P6 build gate | retain | Make / TeX | Make / deterministic builder | living source から派生物を生成 | 代替 builder 全移行後のみ |
| `template/Makefile::build-en` | EN manuscript build | P4/P6 build gate | retain | Make / TeX | Make / deterministic builder | living source から派生物を生成 | 代替 builder 全移行後のみ |
| `template/Makefile::build-submission` | submission artifact build | P6 snapshot build | adapt | Make / shell | Make / deterministic snapshot builder | immutable candidate と living source を分離 | v2 builder 全移行後のみ |
| `template/Makefile::lint-bib` | bibliography lint | P3 citation gate | retain | Make / checker | Make / checker | existing exit semantics を維持 | 置換 checker 同等性確認後のみ |
| `template/Makefile::lint-bib-pre-submit` | strict bibliography lint | P6 submission gate | retain | Make / checker | Make / checker | pre-submit strict を維持 | 置換 checker 同等性確認後のみ |
| `template/Makefile::citation-check` | citation check | P3/P6 citation gate | retain | Make / checker | Make / checker | citation invariant を維持 | 置換 checker 同等性確認後のみ |
| `template/Makefile::mirror-check` | mirror check | P4/P6 mirror gate | retain | Make / checker | Make / checker | JA/EN block invariant を維持 | 置換 checker 同等性確認後のみ |
| `template/Makefile::mirror-freshness-check` | mirror freshness | P4/P6 mirror gate | retain | Make / checker | Make / checker | selective stale と整合 | 置換 checker 同等性確認後のみ |
| `template/Makefile::mirror-strict-check` | strict mirror freshness | P6 submission gate | retain | Make / checker | Make / checker | strict 意味を維持 | 置換 checker 同等性確認後のみ |
| `template/Makefile::public-terms-check` | public terms | P4/P5 authoring gate | retain | Make / checker | Make / checker | public invariant 維持 | 置換 checker 同等性確認後のみ |
| `template/Makefile::concept-term-check` | concept terms | P4/P5 authoring gate | retain | Make / checker | Make / checker | legacy compatibility 維持 | 置換 checker 同等性確認後のみ |
| `template/Makefile::argument-focus-check` | argument focus | P2–P5 diagnostic | adapt | Make / checker | Make / checker | editorial choice と分離 | fixture 同等性確認後のみ |
| `template/Makefile::authoring-intent-check` | authoring intent | P4/P5 gate | retain | Make / checker | Make / checker | invariant 維持 | 置換 checker 同等性確認後のみ |
| `template/Makefile::storyline-check` | storyline | P2 story gate | adapt | Make / checker | Make / typed checker | no-fallback を維持 | legacy reader 利用ゼロ後のみ |
| `template/Makefile::schema-check` | project model の advisory schema 検査 | P1-A schema / reference / semantics / hash gate | retain | Make / checker | Make / checker | audit にだけ接続し finish / pre-submit へは未接続 | P1-B 後の統合 gate へ移行後のみ |
| `template/Makefile::section-contract-check` | section contract | P2–P5 section gate | adapt | Make / checker | Make / typed checker | atomic migration 後に authority 切替 | legacy reader 利用ゼロ後のみ |
| `template/Makefile::section-depth-check` | section depth | P4/P5 diagnostic | adapt | Make / checker | Make / checker | strict/advisory を区別 | fixture 同等性確認後のみ |
| `template/Makefile::quantity-integrity-check` | quantity integrity | P3–P6 gate | retain | Make / checker | Make / checker | invariant 維持 | 置換 checker 同等性確認後のみ |
| `template/Makefile::predicted-results-check` | predicted lifecycle | P3–P5 gate | adapt | Make / checker | Make / typed checker | analysis request linkage 維持 | typed replacement 同等性確認後のみ |
| `template/Makefile::content-first-check` | content-first | P2–P5 workflow gate | adapt | Make / checker | Make / checker | state axis を暗黙変更しない | v2 workflow 同等性確認後のみ |
| `template/Makefile::finish-manuscript-check` | finish strict checks | P4–P6 acceptance | adapt | Make | Make / checker set | Agent/Writer を暗黙起動しない | 同等集約 gate 移行後のみ |
| `template/Makefile::submission-gate` | submission strict subset | P6 snapshot preflight | adapt | Make | Make / checker set | snapshot 作成前に実行 | v2 submission gate 移行後のみ |
| `template/Makefile::block-flow-review-check` | block flow | P4/P5 block gate | adapt | Make / checker | Make / checker | block revision 維持 | typed replacement 同等性確認後のみ |
| `template/Makefile::figure-reference-check` | figure refs | P3–P6 gate | retain | Make / checker | Make / checker | invariant 維持 | 置換 checker 同等性確認後のみ |
| `template/Makefile::figure-obligation-check` | figure obligations | P3–P5 gate | adapt | Make / checker | Make / typed checker | claim/figure ID 維持 | typed replacement 同等性確認後のみ |
| `template/Makefile::figure-design-check` | figure design | P3–P5 diagnostic | adapt | Make / checker | Make / checker | editorial judgment と分離 | fixture 同等性確認後のみ |
| `template/Makefile::claim-evidence-check` | claim/evidence | P3 reference gate | adapt | Make / checker | Make / typed checker | revision/hash を検査 | legacy reader 利用ゼロ後のみ |
| `template/Makefile::paper-layer-card-check` | card schema | P1–P3 migration gate | adapt | Make / checker | Make / migration preflight | atomic migration | typed replacement 同等性確認後のみ |
| `template/Makefile::card-coverage-check` | card coverage | P2/P3 density gate | adapt | Make / checker | Make / checker | old/new fixture 比較 | typed replacement 同等性確認後のみ |
| `template/Makefile::workflow-check` | workflow state | P1–P6 state gate | adapt | Make / checker | Make / typed checker | macro projection 化 | legacy writable state 利用ゼロ後のみ |
| `template/Makefile::archive-seal-check` | archive seal | P6 snapshot gate | adapt | Make / checker | Make / checker | immutable revision/hash を検査 | v2 snapshot 同等性確認後のみ |
| `template/Makefile::submission-drift-check` | submission drift | P6 snapshot gate | adapt | Make / checker | Make / checker | living source と snapshot を分離 | v2 snapshot 同等性確認後のみ |
| `template/Makefile::skill-mirror-check` | skill mirror | P1–P7 compatibility | retain | Make / checker | Make / checker | Agent/Claude mirror 維持 | mirror interface 廃止後のみ |
| `template/Makefile::links-check` | links | P1/P3 confidentiality | adapt | Make / checker | Make / checker | tracked absolute path を拒否 | replacement 同等性確認後のみ |
| `template/Makefile::research-request-handoff-check` | research handoff | P3 request gate | adapt | Make / checker | Make / typed checker | request revision 維持 | typed replacement 同等性確認後のみ |
| `template/Makefile::research-request-handoff-live-check` | live research check | P3 explicit external workflow | retain | explicit Make | explicit Make | network を暗黙利用しない | live workflow 廃止後のみ |
| `template/Makefile::external-import-check` | external import | P3 provenance gate | adapt | Make / checker | Make / typed checker | raw/private 分離 | typed replacement 同等性確認後のみ |
| `template/Makefile::external-import-live-check` | live import check | P3 explicit external workflow | retain | explicit Make | explicit Make | network を暗黙利用しない | live workflow 廃止後のみ |
| `template/Makefile::collect-context` | session context 生成 | P2–P5 generated cache | redirect | collector | deterministic materializer | 出力を authority として読まない | v2 materialize 全移行後のみ |
| `template/Makefile::readiness-check` | starter/project readiness | P1–P7 readiness gate | adapt | Make / checker | Make / checker | starter と strict を区別 | v2 readiness 全移行後のみ |
| `template/Makefile::export-arxiv` | arXiv export | P6 publication export | adapt | Make / shell | deterministic snapshot exporter | immutable snapshot から export | v2 exporter 全移行後のみ |
| `template/Makefile::ci` | baseline CI aggregate | P1–P7 CI gate | adapt | Make | Make / deterministic checks | shadow check を段階追加 | 別 orchestrator 全移行後のみ |
| `template/Makefile::audit` | advisory audit aggregate | P2–P6 diagnostic gate | adapt | Make | Make / deterministic diagnostics | strict check と混同しない | 別 orchestrator 全移行後のみ |
| `template/Makefile::pre-submit` | full pre-submit aggregate | P6 publication gate | adapt | Make | Make / deterministic checks | snapshot 前 gate とする | v2 publication gate 全移行後のみ |
