@{
    ExcludeRules = @(
        # 対話型セットアップスクリプトの進行表示に意図的に使用している
        # （PowerShell 5.0+ では information stream に乗るため抑止・リダイレクト可能）
        'PSAvoidUsingWriteHost',
        # リポジトリ標準は BOM なし UTF-8（BOM は Makefile の awk 抽出や
        # docker compose の .env 解析を壊すため、.ps1 も同一ポリシーで統一する）
        'PSUseBOMForUnicodeEncodedFile'
    )
}
