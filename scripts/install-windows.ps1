# GitHub Actions Simulator - Windows インストールスクリプト
#
# このスクリプトは Windows 環境での GitHub Actions Simulator の
# 自動インストールを支援します。
#
# 使用方法:
#   PowerShell を管理者として実行し、以下のコマンドを実行:
#   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
#   .\scripts\install-windows.ps1

param(
    [switch]$Help,
    [switch]$DockerOnly,
    [switch]$SkipOptimization,
    [switch]$VerifyOnly,
    [switch]$WSLOnly
)

# カラー出力の設定
$ErrorActionPreference = "Stop"

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ️  $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

# Windows バージョン確認
function Test-WindowsVersion {
    Write-Info "Windows バージョンを確認中..."

    $version = [System.Environment]::OSVersion.Version
    $build = (Get-ItemProperty "HKLM:SOFTWARE\Microsoft\Windows NT\CurrentVersion").CurrentBuild

    Write-Info "Windows バージョン: $($version.Major).$($version.Minor) (Build: $build)"

    # Windows 10 version 2004 (build 19041) 以降、または Windows 11 が必要
    if ($version.Major -lt 10 -or ($version.Major -eq 10 -and $build -lt 19041)) {
        Write-Error "Windows 10 version 2004 (build 19041) 以降、または Windows 11 が必要です"
        Write-Error "現在のバージョン: $($version.Major).$($version.Minor) (Build: $build)"
        exit 1
    }

    Write-Success "Windows バージョンは要件を満たしています"
}

# 管理者権限確認
function Test-AdminRights {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    $isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

    if (-not $isAdmin) {
        Write-Error "このスクリプトは管理者権限で実行する必要があります"
        Write-Info "PowerShell を右クリックして「管理者として実行」を選択してください"
        exit 1
    }

    Write-Success "管理者権限で実行されています"
}

# WSL2 の有効化
function Enable-WSL2 {
    Write-Info "WSL2 を有効化中..."

    # WSL 機能の有効化
    $wslFeature = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux
    if ($wslFeature.State -ne "Enabled") {
        Write-Info "WSL 機能を有効化中..."
        Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -All -NoRestart
    }

    # 仮想マシン プラットフォーム機能の有効化
    $vmFeature = Get-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform
    if ($vmFeature.State -ne "Enabled") {
        Write-Info "仮想マシン プラットフォーム機能を有効化中..."
        Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -All -NoRestart
    }

    # Hyper-V の確認（必要に応じて）
    $hyperVFeature = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All
    if ($hyperVFeature.State -ne "Enabled") {
        Write-Warning "Hyper-V が無効です。Docker Desktop の動作に影響する可能性があります"
        $response = Read-Host "Hyper-V を有効化しますか？ (y/N)"
        if ($response -match "^[Yy]$") {
            Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All -NoRestart
        }
    }

    Write-Success "WSL2 機能の有効化が完了しました"
}

# WSL カーネル更新
function Update-WSLKernel {
    Write-Info "WSL カーネルを更新中..."

    $kernelUrl = "https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi"
    $kernelPath = "$env:TEMP\wsl_update_x64.msi"

    try {
        Write-Info "WSL カーネル更新プログラムをダウンロード中..."
        Invoke-WebRequest -Uri $kernelUrl -OutFile $kernelPath

        Write-Info "WSL カーネル更新プログラムをインストール中..."
        Start-Process -FilePath "msiexec.exe" -ArgumentList "/i", $kernelPath, "/quiet" -Wait

        Remove-Item $kernelPath -Force
        Write-Success "WSL カーネルの更新が完了しました"
    }
    catch {
        Write-Warning "WSL カーネルの自動更新に失敗しました: $($_.Exception.Message)"
        Write-Info "手動でダウンロードしてインストールしてください: $kernelUrl"
    }
}

# WSL2 をデフォルトに設定
function Set-WSL2Default {
    Write-Info "WSL2 をデフォルトバージョンに設定中..."

    try {
        & wsl --set-default-version 2
        Write-Success "WSL2 がデフォルトバージョンに設定されました"
    }
    catch {
        Write-Warning "WSL2 のデフォルト設定に失敗しました: $($_.Exception.Message)"
    }
}

