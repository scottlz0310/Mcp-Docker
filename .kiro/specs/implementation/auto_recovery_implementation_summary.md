# AutoRecovery Implementation Summary

## 概要

GitHub Actions Simulatorのハングアップ問題を解決するため、自動復旧メカニズム（AutoRecovery）を実装しました。この機能は、Docker再接続、サブプロセス再起動、バッファクリア、コンテナ状態リセット、フォールバック実行モードを提供します。

## 実装されたコンポーネント

### 1. AutoRecovery クラス (`services/actions/auto_recovery.py`)

#### 主要機能
- **Docker再接続**: Docker daemonとの接続を自動的に復旧
- **サブプロセス再起動**: ハングしたプロセスの段階的終了と再起動
- **バッファクリア**: システムバッファとメモリの清理
- **コンテナ状態リセット**: 孤立したコンテナとリソースの削除
- **フォールバック実行**: プライマリ実行が失敗した場合の代替実行モード

#### データモデル
- `RecoveryAttempt`: 個別の復旧試行記録
- `RecoverySession`: 包括的復旧セッション情報
- `FallbackExecutionResult`: フォールバック実行結果

#### 復旧タイプ
```python
class RecoveryType(Enum):
    DOCKER_RECONNECTION = "docker_reconnection"
    SUBPROCESS_RESTART = "subprocess_restart"
    BUFFER_CLEAR = "buffer_clear"
    CONTAINER_RESET = "container_reset"
    FALLBACK_MODE = "fallback_mode"
```

### 2. EnhancedActWrapper統合

#### 新しいメソッド
- `run_workflow_with_auto_recovery()`: 自動復旧機能付きワークフロー実行
- `get_auto_recovery_statistics()`: 復旧統計情報取得
- `_build_act_command()`: actコマンド構築ヘルパー

#### 復旧フロー
1. プライマリ実行試行
2. 失敗時に包括的復旧処理実行
3. 復旧後の再実行試行
4. フォールバック実行（必要に応じて）

### 3. フォールバック実行モード

#### 実行方法
1. **direct_docker_run**: 直接Dockerコンテナでワークフロー解析
2. **simplified_act_execution**: 簡略化されたact実行（ドライラン）
3. **dry_run_mode**: ワークフローファイルの基本解析と表示

## 実装詳細

### Docker再接続メカニズム

```python
def attempt_docker_reconnection(self) -> bool:
    # 1. 現在の接続状態確認
    # 2. Docker daemon再起動試行
    # 3. Socket権限修正試行
    # 4. 再接続確認
```

### プロセス再起動メカニズム

```python
def restart_hung_subprocess(self, process: subprocess.Popen) -> bool:
    # 1. プロセス状態確認
    # 2. SIGTERM送信
    # 3. プロセスグループ終了
    # 4. SIGKILL強制終了
```

### 包括的復旧処理

```python
def run_comprehensive_recovery(self, ...) -> RecoverySession:
    # 1. 出力バッファクリア
    # 2. ハングプロセス再起動
    # 3. Docker再接続
    # 4. コンテナ状態リセット
    # 5. フォールバック実行（必要時）
```

## テスト実装

### 単体テスト (`tests/test_auto_recovery.py`)
- 23個のテストケース
- 全ての主要機能をカバー
- モックを使用した安全なテスト環境

### 統合テスト (`tests/test_enhanced_act_wrapper_with_recovery.py`)
- 10個のテストケース
- EnhancedActWrapperとの統合をテスト
- 実際の使用シナリオを検証

## 使用例

### 基本的な自動復旧

```python
from services.actions.auto_recovery import AutoRecovery

auto_recovery = AutoRecovery()

# Docker再接続
success = auto_recovery.attempt_docker_reconnection()

# 包括的復旧
session = auto_recovery.run_comprehensive_recovery(
    workflow_file=Path("workflow.yml"),
    original_command=["act", "--list"]
)
```

### EnhancedActWrapperでの使用

```python
from services.actions.enhanced_act_wrapper import EnhancedActWrapper

wrapper = EnhancedActWrapper(enable_diagnostics=True)

result = wrapper.run_workflow_with_auto_recovery(
    workflow_file="workflow.yml",
    enable_recovery=True,
    max_recovery_attempts=2
)
```

## パフォーマンス特性

### 復旧時間
- Docker再接続: 5-30秒
- バッファクリア: 1-3秒
- コンテナリセット: 10-60秒
- フォールバック実行: 1-10秒

### リソース使用量
- メモリ使用量: 最小限（主にログとセッション情報）
- CPU使用量: 復旧処理中のみ一時的に増加
- ディスク使用量: ログファイルとデバッグ情報のみ

## 設定オプション

### AutoRecovery設定

```python
AutoRecovery(
    max_recovery_attempts=3,        # 最大復旧試行回数
    recovery_timeout=60.0,          # 復旧タイムアウト（秒）
    docker_reconnect_timeout=30.0,  # Docker再接続タイムアウト
    enable_fallback_mode=True       # フォールバックモード有効化
)
```

### EnhancedActWrapper設定

```python
wrapper.run_workflow_with_auto_recovery(
    enable_recovery=True,           # 自動復旧有効化
    max_recovery_attempts=2         # 最大復旧試行回数
)
```

## エラーハンドリング

### 復旧失敗時の動作
1. 詳細なエラーログ出力
2. 復旧統計情報の更新
3. 診断結果への失敗情報追加
4. フォールバック実行の試行

### 例外処理
- 全ての復旧操作で例外をキャッチ
- 部分的成功でも継続実行
- タイムアウト処理の実装

## 監視とログ

### ログレベル
- **INFO**: 復旧開始・完了・成功
- **WARNING**: 部分的失敗・警告
- **ERROR**: 復旧失敗・エラー
- **DEBUG**: 詳細な実行ステップ

### 統計情報
```python
{
    "total_sessions": 5,
    "successful_sessions": 4,
    "success_rate": 0.8,
    "recovery_type_statistics": {
        "docker_reconnection": {"total": 5, "success": 5},
        "container_reset": {"total": 3, "success": 2}
    }
}
```

## 今後の拡張可能性

### 追加可能な復旧方法
- ネットワーク設定リセット
- 環境変数の再設定
- 一時ファイルの完全削除
- システムリソースの最適化

### 設定の改善
- 復旧方法の優先順位設定
- 条件付き復旧実行
- カスタム復旧スクリプト実行

## 要件との対応

### Requirement 4.1 (根本原因の修正)
✅ Docker再接続とプロセス管理の改善により対応

### Requirement 4.2 (プロセス管理の改善)
✅ 段階的プロセス終了とリソースクリーンアップで対応

### Requirement 4.3 (タイムアウト処理の強化)
✅ 細かいタイムアウト制御とエスカレーション機能で対応

## まとめ

AutoRecovery機能の実装により、GitHub Actions Simulatorのハングアップ問題に対する包括的な解決策を提供しました。この機能は：

1. **自動化**: 手動介入なしで問題を検出・修正
2. **段階的**: 穏やかな方法から強制的な方法まで段階的に実行
3. **フォールバック**: プライマリ実行が失敗してもサービス継続
4. **監視**: 詳細な統計とログで問題追跡が可能
5. **統合**: 既存のEnhancedActWrapperとシームレスに統合

これにより、ユーザーはより信頼性の高いGitHub Actionsシミュレーション環境を利用できるようになりました。
