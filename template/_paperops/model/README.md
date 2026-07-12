# PaperOps project models

このdirectoryはproject-owned stateであり、`pops update-paperops`のmanaged update対象ではない。新規projectは`pops init`時に六つのstarterを検証し、model hashと`v2-authoritative` stateをmanifestへ記録する。既存projectはauthorityを自動変更せず、M0-0005とP2の`pops model diff|adopt`を使って手動採用する。

現行scopeはResearch、Editorial、Results hierarchy、Manuscript、Issue、Publicationの六モデルである。Research / Manuscript / Issueはindexとper-ID record、Editorial / Results hierarchy / Publicationはaggregate documentを使う。検査はschema、references、semantics、approvals、dependencies、hashの順で実行する。

v2-authoritativeではこの六モデルが意味論上の正本で、workflow macro stateは投影値になる。legacy card / review / request / workflowとhuman-edited TeXは互換参照として維持するがdual-writeしない。既存projectは明示migrationまで従来のauthorityを保ち、legacy artifactの物理削除は別判断とする。
