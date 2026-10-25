# リリースの準備と公開

リリースの prepare / publish / finalize は release-automate の同じ固定 SHA を使う。
導入 PR の通常のマージでは公開しない。

1. 利用者が対象版を指定した後、main の `Prepare Release` に先頭の v を除いた
   SemVer `MAJOR.MINOR.PATCH`（RC・build metadata 可） を渡す。版ファイルを持たないため `bump_strategy: none` とし、
   CHANGELOG の Unreleased を確定した準備 PR を作る。
2. 原稿・比較リンク・同一 HEAD CI・独立レビュー・未解決0を確認する。
   公開する版・コミット・内容について利用者の許可後に、
   `chore(release): vX.Y.Z` の件名で squash merge する。
3. 共通 publish がトリガー SHA に固定したタグと draft を作成する。
4. 同じ SHA の vet/test 後、従来の5ターゲットをクロスビルドし、
   `-X main.version=X.Y.Z` で版を埋め込む。
5. 同じ対象の draft だけへ従来名の5アーカイブと checksums.txt を添付する。
6. draft の対象 SHA と全6 asset 名を再確認し、成果物を再取得する。
   checksum 原稿の digest が同じ run の添付前の値と一致することを確認する。
   `verify-release-assets.sh` で checksum の全項目、アーカイブ内のファイル名、
   Linux amd64 の `--version` を検証する。他 OS での実機検証とは区別する。
7. 成功後だけ共通 finalize が公開し、対象 SHA・run・依存ジョブの検証証跡を追記する。
   本文の原稿は CHANGELOG で、自動生成の What's Changed は併記しない。

prepare は Organization の CLIENT_ID / PRIVATE_KEY、draft・添付・公開は実行 repo の
GITHUB_TOKEN を使う。タグ push 起点の別 workflow の発火には依存しない。
任意の `source_ref` を指定して直接公開する旧手順は、準備 PR へ統一した。

失敗時は draft を保持し、原因を解消した後に同じ run の failed jobs を再実行する。
公開後の本文追記だけが失敗した場合は、failed finalize の再実行で追記する。
別コミットへのタグ移動・削除、別の版での自動再試行は行わない。
公開後は固定タグと Release の対象 SHA・公開状態、5アーカイブと checksum、本文を確認する。
