<#
.SYNOPSIS
    setup-tls.ps1 の .env 更新・証明書再利用判定ロジック。

.DESCRIPTION
    Pester から単体テストできるよう、対象パスはすべて引数で受け取る（#204）。
    mkcert / winget / 証明書ストアなど環境に依存する処理は setup-tls.ps1 本体に残す。
#>

# BOM 付き UTF-8 は Makefile の awk 抽出や docker compose の .env 解析を壊すため、
# 書き込みは常に BOM なし UTF-8 で行う。
function Write-EnvFile {
    param(
        [Parameter(Mandatory)][string]$Path,
        [string[]]$Lines
    )
    [System.IO.File]::WriteAllLines($Path, $Lines, [System.Text.UTF8Encoding]::new($false))
}

function Set-EnvValue {
    # .env 1 ファイルへの軽量な書き込みであり -WhatIf / -Confirm の対象にしない
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSUseShouldProcessForStateChangingFunctions', '')]
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Key,
        [Parameter(Mandatory)][string]$Value
    )
    # PowerShell 5.1 の Get-Content 既定は BOM なし UTF-8 を ANSI と誤認するため明示する
    $lines = @(Get-Content -Path $Path -Encoding UTF8)
    $pattern = "^\s*$([regex]::Escape($Key))\s*="
    $newLine = "$Key=$Value"
    $replaced = $false
    $lines = @($lines | ForEach-Object {
        if (-not $replaced -and $_ -match $pattern) {
            $replaced = $true
            $newLine
        } else {
            $_
        }
    })
    if (-not $replaced) {
        $lines += $newLine
    }
    Write-EnvFile -Path $Path -Lines $lines
    Write-Host "  $newLine"
}

function Get-EnvValue {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Key
    )
    if (-not (Test-Path $Path)) { return $null }
    $line = @(Get-Content -Path $Path -Encoding UTF8) |
        Where-Object { $_ -match "^\s*$([regex]::Escape($Key))\s*=" } |
        Select-Object -Last 1
    if (-not $line) { return $null }
    return ($line -split '=', 2)[1].Trim()
}

# User スコープ環境変数 NODE_EXTRA_CA_CERTS の扱いを判定する（#217）。
# .env は docker compose にしか渡らないため、ホスト側で直接起動する Node 製
# MCP クライアント（mcp-resource-subscriber 等）には User スコープでの設定が必要。
#   set      — 未設定（要設定）
#   noop     — 既に同じパスを指している（区切り文字・大文字小文字の差は無視）
#   conflict — 別の値が設定済み。NODE_EXTRA_CA_CERTS は 1 ファイルしか指定
#              できないため上書きせず、呼び出し側で警告する
function Get-NodeExtraCaCertsAction {
    param(
        [string]$CurrentValue,
        [Parameter(Mandatory)][string]$DesiredValue
    )
    if ([string]::IsNullOrWhiteSpace($CurrentValue)) {
        return 'set'
    }
    $current = ($CurrentValue.Trim() -replace '\\', '/')
    $desired = ($DesiredValue.Trim() -replace '\\', '/')
    if ($current -ieq $desired) {
        return 'noop'
    }
    return 'conflict'
}

# 証明書生成時に記録した CA fingerprint と現在の rootCA.pem の fingerprint を比較し、
# 既存証明書の扱いを判定する。CA 再生成（CAROOT 削除→再実行等）後に旧 CA 署名の
# 証明書を再利用して HTTPS 接続が失敗するのを防ぐ（PR #203 レビュー指摘）。
#   reusable   — 証明書・鍵・fingerprint 記録が揃っており、現在の CA と一致
#   ca-changed — ファイルは揃っているが CA が変わっている（要再生成）
#   missing    — いずれかのファイルが存在しない（要生成）
function Get-CertReuseState {
    param(
        [Parameter(Mandatory)][string]$CertFile,
        [Parameter(Mandatory)][string]$KeyFile,
        [Parameter(Mandatory)][string]$FingerprintFile,
        [Parameter(Mandatory)][string]$CaFingerprint
    )
    if (-not ((Test-Path $CertFile) -and (Test-Path $KeyFile) -and (Test-Path $FingerprintFile))) {
        return 'missing'
    }
    $recorded = @(Get-Content -Path $FingerprintFile -Encoding UTF8)[0]
    if ($recorded -and $recorded.Trim() -eq $CaFingerprint) {
        return 'reusable'
    }
    return 'ca-changed'
}
