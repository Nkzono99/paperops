---
id: D0006
record_type: decision
created_at: '2026-05-20T04:28:09+09:00'
status: adopted
source: RS0010
evidence:
  summary: '.venv/Scripts/python.exe scripts/check-release-version-truth.py: ok; make cli-smoke: 33 tests OK; release mode は --release-version で metadata/changelog/tag/GitHub Release を検証する。'
  guard_path: scripts/check-release-version-truth.py
---

# D0006: adopted RS0010

## 判断

adopted

## 理由

release/version truth は package release heading と旧 template 履歴が混在しており、release 権限のある automation では tag 作成前に機械的な preflight が必要だったため採用する。

## 証拠

.venv/Scripts/python.exe scripts/check-release-version-truth.py: ok; make cli-smoke: 33 tests OK; release mode は --release-version で metadata/changelog/tag/GitHub Release を検証する。

## 回帰リスク

Low-Medium: release skill の手順追加と CHANGELOG 見出し整理は root 層に限定されるが、release 準備時に target version を明示する運用が必要。

## フォローアップ

finalize lane は make smoke と HOPS doctor/migrate を再実行し、release は version/changelog/tag criteria が明示された場合だけ検討する。

## 回帰ガード

scripts/check-release-version-truth.py
