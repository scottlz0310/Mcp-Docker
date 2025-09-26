# CodeQL Service (Archived)

このディレクトリには、かつて `services/codeql/` として提供されていた静的解析サービスの設定が保存されています。

## 背景

- 2025-09-27 時点でローカル CodeQL サービスはプロジェクトから撤去されました。
- GitHub Actions 上での CodeQL 解析は `.github/workflows/security.yml` の過去バージョンを参照してください。
- 代替として `make security` や Trivy ベースのスキャンを強化しています。

## 再導入のヒント

1. `docker-compose.yml` に CodeQL サービスを再追加する。
2. `Dockerfile` に CodeQL CLI のインストール手順を復元する。
3. `main.py` や `Makefile` にサービス呼び出しロジックを追加する。

詳細は `docs/remove_plan_codeql.md` を参照してください。
