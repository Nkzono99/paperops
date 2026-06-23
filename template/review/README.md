# review 層

`review/` は人間の指示、原稿レビュー、模擬査読、実査読コメントをカード化し、原稿だけでなく claim / evidence / request へ遡らせる層である。

- `feedback/`: 人間や査読者からの指摘を feedback card として保存する。
- `rounds/`: 通読、週次、投稿前、査読ラウンドなどの review round を保存する。
- `responses/`: 実査読への返答案、response matrix、改稿方針を保存する。

人間は基本的に原稿レベルのレビューやプロンプト指示を出せばよい。AI は feedback card の `upstream_routes` を見て、claim / gate / evidence / request / manuscript のどこへ反映するかを決める。
