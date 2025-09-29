# パス解決問題の最終修正

## 現状の問題

1. **パス重複**: actが`.github/workflows/.github/workflows/ci.yml`を探している
2. **デバッグログ未表示**: ログレベルの問題でデバッグ情報が表示されない

## 解決策

### 1. 確実な絶対パス使用
ワークフローファイルを絶対パスで指定し、パス重複を完全に回避する。

### 2. ログレベル修正
デバッグログが確実に表示されるようにする。

### 3. 実装

```python
# 絶対パスを確実に使用
absolute_workflow_path = Path("/app/.github/workflows") / Path(workflow_file).name
if absolute_workflow_path.exists():
    final_workflow = str(absolute_workflow_path)
```

これにより、actは絶対パス `/app/.github/workflows/ci.yml` を受け取り、パス重複が発生しない。
