# AGENTS.md

ユーザーとは日本語でやりとりする。

paperops は、AI エージェントと論文を 1 本書くための最小限のハーネスである。設計上の約束は [SPEC.md](SPEC.md) に
あり、変更はそれに合わせる。2.0 は 1.x の作り直しで、1.x の code は tag `v1.0.0` に残っている。

## 構成

```text
src/paperops/
├── cli.py         pops: init, update, context, outline, build
├── project.py     paper.toml の読み込み
├── scaffold.py    init と update
├── harness.py     AGENTS.md の管理 block、skill の配置
├── context.py     pops context
├── tex.py         %> コメントと骨子の抽出
├── build.py       PDF の build と log の要約
├── skills/        論文 project に配る skill（paper-brief, -draft, -figure, -revise, -predict, -check）
└── _scaffold/     論文 project の雛形
tests/             pytest
```

論文 project に配るもの（`skills/`、`_scaffold/`、`harness.py` の block）と、この repository を開発するための
もの（この file、`SPEC.md`）を分けて考える。

## 確認

```bash
uv sync --dev
uv run ruff format src tests
uv run ruff check src tests
uv run pytest
```

build の test は `xelatex` と `bibtex` があるときだけ、図の helper の test は matplotlib（dev の依存）が
あるときだけ動く。京大スパコンでは、test は計算ノードで実行する。

## 変更するとき

- **SPEC の予算を守る。** コマンドは 6 個まで、skill は 6 個まで、実行時の依存は標準 library のみ。
  1.x は機能を足し続けて使えなくなった。足す前に、既存の skill の 1 項目で済まないかを確かめる。
- **実際の執筆で起きた摩擦から直す。** 想定で仕組みを足さず、論文 project で繰り返し起きた問題を、
  skill の文章か CLI の小さな変更で直す。
- **skill と block は「何をするか」と理由で書く。** 禁止の列挙にせず、同じ方針を 2 か所に書かない。
  方針は `harness.py` の block、手順は skill に置く。
- **CLI が読む書式（SPEC §4）を変えたら、雛形・skill・test を同時に直す。**
- **利用者に見える変更は `README.md` と `CHANGELOG.md` に反映する。**
  README の画像は `.github/assets/make_readme_art.py` が生成する（matplotlib が要る）。文言を変えたら
  script を直して SVG を作り直す。

## Git

- commit message は日本語で、変更の理由を書く。意味のある単位で commit する。
- push と release は、ユーザーが明示したときだけ行う。release は `main` の commit に tag `vX.Y.Z` を付け、
  GitHub Release を公開すると PyPI（`paper-harness-cli`）に出る。
