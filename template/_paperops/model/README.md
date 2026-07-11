# PaperOps project models

このdirectoryはproject-owned stateであり、`pops update-paperops`のmanaged update対象ではない。新規projectだけが`pops init`からstarterを受け取り、既存projectはM0-0005を確認して手動採用する。

現行scopeはResearch、Editorial、Results hierarchy、Manuscript、Issue、Publicationの六モデルである。Research / Manuscript / Issueはindexとper-ID record、Editorial / Results hierarchy / Publicationはaggregate documentを使う。検査はschema、references、semantics、approvals、dependencies、hashの順で実行する。

P1-Bはshadow validation境界でありauthority cutoverではない。P2まではlegacy card / review / request、P3まではhuman-edited TeX、P4までは既存workflow writerを維持する。移行中にlegacy artifactを削除したり、modelとdual-writeしたりしない。
