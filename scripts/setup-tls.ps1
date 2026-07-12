<#
.SYNOPSIS
    ローカル HTTPS (TLS) 接続のためのホストセットアップを自動化する。

.DESCRIPTION
    mcp-gateway の TLS 終端（MCP_GATEWAY_TLS_CERT_PATH / MCP_GATEWAY_TLS_KEY_PATH）
    に必要なホスト側の環境構築を行う:
      1. winget による mkcert の非対話インストール
      2. mkcert ローカル CA の生成と信頼登録（実行ユーザーの証明書ストア）
      3. ./config/certs/ への localhost / 127.0.0.1 宛て証明書の生成
      4. .env の自動構成（MCP_GATEWAY_PUBLIC_URL / TLS パス / NODE_EXTRA_CA_CERTS）

    実行方法: make setup-tls
    関連: Mcp-Docker#202 / mcp-gateway#201
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

# Git Bash 等、コンソールを持たないパイプ経由で標準出力が消費される場合、
# PowerShell はシステムのレガシーコードページ（日本語環境では CP932）で
# Write-Host を出力し、日本語文字列が文字化けする。UTF-8 に固定して回避する。
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$RepoRoot = Split-Path -Parent $PSScriptRoot
$CertDir = Join-Path $RepoRoot 'config\certs'
$EnvFile = Join-Path $RepoRoot '.env'
$EnvTemplate = Join-Path $RepoRoot '.env.template'

# .env 更新・証明書再利用判定は Pester で単体テストするため lib に分離している（#204）
. (Join-Path $PSScriptRoot 'lib\setup-tls-functions.ps1')

function Resolve-MkcertPath {
    $cmd = Get-Command mkcert -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
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
    Write-Host '🔐 ローカル CA を生成・信頼登録します...'
    # mkcert は現在の Windows ユーザーの ROOT 証明書ストアへ登録する。RunAs で
    # 昇格すると管理者のプロファイル・証明書ストアが対象となり、呼び出し元の
    # ユーザーには CA が作成・信頼登録されない。Java の cacerts への登録も不要で、
    # JAVA_HOME がある通常ユーザー環境ではアクセス拒否になるため対象を system に絞る。
    $previousTrustStores = $env:TRUST_STORES
    try {
        $env:TRUST_STORES = 'system'
        & $mkcert -install
        $mkcertExitCode = $LASTEXITCODE
    } finally {
        $env:TRUST_STORES = $previousTrustStores
    }
    if ($mkcertExitCode -ne 0) {
        throw "mkcert -install に失敗しました (exit=$mkcertExitCode)"
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

$certState = Get-CertReuseState -CertFile $certFile -KeyFile $keyFile -FingerprintFile $caFingerprintFile -CaFingerprint $caFingerprint
if ($certState -eq 'ca-changed') {
    Write-Host '⚠️  ローカル CA が変更されています。証明書を再生成します...'
}

if ($certState -eq 'reusable') {
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

$port = Get-EnvValue -Path $EnvFile -Key 'MCP_GATEWAY_PORT'
if (-not $port) { $port = '8080' }

Write-Host '🔧 .env を HTTPS 用に更新します:'
Set-EnvValue -Path $EnvFile -Key 'MCP_GATEWAY_PUBLIC_URL' -Value "https://localhost:$port"
# コンテナ内パス（docker-compose.yml の ./config/certs -> /data/certs マウントに対応）
Set-EnvValue -Path $EnvFile -Key 'MCP_GATEWAY_TLS_CERT_PATH' -Value '/data/certs/localhost.pem'
Set-EnvValue -Path $EnvFile -Key 'MCP_GATEWAY_TLS_KEY_PATH' -Value '/data/certs/localhost-key.pem'
# Node.js はバックスラッシュ区切りパスをエスケープと誤認するためスラッシュに変換する
$rootCaPemFwd = $rootCaPem -replace '\\', '/'
Set-EnvValue -Path $EnvFile -Key 'NODE_EXTRA_CA_CERTS' -Value $rootCaPemFwd

# ---------------------------------------------------------------------------
# 5. ユーザー環境変数 NODE_EXTRA_CA_CERTS の設定
# ---------------------------------------------------------------------------
# .env は docker compose にしか渡らない。ホスト側で直接起動する Node 製 MCP
# クライアント（mcp-resource-subscriber 等）は Windows 証明書ストアを参照しない
# ため、User スコープ環境変数として mkcert ローカル CA を信頼させる（#217）。
$currentUserCa = [Environment]::GetEnvironmentVariable('NODE_EXTRA_CA_CERTS', 'User')
switch (Get-NodeExtraCaCertsAction -CurrentValue $currentUserCa -DesiredValue $rootCaPemFwd) {
    'set' {
        [Environment]::SetEnvironmentVariable('NODE_EXTRA_CA_CERTS', $rootCaPemFwd, 'User')
        Write-Host "✅ ユーザー環境変数 NODE_EXTRA_CA_CERTS を設定しました: $rootCaPemFwd"
        Write-Host '   既に起動中のアプリ・シェルには反映されません。クライアントを再起動してください。'
    }
    'noop' {
        Write-Host "✅ ユーザー環境変数 NODE_EXTRA_CA_CERTS は設定済みです: $currentUserCa"
    }
    'conflict' {
        Write-Host "⚠️  ユーザー環境変数 NODE_EXTRA_CA_CERTS に別の値が設定されています: $currentUserCa"
        Write-Host '   NODE_EXTRA_CA_CERTS は 1 ファイルしか指定できないため上書きしません。'
        Write-Host "   mkcert CA も信頼させる場合は、既存 PEM と $rootCaPemFwd を連結した"
        Write-Host '   ファイルを作成し、NODE_EXTRA_CA_CERTS をそのファイルに変更してください。'
    }
}

Write-Host ''
Write-Host '🎉 TLS セットアップが完了しました'
Write-Host ''
Write-Host '次のステップ:'
Write-Host "  1. GitHub App の Callback URL を https://localhost:$port/callback と"
Write-Host "     https://localhost:$port/device_callback に更新してください"
Write-Host '  2. make restart-gateway でサービスを再起動してください'
Write-Host "  3. IDE / CLI の MCP エンドポイントを https://localhost:$port/... に更新してください（make register-all）"
