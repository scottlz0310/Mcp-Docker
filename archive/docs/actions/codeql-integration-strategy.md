# GitHub Actions Simulator - CodeQL統合仕様

## 🔍 統合戦略：既存CodeQL活用

### 現状分析

**既存CodeQL実装状況：**
- `services/codeql/config.yml`：設定済み（Python, JavaScript等対応）
- `.github/workflows/security.yml`：稼働中のCodeQLワークフロー
- `Dockerfile`：CodeQL CLIバイナリ組み込み済み
- `main.py`：`python main.py codeql`で実行可能（未実装だが準備済み）

### 統合方針

**✅ 推奨アプローチ：CodeQL統合（廃止しない）**

理由：
1. **既存資産活用**：動作するCodeQL環境を無駄にしない
2. **Actions関連性**：CodeQLはGitHub Actionsの核心コンポーネント
3. **セキュリティ重要性**：静的分析は開発ワークフローに必須
4. **実用性向上**：ローカル環境でもCodeQL実行可能

## 🏗️ 技術実装設計

### Actions Simulator内でのCodeQL統合

```python
# services/actions/codeql_integration.py
import subprocess
import os
from pathlib import Path
from typing import Dict, List, Optional

class CodeQLIntegration:
    def __init__(self):
        self.codeql_config = self.load_config()
        self.codeql_binary = "/opt/codeql/codeql/codeql"

    def load_config(self) -> Dict:
        """既存のCodeQL設定を読み込み"""
        config_path = Path("services/codeql/config.yml")
        with open(config_path) as f:
            return yaml.safe_load(f)

    def detect_codeql_in_workflow(self, workflow_dict: Dict) -> bool:
        """ワークフローにCodeQLが含まれているかチェック"""
        for job in workflow_dict.get('jobs', {}).values():
            for step in job.get('steps', []):
                if 'github/codeql-action/' in str(step.get('uses', '')):
                    return True
        return False

    def run_codeql_analysis(self, languages: List[str] = None) -> Dict:
        """既存のCodeQLサービスを呼び出し"""
        if languages is None:
            languages = self.codeql_config['analyzer']['languages']

        print("🔍 CodeQL分析を実行中...")
        result = subprocess.run([
            "python", "main.py", "codeql"
        ], capture_output=True, text=True, cwd=os.getcwd())

        return {
            'status': 'success' if result.returncode == 0 else 'failed',
            'stdout': result.stdout,
            'stderr': result.stderr,
            'languages': languages
        }

# services/actions/cli.py での統合使用例
from .codeql_integration import CodeQLIntegration

@click.command()
@click.argument('workflow')
@click.option('--include-codeql/--skip-codeql', default=True)
@click.option('--codeql-languages', multiple=True)
def simulate(workflow, include_codeql, codeql_languages):
    """GitHub Actionsワークフローのシミュレーション"""

    # 1. ワークフロー解析
    workflow_dict = parse_workflow(workflow)

    # 2. CodeQL統合判定
    codeql = CodeQLIntegration()
    has_codeql = codeql.detect_codeql_in_workflow(workflow_dict)

    # 3. act実行
    act_result = act_wrapper.run(workflow)

    # 4. CodeQL実行（必要な場合）
    if include_codeql and has_codeql:
        languages = list(codeql_languages) if codeql_languages else None
        codeql_result = codeql.run_codeql_analysis(languages)

        print("\n📊 CodeQL分析結果:")
        if codeql_result['status'] == 'success':
            print("✅ CodeQL分析完了")
        else:
            print("❌ CodeQL分析エラー:")
            print(codeql_result['stderr'])

    return {
        'act_result': act_result,
        'codeql_result': codeql_result if has_codeql else None
    }
```

## 🎯 使用パターン

### 1. 既存CodeQL単体実行（継続）

```bash
# 従来通りの使用方法
python main.py codeql
make codeql

# Docker経由
docker compose --profile tools run --rm codeql
```

### 2. Actions Simulator統合実行（新機能）

```bash
# Security workflowの完全シミュレーション
python main.py actions simulate .github/workflows/security.yml

# CodeQLを含むCI workflowのシミュレーション
python main.py actions simulate .github/workflows/ci.yml --include-codeql

# 特定言語のみCodeQL実行
python main.py actions simulate security.yml --codeql-languages python

# CodeQLをスキップして高速実行
python main.py actions simulate ci.yml --skip-codeql
```

### 3. 開発ワークフロー統合

```bash
# コミット前の完全チェック
git add .
python main.py actions simulate ci.yml --include-codeql
git commit -m "fix: implement feature"

# プルリクエスト前の事前確認
python main.py actions simulate .github/workflows/security.yml
```

## 📋 実装段階

### Phase 1: 基本統合（1週間）

- [ ] `services/actions/codeql_integration.py`作成
- [ ] 既存`services/codeql/config.yml`読み込み機能
- [ ] Actions Simulator内でのCodeQL呼び出し
- [ ] 基本的な結果統合・表示

### Phase 2: 高度統合（2週間）

- [ ] ワークフロー内CodeQL自動検出
- [ ] 言語別CodeQL実行制御
- [ ] SARIF結果ファイル統合
- [ ] レポート生成機能

### Phase 3: 最適化（1週間）

- [ ] キャッシュ機能（CodeQL DB再利用）
- [ ] 並列実行最適化
- [ ] 詳細ログ・デバッグ機能

## 🎉 期待効果

### 統合によるメリット

1. **既存資産活用**
   - `services/codeql/`の設定・実装を無駄にしない
   - GitHub Actions workflows（security.yml）の検証が完全に

2. **開発効率向上**
   - ローカルでのCodeQL実行でセキュリティ問題を事前発見
   - CI/CD失敗を大幅削減

3. **一貫性保持**
   - `make codeql`と`python main.py actions`両方で利用
   - 既存チームワークフローとの互換性

4. **実用性**
   - Security workflowsの完全ローカル実行
   - プルリクエスト前の包括的検証

### 🚀 結論

**CodeQLは廃止せず、Actions Simulatorに統合する**ことで：

- 既存の投資を最大活用
- GitHub Actionsシミュレーションの完全性を確保
- セキュリティワークフローの実用性を大幅向上

この統合アプローチにより、真に実用的なGitHub Actions Simulatorを実現できます。
