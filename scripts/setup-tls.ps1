<#
.SYNOPSIS
    ローカル HTTPS (TLS) 接続のためのホストセットアップを自動化する。

.DESCRIPTION
    mcp-gateway の TLS 終端（MCP_GATEWAY_TLS_CERT_PATH / MCP_GATEWAY_TLS_KEY_PATH）
    に必要なホスト側の環境構築を行う:
      1. winget による mkcert の非対話インストール
      2. mkcert ローカル CA の生成と信頼登録（この処理のみ UAC 昇格）
      3. ./config/certs/ への localhost / 127.0.0.1 宛て証明書の生成
      4. .env の自動構成（MCP_GATEWAY_PUBLIC_URL / TLS パス / NODE_EXTRA_CA_CERTS）

    実行方法: make setup-tls
    関連: Mcp-Docker#202 / mcp-gateway#201
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot
$CertDir = Join-Path $RepoRoot 'config\certs'
$EnvFile = Join-Path $RepoRoot '.env'
$EnvTemplate = Join-Path $RepoRoot '.env.template'

function Resolve-MkcertPath {
    $cmd = Get-Command mkcert -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

# BOM 付き UTF-8 は Makefile の awk 抽出や docker compose の .env 解析を壊すため、
# 書き込みは常に BOM なし UTF-8 で行う。
function Write-EnvFileLines {
    param([string[]]$Lines)
    [System.IO.File]::WriteAllLines($EnvFile, $Lines, [System.Text.UTF8Encoding]::new($false))
}

function Set-EnvValue {
    param([string]$Key, [string]$Value)
    # PowerShell 5.1 の Get-Content 既定は BOM なし UTF-8 を ANSI と誤認するため明示する
    $lines = @(Get-Content -Path $EnvFile -Encoding UTF8)
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
    Write-EnvFileLines -Lines $lines
    Write-Host "  $newLine"
}

function Get-EnvValue {
    param([string]$Key)
    if (-not (Test-Path $EnvFile)) { return $null }
    $line = @(Get-Content -Path $EnvFile -Encoding UTF8) |
        Where-Object { $_ -match "^\s*$([regex]::Escape($Key))\s*=" } |
        Select-Object -Last 1
    if (-not $line) { return $null }
    return ($line -split '=', 2)[1].Trim()
}

# ---------------------------------------------------------------------------
# 1. mkcert のインストール
# ---------------------------------------------------------------------------
$mkcert = Resolve-MkcertPath
if (-not $mkcert) {
    Write-Host '📦 mkcert が見つかりません。winget でインストールします...'
    winget install --id FiloSottile.mkcert --exact --silent --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "winget による mkcert のインストールに失敗しました (exit=$LASTEXITCODE)"
    }
    # インストール直後は現在のセッションに PATH 変更が反映されないため再読込する
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
        [Environment]::GetEnvironmentVariable('Path', 'User')
    $mkcert = Resolve-MkcertPath
    if (-not $mkcert) {
        throw 'mkcert をインストールしましたが PATH 上に見つかりません。新しいターミナルで再実行してください。'
    }
}
Write-Host "✅ mkcert: $mkcert"

# ---------------------------------------------------------------------------
# 2. ローカル CA の生成と信頼登録
# ---------------------------------------------------------------------------
$caRoot = (& $mkcert -CAROOT).Trim()
if (-not $caRoot) {
    throw 'mkcert -CAROOT が CA ディレクトリを返しませんでした'
}
$rootCaPem = Join-Path $caRoot 'rootCA.pem'

$caTrusted = @(Get-ChildItem Cert:\CurrentUser\Root -ErrorAction SilentlyContinue |
    Where-Object { $_.Subject -match 'mkcert' }).Count -gt 0

