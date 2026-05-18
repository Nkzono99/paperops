---
id: D0005
record_type: decision
created_at: '2026-05-19T04:22:42+09:00'
status: adopted
source: H0003
evidence:
  summary: 'uv run python scripts/check-scaffold-package-boundary.py --out-dir .codex-tmp\\scaffold-boundary-check: ok; wheel contents and wheel-installed pops init excluded generated scaffold artifacts.'
  guard_path: scripts/check-scaffold-package-boundary.py
---

# D0005: adopted H0003

## 判断

adopted

## 理由

package exclude だけでは force-included template directory に効かなかったため、filtered scaffold build hook と release/prepublish guard を採用した。

## 証拠

uv run python scripts/check-scaffold-package-boundary.py --out-dir .codex-tmp\\scaffold-boundary-check: ok; wheel contents and wheel-installed pops init excluded generated scaffold artifacts.

## 回帰リスク

Medium: build hook が scaffold packaging 経路に入るため、EXCLUDED_SCAFFOLD_PATTERNS との同期と publish workflow の継続実行が必要。

## フォローアップ

finalize lane で make smoke と HOPS doctor/migrate を再実行し、publish workflow diff を PR で確認する。

## 回帰ガード

scripts/check-scaffold-package-boundary.py
