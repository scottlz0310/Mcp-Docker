# GitHub Actions Simulator - ドキュメント案内

## 📚 コアドキュメント

| ファイル | 役割 |
| --- | --- |
| [github-actions-simulator-summary.md](github-actions-simulator-summary.md) | プロジェクト概要とロードマップサマリー |
| [implementation-plan.md](implementation-plan.md) | 軽量 act ベースへの実装計画 |
| [github-actions-simulator-design.md](github-actions-simulator-design.md) | 技術設計 (CLI / act / Docker) |
| [ui-design.md](ui-design.md) | CLI・Make・スクリプトのユーザー体験設計 |

## 🗂️ 参考ドキュメント

| ファイル | 用途 |
| --- | --- |
| [act-integration-design.md](act-integration-design.md) | act 詳細設定メモ (軽量化検討時の参考) |
| [archive/docs/actions/actions-service-proposal.md](../../archive/docs/actions/actions-service-proposal.md) | 旧来の常駐サービス案 (アーカイブ) |
| [archive/docs/actions/codeql-integration-strategy.md](../../archive/docs/actions/codeql-integration-strategy.md) | セキュリティ拡張案 (アーカイブ) |
| [archive/docs/actions/external-api-specification.md](../../archive/docs/actions/external-api-specification.md) | REST API 案の記録 (アーカイブ) |

## 📖 推奨読書順

1. `github-actions-simulator-summary.md`
2. `implementation-plan.md`
3. `github-actions-simulator-design.md`
4. `ui-design.md`

必要に応じて参考ドキュメントを確認する。

## 🚀 すぐに試す

```bash
# act を使ったシミュレーション (Docker 必須)
make actions
# もしくは
./scripts/run-actions.sh .github/workflows/ci.yml
```

## 📝 更新履歴

- **2025-09-26**: 軽量 act 方針に合わせて目次を刷新
- **2025-09-25**: 旧ロードマップ向けドキュメントを追加
