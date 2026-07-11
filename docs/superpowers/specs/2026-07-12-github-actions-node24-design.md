# GitHub Actions Node.js 24 更新設計

## 目的

paperops自身と下流向けreusable workflowが参照するGitHub公式JavaScript ActionをNode.js 24 runtimeへ揃え、Node.js 20廃止警告を解消する。workflowのtrigger、permissions、Python version、artifact名、公開条件は変更しない。

## 現状と根拠

2026-07-12時点で、repository内には`actions/checkout@v4`、`actions/setup-python@v5`、`actions/upload-artifact@v4`、`actions/download-artifact@v4`が残っている。直前のv0.13.0公開runではGitHub runnerがこれらをNode.js 24へ強制実行し、Node.js 20廃止警告を出した。

GitHub公式repositoryのlatest releaseと各`action.yml`を確認し、次のmajor tagがNode.js 24を宣言していることを採用根拠とする。

| Action | 現在 | 更新先 | runtime |
| --- | --- | --- | --- |
| `actions/checkout` | `v4` | `v7` | `node24` |
| `actions/setup-python` | `v5` | `v6` | `node24` |
| `actions/upload-artifact` | `v4` | `v7` | `node24` |
| `actions/download-artifact` | `v4` | `v8` | `node24` |

参照した公式releaseは、checkout v7.0.0、setup-python v6.3.0、upload-artifact v7.0.1、download-artifact v8.0.1である。

## 変更範囲

次の全workflowで公式Action参照を一括更新する。

- `.github/workflows/ci.yml`
- `.github/workflows/publish-pypi.yml`
- `.github/workflows/reusable-build.yml`
- `.github/workflows/reusable-mirror-check.yml`
- `.github/workflows/reusable-release.yml`

`pypa/gh-action-pypi-publish@release/v1`はupstream管理のcomposite Actionであり、paperops側から内部依存を差し替えない。今回の対象はpaperopsが直接宣言する`actions/*`参照だけとする。

## 互換性方針

- 現行repositoryのmajor tag追従方針を維持し、commit SHA固定への移行は行わない。
- `with:` input、artifact upload/downloadの名前とpath、checkoutの`fetch-depth`を維持する。
- reusable workflowの公開inputと出力を変更しないため、下流migrationは不要とする。
- GitHub-hosted `ubuntu-latest`を前提とする。古いself-hosted runnerの対応は今回のscope外とする。
- Node.js runtime更新をPython runtime更新と混同せず、`python-version: "3.12"`を維持する。

## 検証

静的回帰テストで全`.github/workflows/*.yml`を走査し、次を保証する。

1. 旧参照`checkout@v4`、`setup-python@v5`、`upload-artifact@v4`、`download-artifact@v4`が残らない。
2. 直接利用する各Actionが設計表のmajor tagに一致する。
3. `pypa/gh-action-pypi-publish@release/v1`とreleaseのmain到達性guardが維持される。

その後、KUDPC計算ノードで対象テスト、`make cli-smoke`、`make smoke`を実行する。push後はGitHub ActionsのSmoke runを確認し、Node.js 20廃止annotationが消えたことを実環境の受入条件とする。

## 変更履歴とリリース

ユーザー影響のあるCI基盤更新として`CHANGELOG.md`の`Unreleased`へ記録する。変更はv0.13.0を書き換えず、次回releaseに含める。workflow更新と検証が成功した段階で日本語の理由付きcommitを作る。

## 受入条件

- repositoryが直接参照するGitHub公式JavaScript ActionがすべてNode.js 24 runtimeのmajor tagである。
- reusable workflowのinterfaceとPyPI Trusted Publishing境界が変わらない。
- ローカル回帰と`make smoke`が成功する。
- GitHub-hosted runner上のSmoke workflowが成功し、Node.js 20廃止警告を出さない。