# Ubuntu ディストリビューションのインストール
function Install-UbuntuWSL {
    Write-Info "Ubuntu WSL ディストリビューションをインストール中..."

    # 既存のディストリビューション確認
    $existingDistros = & wsl --list --quiet 2>$null
    if ($existingDistros -contains "Ubuntu") {
        Write-Success "Ubuntu WSL は既にインストールされています"
        return
    }

    try {
        & wsl --install -d Ubuntu
        Write-Success "Ubuntu WSL のインストールが完了しました"
        Write-Info "初回起動時にユーザー設定を行ってください"
    }
    catch {
        Write-Warning "Ubuntu WSL の自動インストールに失敗しました: $($_.Exception.Message)"
        Write-Info "Microsoft Store から手動でインストールしてください"
    }
}

# Chocolatey のインストール
function Install-Chocolatey {
    Write-Info "Chocolatey をインストール中..."

    if (Get-Command choco -ErrorAction SilentlyContinue) {
        Write-Success "Chocolatey は既にインストールされています"
        return
    }

    try {
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

        # PATH の更新
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")

        Write-Success "Chocolatey のインストールが完了しました"
    }
    catch {
        Write-Warning "Chocolatey の自動インストールに失敗しました: $($_.Exception.Message)"
        Write-Info "手動でインストールしてください: https://chocolatey.org/install"
    }
}

# Docker Desktop のインストール
function Install-DockerDesktop {
    Write-Info "Docker Desktop をインストール中..."

    # Docker Desktop が既にインストールされているかチェック
    $dockerPath = "${env:ProgramFiles}\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $dockerPath) {
        Write-Success "Docker Desktop は既にインストールされています"
        return
    }

    try {
        if (Get-Command choco -ErrorAction SilentlyContinue) {
            # Chocolatey 経由でインストール
            & choco install docker-desktop -y
        }
        else {
            # 手動ダウンロード・インストール
            Write-Info "Docker Desktop を手動でダウンロード中..."
            $dockerUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
            $dockerInstaller = "$env:TEMP\DockerDesktopInstaller.exe"

            Invoke-WebRequest -Uri $dockerUrl -OutFile $dockerInstaller

            Write-Info "Docker Desktop をインストール中..."
            Start-Process -FilePath $dockerInstaller -ArgumentList "install", "--quiet" -Wait

            Remove-Item $dockerInstaller -Force
        }

        Write-Success "Docker Desktop のインストールが完了しました"
    }
    catch {
        Write-Error "Docker Desktop のインストールに失敗しました: $($_.Exception.Message)"
        Write-Info "手動でインストールしてください: https://docs.docker.com/desktop/install/windows-install/"
        exit 1
    }
}

# Docker Desktop の起動
function Start-DockerDesktop {
    Write-Info "Docker Desktop を起動中..."

    $dockerPath = "${env:ProgramFiles}\Docker\Docker\Docker Desktop.exe"
    if (-not (Test-Path $dockerPath)) {
        Write-Error "Docker Desktop が見つかりません: $dockerPath"
        return
    }

    # Docker Desktop が起動しているかチェック
    $dockerProcess = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
    if ($dockerProcess) {
        Write-Success "Docker Desktop は既に起動しています"
        return
    }

    # Docker Desktop を起動
    Start-Process -FilePath $dockerPath

    # Docker が利用可能になるまで待機
    $maxWait = 120
    $waitTime = 0

    Write-Info "Docker の起動を待機中..."
    do {
        Start-Sleep -Seconds 5
        $waitTime += 5

        try {
            & docker info 2>$null | Out-Null
            $dockerReady = $true
        }
        catch {
            $dockerReady = $false
        }

        Write-Host "." -NoNewline
    } while (-not $dockerReady -and $waitTime -lt $maxWait)

    Write-Host ""

    if ($dockerReady) {
        Write-Success "Docker Desktop が正常に起動しました"
    }
    else {
        Write-Warning "Docker の起動がタイムアウトしました"
        Write-Info "手動で Docker Desktop を起動してください"
    }
}