if ((Test-Path $rootCaPem) -and $caTrusted) {
    Write-Host "✅ mkcert ローカル CA は信頼登録済みです: $caRoot"
} else {
    Write-Host '🔐 ローカル CA を生成・信頼登録します（UAC の確認ダイアログが表示されます）...'
    # スクリプト全体を管理者として起動するとカレントディレクトリが System32 に
    # 変わり相対パスが混乱するため、mkcert -install の実行だけを局所的に昇格する。
    $proc = Start-Process -FilePath $mkcert -ArgumentList '-install' -Verb RunAs -Wait -PassThru
    if ($proc.ExitCode -ne 0) {
        throw "mkcert -install に失敗しました (exit=$($proc.ExitCode))"
    }
    if (-not (Test-Path $rootCaPem)) {
        throw "mkcert -install 後も rootCA.pem が見つかりません: $rootCaPem"
    }
    Write-Host "✅ ローカル CA を信頼登録しました: $caRoot"
}

# ---------------------------------------------------------------------------
# 3. localhost / 127.0.0.1 宛て証明書の生成
# ---------------------------------------------------------------------------
New-Item -ItemType Directory -Force -Path $CertDir | Out-Null
$certFile = Join-Path $CertDir 'localhost.pem'
$keyFile = Join-Path $CertDir 'localhost-key.pem'

# 証明書生成時の CA fingerprint を記録し、CA 再生成（CAROOT 削除→再実行等）後に
# 旧 CA 署名の証明書を再利用して HTTPS 接続が失敗するのを防ぐ
$caFingerprintFile = Join-Path $CertDir '.ca-fingerprint'
$caFingerprint = (Get-FileHash -Path $rootCaPem -Algorithm SHA256).Hash

$reuseCert = $false
if ((Test-Path $certFile) -and (Test-Path $keyFile) -and (Test-Path $caFingerprintFile)) {
    $recorded = @(Get-Content -Path $caFingerprintFile -Encoding UTF8)[0]
    if ($recorded -and $recorded.Trim() -eq $caFingerprint) {
        $reuseCert = $true
    } else {
        Write-Host '⚠️  ローカル CA が変更されています。証明書を再生成します...'
    }
}

if ($reuseCert) {
    Write-Host "✅ サーバー証明書は生成済みです（現在の CA と一致）: $certFile"
} else {
    Write-Host '📜 localhost / 127.0.0.1 宛ての証明書を生成します...'
    & $mkcert -cert-file $certFile -key-file $keyFile localhost 127.0.0.1
    if ($LASTEXITCODE -ne 0) {
        throw "mkcert による証明書生成に失敗しました (exit=$LASTEXITCODE)"
    }
    [System.IO.File]::WriteAllText($caFingerprintFile, "$caFingerprint`n", [System.Text.UTF8Encoding]::new($false))
    Write-Host "✅ 証明書を生成しました: $certFile"
}

# ---------------------------------------------------------------------------
# 4. .env の自動構成
# ---------------------------------------------------------------------------
if (-not (Test-Path $EnvFile)) {
    Copy-Item -Path $EnvTemplate -Destination $EnvFile
    Write-Host "📄 .env を .env.template から作成しました"
}

$port = Get-EnvValue 'MCP_GATEWAY_PORT'
if (-not $port) { $port = '8080' }

Write-Host '🔧 .env を HTTPS 用に更新します:'
Set-EnvValue 'MCP_GATEWAY_PUBLIC_URL' "https://localhost:$port"
# コンテナ内パス（docker-compose.yml の ./config/certs -> /data/certs マウントに対応）
Set-EnvValue 'MCP_GATEWAY_TLS_CERT_PATH' '/data/certs/localhost.pem'
Set-EnvValue 'MCP_GATEWAY_TLS_KEY_PATH' '/data/certs/localhost-key.pem'
# Node.js はバックスラッシュ区切りパスをエスケープと誤認するためスラッシュに変換する
$rootCaPemFwd = $rootCaPem -replace '\\', '/'
Set-EnvValue 'NODE_EXTRA_CA_CERTS' $rootCaPemFwd

Write-Host ''
Write-Host '🎉 TLS セットアップが完了しました'
Write-Host ''
Write-Host '次のステップ:'
Write-Host "  1. GitHub App の Callback URL を https://localhost:$port/callback と"
Write-Host "     https://localhost:$port/device_callback に更新してください"
Write-Host '  2. make restart-gateway でサービスを再起動してください'
Write-Host "  3. IDE / CLI の MCP エンドポイントを https://localhost:$port/... に更新してください（make register-all）"
