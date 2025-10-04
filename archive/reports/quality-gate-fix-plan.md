# Quality Gate ワークフロー修正計画

## 問題の概要

現在のQuality Gateワークフローは、Git環境の設定に依存する問題があり、act直接実行時に失敗します。

### 🔍 特定された問題

1. **Git参照エラー**: `origin/...HEAD`の参照が失敗
2. **環境依存性**: ローカル環境のGit設定に依存
3. **PRイベント判定**: 非PRイベントでもPR用のGitコマンドが実行される

## 修正提案

### 1. 変更ファイル検出ロジックの改善

現在のコード:
```yaml
- name: 🔍 変更ファイル検出
  id: changes
  run: |
    # 変更されたファイルの検出
    if [[ "${{ github.event_name }}" == "pull_request" ]]; then
      # PRの場合は変更されたファイルを取得
      git diff --name-only origin/${{ github.base_ref }}...HEAD > changed_files.txt
    else
      # その他の場合は全ファイルを対象
      find . -type f \( -name "*.py" -o -name "*.sh" -o -name "*.yml" -o -name "*.yaml" -o -name "*.md" -o -name "*.sample" -o -name "*.example" \) > changed_files.txt
    fi
```

修正後のコード:
```yaml
- name: 🔍 変更ファイル検出
  id: changes
  run: |
    # 変更されたファイルの検出
    if [[ "${{ github.event_name }}" == "pull_request" ]]; then
      # PRの場合は変更されたファイルを取得（安全な方法）
      if git rev-parse --verify "origin/${{ github.base_ref }}" >/dev/null 2>&1; then
        git diff --name-only origin/${{ github.base_ref }}...HEAD > changed_files.txt
      else
        # フォールバック: 最近のコミットとの差分
        git diff --name-only HEAD~1...HEAD > changed_files.txt 2>/dev/null || {
          # さらなるフォールバック: 全ファイル検索
          find . -type f \( -name "*.py" -o -name "*.sh" -o -name "*.yml" -o -name "*.yaml" -o -name "*.md" -o -name "*.sample" -o -name "*.example" \) > changed_files.txt
        }
      fi
    else
      # その他の場合は全ファイルを対象
      find . -type f \( -name "*.py" -o -name "*.sh" -o -name "*.yml" -o -name "*.yaml" -o -name "*.md" -o -name "*.sample" -o -name "*.example" \) > changed_files.txt
    fi
```

### 2. Git環境の事前確認

```yaml
- name: 🔧 Git環境確認
  run: |
    echo "🔍 Git環境の確認中..."

    # Git設定の確認
    git config --get user.name || git config user.name "GitHub Actions"
    git config --get user.email || git config user.email "actions@github.com"

    # リモート設定の確認
    if ! git remote get-url origin >/dev/null 2>&1; then
      echo "⚠️ originリモートが設定されていません"
      git remote add origin https://github.com/example/repo.git || true
    fi

    # ブランチ情報の表示
    echo "📋 現在のブランチ: $(git branch --show-current)"
    echo "📋 利用可能なリモートブランチ:"
    git branch -r 2>/dev/null || echo "リモートブランチなし"

    echo "✅ Git環境確認完了"
```

### 3. エラーハンドリングの強化

```yaml
- name: 🔍 変更ファイル検出（改善版）
  id: changes
  run: |
    set -e  # エラー時に停止

    # 変更されたファイルの検出
    echo "🔍 変更ファイル検出を開始します..."

    # 安全な変更ファイル検出関数
    detect_changed_files() {
      local method="$1"
      local success=false

      case "$method" in
        "pr_diff")
          if [[ "${{ github.event_name }}" == "pull_request" ]] && git rev-parse --verify "origin/${{ github.base_ref }}" >/dev/null 2>&1; then
            echo "📋 PR差分を使用して変更ファイルを検出中..."
            git diff --name-only origin/${{ github.base_ref }}...HEAD > changed_files.txt && success=true
          fi
          ;;
        "recent_commit")
          echo "📋 最近のコミットとの差分を使用して変更ファイルを検出中..."
          git diff --name-only HEAD~1...HEAD > changed_files.txt 2>/dev/null && success=true
          ;;
        "find_all")
          echo "📋 全ファイル検索を使用して変更ファイルを検出中..."
          find . -type f \( -name "*.py" -o -name "*.sh" -o -name "*.yml" -o -name "*.yaml" -o -name "*.md" -o -name "*.sample" -o -name "*.example" \) > changed_files.txt && success=true
          ;;
      esac

      if [[ "$success" == "true" ]]; then
        echo "✅ $method による検出が成功しました"
        return 0
      else
        echo "❌ $method による検出が失敗しました"
        return 1
      fi
    }

    # 複数の方法を順次試行
    detect_changed_files "pr_diff" || \
    detect_changed_files "recent_commit" || \
    detect_changed_files "find_all" || {
      echo "❌ すべての変更ファイル検出方法が失敗しました"
      exit 1
    }

    # 結果の確認と出力
    if [[ -f changed_files.txt ]]; then
      CHANGED_FILES=$(cat changed_files.txt | tr '\n' ',' | sed 's/,$//')
      FILE_COUNT=$(wc -l < changed_files.txt)

      echo "📋 変更ファイル数: $FILE_COUNT"
      echo "🔍 完全検証必要: $(if [[ $FILE_COUNT -gt 10 ]]; then echo 'true'; else echo 'false'; fi)"

      # GitHub Outputに設定
      echo "changed-files=$CHANGED_FILES" >> $GITHUB_OUTPUT
      echo "needs-full-validation=$(if [[ $FILE_COUNT -gt 10 ]]; then echo 'true'; else echo 'false'; fi)" >> $GITHUB_OUTPUT
    else
      echo "❌ changed_files.txt が作成されませんでした"
      exit 1
    fi
```

## 実装計画

### Phase 1: 緊急修正（即座に実装）
1. ✅ Git参照の安全性チェック追加
2. ✅ フォールバック機能の実装
3. ✅ エラーハンドリングの強化

### Phase 2: 改善（1週間以内）
1. 🔄 Git環境の事前確認機能
2. 🔄 詳細なログ出力
3. 🔄 テストケースの追加

### Phase 3: 最適化（2週間以内）
1. 🔮 パフォーマンス改善
2. 🔮 キャッシュ機能の追加
3. 🔮 並列処理の最適化

## 検証方法

### 1. ローカル検証
```bash
# act直接実行での検証
act -W .github/workflows/quality-gates.yml -j quality-gate-setup --rm

# Actions Simulatorでの検証（推奨）
uv run main.py actions simulate .github/workflows/quality-gates.yml --event push --job quality-gate-setup
```

### 2. 複数環境での検証
- ✅ 新しいGitリポジトリ
- ✅ 既存のGitリポジトリ
- ✅ PRイベント
- ✅ pushイベント
- ✅ 手動実行

### 3. 回帰テスト
- ✅ 既存の成功ケースが引き続き動作することを確認
- ✅ 新しい失敗ケースが適切に処理されることを確認

## 期待される効果

### 🎯 改善効果
1. **実行成功率の向上**: 90%以上の成功率を目標
2. **環境依存性の削減**: Git設定に依存しない動作
3. **エラーメッセージの改善**: 問題の特定と解決が容易

### 📊 測定指標
- 実行成功率: 現在 < 50% → 目標 > 90%
- 平均実行時間: 現在の時間を維持
- エラー解決時間: 50%短縮を目標

---

**作成日時**: 2025-09-29 11:30:00 UTC
**優先度**: 高（緊急修正が必要）
**担当**: GitHub Actions Quality Gate Team