# WSL2 設定の最適化
function Optimize-WSL2Config {
    Write-Info "WSL2 設定を最適化中..."

    $wslConfigPath = "$env:USERPROFILE\.wslconfig"

    if (Test-Path $wslConfigPath) {
        Write-Info "既存の .wslconfig ファイルが見つかりました"
        $backup = "${wslConfigPath}.backup.$(Get-Date -Format 'yyyyMMdd-HHmmss')"
        Copy-Item $wslConfigPath $backup
        Write-Info "バックアップを作成しました: $backup"
    }

    # 最適化された .wslconfig を作成
    $wslConfig = @"
[wsl2]
memory=8GB
processors=4
swap=2GB
localhostForwarding=true

[experimental]
sparseVhd=true
"@

    Set-Content -Path $wslConfigPath -Value $wslConfig -Encoding UTF8
    Write-Success "WSL2 設定ファイルを作成しました: $wslConfigPath"

    Write-Info "設定を適用するため WSL を再起動中..."
    & wsl --shutdown
    Start-Sleep -Seconds 3

    Write-Success "WSL2 設定の最適化が完了しました"
}

# Git のインストール
function Install-Git {
    Write-Info "Git をインストール中..."

    if (Get-Command git -ErrorAction SilentlyContinue) {
        Write-Success "Git は既にインストールされています"
        return
    }

    try {
        if (Get-Command choco -ErrorAction SilentlyContinue) {
            & choco install git -y
        }
        else {
            Write-Warning "Chocolatey が利用できません。手動でインストールしてください"
            Write-Info "Git for Windows: https://git-scm.com/download/win"
            return
        }

        # PATH の更新
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")

        Write-Success "Git のインストールが完了しました"
    }
    catch {
        Write-Warning "Git のインストールに失敗しました: $($_.Exception.Message)"
        Write-Info "手動でインストールしてください: https://git-scm.com/download/win"
    }
}

# インストール検証
function Test-Installation {
    Write-Info "インストールを検証中..."

    $errors = 0

    # Windows バージョン
    $version = [System.Environment]::OSVersion.Version
    $build = (Get-ItemProperty "HKLM:SOFTWARE\Microsoft\Windows NT\CurrentVersion").CurrentBuild
    Write-Success "Windows: $($version.Major).$($version.Minor) (Build: $build)"

    # WSL2
    try {
        $wslVersion = & wsl --version 2>$null
        if ($wslVersion) {
            Write-Success "WSL2: インストール済み"
        }
        else {
            Write-Error "WSL2 が見つかりません"
            $errors++
        }
    }
    catch {
        Write-Error "WSL2 が見つかりません"
        $errors++
    }

    # Docker Desktop
    $dockerPath = "${env:ProgramFiles}\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $dockerPath) {
        Write-Success "Docker Desktop: インストール済み"

        try {
            $dockerVersion = & docker --version 2>$null
            Write-Success "Docker: $dockerVersion"
        }
        catch {
            Write-Warning "Docker コマンドが利用できません"
        }

        try {
            $composeVersion = & docker compose version 2>$null
            Write-Success "Docker Compose: $composeVersion"
        }
        catch {
            Write-Warning "Docker Compose が利用できません"
        }
    }
    else {
        Write-Error "Docker Desktop が見つかりません"
        $errors++
    }

    # Git
    if (Get-Command git -ErrorAction SilentlyContinue) {
        $gitVersion = & git --version 2>$null
        Write-Success "Git: $gitVersion"
    }
    else {
        Write-Error "Git が見つかりません"
        $errors++
    }

    # Chocolatey
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        $chocoVersion = & choco --version 2>$null
        Write-Success "Chocolatey: $chocoVersion"
    }
    else {
        Write-Warning "Chocolatey が見つかりません（オプション）"
    }

    if ($errors -eq 0) {
        Write-Success "✅ すべての依存関係が正常にインストールされました！"
        return $true
    }
    else {
        Write-Error "❌ $errors 個のエラーが見つかりました"
        return $false
    }
}

# 使用方法の表示
function Show-Usage {
    Write-Host @"
GitHub Actions Simulator - Windows インストールスクリプト

使用方法:
  .\scripts\install-windows.ps1 [オプション]

オプション:
  -Help               このヘルプを表示
  -DockerOnly         Docker Desktop のみをインストール
  -SkipOptimization   最適化設定をスキップ
  -VerifyOnly         インストール検証のみを実行
  -WSLOnly            WSL2 のみをセットアップ

例:
  .\scripts\install-windows.ps1                # 完全インストール
  .\scripts\install-windows.ps1 -DockerOnly   # Docker Desktop のみ
  .\scripts\install-windows.ps1 -VerifyOnly   # 検証のみ実行
  .\scripts\install-windows.ps1 -WSLOnly      # WSL2 のみセットアップ

注意:
  このスクリプトは管理者権限で実行する必要があります。
  PowerShell を右クリックして「管理者として実行」を選択してください。
"@
}

# メイン処理
function Main {
    if ($Help) {
        Show-Usage
        exit 0
    }

    Write-Host "🪟 GitHub Actions Simulator - Windows インストーラー" -ForegroundColor Cyan
    Write-Host "====================================================" -ForegroundColor Cyan
    Write-Host ""

    # 検証のみの場合
    if ($VerifyOnly) {
        Test-Installation
        exit 0
    }

    # 管理者権限確認
    Test-AdminRights

    # Windows バージョン確認
    Test-WindowsVersion

    Write-Host ""

    # WSL2 のセットアップ
    Enable-WSL2
    Update-WSLKernel
    Set-WSL2Default
    Install-UbuntuWSL

    if ($WSLOnly) {
        Write-Success "WSL2 のセットアップが完了しました"
        Write-Info "システムを再起動してから Docker Desktop をインストールしてください"
        exit 0
    }

    # 再起動が必要かチェック
    $rebootRequired = $false
    $wslFeature = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux
    $vmFeature = Get-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform

    if ($wslFeature.RestartRequired -or $vmFeature.RestartRequired) {
        $rebootRequired = $true
    }

    if ($rebootRequired) {
        Write-Warning "システムの再起動が必要です"
        $response = Read-Host "今すぐ再起動しますか？ (y/N)"
        if ($response -match "^[Yy]$") {
            Write-Info "システムを再起動しています..."
            Restart-Computer -Force
        }
        else {
            Write-Info "再起動後にこのスクリプトを再実行してください"
            exit 0
        }
    }

    # Chocolatey のインストール
    Install-Chocolatey

    # Docker Desktop のインストール
    Install-DockerDesktop
    Start-DockerDesktop

    if ($DockerOnly) {
        Test-Installation
        exit 0
    }

    # その他のツールのインストール
    Install-Git

    # 最適化設定
    if (-not $SkipOptimization) {
        Optimize-WSL2Config
    }

    Write-Host ""
    Write-Host "🎉 インストールが完了しました！" -ForegroundColor Green
    Write-Host ""

    # インストール検証
    $success = Test-Installation

    Write-Host ""
    Write-Host "📋 次のステップ:" -ForegroundColor Cyan
    Write-Host "  1. Docker Desktop の WSL2 統合を有効化"
    Write-Host "  2. WSL2 Ubuntu 内で GitHub Actions Simulator を実行:"
    Write-Host "     wsl"
    Write-Host "     cd /mnt/c/path/to/your/project"
    Write-Host "     ./scripts/run-actions.sh --check-deps"
    Write-Host ""
    Write-Host "📖 詳細なドキュメント: docs/PLATFORM_SUPPORT.md#windows-wsl2" -ForegroundColor Cyan

    if (-not $success) {
        exit 1
    }
}

# スクリプトが直接実行された場合のみ Main を呼び出し
if ($MyInvocation.InvocationName -ne '.') {
    Main
}
